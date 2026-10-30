# Detached deployment fixture correction

Pre-mortem-artifact: plans/hostile-review-detached-deploy-fixture.md
Hostile-review-artifact: plans/hostile-review-detached-deploy-fixture.md

## Assumptions

GitHub checks out a detached candidate. A disposable source clone must establish its own accepted main ref; the outer checkout must not determine the fixture's ref naming.

## Peer review

Independent promotion_review reproduced detached HEAD to empty bare remote with HEAD:main: failure exit1. Creating local main and pushing HEAD:refs/heads/main succeeds exit0, with remote main exactly equal to the fixture commit. The inspected diff changes only disposable setup and explicit destination spelling. No production authority rule changes.

## Lead review

The real deployment fixture passed locally after correction, including untracked-input isolation, operator preservation, source mutation and corrupt-artifact refusal. The fixture explicitly detaches before naming main, exercising the CI starting condition on every run. Review-risk metrics remain current; generated inventory gained the test's ref-setup coverage entry.

## Quantified claims

PR1137 run41068717391 failed at the abbreviated destination in this fixture. Earlier full workflow passed all51 hook files on the previous tree; this follow-up does not claim that the edited fixture was part of that older run. Protected CI reruns on the corrected head. Independent negative/positive reproduction used disposable repositories only.

## Test plan

Run deployment-source fixture, generated freshness checks and native pre-push checks, then required protected CI. No live installation before main acceptance. Exact-main installation and same-session GA acceptance remain outstanding.
