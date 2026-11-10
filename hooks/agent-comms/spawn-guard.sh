#!/usr/bin/env bash
# Hook: spawn-guard
# Enforces: RESOLVER.md spawn-protocol and session-coordination spawn discipline.
# Trigger: PreToolUse on mcp__session__spawn_session
#
# Blocks child-session spawns that rely on inherited defaults or omit the rule
# bundle/prompt contract needed to bind non-Claude runtimes in prose. This is a
# parent-side guard: it fires before an unhooked child runtime exists.
#
# Ref: claude-configs-public#609

set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"
export PATH="$PATH:/usr/local/bin:/opt/homebrew/bin"

INPUT=$(cat)

python3 - 3<<<"$INPUT" <<'PY'
import json
import os
import re
import stat
import subprocess
import sys

try:
    with os.fdopen(3, "rb") as stream:
        payload = json.load(stream)
except Exception:
    sys.exit(0)

tool_input = payload.get("tool_input") or {}
if tool_input.get("help") is True:
    sys.exit(0)

prompt = str(tool_input.get("prompt") or "")
name = str(tool_input.get("name") or "")
model = str(tool_input.get("model") or "")
permission = str(tool_input.get("permissionMode") or "")
thinking = str(tool_input.get("thinkingLevel") or "")
parent_directory = payload.get("cwd") or os.getcwd()
if not isinstance(parent_directory, str):
    parent_directory = os.getcwd()
raw_working_directory = tool_input.get("workingDirectory")
literal_absolute_directory = (
    isinstance(raw_working_directory, str)
    and os.path.isabs(raw_working_directory)
    and not re.search(r"\$\{HOME\}|\$HOME(?=/|$)", raw_working_directory)
)
# The host lexically normalizes before the OS follows symlinks. Do the same.
working_directory = os.path.realpath(os.path.normpath(raw_working_directory)) if literal_absolute_directory else None
labels_key_present = "labels" in tool_input
raw_labels = tool_input.get("labels")
valid_labels = (
    isinstance(raw_labels, list)
    and bool(raw_labels)
    and all(isinstance(label, str) and label.strip() for label in raw_labels)
)
labels = " ".join(raw_labels) if valid_labels else ""
attachments = tool_input.get("attachments") or []
source_key_present = "enabledSourceSlugs" in tool_input
sources = tool_input.get("enabledSourceSlugs")

haystack = "\n".join([prompt, name, labels]).lower()
attachment_text = "\n".join(
    str(item.get("path") or item.get("name") or item) if isinstance(item, dict) else str(item)
    for item in attachments
).lower()

errors = []

if permission != "allow-all":
    errors.append("permissionMode must be explicit allow-all for spawned sessions that may act or reply")

if not labels_key_present or not valid_labels:
    errors.append("labels must be an explicit nonempty array of nonempty role-label strings; never inherit parent identity")

if not model:
    errors.append("model must be explicit; do not rely on inherited defaults")

review_like = bool(re.search(r'\b(review|hostile|security|bypass|regression|audit|approve|request_changes)\b', haystack))
if review_like:
    if thinking not in {"high", "xhigh", "max"}:
        errors.append("review/security/bypass sessions require thinkingLevel high, xhigh, or max")
    if re.search(r'\b(mini|haiku|flash|lite|gpt-4o)\b', model.lower()):
        errors.append("review/security/bypass sessions must not use non-reasoning or weak models when stronger reasoning-capable models are available")
elif not thinking:
    errors.append("thinkingLevel must be explicit, even if set to off for simple non-review work")

if not source_key_present:
    errors.append("enabledSourceSlugs must be explicit; use [] only when no external sources are needed")

rules_bound = any(token in haystack or token in attachment_text for token in [
    "rules_bundle", "rules bundle", "resolver.md", "spawn-protocol", "session-coordination"
])
if not rules_bound:
    errors.append("prompt/attachments must carry RULES_BUNDLE/RESOLVER/session-coordination rules for the child runtime")

write_like = bool(re.search(r'\b(implement|fix|edit|write|commit|push|pr|pull request|modify|change files)\b', haystack))
read_only_declared = bool(re.search(r'\b(do not modify|no file edits|read-only|passive analysis|reviewer, not an implementer)\b', haystack))
def git_workspace(directory):
    """Read actual Git ownership, never infer isolation from words or paths."""
    # This gate is scoped to actual Git workspaces. Plain existing directories
    # need no Git executable or metadata service to retain their normal route.
    current = os.path.realpath(directory)
    while not os.path.lexists(os.path.join(current, ".git")):
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent
    env = dict(os.environ, LC_ALL="C", GIT_OPTIONAL_LOCKS="0")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)

    def query(*args):
        return subprocess.run(
            ["git", "-C", directory, "rev-parse", *args],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=2, env=env,
        )

    inside = query("--is-inside-work-tree")
    if inside.returncode:
        raise ValueError("Git workspace metadata could not be read")
    if inside.stdout.strip() != "true":
        raise ValueError("target is not a Git working tree")
    values = []
    for option in ("--show-toplevel", "--absolute-git-dir", "--git-common-dir"):
        result = query(option)
        if result.returncode or not result.stdout:
            raise ValueError("Git worktree ownership could not be resolved")
        values.append(os.path.realpath(os.path.join(directory, result.stdout.rstrip("\n"))))
    return tuple(values)


if write_like and not read_only_declared:
    try:
        if working_directory is None:
            raise ValueError("write-capable child requires an explicit absolute workingDirectory; pass the actual existing path instead of relative, tilde, unexpanded HOME, or inherited defaults")
        if not os.path.exists(working_directory):
            raise ValueError("workingDirectory does not exist; prepare it before spawning the writer")
        if not os.path.isdir(working_directory):
            raise ValueError("workingDirectory is not a directory")
        target = git_workspace(working_directory)
        if target is not None:
            root, git_dir, common_dir = target
            if git_dir == common_dir:
                raise ValueError("workingDirectory is a primary Git checkout, not an isolated linked worktree")
            # Git's per-worktree backpointer binds this admin directory to its
            # registered root. Copying a .git pointer elsewhere proves nothing.
            descriptor = os.open(os.path.join(git_dir, "gitdir"), os.O_RDONLY | os.O_NONBLOCK)
            try:
                metadata = os.fstat(descriptor)
                if not stat.S_ISREG(metadata.st_mode) or not 0 < metadata.st_size <= 4096:
                    raise ValueError("registered worktree backpointer must be a small regular file")
                pointer = os.read(descriptor, 4097)
                if not pointer or len(pointer) > 4096:
                    raise ValueError("registered worktree backpointer is empty or oversized")
            finally:
                os.close(descriptor)
            registered = os.path.realpath(os.path.join(git_dir, os.fsdecode(pointer).rstrip("\n")))
            if registered != os.path.realpath(os.path.join(root, ".git")) or os.path.commonpath([working_directory, root]) != root:
                raise ValueError("workingDirectory does not match the registered Git worktree root")
            parent = git_workspace(os.path.realpath(parent_directory))
            if parent is not None and parent[0] == root:
                raise ValueError("child workingDirectory reuses the parent's Git worktree")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        errors.append(str(error) + "; prepare a separate registered Git worktree and pass its workingDirectory before spawning, or keep an explicitly read-only assignment")

if re.search(r'\bsend_agent_message\b|\bset_session_status\b|\breply back\b|\breturn findings\b', haystack):
    if "send_agent_message" not in haystack:
        errors.append("sessions expected to communicate back must name send_agent_message in the prompt")
    if "set_session_status" not in haystack and "status" not in haystack:
        errors.append("sessions expected to communicate back must include a status-setting requirement")

if errors:
    print("BLOCKED: spawn_session call violates spawn-protocol.", file=sys.stderr)
    print("", file=sys.stderr)
    for err in errors:
        print(f"  - {err}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Required: explicit permissionMode=allow-all, nonempty role labels, model, thinkingLevel, enabledSourceSlugs,", file=sys.stderr)
    print("and a prompt/attachment that binds child sessions to RULES_BUNDLE/RESOLVER/session-coordination rules.", file=sys.stderr)
    print("Review/security/bypass sessions require high-or-higher reasoning and a strong reasoning-capable model.", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
PY
