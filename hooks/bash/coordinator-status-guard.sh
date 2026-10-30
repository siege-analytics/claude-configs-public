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
# Fast skip (#1083): exit before starting python3 when the tool payload's
# command cannot match this hook's trigger. Only taken when tool_input's first
# key is a non-empty "command" (an empty or missing command keeps the git-push
# fallback) and the command uses no JSON escape other than \n \t \r \" \\ \/
# (\u, \f, \b could hide letters or whitespace). \n \t \r become spaces, so an
# escaped newline before the trigger still counts as a boundary. Git-hook
# invocations (refs on stdin, no JSON) take the full path.
_FAST_CMDS=$(printf '%s' "$INPUT" | grep -oE '"command"[[:space:]]*:[[:space:]]*"(\\.|[^"\\])*"' 2>/dev/null || true)
# A long command takes the full path (#1098): bash substitutions slow down
# superlinearly under a UTF-8 locale, and past the hook timeout a skip check
# would let the command through. 16 KiB keeps the check in milliseconds.
_FAST_FULL=0; (( ${#_FAST_CMDS} > 16384 )) && { _FAST_FULL=1; _FAST_CMDS=""; }
_FAST_ESC="${_FAST_CMDS//'\\'/}"; _FAST_ESC="${_FAST_ESC//'\"'/}"; _FAST_ESC="${_FAST_ESC//'\/'/}"
_FAST_ESC="${_FAST_ESC//'\n'/}"; _FAST_ESC="${_FAST_ESC//'\t'/}"; _FAST_ESC="${_FAST_ESC//'\r'/}"
_FAST_CMDS="${_FAST_CMDS//'\n'/ }"; _FAST_CMDS="${_FAST_CMDS//'\t'/ }"; _FAST_CMDS="${_FAST_CMDS//'\r'/ }"
# The shell rebuilds words from quotes and backslashes (#1098): `git "add"`,
# `g\it add` and `git  add` all run git add. Match the trigger against the text
# as written and against a copy with quote and backslash characters dropped and
# blanks squeezed; skip only if neither matches. A command containing ANSI-C
# $'...' (which can spell any byte) takes the full path.
[[ "$_FAST_CMDS" == *"\$'"* ]] && _FAST_FULL=1
# A quote or backslash between two letters or digits (`pr"x"`, `x\git`) joins
# words; only the full path's quote handling decides what that runs. In the
# JSON text a shell `"` or `\` is itself escaped, hence the leading backslash.
[[ "$_FAST_CMDS" == *[[:alnum:]]\\[\"\\][[:alnum:]]* || "$_FAST_CMDS" == *[[:alnum:]]\'[[:alnum:]]* ]] && _FAST_FULL=1
_FAST_BUILT="${_FAST_CMDS//[\"\'\\]/}"
while [[ "$_FAST_BUILT" == *"  "* ]]; do _FAST_BUILT="${_FAST_BUILT//  / }"; done
# shlex joins quoted pieces (g''h, "g"h, g\h -> gh): also test with quotes removed.
_FAST_BARE="${_FAST_CMDS//[\"\'\\]/}"

_FAST_FIRST='"tool_input"[[:space:]]*:[[:space:]]*[{][[:space:]]*"command"[[:space:]]*:[[:space:]]*"[^"]'
_FAST_RE='gh'
if [[ $_FAST_FULL == 0 && "$INPUT" =~ $_FAST_FIRST && "$_FAST_ESC" != *'\'* ]] && ! [[ "$_FAST_CMDS" =~ $_FAST_RE || "$_FAST_BUILT" =~ $_FAST_RE || "$_FAST_BARE" =~ $_FAST_RE ]]; then exit 0; fi
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
COMMAND=$(printf '%s' "$INPUT" | python3 "$EXTRACT" tool_input.command 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

CWD=$(printf '%s' "$INPUT" | python3 "$EXTRACT" cwd 2>/dev/null || true)
python3 -B - "$COMMAND" "$HOOK_DIR/../lib" "$CWD" <<'PY'
import re
import shlex
import sys
from pathlib import Path

command = sys.argv[1]
sys.path.insert(0, sys.argv[2])
from task_actions import action as classify_action
import os
# Text edits to existing artifacts are not coordinator state transitions.
if classify_action(command, sys.argv[3] or os.getcwd()).get("metadata_only"):
    sys.exit(0)
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
        if re.search(r'/(?:issues|pulls)/[0-9]+(?:/comments)?(?:$|[/?#])', tok):
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
    elif re.search(r'/pulls/[0-9]+(?:$|[/?#])', api_path):
        resource = "pr"
        action = "edit"

# Read-only subcommands carry no status claim to evaluate; never gate them.
# A completion/evidence gate firing on `gh pr view --json state,mergedAt` is a
# false positive: the --json field names, not a status update, match the
# vocabulary. Reads are outside this guard's domain (status comments + state
# transitions). Ref: claude-configs-public#940.
READ_ACTIONS = {"view", "list", "diff", "checks", "status"}
if resource in {"issue", "pr"} and action in READ_ACTIONS:
    sys.exit(0)
# `gh api` without a mutating method or a request-body/field flag is a GET read.
# (Issue-comment/edit api paths were already reclassified to issue+comment/edit
# above, so they are writes and are not exempted here.)
if resource == "api":
    _api_args = tokens[idx + 2:]
    _mutating_method = any(t in {"-X", "--method"} for t in _api_args) and any(
        t.upper() in {"POST", "PUT", "PATCH", "DELETE"} for t in _api_args
    )
    _has_body = any(
        t in {"-f", "--field", "--raw-field", "--input", "-F"}
        or t.startswith(("-f=", "--field=", "--raw-field=", "--input=", "-F="))
        for t in _api_args
    )
    if not _mutating_method and not _has_body:
        sys.exit(0)

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
api_state_transition = bool(api_path and (state_value or state_reason_value))
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
state_action = action in {"close", "reopen", "ready"} or (resource == "pr" and action == "review") or api_state_transition
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
if completion or action in {"close", "ready"} or api_state_transition:
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
