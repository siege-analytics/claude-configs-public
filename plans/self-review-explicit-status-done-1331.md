# Explicit project-granted Done review

## Assumptions

Goal source: Core #1331, client integration electinfo/electinfo_claude_skills#482,
and the user's authorization for TC board stewardship without unnecessary
operator-only gates.

Actual source consulted: `resolve-think-gate.py::project_policy` rejects all
Status grant values except Progress/Review; `select_project_task` still binds
the live target to one current-session implementing Task's exact canonical
Issue. `github-project-status.py::verify` proves owner/project/Issue/field/option
relationships and matches the chosen Status name to the installed grant. It
also refuses resetting an already-Done item. These facts support changing only
the installed policy's allowed value vocabulary, leaving that verifier intact.

The default `hooks/github-project-policy.json` has no grants and is unchanged.
`coordinator-status-guard.sh` does not classify `gh project item-edit`; no
existing business-completion gate is being represented as applied here. Core
proves metadata authority and scope, not all business completion. Client
workflow must retain actual review/tests/merge and applicable downstream or
runtime evidence, and preserve genuine owner holds. An Issue-CLOSED query or
new role/capability field is outside this change.

## Test plan

Executed `bash hooks/_test/github_project_status.test.sh`: passed, including an
explicit Done-only grant, absent Done permission, foreign Task/project/owner/
field, unchanged current-Done protection and existing fixed-query/failure cases.
The completed-Issue fixture supplies context; Core does not use its state as a
new admission gate. The hook fixtures use a controlled read-only GitHub
transport; they do not perform live board writes.

Executed `bash hooks/_test/github_project_scope.test.sh`: 14 tests passed.
The complete selected-source scan exited 1 with 62 existing resolver findings
(raw log SHA256 `303aa90dd46a2ac396eee0d217a5ae07dc1debc87a9930e5c0ce8a174dccc4d2`).
All 32 exception-handler ASTs match base d3581bbd exactly. The changed policy
function adds no handler or call; Done reaches the same live identity verifier
as the existing values. This is not a clean scan claim: unchanged resolver
coverage and diagnostic debt is tracked in #1329, with the separate #1328
per-handler review. The newly admitted value has the direct hook controls above.
Canonical inventory regeneration produced no tracked delta; generated source
authority check passed. The source diff check passed. There is no deployment or live board-acceptance claim.

## Findings

The production change adds Done to the narrow installed-grant vocabulary. It
does not add a default grant, accept Task/role metadata as policy, introduce an
arbitrary API mutation, or change target identity and current-Done guards.
Premature business completion remains a workflow error rather than something
this metadata verifier claims to establish. Reverting the explicit client value
grant removes Done permission without changing other board operations.

## Independent review

Root independently reviewed commit `5156f4c3db1e1b264755aa2ad6a9f312a60e2503`
and accepted with no blocking finding: the two-line vocabulary change retains
the explicit-value/project/current-Task/field proofs, unchanged empty default
policy and current-Done reset guard; actual tests cover grant and foreign
identities. This review was communicated directly on 2026-11-12; Root will post
the direct review on PR #1332. CI remains pending; no full-suite claim is made.

## Publication history repair

PR #1332 preserves the original accepted source and actual Root review. Its
source commit lacked per-commit review references, so this replacement starts
from fresh remote develop `fb3416d6d13d27dd09a3802ebbd4646863ad6613` and
publishes the same source and test blobs in one reviewed commit. No published
history is rewritten. The affected resolver, verifier and project test files
are unchanged between the old and fresh bases; source/test blob equality was
verified. Fresh-base results: Status 14/14, project scope 14/14 and diff-files reader
integration 4/4 passed. Inventory and generated-source-authority checks passed.
