#!/bin/bash
# Hook: universal-mutation-gate — task-owned mutations only (#1051).
# Positively classified reads bypass ALL gate lookup. Unknown actions remain
# fail-closed and must resolve one task with complete implementation artifacts.
set -uo pipefail
export PATH="/home/craftagents/bin:$PATH"

INPUT=$(cat)
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
EXTRACT="$HOOK_DIR/../lib/extract-json.py"
export CCP_HOOK_LIB="$HOOK_DIR/../lib"
# Block-event logging (#602): record every block for classification.
source "$HOOK_DIR/../lib/log-block.sh" 2>/dev/null || true
_fail_closed() {
    command -v log_block_event >/dev/null 2>&1 && log_block_event "universal-mutation-gate" "$1" "" 2>/dev/null
    echo "BLOCKED by universal-mutation-gate: $1; failing closed." >&2
    exit 2
}

# Fail CLOSED when the gate cannot read its own input (#1097). An empty command
# below means "nothing to check", so every way extraction can break used to
# allow every command. extract-json.py exits 0 for a missing key, {}, malformed
# JSON and empty stdin alike, so its result cannot be trusted on its own.
[[ -f "$EXTRACT" && -r "$EXTRACT" ]] || _fail_closed "cannot read its JSON extractor at $EXTRACT"
command -v python3 >/dev/null 2>&1 || _fail_closed "python3 is not on PATH, so the payload cannot be read"
[[ -z "$INPUT" ]] && exit 0   # no event at all: nothing to decide

# One probe parses the payload and returns, NUL-separated: a status, the three
# fields this hook reads (with extract-json.py's exact output rules), and a slim
# copy of the payload with every long string emptied except tool_input.command.
# The status is "ok" only for a JSON object whose fields could be read, so any
# failure - including a python3 that does nothing - blocks. The slim copy is
# what the resolver reads from the environment: an exported value over the
# kernel's 128 KiB per-string limit makes every later exec fail, which used to
# let a padded command through and would now block a large Write.
_PROBE_PY='
import json, sys
def field(data, path):
    cur = data
    for key in path.split("."):
        if not (isinstance(cur, dict) and key in cur):
            return ""
        cur = cur[key]
    if cur is None or cur == "":
        return ""
    text = json.dumps(cur) if isinstance(cur, (dict, list)) else str(cur)
    return text.rstrip("\n").replace("\0", "")
def slim(v):
    if isinstance(v, str):
        return "" if len(v) > 4096 else v
    if isinstance(v, dict):
        return {k: slim(x) for k, x in v.items()}
    if isinstance(v, list):
        return [slim(x) for x in v]
    return v
def emit(*parts):
    sys.stdout.buffer.write(b"".join(p.encode("utf-8") + b"\0" for p in parts))
try:
    data = json.load(sys.stdin)
except Exception:
    emit("bad"); sys.exit()
if not isinstance(data, dict):
    emit("bad"); sys.exit()
command = field(data, "tool_input.command")
# Sizes are bytes as exec sees them, not characters: a command of 64k
# four-byte characters is 256 KiB in argv, and json.dumps escapes each as
# \uXXXX (#1106 review).
if len(command.encode("utf-8", "surrogatepass")) > 65536:
    emit("large"); sys.exit()
out = slim(data)
if command:
    out["tool_input"]["command"] = data["tool_input"]["command"]
slim_json = json.dumps(out)
if len(slim_json.encode("utf-8")) > 98304:
    emit("large"); sys.exit()
try:
    emit("ok", command, field(data, "cwd"), field(data, "tool_name"), slim_json)
except UnicodeEncodeError:
    sys.stdout.buffer.write(b"unreadable\0")
'
_STATUS=""; COMMAND=""; CWD=""; TOOL_NAME=""; _SLIM=""
{ IFS= read -r -d '' _STATUS; IFS= read -r -d '' COMMAND; IFS= read -r -d '' CWD
  IFS= read -r -d '' TOOL_NAME; IFS= read -r -d '' _SLIM; } \
    < <(printf '%s' "$INPUT" | python3 -c "$_PROBE_PY" 2>/dev/null)
case "$_STATUS" in
    ok) ;;
    large) _fail_closed "the command or its payload is too large to check (over 64 KiB / 96 KiB)" ;;
    unreadable) _fail_closed "the command cannot be read as text" ;;
    *) _fail_closed "input is not a JSON hook payload" ;;
esac
export CCP_HOOK_INPUT_JSON="$_SLIM"
if [[ -z "$COMMAND" && ! "$TOOL_NAME" =~ ^(Write|Edit|MultiEdit|NotebookEdit)$ ]]; then exit 0; fi

# No emergency disable. To disable the gate, comment out the hook in
# settings.json — that produces an auditable change. (#477)

# Governance issue reporting is a reporting surface, not an implementation
# mutation. Allow only inspectable `gh issue create` / `gh issue comment`
# commands with non-empty title/body evidence. Issue edit/close/delete/etc.
# remain guarded shared-resource mutations.
is_governance_issue_reporting_command() {
    python3 - "$COMMAND" "$CWD" <<'PYCODE'
import os, shlex, sys

command = sys.argv[1]
cwd = sys.argv[2] or os.getcwd()
if any(ch in command for ch in "\n\r;&|<>`$"):
    sys.exit(1)
try:
    args = shlex.split(command)
except ValueError:
    sys.exit(1)
if len(args) >= 3 and args[0] == "cd":
    if len(args) < 5 or args[2] != "&&":
        sys.exit(1)
    cwd = args[1]
    args = args[3:]
if len(args) < 3 or args[0] != "gh" or args[1] != "issue":
    sys.exit(1)
sub = args[2]
if sub not in {"create", "comment"}:
    sys.exit(1)

def parse_flags(positional_count, required_flags):
    positional = []
    flags = {}
    i = 3
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            if "=" in arg:
                flag, value = arg.split("=", 1)
            else:
                flag = arg
                i += 1
                if i >= len(args):
                    sys.exit(1)
                value = args[i]
            if flag not in required_flags:
                sys.exit(1)
            if flag in flags:
                sys.exit(1)
            flags[flag] = value
        else:
            positional.append(arg)
        i += 1
    if len(positional) != positional_count:
        sys.exit(1)
    return positional, flags

def nonempty_body(flags):
    has_body = "--body" in flags
    has_body_file = "--body-file" in flags
    if has_body == has_body_file:
        return False
    if has_body:
        return bool(flags["--body"].strip())
    body_file = flags["--body-file"]
    if body_file == "-" or body_file.startswith(("/dev/fd/", "/proc/self/fd/")):
        return False
    path = body_file if os.path.isabs(body_file) else os.path.join(cwd, body_file)
    try:
        return os.path.isfile(path) and os.path.getsize(path) > 0 and bool(open(path, encoding="utf-8").read().strip())
    except Exception:
        return False

if sub == "create":
    _positional, flags = parse_flags(0, {"--repo", "--title", "--body", "--body-file"})
    title = flags.get("--title", "")
    if not title.strip():
        sys.exit(1)
    if not nonempty_body(flags):
        sys.exit(1)
    sys.exit(0)

positional, flags = parse_flags(1, {"--repo", "--body", "--body-file"})
if positional[0].startswith("-"):
    sys.exit(1)
if not nonempty_body(flags):
    sys.exit(1)
sys.exit(0)
PYCODE
}

if is_governance_issue_reporting_command; then
    exit 0
fi

RESOLVE_TG="$HOOK_DIR/../lib/resolve-think-gate.py"
WORKSPACE_CANDIDATE="$(dirname "$(dirname "$HOOK_DIR")")"
WORKSPACE_FOR_RESOLVE="${CRAFT_AGENT_WORKSPACE:-$WORKSPACE_CANDIDATE}"
RESOLUTION=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_FOR_RESOLVE" --action-json || true)
READ_ONLY=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" read_only 2>/dev/null || true)
[[ "$READ_ONLY" == "True" || "$READ_ONLY" == "true" ]] && exit 0
EARLY_ALLOW=$(printf '%s' "$RESOLUTION" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(bool(d.get("investigation") or d.get("self_management")))' 2>/dev/null || true)
[[ "$EARLY_ALLOW" == "True" ]] && exit 0
THINK_GATE=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" gate.path 2>/dev/null || true)
if [[ -z "$THINK_GATE" ]]; then
    REASON=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" error 2>/dev/null || true)
    echo "BLOCKED by universal-mutation-gate: ${REASON:-Task/action resolution failed closed; open a scoped task gate.}" >&2
    log_block_event "universal-mutation-gate" "unscoped or ambiguous mutation" "$COMMAND"
    exit 2
fi
GATE_PATHS_JSON=$(printf '%s' "$RESOLUTION" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("artifacts", {})))' 2>/dev/null || echo '{}')
HOST_SESSION_DIR=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" session_dir 2>/dev/null || true)
# Proportional task gates (#1086): the selected task's effective review tier
# (declared tier, never below the floor review-risk.py computes for the targets).
TIER_JSON=$(printf '%s' "$RESOLUTION" | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin).get("tier") or {"effective": "C", "reasons": ["C:no tier resolved; failing closed"]}))' 2>/dev/null || echo '{"effective": "C"}')
REPO_ROOT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("repo_root", ""))' "$THINK_GATE" 2>/dev/null || true)

if [[ -n "$THINK_GATE" ]]; then
    TG_STATUS=$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('status', ''))
except Exception:
    pass
" "$THINK_GATE" 2>/dev/null || true)

    if [[ "$TG_STATUS" == "designing" || "$TG_STATUS" == "reviewing" ]]; then
        # Recognized reads, bounded diagnostics and own signal lifecycle
        # writes exited above. Other actions require implementation authority.
        CMD_SHORT_DESIGN="${COMMAND:0:120}"
        if [[ ${#COMMAND} -gt 120 ]]; then
            CMD_SHORT_DESIGN="${CMD_SHORT_DESIGN}..."
        fi
        cat >&2 <<DESIGNEOF
BLOCKED by universal-mutation-gate (#574): mutations not allowed during designing/reviewing

Command: $CMD_SHORT_DESIGN

Status '$TG_STATUS' allows read-only and investigation commands, but this
command is not a recognized reader or bounded investigation command. Mutations require
status=implementing with this task's effective review tier satisfied.
Effective tier: $(printf '%s' "$TIER_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("effective", "C"))' 2>/dev/null || echo C).
Tier A needs its implementing gate; B adds investigation and pre-mortem;
C also requires junior/senior review and artifacts-posted.

To proceed:
  1. Complete your design, then update think-gate.json status to 'implementing'
  2. Ensure all required artifacts reference the current ticket
  3. Retry the command
DESIGNEOF
        log_block_event "universal-mutation-gate" "mutations require implementing status" "$COMMAND"
        exit 2
    fi

    if [[ "$TG_STATUS" == "implementing" ]]; then
        MISSING=$(python3 -c "
import json, sys, os, glob

think_gate_path = sys.argv[1]
workspace = sys.argv[2]
plans_path = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '__none__' else ''
gate_paths = json.loads(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4] not in ('', '__none__') else {}
try:
    tier = json.loads(sys.argv[5]).get('effective', 'C') if len(sys.argv) > 5 else 'C'
except Exception:
    tier = 'C'
tier = tier if tier in ('A', 'B', 'C') else 'C'
# A: an implementing gate bound to the ticket. B: + investigation and pre-mortem.
# C: + junior/senior and artifacts-posted (the pre-#1086 requirement).
need_investigation = tier in ('B', 'C')
need_premortem = tier in ('B', 'C')
need_review_comments = tier == 'C' 

try:
    tg = json.load(open(think_gate_path))
except Exception:
    print('malformed think gate')
    sys.exit(0)

current_ticket = tg.get('ticket') or tg.get('task_id') or tg.get('task', '')

def file_references_ticket(path, ticket, content=None):
    if not ticket:
        return True
    try:
        content = open(path).read(4096) if content is None else content[:4096]
    except Exception:
        return False
    return bool(re.search(r'(?<![A-Za-z0-9_/#-])' + re.escape(ticket) + r'(?![A-Za-z0-9_#-])', content))

import re
def premortem_has_risks(path, content=None):
    try:
        content = open(path).read(8192) if content is None else content
    except Exception:
        return False
    lower = content.lower()
    return bool(
        'severity:' in lower
        or '**urgency:**' in lower
        or re.search(r'(?:tiger|paper tiger|elephant)\s+\d', lower)
    )

def premortem_has_launch_blocker(path, content=None):
    try:
        content = open(path).read(8192) if content is None else content
    except Exception:
        return False
    lower = content.lower()
    if 'implementation may proceed: no' in lower:
        return True
    if re.search(r'\*\*status:\*\*\s*blocks-launch', lower):
        return True
    return False

missing = []
def need(kind, item):
    # Only the artifacts this task's tier requires can block (#1086).
    if {'investigation': need_investigation, 'premortem': need_premortem,
        'review_comments': need_review_comments}[kind]:
        missing.append(item)

# 1. Check investigate-gate.json (ticket field must match)
invest_found = False
invest_candidates = []
resolved_invest = gate_paths.get('investigate-gate')
if resolved_invest:
    invest_candidates.append(resolved_invest)
for candidate in invest_candidates:
    if os.path.isfile(candidate):
        try:
            ig = json.load(open(candidate))
            if (ig.get('ticket') or ig.get('task_id') or ig.get('task', '')) == current_ticket:
                findings = ig.get('findings', [])
                if not findings:
                    need('investigation', 'investigation has no findings (investigate-gate.json for ' + (current_ticket or 'current task') + ')')
                invest_found = True
                break
        except Exception:
            pass
if not invest_found:
    need('investigation', 'investigate-gate.json for ' + (current_ticket or 'current task'))

# 2. Check pre-mortem artifact (must reference current ticket)
premortem_found = False
plan_dirs = []
# The current host session's own plans are a writable lifecycle surface.
# Other sessions' plans are never discovered here.
current_session_dir = sys.argv[6] if len(sys.argv) > 6 and sys.argv[6] else None
# A mis-tagged session dir must not lend this task another session's plans (#1099).
sys.path.insert(0, os.environ.get('CCP_HOOK_LIB', ''))
from session_anchor import verified_session_dir, payload_from_env
current_session_dir = verified_session_dir(current_session_dir or '', payload_from_env()) or current_session_dir
if current_session_dir:
    session_plans = os.path.join(current_session_dir, 'plans')
    if os.path.isdir(session_plans):
        plan_dirs.append(session_plans)
if plans_path and os.path.isdir(plans_path):
    plan_dirs.append(plans_path)
ca_ws = os.environ.get('CRAFT_AGENT_WORKSPACE', '')
if ca_ws:
    ca_plans = os.path.join(ca_ws, 'plans')
    if os.path.isdir(ca_plans):
        plan_dirs.append(ca_plans)
ws_plans = os.path.join(workspace, 'plans')
if os.path.isdir(ws_plans):
    plan_dirs.append(ws_plans)

# Repo plans/ (from think-gate.json repo_root field)
repo_root = tg.get('repo_root', '')
if repo_root:
    repo_plans = os.path.join(repo_root, 'plans')
    if os.path.isdir(repo_plans) and repo_plans not in plan_dirs:
        plan_dirs.append(repo_plans)

# A plain task id is unique only inside its host session. Shared plan shelves
# cannot establish provenance for it; a full repository-qualified ticket can.
plain_task_id = not re.fullmatch(r'[^/\s]+/[^#\s]+#[0-9]+', current_ticket)
if plain_task_id:
    plan_dirs = [os.path.join(current_session_dir, 'plans')] if current_session_dir else []

def read_own_premortem(path):
    # Read plain-id evidence once without following borrowed links.
    import stat
    root_fd = plans_fd = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        root_fd = os.open(os.path.realpath(current_session_dir), directory_flags)
        plans_fd = os.open('plans', directory_flags, dir_fd=root_fd)
        fd = os.open(os.path.basename(path), os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                     dir_fd=plans_fd)
        with os.fdopen(fd) as source:
            st = os.fstat(source.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
                return None
            return source.read(8192)
    except (OSError, ValueError, UnicodeError):
        return None
    finally:
        if plans_fd is not None:
            os.close(plans_fd)
        if root_fd is not None:
            os.close(root_fd)

premortem_empty = False
premortem_launch_blocked = False
premortem_path = ''
for d in plan_dirs:
    for pattern in ['pre-mortem*', 'premortem*', 'risk*']:
        for f in glob.glob(os.path.join(d, pattern)):
            content = read_own_premortem(f) if plain_task_id else None
            if plain_task_id and content is None:
                continue
            if os.path.isfile(f) and file_references_ticket(f, current_ticket, content):
                premortem_found = True
                premortem_path = f
                if not premortem_has_risks(f, content):
                    premortem_empty = True
                if premortem_has_launch_blocker(f, content):
                    premortem_launch_blocked = True
                break
        if premortem_found:
            break
    if premortem_found:
        break

if not premortem_found:
    need('premortem', 'pre-mortem artifact for ' + (current_ticket or 'current task'))
elif premortem_empty:
    need('premortem', 'pre-mortem artifact has no classified risks (need Severity: or Tiger/Elephant entries)')
elif premortem_launch_blocked:
    need('premortem', 'pre-mortem contains Launch-Blocking Tiger (' + os.path.basename(premortem_path) + ') — mitigate before implementation')

# 3. Check junior-senior-gate.json (#492)
js_gate_found = False
js_candidates = []
resolved_js = gate_paths.get('junior-senior-gate')
if resolved_js:
    js_candidates.append(resolved_js)
for js_candidate in js_candidates:
    if os.path.isfile(js_candidate):
        try:
            js = json.load(open(js_candidate))
            if (js.get('ticket') or js.get('task_id') or js.get('task', '')) == current_ticket:
                if js.get('junior_found') and js.get('senior_found'):
                    js_gate_found = True
                else:
                    if not js.get('junior_found'):
                        need('review_comments', 'Junior task description on ' + (current_ticket or 'ticket'))
                    if not js.get('senior_found'):
                        need('review_comments', 'Senior adversarial checklist on ' + (current_ticket or 'ticket'))
                    js_gate_found = True  # file found, just incomplete
                break
        except Exception:
            pass
if not js_gate_found:
    need('review_comments', 'Junior/Senior comments (junior-senior-gate.json) for ' + (current_ticket or 'current task'))

# 4. Check artifacts-posted-gate.json (#513)
ap_gate_found = False
ap_candidates = []
resolved_ap = gate_paths.get('artifacts-posted-gate')
if resolved_ap:
    ap_candidates.append(resolved_ap)
for ap_candidate in ap_candidates:
    if os.path.isfile(ap_candidate):
        try:
            ap = json.load(open(ap_candidate))
            if (ap.get('ticket') or ap.get('task_id') or ap.get('task', '')) == current_ticket:
                if not ap.get('investigate_posted'):
                    need('review_comments', 'Investigation not posted to ticket ' + (current_ticket or ''))
                if not ap.get('premortem_posted'):
                    need('review_comments', 'Pre-mortem not posted to ticket ' + (current_ticket or ''))
                if 'selfreview_posted' in ap and not ap.get('selfreview_posted'):
                    need('review_comments', 'Self-review not posted to ticket ' + (current_ticket or ''))
                ap_gate_found = True
                break
        except Exception:
            pass
if not ap_gate_found:
    need('review_comments', 'Artifacts-posted check (artifacts-posted-gate.json) for ' + (current_ticket or 'current task'))

# 5. Check review-gate.json (#526)
# If a review was done and HEAD has moved since, block until re-review.
# No file = no review = no block (not every task has a review).
import subprocess as _sp
rg_candidates = []
resolved_rg = gate_paths.get('review-gate')
if resolved_rg:
    rg_candidates.append(resolved_rg)
for rg_candidate in rg_candidates:
    if os.path.isfile(rg_candidate):
        try:
            rg = json.load(open(rg_candidate))
            rg_verdict = rg.get('verdict', '')
            if rg_verdict == 'approve':
                break
            rg_branch = rg.get('branch', '')
            rg_commit = rg.get('reviewed_commit', '')
            if not rg_branch or not rg_commit:
                break
            try:
                cur_branch = _sp.check_output(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    text=True, timeout=5
                ).strip()
            except Exception:
                break
            if cur_branch != rg_branch:
                break
            try:
                head = _sp.check_output(
                    ['git', 'rev-parse', 'HEAD'],
                    text=True, timeout=5
                ).strip()
            except Exception:
                break
            if not head.startswith(rg_commit) and not rg_commit.startswith(head):
                missing.append('Re-review required: new commits since last review on ' + rg_branch)
        except Exception:
            missing.append('malformed review gate')
        break

print('|'.join(missing))
" "$THINK_GATE" "$WORKSPACE_CANDIDATE" "${CRAFT_AGENT_PLANS_PATH:-__none__}" "$GATE_PATHS_JSON" "$TIER_JSON" "$HOST_SESSION_DIR" 2>/dev/null || echo "artifact validation failed closed")

        if [[ -z "$MISSING" ]]; then
            exit 0
        fi

        # Format the missing list for display
        MISSING_DISPLAY=$(echo "$MISSING" | tr '|' '\n' | sed 's/^/  - /')
        TIER_LABEL=$(printf '%s' "$TIER_JSON" | python3 -c 'import json,sys
t = json.load(sys.stdin); r = "; ".join(t.get("reasons", [])[:3])
print(t.get("effective", "C") + (" (" + r + ")" if r else ""))' 2>/dev/null || echo C)

        cat >&2 <<ARTEOF
BLOCKED by universal-mutation-gate (#477/#484): artifacts missing or wrong ticket

This task's review tier is $TIER_LABEL.
Its required artifacts are missing or do not reference the current ticket:
$MISSING_DISPLAY
Tier A (prose, plans, generated files) needs only this implementing gate; B adds
an investigation and a pre-mortem; C (enforcement, release, deploy, credentials,
destructive operations) adds junior/senior review and artifacts-posted (#1086).

The gate requires both an investigation artifact (investigate-gate.json)
and a pre-mortem artifact (plans/pre-mortem-*.md) that reference the
CURRENT ticket. Artifacts from prior tasks do not satisfy the gate.

Produce the missing artifacts for the current ticket, then retry.
ARTEOF
        log_block_event "universal-mutation-gate" "implementing artifacts incomplete" "$COMMAND"
        exit 2
    fi
fi

# Invalid/non-implementation task statuses cannot grant mutation authority.
echo "BLOCKED by universal-mutation-gate: selected task status '${TG_STATUS:-unknown}' cannot authorize mutation; complete its implementation artifacts." >&2
log_block_event "universal-mutation-gate" "task status cannot authorize mutation" "$COMMAND"
exit 2
