#!/usr/bin/env python3
"""Resolve direct literal git commit message sources for ticket enforcement.

This helper is intentionally narrow. It accepts only a simple command beginning
with literal ``git commit`` and resolves ``-m`` plus file-backed ``-F`` /
``--file`` forms. Unsupported dispatch stays on the hook's legacy command-text
path; a recognized source that cannot be read fails closed.
"""

import argparse
import os
import shlex
import stat
import sys
from pathlib import Path

RESOLVED = 0
SOURCE_ERROR = 2
UNSUPPORTED = 3
MAX_MESSAGE_BYTES = 1024 * 1024
SHELL_OPERATORS = {";", "&&", "||", "|", "&", "(", ")", "<", ">", "<<", ">>"}


class MessageSourceError(Exception):
    """A recognized message source cannot be resolved safely."""


def command_tokens(command):
    """Tokenize a simple shell command without treating ticket hashes as comments."""
    if any(marker in command for marker in ("$", "`", "\\", "\n", "\r")):
        return None
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        tokens = list(lexer)
    except ValueError:
        return None
    if any(token in SHELL_OPERATORS for token in tokens):
        return None
    return tokens


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
    except OSError as exc:
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


def resolve(command, cwd):
    """Return the effective message, None for unsupported, or raise on source error."""
    tokens = command_tokens(command)
    if not tokens or tokens[:2] != ["git", "commit"]:
        return None

    messages = []
    file_source = None
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token == "-m":
            if index + 1 >= len(tokens):
                raise MessageSourceError("-m requires a message argument")
            messages.append(tokens[index + 1])
            index += 2
            continue
        if token.startswith("-m") and token != "-m":
            messages.append(token[2:])
            index += 1
            continue
        if token in {"-F", "--file"}:
            if index + 1 >= len(tokens):
                raise MessageSourceError(f"{token} requires a file argument")
            if file_source is not None:
                raise MessageSourceError("multiple file message sources are unsupported")
            file_source = tokens[index + 1]
            index += 2
            continue
        if token.startswith("-F") and token != "-F":
            if file_source is not None:
                raise MessageSourceError("multiple file message sources are unsupported")
            file_source = token[2:]
            index += 1
            continue
        if token.startswith("--file="):
            if file_source is not None:
                raise MessageSourceError("multiple file message sources are unsupported")
            file_source = token.split("=", 1)[1]
            index += 1
            continue
        index += 1

    if messages and file_source is not None:
        raise MessageSourceError("-m and -F/--file message sources cannot be combined")
    if messages:
        return "\n\n".join(messages)
    if file_source is not None:
        return read_message_file(file_source, cwd)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()
    command = sys.stdin.read()
    try:
        message = resolve(command, args.cwd)
    except MessageSourceError as exc:
        print(str(exc), file=sys.stderr)
        return SOURCE_ERROR
    if message is None:
        return UNSUPPORTED
    sys.stdout.write(message)
    return RESOLVED


if __name__ == "__main__":
    raise SystemExit(main())
