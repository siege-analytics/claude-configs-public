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
