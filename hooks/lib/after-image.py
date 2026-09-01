#!/usr/bin/env python3
"""Print the content a PreToolUse write would leave on disk.

Usage: after-image.py {path|content}

Reads a PreToolUse payload on stdin. `path` prints the target file path;
`content` prints the post-write content of that file.

A guard that inspects the file on disk inspects the wrong document: an Edit
that introduces the first ticket reference into a clean artifact is judged
against the clean pre-image and allowed. Every write-shaped tool is therefore
resolved to the content it would produce, so one check covers all of them
rather than one patch per tool name.

Exit 0 on success. Exit 3 when the payload is a write whose after-image cannot
be determined, so callers can fail closed instead of treating an unknown tool
as an empty document.
"""

import json
import sys

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}


def target_path(ti: dict) -> str:
    for key in ("file_path", "path", "notebook_path"):
        value = ti.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def on_disk(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def apply_edit(text: str, edit: dict) -> str:
    old = edit.get("old_string", "")
    new = edit.get("new_string", "")
    if not isinstance(old, str) or not isinstance(new, str):
        raise ValueError("edit strings must be strings")
    if old == "":
        return text + new
    count = -1 if edit.get("replace_all") else 1
    return text.replace(old, new, count)


def after_image(tool: str, ti: dict, path: str) -> str:
    if tool == "Write":
        content = ti.get("content", "")
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        return content
    if tool == "Edit":
        return apply_edit(on_disk(path), ti)
    if tool == "MultiEdit":
        edits = ti.get("edits")
        if not isinstance(edits, list):
            raise ValueError("edits must be a list")
        text = on_disk(path)
        for edit in edits:
            if not isinstance(edit, dict):
                raise ValueError("each edit must be an object")
            text = apply_edit(text, edit)
        return text
    if tool == "NotebookEdit":
        # Cell semantics do not apply to a markdown artifact. Both halves are
        # returned so a reference in either the existing file or the incoming
        # source is seen.
        source = ti.get("new_source", "")
        if not isinstance(source, str):
            raise ValueError("new_source must be a string")
        return on_disk(path) + "\n" + source
    raise ValueError(f"unhandled write tool: {tool}")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in ("path", "content"):
        print(__doc__, file=sys.stderr)
        return 64
    try:
        payload = json.loads(sys.stdin.read())
    except (ValueError, TypeError):
        return 3
    if not isinstance(payload, dict):
        return 3
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input")
    if not isinstance(ti, dict):
        ti = {}
    path = target_path(ti)
    if sys.argv[1] == "path":
        sys.stdout.write(path)
        return 0
    if tool not in WRITE_TOOLS:
        return 3
    try:
        sys.stdout.write(after_image(tool, ti, path))
    except ValueError as exc:
        print(f"after-image: {exc}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
