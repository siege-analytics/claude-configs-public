## Assumptions
Goal source: issue #1358 and PR #1335 discussions4559989494 and4559989502. Read both publication adapters, the artifact contract and the actual publication fixtures. Required compact/historical sections keep their existing documented names. Optional Findings sections may contain annotations, alternate case or whitespace and must not hide an unresolved P1.

## Test plan
Before correction, two real fixture methods produced seven failing subcases: unresolved annotated Findings were accepted and the native compact format accepted a noncanonical required heading. After correction, three focused methods passed in 7.614 seconds. Expanded actual publication suite passed all 26 methods in 34.943 seconds, including Tier B, compact Tier C, historical Tier C, resolved positives and the existing table/independent-review/reference controls. Full build, diff check and normal source-authority/inventory/progressive/review-risk checks passed. Independent checks are recorded in the separate review.

## Findings
None. The tool guard and both extractors use the same anchored case-folded Findings word boundary. Level-two headings end the section; nested headings remain inside it. Native required-section checks are anchored to the existing canonical headings, matching the tool adapter. Whole resolution-cell matching and actual independent-review requirements are unchanged.

## Independent review
Separate result: plans/findings-heading-1358-independent.md. Source-only review and local tests do not establish hosted CI or installed runtime acceptance.
