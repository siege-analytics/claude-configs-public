#!/usr/bin/env python3
"""Classify shell invocations that can bypass catalog-managed storage.

The command is parsed as data. This module never invokes a shell, expands a
variable, or evaluates a payload. Exit 2 means a dangerous invocation was
found; exit 0 means no supported dangerous invocation was found.
"""

import ast
import os
import re
import shlex
import sys

MAX_RECURSION = 8
HEREDOC_MARKER = "__CATALOG_GUARD_HEREDOC_{}__"
SUBSTITUTION_MARKER = "__CATALOG_GUARD_SUBSTITUTION_{}__"
QUOTED_SUBSTITUTION_MARKER = "__CATALOG_GUARD_QUOTED_SUBSTITUTION_{}__"
PROCESS_INPUT_MARKER = "__CATALOG_GUARD_PROCESS_INPUT_{}__"
PROCESS_OUTPUT_MARKER = "__CATALOG_GUARD_PROCESS_OUTPUT_{}__"

MANAGED_URI_RE = re.compile(
    r"s3a?://(?:hive-warehouse|silver|gold|bronze|bullion|platinum|quicksilver)(?:/|$)",
    re.IGNORECASE,
)
RAW_WRITE_RE = re.compile(
    r"\.\s*write\s*\.\s*(?:save|parquet|text|json|csv)\s*\([^)]*s3a?://",
    re.IGNORECASE | re.DOTALL,
)
FORMAT_RE = re.compile(
    r"\.\s*write\s*\.\s*format\s*\(\s*[\"']?(?:delta|iceberg|parquet)[\"']?\s*\)",
    re.IGNORECASE | re.DOTALL,
)
SAVE_URI_RE = re.compile(
    r"\.\s*save\s*\([^)]*s3a?://", re.IGNORECASE | re.DOTALL
)
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
PYTHON_RE = re.compile(r"^python(?:[0-9]+(?:\.[0-9]+)*)?$")

RAW_WRITE_REASON = "Python/Spark raw-path write (.write.save/parquet/etc. with s3 path)"
FORMAT_SAVE_REASON = "Spark write.format().save() with raw s3 path - bypasses catalog"
OBJECT_COPY_REASON = "Direct S3 copy into catalog-managed bucket"
KUBECTL_WRITE_REASON = "kubectl exec + Python + Spark Delta write - likely catalog bypass"
DEPTH_REASON = (
    "Command nesting exceeds catalog-guard classifier depth; refusing to classify"
)


class ClassificationDepthError(RuntimeError):
    """Signal that bounded classification cannot safely continue."""


def _basename(token):
    return os.path.basename(token)


def _is_shell_comment_boundary(chars):
    if not chars:
        return True
    previous = chars[-1]
    if previous in ";|&(){}":
        return True
    if not previous.isspace():
        return False
    backslashes = 0
    index = len(chars) - 2
    while index >= 0 and chars[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 0


def _parse_heredoc_delimiter(line, start):
    """Apply shell quote removal to one heredoc delimiter word."""
    delimiter = []
    quoted = False
    quote = None
    escaped = False
    i = start
    while i < len(line):
        ch = line[i]
        if escaped:
            delimiter.append(ch)
            quoted = True
            escaped = False
            i += 1
            continue
        if quote == "'":
            quoted = True
            if ch == "'":
                quote = None
            else:
                delimiter.append(ch)
            i += 1
            continue
        if quote == '"':
            quoted = True
            if ch == "\\":
                escaped = True
            elif ch == '"':
                quote = None
            else:
                delimiter.append(ch)
            i += 1
            continue
        if ch in " \t\r\n;|&<>":
            break
        if ch == "\\":
            escaped = True
            quoted = True
        elif ch in ("'", '"'):
            quote = ch
            quoted = True
        else:
            delimiter.append(ch)
        i += 1
    if quote is not None or escaped or not delimiter:
        return "", i, quoted, True
    return "".join(delimiter), i, quoted, False


def _remove_line_continuations(command):
    """Apply shell backslash-newline removal without evaluating the command."""
    out = []
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "\\" and quote != "'":
            if i + 1 < len(command) and command[i + 1] == "\n":
                i += 2
                continue
            if i + 2 < len(command) and command[i + 1 : i + 3] == "\r\n":
                i += 3
                continue
            out.append(ch)
            if i + 1 < len(command):
                out.append(command[i + 1])
                i += 2
                continue
        if ch == "'" and quote != '"':
            quote = None if quote == "'" else "'"
        elif ch == '"' and quote != "'":
            quote = None if quote == '"' else '"'
        out.append(ch)
        i += 1
    return "".join(out)


def _find_heredoc_specs(line, initial_quote=None):
    """Return heredoc declarations plus shell quote state across physical lines."""
    specs = []
    quote = initial_quote
    escaped = False
    i = 0
    token_boundary = True
    while i < len(line):
        ch = line[i]
        if escaped:
            escaped = False
            token_boundary = False
            i += 1
            continue
        if quote == "'":
            if ch == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if ch == "\\":
                escaped = True
            elif ch == '"':
                quote = None
            i += 1
            continue
        if ch == "\\":
            escaped = True
            token_boundary = False
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            token_boundary = False
            i += 1
            continue
        if ch == "#" and token_boundary:
            break
        if (
            line.startswith("<<", i)
            and not line.startswith("<<<", i)
            and (i == 0 or line[i - 1] != "<")
        ):
            start = i
            j = i + 2
            strip_tabs = False
            if j < len(line) and line[j] == "-":
                strip_tabs = True
                j += 1
            while j < len(line) and line[j] in " \t":
                j += 1
            if j >= len(line) or line[j] in "\r\n;|&<>":
                i += 2
                token_boundary = False
                continue
            delimiter, j, quoted, malformed = _parse_heredoc_delimiter(line, j)
            if malformed:
                return [], True, quote
            specs.append((start, j, delimiter, strip_tabs, quoted))
            i = j
            token_boundary = False
            continue
        token_boundary = ch.isspace() or ch in ";|&(){}"
        i += 1
    return specs, False, quote


def _extract_heredocs(command):
    """Remove heredoc bodies from shell structure and retain them by marker."""
    lines = command.splitlines(True)
    cleaned = []
    documents = {}
    index = 0
    line_index = 0
    shell_quote = None
    while line_index < len(lines):
        line = lines[line_index]
        specs, malformed, shell_quote = _find_heredoc_specs(line, shell_quote)
        if malformed:
            # Preserve the current line so the ordinary segmenter can still
            # classify complete invocations before the malformed declaration.
            cleaned.append(line)
            return "".join(cleaned), documents, True
        if not specs:
            cleaned.append(line)
            line_index += 1
            continue

        replacements = []
        pending = []
        for start, end, delimiter, strip_tabs, quoted in specs:
            marker = HEREDOC_MARKER.format(index)
            index += 1
            replacements.append((start, end, marker))
            pending.append((marker, delimiter, strip_tabs, quoted))
        for start, end, marker in reversed(replacements):
            line = line[:start] + " " + marker + " " + line[end:]
        cleaned.append(line)
        line_index += 1

        for marker, delimiter, strip_tabs, quoted in pending:
            body_lines = []
            terminated = False
            while line_index < len(lines):
                candidate = lines[line_index]
                compare = candidate.rstrip("\r\n")
                if strip_tabs:
                    compare = compare.lstrip("\t")
                line_index += 1
                if compare == delimiter:
                    terminated = True
                    break
                body_lines.append(candidate.lstrip("\t") if strip_tabs else candidate)
            if not terminated:
                # An unterminated heredoc is still consumed to EOF by common shells.
                # Retain the body rather than reinterpreting it as shell structure.
                pass
            documents[marker] = ("".join(body_lines), not quoted)
    return "".join(cleaned), documents, False


def _consume_dollar_paren(text, start):
    depth = 1
    quote = None
    escaped = False
    i = start + 2
    payload_start = i
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
            i += 1
            continue
        if quote == "'":
            if ch == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            if ch == "\\":
                escaped = True
            elif ch == '"':
                quote = None
            elif text.startswith("$(", i):
                depth += 1
                i += 2
                continue
            i += 1
            continue
        if ch == "\\":
            escaped = True
        elif ch in ("'", '"'):
            quote = ch
        elif text.startswith("$(", i):
            depth += 1
            i += 2
            continue
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[payload_start:i], i + 1, False
        i += 1
    return "", len(text), True


def _consume_backticks(text, start):
    escaped = False
    i = start + 1
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "`":
            return text[start + 1 : i], i + 1, False
        i += 1
    return "", len(text), True


def _mask_substitutions(
    text, comments=True, shell_quotes=True, process_substitutions=True
):
    """Mask active command substitutions and return their unevaluated payloads."""
    out = []
    payloads = []
    process_payloads = []
    quote = None
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if escaped:
            out.append(ch)
            escaped = False
            i += 1
            continue
        if shell_quotes and quote == "'":
            out.append(ch)
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "\\":
            out.append(ch)
            escaped = True
            i += 1
            continue
        if (
            comments
            and quote is None
            and ch == "#"
            and _is_shell_comment_boundary(out)
        ):
            while i < len(text) and text[i] != "\n":
                i += 1
            if i < len(text):
                out.append("\n")
                i += 1
            continue
        if shell_quotes and ch == "'" and quote is None:
            quote = "'"
            out.append(ch)
            i += 1
            continue
        if shell_quotes and ch == '"':
            quote = None if quote == '"' else '"'
            out.append(ch)
            i += 1
            continue
        if (
            process_substitutions
            and quote is None
            and (text.startswith("<(", i) or text.startswith(">(", i))
        ):
            payload, end, malformed = _consume_dollar_paren(text, i)
            if malformed:
                return "".join(out), payloads, process_payloads, True
            marker_format = PROCESS_INPUT_MARKER if text[i] == "<" else PROCESS_OUTPUT_MARKER
            marker = marker_format.format(len(process_payloads))
            process_payloads.append(payload)
            out.append(marker)
            i = end
            continue
        if text.startswith("$(", i):
            payload, end, malformed = _consume_dollar_paren(text, i)
            if malformed:
                return "".join(out), payloads, process_payloads, True
            marker_template = (
                QUOTED_SUBSTITUTION_MARKER if quote else SUBSTITUTION_MARKER
            )
            marker = marker_template.format(len(payloads))
            payloads.append(payload)
            out.append(marker)
            i = end
            continue
        if ch == "`":
            payload, end, malformed = _consume_backticks(text, i)
            if malformed:
                return "".join(out), payloads, process_payloads, True
            marker_template = (
                QUOTED_SUBSTITUTION_MARKER if quote else SUBSTITUTION_MARKER
            )
            marker = marker_template.format(len(payloads))
            payloads.append(payload)
            out.append(marker)
            i = end
            continue
        out.append(ch)
        i += 1
    if quote is not None or escaped:
        return "".join(out), payloads, process_payloads, True
    return "".join(out), payloads, process_payloads, False


def _split_segments(command):
    # Each entry is (segment, connector_from_previous). Keeping the connector
    # lets a later stdin executor distinguish `printf ... | sh` from unrelated
    # sequential commands without evaluating the pipeline.
    segments = []
    current = []
    pending_connector = None
    quote = None
    escaped = False
    i = 0

    def flush():
        nonlocal pending_connector
        segment = "".join(current).strip()
        if segment:
            segments.append((segment, pending_connector))
            pending_connector = None
            current[:] = []
            return True
        current[:] = []
        return False

    while i < len(command):
        ch = command[i]
        if escaped:
            current.append(ch)
            escaped = False
            i += 1
            continue
        if quote == "'":
            current.append(ch)
            if ch == "'":
                quote = None
            i += 1
            continue
        if quote == '"':
            current.append(ch)
            if ch == "\\":
                escaped = True
            elif ch == '"':
                quote = None
            i += 1
            continue
        if ch == "\\":
            current.append(ch)
            escaped = True
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            current.append(ch)
            i += 1
            continue
        if ch == "#" and _is_shell_comment_boundary(current):
            while i < len(command) and command[i] != "\n":
                i += 1
            continue
        if ch in "\r\n;|()":
            connector = ";"
            advance = 1
            if ch == "|":
                connector = "|"
                if i + 1 < len(command) and command[i + 1] == "|":
                    connector = "||"
                    advance = 2
                elif i + 1 < len(command) and command[i + 1] == "&":
                    connector = "|&"
                    advance = 2
            elif ch == ";" and i + 1 < len(command) and command[i + 1] == ";":
                advance = 2
            if flush():
                pending_connector = connector
            i += advance
            continue
        if ch == "&":
            if (current and current[-1] in {">", "<"}) or (
                i + 1 < len(command) and command[i + 1] == ">"
            ):
                current.append(ch)
            else:
                connector = "&&" if i + 1 < len(command) and command[i + 1] == "&" else "&"
                if flush():
                    pending_connector = connector
                if connector == "&&":
                    i += 1
            i += 1
            continue
        current.append(ch)
        i += 1
    if quote is not None or escaped:
        # Keep only complete earlier segments. An isolated malformed segment
        # cannot be classified reliably, but must not erase prior invocations.
        return segments, True
    flush()
    return segments, False


def _skip_options(tokens, index, options_with_values):
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return index + 1
        if ASSIGNMENT_RE.match(token):
            index += 1
            continue
        if not token.startswith("-") or token == "-":
            return index
        option = token.split("=", 1)[0]
        index += 1
        if option in options_with_values and "=" not in token and index < len(tokens):
            index += 1
    return index


def _xargs_command(tokens):
    options_with_values = {
        "-a", "--arg-file", "-d", "--delimiter", "-E", "--eof", "-I",
        "--replace", "-L", "--max-lines", "-n", "--max-args", "-P",
        "--max-procs", "-s", "--max-chars",
    }
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            index += 1
            break
        if not token.startswith("-") or token == "-":
            break
        option = token.split("=", 1)[0]
        attached_short_value = len(token) > 2 and token[:2] in {
            "-a", "-d", "-E", "-I", "-L", "-n", "-P", "-s"
        }
        index += 1
        if (
            option in options_with_values
            and "=" not in token
            and not attached_short_value
            and index < len(tokens)
        ):
            index += 1
    return tokens[index:]


def _unwrap_env(tokens):
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            return tokens[index + 1 :]
        if ASSIGNMENT_RE.match(token):
            index += 1
            continue
        if token in {"-S", "--split-string"} and index + 1 < len(tokens):
            try:
                return shlex.split(tokens[index + 1], comments=False, posix=True) + tokens[index + 2 :]
            except ValueError:
                return []
        if token.startswith("--split-string="):
            try:
                return shlex.split(token.split("=", 1)[1], comments=False, posix=True) + tokens[index + 1 :]
            except ValueError:
                return []
        if token.startswith("-S") and token != "-S":
            try:
                return shlex.split(token[2:], comments=False, posix=True) + tokens[index + 1 :]
            except ValueError:
                return []
        option = token.split("=", 1)[0]
        if option in {"-u", "--unset", "-C", "--chdir"}:
            index += 1
            if "=" not in token and index < len(tokens):
                index += 1
            continue
        if token.startswith("-") and token != "-":
            index += 1
            continue
        return tokens[index:]
    return []


def _remove_nonpayload_redirections(tokens):
    redirections = {">", ">>", "<", "<<<", "<>", ">&", "<&", ">|"}
    cleaned = []
    index = 0
    while index < len(tokens):
        if (
            index + 2 < len(tokens)
            and tokens[index].isdigit()
            and tokens[index + 1] in redirections
        ):
            index += 3
            continue
        if tokens[index] in redirections:
            index += 2
            continue
        cleaned.append(tokens[index])
        index += 1
    return cleaned


def _unwrap(tokens):
    tokens = _remove_nonpayload_redirections([token for token in tokens if token])
    effective_tokens = []
    for token in tokens:
        if token.startswith("__CATALOG_GUARD_HEREDOC_"):
            if effective_tokens and effective_tokens[-1].isdigit():
                effective_tokens.pop()
            continue
        effective_tokens.append(token)
    tokens = effective_tokens
    payload_markers = []
    control_words = {"if", "then", "elif", "else", "while", "until", "do"}
    redirections = {">", ">>", "<", "<<", "<<<", "<>", ">&", "<&", ">|"}
    while tokens:
        changed = True
        while tokens and changed:
            changed = False
            if (
                ASSIGNMENT_RE.match(tokens[0])
                or tokens[0] in {"!", "--", "{", "}"}
                or tokens[0].lower() in control_words
            ):
                tokens = tokens[1:]
                changed = True
                continue
            if tokens[0].startswith("__CATALOG_GUARD_HEREDOC_"):
                payload_markers.append(tokens[0])
                tokens = tokens[1:]
                changed = True
                continue
            redirection_index = 0
            if len(tokens) > 1 and tokens[0].isdigit() and tokens[1] in redirections:
                redirection_index = 1
            if tokens and tokens[redirection_index] in redirections:
                remove_count = redirection_index + 2
                tokens = tokens[remove_count:] if len(tokens) >= remove_count else []
                changed = True
        if not tokens:
            return payload_markers
        program = _basename(tokens[0])
        if program == "env":
            tokens = _unwrap_env(tokens)
            continue
        if program == "sudo":
            index = _skip_options(
                tokens,
                1,
                {"-u", "--user", "-g", "--group", "-h", "--host", "-p", "--prompt", "-C", "--close-from", "-R", "--chroot", "-T", "--command-timeout", "-r", "--role", "-t", "--type"},
            )
            tokens = tokens[index:]
            continue
        if program in {"command", "builtin", "exec", "nohup"}:
            tokens = tokens[_skip_options(tokens, 1, set()):]
            continue
        if program == "time":
            tokens = tokens[_skip_options(tokens, 1, {"-f", "--format", "-o", "--output"}):]
            continue
        if program == "timeout":
            index = _skip_options(
                tokens,
                1,
                {"-k", "--kill-after", "-s", "--signal"},
            )
            # GNU timeout requires a duration before its wrapped command.
            tokens = tokens[index + 1 :] if index < len(tokens) else []
            continue
        if program == "nice":
            tokens = tokens[
                _skip_options(tokens, 1, {"-n", "--adjustment"}) :
            ]
            continue
        if program == "stdbuf":
            tokens = tokens[
                _skip_options(
                    tokens,
                    1,
                    {"-i", "--input", "-o", "--output", "-e", "--error"},
                ) :
            ]
            continue
        if program == "setsid":
            tokens = tokens[_skip_options(tokens, 1, set()) :]
            continue
        if program == "xargs":
            tokens = _xargs_command(tokens)
            continue
        break
    return tokens + payload_markers


def _first_positionals(tokens, options_with_values, count):
    values = []
    index = 0
    while index < len(tokens) and len(values) < count:
        token = tokens[index]
        if token == "--":
            index += 1
            values.extend(tokens[index : index + count - len(values)])
            break
        if token.startswith("-") and token != "-":
            option = token.split("=", 1)[0]
            index += 1
            if option in options_with_values and "=" not in token and index < len(tokens):
                index += 1
            continue
        values.append(token.lower())
        index += 1
    return values


def _all_positionals(tokens, options_with_values):
    values = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            values.extend(tokens[index + 1 :])
            break
        if token.startswith("-") and token != "-":
            option = token.split("=", 1)[0]
            index += 1
            if option in options_with_values and "=" not in token and index < len(tokens):
                index += 1
            continue
        values.append(token)
        index += 1
    return values


def _aws_copy_operands(args):
    options_with_values = {
        "--profile", "--region", "--endpoint-url", "--ca-bundle",
        "--cli-read-timeout", "--cli-connect-timeout", "--output", "--query",
        "--color", "--exclude", "--include", "--acl", "--sse", "--sse-c",
        "--sse-c-key", "--sse-kms-key-id", "--sse-c-copy-source",
        "--sse-c-copy-source-key", "--storage-class", "--grants",
        "--website-redirect", "--content-type", "--cache-control",
        "--content-disposition", "--content-encoding", "--content-language",
        "--expires", "--source-region", "--page-size", "--request-payer",
        "--checksum-mode", "--checksum-algorithm", "--metadata-directive",
        "--copy-props", "--metadata",
    }
    positionals = _all_positionals(args, options_with_values)
    if len(positionals) < 4 or [value.lower() for value in positionals[:2]] not in (
        ["s3", "cp"],
        ["s3", "sync"],
    ):
        return []
    return positionals[2:4]


def _mc_copy_operands(args):
    options_with_values = {
        "--config-dir", "--limit-upload", "--limit-download", "--custom-header",
        "--attr", "--encrypt", "--storage-class", "--tags", "--rewind",
        "--version-id", "--newer-than", "--older-than",
    }
    positionals = _all_positionals(args, options_with_values)
    if not positionals or positionals[0].lower() not in {"cp", "mirror"}:
        return []
    return positionals[1:]


def _python_inline_payloads(args):
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--" or arg == "-" or not arg.startswith("-"):
            return []
        if arg == "-m" or arg.startswith("-m"):
            # Everything after the module selector belongs to the module.
            return []
        if arg in {"-W", "-X"}:
            index += 2
            continue
        if arg.startswith("--"):
            index += 1
            continue
        option_text = arg[1:]
        c_index = option_text.find("c")
        if c_index >= 0:
            attached = option_text[c_index + 1 :]
            if attached:
                return [attached]
            return [args[index + 1]] if index + 1 < len(args) else []
        index += 1
    return []


def _python_reads_stdin_code(args):
    code_args = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("__CATALOG_GUARD_HEREDOC_"):
            index += 1
            continue
        if arg == "<<<":
            index += 2
            continue
        code_args.append(arg)
        index += 1
    args = code_args
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--":
            index += 1
            break
        if arg == "-":
            return True
        if arg == "-m" or arg.startswith("-m"):
            return False
        if arg in {"-W", "-X"}:
            index += 2
            continue
        if arg.startswith("--"):
            index += 1
            continue
        if arg.startswith("-"):
            index += 1
            continue
        return False
    return index >= len(args) or args[index] == "-"


def _shell_noexec(args):
    """Return the effective invocation-time noexec state before any script."""
    value_options = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
    noexec = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--" or arg == "-" or not arg.startswith(("-", "+")):
            break
        if arg in value_options:
            if (
                arg in {"-o", "+o"}
                and index + 1 < len(args)
                and args[index + 1] == "noexec"
            ):
                noexec = arg == "-o"
            index += 2
            continue
        if arg.startswith("--"):
            index += 1
            continue
        flags = arg[1:]
        if "n" in flags:
            noexec = arg.startswith("-")
        if "c" in flags and arg.startswith("-"):
            break
        index += 1
    return noexec


def _shell_inline_payloads(args):
    # Common no-value invocation flags accepted in clusters by supported
    # Bourne-like shells. Value-taking options are skipped explicitly.
    cluster_flags = set("abefhkmnptuvxBCEHPTirsDcl")
    value_options = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
    noexec = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--" or arg == "-" or not arg.startswith(("-", "+")):
            return []
        if arg in value_options:
            if (
                arg in {"-o", "+o"}
                and index + 1 < len(args)
                and args[index + 1] == "noexec"
            ):
                noexec = arg == "-o"
            index += 2
            continue
        if arg.startswith("--"):
            index += 1
            continue
        flags = arg[1:]
        if "n" in flags:
            noexec = arg.startswith("-")
        if (
            "c" in flags
            and arg.startswith("-")
            and flags
            and all(flag in cluster_flags for flag in flags)
        ):
            if noexec:
                return []
            return [args[index + 1]] if index + 1 < len(args) else []
        index += 1
    return []


def _shell_reads_stdin_code(args):
    code_args = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg.startswith("__CATALOG_GUARD_HEREDOC_"):
            index += 1
            continue
        if arg == "<<<":
            index += 2
            continue
        code_args.append(arg)
        index += 1

    value_options = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
    index = 0
    reads_stdin = False
    while index < len(code_args):
        arg = code_args[index]
        if arg == "--":
            index += 1
            break
        if arg == "-":
            return True
        if arg in value_options:
            index += 2
            continue
        if arg.startswith("--"):
            index += 1
            continue
        if arg.startswith(("-", "+")):
            flags = arg[1:]
            if "s" in flags:
                reads_stdin = True
            index += 1
            continue
        return reads_stdin
    return reads_stdin or index >= len(code_args)


def _source_reads_stdin(args):
    positionals = [arg for arg in args if arg == "-" or not arg.startswith("-")]
    if not positionals:
        return False
    return positionals[0] in {
        "/dev/stdin",
        "/dev/fd/0",
        "/proc/self/fd/0",
    }


def _chain_contains_write(node):
    while node is not None:
        if isinstance(node, ast.Name) and getattr(node, "_catalog_writer", False):
            return True
        if isinstance(node, ast.Attribute):
            if node.attr == "write":
                return True
            node = node.value
            continue
        if isinstance(node, ast.Call):
            method, receiver = _writer_call_target(node)
            if method == "write":
                return True
            node = receiver if receiver is not None else node.func
            continue
        return False
    return False


def _static_string(node):
    if isinstance(node, ast.Name):
        return getattr(node, "_catalog_static_string", None)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left)
        right = _static_string(node.right)
        return left + right if left is not None and right is not None else None
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
                continue
            if isinstance(value, ast.FormattedValue):
                resolved = _static_string(value.value)
                if resolved is not None and value.format_spec is None:
                    parts.append(resolved)
                    continue
            return None
        return "".join(parts)
    return None


class _StaticLoadAnnotator(ast.NodeVisitor):
    def __init__(
        self, values, writers, functions=None, writer_methods=None
    ):
        self.values = values
        self.writers = writers
        self.functions = dict(functions or {})
        self.writer_methods = set(writer_methods or set())

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Load):
            return
        if node.id in self.values:
            node._catalog_static_string = self.values[node.id]
        elif hasattr(node, "_catalog_static_string"):
            del node._catalog_static_string
        if node.id in self.writers:
            node._catalog_writer = True
        elif hasattr(node, "_catalog_writer"):
            del node._catalog_writer
        if node.id in self.writer_methods:
            node._catalog_writer_method = True
        elif hasattr(node, "_catalog_writer_method"):
            del node._catalog_writer_method

    def visit_Call(self, node):
        node._catalog_static_values = dict(self.values)
        node._catalog_static_writers = set(self.writers)
        node._catalog_static_functions = dict(self.functions)
        node._catalog_static_writer_methods = set(self.writer_methods)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        return None

    def visit_AsyncFunctionDef(self, node):
        return None

    def visit_Lambda(self, node):
        return None



def _annotate_static_names(
    statements,
    inherited_values=None,
    inherited_writers=None,
    inherited_functions=None,
    inherited_writer_methods=None,
):
    values = dict(inherited_values or {})
    writers = set(inherited_writers or set())
    functions = dict(inherited_functions or {})
    writer_methods = set(inherited_writer_methods or set())
    for statement in statements:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            statement._catalog_static_values = dict(values)
            statement._catalog_static_writers = set(writers)
            default_annotator = _StaticLoadAnnotator(
                values, writers, functions, writer_methods
            )
            for default in (
                list(statement.args.defaults)
                + list(statement.args.kw_defaults)
            ):
                if default is not None:
                    default_annotator.visit(default)
            if isinstance(statement, ast.FunctionDef):
                functions[statement.name] = statement
            _annotate_static_names(
                statement.body,
                values,
                writers,
                functions,
                writer_methods,
            )
            continue
        annotator = _StaticLoadAnnotator(
            values, writers, functions, writer_methods
        )
        annotator.visit(statement)
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            value_node = statement.value
            value = _static_string(value_node) if value_node is not None else None
            is_writer = bool(value_node and _chain_contains_write(value_node))
            bound_method, bound_receiver = (
                _writer_call_target(value_node)
                if value_node is not None
                else (None, None)
            )
            is_writer_method = bool(
                bound_method in {"save", "parquet", "text", "json", "csv"}
                and _chain_contains_write(bound_receiver)
            )
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            for target in targets:
                if isinstance(target, ast.Name):
                    if value is None:
                        values.pop(target.id, None)
                    else:
                        values[target.id] = value
                    if is_writer:
                        writers.add(target.id)
                    else:
                        writers.discard(target.id)
                    if is_writer_method:
                        writer_methods.add(target.id)
                    else:
                        writer_methods.discard(target.id)
                    functions.pop(target.id, None)
        elif isinstance(statement, ast.If):
            # Branch-local assignments are not treated as unconditional.
            _annotate_static_names(statement.body, values, writers, functions, writer_methods)
            _annotate_static_names(statement.orelse, values, writers, functions, writer_methods)
        elif isinstance(statement, (ast.For, ast.AsyncFor, ast.While)):
            _annotate_static_names(statement.body, values, writers, functions, writer_methods)
            _annotate_static_names(statement.orelse, values, writers, functions, writer_methods)
        elif isinstance(statement, (ast.With, ast.AsyncWith)):
            _annotate_static_names(statement.body, values, writers, functions, writer_methods)
        elif isinstance(statement, ast.Try):
            _annotate_static_names(statement.body, values, writers, functions, writer_methods)
            _annotate_static_names(statement.orelse, values, writers, functions, writer_methods)
            _annotate_static_names(statement.finalbody, values, writers, functions, writer_methods)
            for handler in statement.handlers:
                _annotate_static_names(handler.body, values, writers, functions, writer_methods)
    return values, writers


def _has_s3_static_path(node):
    if isinstance(node, ast.Starred):
        return _has_s3_static_path(node.value)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_has_s3_static_path(item) for item in node.elts)
    value = _static_string(node)
    return bool(value and re.search(r"s3a?://", value, re.IGNORECASE))


def _keyword_path_has_s3(keywords):
    for keyword in keywords:
        if keyword.arg == "path" and _has_s3_static_path(keyword.value):
            return True
        if keyword.arg is None and isinstance(keyword.value, ast.Dict):
            for key, value in zip(keyword.value.keys, keyword.value.values):
                if (_static_string(key) or "").lower() == "path" and _has_s3_static_path(value):
                    return True
    return False


def _writer_call_target(function):
    if isinstance(function, ast.Attribute):
        return function.attr, function.value
    if (
        isinstance(function, ast.Call)
        and isinstance(function.func, ast.Name)
        and function.func.id == "getattr"
        and len(function.args) >= 2
    ):
        method = _static_string(function.args[1])
        if method:
            return method, function.args[0]
    return None, None


def _writer_path_has_s3(call, receiver):
    if call.args and _has_s3_static_path(call.args[0]):
        return True
    if _keyword_path_has_s3(call.keywords):
        return True
    node = receiver
    while isinstance(node, ast.Call):
        method, parent = _writer_call_target(node.func)
        if method == "option" and len(node.args) >= 2:
            key = _static_string(node.args[0])
            if key and key.lower() == "path" and _has_s3_static_path(node.args[1]):
                return True
        if method == "options" and _keyword_path_has_s3(node.keywords):
            return True
        node = parent
    return False


def _format_call_in_chain(node):
    while node is not None:
        if isinstance(node, ast.Call):
            method, receiver = _writer_call_target(node.func)
            if (
                method == "format"
                and _chain_contains_write(receiver)
                and node.args
                and (_static_string(node.args[0]) or "").lower()
                in {"delta", "iceberg", "parquet"}
            ):
                return True
            node = receiver
            continue
        if isinstance(node, ast.Attribute):
            node = node.value
            continue
        return False
    return False


def _static_argv(node):
    if not isinstance(node, (ast.List, ast.Tuple)):
        return None
    values = [_static_string(item) for item in node.elts]
    if any(value is None for value in values):
        return None
    return shlex.join(values)


def _python_executor_payload(node):
    if not isinstance(node, ast.Call):
        return None, None
    function = node.func
    if isinstance(function, ast.Name) and function.id in {"exec", "eval"}:
        return (
            ("python", _static_string(node.args[0]))
            if node.args
            else (None, None)
        )
    if not isinstance(function, ast.Attribute) or not isinstance(function.value, ast.Name):
        return None, None
    owner = function.value.id
    method = function.attr
    if owner == "os" and method in {"system", "popen"}:
        return (
            ("shell", _static_string(node.args[0]))
            if node.args
            else (None, None)
        )
    if owner != "subprocess":
        return None, None
    argument = node.args[0] if node.args else next(
        (keyword.value for keyword in node.keywords if keyword.arg == "args"),
        None,
    )
    if argument is None:
        return None, None
    if method in {"getoutput", "getstatusoutput"}:
        return "shell", _static_string(argument)
    if method not in {"run", "call", "check_call", "check_output", "Popen"}:
        return None, None
    shell_enabled = any(
        keyword.arg == "shell"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value is True
        for keyword in node.keywords
    )
    if shell_enabled and isinstance(argument, (ast.List, ast.Tuple)):
        first = _static_string(argument.elts[0]) if argument.elts else None
        return "shell", first
    argv = _static_argv(argument)
    if argv:
        return "shell", argv
    return (
        ("shell", _static_string(argument))
        if shell_enabled
        else (None, None)
    )


def _executed_ast_nodes(tree):
    def walk(node, active_functions=None, execute_lambda=False):
        active_functions = set(active_functions or set())
        yield node
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                yield from walk(decorator, active_functions)
            for default in node.args.defaults + node.args.kw_defaults:
                if default is not None:
                    yield from walk(default, active_functions)
            return
        if isinstance(node, ast.Lambda) and not execute_lambda:
            return
        if isinstance(node, ast.Call):
            for child in ast.iter_child_nodes(node):
                yield from walk(child, active_functions)
            if isinstance(node.func, ast.Lambda):
                annotator = _StaticLoadAnnotator(
                    getattr(node, "_catalog_static_values", {}),
                    getattr(node, "_catalog_static_writers", set()),
                    getattr(node, "_catalog_static_functions", {}),
                    getattr(node, "_catalog_static_writer_methods", set()),
                )
                annotator.visit(node.func.body)
                yield from walk(
                    node.func.body, active_functions, execute_lambda=True
                )
            elif (
                isinstance(node.func, ast.Name)
                and node.func.id
                in getattr(node, "_catalog_static_functions", {})
                and node.func.id not in active_functions
            ):
                function = node._catalog_static_functions[node.func.id]
                call_values = dict(
                    getattr(node, "_catalog_static_values", {})
                )
                positional = (
                    list(function.args.posonlyargs)
                    + list(function.args.args)
                )
                defaults = [None] * (
                    len(positional) - len(function.args.defaults)
                ) + list(function.args.defaults)
                keyword_arguments = {
                    keyword.arg: keyword.value
                    for keyword in node.keywords
                    if keyword.arg is not None
                }
                for index, parameter in enumerate(positional):
                    argument = (
                        node.args[index]
                        if index < len(node.args)
                        else keyword_arguments.get(
                            parameter.arg, defaults[index]
                        )
                    )
                    call_values.pop(parameter.arg, None)
                    value = _static_string(argument)
                    if value is not None:
                        call_values[parameter.arg] = value
                for parameter, default in zip(
                    function.args.kwonlyargs, function.args.kw_defaults
                ):
                    argument = keyword_arguments.get(parameter.arg, default)
                    call_values.pop(parameter.arg, None)
                    value = _static_string(argument)
                    if value is not None:
                        call_values[parameter.arg] = value
                _annotate_static_names(
                    function.body,
                    call_values,
                    getattr(node, "_catalog_static_writers", set()),
                    getattr(node, "_catalog_static_functions", {}),
                    getattr(
                        node, "_catalog_static_writer_methods", set()
                    ),
                )
                nested_active = active_functions | {node.func.id}
                for statement in function.body:
                    yield from walk(statement, nested_active)
            return
        for child in ast.iter_child_nodes(node):
            yield from walk(child, active_functions, execute_lambda)

    yield from walk(tree)


def _python_ast_write_reason(
    payload,
    kubectl_exec=False,
    depth=0,
    inherited_values=None,
    inherited_writers=None,
):
    if depth > MAX_RECURSION:
        return True, DEPTH_REASON
    try:
        tree = ast.parse(payload)
    except (SyntaxError, ValueError, TypeError):
        return False, None
    _annotate_static_names(
        tree.body,
        inherited_values=inherited_values,
        inherited_writers=inherited_writers,
    )
    for node in _executed_ast_nodes(tree):
        if not isinstance(node, ast.Call):
            continue
        executor_kind, executor_payload = _python_executor_payload(node)
        if executor_payload:
            if executor_kind == "shell":
                reason = classify_command(executor_payload, depth + 1)
            else:
                _parsed, reason = _python_ast_write_reason(
                    executor_payload,
                    kubectl_exec=kubectl_exec,
                    depth=depth + 1,
                    inherited_values=getattr(
                        node, "_catalog_static_values", None
                    ),
                    inherited_writers=getattr(
                        node, "_catalog_static_writers", None
                    ),
                )
            if reason:
                return True, reason
        if (
            isinstance(node.func, ast.Name)
            and getattr(node.func, "_catalog_writer_method", False)
            and _writer_path_has_s3(node, None)
        ):
            return True, RAW_WRITE_REASON
        method, receiver = _writer_call_target(node.func)
        if (
            method in {"save", "parquet", "text", "json", "csv"}
            and _chain_contains_write(receiver)
            and _writer_path_has_s3(node, receiver)
        ):
            if method == "save" and _format_call_in_chain(receiver):
                return True, FORMAT_SAVE_REASON
            return True, RAW_WRITE_REASON
        if (
            kubectl_exec
            and method == "format"
            and _chain_contains_write(receiver)
            and _format_call_in_chain(node)
        ):
            return True, KUBECTL_WRITE_REASON
    return True, None


def _write_reason(payload, kubectl_exec=False, depth=0):
    parsed, reason = _python_ast_write_reason(
        payload, kubectl_exec=kubectl_exec, depth=depth
    )
    if reason:
        return reason
    if parsed:
        return None
    if RAW_WRITE_RE.search(payload):
        return RAW_WRITE_REASON
    if FORMAT_RE.search(payload) and SAVE_URI_RE.search(payload):
        return FORMAT_SAVE_REASON
    if kubectl_exec and FORMAT_RE.search(payload):
        return KUBECTL_WRITE_REASON
    return None


def _fd_states(tokens, documents):
    # Track bounded fd sources left-to-right. Each value is (kind, payloads).
    fd_sources = {0: ("inherit", [])}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in documents:
            fd = int(tokens[index - 1]) if index > 0 and tokens[index - 1].isdigit() else 0
            fd_sources[fd] = ("payload", [documents[token][0]])
            index += 1
            continue
        if token == "<<<" and index + 1 < len(tokens):
            fd = int(tokens[index - 1]) if index > 0 and tokens[index - 1].isdigit() else 0
            fd_sources[fd] = ("payload", [tokens[index + 1]])
            index += 2
            continue

        if token.isdigit() and index + 1 < len(tokens) and tokens[index + 1] == "<":
            fd = int(token)
            target_index = index + 2
        elif token == "<":
            fd = 0
            target_index = index + 1
        else:
            index += 1
            continue

        target = tokens[target_index] if target_index < len(tokens) else ""
        if target == "&" and target_index + 1 < len(tokens):
            target += tokens[target_index + 1]
            target_index += 1
        if target.startswith("__CATALOG_GUARD_PROCESS_INPUT_"):
            fd_sources[fd] = ("process", [target])
        elif re.fullmatch(r"&\d+", target):
            source_fd = int(target[1:])
            fd_sources[fd] = fd_sources.get(source_fd, ("file", []))
        elif target == "&-":
            fd_sources[fd] = ("file", [])
        else:
            fd_path = re.fullmatch(r"/(?:dev|proc/self)/fd/(\d+)", target)
            if target == "/dev/stdin":
                source_fd = 0
            elif fd_path:
                source_fd = int(fd_path.group(1))
            else:
                source_fd = None
            if source_fd is not None:
                fd_sources[fd] = fd_sources.get(source_fd, ("file", []))
            else:
                fd_sources[fd] = ("file", [])
        index = target_index + 1
    return fd_sources


def _stdin_state(tokens, documents):
    return _fd_states(tokens, documents).get(0, ("inherit", []))


def _fd_path_number(path):
    if path == "/dev/stdin":
        return 0
    match = re.fullmatch(r"/(?:dev|proc/self)/fd/(\d+)", path)
    return int(match.group(1)) if match else None


def _stdin_source_type(tokens, documents):
    return _stdin_state(tokens, documents)[0]


def _payloads_for(tokens, documents):
    source_type, payloads = _stdin_state(tokens, documents)
    return list(payloads) if source_type == "payload" else []


def _decode_ansi_c_content(content):
    """Decode Bash $'...' quoting without evaluating shell input."""
    simple = {
        "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f",
        "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\",
        "'": "'", '"': '"',
    }
    output = []
    index = 0
    while index < len(content):
        if content[index] != "\\" or index + 1 >= len(content):
            output.append(content[index])
            index += 1
            continue
        escaped = content[index + 1]
        if escaped == "\n":
            index += 2
            continue
        if escaped in simple:
            output.append(simple[escaped])
            index += 2
            continue
        if escaped in "01234567":
            end = index + 2
            while end < min(index + 5, len(content)) and content[end] in "01234567":
                end += 1
            output.append(chr(int(content[index + 1 : end], 8)))
            index = end
            continue
        widths = {"x": 2, "u": 4, "U": 8}
        if escaped in widths:
            end = index + 2
            limit = min(end + widths[escaped], len(content))
            while end < limit and content[end] in "0123456789abcdefABCDEF":
                end += 1
            if end > index + 2:
                value = int(content[index + 2 : end], 16)
                if value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF:
                    output.append(chr(value))
                else:
                    output.append(content[index:end])
                index = end
                continue
        output.extend(("\\", escaped))
        index += 2
    return "".join(output)


def _normalize_ansi_c_quotes(segment):
    """Convert unquoted Bash ANSI-C words to ordinary safely quoted words."""
    output = []
    quote = None
    escaped = False
    index = 0
    while index < len(segment):
        char = segment[index]
        if escaped:
            output.append(char)
            escaped = False
            index += 1
            continue
        if quote:
            output.append(char)
            if char == "\\" and quote == '"':
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char == "\\":
            output.append(char)
            escaped = True
            index += 1
            continue
        if char in ("'", '"'):
            output.append(char)
            quote = char
            index += 1
            continue
        if segment.startswith("$'", index):
            cursor = index + 2
            content = []
            while cursor < len(segment):
                if segment[cursor] == "\\" and cursor + 1 < len(segment):
                    content.extend((segment[cursor], segment[cursor + 1]))
                    cursor += 2
                    continue
                if segment[cursor] == "'":
                    break
                content.append(segment[cursor])
                cursor += 1
            if cursor >= len(segment):
                output.append(segment[index:])
                break
            output.append(shlex.quote(_decode_ansi_c_content("".join(content))))
            index = cursor + 1
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _shell_tokens(segment):
    # Punctuation-aware tokenization keeps an actual <<< operator distinct
    # from a quoted argument that merely begins with those characters.
    lexer = shlex.shlex(
        _normalize_ansi_c_quotes(segment), posix=True, punctuation_chars="<>"
    )
    lexer.whitespace_split = True
    # Real shell comments were removed at token boundaries by the segmenter;
    # a mid-word '#' is literal and must not truncate later arguments.
    lexer.commenters = ""
    return list(lexer)


def _printf_escape_at(text, index):
    if index + 1 >= len(text) or text[index] != "\\":
        return text[index], index + 1, False
    escaped = text[index + 1]
    simple = {
        "a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f",
        "n": "\n", "r": "\r", "t": "\t", "v": "\v", "\\": "\\",
        "'": "'", '"': '"',
    }
    if escaped == "c":
        return "", len(text), True
    if escaped in simple:
        return simple[escaped], index + 2, False
    if escaped == "0":
        end = index + 2
        while end < min(index + 5, len(text)) and text[end] in "01234567":
            end += 1
        digits = text[index + 2 : end]
        return chr(int(digits or "0", 8)), end, False
    if escaped == "x":
        end = index + 2
        while end < min(index + 4, len(text)) and text[end] in "0123456789abcdefABCDEF":
            end += 1
        if end > index + 2:
            return chr(int(text[index + 2 : end], 16)), end, False
    return "\\" + escaped, index + 2, False


def _decode_printf_escapes(text):
    output = []
    index = 0
    while index < len(text):
        if text[index] != "\\":
            output.append(text[index])
            index += 1
            continue
        decoded, index, stop = _printf_escape_at(text, index)
        output.append(decoded)
        if stop:
            return "".join(output), True
    return "".join(output), False


def _expand_printf_format(format_text, values):
    """Assemble bounded literal %s/%b/%% printf output without execution."""
    output = []
    value_index = 0
    conversion_count = 0
    halted = False

    def render_once():
        nonlocal value_index, conversion_count, halted
        fragment = []
        index = 0
        while index < len(format_text):
            if format_text.startswith("%%", index):
                fragment.append("%")
                index += 2
                continue
            if format_text.startswith(("%s", "%b"), index):
                conversion = format_text[index + 1]
                conversion_count += 1
                value = values[value_index] if value_index < len(values) else ""
                value_index += 1
                if conversion == "b":
                    value, halted = _decode_printf_escapes(value)
                fragment.append(value)
                index += 2
                if halted:
                    break
                continue
            if format_text[index] == "%":
                return None
            if format_text[index] == "\\":
                decoded, index, halted = _printf_escape_at(format_text, index)
                fragment.append(decoded)
                if halted:
                    break
                continue
            fragment.append(format_text[index])
            index += 1
        return "".join(fragment)

    first = render_once()
    if first is None:
        return None
    output.append(first)
    if conversion_count == 0 or halted:
        # Shell printf ignores surplus arguments when the format consumes none.
        return "".join(output)
    while value_index < len(values):
        repeated = render_once()
        if repeated is None:
            return None
        output.append(repeated)
        if halted:
            break
    return "".join(output)


def _xargs_literal_invocations(tokens, payload):
    try:
        xargs_index = next(
            index for index, token in enumerate(tokens) if _basename(token) == "xargs"
        )
    except StopIteration:
        return []
    xargs_tokens = tokens[xargs_index:]
    child = _xargs_command(xargs_tokens)
    if not child:
        return []

    replacement = None
    null_delimited = False
    max_args = None
    index = 1
    while index < len(xargs_tokens):
        token = xargs_tokens[index]
        if token == "--":
            break
        if token in {"-0", "--null"}:
            null_delimited = True
        if token in {"-n", "--max-args"} and index + 1 < len(xargs_tokens):
            try:
                max_args = max(1, int(xargs_tokens[index + 1]))
            except ValueError:
                return []
            index += 2
            continue
        if token.startswith("-n") and token != "-n":
            try:
                max_args = max(1, int(token[2:]))
            except ValueError:
                return []
        if token.startswith("--max-args="):
            try:
                max_args = max(1, int(token.split("=", 1)[1]))
            except ValueError:
                return []
        if token in {"-I", "--replace"} and index + 1 < len(xargs_tokens):
            replacement = xargs_tokens[index + 1]
            break
        if token.startswith("-I") and token != "-I":
            replacement = token[2:]
            break
        if token.startswith("--replace="):
            replacement = token.split("=", 1)[1]
            break
        index += 1

    if replacement is not None:
        items = payload.split("\0") if null_delimited else payload.splitlines()
        return [
            [token.replace(replacement, item) for token in child]
            for item in items
            if item
        ]
    if null_delimited:
        items = [item for item in payload.split("\0") if item]
    else:
        try:
            items = shlex.split(payload, comments=False, posix=True)
        except ValueError:
            return []
    if not items:
        return []
    if max_args is None:
        return [child + items]
    return [
        child + items[start : start + max_args]
        for start in range(0, len(items), max_args)
    ]


def _literal_producer_payloads(tokens, documents):
    stdin_payloads = _payloads_for(tokens, documents)
    tokens = _unwrap(tokens)
    if not tokens:
        return []
    program = _basename(tokens[0]).lower()
    args = tokens[1:]
    if program == "printf" and args:
        if args[0] == "--":
            args = args[1:]
        if not args:
            return []
        assembled = _expand_printf_format(args[0], args[1:])
        return [assembled] if assembled is not None else []
    if program == "echo":
        decode_escapes = False
        while args:
            option = args[0]
            if option == "--":
                args = args[1:]
                break
            if not re.fullmatch(r"-[neE]+", option):
                break
            for flag in option[1:]:
                if flag == "e":
                    decode_escapes = True
                elif flag == "E":
                    decode_escapes = False
            args = args[1:]
        if not args:
            return []
        output = " ".join(args)
        if decode_escapes:
            output, _ = _decode_printf_escapes(output)
        return [output]
    if program == "cat":
        return stdin_payloads
    return []


def _has_stdout_redirection(tokens):
    for index, token in enumerate(tokens):
        if token not in {">", ">>", ">|"}:
            continue
        if index > 0 and tokens[index - 1].isdigit() and tokens[index - 1] != "1":
            continue
        return True
    return False


def _known_stdout_payloads(tokens, documents, incoming_payloads, depth=0):
    if depth > MAX_RECURSION:
        raise ClassificationDepthError(DEPTH_REASON)
    literal = _literal_producer_payloads(tokens, documents)
    if literal:
        return literal
    effective = _unwrap(tokens)
    if not effective:
        return []
    program = _basename(effective[0]).lower()
    args = effective[1:]
    if program == "cat":
        positionals = [arg for arg in args if arg == "-" or not arg.startswith("-")]
        if not positionals or "-" in positionals:
            return list(incoming_payloads)
    if program == "tee":
        return list(incoming_payloads)
    if program == "eval":
        inline_commands = [" ".join(args)] if args else []
    elif program in {"sh", "bash", "dash", "zsh", "ksh"}:
        inline_commands = _shell_inline_payloads(args)
    else:
        inline_commands = []
    if inline_commands:
        outputs = []
        for inline_command in inline_commands:
            outputs.extend(
                _literal_outputs_for_command(
                    inline_command,
                    incoming_payloads,
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            )
        return outputs
    return []


def _pipeline_output_payloads(tokens, documents, incoming_payloads, depth=0):
    if depth > MAX_RECURSION:
        raise ClassificationDepthError(DEPTH_REASON)
    if _has_stdout_redirection(tokens):
        return []
    return _known_stdout_payloads(
        tokens, documents, incoming_payloads, depth=depth
    )


def _literal_outputs_for_command(
    command, input_payloads=None, inherited_documents=None, depth=0
):
    if depth > MAX_RECURSION:
        raise ClassificationDepthError(DEPTH_REASON)
    command = _remove_line_continuations(command)
    cleaned, local_documents, _heredoc_malformed = _extract_heredocs(command)
    documents = dict(inherited_documents or {})
    documents.update(local_documents)
    masked, substitutions, process_substitutions, _malformed = _mask_substitutions(cleaned)
    segments, _segment_malformed = _split_segments(masked)
    try:
        tokenized = [
            (_shell_tokens(segment), connector) for segment, connector in segments
        ]
    except ValueError:
        return []
    stage_outputs = []
    captured_outputs = []
    remaining_payloads = list(input_payloads or [])
    for index, (tokens, connector) in enumerate(tokenized):
        incoming = list(remaining_payloads)
        if connector in {"|", "|&"} and index > 0:
            incoming = stage_outputs[index - 1]
        tokens = _expand_known_substitution_tokens(
            tokens, substitutions, documents, depth, input_payloads=incoming
        )
        stdin_source = _stdin_source_type(tokens, documents)
        if stdin_source == "payload":
            incoming = _payloads_for(tokens, documents)
        elif stdin_source == "file":
            incoming = []
        outputs = _pipeline_output_payloads(
            tokens, documents, incoming, depth=depth
        )
        stage_outputs.append(outputs)
        next_is_pipe = (
            index + 1 < len(tokenized)
            and tokenized[index + 1][1] in {"|", "|&"}
        )
        if not next_is_pipe:
            captured_outputs.extend(outputs)
        if (
            connector not in {"|", "|&"}
            and incoming
            and (
                _consumes_inherited_stdin(tokens, documents, depth + 1)
                or _script_process_consumes_stdin(
                    tokens, process_substitutions, documents, depth + 1
                )
            )
        ):
            remaining_payloads = []
    return captured_outputs


def _expand_known_substitution_tokens(
    tokens, substitutions, documents, depth, input_payloads=None
):
    """Replace command-substitution markers only when stdout is literal."""
    expanded = list(tokens)
    for index, command in enumerate(substitutions):
        marker = SUBSTITUTION_MARKER.format(index)
        quoted_marker = QUOTED_SUBSTITUTION_MARKER.format(index)
        if not any(
            marker in token or quoted_marker in token for token in expanded
        ):
            continue
        outputs = _literal_outputs_for_command(
            command,
            input_payloads=input_payloads,
            inherited_documents=documents,
            depth=depth + 1,
        )
        if not outputs:
            continue
        # Shell command substitution strips trailing newlines. Unquoted output
        # then undergoes IFS whitespace splitting, but quotes inside expansion
        # output are ordinary data and must not be reparsed.
        replacement = "".join(outputs).rstrip("\n")
        replaced = []
        for token in expanded:
            if token == marker:
                replaced.extend(replacement.split())
                continue
            replaced.append(
                token.replace(marker, replacement).replace(
                    quoted_marker, replacement
                )
            )
        expanded = replaced
    return expanded


def _process_marker_index(token):
    marker_match = re.fullmatch(r"__CATALOG_GUARD_PROCESS_INPUT_(\d+)__", token)
    return int(marker_match.group(1)) if marker_match else None


def _fd_script_payloads(
    tokens,
    path,
    process_substitutions,
    documents,
    input_payloads,
    depth,
):
    fd = _fd_path_number(path)
    if fd is None:
        return []
    source_type, sources = _fd_states(tokens, documents or {}).get(
        fd, ("file", [])
    )
    if source_type == "payload":
        return list(sources)
    if source_type == "inherit":
        return list(input_payloads or [])
    if source_type == "process":
        payloads = []
        for marker in sources:
            marker_index = _process_marker_index(marker)
            if marker_index is None or marker_index >= len(process_substitutions):
                continue
            payloads.extend(
                _literal_outputs_for_command(
                    process_substitutions[marker_index],
                    input_payloads,
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            )
        return payloads
    return []


def _process_script_payloads(
    tokens,
    process_substitutions,
    kubectl_exec=False,
    documents=None,
    input_payloads=None,
    depth=0,
):
    effective = _unwrap(tokens)
    if not effective:
        return None, False, []
    program = _basename(effective[0]).lower()
    args = effective[1:]
    if program == "kubectl":
        # Process-substitution paths are local file descriptors and are not
        # readable as script paths inside the remote container.
        return None, False, []
    if program in {"sh", "bash", "dash", "zsh", "ksh"}:
        if (
            _shell_noexec(args)
            or _shell_inline_payloads(args)
            or _shell_reads_stdin_code(args)
        ):
            return None, False, []
        value_options = {"-o", "+o", "-O", "+O", "--rcfile", "--init-file"}
        index = 0
        while index < len(args):
            arg = args[index]
            if arg in value_options:
                index += 2
                continue
            if arg.startswith(("-", "+")) and arg != "-":
                index += 1
                continue
            marker_index = _process_marker_index(arg)
            if marker_index is not None and marker_index < len(process_substitutions):
                return "shell", kubectl_exec, _literal_outputs_for_command(
                    process_substitutions[marker_index],
                    input_payloads,
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            fd_payloads = _fd_script_payloads(
                tokens,
                arg,
                process_substitutions,
                documents,
                input_payloads,
                depth,
            )
            return (
                ("shell", kubectl_exec, fd_payloads)
                if fd_payloads
                else (None, False, [])
            )
    if PYTHON_RE.match(program):
        if _python_inline_payloads(args) or _python_reads_stdin_code(args):
            return None, False, []
        index = 0
        while index < len(args):
            arg = args[index]
            if arg in {"-W", "-X"}:
                index += 2
                continue
            if arg == "-m" or arg.startswith("-m"):
                return None, False, []
            if arg.startswith("-") and arg != "-":
                index += 1
                continue
            marker_index = _process_marker_index(arg)
            if marker_index is not None and marker_index < len(process_substitutions):
                return "python", kubectl_exec, _literal_outputs_for_command(
                    process_substitutions[marker_index],
                    input_payloads,
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            fd_payloads = _fd_script_payloads(
                tokens,
                arg,
                process_substitutions,
                documents,
                input_payloads,
                depth,
            )
            return (
                ("python", kubectl_exec, fd_payloads)
                if fd_payloads
                else (None, False, [])
            )
    if program == "source" or effective[0] == ".":
        for arg in args:
            if arg.startswith("-"):
                continue
            marker_index = _process_marker_index(arg)
            if marker_index is not None and marker_index < len(process_substitutions):
                return "shell", kubectl_exec, _literal_outputs_for_command(
                    process_substitutions[marker_index],
                    input_payloads,
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            fd_payloads = _fd_script_payloads(
                tokens,
                arg,
                process_substitutions,
                documents,
                input_payloads,
                depth,
            )
            return (
                ("shell", kubectl_exec, fd_payloads)
                if fd_payloads
                else (None, False, [])
            )
    return None, False, []


def _process_output_commands(tokens, process_substitutions):
    effective = _unwrap(tokens)
    tee_output_operand = bool(effective) and _basename(effective[0]).lower() == "tee"

    def is_stdout_operator(operator_index):
        if operator_index > 0 and tokens[operator_index - 1].isdigit():
            return tokens[operator_index - 1] == "1"
        return True

    commands = []
    for index, token in enumerate(tokens):
        marker_match = re.fullmatch(r"__CATALOG_GUARD_PROCESS_OUTPUT_(\d+)__", token)
        if not marker_match:
            continue
        is_redirection_target = (
            index > 0 and tokens[index - 1] in {">", ">>", ">|"}
        )
        if not tee_output_operand and not is_redirection_target:
            continue
        if is_redirection_target:
            if not is_stdout_operator(index - 1):
                continue
            if any(
                later in {">", ">>", ">|"} and is_stdout_operator(later_index)
                for later_index, later in enumerate(tokens[index + 1 :], start=index + 1)
            ):
                continue
        process_index = int(marker_match.group(1))
        if process_index < len(process_substitutions):
            commands.append(process_substitutions[process_index])
    return commands


def _classify_with_literal_stdin(
    command, payloads, depth, inherited_documents=None
):
    if depth > MAX_RECURSION:
        return DEPTH_REASON
    command = _remove_line_continuations(command)
    cleaned, local_documents, _heredoc_malformed = _extract_heredocs(command)
    documents = dict(inherited_documents or {})
    documents.update(local_documents)
    masked, substitutions, process_substitutions, _malformed = _mask_substitutions(cleaned)
    segments, _segment_malformed = _split_segments(masked)
    try:
        tokenized = [
            (_shell_tokens(segment), connector) for segment, connector in segments
        ]
    except ValueError:
        return None
    pipeline_outputs = []
    remaining_payloads = list(payloads)
    for index, (tokens, connector) in enumerate(tokenized):
        pipeline_input = list(remaining_payloads)
        if connector in {"|", "|&"} and index > 0:
            pipeline_input = pipeline_outputs[index - 1]
        tokens = _expand_known_substitution_tokens(
            tokens,
            substitutions,
            documents,
            depth,
            input_payloads=pipeline_input,
        )
        stdin_source = _stdin_source_type(tokens, documents)
        if stdin_source == "process":
            incoming = _process_stdin_payloads(
                tokens, process_substitutions, documents, depth=depth
            )
        elif stdin_source == "payload":
            incoming = _payloads_for(tokens, documents)
        elif stdin_source == "file":
            incoming = []
        else:
            incoming = pipeline_input
        reason = _classify_tokens(tokens, documents, depth)
        if reason:
            return reason
        script_kind, script_kubectl, script_payloads = _process_script_payloads(
            tokens,
            process_substitutions,
            documents=documents,
            input_payloads=incoming,
            depth=depth,
        )
        for script_payload in script_payloads:
            if script_kind == "shell":
                reason = classify_command(
                    script_payload,
                    depth + 1,
                    kubectl_exec=script_kubectl,
                    inherited_documents=documents,
                )
            else:
                reason = _write_reason(
                    script_payload,
                    kubectl_exec=script_kubectl,
                    depth=depth + 1,
                )
            if reason:
                return reason
        for inline_command in _inline_shell_commands(tokens):
            reason = _classify_with_literal_stdin(
                inline_command,
                incoming,
                depth + 1,
                inherited_documents=documents,
            )
            if reason:
                return reason
        process_outputs = _known_stdout_payloads(
            tokens, documents, incoming, depth=depth
        )
        for process_command in _process_output_commands(tokens, process_substitutions):
            reason = _classify_with_literal_stdin(
                process_command,
                process_outputs,
                depth + 1,
                inherited_documents=documents,
            )
            if reason:
                return reason
        if incoming and any(_basename(token) == "xargs" for token in tokens):
            for payload in incoming:
                for invocation in _xargs_literal_invocations(tokens, payload):
                    reason = _classify_tokens(invocation, documents, depth + 1)
                    if reason:
                        return reason
        consumer = _stdin_payload_consumer(tokens, documents)
        if consumer:
            consumer_kind, consumer_kubectl = consumer
            for payload in incoming:
                if consumer_kind == "shell":
                    reason = classify_command(
                        payload,
                        depth + 1,
                        kubectl_exec=consumer_kubectl,
                        inherited_documents=documents,
                    )
                else:
                    reason = _write_reason(
                        payload,
                        kubectl_exec=consumer_kubectl,
                        depth=depth + 1,
                    )
                if reason:
                    return reason
        pipeline_outputs.append(
            _pipeline_output_payloads(
                tokens, documents, incoming, depth=depth
            )
        )
        if (
            connector not in {"|", "|&"}
            and incoming
            and (
                _consumes_inherited_stdin(tokens, documents, depth + 1)
                or _script_process_consumes_stdin(
                    tokens, process_substitutions, documents, depth + 1
                )
            )
        ):
            remaining_payloads = []
    return None


def _process_command_consumes_stdin(
    command, inherited_documents=None, depth=0
):
    if depth > MAX_RECURSION:
        raise ClassificationDepthError(DEPTH_REASON)
    cleaned, local_documents, _heredoc_malformed = _extract_heredocs(
        _remove_line_continuations(command)
    )
    documents = dict(inherited_documents or {})
    documents.update(local_documents)
    masked, substitutions, process_substitutions, _malformed = _mask_substitutions(cleaned)
    segments, _segment_malformed = _split_segments(masked)
    try:
        tokenized = [
            (
                _expand_known_substitution_tokens(
                    _shell_tokens(segment), substitutions, documents, depth
                ),
                connector,
            )
            for segment, connector in segments
        ]
    except ValueError:
        return False
    return any(
        connector not in {"|", "|&"}
        and (
            _consumes_inherited_stdin(segment_tokens, documents, depth + 1)
            or _script_process_consumes_stdin(
                segment_tokens,
                process_substitutions,
                documents,
                depth + 1,
            )
        )
        for segment_tokens, connector in tokenized
    )


def _script_process_consumes_stdin(
    tokens, process_substitutions, documents=None, depth=0
):
    for token in tokens:
        marker_index = _process_marker_index(token)
        if marker_index is None or marker_index >= len(process_substitutions):
            continue
        if _process_command_consumes_stdin(
            process_substitutions[marker_index], documents, depth + 1
        ):
            return True
    return False


def _process_stdin_payloads(
    tokens, process_substitutions, documents=None, depth=0
):
    source_type, markers = _stdin_state(tokens, documents or {})
    if source_type != "process":
        return []
    payloads = []
    for marker in markers:
        process_index = _process_marker_index(marker)
        if process_index is not None and process_index < len(process_substitutions):
            payloads.extend(
                _literal_outputs_for_command(
                    process_substitutions[process_index],
                    inherited_documents=documents,
                    depth=depth + 1,
                )
            )
    return payloads


def _consumes_inherited_stdin(tokens, documents, depth=0):
    if depth > MAX_RECURSION:
        raise ClassificationDepthError(DEPTH_REASON)
    if _stdin_source_type(tokens, documents) not in {"none", "inherit"}:
        return False
    effective = _unwrap(tokens)
    if not effective:
        return False
    program = _basename(effective[0]).lower()
    args = effective[1:]
    if program == "xargs":
        return True
    if program == "tee":
        return True
    if program == "cat":
        positionals = [arg for arg in args if arg == "-" or not arg.startswith("-")]
        return not positionals or "-" in positionals
    if (program == "source" or effective[0] == ".") and _source_reads_stdin(args):
        return True
    if program == "eval":
        return any(
            _process_command_consumes_stdin(command, documents, depth + 1)
            for command in ([" ".join(args)] if args else [])
        )
    if program in {"sh", "bash", "dash", "zsh", "ksh"}:
        inline_commands = _shell_inline_payloads(args)
        if inline_commands:
            return any(
                _process_command_consumes_stdin(
                    command, documents, depth + 1
                )
                for command in inline_commands
            )
        return _shell_reads_stdin_code(args)
    if PYTHON_RE.match(program):
        return not _python_inline_payloads(args) and _python_reads_stdin_code(args)
    return False


def _inline_shell_commands(tokens):
    effective = _unwrap(tokens)
    if not effective:
        return []
    if _basename(effective[0]).lower() == "kubectl":
        remote = _kubectl_remote(effective)
        remote_start = len(effective) - len(remote) if remote else len(effective)
        kubectl_args = effective[1:remote_start]
        forwards_stdin = any(
            token == "--stdin"
            or token.lower() in {"--stdin=true", "--stdin=1"}
            or token == "-i"
            or (token.startswith("-") and not token.startswith("--") and "i" in token[1:])
            for token in kubectl_args
        )
        if not forwards_stdin or not remote:
            return []
        effective = _unwrap(remote)
    if not effective:
        return []
    program = _basename(effective[0]).lower()
    if program == "eval":
        return [" ".join(effective[1:])] if len(effective) > 1 else []
    if program not in {"sh", "bash", "dash", "zsh", "ksh"}:
        return []
    return _shell_inline_payloads(effective[1:])


def _stdin_payload_consumer(tokens, documents):
    stdin_source = _stdin_source_type(tokens, documents)
    # xargs consumes pipeline input and turns it into argv; it does not forward
    # that input as stdin to its command template.
    if any(_basename(token) == "xargs" for token in tokens):
        return None
    tokens = _unwrap(tokens)
    if not tokens:
        return None
    program = _basename(tokens[0]).lower()
    args = tokens[1:]
    if stdin_source in {"payload", "file"}:
        return None
    if program == "kubectl":
        remote = _kubectl_remote(tokens)
        remote_start = len(tokens) - len(remote) if remote else len(tokens)
        kubectl_args = tokens[1:remote_start]
        forwards_stdin = any(
            token == "--stdin"
            or token.lower() in {"--stdin=true", "--stdin=1"}
            or token == "-i"
            or (token.startswith("-") and not token.startswith("--") and "i" in token[1:])
            for token in kubectl_args
        )
        if forwards_stdin and remote:
            nested = _stdin_payload_consumer(remote, documents)
            if nested:
                return nested[0], True
        return None
    if (program == "source" or tokens[0] == ".") and _source_reads_stdin(args):
        return "shell", False
    if program in {"sh", "bash", "dash", "zsh", "ksh"}:
        if _shell_noexec(args) or _shell_inline_payloads(args):
            return None
        if _shell_reads_stdin_code(args):
            return "shell", False
    if PYTHON_RE.match(program):
        if _python_inline_payloads(args):
            return None
        if _python_reads_stdin_code(args):
            return "python", False
    return None


def _kubectl_remote(tokens):
    global_options_with_values = {
        "--as", "--as-group", "--cache-dir", "--certificate-authority",
        "--client-certificate", "--client-key", "--cluster", "--context",
        "--kubeconfig", "--namespace", "-n", "--password", "--profile",
        "--request-timeout", "--server", "-s", "--tls-server-name", "--token",
        "--user", "--username", "-v", "--vmodule",
    }
    index = 1
    while index < len(tokens) and tokens[index].startswith("-"):
        option = tokens[index].split("=", 1)[0]
        index += 1
        if option in global_options_with_values and "=" not in tokens[index - 1] and index < len(tokens):
            index += 1
    if index >= len(tokens) or tokens[index].lower() != "exec":
        return []
    exec_index = index
    if "--" in tokens[exec_index + 1 :]:
        separator = tokens.index("--", exec_index + 1)
        return tokens[separator + 1 :]

    options_with_values = {
        "-c", "--container", "-n", "--namespace", "--context", "--cluster",
        "--user", "--request-timeout", "--pod-running-timeout",
    }
    index = exec_index + 1
    target_seen = False
    while index < len(tokens):
        token = tokens[index]
        if token.startswith("-"):
            option = token.split("=", 1)[0]
            index += 1
            if option in options_with_values and "=" not in token and index < len(tokens):
                index += 1
            continue
        if not target_seen:
            target_seen = True
            index += 1
            continue
        return tokens[index:]
    return []


def _classify_tokens(tokens, documents, depth, kubectl_exec=False):
    if depth > MAX_RECURSION:
        return DEPTH_REASON
    stdin_payloads = _payloads_for(tokens, documents)
    tokens = _unwrap(tokens)
    if not tokens:
        return None
    program = _basename(tokens[0]).lower()
    args = tokens[1:]

    if program == "aws":
        operands = _aws_copy_operands(args)
        if any(MANAGED_URI_RE.search(operand) for operand in operands):
            return OBJECT_COPY_REASON
    if program == "mc":
        operands = _mc_copy_operands(args)
        if any(MANAGED_URI_RE.search(operand) for operand in operands):
            return OBJECT_COPY_REASON

    if program == "kubectl":
        remote = _kubectl_remote(tokens)
        if remote:
            return _classify_tokens(remote, documents, depth + 1, kubectl_exec=True)
        return None

    heredoc_payloads = stdin_payloads

    if (program == "source" or tokens[0] == ".") and _source_reads_stdin(args):
        for payload in heredoc_payloads:
            reason = classify_command(
                payload,
                depth + 1,
                kubectl_exec=kubectl_exec,
                inherited_documents=documents,
            )
            if reason:
                return reason
        return None

    if PYTHON_RE.match(program):
        inline_payloads = _python_inline_payloads(args)
        payloads = inline_payloads
        if not inline_payloads and _python_reads_stdin_code(args):
            payloads = list(heredoc_payloads)
        for payload in payloads:
            reason = _write_reason(
                payload, kubectl_exec=kubectl_exec, depth=depth + 1
            )
            if reason:
                return reason
        return None

    if program in {"pyspark", "spark-submit", "spark-sql"}:
        payload = " ".join(args + heredoc_payloads)
        return _write_reason(
            payload, kubectl_exec=kubectl_exec, depth=depth + 1
        )

    if program == "eval":
        if not args:
            return None
        return classify_command(
            " ".join(args),
            depth + 1,
            kubectl_exec=kubectl_exec,
            inherited_documents=documents,
        )

    if program in {"sh", "bash", "dash", "zsh", "ksh"}:
        if _shell_noexec(args):
            return None
        inline_payloads = _shell_inline_payloads(args)
        payloads = inline_payloads
        if not inline_payloads and _shell_reads_stdin_code(args):
            payloads = list(heredoc_payloads)
        for payload in payloads:
            reason = classify_command(
                payload,
                depth + 1,
                kubectl_exec=kubectl_exec,
                inherited_documents=documents,
            )
            if reason:
                return reason
        return None

    return None


def classify_command(
    command, depth=0, kubectl_exec=False, inherited_documents=None
):
    if depth > MAX_RECURSION:
        return DEPTH_REASON

    command = _remove_line_continuations(command)
    cleaned, local_documents, heredoc_malformed = _extract_heredocs(command)
    documents = dict(inherited_documents or {})
    documents.update(local_documents)
    masked, substitutions, process_substitutions, substitution_malformed = _mask_substitutions(cleaned)

    expanded_heredoc_substitutions = []
    # Expand substitutions once when a heredoc is introduced. Inherited
    # documents remain available for marker lookup but must not recursively
    # re-enqueue the same substitution at every nested classification depth.
    for body, expands in local_documents.values():
        if not expands:
            continue
        _masked_body, body_substitutions, body_process_substitutions, body_malformed = _mask_substitutions(
            body,
            comments=False,
            shell_quotes=False,
            process_substitutions=False,
        )
        expanded_heredoc_substitutions.extend(body_substitutions)
        process_substitutions.extend(body_process_substitutions)
        substitution_malformed = substitution_malformed or body_malformed

    segments, segment_malformed = _split_segments(masked)
    tokenized = []
    try:
        for segment, incoming_connector in segments:
            tokenized.append((_shell_tokens(segment), incoming_connector))
    except ValueError:
        return None

    for payload in substitutions + expanded_heredoc_substitutions + process_substitutions:
        reason = classify_command(
            payload, depth + 1, inherited_documents=documents
        )
        if reason:
            return reason
    pipeline_outputs = []
    for index, (tokens, incoming_connector) in enumerate(tokenized):
        pipeline_payloads = []
        if incoming_connector in {"|", "|&"} and index > 0:
            pipeline_payloads = list(pipeline_outputs[index - 1])
        tokens = _expand_known_substitution_tokens(
            tokens,
            substitutions,
            documents,
            depth,
            input_payloads=pipeline_payloads,
        )
        stdin_source = _stdin_source_type(tokens, documents)
        if stdin_source == "process":
            incoming_payloads = _process_stdin_payloads(
                tokens, process_substitutions, documents, depth=depth
            )
        elif stdin_source == "payload":
            incoming_payloads = _payloads_for(tokens, documents)
        elif stdin_source == "file":
            incoming_payloads = []
        else:
            incoming_payloads = pipeline_payloads

        process_outputs = _known_stdout_payloads(
            tokens, documents, incoming_payloads, depth=depth
        )
        for process_command in _process_output_commands(tokens, process_substitutions):
            reason = _classify_with_literal_stdin(
                process_command,
                process_outputs,
                depth + 1,
                inherited_documents=documents,
            )
            if reason:
                return reason

        script_kind, script_kubectl, script_payloads = _process_script_payloads(
            tokens,
            process_substitutions,
            kubectl_exec=kubectl_exec,
            documents=documents,
            input_payloads=incoming_payloads,
            depth=depth,
        )
        for payload in script_payloads:
            if script_kind == "shell":
                reason = classify_command(
                    payload,
                    depth + 1,
                    kubectl_exec=script_kubectl,
                    inherited_documents=documents,
                )
            else:
                reason = _write_reason(
                    payload,
                    kubectl_exec=script_kubectl,
                    depth=depth + 1,
                )
            if reason:
                return reason

        reason = _classify_tokens(tokens, documents, depth, kubectl_exec=kubectl_exec)
        if reason:
            return reason
        for inline_command in _inline_shell_commands(tokens):
            reason = _classify_with_literal_stdin(
                inline_command,
                incoming_payloads,
                depth + 1,
                inherited_documents=documents,
            )
            if reason:
                return reason

        if incoming_payloads and any(_basename(token) == "xargs" for token in tokens):
            for payload in incoming_payloads:
                for invocation in _xargs_literal_invocations(tokens, payload):
                    reason = _classify_tokens(
                        invocation, documents, depth + 1, kubectl_exec=kubectl_exec
                    )
                    if reason:
                        return reason
        elif incoming_payloads:
            consumer = _stdin_payload_consumer(tokens, documents)
            if consumer:
                consumer_kind, remote_kubectl = consumer
                payload_is_kubectl = kubectl_exec or remote_kubectl
                for payload in incoming_payloads:
                    if consumer_kind == "shell":
                        reason = classify_command(
                            payload,
                            depth + 1,
                            kubectl_exec=payload_is_kubectl,
                            inherited_documents=documents,
                        )
                    else:
                        reason = _write_reason(
                            payload,
                            kubectl_exec=payload_is_kubectl,
                            depth=depth + 1,
                        )
                    if reason:
                        return reason

        pipeline_outputs.append(
            _pipeline_output_payloads(
                tokens, documents, incoming_payloads, depth=depth
            )
        )
    # Malformed tails are intentionally not guessed. Complete earlier segments
    # have already been classified above.
    _ = heredoc_malformed or substitution_malformed or segment_malformed
    return None


def main():
    command = sys.stdin.read()
    try:
        reason = classify_command(command)
    except ClassificationDepthError:
        reason = DEPTH_REASON
    if reason:
        print(reason)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
