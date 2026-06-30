# Pre-mortem: Skill-enforcement-gate (#449)

Ticket: #449

## Context

Add UserPromptSubmit hook that parses session.jsonl transcript for SKILL.md
Read receipts. Blocks via ca-enforcement-gate.sh wrapper when required skills
haven't been read.

## Tigers

**Tiger 1: session.jsonl parsing performance on large sessions**
**Severity:** MEDIUM
**Likelihood:** Low — benchmarked at 0.09s for 5740 lines
**Mitigation:** Python JSON parsing is O(n) with early-exit on first match.
If sessions grow past 50K lines, can switch to reverse-scan (tail) or
cache last-checked line number in a signal file. Current 0.1s overhead
is acceptable for a per-turn hook.

**Tiger 2: Bootstrapping — this commit touches .sh and .py files**
**Severity:** LOW
**Likelihood:** Certain — diff modifies hooks/resolver/*.sh and bin/build.py
**Mitigation:** Self-review artifact uses Hostile-review-artifact: WAIVED
with declaration block (same pattern as #470).

**Tiger 3: CRAFT_SESSION_DIR not available in all environments**
**Severity:** LOW
**Likelihood:** Medium — env var is Craft Agent specific
**Mitigation:** Hook exits 0 (fail-open) when CRAFT_SESSION_DIR is unset
or session.jsonl doesn't exist. Claude Code sessions use PreToolUse hooks
for enforcement, not this UserPromptSubmit gate.

## Implementation may proceed: yes

No launch-blocking Tigers.
