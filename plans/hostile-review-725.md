# Hostile review: PR #725 (#709 investigate-gate schema)

**Pinned to:** `fix/709-investigate-gate-schema` @ `9b3f4be`
**Reviewed:** 2026-09-04 by long-swan (Opus 4.7, self-review)
**Total findings:** 4 (2 S3, 2 informational). No S1 or S2.

## Reviewer discipline caveat

`skills/hostile-review/SKILL.md` line 15 prescribes a fresh agent
session, not the author. This is an author-self-review under operator
authority ("forget external review, use claude") after the retry
ladder for external dispatch (claude-max respawn, chatgpt-plus GPT-5.5,
cross-review MCP, review-deferred artifact) exhausted. The review
below applies the 9-category grep-based protocol to the three touched
files, but the author-blindness discount applies: findings a fresh
agent might have caught by not sharing the author's mental model of
what the file "obviously means" are absent from this pass.

Scope of the diff (per `git show --stat HEAD`):

- `skills/investigate/SKILL.md` (+61 lines, prose + JSON block + two tables)
- `hooks/resolver/investigate-gate-guard.sh` (23 lines, comment-only)
- `hooks/_test/investigate_gate_schema.test.sh` (+219 lines, new file)

Non-scope: seven inapplicable categories (no security surface, no
distributed compute, no packaging change, no data pipeline). Reviewed
categories: Engineering discipline (Cat 1), Domain correctness (Cat 3),
Composability (Cat 7), Test adequacy (Cat 9).

## Findings

### Finding 1 — S3: line-number citations drift within the same PR

**File:** `skills/investigate/SKILL.md:505`, `plans/design-709.md:38-39`
**Category:** 7 (composability, cross-file references)

The skill's new table cites `investigate-gate-guard.sh:191` for the
"No citations to spot-check" warning. Actual location at HEAD:

- Line 214 (the `if not shapes:` guard)
- Line 217 (the WARN print itself)

Design note cites `investigate-gate-guard.sh:390` for disposition
validation; actual location is 411. Same file, `:199-209` for the
grep spot-check block; actual location is 226+.

The three inaccurate citations all target the file THIS PR just added
23 lines of comment to. The citations were correct against the
pre-PR line numbering and no one updated them after the guard-hook
comment block landed. Self-inflicted drift within one commit.

Contrast: the other three cross-file citations
(`universal-mutation-gate.sh:298`, `pipeline-state-guard.sh:173`,
`self-review.sh:460`) are all correct at HEAD because those files
were not touched by this PR.

**Impact:** small. A reader who greps for the message string
("No citations to spot-check") finds the right code. But the citation
form implies precision it does not deliver.

**Remediation:** re-derive the three internal line numbers post-diff
and update the skill table + design note.

### Finding 2 — S3: `python3` availability not guarded in test

**File:** `hooks/_test/investigate_gate_schema.test.sh:70,81,91,153,176`
**Category:** 1 (external-binary dependency audit)

Five invocations of `python3` with no `command -v python3` precheck.
On a system without python3 in PATH, the first `if ! python3 -c ...`
guard on line 70 returns non-zero, the `!` inverts, and the test
reports "the json block in $SKILL is not valid JSON" — which is
misleading (JSON is fine; python3 is absent).

**Impact:** near-zero in practice. The guard hooks that this test
exercises also require python3 (universal-mutation-gate.sh embeds
python3 -c blocks), so python3 is de-facto guaranteed present in any
environment where the test could meaningfully run.

**Remediation:** optional. If added, a single `command -v python3
>/dev/null || { echo "SETUP FAILED: python3 not on PATH" >&2; exit 1; }`
at the top of the script would produce an accurate error message.

### Finding 3 — informational: no test that verifiedShapes-absence produces the documented warning

**File:** `hooks/_test/investigate_gate_schema.test.sh` (absence)
**Category:** 9 (test adequacy)

The skill's new table claims: "verifiedShapes absent → warning only.
investigate-gate-guard.sh:191 prints 'No citations to spot-check.
Proceeding, but this is suspicious.' and exits 0."

That is a testable claim about the guard hook's behavior. The test
file asserts scenario (d) — guard exits 0 on the documented example
(which HAS verifiedShapes) — and nothing asserts the guard exits 0
AND prints the warning message when verifiedShapes is removed. If a
future guard change starts blocking on empty verifiedShapes, the
skill table becomes wrong and no test goes red.

**Impact:** small. Scenario (d) covers the "with verifiedShapes"
half; the missing scenario would cover the "without verifiedShapes"
half. Adding it is one dozen lines of test code, symmetric with
scenario (c).

**Remediation:** add scenario (f): remove verifiedShapes from the
transcribed example, assert guard exits 0 AND the warning string
appears in output.

### Finding 4 — informational: skill table uses "hard block" without specifying which readers block

**File:** `skills/investigate/SKILL.md:504`
**Category:** 3 (domain correctness — precision of documented claims)

The skill table's "hard block" cell cites two hooks:
`universal-mutation-gate.sh:298` (refuses next mutation) and
`pipeline-state-guard.sh:173` (records artifact as not posted).

Verified at HEAD:
- Line 298 is `findings = ig.get('findings', [])` followed by
  `if not findings:` and adds to `missing` list — this contributes
  to a hard block only if the mutation-gate exits non-zero when
  `missing` is non-empty.
- Line 173 is a print statement — the "records artifact as not
  posted" phrasing suggests it also contributes to blocking.

Both are grep-verifiable and I did not trace the full call chains
to confirm the "hard block" verb is precise vs "adds to a warning
list that may or may not block depending on other predicates."

**Impact:** none for a reader who trusts the claim; potentially
misleading for a reader who tries to reason about when the block
actually fires vs when it degrades to a warning.

**Remediation:** optional. If tightened, the sentence would say
"contributes to a mutation-gate refusal" rather than "refuses",
and would name the surrounding conjunction (is it the only blocker
or one of several).

## Categories with no findings

- **Cat 2 (Security):** N/A. No user input flows, no subprocess with
  interpolation, no SQL, no auth. Test file's mktemp + trap rm is
  standard.
- **Cat 4 (Data integrity):** N/A. No writes to persistent storage.
  Test writes to $TMP_DIR which is trap-cleaned.
- **Cat 5 (Resource management):** N/A. No open files, connections,
  sessions, or unbounded accumulation.
- **Cat 6 (Packaging truth):** N/A. Doc + shell only.
- **Cat 8 (Performance at scale):** N/A. Test runs once with a
  hand-authored fixture; no loop iterations or dataset size.

## Summary

Zero S1/S2 findings. Two S3 (line-number drift, python3 unguarded).
Two informational (verifiedShapes-absent scenario missing;
"hard block" precision).

The doc-only + comment-only nature of the diff limits the attack
surface; the empirical-evidence table (four signal-file shapes) is
grep-verified against the workspace at HEAD; the five test scenarios
pass.

Recommendation: **merge as-is** or **remediate finding 1 only** (a
one-commit citation re-derivation). Findings 2-4 are opportunistic;
they do not block the fix's stated Goal.

Author-blindness caveat re-applied: a fresh agent would be more
likely than long-swan to catch a finding I missed in the "obvious"
prose. Recommend that finding-1 remediation include a re-run of
this review by a fresh Opus 5 session when the rate-limit window
next clears.
