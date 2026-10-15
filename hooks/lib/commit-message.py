#!/usr/bin/env python3
"""Resolve and validate the effective message for ``git commit`` guards.

This module never evaluates shell text. It accepts a deliberately bounded command
shape, resolves deterministic Git message sources, and fails closed when an editor,
opaque stdin, shell expansion, unsupported option, or unsafe file path prevents an
exact answer. Message files are confined to the target repository after symlink
resolution and are capped at 1 MiB.

CLI exit codes:
  0  message contains an accepted ticket/task reference
  1  deterministic message is missing a reference
  2  commit command/message cannot be inspected safely (fail closed)
  3  command is not a supported git commit invocation (caller should ignore it)
  4  message contains a prohibited bare [no-ticket] override
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import stat
import subprocess
import sys
from pathlib import Path
from typing import NoReturn, Optional, Sequence, Tuple

MAX_MESSAGE_BYTES = 1024 * 1024

VALID = 0
MISSING = 1
INDETERMINATE = 2
NOT_COMMIT = 3
INVALID_OVERRIDE = 4

STRUCTURED_OVERRIDE_RE = re.compile(
    r"\[no-ticket:\s+Reason:\s*[^;\s][^;]*;\s*"
    r"Evidence:\s*[^;\s][^;]*;\s*"
    r"Falsification:\s*[^]\s][^]]*\]",
    re.MULTILINE,
)
BARE_OVERRIDE_RE = re.compile(r"\[no-ticket\]|\[no-ticket:\s*\]")
TASK_RE = re.compile(r"\[task:\s+\S(?:[^]]*\S)?\]", re.MULTILINE)
TICKET_RE = re.compile(r"#[0-9]+|[A-Z]+-[0-9]+")
TRACKER_URL_RE = re.compile(
    r"https?://\S+/(?:issues|browse|tickets|merge_requests|pull|stories|tasks)/\S+"
)

NO_ARG_LONG = {
    "--all",
    "--patch",
    "--interactive",
    "--signoff",
    "--verbose",
    "--no-verify",
    "--dry-run",
    "--allow-empty",
    "--allow-empty-message",
    "--reset-author",
    "--no-post-rewrite",
    "--status",
    "--no-status",
    "--short",
    "--branch",
    "--porcelain",
    "--long",
    "--null",
    "--pathspec-file-nul",
    "--untracked-files",
    "--gpg-sign",
}
ARG_LONG = {
    "--author",
    "--date",
    "--pathspec-from-file",
}
NO_ARG_SHORT = set("apsvnieoq")
OPTIONAL_ATTACHED_SHORT = {"u", "S"}


class ResolutionError(Exception):
    pass


class NotCommit(Exception):
    pass


def die(message: str, code: int = INDETERMINATE) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def cleanup_stable_message(message: str, comment_char: str) -> str:
    """Remove content Git may discard under strip/scissors cleanup.

    Native commit-msg hooks run before final cleanup and cannot see the invoking
    command's --cleanup option. Validating only the cleanup-stable portion keeps
    the native layer from accepting a reference that can disappear afterward.
    """

    marker = f"{comment_char} ------------------------ >8 ------------------------"
    stable_lines = []
    for line in message.splitlines(keepends=True):
        if line.rstrip("\r\n") == marker:
            break
        if line.startswith(comment_char):
            continue
        stable_lines.append(line)
    return "".join(stable_lines)


def validate_message(message: str) -> int:
    # A prohibited bare marker remains prohibited even if a second, structured
    # marker appears elsewhere in the same message.
    if BARE_OVERRIDE_RE.search(message):
        return INVALID_OVERRIDE
    if STRUCTURED_OVERRIDE_RE.search(message):
        return VALID
    if TASK_RE.search(message):
        return VALID
    if TICKET_RE.search(message):
        return VALID
    if TRACKER_URL_RE.search(message):
        return VALID
    return MISSING


def remove_shell_comments(text: str) -> str:
    """Remove unquoted shell comments while preserving command-separating newlines."""

    result = []
    quote: Optional[str] = None
    escaped = False
    in_comment = False
    for index, char in enumerate(text):
        if in_comment:
            if char in {"\n", "\r"}:
                in_comment = False
                result.append(char)
            continue
        if escaped:
            result.append(char)
            escaped = False
            continue
        if quote == "'":
            result.append(char)
            if char == "'":
                quote = None
            continue
        if char == "\\":
            result.append(char)
            escaped = True
            continue
        if quote == '"':
            result.append(char)
            if char == '"':
                quote = None
            continue
        if char in {"'", '"'}:
            result.append(char)
            quote = char
            continue
        if char == "#" and (index == 0 or text[index - 1].isspace() or text[index - 1] in ";|&<>"):
            in_comment = True
            continue
        result.append(char)
    return "".join(result)


def unquoted_path_expansion(text: str) -> bool:
    quote: Optional[str] = None
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if quote == "'":
            if char == "'":
                quote = None
            continue
        if char == "\\":
            escaped = True
            continue
        if quote == '"':
            if char == '"':
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in {"~", "*", "?", "[", "{"}:
            return True
    return False


def unquoted_newline(text: str) -> bool:
    quote: Optional[str] = None
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if quote == "'":
            if char == "'":
                quote = None
            continue
        if char == "\\":
            escaped = True
            continue
        if quote == '"':
            if char == '"':
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char in {"\n", "\r"}:
            return True
    return False


def heredoc_operators(header: str) -> Sequence[Tuple[int, int, re.Match[str], int]]:
    """Find real, unquoted heredoc operators and their optional file descriptor."""

    found = []
    quote: Optional[str] = None
    escaped = False
    index = 0
    pattern = re.compile(r"<<(?P<tabs>-?)\s*(?P<quote>['\"])(?P<delimiter>[A-Za-z0-9_]+)(?P=quote)")
    while index < len(header):
        char = header[index]
        if escaped:
            escaped = False
            index += 1
            continue
        if quote == "'":
            if char == "'":
                quote = None
            index += 1
            continue
        if char == "\\":
            escaped = True
            index += 1
            continue
        if quote == '"':
            if char == '"':
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        if header.startswith("<<", index):
            match = pattern.match(header, index)
            if match is None:
                raise ResolutionError("stdin heredoc must use one quoted delimiter")
            fd_start = index
            while fd_start > 0 and header[fd_start - 1].isdigit():
                fd_start -= 1
            descriptor = header[fd_start:index]
            fd = int(descriptor) if descriptor else 0
            found.append((fd_start, match.end(), match, fd))
            index = match.end()
            continue
        index += 1
    return found


def split_quoted_heredoc(command: str) -> Tuple[str, Optional[str]]:
    """Return command header and literal stdin from one quoted heredoc.

    Only a quoted stdin delimiter is accepted because an unquoted heredoc performs
    shell expansion. Content after the delimiter is rejected so unrelated shell
    commands cannot affect classification.
    """

    first_newline = command.find("\n")
    raw_search_area = command if first_newline < 0 else command[:first_newline]
    search_area = remove_shell_comments(raw_search_area)
    matches = heredoc_operators(search_area)
    if not matches:
        return remove_shell_comments(command), None
    if len(matches) != 1 or first_newline < 0:
        raise ResolutionError("exactly one complete quoted heredoc is supported")

    start, end, match, descriptor = matches[0]
    if descriptor != 0:
        raise ResolutionError("message heredoc must redirect standard input (fd 0)")
    delimiter = match.group("delimiter")
    strip_tabs = match.group("tabs") == "-"
    header = search_area[:start] + search_area[end:]
    lines = command[first_newline + 1 :].splitlines(keepends=True)
    body_lines = []
    terminator_index = None
    for index, line in enumerate(lines):
        candidate = line.rstrip("\r\n")
        if strip_tabs:
            candidate = candidate.lstrip("\t")
        if candidate == delimiter:
            terminator_index = index
            break
        body_lines.append(line.lstrip("\t") if strip_tabs else line)
    if terminator_index is None:
        raise ResolutionError("quoted heredoc delimiter is missing")
    if any(line.strip() for line in lines[terminator_index + 1 :]):
        raise ResolutionError("commands after a message heredoc are unsupported")
    return header, "".join(body_lines)


def shell_tokens(command: str) -> Tuple[Sequence[str], Optional[str]]:
    header, heredoc = split_quoted_heredoc(command)
    if unquoted_newline(header):
        raise ResolutionError("newline-separated shell commands are unsupported")
    if unquoted_path_expansion(header):
        raise ResolutionError("unquoted shell pathname expansion is unsupported")
    # shlex does not retain quote context. Refuse expansion syntax rather than
    # accidentally validating the source spelling instead of the shell result.
    if "$" in header or "`" in header:
        raise ResolutionError("shell expansion in git commit commands is unsupported")
    try:
        lexer = shlex.shlex(header, posix=True, punctuation_chars=";&|<>()")
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError as exc:
        raise ResolutionError(f"cannot parse git commit command: {exc}") from exc
    return tokens, heredoc


def resolve_dir(base: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = base / candidate
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ResolutionError(f"working directory is unavailable: {value}") from exc
    if not resolved.is_dir():
        raise ResolutionError(f"working directory is not a directory: {value}")
    return resolved


def command_parts(command: str, cwd: Path) -> Tuple[Sequence[str], Optional[str], Path]:
    try:
        tokens, heredoc = shell_tokens(command)
    except ResolutionError:
        if re.search(r"(?:^|[^\w])git(?:\s|$).*?\bcommit(?:\s|$)", command, re.DOTALL):
            raise
        raise NotCommit

    controls = [i for i, token in enumerate(tokens) if token in {";", "&&", "&", "||", "|", "<", ">", "<<", ">>", "(", ")"}]
    effective_cwd = cwd
    if controls:
        if len(controls) != 1 or tokens[controls[0]] != "&&":
            if "git" in tokens and "commit" in tokens:
                raise ResolutionError("shell pipelines, redirects, and command chains are unsupported")
            raise NotCommit
        prefix, tokens = tokens[: controls[0]], tokens[controls[0] + 1 :]
        if len(prefix) == 2 and prefix[0] == "cd":
            if not Path(prefix[1]).is_absolute():
                raise ResolutionError("relative cd prefixes are unsupported because CDPATH can redirect them")
            effective_cwd = resolve_dir(cwd, prefix[1])
        elif len(prefix) == 3 and prefix[:2] == ["cd", "--"]:
            if not Path(prefix[2]).is_absolute():
                raise ResolutionError("relative cd prefixes are unsupported because CDPATH can redirect them")
            effective_cwd = resolve_dir(cwd, prefix[2])
        else:
            if "git" in tokens and "commit" in tokens:
                raise ResolutionError("only a literal 'cd <path> && git commit' prefix is supported")
            raise NotCommit

    if not tokens:
        raise NotCommit
    if Path(tokens[0]).name != "git":
        if "commit" in tokens and any(Path(token).name == "git" for token in tokens):
            raise ResolutionError("wrappers and environment prefixes around git commit are unsupported")
        raise NotCommit

    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "-C":
            if index + 1 >= len(tokens):
                raise ResolutionError("git -C requires a directory")
            effective_cwd = resolve_dir(effective_cwd, tokens[index + 1])
            index += 2
        elif token.startswith("-C") and token != "-C":
            effective_cwd = resolve_dir(effective_cwd, token[2:])
            index += 1
        elif token in {"--no-pager", "--paginate", "-p", "-P", "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs"}:
            index += 1
        else:
            break
    if index >= len(tokens) or tokens[index] != "commit":
        if "commit" in tokens[index:]:
            raise ResolutionError("unsupported git global options before commit")
        raise NotCommit
    return tokens[index + 1 :], heredoc, effective_cwd


def take_value(args: Sequence[str], index: int, option: str) -> Tuple[str, int]:
    if index + 1 >= len(args):
        raise ResolutionError(f"{option} requires a value")
    return args[index + 1], index + 2


def git_output(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise ResolutionError("repository state required for the commit message is unavailable") from exc
    return result.stdout


def git_config(cwd: Path, key: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "config", "--get", key],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )
    except (OSError, UnicodeError) as exc:
        raise ResolutionError("repository configuration cannot be inspected") from exc
    if result.returncode == 1:
        return ""
    if result.returncode != 0:
        raise ResolutionError("repository configuration cannot be inspected")
    return result.stdout.strip()


def repo_root(cwd: Path) -> Path:
    value = git_output(cwd, "rev-parse", "--show-toplevel").strip()
    try:
        return Path(value).resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ResolutionError("repository root cannot be resolved") from exc


def bounded_descriptor_text(descriptor: int) -> str:
    metadata = os.fstat(descriptor)
    if not stat.S_ISREG(metadata.st_mode):
        raise ResolutionError("commit message path is not a regular file")
    if not metadata.st_mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
        raise ResolutionError("commit message file has no read permission")
    if metadata.st_size > MAX_MESSAGE_BYTES:
        raise ResolutionError("commit message file exceeds the 1 MiB safety limit")
    with os.fdopen(descriptor, "rb", closefd=False) as stream:
        data = stream.read(MAX_MESSAGE_BYTES + 1)
    if len(data) > MAX_MESSAGE_BYTES:
        raise ResolutionError("commit message file exceeds the 1 MiB safety limit")
    return data.decode("utf-8")


def bounded_file_text(path: Path, *, no_follow: bool) -> str:
    flags = os.O_RDONLY
    if no_follow and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(str(path), flags)
    try:
        return bounded_descriptor_text(descriptor)
    finally:
        os.close(descriptor)


def bounded_repo_file_text(root: Path, relative: Path) -> str:
    """Open every path component relative to pinned descriptors without symlinks."""

    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | no_follow
    descriptors = [os.open(str(root), directory_flags)]
    try:
        for component in relative.parts[:-1]:
            descriptors.append(os.open(component, directory_flags, dir_fd=descriptors[-1]))
        file_descriptor = os.open(relative.parts[-1], os.O_RDONLY | no_follow, dir_fd=descriptors[-1])
        descriptors.append(file_descriptor)
        return bounded_descriptor_text(file_descriptor)
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def read_message_file(path_value: str, cwd: Path) -> str:
    root = repo_root(cwd)
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = cwd / candidate
    try:
        resolved = candidate.resolve(strict=True)
        relative = resolved.relative_to(root)
        if not relative.parts:
            raise ResolutionError("commit message path is not a regular file")
    except ValueError as exc:
        raise ResolutionError("commit message file resolves outside the repository") from exc
    except (OSError, RuntimeError) as exc:
        raise ResolutionError(f"commit message file is missing or unreadable: {path_value}") from exc
    try:
        return bounded_repo_file_text(root, relative)
    except ResolutionError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ResolutionError(f"commit message file is missing or unreadable: {path_value}") from exc


def read_commit_message(cwd: Path, revision: str) -> str:
    try:
        sha = git_output(cwd, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}").strip()
    except ResolutionError as exc:
        raise ResolutionError(f"commit message revision cannot be resolved: {revision}") from exc
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", sha):
        raise ResolutionError(f"commit message revision is invalid: {revision}")
    try:
        process = subprocess.Popen(
            ["git", "-C", str(cwd), "show", "-s", "--format=%B", sha],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        assert process.stdout is not None
        data = process.stdout.read(MAX_MESSAGE_BYTES + 1)
        if len(data) > MAX_MESSAGE_BYTES:
            process.kill()
            process.wait()
            raise ResolutionError("reused commit message exceeds the 1 MiB safety limit")
        return_code = process.wait()
        if return_code != 0:
            raise ResolutionError("repository state required for the commit message is unavailable")
        return data.decode("utf-8")
    except ResolutionError:
        raise
    except (OSError, UnicodeError) as exc:
        raise ResolutionError("repository state required for the commit message is unavailable") from exc


def resolve_message(command: str, cwd_value: str) -> str:
    cwd = resolve_dir(Path.cwd(), cwd_value)
    args, heredoc, effective_cwd = command_parts(command, cwd)

    messages = []
    files = []
    reuse = []
    reedit = []
    templates = []
    amend = False
    edit_flag: Optional[bool] = None
    unsupported_message_mutator = None
    cleanup_modes = []
    positional = False

    index = 0
    while index < len(args):
        token = args[index]
        if positional:
            index += 1
            continue
        if token == "--":
            positional = True
            index += 1
            continue

        long_sources = {
            "--message": messages,
            "--file": files,
            "--reuse-message": reuse,
            "--reedit-message": reedit,
            "--template": templates,
        }
        matched = False
        for option, target in long_sources.items():
            if token == option:
                value, index = take_value(args, index, option)
                target.append(value)
                matched = True
                break
            if token.startswith(option + "="):
                target.append(token.split("=", 1)[1])
                index += 1
                matched = True
                break
        if matched:
            continue

        if token == "--amend":
            amend = True
            index += 1
        elif token == "--cleanup":
            value, index = take_value(args, index, token)
            cleanup_modes.append(value)
        elif token.startswith("--cleanup="):
            cleanup_modes.append(token.split("=", 1)[1])
            index += 1
        elif token in {"--edit"}:
            edit_flag = True
            index += 1
        elif token in {"--no-edit"}:
            edit_flag = False
            index += 1
        elif token in {"--fixup", "--squash", "--trailer"} or any(
            token.startswith(option + "=") for option in ("--fixup", "--squash", "--trailer")
        ):
            unsupported_message_mutator = token.split("=", 1)[0]
            if "=" in token:
                index += 1
            else:
                _, index = take_value(args, index, token)
        elif token in NO_ARG_LONG:
            index += 1
        elif token.split("=", 1)[0] in ARG_LONG:
            if "=" in token:
                index += 1
            else:
                _, index = take_value(args, index, token)
        elif token.startswith("--untracked-files=") or token.startswith("--gpg-sign="):
            index += 1
        elif token.startswith("--"):
            raise ResolutionError(f"unsupported git commit option: {token}")
        elif token.startswith("-") and token != "-":
            cluster = token[1:]
            cursor = 0
            index += 1
            while cursor < len(cluster):
                option = cluster[cursor]
                cursor += 1
                if option in {"m", "F", "C", "c", "t"}:
                    if cursor < len(cluster):
                        value = cluster[cursor:]
                        cursor = len(cluster)
                    else:
                        if index >= len(args):
                            raise ResolutionError(f"-{option} requires a value")
                        value = args[index]
                        index += 1
                    {"m": messages, "F": files, "C": reuse, "c": reedit, "t": templates}[option].append(value)
                elif option == "e":
                    edit_flag = True
                elif option in NO_ARG_SHORT:
                    continue
                elif option in OPTIONAL_ATTACHED_SHORT:
                    # Git's -u[<mode>] and -S[<keyid>] optional values must be
                    # attached to the same argv token. A following -m/-F remains
                    # a separate option and must never be consumed as their value.
                    if cursor < len(cluster):
                        cursor = len(cluster)
                else:
                    raise ResolutionError(f"unsupported git commit option: -{option}")
        else:
            index += 1

    if unsupported_message_mutator:
        raise ResolutionError(f"{unsupported_message_mutator} changes the message in a configuration-dependent way")
    cleanup_mode = cleanup_modes[-1] if cleanup_modes else git_config(effective_cwd, "commit.cleanup")
    if cleanup_mode and cleanup_mode not in {"default", "whitespace", "verbatim"}:
        source = "--cleanup" if cleanup_modes else "configured commit.cleanup"
        raise ResolutionError(f"{source}={cleanup_mode} can remove validated message content")
    source_count = sum(bool(values) for values in (messages, files, reuse, reedit))
    if source_count > 1 or (reuse and reedit):
        raise ResolutionError("conflicting git commit message sources")

    if messages:
        message = "\n\n".join(messages)
        default_edit = False
    elif files:
        selected = files[-1]
        if selected == "-":
            if heredoc is None:
                raise ResolutionError("git commit -F - requires a literal quoted heredoc")
            message = heredoc
        else:
            message = read_message_file(selected, effective_cwd)
        default_edit = False
    elif reuse:
        message = read_commit_message(effective_cwd, reuse[-1])
        default_edit = False
    elif reedit:
        message = read_commit_message(effective_cwd, reedit[-1])
        default_edit = True
    elif amend and edit_flag is False:
        message = read_commit_message(effective_cwd, "HEAD")
        default_edit = False
    else:
        if templates:
            raise ResolutionError("template-based commit message still requires an editor")
        raise ResolutionError("commit message requires an editor or unsupported repository state")

    will_edit = default_edit if edit_flag is None else edit_flag
    if will_edit:
        raise ResolutionError("commit message may be changed by an editor")
    if heredoc is not None and not (files and files[-1] == "-"):
        raise ResolutionError("message heredoc is not the selected commit message source")
    if len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ResolutionError("effective commit message exceeds the 1 MiB safety limit")
    return message


def check_command(cwd: str) -> int:
    command = sys.stdin.read(MAX_MESSAGE_BYTES + 1)
    if len(command.encode("utf-8")) > MAX_MESSAGE_BYTES:
        print("git commit command exceeds the 1 MiB safety limit", file=sys.stderr)
        return INDETERMINATE
    try:
        message = resolve_message(command, cwd)
    except NotCommit:
        return NOT_COMMIT
    except ResolutionError as exc:
        print(str(exc), file=sys.stderr)
        return INDETERMINATE
    return validate_message(message)


def check_message_file(path: str) -> int:
    try:
        message = bounded_file_text(Path(path), no_follow=False)
        comment_char = git_config(Path.cwd(), "core.commentChar") or "#"
        if comment_char == "auto":
            comment_char = "#"
        if len(comment_char) != 1 or comment_char.isalnum() or comment_char.isspace():
            raise ResolutionError("repository core.commentChar is unsupported")
        message = cleanup_stable_message(message, comment_char)
    except (OSError, UnicodeError, ResolutionError) as exc:
        print(f"commit message cannot be read safely: {exc}", file=sys.stderr)
        return INDETERMINATE
    return validate_message(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode", required=True)
    command_parser = subparsers.add_parser("check-command")
    command_parser.add_argument("--cwd", required=True)
    file_parser = subparsers.add_parser("check-message-file")
    file_parser.add_argument("path")
    args = parser.parse_args()
    if args.mode == "check-command":
        return check_command(args.cwd)
    return check_message_file(args.path)


if __name__ == "__main__":
    raise SystemExit(main())
