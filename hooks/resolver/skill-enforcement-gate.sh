#!/bin/bash
# Hook: skill-enforcement-gate
# Enforces: SKILL.md read receipts via session transcript parsing
# Trigger: Called by ca-enforcement-gate.sh (UserPromptSubmit)
#
# Checks $CRAFT_SESSION_DIR/session.jsonl for Read tool calls targeting
# required SKILL.md files. Outputs BLOCKED: prefix for blocking signals
# (converted to continue:false by ca-enforcement-gate.sh).
#
# Enforcement checks:
#   1. think SKILL.md — if think-gate.json status=implementing,
#      skills/thinking/think/SKILL.md must appear in session Read calls.
#   2. self-review SKILL.md — if code-modifying tool calls exist,
#      skills/self-review/SKILL.md must have been Read.
#
# Ref: #449 (skill-enforcement-gate), #416 (continue:false mechanism)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

SESSION_DIR="${CRAFT_SESSION_DIR:-}"
if [[ -z "$SESSION_DIR" ]] || [[ ! -f "$SESSION_DIR/session.jsonl" ]]; then
    exit 0
fi

TRANSCRIPT="$SESSION_DIR/session.jsonl"

# Resolve think-gate (repo-scoped or legacy singleton)
RESOLVE_TG="$SCRIPT_DIR/../lib/resolve-think-gate.py"
THINK_GATE=""

if [[ -n "${CLAUDE_THINK_GATE:-}" ]] && [[ -f "$CLAUDE_THINK_GATE" ]]; then
    THINK_GATE="$CLAUDE_THINK_GATE"
elif [[ -f "$RESOLVE_TG" ]]; then
    THINK_GATE=$(python3 "$RESOLVE_TG" --workspace "$WORKSPACE_ROOT" 2>/dev/null \
        | python3 -c "import json,sys; r=json.load(sys.stdin); print(r['path'] if r else '')" 2>/dev/null || true)
fi
if [[ -z "$THINK_GATE" ]] && [[ -f "$WORKSPACE_ROOT/think-gate.json" ]]; then
    THINK_GATE="$WORKSPACE_ROOT/think-gate.json"
fi

if [[ -z "$THINK_GATE" ]] || [[ ! -f "$THINK_GATE" ]]; then
    exit 0
fi

TG_STATUS=$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('status', ''))
except: pass
" "$THINK_GATE" 2>/dev/null || true)

if [[ "$TG_STATUS" != "implementing" ]]; then
    exit 0
fi

# Parse session transcript for SKILL.md Read receipts.
# Python JSON parsing: ~0.1s for 5700 lines.
python3 - "$TRANSCRIPT" "$THINK_GATE" <<'PYEOF'
import json
import sys

transcript_path = sys.argv[1]
think_gate_path = sys.argv[2]

skill_reads = set()
has_code_mutations = False

CODE_TOOLS = {"Edit", "Write", "NotebookEdit"}

try:
    with open(transcript_path) as f:
        for i, line in enumerate(f):
            if i == 0:
                continue
            try:
                d = json.loads(line.strip())
            except (json.JSONDecodeError, ValueError):
                continue

            tool_name = d.get("toolName", "")

            if tool_name == "Read":
                inp = d.get("toolInput", {})
                if isinstance(inp, str):
                    try:
                        inp = json.loads(inp)
                    except (json.JSONDecodeError, ValueError):
                        continue
                fp = inp.get("file_path", "")
                if "SKILL.md" in fp:
                    norm = fp.lstrip("./")
                    skill_reads.add(norm)

            if tool_name in CODE_TOOLS:
                has_code_mutations = True
except Exception:
    sys.exit(0)

# Check 1: think skill read receipt
think_patterns = ["skills/thinking/think/SKILL.md", "skills/think/SKILL.md"]
think_read = any(
    any(p in sr for p in think_patterns) for sr in skill_reads
)

if not think_read:
    try:
        tg = json.load(open(think_gate_path))
        ticket = tg.get("ticket", "current task")
    except Exception:
        ticket = "current task"
    print(f"BLOCKED: skills/thinking/think/SKILL.md has not been Read this "
          f"session. The think skill is the first gate for {ticket} — "
          f"read it before proceeding with implementation. Ref: #449")
    sys.exit(0)

# Check 2: self-review skill read receipt (warning only — not blocking)
if has_code_mutations:
    sr_patterns = ["skills/self-review/SKILL.md"]
    sr_read = any(
        any(p in sr for p in sr_patterns) for sr in skill_reads
    )
    if not sr_read:
        print("WARNING: Code-modifying tool calls detected but "
              "skills/self-review/SKILL.md has not been Read this session. "
              "Read the self-review skill before pushing. Ref: #449")
        sys.exit(0)
PYEOF

exit 0
