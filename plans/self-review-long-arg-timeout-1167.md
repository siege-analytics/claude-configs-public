---
ticket_refs:
  - siege-analytics/claude-configs-public#1167: self-review posted to the ticket before push
---

# Self-review: long literal operand lists in mutation-gate target resolution

Ticket: siege-analytics/claude-configs-public#1167
Review tier: C (enforcement code: `hooks/lib/resolve-think-gate.py`)

## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Working as: software engineer, tech lead
Goal source: #1167
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1167` → BLOCK (the operator-authored body lacks literal Context/Goal/Design/Assumptions headings). Handled by the Exemption block below; the coordinating hub directed not to amend the operator's ticket body.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780575489
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780574482
Project-contribution: agents can run one long literal copy/touch/chmod command under the mutation gate instead of splitting it into hand-sized chunks, with scope enforcement unchanged and git subprocess cost independent of operand count.

Assumptions that must hold:
- A git toplevel for one canonical, symlink-resolved existing directory is constant within one hook invocation (same process, same git environment).
- `_same_repo(a, b)` is a pure function of (a, b) within one invocation, except that transient origin-read failures only produce False (stricter).
- Only git's own positive exit status is a definitive "no toplevel"; timeouts, launch failures and negative (signal) exits are transient.

## Pre-implementation comprehension
Posted before any source edit: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231 (Junior task description, Senior adversarial checklist, Investigation fact sheet, Pre-mortem). The pipeline writer computed junior_found, senior_found, investigate_posted and premortem_posted as true at 2026-11-10 15:54:52 CST before implementation began.

## Peer review

- writing-code:2 (no issue refs in code comments): added comments and docstrings describe behavior. `git diff -U0 hooks/lib/resolve-think-gate.py | grep -c "^+.*#[0-9]"` → 0; the new test files → 0 matches for `#[0-9]`.
- writing-code:3 (no speculative abstraction): `_nearest_directory` and `_toplevel` each have two callers (`_target_repo` and the per-call cache in `select_task`).
- writing-code:7 / writing-code:13 (no silent swallowing; consistent failure contract): `_toplevel` keeps develop's catch-all-to-empty result and adds an explicit definitive flag; `_target_repo` returns exactly what develop returned.
- writing-code:15 (blocking I/O declares a timeout): the git call keeps `timeout=3`.
- writing-tests:1 (tests fail if behavior breaks): on unmodified develop 8043c583 the new file reports "FAILED (failures=8)" for 13 tests: 6 test methods fail (8 failure records with the 3 transient subtests), all performance/cache, and the 7 scope-guard methods pass (50 operands 11.65 s with 650 git calls; 182→1300 calls for 14→100 operands; same-origin checkouts 98→700; 5 toplevel lookups where 1 is expected). On the change → 13 passed. The signal-killed-git sibling case was also RED against the change's own first classification (a nested foreign-repository sibling was allowed) before the fix to `error.returncode > 0`.
- writing-tests:4 (mock fidelity): end-to-end cases run the real `hooks/bash/universal-mutation-gate.sh` with a counting git shim; unit cases patch only `subprocess.check_output` for the `rev-parse --show-toplevel` argv and pass every other git call through to real git.
- writing-tests:5 (every except fires): `CalledProcessError` positive (reused), negative (retried), `OSError` and `TimeoutExpired` (retried) are each forced by a unit case.
- writing-tests:7 (acceptance criteria have falsifiers): AC1 → `test_fifty_operand_copy_is_allowed_within_half_the_hook_timeout` (< 5.0 s) and the two scale-invariance cases; AC2 → `test_one_out_of_scope_operand_denies_the_whole_command`.
- writing-tests:8 (shared-function changes are caller-covered): `select_task` callers (resolve_action local/remote/review/metadata branches, `select_metadata_post_task`) are exercised by the affected suites listed in Quantified claims, run on both develop and the change.
- Gate 1 syntax: `python3 -m py_compile hooks/lib/resolve-think-gate.py hooks/_test/long_operand_resolution_1167.py` → exit 0; `bash -n hooks/_test/long_operand_resolution_1167.test.sh` → exit 0; `python3 bin/build.py --check` → "Build check complete."
- Gate 2 tests: new file → 13 passed; full hook suite → 76 PASS / 1 FAIL (environmental, identical on develop; see Quantified claims).
- Gate 3 docs: N/A, no documented behavior changed. Gate 4 notebooks: N/A.

## Lead review

- Did this fix the problem or move it? Fixed at the source. The operand-scaled loop in `select_task` now asks git once per distinct canonical directory and once per distinct (repo_root, toplevel) pair, and builds diagnostics only for the target that ends unowned. The same fixture and driver before/after: N=50 10.80 s / 650 git calls → 0.36 s / 3.
- Affirmative standard, scope enforcement (software engineer, tech lead): allow/deny verdicts are unchanged. Negative cases pass on develop and on the change: one out-of-scope operand, an out-of-scope destination, a destination symlink escaping scope, a nested foreign repository inside scope, operands split across two owned repositories through a symlinked directory, and an unowned repository listing all four rejected gates.
- Dismissals examined: hostile S3-1 (a cached transient False) is accepted because it can only deny. S3-4 (no golden diagnostic test) is accepted because diagnostics are built from the same inputs in the same gate order, and the existing diagnostic-asserting suites pass on the change.
- Blast radius: one module and three functions (`_target_repo` refactored into `_nearest_directory` + `_toplevel`, plus `select_task`). It runs on every gated mutation once installed. Installation is a separate post-merge step (`.claude/deploy-model` is merge-then-deploy) and is not part of this change.
- Approach fit: memoization keeps the existing resolution order and messages. Raising the hook timeout would hide the cost; checking scope before repository identity would change which diagnostics appear.
- Sequencing assumption: no caller relies on per-target git re-evaluation within one call. Verified by reading every caller.
- Post-mortem applicability: a performance defect with no prior shipped fix, not a regression; no post-mortem trigger.

## Inventoried shapes
Added after the work commit 834e18ab was pushed. That commit's message lacks the `Inventoried-shape:` trailer the installed self-review hook requires for executable diffs. Pushed history is not amended, so this record and the follow-up commit's trailer carry the measurement. All measurements predate the first source edit unless marked.
- Topology (repository identity per target), measured on develop 8043c583 with a git PATH shim and three own-session gates in another repository: 13 git subprocesses per operand (1 `rev-parse --show-toplevel` + 2 `_same_repo` origin reads + 2 `_scope_diagnostic` origin reads per foreign gate). Same-origin checkouts: 7 per operand (`AssertionError: 98 != 700`, measured after the edit against the unmodified develop checkout).
- Config-state: candidate gate JSON `repo_root` / `scope_paths` are read per candidate and are unchanged by this work.
- Branch base: develop 8043c583 (`git rev-parse origin/develop FETCH_HEAD` after `git fetch origin develop` → 8043c583b81f976c5bc95d620fe4212921c7dfb3 for both, immediately before commit).
- Data-shape, plan-shape, version-resolution: N/A (no data stores, query plans or dependency resolution touched).

## Self-hosted gate disclosure
The worktree's `.claude/settings.json` registers repo-relative hooks (`hooks/bash/universal-mutation-gate.sh`, `hooks/resolver/pipeline-state-guard.sh`). From the first edit of `hooks/lib/resolve-think-gate.py` onward, the authoring session's own mutation-gate decisions partly ran the modified resolver, so every local ALLOW after that edit is self-hosted and is not independent evidence of safety.

Independent evidence is limited to:
- the RED reproduction on unmodified develop 8043c583, run before any source edit;
- the final test file and the affected suites run against an unmodified develop 8043c583 checkout;
- hosted CI on the pushed head;
- the cross-family review on the PR.

## Known pre-existing finding (not in this diff)
Hostile S2-2: when `rev-parse --show-toplevel` fails, `expected_repo` is empty and `select_task` skips the repo_root comparison for that one target. A transient git failure can therefore let a foreign-repository gate authorize that single target. This exists on develop and is not widened here; `test_signal_killed_git_cannot_skip_the_repository_check_for_siblings` pins that it no longer spreads to siblings. The coordinating hub drafted a separate fail-open ticket for it; it is kept out of this diff.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L1 | P2 | Hostile S2-1: a signal-killed git (negative CalledProcessError) was cached as definitive, letting sibling targets skip the repository check. | fixed |
| L2 | P2 | Hostile S2-2, pre-existing: any rev-parse failure skips the repository comparison for that target. | hub-drafted separate ticket (outside this diff) |
| L3 | P3 | Hostile S3-1: a cached transient False from an origin read applies to later targets (deny direction only). | noted |
| L4 | P3 | Hostile S3-4: diagnostic text/order is not pinned by a golden test. | noted |
| L5 | P3 | About ten python3 launches per Bash call in universal-mutation-gate.sh (fixed cost, independent of operand count). | noted |

## Test plan
- `bash hooks/_test/long_operand_resolution_1167.test.sh` on the change and on unmodified develop (observed: 13 passed vs "FAILED (failures=8)").
- Full `hooks/_test/*.test.sh` loop mirroring CI after `python3 bin/build.py`.
- The 21 resolver/gate-affected suites on unmodified develop for comparison.
- Before/after timing with first-surge's driver (14/42/50/100 operands, git-shim counts).

## Quantified claims
- "N=14/42/50/100: 3.31/9.10/10.80/25.28 s, 182/546/650/1300 git calls on develop" -- `python3 debug/repro_1167.py <develop-8043c583 checkout> develop-8043c583 14 42 50 100` (run before any source edit) → the four in-scope lines quoted.
- "0.52/0.35/0.36/0.40 s, 3 git calls each after the change" -- the same command on the changed checkout → the four in-scope lines quoted; out-of-scope lines exit 2.
- "FAILED (failures=8) for 13 tests on develop; 6 methods fail, 7 pass" -- `python3 debug/develop-base/hooks/_test/long_operand_resolution_1167.py` (develop 8043c583 checkout, `git status --porcelain` → only `?? hooks/_test/long_operand_resolution_1167.py`, identical by `cmp`) → "Ran 13 tests in 109.803s / FAILED (failures=8)"; failing methods: fifty-operand, scale-invariance, same-origin (98 != 700), git refusal reuse, one toplevel lookup, transient retry (3 subtests).
- "13 passed" -- `python3 hooks/_test/long_operand_resolution_1167.py` → "Ran 13 tests ... OK".
- "76 PASS / 1 FAIL" -- `bash debug/run_hook_suite.sh final` (CI loop mirror) → 77 files, single failing file `hooks/_test/ca_enforcement_runtime.test.sh`.
- "ca_enforcement_runtime fails identically on develop" -- `bash debug/run_one.sh <develop checkout> hooks/_test/ca_enforcement_runtime.test.sh` → "Results: 12 passed, 4 failed" (the same four F4 / Craft-ancestry cases; the local process ancestry is a real Craft host).
- "affected suites on develop" -- `bash debug/run_subset.sh <develop checkout> base` → "[base] all 21 affected suites passed." (`metadata_comment_reporting` has no own `.test.sh`). The same 21 files are PASS in the 76-PASS full run on the change.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| think-gate claim FAILED (BRE grep error on `\(`) | did not dry-run the claim's grep pattern | 5 s | 1 turn | 1:12 |
| investigate-gate STALE after a think-gate edit | edited think-gate after investigate-gate | 2 s | 1 rewrite | 1:30 |
| hostile S2-1 (signal exit cached as definitive) | treated every CalledProcessError as definitive without checking negative return codes | 1 min | fix + 3 tests + suite restart | 1:20 |
| full suite restarted on final code | started the suite before hostile review returned | 0 | ~15 min suite time | n/a |
| issue refs removed from new comments (writing-code:2) | did not re-read the shelf before writing comments | 1 min | 4 comment edits | 1:4 |
| hosted CI "Generated source authority and drift": stale `catalog/skills-inventory.json` after adding the test files | ran `bin/build.py --check` locally but not `bin/generated-source-authority.py --check`, which CI runs separately | 3 s | CI cycle + regeneration commit | 1:60 |
| PR create blocked: work commit lacks `Inventoried-shape:` trailer | read the repo copy of the trailer contract but not the installed hook's v2.4 check before committing | 1 min | follow-up commit (pushed history not amended) | 1:10 |

## Evidence-predates-work
Artifact: plans/self-review-long-arg-timeout-1167.md
First-added commit: this normal author commit (the artifact is committed together with the work).
Work commit: assigned at commit time after the tests above.
Verification: this artifact is post-work. The pre-edit evidence is the design/investigation/pre-mortem comment https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231 and the develop 8043c583 reproduction, both of which predate the first source edit. No historical committed pre-mortem or retroactive enforcement is claimed.

## Exemption: evaluate-ticket fitness sections
Reason: the operator authored the ticket body in the bug-report template (Summary / Intended outcome / Starting conditions / Observed outcome / Acceptance criteria / QA). It carries the goal and falsifiable acceptance criteria, but not the literal Context/Goal/Design/Assumptions headings the checker looks for. The coordinating hub directed that the operator's body not be amended; the design and assumptions live in the posted Tier C comment.
Evidence: `bash scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1167` → "BLOCK ... missing sections: Context,Goal; no /think design-note reference; no '## Assumptions' block". Design and assumptions: https://github.com/siege-analytics/claude-configs-public/issues/1167#issuecomment-6780266231
Falsification: the exemption is wrong if the ticket's acceptance criteria (AC1: 50-operand cp within half the 10 s hook timeout; AC2: one out-of-scope operand still denies) are not what `hooks/_test/long_operand_resolution_1167.py` asserts, or if the operator rejects the posted design as the ticket's design.
