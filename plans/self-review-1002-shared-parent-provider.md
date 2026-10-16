# Self-review: shared-parent provider event normalization (#1002)

Pre-mortem-artifact: plans/pre-mortem-1002-shared-parent-provider.md
Hostile-review-artifact: plans/hostile-review-1002-shared-parent-provider.md

## Assumptions

- Accepted develop `cd014600d7262492c7ce95512ba308b307a8efa5` includes the verified public provider and native registration repairs.
- Host registration pins parent authority independently of consumer event data. The normalizer validates that pin and never grants it.
- Parent, canonical consumer/base, candidate/head and executed consumer workflow are distinct identity domains.
- The host supplies complete canonical workflow history through a separate authenticated checkout, then removes credentials. The public self-hosted exact-base checkout already serves as its independent canonical object store.
- Registered events delegate policy to the existing approved evaluator; retained local compatibility is not migration proof.

## Test plan

Replay both profile histories through direct and registered-event interfaces using one parent. Falsify repository/revision/workflow bindings, candidate-code isolation, interior history and installed content. Replay public self-hosted and local topology cases, full Python/hook/workflow/build/freshness matrices, then independently review the exact published head. A subsequent disposable public GitHub negative/repair pair remains required after normal integration.

## Peer review

Direction review by the existing Craft coordinator is recorded in #1002 comment 6210551816. Its independent canonical-workflow checkout and parent repository requirements were incorporated. Complete implementation review is pending.

## Lead review

Pending exact-head review and hosted evidence.

## Quantified claims

Nine focused registered-event scenarios pass. Full current-tree validation passes 86/86 commands in 596.0 seconds: all Python modules, 36 hook suites, both workflow suites, canonical build, freshness and source/consumer validators. This includes the existing 13 policy cases and 10 local topology cases. Log: `/tmp/cc-shared-provider-full.log`. All local fixtures are synthetic and disposable. No host registration, shared installation or authorization is established by these tests.

## Rollback

Revert this bounded change. Existing public strict-profile behavior must remain covered by the same approved evaluator. No main, default-branch, protection, consumer workflow installation or live Craft setting is changed during implementation. The install.sh comment is aligned with the already merged settings-preservation behavior only; it changes no installer execution.
