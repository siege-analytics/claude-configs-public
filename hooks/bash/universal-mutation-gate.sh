#!/bin/bash
# Hook: universal-mutation-gate — task-owned mutations only (#1051).
# Positively classified reads bypass ALL gate lookup. Unknown actions remain
# fail-closed and must resolve one owned implementing Task and its actual scope.
set -uo pipefail
source "$(f="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/hook-path.sh"; [[ -f "$f" ]] && printf '%s' "$f" || printf /dev/null)"

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
try:
    import os
    sys.path.insert(0, os.environ["CCP_HOOK_LIB"])
    sys.dont_write_bytecode = True
    from hook_payload import metadata_environment
    slim_json = metadata_environment(data)
except (ValueError, TypeError):
    emit("large"); sys.exit()
except (ImportError, OSError):
    emit("bad"); sys.exit()
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

# Every new remote post reaches typed Task/target resolution below. A second
# legacy reporting shortcut must not authorize shapes the shared parser declines.
RESOLVE_TG="$HOOK_DIR/../lib/resolve-think-gate.py"
WORKSPACE_CANDIDATE="$(dirname "$(dirname "$HOOK_DIR")")"
WORKSPACE_FOR_RESOLVE="${CRAFT_AGENT_WORKSPACE:-$WORKSPACE_CANDIDATE}"
RESOLUTION=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_FOR_RESOLVE" --action-json || true)
READ_ONLY=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" read_only 2>/dev/null || true)
[[ "$READ_ONLY" == "True" || "$READ_ONLY" == "true" ]] && exit 0
EARLY_ALLOW=$(printf '%s' "$RESOLUTION" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(bool(((d.get("metadata_only") or d.get("remote_contact_only") or d.get("investigation")) and not d.get("metadata_posts")) or d.get("self_management") or d.get("remote_only_authorized")))' 2>/dev/null || true)
[[ "$EARLY_ALLOW" == "True" ]] && exit 0
THINK_GATE=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" gate.path 2>/dev/null || true)
if [[ -z "$THINK_GATE" ]]; then
    REASON=$(printf '%s' "$RESOLUTION" | python3 "$EXTRACT" error 2>/dev/null || true)
    echo "BLOCKED by universal-mutation-gate: ${REASON:-Task/action resolution failed closed; open a scoped task gate.}" >&2
    log_block_event "universal-mutation-gate" "unscoped or ambiguous mutation" "$COMMAND"
    exit 2
fi
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
status=implementing within this Task's actual authorized scope.
Preparation notes and review artifacts do not grant mutation authority.

To proceed:
  1. Complete your design, then update think-gate.json status to 'implementing'
  2. Confirm the action is within this Task's existing grant and scope
  3. Retry only when its actual prerequisites are satisfied
DESIGNEOF
        log_block_event "universal-mutation-gate" "mutations require implementing status" "$COMMAND"
        exit 2
    fi

    # The resolver has checked own session/Task binding and the modeled targets
    # against scope. Trusted project execution may use a cwd fallback; this
    # is not a sandbox or authority for unmodeled transitive effects. Review belongs
    # at publication, not in required pre-edit prose or posted rank signals.
    if [[ "$TG_STATUS" == "implementing" ]]; then
        exit 0
    fi
fi

# Invalid/non-implementation task statuses cannot grant mutation authority.
echo "BLOCKED by universal-mutation-gate: selected task status '${TG_STATUS:-unknown}' cannot authorize mutation; use the truthful Task state within its existing grant." >&2
log_block_event "universal-mutation-gate" "task status cannot authorize mutation" "$COMMAND"
exit 2
