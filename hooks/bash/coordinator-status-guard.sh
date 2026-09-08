#!/usr/bin/env bash
# Hook: coordinator-status-guard
# Enforces: coordinator lane/status transitions must carry evidence.
# Trigger: PreToolUse on Bash commands that update GitHub issues/PRs.
#
# Blocks coordinator-style completion/status comments and issue closes when
# owner signoff, merge/branch, and rollout evidence are absent, or when
# unresolved blockers are mentioned in the same completion claim.
#
# Ref: claude-configs-public#609

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

python3 - "$COMMAND" <<'PY'
import re
import shlex
import sys
from pathlib import Path

command = sys.argv[1]
normalized_command = command.replace("$(which gh)", "gh")

try:
    tokens = shlex.split(normalized_command)
except ValueError:
    tokens = normalized_command.split()

# Find the first gh subcommand in shell-ish command tokens. Accept common
# wrapper and absolute-path forms used by shell/Codex sessions: `command gh`,
# `env gh`, `/usr/bin/gh`, `/opt/homebrew/bin/gh`, and `$(which gh)`.
idx = None
for i, tok in enumerate(tokens):
    base = tok.rsplit("/", 1)[-1]
    if base == "gh" and i + 1 < len(tokens) and tokens[i + 1] in {"issue", "pr", "api"}:
        idx = i
        break
if idx is None:
    sys.exit(0)

resource = tokens[idx + 1]
action = tokens[idx + 2] if idx + 2 < len(tokens) else ""
args = tokens[idx + 3:]
api_path = ""
if resource == "api":
    resource = "api"
    api_args = tokens[idx + 2:]
    for tok in api_args:
        if re.search(r'/issues/[0-9]+(?:/comments)?(?:$|[/?#])', tok):
            api_path = tok
            break
    action = "api"
    args = api_args
    if re.search(r'/issues/[0-9]+/comments(?:$|[/?#])', api_path):
        resource = "issue"
        action = "comment"
    elif re.search(r'/issues/[0-9]+(?:$|[/?#])', api_path):
        resource = "issue"
        action = "edit"

BODY_FLAGS = {"--body", "-b", "--comment", "--message", "-m", "--title"}
BODY_FILE_FLAGS = {"--body-file", "-F"}
EDITOR_FLAGS = {"--editor", "-e", "--web", "-w"}
API_FIELD_FLAGS = {"-f", "--field", "-F", "--raw-field"}
API_INPUT_FLAGS = {"--input"}

def flag_value(flags):
    for i, tok in enumerate(args):
        if tok in flags and i + 1 < len(args):
            return args[i + 1]
        for flag in flags:
            if tok.startswith(flag + "="):
                return tok.split("=", 1)[1]
    return ""


def bool_flag_present(flags):
    for tok in args:
        if tok in flags:
            return True
        for flag in flags:
            if tok.startswith(flag + "="):
                value = tok.split("=", 1)[1].strip().lower()
                if value not in {"0", "false", "no", "off"}:
                    return True
    return False


def api_field_value(name):
    prefixes = (f"{name}=", f"{name}:=")
    for i, tok in enumerate(args):
        candidates = []
        if tok in API_FIELD_FLAGS and i + 1 < len(args):
            candidates.append(args[i + 1])
        for flag in API_FIELD_FLAGS:
            if tok.startswith(flag + "="):
                candidates.append(tok.split("=", 1)[1])
        for candidate in candidates:
            for prefix in prefixes:
                if candidate.startswith(prefix):
                    return candidate[len(prefix):]
    return ""

body = flag_value(BODY_FLAGS)
body_file = flag_value(BODY_FILE_FLAGS)
editor_body = bool_flag_present(EDITOR_FLAGS)
api_input = flag_value(API_INPUT_FLAGS)
if action == "comment":
    body = body or api_field_value("body")
state_value = api_field_value("state")
state_reason_value = api_field_value("state_reason")
unreadable_body_file = ""
uninspectable_body = ""
uninspectable_editor_body = ""
uninspectable_api_payload = ""
if action in {"comment", "edit", "review"} and editor_body:
    uninspectable_editor_body = "editor"
if action in {"comment", "edit"} and api_input:
    uninspectable_api_payload = api_input
if body and body.startswith("@") and action == "comment":
    uninspectable_api_payload = body
if body and re.search(r'\$\(|`|\$\{![^}]+\}|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|\$[0-9#@*?!-]', body):
    uninspectable_body = body
if body_file:
    if body_file in {"-", "/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"}:
        unreadable_body_file = body_file
    else:
        try:
            body = Path(body_file).read_text()
        except OSError:
            unreadable_body_file = body_file

text = body or normalized_command
lower = text.lower()

# Scope: ordinary issue comments are allowed. The guard only engages when a
# command performs a state transition directly, or when a comment looks like a
# coordinator lane/status update.
state_action = action in {"close", "reopen", "ready"} or (resource == "pr" and action == "review")
coordinator_marker = re.search(
    r'\b(status|state|lane|coordinator|transition|ready for|done|complete|completed|resolved|shipped|merged|blocked|blocker)\b',
    lower,
)
if unreadable_body_file and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect --body-file content.", file=sys.stderr)
    print("Use an inline --body value or a readable file path instead of stdin/process substitution.", file=sys.stderr)
    sys.exit(2)

if uninspectable_body and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect shell-expanded --body content.", file=sys.stderr)
    print("Use a literal inline --body value or a readable --body-file path instead of variables/command substitution.", file=sys.stderr)
    sys.exit(2)

if uninspectable_api_payload and action in {"comment", "edit"}:
    print("BLOCKED: coordinator status guard cannot inspect gh api file/input payload content.", file=sys.stderr)
    print("Use literal inspectable fields instead of body=@file, body=@-, or --input payloads for status updates.", file=sys.stderr)
    sys.exit(2)

if uninspectable_editor_body and action in {"comment", "edit", "review"}:
    print("BLOCKED: coordinator status guard cannot inspect editor/web-supplied body content.", file=sys.stderr)
    print("Use a literal inline --body value or a readable --body-file path instead of --editor/--web for status updates.", file=sys.stderr)
    sys.exit(2)

if not state_action and not coordinator_marker:
    sys.exit(0)

completion = re.search(r'\b(done|complete|completed|resolved|closed|ready|shipped|released|merged|unblocked|green|go)\b', lower)
blocked = re.search(r'\b(blocked|blocker|request changes|requested changes|no owner response|awaiting owner|awaiting maintainer|awaiting approval|pending approval|approval pending|owner response pending|approval missing|signoff missing|sign-off missing|not approved|not signed off|unresolved|not satisfied|missing evidence|missing)\b', lower)
future_gate_plan = re.search(r"\b(i'll|i will|we will|i am going to|i'm going to|going to|will re-run|will rerun|re-run|rerun|then only decide|only decide whether)\b", lower) and re.search(r'\b(gate|gates|deployment|deploy|uat|hotfix|staging|movement|allowed|rollout)\b', lower)

# Block comments that turn ticket comments into promises to do gates later.
# Gate/deploy/UAT/hotfix movement updates must report current evidence or a
# concrete blocker, not future intent. Ref: #609.
if future_gate_plan:
    print("BLOCKED: coordinator gate/status update is a future-plan comment, not evidence.", file=sys.stderr)
    print("Run the gates first, then post current evidence or an explicit blocker/failure reason.", file=sys.stderr)
    sys.exit(2)

# Block comments that imply completion while naming unresolved blockers.
if completion and blocked:
    print("BLOCKED: coordinator status update mixes completion with unresolved blocker language.", file=sys.stderr)
    print("Keep the lane visibly blocked until the blocker is resolved, or remove the completion claim.", file=sys.stderr)
    sys.exit(2)

# Blocked states are valid only when the failure reason is explicit.
if blocked and not re.search(r'\b(blocked because|blocker:|failure reason:|reason:|missing:|waiting on|awaiting)', lower):
    print("BLOCKED: blocked coordinator state must include an explicit failure reason.", file=sys.stderr)
    print("Add 'Blocker:', 'Failure reason:', 'Missing:', or 'Waiting on:' with concrete evidence.", file=sys.stderr)
    sys.exit(2)

# Completion/close/ready transitions require evidence prerequisites.
if completion or action in {"close", "ready"}:
    evidence = {
        "owner_signoff": re.search(r'\b(owner|maintainer|operator)\b.{0,40}\b(approved|signoff|sign-off|signed off|confirmed)\b|\b(approved|signed off|confirmed)\b.{0,40}\bby\b.{0,20}\b(owner|maintainer|operator)\b|\bapproval thread\b.{0,80}\bhttps?://|\bowner response\b.{0,80}\bhttps?://', lower, re.S),
        "merge_or_branch": re.search(r'\b(merged|merge commit|merge evidence|pr #[0-9]+|pull/[0-9]+|branch target|target branch|base branch|develop|main|hotfix)\b|\b[0-9a-f]{7,40}\b', lower),
        "rollout": re.search(r'\b(deploy|deployed|deployment|uat|user acceptance|rollout|release|released|backfill|reindex|migration|not applicable|n/a)\b', lower),
    }
    missing = [name for name, ok in evidence.items() if not ok]
    if missing:
        print("BLOCKED: coordinator completion/state transition lacks required evidence.", file=sys.stderr)
        print("Missing: " + ", ".join(missing), file=sys.stderr)
        print("Required evidence: owner/maintainer signoff, merge/branch target evidence, and deploy/UAT/rollout evidence or N/A.", file=sys.stderr)
        sys.exit(2)

sys.exit(0)
PY
