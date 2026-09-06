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
export PATH="/home/craftagents/bin:$PATH:/usr/local/bin:/opt/homebrew/bin"

INPUT=$(cat)

INPUT_JSON="$INPUT" python3 - <<'PY'
import json
import os
import re
import subprocess
import sys

try:
    payload = json.loads(os.environ.get("INPUT_JSON", ""))
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
working_directory = str(tool_input.get("workingDirectory") or os.getcwd())
labels = " ".join(map(str, tool_input.get("labels") or []))
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
worktree_declared = bool(re.search(r'\b(git worktree|worktree-isolated|worktree isolated|/worktrees?/|\.worktrees/)\b', haystack + "\n" + working_directory.lower()))
if write_like and not read_only_declared and not worktree_declared:
    try:
        inside_git = subprocess.run(
            ["git", "-C", working_directory, "rev-parse", "--is-inside-work-tree"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).stdout.strip() == "true"
    except Exception:
        inside_git = False
    if inside_git:
        errors.append("write-capable child sessions in a Git repo must use a git worktree or be declared read-only/no-file-edits")

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
    print("Required: explicit permissionMode=allow-all, model, thinkingLevel, enabledSourceSlugs,", file=sys.stderr)
    print("and a prompt/attachment that binds child sessions to RULES_BUNDLE/RESOLVER/session-coordination rules.", file=sys.stderr)
    print("Review/security/bypass sessions require high-or-higher reasoning and a strong reasoning-capable model.", file=sys.stderr)
    sys.exit(2)

sys.exit(0)
PY
