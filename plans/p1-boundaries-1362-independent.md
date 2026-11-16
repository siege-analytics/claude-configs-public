# P1 boundaries independent review

Verdict: ACCEPT the bounded Root1362 delta. No blocking finding in the reviewed changes. Reviewer: bounded_reader_1327, separate from the source author. Scanner1361 changes are outside this review.

Reviewed base: `2a7c2ba4f8635cfffb48e4220ecaa275754721e6`. Production/contract diff SHA256: `2e9680e280cac35e97611389f985c0938c26cf2b229c75e75767f017e00c3906`.

| Reviewed file | SHA256 |
| --- | --- |
| hooks/git/self-review.sh | 594b383a2d2a8b7b197cba82e700de523cad463fe571bddd27b26a157aa6630b |
| hooks/git/pre-push-self-review.sh | c59cea942ad54a91a22071ed67d1797c08e36e76ad84c32873930c10f1ec1f6a |
| hooks/_test/lean_publication_review.py | c2245a1815d96947bdec0369e9570b3dcd944be96ba15d9cf74309b950c3615b |
| skills/self-review/artifact-contract.md | e0b35271cf9f1dc25eca139de3b3ad2e6ba6c66ed79de8402b2792cf6dcf093a |

## Source assessment

Read the complete four-file diff and both affected publication predicates. The table prefix `^[ ]?[ ]?[ ]?\|` admits the intended zero-to-three leading spaces without shifting the pipe-delimited column positions. Existing escaped-pipe handling and exact complete fixed-resolution-cell checks remain intact.

Both compact-entry predicates split each supported line into semicolon-separated fields, reset counters per line, recognize Resolution only at a trimmed field start, and require exactly one Resolution whose trimmed case-folded value is fixed. Missing, conflicting, duplicate-fixed and empty duplicate fields cannot be masked by a separate fixed token. Other context fields remain usable. Tool and native logic match.

The contract now states the real external-pointer limitation: URL and #ticket references are accepted without fetching their contents. This does not prove their findings resolved; actual author/reviewer inspection remains required. The wording adds no duplicate local artifact, operator waiver, remote fetch or permission expansion. No stronger machine guarantee is claimed than the code supplies.

## Executed independent checks

Executed the four new methods against these exact source bytes:

`python3.11 hooks/_test/lean_publication_review.py PublicationReview.test_indented_unresolved_table_rows_block_both_publishers PublicationReview.test_indented_fixed_table_rows_remain_publishable PublicationReview.test_compact_resolution_must_be_unique_and_fixed PublicationReview.test_compact_fixed_resolution_allows_other_context_fields`

Result: four methods PASS in 5.678s. These run actual tool/native publisher adapters for one/two/three-space unresolved rows, fixed indented rows, conflicting/duplicate Resolution fields and a single fixed field with context.

Additional existing-fixture probes passed through both publishers: Tier B with a three-space unresolved table row denies (tool2/native1); a fixed Resolution plus an empty duplicate denies; one trimmed mixed-case fixed Resolution with a separate Evidence field allows (tool0/native0).

Focused log: `instruction-refactor-evidence-20261104/core1362-p1-boundaries-independent-focused-20261113.log`. Probe results and scoped review JSON are beside it with prefixes `core1362-p1-boundaries-independent-probes` and `core1362-p1-boundaries-independent-review`.

## Limits

These are supported-format source and synthetic publication-adapter checks, not a full Markdown parser, complete author/cohort-suite rerun, hosted CI, release or runtime acceptance. Existing external pointers remain uninspected by these hooks. Only this granted review artifact was written in the author's worktree; no code, test, generated or workflow files were edited.

Verified-by: the exact focused command and independent boundary probe results above.
