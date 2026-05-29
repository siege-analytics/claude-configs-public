#!/bin/bash
# UserPromptSubmit hook — inject the RESOLVER into active context on every prompt.
#
# Why: the RESOLVER at the repo root is only useful if the agent consults it
# BEFORE acting. Loading it at session start decays — by turn 20 the agent
# may have "forgotten" what patterns map to which skills. This hook keeps
# the resolver at the top of working context on every user turn.
#
# Design notes:
# - Output format: a plain text block that Claude sees as part of the
#   conversation. Not a tool result — just raw injection.
# - The universal checks list and the Failure handling routing rows are
#   EXTRACTED LIVE from RESOLVER.md at every hook invocation, not hard-
#   coded. This closes the divergence loophole from claude-configs-public#192:
#   if RESOLVER.md gains a new universal check or a new failure-handling
#   row, the hook output reflects it on the next UserPromptSubmit without
#   a hook edit.
# - The intro (think gate + 1/2/3 instructions) stays static — it names
#   the hook's contract with the agent, not the resolver's content.
# - Fail-open: if RESOLVER.md is missing, emit a warning but don't block
#   the prompt.

set -euo pipefail

RESOLVER="${CLAUDE_RESOLVER_PATH:-$HOME/git/electinfo/claude-configs-public/RESOLVER.md}"

if [ ! -f "$RESOLVER" ]; then
  echo "[resolver-hook] RESOLVER.md not found at $RESOLVER — skills enforcement not injected." >&2
  exit 0
fi

# Extract the "Universal pre-action checks" section, line by line.
# Section is delimited: starts at the heading, ends at the next "---"
# horizontal rule per the canonical RESOLVER.md structure.
UNIVERSAL_CHECKS=$(awk '
    /^## Universal pre-action checks/ { flag=1; next }
    /^---/ && flag                    { flag=0 }
    flag && /^[0-9]+\. /              { print }
' "$RESOLVER")

# Extract the "Failure handling" task-pattern routing rows (the table body).
# Section is delimited by "### Failure handling" -> next "### " heading.
# Strip the heading + intro paragraph; keep the table content.
FAILURE_HANDLING=$(awk '
    /^### Failure handling/ { flag=1; next }
    /^### /                 { if (flag) flag=0 }
    flag                    { print }
' "$RESOLVER")

cat <<EOF
<skill-resolver>
The skill resolver is ACTIVE for this session.

>>> THE FIRST GATE IS think <<<

Before ANY non-trivial action (feature, refactor, architecture change,
cutover, schema change, >30min task) you MUST read
skills/thinking/think/SKILL.md and produce a design note. Every
catalog-bypass, premature cutover, and half-designed pipeline this
resolver prevents traces back to skipping this step. think is
not a pattern to match — it is the gate before everything else.

For the task itself:
1. Scan the task patterns in $RESOLVER
2. If a pattern matches, READ the mapped SKILL.md in full before acting
3. Apply the universal pre-action checks regardless

Universal pre-action checks (extracted live from $RESOLVER):
$UNIVERSAL_CHECKS

Failure handling (extracted live from $RESOLVER):
$FAILURE_HANDLING

Full resolver: cat $RESOLVER
Skills: ls ~/git/electinfo/claude-configs-public/skills/ and ~/git/electinfo/electinfo_claude_skills/skills/
</skill-resolver>
EOF

# --- Pipeline status: scan for plan artifacts and warn on incomplete chains ---
# Scan locations: CRAFT_AGENT_PLANS_PATH (session plans) and CWD/plans/ (repo plans).
# Only emit the warning if think-*.md files exist (no noise otherwise).

PLANS_DIRS=""
[[ -n "${CRAFT_AGENT_PLANS_PATH:-}" ]] && [[ -d "$CRAFT_AGENT_PLANS_PATH" ]] && PLANS_DIRS="$CRAFT_AGENT_PLANS_PATH"
[[ -d "plans" ]] && PLANS_DIRS="$PLANS_DIRS${PLANS_DIRS:+ }plans"

if [[ -n "$PLANS_DIRS" ]]; then
    # shellcheck disable=SC2086
    THINK_FILES=$(find $PLANS_DIRS -maxdepth 1 -name 'think-*.md' 2>/dev/null | head -10)

    if [[ -n "$THINK_FILES" ]]; then
        # Check for downstream artifacts (any, not ticket-matched — v1)
        # shellcheck disable=SC2086
        HAS_INVESTIGATE=$(find $PLANS_DIRS -maxdepth 1 -name 'investigate-*.md' 2>/dev/null | head -1)
        # shellcheck disable=SC2086
        HAS_PREMORTEM=$(find $PLANS_DIRS -maxdepth 1 \( -name 'pre-mortem-*.md' -o -name 'premortem-*.md' \) 2>/dev/null | head -1)
        # shellcheck disable=SC2086
        HAS_SELFREVIEW=$(find $PLANS_DIRS -maxdepth 1 -name 'self-review-*.md' 2>/dev/null | head -1)

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
