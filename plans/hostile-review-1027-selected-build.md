# Hostile-review preparation: selected build (#1027)

All verdicts on `d00f73faa216d9617323faac362c2281e1a5412d` are obsolete.
The generated-path overwrite below falsified its claimed ownership closure;
green historical checks do not override that evidence.

Pinned baseline: c7d9d65e30dfd4450682a63b33fd0b53b979e2a0.
Role: author-side attack plan, not an independent acceptance verdict.
Independent review: pending with the existing reviewer after draft publication.

## Attack chain

Normal build -> selected component verification -> immutable source snapshot ->
existing composer/ProcedureGraph -> resident and installed resolver -> package
publication. Independent registration source/digest enters separately.

Try candidate-supplied policy replacement, duplicate component/publisher IDs,
changed blob/mode/digest, wrong scaffold tools, unknown backend, missing declared
capability, missing workflow adoption, alias/prerequisite cycles, missing or
foreign project source, existing output, and interrupted publication. Inspect
actual files/receipts and resolver output, not just function return values.

Separately inspect native and generation call chains. Their current fixed
Siege sources are unresolved acceptance work, not a reason to redefine a
composition receipt as registered enforcement. Keep #1003 non-live boundaries.

## Findings

Pending implementation and falsification. No acceptance verdict yet.

## Author falsification results

`python3 -B bin/_test/package_selection_test.py` passed 18 tests (43.062s).
The cases execute the copied normal builder and installed resolver. Failure
cases cover independent pin replacement, missing profile adoption, changed
committed bundle bytes, wrong scaffold bytes, ambiguous names, graph cycles,
symlink blobs, foreign project sources, malformed/duplicate JSON, unsupported
adapters/backends, existing destinations and interrupted publication.

The existing installer was invoked against selected output with disposable
operator settings and a real fixture Git repository. It rejected the missing
settings snippet before changing those settings or core.hooksPath. This is a
negative registration-boundary test, not completed selected registration.

The executable Siege case checks the complete composition file set and bytes,
plus the existing evaluator's policy decisions with three capability states.
It does not claim native allow/deny observations. The full legacy export
comparison retained 3379 files, with no added/removed files. Working-source
byte changes were only build timestamps and the added Tier C source-path
patterns. Final committed-head comparison remains required before publication.

## Scope verdict

The selection-to-composition boundary can be reviewed independently. The
registration/generation acceptance remains blocked by the retained fixed
native/protected policy sources identified in the pre-mortem. The author does
not issue independent ACCEPT. Exact-head independent review remains required
before merge; no additional worker was started.

## F1 / S1: generated path overwrite, reproduced and corrected

The source at d00f73faa216d9617323faac362c2281e1a5412d silently replaced a
publisher's nested asset with another publisher's bytes. Reversing selection
order reversed the surviving bytes. This is a content-integrity defect in the
normal copied build path; it is not a demonstrated authorization bypass.

Before source edits, the exact probe from PR comment 6227734449 returned:

```text
declared 0 -> SECOND_PUBLISHER_BYTES
reversed 0 -> FIRST_PUBLISHER_BYTES
AssertionError: duplicate generated path was published
```

Pinned target: `skills/outer/inner/shared.txt`.
Owners: `bundles/first/skills/outer/inner/shared.txt` and
`bundles/second/skills/outer/inner/shared.txt`.
Evidence: `cache/selected-build-correction/parent-collision-red.log`.
Post-error revision: https://github.com/siege-analytics/claude-configs-public/issues/1027#issuecomment-6227762888.

Function contract: `compose-project.package` must validate complete generated
ownership before either layout is written. Chain: `build.py --selection` ->
`package_selection.build` -> existing composer -> generated file map -> staged
directory publication. The old source-path checks were upstream of a many-to-one
path mapping and could not establish that contract. DDIA's derived-data lens
requires reconciling generated artifacts with their source owners; a receipt
listing both sources cannot repair an overwritten output.

Correction: `GeneratedFiles.add` claims the output path before inserting bytes.
All composer assignments use it, including primary skill Markdown, binary/text
assets, rules, generated bundles, resident, catalogs, tools and receipt. Equal
bytes still reject. Case/Unicode aliases and file/directory conflicts also
reject. Errors name both source-relative owners and the generated path without
source contents or private absolute paths. Existing destination guards remain.

Green replay: the exact posted probe exits 0; each inner build returns 1 with
both owners in a non-authorizing collision diagnostic and no published output.
See `parent-collision-green.log`. Both newly added nested and flat/router tests
also fail against the original product source: two tests/eight failed subcases
per CLI in `direct-revert-red.log` and `selected-revert-red.log`.

Attack coverage lives in `GeneratedOwnershipCases`, inherited by direct selected
composition and copied normal selected-build suites. It covers both orders,
equal bytes, flat-only router collisions, aliases, file/directory conflicts,
no output, unchanged existing sentinel and complete output package, and stable
qualified publisher outputs. Case-insensitive discovery rejects the primary
case-alias fixture before rendering; case-sensitive discovery exercises it as
an asset. Direct claim tests separately cover primary/rule/reserved outputs.
A root-level SKILL fixture is already invalid; that earlier rejection is not
claimed as a newly fixed reserved-path bypass.

The working direct suite passed 22 tests. Focused/dependent and committed-head
matrix logs are kept under `cache/selected-build-correction/`; final exact
head/tree/parents and green replay are posted on the draft PR. The scanner's
inherited missing-test-discovery finding remains disclosed in self-review.
No risk-classification adjustment is needed: touched code/tests already require
Tier C. No further source blocker was found in this author review, but it is not
independent ACCEPT. Registration and merge remain outside the correction.
