#!/bin/bash
# UserPromptSubmit hook: inject the compact kernel and a deterministic task/project load set.
set -euo pipefail
HOOK_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$HOOK_DIR/../.." && pwd)"
CANONICAL_KERNEL="$REPO_ROOT/skills/KERNEL.md"
KERNEL="${CLAUDE_KERNEL_PATH:-$CANONICAL_KERNEL}"
SELECTOR="$REPO_ROOT/bin/resolve-load-set.py"
block_invalid_kernel() {
  printf '%s\n' '{"continue":false,"systemMessage":"BLOCKED: mandatory compact safety kernel is unavailable or invalid; restore the canonical KERNEL.md before continuing."}'
  exit 0
}
# A caller-controlled path may be useful for packaging tests, but it must not
# change the invariant policy surface. Accept only byte-identical kernel
# content within the source-bound budget; never treat arbitrary content as the
# kernel merely because an environment variable points to it.
[[ -f "$CANONICAL_KERNEL" && -f "$KERNEL" ]] || block_invalid_kernel
[[ "$(wc -c < "$KERNEL" | tr -d ' ')" -le 80000 ]] || block_invalid_kernel
cmp -s "$CANONICAL_KERNEL" "$KERNEL" || block_invalid_kernel
PAYLOAD="$(cat || true)"
PROMPT="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; d=json.load(sys.stdin) if not sys.stdin.isatty() else {}; print(d.get("prompt") or d.get("tool_input",{}).get("prompt") or "")' 2>/dev/null || true)"
PROMPT_CWD="$(printf '%s' "$PAYLOAD" | python3 -c 'import json,sys; d=json.load(sys.stdin) if not sys.stdin.isatty() else {}; print(d.get("cwd") or "")' 2>/dev/null || true)"
[[ -n "$PROMPT_CWD" && -d "$PROMPT_CWD" ]] || PROMPT_CWD="$PWD"
MODE="${CLAUDE_PROGRESSIVE_LOADING:-on}"
if [[ "$MODE" == "off" || "$MODE" == "kernel-only" ]]; then
  cat <<EOF
<skill-kernel mode="kernel-only">
$(cat "$KERNEL")
</skill-kernel>
<progressive-load-set>
state: disabled
project: none
diagnostic: selector disabled by canary control; kernel only
</progressive-load-set>
EOF
elif [[ ! -x "$(command -v python3 || true)" || ! -f "$SELECTOR" ]]; then
  cat <<EOF
<skill-kernel mode="$MODE">
$(cat "$KERNEL")
</skill-kernel>
<progressive-loading-warning>Selector unavailable; kernel-only mode. No broad fallback was loaded.</progressive-loading-warning>
EOF
else
  RESULT="$(python3 "$SELECTOR" --prompt "$PROMPT" --cwd "$PROMPT_CWD" 2>/dev/null || true)"
  LABEL="load"; ACTION="Read each selected skill before acting."
  if [[ "$MODE" == "canary" ]]; then LABEL="candidate"; ACTION="Canary mode: report candidates but do not load them automatically."; fi
  cat <<EOF
<skill-kernel mode="$MODE">
$(cat "$KERNEL")
</skill-kernel>
<progressive-load-set>
EOF
  printf '%s' "$RESULT" | python3 -c 'import json,sys; from pathlib import Path; label=sys.argv[1]; root=Path(sys.argv[2]).resolve(); d=json.load(sys.stdin); selected=d.get("selected",[]); resolved=[(x,(root/x.get("load_path",x.get("source_path","unknown"))).resolve()) for x in selected]; [p.relative_to(root) for _,p in resolved]; missing=[str(p) for _,p in resolved if not p.is_file()]; assert not missing,"unreadable runtime path(s): "+",".join(missing); print("state: "+d["state"]); print("project: "+str(d.get("project") or "none")); [print("%s: %s | path=%s | source=%s | route=%s | reasons=%s"%(label,x["slug"],p,x.get("source_path","unknown"),x["route"],",".join(x["reasons"]))) for x,p in resolved]; print("diagnostic: "+d["diagnostic"])' "$LABEL" "$REPO_ROOT" 2>/dev/null || printf 'state: error\ndiagnostic: selector output invalid or selected runtime path unreadable; kernel only\n'
  cat <<EOF
$ACTION Unknown or ambiguous means kernel only; do not load the full library.
Reference shelves never self-select and may load only through an active skill's declared reference.
</progressive-load-set>
EOF
fi

# --- Pipeline status: scan for plan artifacts and warn on incomplete chains ---
# Scan locations: CRAFT_AGENT_PLANS_PATH (session plans) and CWD/plans/ (repo plans).
# Only emit the warning if think-*.md files exist (no noise otherwise).

PLANS_DIRS=""
[[ -n "${CRAFT_AGENT_PLANS_PATH:-}" ]] && [[ -d "$CRAFT_AGENT_PLANS_PATH" ]] && PLANS_DIRS="$CRAFT_AGENT_PLANS_PATH"
[[ -d "plans" ]] && PLANS_DIRS="$PLANS_DIRS${PLANS_DIRS:+ }plans"

if [[ -n "$PLANS_DIRS" ]]; then
    # shellcheck disable=SC2086
    THINK_FILES=$(find $PLANS_DIRS -maxdepth 1 -name 'think-*.md' 2>/dev/null | sed -n '1,10p')

    if [[ -n "$THINK_FILES" ]]; then
        # Check for downstream artifacts (any, not ticket-matched — v1)
        # shellcheck disable=SC2086
        HAS_INVESTIGATE=$(find $PLANS_DIRS -maxdepth 1 -name 'investigate-*.md' 2>/dev/null | sed -n '1p')
        # shellcheck disable=SC2086
        HAS_PREMORTEM=$(find $PLANS_DIRS -maxdepth 1 \( -name 'pre-mortem-*.md' -o -name 'premortem-*.md' \) 2>/dev/null | sed -n '1p')
        # shellcheck disable=SC2086
        HAS_SELFREVIEW=$(find $PLANS_DIRS -maxdepth 1 -name 'self-review-*.md' 2>/dev/null | sed -n '1p')

        MISSING=""
        [[ -z "$HAS_INVESTIGATE" ]] && MISSING="${MISSING}  [!] investigate artifact: MISSING — produce Fact Sheet before implementation\n"
        [[ -z "$HAS_PREMORTEM" ]] && MISSING="${MISSING}  [!] pre-mortem artifact: MISSING — classify risks before implementation\n"

        if [[ -n "$MISSING" ]]; then
            THINK_LIST=$(echo "$THINK_FILES" | sed 's/^/  /')
            cat <<PIPELINE

>>> PIPELINE STATUS (think Step 7 enforcement) <<<
Design note(s) found:
$THINK_LIST

Downstream artifacts incomplete:
$(printf '%b' "$MISSING")
DO NOT proceed to implementation until investigate and pre-mortem
are complete. Post each artifact to the ticket before the next stage.
The self-review hook will block your push if these are missing.

PIPELINE
        fi
    fi
fi
