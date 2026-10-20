#!/usr/bin/env python3
"""Resolve direct literal git commit message sources for ticket enforcement.

This helper accepts simple commands beginning with literal ``git commit`` and
models explicit message options. Other dispatch shapes stay on the hook's
legacy command-text path. A direct commit whose effective message cannot be
modeled fails closed.
"""

import argparse
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path

RESOLVED = 0
SOURCE_ERROR = 2
UNSUPPORTED = 3
MAX_MESSAGE_BYTES = 1024 * 1024
CONFIG_TIMEOUT_SECONDS = 2
SHELL_OPERATOR_CHARS = frozenset(";&|()<>")
DIRECT_COMMIT_RE = re.compile(r"^\s*git[ \t]+commit(?:[ \t\r\n]|$)")
HEREDOC_RE = re.compile(
    r'"\$\(cat[ \t]+<<(?P<quote>[\'\"])(?P<delimiter>[A-Za-z_][A-Za-z0-9_]*)'
    r'(?P=quote)\n(?P<body>.*?)\n(?P=delimiter)\n?\)"',
    re.DOTALL,
)
SCISSORS_LINE = "# ------------------------ >8 ------------------------"

LONG_OPTIONS = frozenset(
    {
        "ahead-behind",
        "all",
        "allow-empty",
        "allow-empty-message",
        "amend",
        "author",
        "branch",
        "cleanup",
        "date",
        "dry-run",
        "edit",
        "file",
        "fixup",
        "gpg-sign",
        "include",
        "inter-hunk-context",
        "interactive",
        "long",
        "message",
        "no-post-rewrite",
        "no-verify",
        "null",
        "only",
        "patch",
        "pathspec-file-nul",
        "pathspec-from-file",
        "porcelain",
        "post-rewrite",
        "quiet",
        "reedit-message",
        "reset-author",
        "reuse-message",
        "short",
        "signoff",
        "squash",
        "status",
        "template",
        "trailer",
        "unified",
        "untracked-files",
        "verbose",
        "verify",
    }
)
LONG_REQUIRED_VALUES = frozenset(
    {
        "author",
        "cleanup",
        "date",
        "file",
        "fixup",
        "inter-hunk-context",
        "message",
        "pathspec-from-file",
        "reedit-message",
        "reuse-message",
        "squash",
        "template",
        "trailer",
        "unified",
    }
)
UNMODELED_MESSAGE_OPTIONS = frozenset(
    {"fixup", "reedit-message", "reuse-message", "squash", "template"}
)
SHORT_FLAGS = frozenset("aqvseionpz")


class MessageSourceError(Exception):
    """A direct commit message cannot be resolved safely."""


def extract_heredocs(command):
    """Replace the canonical quoted-delimiter cat substitution with tokens."""
    values = {}

    def replace(match):
        index = len(values)
        placeholder = f"__CCP_LITERAL_HEREDOC_{index}__"
        while placeholder in command or placeholder in values:
            index += 1
            placeholder = f"__CCP_LITERAL_HEREDOC_{index}__"
        values[placeholder] = match.group("body").rstrip("\n")
        return placeholder

    return HEREDOC_RE.sub(replace, command), values


def strip_comment_and_check_syntax(command):
    """Strip a Bash word-start comment and reject unmodeled shell syntax."""
    quote = None
    word_start = True
    result = []
    index = 0
    while index < len(command):
        char = command[index]
        if quote == "'":
            result.append(char)
            if char == "'":
                quote = None
            index += 1
            continue
        if quote == '"':
            if char == '"':
                quote = None
                result.append(char)
                index += 1
                continue
            if char in {"$", "`", "\\"}:
                raise MessageSourceError("double-quoted expansion or escape is outside the narrow message model")
            result.append(char)
            index += 1
            continue

        if char in {"'", '"'}:
            quote = char
            word_start = False
            result.append(char)
            index += 1
            continue
        if char == "#" and word_start:
            break
        if char in SHELL_OPERATOR_CHARS or char in {"\n", "\r"}:
            raise MessageSourceError("compound shell syntax is outside the narrow message model")
        if char in {"$", "`", "\\"}:
            raise MessageSourceError("shell expansion or escape is outside the narrow message model")
        result.append(char)
        word_start = char.isspace()
        index += 1
    return "".join(result)


def command_tokens(command):
    """Tokenize a direct command while preserving approved literal heredocs."""
    if not DIRECT_COMMIT_RE.match(command):
        return None, {}
    replaced, heredocs = extract_heredocs(command)
    cleaned = strip_comment_and_check_syntax(replaced)
    try:
        lexer = shlex.shlex(cleaned, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:  # noqa: writing-tests-5 handler exercised by ticket_required.test.sh
        raise MessageSourceError(f"commit command cannot be parsed safely: {exc}") from exc
    if tokens[:2] != ["git", "commit"]:
        raise MessageSourceError("literal git commit prefix changed during parsing")
    return tokens, heredocs


def restore_literal(value, heredocs):
    """Restore a canonical heredoc body after shell tokenization."""
    return heredocs.get(value, value)


def read_message_file(raw_path, cwd):
    """Read one bounded regular file relative to the tool payload's cwd."""
    if raw_path == "-":
        raise MessageSourceError("stdin message source (-F -) is outside the narrow #994 scope")
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path(cwd) / path
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:  # noqa: writing-tests-5 handler exercised by ticket_required.test.sh
        raise MessageSourceError(f"message file is not readable: {raw_path}: {exc.strerror}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise MessageSourceError(f"message source is not a regular file: {raw_path}")
        if info.st_mode & 0o444 == 0:
            raise MessageSourceError(f"message file is not readable: {raw_path}: no read permission")
        if info.st_size > MAX_MESSAGE_BYTES:
            raise MessageSourceError(f"message file exceeds {MAX_MESSAGE_BYTES} bytes: {raw_path}")
        with os.fdopen(fd, "rb", closefd=True) as stream:
            fd = -1
            data = stream.read(MAX_MESSAGE_BYTES + 1)
    finally:
        if fd >= 0:
            os.close(fd)
    if len(data) > MAX_MESSAGE_BYTES:
        raise MessageSourceError(f"message file exceeds {MAX_MESSAGE_BYTES} bytes: {raw_path}")
    return data.decode("utf-8", errors="replace")


def resolve_long_option(raw_name):
    """Resolve a full or unambiguous Git long-option prefix."""
    negated = raw_name.startswith("no-")
    prefix = raw_name[3:] if negated else raw_name
    if prefix in LONG_OPTIONS:
        return prefix, negated
    matches = sorted(name for name in LONG_OPTIONS if name.startswith(prefix))
    if len(matches) != 1:
        reason = "unknown" if not matches else "ambiguous"
        raise MessageSourceError(f"{reason} git commit option: --{raw_name}")
    return matches[0], negated


def take_value(tokens, index, option, attached):
    """Return a required option value and the next token index."""
    if attached is not None:
        return attached, index + 1
    if index + 1 >= len(tokens):
        raise MessageSourceError(f"{option} requires a value")
    return tokens[index + 1], index + 2


def add_file_source(state, value):
    if state["file"] is not None:
        raise MessageSourceError("multiple file message sources are unsupported")
    state["file"] = value


def add_trailer(state, value):
    if not re.match(r"^[^:=\n]+[:=][ \t]*\S", value):
        raise MessageSourceError("trailer value cannot be modeled safely")
    state["trailers"].append(value)


def apply_long_option(tokens, index, state, heredocs):
    token = tokens[index]
    name_text, separator, attached = token[2:].partition("=")
    attached_value = attached if separator else None
    name, negated = resolve_long_option(name_text)
    if negated:
        if attached_value is not None or name in LONG_REQUIRED_VALUES:
            raise MessageSourceError(f"negated value option cannot be modeled safely: --{name_text}")
        return index + 1
    if name in LONG_REQUIRED_VALUES:
        value, next_index = take_value(tokens, index, f"--{name_text}", attached_value)
        value = restore_literal(value, heredocs)
        if name == "message":
            state["messages"].append(value)
        elif name == "file":
            add_file_source(state, value)
        elif name == "trailer":
            add_trailer(state, value)
        elif name == "cleanup":
            state["cleanup"] = value
        elif name in UNMODELED_MESSAGE_OPTIONS:
            raise MessageSourceError(f"--{name} supplies a message this helper cannot model")
        return next_index
    if attached_value is not None and name not in {"gpg-sign", "untracked-files"}:
        raise MessageSourceError(f"--{name_text} does not accept a value")
    return index + 1


def take_short_value(tokens, index, cluster, position, option):
    attached = cluster[position + 1 :]
    if attached:
        return attached, index + 1
    if index + 1 >= len(tokens):
        raise MessageSourceError(f"-{option} requires a value")
    return tokens[index + 1], index + 2


def apply_short_options(tokens, index, state, heredocs):
    cluster = tokens[index][1:]
    if not cluster:
        raise MessageSourceError("bare '-' cannot be modeled as a commit option")
    position = 0
    while position < len(cluster):
        option = cluster[position]
        if option in SHORT_FLAGS:
            position += 1
            continue
        if option in {"m", "F", "c", "C", "t", "U"}:
            if option == "F" and position != 0:
                raise MessageSourceError("clustered -F is outside the narrow #994 scope")
            value, next_index = take_short_value(tokens, index, cluster, position, option)
            value = restore_literal(value, heredocs)
            if option == "m":
                state["messages"].append(value)
            elif option == "F":
                add_file_source(state, value)
            elif option in {"c", "C", "t"}:
                raise MessageSourceError(f"-{option} supplies a message this helper cannot model")
            return next_index
        if option in {"S", "u"}:
            return index + 1
        raise MessageSourceError(f"unknown git commit short option: -{option}")
    return index + 1


def configured_cleanup(cwd):
    """Read commit.cleanup without invoking a shell."""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "config", "--get", "commit.cleanup"],
            capture_output=True,
            text=True,
            timeout=CONFIG_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # noqa: writing-tests-5 handler exercised by ticket_required.test.sh
        raise MessageSourceError(f"commit.cleanup cannot be read safely: {exc}") from exc
    if result.returncode == 1:
        return "whitespace"
    if result.returncode != 0:
        raise MessageSourceError("commit.cleanup cannot be read safely")
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return values[-1] if values else "whitespace"


def strip_space(lines):
    """Apply Git's relevant trailing/blank-line cleanup for ticket matching."""
    cleaned = [line.rstrip() for line in lines]
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    collapsed = []
    for line in cleaned:
        if line or not collapsed or collapsed[-1]:
            collapsed.append(line)
    return collapsed


def cleanup_message(message, mode):
    """Apply cleanup modes that can remove ticket-bearing lines."""
    normalized = (mode or "whitespace").strip().lower()
    if normalized == "default":
        normalized = "whitespace"
    if normalized not in {"strip", "whitespace", "verbatim", "scissors"}:
        raise MessageSourceError(f"unsupported commit cleanup mode: {mode}")
    if normalized == "verbatim":
        return message
    lines = message.splitlines()
    if normalized == "scissors":
        lines = lines[: next((i for i, line in enumerate(lines) if line == SCISSORS_LINE), len(lines))]
    if normalized == "strip":
        lines = [line for line in lines if not line.startswith("#")]
    return "\n".join(strip_space(lines))


def resolve(command, cwd):
    """Return the effective message, None for non-direct dispatch, or raise."""
    tokens, heredocs = command_tokens(command)
    if tokens is None:
        return None

    state = {"messages": [], "file": None, "trailers": [], "cleanup": None}
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--"):
            index = apply_long_option(tokens, index, state, heredocs)
            continue
        if token.startswith("-"):
            index = apply_short_options(tokens, index, state, heredocs)
            continue
        index += 1

    if state["messages"] and state["file"] is not None:
        raise MessageSourceError("-m/--message and -F/--file message sources cannot be combined")
    if state["messages"]:
        message = "\n\n".join(state["messages"])
    elif state["file"] is not None:
        message = read_message_file(state["file"], cwd)
    else:
        raise MessageSourceError("direct git commit has no modeled message source")

    mode = state["cleanup"] if state["cleanup"] is not None else configured_cleanup(cwd)
    message = cleanup_message(message, mode)
    if state["trailers"]:
        suffix = "\n".join(state["trailers"])
        message = f"{message}\n\n{suffix}" if message else suffix
    return message


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()
    command = sys.stdin.read()
    try:
        message = resolve(command, args.cwd)
    except MessageSourceError as exc:  # noqa: writing-tests-5 handler exercised by ticket_required.test.sh
        print(str(exc), file=sys.stderr)
        return SOURCE_ERROR
    if message is None:
        return UNSUPPORTED
    sys.stdout.write(message)
    return RESOLVED


if __name__ == "__main__":
    raise SystemExit(main())
