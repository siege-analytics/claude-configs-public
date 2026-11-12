# Independent review: goal continuity and proportionate work

## Assumptions and actual preparation

Goal source: issue #1328 plus the subsequent user direction recorded in
`plans/1328-simplify-task-workflow.md`: remove redundant pre-mortem and rank
ceremonies while preserving informed implementation, meaningful verification,
real scope and genuine action-specific holds.

A separate review-only task, `bounded_reader_1327`, inspected the actual diff
and current source without authoring the simplification. The issue supplies
the parent-goal/re-entry requirement; the later request supplies simplification.

Actual source facts informed this verdict:

- UMG still parses payloads fail-closed and resolves the actual own Task before
  allowing implementation. Designing/reviewing and unknown states remain denied.
- The resolver changes its retired companion lookup map; the preceding exact
  own-task test-receipt/output ownership rejection remains.
- Prompt code no longer fetches rank comments or derives permission companions.
  The investigation compatibility hook grants no new authority; mutation
  admission remains with the Task resolver and action guards.
- Publication retains computed risk floors, protected policy-file Tier C,
  actual independent-review evidence, exact destination range checks and real
  unresolved P1 rejection. Native Git, Git-command, Task-action, branch and
  destructive-action protectors were not changed by this patch.
- The revised procedures require concrete consulted source/documentation facts
  and their effect on the approach. Research is conditional on materially
  unfamiliar/changeable behavior; repeated reading and prescribed pre-edit
  posting do not substitute for useful evidence.

These facts support removing old preparation signals while retaining admission
and publication protections. No new external contract required independent web
research for this local-source review.

## Reviewed snapshot

Base HEAD: `d3581bbd429d03ae82128187b9e46bcc624df278`.

Initial writer enforcement diff SHA256: `3153297b14e2eadc61055d820c1009556b0c22bb0065511295bab7abcf173917`.

Final reviewed source/test/prose diff SHA256: `da8a2056c4b5caf386bdb37dec5e0748c3da6e59513d3a7244a7eff73a758126`.

Final file-manifest SHA256 (canonical sorted compact JSON): `10ca223f4e10d4b7ddca3171fe83d3d7930089dc73cc508a6361a21eb3742529`.

The initial production diff was compared byte-for-byte with the writer's frozen patch. The final source delta was then reviewed and rebound below.
The manifest pins reviewed fixtures, substantive procedure changes and test
adaptations, including obsolete-feature test deletions. Generated inventory
outputs and review bookkeeping are excluded; Root owns their freshness checks.
Later substantive source changes need review of that delta.

```json
{
  ".githooks/commit-msg": "1d49f097ee06f086254ae8f00537901bd14ea9ff6e5ef865da565c69046b6c1d",
  "CHANGELOG.md": "909830b31f696ef0c0e7ddc271eecddda5aeb75b58220ce0f21c5f0a8a9a7af0",
  "RESOLVER.md": "76900ae099fcd444bc87b14f7aca929691bc608b50b6b1e6005a30599536fc45",
  "bin/_test/inline_delivery_test.py": "4f8f82153d7866dd9f82536682146c940dc5a86da7900ecbbbbc9b59f23f71d0",
  "bin/_test/review_risk_test.py": "0ef562a73cd6a31ca11aa2634b66b121b7085389226bce2b06466dd76141f5d7",
  "bin/verify-enforcement.sh": "d7d1183fc14ae954dfd01161f6efcb227d1d7f4a3527b80a03a07be03dc5bb56",
  "catalog/review-risk-policy.json": "2044acec187a1a35b322377d2ef396064606382c089ef9bb057c1576b1fd2251",
  "hooks/_test/artifact_result_followup.py": "8a130952e045eb332962f6f27746fad21d47137a355fb91a41a7c9ea6b973a80",
  "hooks/_test/execution_risk.py": "99dcba81073e4b80301d6a07e5bb731610d40bb49abc3abd3547ccf1d1b9f8ef",
  "hooks/_test/explicit_target_operands.py": "fa581f4d686f2458ffb50ae12c4a65d1a3720c2ace891f2ba4d9508a91c40e9a",
  "hooks/_test/gate_bypass_1164.py": "2b2dd02b1d92392c48972dd189b1141cb4420ca42088d0beba0811bae21bc791",
  "hooks/_test/git_add_risk.py": "d5555a1a8d9c3c719436e67620413ca812b7420e4bcd7a49034aa410387b9722",
  "hooks/_test/git_bootstrap_targets.py": "a9093aa97309e083a79b27d7432f74fc9930428a9ffe7546da0843be27a9e226",
  "hooks/_test/github_project_scope.py": "d34051e834139c7df3c864a0174daa72e1b6d6c8a4e624c2e23d88f248d3a08a",
  "hooks/_test/github_project_status.py": "173eef355d861ed23e9fba0ba89bc38107cbcd3f7afddf22afae80ebd90dcd87",
  "hooks/_test/investigate_gate_schema.test.sh": "a06ea7e93eb805ae053839625bf4ffc17220972090914bb128a804d2c812b15d",
  "hooks/_test/lean_publication_review.py": "7a271b6d112e92ea5bcaa59d20e3762ff490ce454fb69df959d9f0cdbbf46a55",
  "hooks/_test/lean_publication_review.test.sh": "ef1c2378776bcdcfb21500be146faa013595f33288e79abe0a4844e2d8879c00",
  "hooks/_test/lean_task_pipeline.py": "dea0150981c778474eea88808176f71a35dd9503e948cc163c45264fb9e6992d",
  "hooks/_test/lean_task_pipeline.test.sh": "a313f0a2a2a9969ee59cb64d975612dd9120e122e3ae61651f1c85344e991a78",
  "hooks/_test/metadata_comment_reporting.py": "b47517817aec771b383d304e30583af5d7d0ab0e250f2c988e3f31237af82837",
  "hooks/_test/pipeline_author_permissions.py": "DELETED",
  "hooks/_test/pipeline_author_permissions.test.sh": "DELETED",
  "hooks/_test/pipeline_review_headings_1164.test.sh": "DELETED",
  "hooks/_test/pipeline_state_own_pr_1274.py": "DELETED",
  "hooks/_test/pipeline_state_own_pr_1274.test.sh": "DELETED",
  "hooks/_test/quoted_mutation_operands.py": "c2f1f91325594605c2ba53b70c0529f27c2f8d3a4775229905953b53d4ab890e",
  "hooks/_test/review_risk_policy.test.sh": "da951411853fe256d6580af9f7be7e3ccfa03d11586da5103934cdc0bea67a39",
  "hooks/_test/scoped_test_evidence.py": "af5575eef15698b1ab9034a3c70beba92f3e7c563950e12f5bb3f4af5476a088",
  "hooks/_test/self_review_hook_489_deploy_model.test.sh": "DELETED",
  "hooks/_test/self_review_hook_819_820.test.sh": "DELETED",
  "hooks/_test/session_signal_resolution.test.sh": "39abb7edfd81fecf20ef0a5f47d940e746937fcdbac071eb5a5b12c4fb09e8ab",
  "hooks/_test/task_keyed_gates.py": "4cb9227e5c1e7ce1be155ae8fd77841da3c1f0938d2421f6f79a3e1aa6c50425",
  "hooks/_test/tier_trailer_aggregation_1168.test.sh": "c4c96215ca34919d415093f998dc1729a5243a76ecf1adf2453c45ddb37491ff",
  "hooks/_test/universal_mutation_gate_831.test.sh": "5c979090097a3d13063775e12eec549526541f147b013b3f7c7ea91b19e731a5",
  "hooks/_test/universal_mutation_gate_empty_reporoot.test.sh": "28babcf11ddd240ce65df421f840e41d57ac834e224b40bb8f400b42ac589230",
  "hooks/_test/verify_enforcement.test.sh": "25b230c6b7b870d55b3dc0c32ac870b9e7090a0d7b939b3be8ccb1f2402d5969",
  "hooks/_test/worktree_materialization_risk.py": "db788d352302a8d500188ee3503e9aa5f731486c357c12d0e215f714e4fbf88d",
  "hooks/bash/universal-mutation-gate.sh": "1d6c83cd347a9b7009ce3c40f31b8d46ca2240316db7ffc375828cd0a4452643",
  "hooks/git/pre-push-self-review.sh": "0d2f1bbdff005660a8ab6992bda1e7ca7f2cf57a6a5ef8fefa3da9118723c1cc",
  "hooks/git/self-review.sh": "ad6384042e8cba163e4bb8bc0f826d23b0225d91d33f5fabdfe83af9046f72aa",
  "hooks/lib/pipeline_state.py": "93771ceda8b9dd4cb8cd5b41722a8046d25280615121708f98edc46d70943153",
  "hooks/lib/resolve-think-gate.py": "92126dd5e1e1927c0c53c6a5a0c0b724d39dafaccc66a2e4a8fb2beddd1422fb",
  "hooks/resolver/inject-resolver.sh": "d6e0b3d6c24afba30a7dab0e6e3611b35bdb7905c2e31e373109e1c8524d72cc",
  "hooks/resolver/investigate-gate-guard.sh": "a12e12da227d4bde8aafc19a834228904b77e3887e0e40e7e3a439b05ab58676",
  "skills/KERNEL.md": "4d0da35d7f4eed3689c42182530b2d482e4e82172cdbd1462461e9675975be74",
  "skills/RESOLVER.md": "e18b06794e6995b77c4fbbd59d303990bab5020d221e4c170fc126c1017a288f",
  "skills/_authoring-against-state-rules.md": "5aeb36d0136cfa02c6601cae0bb22134778fe245817f52acd47b19c54fd78db9",
  "skills/_definition-of-done-rules.md": "447e5513e9ad33d111342244ead47cdeee18f4b8da357eff1b297e48f899d0d4",
  "skills/_enforcement-contradiction-rules.md": "202b3a86e9f16f2b75bd6adf31d7b58153fd9b389ab0e67260e6313f42de332d",
  "skills/_output-rules.md": "f1d822a5a28133bd8b387e837aa5eb1b8d33d05f9ebc4cb8eab4d5c8d4065f66",
  "skills/_standing-approval-rules.md": "16ed11b51257fa12aa924bd620b902369e868466f4469d938e1caad2bba0faeb",
  "skills/_strategic-agency-rules.md": "87d02b23d9858f560a520d5b1cd672671cebee25e3ec73e0d38e7fd3964bf8c9",
  "skills/_verify-before-execute-rules.md": "12f77418420744fdbd2247ddf7b6a610cb04a9665c7f8867ff070afaf595e087",
  "skills/_writing-code-rules.md": "bd9b921f985361580dc0845463357dd5d9e056996cdf3b3509c34a80ef5b8ddc",
  "skills/code-review/SKILL.md": "998ffdd280fac058a14ee1cc1f71d7e605c1bfccd67aad3bd77d8b58e7e98e6e",
  "skills/commit/SKILL.md": "743e9685d177b036d9f54ec811b6838eb8ac17dca48881157c6e3d8c9f6abe9f",
  "skills/create-pr/SKILL.md": "33876560d2e44f3b2e9ef21ba5668e3d1fbe1f8e9f18a7f8ef1568222260d6f2",
  "skills/detect-ai-fingerprints/SKILL.md": "dee9c4ca5bda753891f2aaea229d9d769b06023550e5ae4d6833a46d838b414f",
  "skills/drive-while-away/SKILL.md": "576e5550f4fa8074f25f5ab7c1d813bfaf1d126ad9c58a81a420ee72decf73e6",
  "skills/hostile-review/SKILL.md": "1f247d589f1cf840418a6ce5a975d2deffb5063c7c6de4b71f2d6c500a7d9760",
  "skills/investigate/SKILL.md": "5e9967e99b91b87eb2040bb6099fe263416f16f5e38b0cce728c25d2b92b4979",
  "skills/post-mortem/SKILL.md": "78d1d50b7971a2dc59d7a9d22b6c4b19708335b596062412817c5ed19cebac0b",
  "skills/pre-mortem/SKILL.md": "d2b79fbb67ad59ec62be5070859b18b93dfb9abd07b66e2dc4fd490a70921680",
  "skills/pre-work-check/SKILL.md": "8a2caa512eaedfbe1247fbc64f28b7c0a287d7b26f359f10c222653abd88763c",
  "skills/self-review/SKILL.md": "fe17fa9049060e53a8a5bf2fcb37e55a3d42e07ce458b454a0e2f142ea177d29",
  "skills/self-review/artifact-contract.md": "ebe1388d1af78cc526a0ef13aa077c96a69d958ead789c277b32eaaadd846eb0",
  "skills/self-review/review-checklists.md": "6511282bbe0939611bde3bd6dd2f9a2a995d636dc82766b3d932f04dd656e857",
  "skills/think/SKILL.md": "01713a3a42cc226449e535662a4958e42e03f89908375711de1ab0f82dda0635",
  "skills/think/design-workflow.md": "00bac296b5207faa6c808459167ef21a50848c853569f3b682cb9942931b9ebf",
  "skills/think/task-evidence.md": "69c476352ffcd5896939e4e7a4413d48702d756592889b9c8918305fe40aca48",
  "skills/ticket-guard/SKILL.md": "a1f5a7b377c1a08220751c2152c0197b316a609f22b1d392c49723a60c3500e8"
}
```

## Findings and resolutions

- **Resolved: contradictory preparation gates.** Selected resolver, readiness,
  authoring, verification, commit/PR and pre-work entry points now agree with
  optional investigation/pre-mortem and the compact review contract. Actual
  project/owner requirements still apply to their real scope.
- **Resolved: historical record compatibility.** Native and tool validators
  accept useful historical B/C records alongside compact records. The baseline
  distinction matters: native B accepted the minimal record; the old tool hook
  separately imposed a Goal-source literal. The simplified contract does not
  turn that adapter inconsistency into a magic-field migration requirement.
  Actual goal/source substance remains required by the authored review contract.
- **Resolved: extra mandatory publication trailers.** Universal separate
  Negative-Tests/Full-Suite/Canary-Rollback trailers were removed. Meaningful
  negative checks, affected regression coverage and applicable runtime/rollback
  proof remain in the compact evidence contract. Actual Tier C independent
  review and unresolved critical-finding rejection remain required.

No unresolved source safety blocker was found in this pinned scope. Parent-goal
continuation remains within the existing grant and preserves explicit user
horizons/pauses. It does not manufacture work for a completed finite assignment.
A refused operation is not replayed through another actor, spelling or phase.

## Validation and limits

This reviewer read the actual hook, procedure and regression-test deltas. It did
not independently execute the full hook suite and does not claim those results
as its own. The enforcement writer reported actual exec 90517 completion:
selected host-binding case passed; lean Task fixtures passed; publication
fixtures passed, including historical minimal B, required independent review
and unresolved P1 controls; native format, syntax and diff checks passed.
These are writer-executed results, not independent reruns. The earlier broad
Task run had an outdated fixture; its corrected selected case passed. That is
not represented as an initially clean full run.

Root owns final generated freshness, remaining regression/CI results, direct
PR review publication and protected delivery. A complete non-clean scanner
still needs real dispositions; this review makes no clean-scanner claim.
Static review does not establish installed native acceptance or sustained
multi-role outcomes. Runtime continuation/handoff acceptance remains separate.

## Verdict

ACCEPT the pinned source/prose change after the concrete resolutions above,
subject to actual required validation and normal protected publication.
This verdict does not waive an owner hold, authorize a runtime action, certify
a deployment, or declare the parent objective complete.

## Independent follow-up evidence

The reporter/effect concern was checked with isolated base policy from the
reviewed base commit, complete C preparation, and candidate policy both with
and without companions. Actual hook callbacks allowed own-CWD local reporter,
plugin and config forms in each version; they denied literal foreign reporter
outputs (equal/split options, junit alias, HTML, relative sibling path, absolute
venv executable) and foreign shell redirection. The requested program strings
were never executed. The probe is scoped evidence, not a claim that plugins,
Makefiles or scripts are sandboxed. Opaque execution keeps its existing trusted
project-code boundary: CWD is an unknown-writes proxy, not proof of every
transitive effect or a grant for outside effects. Relevant code/effects and
actual authorization still matter.

Independent exception review is in
`plans/1328-independent-scanner-review.json` with reproducible classifier-only
probes in `plans/1328-independent-exception-probes.txt`. This reviewer also ran
the existing ResolverRecovery tests and the diagnostic-input regression; these
independent runs do not substitute for Root's affected suite and protected CI.

The verifier anchor update was inspected separately. Only its code-owned
expected digest changed. Restoring canonical token references in the rendered
`dist/flat/skills/KERNEL.md` reproduced authored `skills/KERNEL.md` byte-for-byte;
the rendered digest is
`9588c93f6156f97e11848b232e720d37662dde1d6f1363e1d068dd734a9457a1`.
No expected value is derived from an untrusted installed target, and altered,
symlink and wide-bundle verification logic was not weakened.

## Final rebind

Final enforcement plus verifier-anchor diff SHA256: `c3dab5e723ee81792c6290b955ba664e208f4852bb0057704def15a3796d4df0`.

The later scope-comment clarification, simplified diagnostic entry point,
source-consultation prose, verifier anchor and regression-fixture adaptations
were reviewed. The diagnostic handler has actual independent missing-argv,
missing-file, malformed/nonobject JSON proof. Native formats preserve genuine
independent review and historical records without the redundant extra trailer
bundle. The fixture changes separate risk classification from edit admission
and retain foreign-output, unresolved inline/env/glob, foreign Task/repository,
nonimplementing and branch-source controls. The verifier change is only its
code-owned rendered-kernel digest; no untrusted override was introduced.

The scanner class record accepts the pinned demonstrated false positives and
unchanged, non-newly-exposed coverage debt with exact function/handler AST and
caller evidence. Remaining resolver-specific debt was appended to existing
issue #1329 at its linked comment, without duplicating the issue set. Root's
style/timeout fixes and final complete scan are not waived by this acceptance.
No unresolved safety blocker remains in this final reviewed source scope.

## Independent follow-up: bootstrap machine-output fixture

The final test-only delta in `hooks/_test/git_bootstrap_targets.py` was reviewed independently after the manifest above. Whole pretty-printed JSON is parsed before actual Git execution; malformed machine output fails the fixture, and continue-false, block and nested permission-deny controls are asserted. The added negative cases cover these shapes. Ordinary advisory text is not treated as machine authority. No production behavior changed. The author executed all 36 bootstrap tests successfully; the follow-up reviewer inspected the code and negative cases without claiming a separate rerun. Verdict: accepted. Final file SHA256: `25d6472e5ff7afcde21ade6f41403c56bb6f921fbace313414488096e2221711`.
