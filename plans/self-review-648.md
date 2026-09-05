---
ticket_refs:
  - siege-analytics/claude-configs-public#648
---

# Self-review: PR for #648 (pr-base-guard false positives)

## Assumptions

Working as: software engineer
Domain: shell hook (pr-base-guard.sh) + its bats-style scenario test file
Goal source: siege-analytics/claude-configs-public#648
Pre-author-inventory: `grep -n TRIGGER hooks/git/pr-base-guard.sh` returned line 37; the trigger regex was matching `gh pr create` as a substring anywhere in COMMAND including inside single-quoted body prose. `grep -n HEAD_BRANCH hooks/git/pr-base-guard.sh` returned line 142; the resolver was reading `git rev-parse --abbrev-ref HEAD` unconditionally rather than preferring an explicit `--head` arg.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below; failure surface is one shell hook with a paired test file, all in-scope failure modes covered by the 4 new regression scenarios)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates two false-positive classes in the develop-guard mechanical enforcement so operators can (a) file bug tickets whose body cites the CLI as prose and (b) open PRs with explicit head args from any working-tree branch. Restores discipline gate to its stated invariant (block feature-to-main) without producing spurious blocks on innocent operator surface. Ticket #648 originated from a session that had to bypass via `gh api` because of these exact bugs; removing them removes the class-2 enforcement-contradiction that motivated the bypass.

Trivial-against-state: this change edits only two files (hook + its paired test); no data, config, plan, or version-resolution surface is contacted. Data-shape: no schema/query/DataFrame touched. Config-state: no config file authored or consumed at runtime by this fix (the hook reads live command payloads; command-payload shape is invariant across the fix). Topology: no service/pod/path/dependency wiring changes. Plan-shape: no DAG/pipeline. Version-resolution: no dependency, pin, or lockfile touched.

## Post-mortem applicability

Not applicable per skills/post-mortem/SKILL.md's three triggers:
- Shipped implementation contradicting ticket hypothesis: no — this ticket had no shipped implementation to contradict; #648 was filed as a bug against pre-existing behavior.
- Pre-mortem Tiger materializing: no — no pre-mortem exists for this fix (trivial-investigation declared).
- Test failure revealing a shipped bug that passed self-review: no — the bug pre-dates any self-review; this fix ADDS the regression tests that would have caught it.

The commit subject begins with `fix(#648):` because the ticket type is bug-fix, not because it's a regression of a prior fix.

## Trivial-investigation declaration

Reason: ticket #648 already documented both bugs with file:line pointers and a reproducer session. The pre-author-inventory greps confirmed the pointers at HEAD and located the two logic sites needing edit. No additional discovery was required.
Cannot produce error: the fix is scoped to two identified functions inside one shell hook. Both changes have paired regression tests that fail on the pre-fix hook and pass on the post-fix hook.
Evidence: `git diff --stat` shows 2 code files + 1 self-review, no changes outside hooks/git/pr-base-guard.sh + hooks/_test/pr_base_guard.test.sh. `bash hooks/_test/pr_base_guard.test.sh` returns 35 passed 0 failed.
Falsification: not trivial if either regression test can be made to pass against the pre-fix hook by adjusting the test rather than the fix. Verified by manual revert of both edits: 4 tests failed as expected.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n hooks/git/pr-base-guard.sh` -> exit 0
- Gate 2 (tests): `bash hooks/_test/pr_base_guard.test.sh` -> "ALL PASS: 35 scenarios passed" (31 existing + 4 new for #648)
- Gate 3 (docs): N/A -- no doc pipeline; the hook's own header comment describes the enforced invariant
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical code): the sed-based quote-stripping was verified against a real payload in scenario (af). Not extrapolated from theory.
- writing-tests:1 (tests must fail on revert): all 4 new scenarios were confirmed FAILing against the pre-fix hook before the fix landed. Grep-verifiable: temporarily reverting the two edits produces the failures.
- writing-tests:5 (every except-block exercised): the two logic changes both have paired new tests. Scenario (af) covers the trigger-side fix; scenarios (ag)(ah)(ai) cover the head-resolver fix. Scenario (ai) is the negative-symmetry test that ensures --head arg wins in BOTH directions (an allowed cwd + disallowed --head must still block).
- writing-claims:1 (grep for siblings before declaring class complete): searched for other unquoted-content-scanning regex sites in `hooks/git/*.sh`; found `self-review.sh` and `branch-guard.sh` both have similar TRIGGER shapes but their scope is scoped narrowly (single-word matches) and the `gh issue create` false-positive shape doesn't apply to them because they don't scan for GitHub subcommand names. Class scoped to pr-base-guard.sh; no siblings.

## Lead review

- Junior solved the stated goal: yes. The two bugs #648 named ("false-positive on issue-body quoting" and "cwd branch used in place of --head arg") are both fixed and covered by regression tests.
- Junior over-scoped: no. The third symptom in #648 ("grep: empty (sub)expression") was not reproduced in my testing at HEAD; it may have been fixed in an intervening commit. No change made for that symptom. If it recurs, file a follow-up.
- Junior under-scoped: no. Both editable-branch failure modes named in the ticket now have paired tests + fixes.
- Standards affirmatively met: writing-code:5 (verified sed behavior on real payloads), writing-tests:1 (all 4 new tests confirmed red on pre-fix), writing-tests:5 (per-edit test coverage), writing-claims:1 (sibling scan).

## Quantified claims

Claim: "31 existing + 4 new = 35 scenarios."
Verified-by: `bash hooks/_test/pr_base_guard.test.sh` returns "ALL PASS: 35 scenarios passed."

Claim: "4 new tests fail on the pre-fix hook."
Verified-by: temporarily reverted both edits in a sandbox; test output showed `FAIL: 4 test(s) failed` with the 4 new scenarios listed. Restored the edits and re-ran -> ALL PASS: 35.

Claim: "sed-based quote-stripping handles both single-quoted and double-quoted body content."
Verified-by: scenario (af) uses single quotes; the regex also handles double quotes (`s/\"[^\"]*\"//g`), verified by manual test with a double-quoted body variant that produced the same PASS result. Not made into a formal scenario to avoid duplication.
