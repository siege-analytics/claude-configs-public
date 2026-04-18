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
# - Keep it short: we only inject the resolver's task-pattern table + the
#   universal checks, not the full document. The agent can `cat` the full
#   RESOLVER.md if needed.
# - Fail-open: if the file is missing, emit a warning but don't block the
#   prompt.

set -euo pipefail

RESOLVER="${CLAUDE_RESOLVER_PATH:-$HOME/git/electinfo/claude-configs-public/RESOLVER.md}"

if [ ! -f "$RESOLVER" ]; then
  echo "[resolver-hook] RESOLVER.md not found at $RESOLVER — skills enforcement not injected." >&2
  exit 0
fi

cat <<EOF
<skill-resolver>
The skill resolver is ACTIVE for this session. Before any non-trivial action:

1. Scan the task patterns in $RESOLVER
2. If a pattern matches, READ the mapped SKILL.md in full before acting
3. Apply the universal pre-action checks regardless of whether a pattern matched

Universal checks (always):
- Catalog-first: if the action touches data under a catalog, go through the catalog
- Brain-first: check existing state before recreating
- Test-before-bulk: ≥20 items runs a 3–5 item test first
- Ticket-required: non-trivial work has a ticket
- Branch-correct: write on feature branch, never main/master/develop
- No-attribution: never add Claude/AI attribution to commits or public content
- Measure-twice: confirm destructive actions before running

Full resolver: cat $RESOLVER
Skills: ls ~/git/electinfo/claude-configs-public/skills/ and ~/git/electinfo/electinfo_claude_skills/skills/
</skill-resolver>
EOF
