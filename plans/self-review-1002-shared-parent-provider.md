# Self-review: shared-parent provider event normalization (#1002)

Pre-mortem-artifact: plans/pre-mortem-1002-shared-parent-provider.md
Hostile-review-artifact: plans/hostile-review-1002-shared-parent-provider.md

## Assumptions

- Accepted develop `6fb4d463b5861b79100ee048c7c069f1ff937db7` includes the verified public provider, native registration and coherent generation repairs. Both parents retain their independent acceptance evidence.
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

Nine focused registered-event scenarios and full validation passed 86/86 commands in 596.0 seconds: all Python modules, 36 hook suites, both workflow suites, canonical build, freshness and source/consumer validators. This includes the existing 13 policy cases and 10 local topology cases. Log: `/tmp/cc-shared-provider-full.log`. A subsequent test-only addition brings the event suite to ten passing scenarios, covering the actual public self-hosted shell entrypoint, shallow-parent recovery, missing-ticket denial/repair, strict branch denial and distinct workflow provenance. Logs: `/tmp/cc-shared-provider-final-events.log` and `/tmp/cc-shared-provider-public-event.log`. All local fixtures are synthetic and disposable. No host registration, shared installation or authorization is established by these tests.

Accepted-generation integration passed 13/13 commands in 281.0 seconds at `ca448ab55d90e8256595cc432e55308cc3407ad3`. A later mixed-case repository reproduction identified a false block in whole-string workflow-ref comparison. The bounded component-wise correction passes all eleven event scenarios in 66.502 seconds, including both-profile direct/event positives and exact workflow path/ref-case negatives. Log: `/tmp/cc-shared-provider-case-events.log`. The remaining twelve committed-head build/policy/generation/risk/ontology/freshness commands passed in 224.6 seconds at `ca10e5519f8b47282dcbf81d9e83cca886b2baf5` (`/tmp/cc-shared-provider-case-integration.log`).

Hosted validation then exposed the fixture's reliance on runner-local branch refs. The test-only advertised-parent/default-ref correction passes all eleven event scenarios in 62.157 seconds and all thirteen policy scenarios in 55.937 seconds from a branchless detached source checkout (`/tmp/cc-shared-provider-ci-shape-fixed.log`). Production adapter bytes are unchanged by this fixture correction. Earlier full results do not substitute for the new head's terminal hosted checks or independent verdict.

## Rollback

Revert this bounded change. Existing public strict-profile behavior must remain covered by the same approved evaluator. No main, default-branch, protection, consumer workflow installation or live Craft setting is changed during implementation. The install.sh comment is aligned with the already merged settings-preservation behavior only; it changes no installer execution.
