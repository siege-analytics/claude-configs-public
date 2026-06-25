---
ticket: "#468"
scope: "hooks/resolver/review-gate-guard.sh, skills/cross-review/SKILL.md, skills/self-review/SKILL.md"
---

# Self-Review — #468 review-gate signal file + hook

## Junior Assessment

**What changed:** Added the review-gate infrastructure — a signal file
+ checking hook + skill lifecycle instructions — so that hostile reviews
automatically trigger re-review when the author pushes fixes.

Three files:

1. **`hooks/resolver/review-gate-guard.sh`** — UserPromptSubmit hook.
   Checks for `review-gate.json` signal file. If the current branch has
   new commits since `reviewed_commit`, emits a re-review directive.
   Works cross-runtime (git + python3 only).

2. **`skills/cross-review/SKILL.md`** — new "Review-Gate Lifecycle"
   section. Instructs reviewers to write the signal file on
   request-changes and delete it on approve.

3. **`skills/self-review/SKILL.md`** — new Gate 5 (review-gate check).
   Pre-push verification that no unresolved review-gate blocks the push.

## Lead Assessment

**Pattern is proven:** This is the same infrastructure as think-gate
(signal file + guard hook). The pattern has been in production since
#262 and works reliably.

**Cross-runtime verified:** The hook uses only `git`, `python3`, and
file I/O. No Craft Agent primitives. Signal file search order:
env var → workspace root → repo root `.review-gate.json`.

**Fail-open is correct:** Missing signal file = silent exit. This
avoids blocking workflows that don't use hostile review. The gate only
activates when a reviewer explicitly writes the signal.

**Commit comparison is robust:** Uses full SHA from `git rev-parse HEAD`
compared to `reviewed_commit`. Handles prefix matching for short SHAs.

## Trivial-investigation declaration

Extending an existing infrastructure pattern (think-gate) to a new
domain (review). No new dependencies. No architectural decisions.

## Trivial pre-mortem declaration

Additive-only: new hook file, new skill sections. No existing behavior
changes. The hook is silent when no signal file exists.
