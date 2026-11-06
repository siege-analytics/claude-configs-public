# Review of explicit staging risk targets

## Assumptions

Goal source: siege-analytics/claude-configs-public#1174
Pre-mortem-artifact: plans/git-add-risk-targets-1174.md#pre-mortem
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1174

The Git index remains repository-owned. Risk targets are a separate view of a proved sole named-file staging action, not an alternate task scope. This feature is based on the reviewed parent #1161 candidate c4d2f8a; it must integrate after that parent. No installation, protected merge or global settings change occurred.

## Peer review

Independent source reviewer accepted the resolver-only runtime change and the positive/negative test coverage. Qualification retained: the helper observes current filesystem paths in a cooperative worktree, not an atomic Git index transaction or symlink-race guarantee. Existing repository Git configuration trust is unchanged.

## Lead review

The same repository ownership selection runs before risk calculation. Named prose can use its A floor, ordinary code B, enforcement/workflow/policy C, and the declared tier still raises the effective tier. Directories, missing/deleted files, symlinks, globs, pathspec syntax, configuration overrides, compounds, unknown flags and unproved dispatch retain the existing calculation. The actual tool cwd reaches the risk helper, and the existing Git prefix normalizer handles -C resolution. No task_actions path or authorization predicate changed.

## Test plan and evidence

The original baseline returned C for git add README.md solely from unrelated workflow/enforcement/policy paths; the behavior assertion failed as expected. An initial test helper also encountered the not-yet-added optional cwd interface; that TypeError is not represented as the behavioral red proof.

Ten focused tests passed in 8.806 seconds before the additional metadata-failure control; the final content-bound run must include that control. Existing repository ownership, proportional tiers, lone-commit targets and declared-tier tests passed. One selected existing case initially named the wrong unittest class; its corrected ResolverRecovery invocation passed. No failed selection is reported as a passing full suite.

Build check, normal full package build, source validator and both consumer hook validators passed. Generated source authority is current. Protected exact-head full CI is required before integration; no local full-suite pass or installed local-session success is claimed.

## Quantified claims

Ten focused methods passed in 8.424 seconds in /tmp/git-add-1174-focused-final.log. Five correctly selected existing methods passed in the first selected run; one incorrectly selected class/method produced a test-discovery error and its corrected ResolverRecovery invocation passed separately. These are focused checks, not a full-suite claim. Final native content receipts execute the actual selected suites again against committed source bytes.

## Canary and rollback

Real isolated hook fixtures prove named-file staging permission and retained B/C preparation, designing, wrong-binding, current-session and repository-owner boundaries. They never execute a real Git push. Default unsupported forms retain their previous conservative classification. Normal reviewed revert restores the prior implementation; no live runtime or settings were changed.

## Selected snapshot scanner

Selected staged scan completed with exit 1, nonclean, with 40 AST findings and no lexical findings. Raw output: /tmp/git-add-1174-scan.log. The unchanged resolver findings were already individually reviewed for parent #1161; they remain denial/unavailable sentinel returns or a pytest.raises test-locator convention that does not describe the CLI assertion suites. This is not a claim every exception branch was raised.

The new helper's handler returns None to select the pre-existing whole-repository risk calculation; it never returns authority or a lower tier. Its malformed-shell and unreadable-file negatives retain C in the workflow-bearing fixture. The scanner's writing-tests:5 expects pytest.raises in task_keyed_gates.py, whereas these handled errors are observed through effective risk and hook exit/diagnostics in git_add_risk.py. That convention mismatch does not establish missing user-visible failure checks and does not establish exhaustive branch coverage. Root reviewed and accepted the new handler as preserving the prior risk calculation and the parent scanner dispositions narrowly. Neither that acceptance nor the test-locator convention establishes exhaustive handler-branch coverage. Normal exact-head protected checks remain required before integration.
