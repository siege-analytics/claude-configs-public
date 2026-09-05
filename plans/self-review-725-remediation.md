---
propagation-deferred: self-review for the citation-drift remediation on PR #725; propagates via same PR body
---

# Self-review: PR #725 remediation commit

## Assumptions

Working as: software engineer
Domain: doc-only citation-line-number fixes on skills/investigate/SKILL.md + plans/design-709.md
Geospatial cross-cut: no
Goal source: hostile-review of PR #725 at plans/hostile-review-725.md, Finding 1 (S3)
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 709` PASS at branch head
Plan reference: `plans/hostile-review-725.md` (same-session hostile review, author-self-review under operator authority)
Pre-author-inventory: greps `grep -n "shapes = data.get" hooks/resolver/investigate-gate-guard.sh` returned 212 and 411; `grep -n "for shape in shapes"` returned 226; `grep -n "if not shapes"` returned 214 and 412. These are the actual anchor lines at HEAD post-comment-block edit.
Investigate-artifact: `plans/fact-sheet-709.md` (from primary PR) + `plans/hostile-review-725.md` (this remediation)
Pre-mortem-artifact: `plans/pre-mortem-709.md` (from primary PR)
Hostile-review-artifact: `plans/hostile-review-725.md` (author-self-review; caveat re: fresh-agent absence documented in the file)
Project-contribution: eliminates line-drift in citations added by the primary #725 commit. The primary commit added 23 lines of guard-hook comment which shifted every subsequent line number by 23; the skill table and design table were not updated to reflect the shift.

## Trivial-investigation declaration

Reason: doc-only citation-line-number fix. Diff is 2 markdown files (skills/investigate/SKILL.md line 505; plans/design-709.md lines 38-39, 79). No hook behavior change; no test change; the 5 test scenarios pass at HEAD post-edit.
Evidence: `git diff --stat HEAD` shows 2 files, ~4 lines changed. Numbers derived by grep at HEAD. Tests re-run: 5 passed, 0 failed.
Falsification: not trivial if any citation is still wrong. Verified by grep at HEAD: `investigate-gate-guard.sh:214` (if not shapes for warning branch), `:411` (disposition validation shapes assignment), `:226` (spot-check loop start).

## Peer review

Findings 2, 3, 4 from hostile-review-725.md are NOT remediated in this commit:
- Finding 2 (python3 unguarded): near-zero practical impact, and adding a guard is out of scope for a citation-drift fix.
- Finding 3 (missing verifiedShapes-absent scenario): symmetric addition to scenario (c); worth doing but out of scope for a citation-drift fix. Deferred as opportunistic.
- Finding 4 ("hard block" precision): documentation-tightening rather than a fix; deferred.

Each remains in the hostile-review artifact for future reference or fresh-agent pickup.

## Quantified claims

Claim: "line-number citations for investigate-gate-guard.sh in the skill table + design note were off by ~23 lines because the primary #725 commit added 23 lines of comment above them."
Verified-by: `git show HEAD -- hooks/resolver/investigate-gate-guard.sh | head -80` at pre-remediation HEAD showed the comment block added at lines 22-73 in the file. Post-add anchors moved: `if not shapes:` (warning branch) from 191 to 214 (delta 23); disposition-check `shapes = data.get` from 388 to 411 (delta 23).

Claim: "the two off-file citations (universal-mutation-gate.sh:298, pipeline-state-guard.sh:173, self-review.sh:460) are correct at HEAD."
Verified-by: `grep -n findings hooks/bash/universal-mutation-gate.sh` returns 298 (first occurrence). Same for the other two.

Claim: "5 test scenarios pass at HEAD post-edit."
Verified-by: `bash hooks/_test/investigate_gate_schema.test.sh` returns "Results: 5 passed, 0 failed".

## Lead review

- Junior solved the stated goal: yes. The three inaccurate citations to `investigate-gate-guard.sh` in the skill table and design note are corrected to their actual anchor lines at HEAD.
- Junior over-scoped: no. Findings 2, 3, 4 from the hostile-review artifact were explicitly deferred as out-of-scope for a citation-drift fix; they remain documented in `plans/hostile-review-725.md` for future pickup.
- Junior under-scoped: no. All three drifted citations updated; test suite re-run to confirm no regression.
- Standards affirmatively met: writing-code:6 (doc-edit symmetry across the same-PR file that shifted the line numbers); writing-claims:2 (each corrected line number produced by grep at HEAD, output cited in Quantified Claims); writing-claims:8 (specific line-number counts each backed by grep).

## Rework ledger

- Cycle 0: initial primary PR #725 (bright-gust design + long-swan completion) landed citations against pre-comment-block line numbers.
- Cycle 1 (this commit): author-self-hostile-review at plans/hostile-review-725.md caught the drift; this commit is the remediation of Finding 1 only.

## Evidence-predates-work

The hostile-review artifact (plans/hostile-review-725.md) was authored before this commit's file edits. Grep evidence for anchor lines produced same-turn in the commit process. Test re-run happened after edits, before commit.
