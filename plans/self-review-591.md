---
ticket_refs:
  - siege-analytics/claude-configs-public#591: open
type: self-review
---

## Self-review for #591: stderr redirect false positive

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #591
Plan reference: plans/pre-mortem-591.md
Pre-author-inventory: NONE
Trivial-against-state: single-line regex refinement in existing MUTATION_INDICATORS array; no new state surfaces, no new code paths
Investigate-artifact: investigate-gate.json (workspace signal file)
Pre-mortem-artifact: plans/pre-mortem-591.md
Hostile-review-artifact: WAIVED (single-line regex fix, no prose-only content)
Project-contribution: Eliminates false-positive mutation blocks on commands
  using stderr redirection, restoring normal workflow for any command that
  suppresses errors via `2>/dev/null` or merges streams via `2>&1`.

## Pre-implementation comprehension

**Current behavior:** The MUTATION_INDICATORS pattern `>[^ ]|> |>> ` matches
any `>` followed by a non-space character, including `2>/dev/null` (the `>`
is followed by `/`) and `2>&1` (the `>` is followed by `&`). Commands like
`ls /path 2>/dev/null` are classified as mutations and blocked during the
implementing status.

**Intended behavior:** Stderr redirects (`2>/dev/null`, `2>&1`, `2> /dev/null`,
`2>> errlog`, `&>/dev/null`, `&>> combined`) do not trigger COMPOUND_MUTATION.
Stdout redirects (`> file`, `>> file`, `>file`) still trigger it.

**Steps:** Single-line edit to line 103 of `hooks/bash/universal-mutation-gate.sh`.
Prefix each of the three redirect sub-patterns with `(^|[^0-9&>])` to exclude
redirects preceded by a digit (FD number), ampersand (`&>`), or another `>`
(second `>` in `>>`).

**Success criteria:** 19 regex test cases pass (7 stdout match, 6 stderr skip,
6 edge cases). All 19 existing destructive-guard tests pass.

**What could go wrong:** Explicit FD-1 stdout redirects (`1>file`) are no
longer caught. Acceptable trade-off: they are rare and the conservative
approach avoids complexity.

## Peer review (the Junior's checklist)

Syntax check: `bash -n` passes on universal-mutation-gate.sh
Test suite: 19 destructive-guard tests pass (exit 0)
writing-code: single-line regex refinement in MUTATION_INDICATORS array; prefixes three redirect sub-patterns with `(^|[^0-9&>])` to exclude FD-prefixed redirects
writing-claims: 1 file modified (hooks/bash/universal-mutation-gate.sh), 1 line changed; all counts verified in Quantified claims section

## Lead review

**Domain: software engineering**

The fix correctly narrows the mutation-indicator regex. The class of false
positives (stderr redirects) is fully covered by the `[^0-9&>]` exclusion.

**Approach fit:** Correct. Using a negated character class before `>` is the
right ERE-compatible alternative to lookbehinds (which POSIX ERE does not
support). Pre-mortem Tiger 2 identified this constraint; the implementation
addressed it.

**Blast radius:** Minimal. Only the redirect-detection sub-patterns changed.
The `cat .* >` and `tee ` patterns are untouched. All existing safe-patterns
and mutation-indicators continue to work identically.

**Sequencing assumption:** None. This is a standalone fix with no dependencies
on other in-flight tickets.

**Known limitation accepted:** `cat file 2>/dev/null` still matches via the
separate `cat .* >` pattern. This is a different class of false positive
(cat-specific) and would be a separate ticket if it causes problems in
practice.

## Findings

No findings.

## Quantified claims

- "19 regex test cases pass" — manual bash test script with `check_match`
  function → "Results: 19 passed, 0 failed"
- "19 destructive-guard tests pass" — `bash hooks/_test/destructive_bash_guard.test.sh`
  → "Results: 19 passed, 0 failed"
- "7 stdout match, 6 stderr skip, 6 edge cases" — test script sections:
  7 cases under "SHOULD match", 6 under "should NOT match", 3+3 under
  "Edge cases" and "Additional edge cases"

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| First regex attempt missed `2>>` and `&>>` | Did not trace the second `>` in `>>` matching the single-`>` pattern | 30s to run test | 2 min to diagnose and add `>` to exclusion class | 4x |

## Evidence-predates-work

Artifact: plans/self-review-591.md
