# Self-review: issue #993 catalog guard invocation classification

## Assumptions

Domain(s): software engineering

Geospatial cross-cut: no

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/993

Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 'siege-analytics/claude-configs-public#993'` → `BLOCK` because the reporter-form issue lacks the repository template headings (`Context`, `Goal`, `Acceptance`), a `/think` design reference, and an `## Assumptions` block.

Plan reference: `plans/pre-mortem-993-catalog-guard.md`

Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/993#issuecomment-6184547090

Investigate-artifact: issue #993 body plus exact-base reproduction matrix in this artifact.

Pre-mortem-artifact: `plans/pre-mortem-993-catalog-guard.md`

Hostile-review-artifact: `plans/hostile-review-993-catalog-guard.md`

Project-contribution: restore the blocking catalog boundary for direct/wrapped object copies while removing raw-string prose false blocks, with installed-consumer and Tier C dependency evidence.

### Goal-source exemption

Reason: issue #993 is a detailed external-style defect report rather than a repository template ticket. Reformatting the reporter's body would alter provenance without improving the observable acceptance contract.

Evidence: the issue names the exact hook, legacy first-token gate, unreachable object-copy pattern, concrete false-negative/false-positive commands, wrapper/pipeline expectations, direction-blind policy, extraction-control hazard, and a 20-case result target. The exact base reproduction produced policy `10/20` with extraction `20/20`.

Falsification: this exemption is invalid if any implementation decision lacks an observable expectation in the issue or pre-mortem, or if the final matrix cannot reproduce the recorded `10/20 → 20/20` transition.

## Pre-implementation comprehension

**Current behavior.** At exact reproduction base `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`, direct and wrapped `aws`/`mc` copies bypass the first-token allowlist, while executor-prefixed commands can block on quoted write prose. The reconstructed 20-case matrix confirms `10/20` policy matches with `20/20` exact nonempty extraction.

**Intended behavior.** Block supported executable writes/copies regardless of evidenced wrapper, pipeline, payload, substitution, heredoc, or stdin transport; allow quoted prose and non-executing consumers; preserve conservative direction-blind copy matching and all existing Python/Spark/kubectl block paths; fail closed when extraction/classification dependencies fail.

**Steps.** Separate raw-command classification into a non-evaluating Python helper; wire the hook fail-closed; add source and full-consumer regressions; obtain hostile acceptance; merge current develop; classify the decision-changing helper narrowly Tier C under F4; run matrix, fuzz, full suite, and package canaries.

**Success criteria.** Current matrix `20/20`, exact extraction `20/20`; focused suite and all repository suites green; no eval/shell execution primitives; both built consumer packages exhibit block/pass canaries; helper computes Tier C and rejects declared B in direct/modify/delete/rename shapes.

**Risks.** Approximate shell parsing can over-block prose or miss dataflow/redirection precedence; recursive modeling can diverge or execute input; copied hooks can silently lose extraction; a new helper can fall below the F4 review boundary.

## Senior adversarial checklist

1. The initial description under-specified redirection precedence, fd duplication, producer/consumer flow, and nested process substitutions; hostile review exposed each class.
2. The result is observable: named commands either exit 2 with a policy reason or exit 0, and extraction is independently exact/nonempty.
3. Parser implementation did not displace consumer packaging, F4 classification, or fail-closed dependency checks; all are independently tested.
4. Develop moved during work; it was merged without force at `f97d194fedf1eda053a16e938851c6151f308d72`, then policy/evidence were reconciled.
5. Prior work read: issue #993, `catalog-guard.sh`, hook README/tests, workflow, self-review skill, F4 audit/policy/tests, and F4 evidence examples.
6. Environment is the selected worktree on `fix/993-catalog-guard-invocation`; target is draft PR to `develop`, never `main`.
7. Negative cases cover quoted prose, malformed syntax, override ordering, consumed stdin, unknown files, dependency failures, and declared-B rejection.
8. The class—not one command—is addressed across direct/wrapped/pipelined/payload/substitution/source-consumer forms with bounded explicit models.
9. Done means draft PR evidence and reporter exact-SHA re-review, not merely a local commit.
10. Pre-committed non-skips: hostile ACCEPT, exact matrix, deterministic fuzz, full suite, package canaries, F4 shape coverage, hosted checks, external exact-SHA review.

## Test plan

1. Focused source/consumer suite with exact extraction controls and fail-closed dependency fixtures.
2. Exact 20-case base/current matrix.
3. Seeded malformed-input determinism/crash fuzz.
4. Static shell/Python/diff checks and execution-primitive scan.
5. F4 risk-policy graph and staged modify/delete/rename/declared-B suite.
6. Current workflow's full build, 18 Python fixture modules, authorities, metrics, package/layout validators, and canaries.
7. Every hook test file with accumulated failures.
8. Two-package post-build catalog and Tier C canaries.

## Peer review

- **Parsing safety:** `classify-catalog-command.py` imports no subprocess module and calls no `eval`, `exec`, `os.system`, or `shell=True`; parsed text is data only.
- **Invocation correctness:** 182 focused cases cover preserved blockers, direct/wrapped copies, pipelines/control lists, shell/Python/kubectl payloads, substitutions, heredocs/here-strings, descriptor state, nested process flow, malformed syntax, and prose consumers.
- **Consumer correctness:** all 172 full-hook cases independently require the real extractor to return the exact nonempty command before evaluating policy output; missing classifier/extractor, malformed JSON, and empty command exit 2.
- **F4 boundary:** the policy regex names only `classify-catalog-command`; graph audit pins the exact catalog-guard assignment and Python operand; `review_risk_test.py` exercises direct, staged modification, deletion, rename source, and declared-B rejection.
- **Syntax/static:** shellcheck on both shell files, Python 3.13 byte compilation, `git diff --check`, and call/import-specific unsafe primitive scan all exit 0.
- **Suite:** full current-develop non-hook workflow command set exits 0; all 37 hook suite files pass.

## Lead review

**Affirmative standards.** Enforcement is fail-closed at dependency boundaries, parser input is never executed, matching is invocation-scoped rather than raw-string-scoped, existing conservative direction policy remains, and every quantified extraction result is independently controlled. F4 cannot be downgraded merely by moving/deleting the helper.

**Approach fit.** A standalone bounded parser is justified because shell regexes cannot distinguish executor payloads from grep/git/editor prose or model evidenced dataflow. The implementation intentionally models a finite supported subset and keeps malformed non-executable tails from inventing blocks while retaining complete earlier invocations.

**Blast radius.** One configured Bash PreToolUse hook, one packaged helper, its focused tests, and the review-risk policy/audit/metrics needed for the new decision edge. No installation, deployment, release, ready transition, PR merge, or `main` action.

**Sequencing assumption.** `develop` reconciliation and F4 classification must precede publication; hosted checks and exact-SHA external review follow push and draft-PR creation.

## Findings

No unresolved findings. Every valid hostile finding was fixed and regression-tested; final parser and full-candidate reviews returned `ACCEPT`.

## Quantified claims

- "Focused catalog suite: 182 passed, 0 failed; extraction 172/172" — `bash hooks/_test/catalog_guard.test.sh` → `Results: 182 passed, 0 failed`; `extraction control: 172/172 full-hook commands nonempty`.
- "Original matrix base 10/20, current 20/20, extraction 20/20 each" — exact-base/current matrix command → `SUMMARY base_policy=10/20 current_policy=20/20 base_exact_nonempty=20/20 current_exact_nonempty=20/20`.
- "Malformed fuzz deterministic and crash-free" — seed-993 fuzz → `classifier_cases=500 repeated=2 hook_cases=100 exits={0,2} tracebacks=0`.
- "18 Python fixture modules" — `find bin/_test -maxdepth 1 -name '*_test.py' | wc -l` → `18`; current workflow non-hook command sequence → `FULL_NON_HOOK_SUITE_PASS`.
- "37/37 hook files" — accumulated `hooks/_test/*.test.sh` runner → `HOOK_FILES_TOTAL=37 PASS=37 FAIL=0`.
- "F4 graph/shape suite" — `python3.13 bin/_test/review_risk_test.py` → `review_risk_test: PASS`.
- "Generated authorities" — checks → `198 sources, 804 artifact snapshots, 2904 generated file mappings`; kernel `6995 chars, 1749 estimated tokens`; inventory current.
- "Two package canaries" — built `claude-code` and `craft-agent` hooks → each `block=2 prose=0 tier=C`.
- "Tier C classification" — `python3.13 bin/review-risk.py --paths hooks/lib/classify-catalog-command.py --declared C` → `computed_tier: C`, `valid: true`; declared B exits 2 and reports `valid: false`.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---:|---:|---:|
| Repeated hostile parser findings | Initial finite model omitted several shell dataflow/descriptor interactions | One exact-input review + focused rerun per round | Added bounded model + regression per valid finding | High rework, high defect yield |
| Invalid stdout-duplication finding | Reviewer evaluated stale behavior | One direct reproduction | Added a passing regression; required fresh review | Low |
| Develop advanced to F4 | Original base predated policy boundary | Fetch/merge and authoritative F4 test | Narrow policy/graph/audit/metrics reconciliation | Moderate |
| First matrix reconstruction gave 13/20 and 0 extraction | Selected prose cases did not enter legacy gate; compared extractor print newline literally | One matrix run | Corrected case composition and normalized extractor-owned newline | Low |
| Unsafe primitive grep flagged parser string `exec` | Pattern matched data tokens, not calls | One grep | Refined to call/import-specific scan | Low |

## Evidence-predates-work

Artifact: `plans/self-review-993-catalog-guard.md`

First-added commit: `EVIDENCE_COMMIT_PENDING`

Work commit: `WORK_COMMIT_PENDING`

Verification: `git merge-base --is-ancestor EVIDENCE_COMMIT_PENDING WORK_COMMIT_PENDING; echo $?` → pending final commit IDs; must be 0 before push.

## Canary and rollback

Canary: build both consumer packages; direct managed copy exits 2 with the direct-copy reason; grep prose exits 0; packaged review-risk policy accepts declared Tier C for the helper. Both packages passed.

Rollback: revert the isolated implementation commit and its evidence-only follow-up if needed. Do not force-push. No install/deployment/release cleanup is required because none occurred.
