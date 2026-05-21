#!/bin/bash
# UserPromptSubmit hook — inject the RESOLVER into active context on every prompt.
#
# Why: the RESOLVER at the repo root is only useful if the agent consults it
# BEFORE acting. Loading it at session start decays — by turn 20 the agent
# may have "forgotten" what patterns map to which skills. This hook keeps
# the resolver at the top of working context on every user turn.
#
# Mid-session staleness detection (see claude-configs-public#169 comment):
# Skills may be updated (git pull / subtree sync) while a session is running.
# On each prompt turn we hash the RESOLVER and compare against the last-seen
# hash cached in /tmp. If it changed we emit a visible banner so the agent
# knows its context was refreshed from the updated files.
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

# Scope: this resolver, its skills, and its task patterns are written for
# electinfo work. Outside electinfo contexts (e.g., Craft Agent sessions for
# the moshi-ai workspace, satsuma-ai, Ringer-Sciences, etc.) the rules and
# skill paths don't apply. Only inject the resolver when the cwd is inside
# an electinfo workspace or the electinfo git checkout.
CWD="$(pwd)"
case "$CWD" in
  "$HOME"/git/electinfo*|"$HOME"/.craft-agent/workspaces/electinfo-*|"$HOME"/.craft-agent/workspaces/electinfo-*/*)
    : # in scope, continue
    ;;
  *)
    exit 0
    ;;
esac

if [ ! -f "$RESOLVER" ]; then
  echo "[resolver-hook] RESOLVER.md not found at $RESOLVER — skills enforcement not injected." >&2
  exit 0
fi

# --- Mid-session staleness detection ---
# Hash the resolver content. Compare against the cached hash from the last
# invocation. If they differ, the skills were updated mid-session; emit a
# refresh banner so the agent knows its context now reflects the new state.
HASH_CACHE="/tmp/resolver-last-seen-hash"
CURRENT_HASH="$(sha256sum "$RESOLVER" 2>/dev/null | cut -d' ' -f1 || echo "unknown")"

STALE_BANNER=""
if [ -f "$HASH_CACHE" ]; then
  CACHED_HASH="$(cat "$HASH_CACHE" 2>/dev/null || echo "")"
  if [ -n "$CACHED_HASH" ] && [ "$CURRENT_HASH" != "$CACHED_HASH" ]; then
    STALE_BANNER="
[SKILLS UPDATED MID-SESSION] The resolver and skills were updated since
this session started. This injection reflects the current state of the
files on disk. Rules and skill references below are up to date.
Specifically: verify-failure-premise Step 5 (post-error-revision trigger),
writing-rules:6 pre-fix pause, writing-rules:7 session-scale gate, and the
sibling-grep gate in think Step 1 may not have been in your earlier context.
"
  fi
fi
echo "$CURRENT_HASH" > "$HASH_CACHE"
# --- End staleness detection ---

cat <<EOF
<skill-resolver>
The skill resolver is ACTIVE for this session.
${STALE_BANNER}
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

Universal checks (always):
- THINK FIRST (the non-negotiable)
- Catalog-first: action on catalog-managed data goes through the catalog
- Brain-first: check existing state before recreating
- Verify-failure-premise: before debugging a reported failure, confirm it
  actually happened (durable-commit evidence), then trace the causal path.
  Step 5: if diagnosis falsifies a documented Assumption, run post-error-revision
  BEFORE writing the fix. See skills/verify-failure-premise/SKILL.md.
- Pre-fix pause (writing-rules:6): when any failure fires, ask out loud
  "What did I believe that this evidence contradicts?" If the answer names
  a durable artifact (skill / rule / ticket / hook / docstring / Trivial-change
  block), the post-error-revision block comes BEFORE the fix.
- Session-scale gate (writing-rules:7): N>=2 same-shape fixes in one session
  = warn + sibling-grep. N>=3 = hard gate, produce class-audit or revert to
  /think. Pairs-with relationships in skills are dependencies, not hints.
- Test-before-bulk: >=20 items runs a 3-5 item test first
- Ticket-required: non-trivial work has a ticket that passes evaluate-ticket
  (six criteria: title shape, sections, evidence, /think link, Assumptions,
  falsification). See skills/evaluate-ticket/SKILL.md.
- Branch-correct: write on feature branch, never main/master/develop
- No-attribution: never add Claude/AI attribution to commits or public content
- Measure-twice: confirm destructive actions before running

Full resolver: cat $RESOLVER
Skills: ls ~/git/electinfo/claude-configs-public/skills/ and ~/git/electinfo/electinfo_claude_skills/skills/
</skill-resolver>
EOF
