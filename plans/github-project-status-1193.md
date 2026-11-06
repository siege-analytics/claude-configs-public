## Context
Follow-up to #1161 AC6. Add-only implementation1173 is stacked in reviewed parent1185 at d4feed76905358a840993a899764d0969ec20209. This feature depends on that parent and does not delay original item-add delivery. Current item-edit remains denied; opaque item/field IDs cannot borrow local path authority.

## Goal
Support exactly typed own-task project Status single-select updates under a separate fixed installed grant. Core remains deny-by-default. Existing client lifecycle authorizes In Progress/In Review; Done belongs to the operator. No client policy deployment or live board mutation here.

## Acceptance criteria
- Strict literal item-edit flags resolve exact project/item/field/option through one fixed read-only GraphQL query, with matching issue and current session task.
- Installed source policy grants field name/type and allowed value names; task fields and cached attestations cannot grant authority.
- Default Core denies; Done/all-fields/reset/admin/arbitrary GraphQL remain denied.
- Bound total query time/output and clean child process groups; invoke only after the supported item-edit shape and fixed installed grant are established; select the exact current-session task after live proof resolves the issue.
- Real-hook controlled-gh fixtures cover exact positives, foreign membership/field/value, malformed/timeout/oversized output, identity/holds and shell composition. No production test exemption.
- Source/scanner peer review, meaningful focused checks, actual native receipt and Git hooks precede normal feature PR. Protected CI/merge/install remain separate.

## Assumptions
Existing source-owned client lifecycle: work start In Progress; PR creation In Review; operator only Done. New fixed-policy schema extension implements those instructions but does not invent a generic project grant. Parent1185 supplies add-only typed remote flow and bounded execution infrastructure. User authorized this repair; Root owns protected merges/install.

## Design and investigation
Official schema https://docs.github.com/en/graphql/reference/projects documents ProjectV2Item.project/content and ProjectV2SingleSelectField.project/options. Query exact item and field nodes; verify item project owner/number/id, Issue canonical repository/number/URL, field project identity/name/dataType and option identity/name. Use variables, never interpolate caller GraphQL. Reject partial/error/ambiguous responses. Existing exact task ticket/task_id and shell composition boundaries remain.

## Pre-mortem
Launch-Blocking Tiger: forged IDs or task-attestation allow editing a foreign item. Mitigate live exact node relations and fixed installed grant, real-hook negatives.
Launch-Blocking Tiger: network hangs hook or leaves children. Mitigate existing bounded runner, total short deadline, output cap, group termination/reap; no retries/pagination.
Launch-Blocking Tiger: schema mismatch or partial response is treated as proof. Mitigate official type checks, strict response validation, errors/null/type/membership negatives.
Paper Tiger: original add repair waits on new feature. Separate stacked branch/PR; no parent hold.
Falsification: unsupported update gains authority, unknown result is accepted, timeout exceeds bound/leaks child, or original add semantics change.

## Candidate interface and limits

Core hooks/github-project-policy.json remains empty/deny. A client may separately publish one item-edit grant with existing host/owner/project/issue_owner/issue_binding/authority_source fields plus operation=item-edit, field_name=Status, field_type=SINGLE_SELECT and values=[In Progress, In Review]. Existing item-add grant remains separate. Duplicate operation grants, other fields/values and task-supplied authority are invalid. This proposal does not edit the client branch.

One exact item-edit per invocation triggers one fixed readonly query with a3-second budget, inherited bounded stdout/stderr runner and process-group cleanup (up to2seconds). The response acceptance cap is64KiB and field membership is complete only when first100 has no next page. No retry, cache, pagination or task attestation. Existing Done cannot be reset. Mixed local writes still require the same task's complete local gate; repeated remote mutations must be split. A foreign or unsupported operation never becomes cwd authority.

Official schema checked2026-11-05: https://docs.github.com/en/graphql/reference/projects. Node type, item-to-project, content-to-Issue, field-to-project and options are validated; ProjectV2Owner may also be Issue/PullRequest, which this narrow lane rejects. Field uniqueness uses project field enumeration, not first-match fieldValueByName alone. Live read-to-CLI execution has an unavoidable remote time-of-check race; the gate does not claim an atomic GitHub transaction or network availability.

Red-first baseline: newpositive fails because item-edit was unsupported. Initial5 passed after implementation; later focused runs added per-task coexistence and ownership negatives. Existingadd13 pass13.633s after updating only the modeled-edit denial expectation. No live board actions occurred.

## Peer correction and final focused evidence

Root identified that preselecting one implementing task before lookup recreated a global ambiguity block. Removed that preselection: live fixed-policy proof returns the exact issue, then existing per-issue session/task selection decides ownership. Different active/designing/terminal tasks do not block the item owner; duplicate same-issue owners still deny. No explicit binding is newly required for unrelated tasks.

An earlier10 real-hook run passed17.782s, including exact original canonical task_id fallback, valid local companion gated independently, unrelated task coexistence, malformed/null/error responses, wrong owner/archived/Done reset, duplicate field membership and bounded descendant termination. Existingadd13 pass13.633s. Audited dependency graph and newhelper TierC floor passed. Final selected scan is non-clean62 heuristic AST findings, not a clean result or exhaustive exception-path proof.

Final11 real-hook cases pass19.156s after adding missing/designing exact-owner and foreign-session-gate isolation. An unknown SDK UUID with no legacy turn anchors is not covered as a denial: that legacy host-binding behavior was reported separately to Root and left unchanged.
