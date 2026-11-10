# Combined followup integration (#1241)

Integrate the exact reviewed memory/resume (#1239), owned copy/bundle (#1236), and fresh repository (#1240) fixes once after #1235 reaches canonical develop. This is source integration and release coordination, not runtime installation.

## Inputs and base

Create the named integration branch in a new worktree from freshly fetched canonical develop after the normal #1235 merge. Base commit: `ce21650cdcacbbaaa25553c37f8a4bb3b74e73cd`; tree: `cb2bbd8be40d0b77ca1f44e757aca57d7b912a76`. Record the final independently reviewed source head for each input before merging. Retain each source PR's actual review and test evidence. Do not individually resync author branches or include unreviewed additional guards.

## Closure and verification

Merge the reviewed heads, inspect all non-generated resolutions and preserve the already integrated owner-grant/develop-source policy. Regenerate canonical inventory/catalog/metrics outputs once for the combined source; retain source-owned verifier pins and unchanged limits. Run affected meaningful source/package checks for combined interactions, build/freshness and the required full pipeline on the final integration head. Record failures and repairs honestly rather than converting cancellation or prior-head evidence to a pass.

## Integration and publication

Obtain exact combined-source review, then use the normal develop PR merge with current required checks. Coordinate one develop-to-main promotion with Root when all batch predicates pass. Let the normal main-only producer publish immutable source/consumer tags, manifests and archives; verify exact refs and consumer loading before claiming publication complete. Give the client import owner that actual release handoff. Do not edit the client import lane or live host settings here.

## Boundaries

No main/develop direct pushes, force merges, review/check bypasses, new grants/registries, timeout/budget increases, or unrelated source changes. Actual owner conditions, Task/role/path scope, native acceptance uncertainty and publication checks remain intact. No separate merge of the constituent source PRs.

## Reviewed input pins

- Memory/resume PR #1239: `576a0acd3633df22672086a89e84b33bcc56f926` (current source PR head verified; required source CI passed).
- Fresh-repository PR #1242 / issue #1240: `18739384bc5950d60d57fea4f6d19d43ae4972d1`; this supersedes 4d9/35a after actual template whitespace/CR, clone-source CR, Git-file independent-object and clone-configuration-context counterexamples were repaired. Current-head CI remains separate from earlier baseline success.
- Owned copy/bundle PR #1244 / issue #1236: `9eed5cd7f6c302399dcd08beb8ab3e36488c6175`, including both reviewed commits and all fixtures/notes.

## Observed provenance correction

An ordinary client preparation branch was created from develop and then fast-forwarded to main because the file trees matched. The correction used normal main-to-develop synchronization, followed by a fresh ordinary branch from the resulting develop. Equal contents do not establish develop provenance. The coordination paragraph now says so without adding a mechanical merge ban, changing the explicit owner release/backport exception, or removing honestly reported offline cached-develop use. Already reconciled develop needs no additional sync; a known release-ancestry gap follows the normal sync route before the next ordinary branch.
