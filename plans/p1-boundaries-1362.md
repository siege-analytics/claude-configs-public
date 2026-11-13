## Assumptions
Goal source: issue #1362 and PR #1335 discussions4560516879,4560629302,4560629345. Read both publication adapters, their current fixture producer, the artifact contract and the official GFM table/indented-block specification (https://github.github.com/gfm/). These hooks validate supported local Findings formats; external record references remain pointers and are not fetched.

## Test plan
Actual baseline tests produced six failing subcases: one to three leading spaces hid unresolved table rows, and duplicate/conflicting compact resolution fields were accepted. Corrected focused four methods passed in 6.308 seconds; the full publication suite passed 30 methods in 45.320 seconds, adjacent artifact tests passed 14 in 6.421 seconds and the risk-policy script passed 13 checks. Full normal build and official inventory, source-authority, loading, language and data generators passed. Separate independent results are committed below.

## Findings
None. Table recognition admits the supported zero-to-three-space indentation without changing cell splitting, escape handling or complete fixed-value requirements. Compact P1 records require exactly one complete Resolution field equal to fixed after trimming/case folding; context fields remain allowed. External URL and ticket records retain their existing workflow, while the contract states the limits of mechanical validation and the actual review duty. No local duplicate, new review rank or operator waiver is required.

## Independent review
Separate actual result: plans/p1-boundaries-1362-independent.md. The reviewer inspected both adapters, test cases and contract, ran four focused methods and boundary controls, and did not author implementation. Hosted CI and actual deployment remain separate required observations.
