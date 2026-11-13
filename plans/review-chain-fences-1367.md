# Review chain and fence boundaries

Refs: #1367

## Assumptions

The selected develop base is 3154162a060e29a28e93feeaf2ebd00ce915f60e, prepared through the canonical task-branch helper. Read the actual coordinator proof and both publication adapters before changing their boundaries. The CommonMark fenced-code contract (https://spec.commonmark.org/0.31.2/#fenced-code-blocks) requires matching fence character and sufficient closing width, permits zero through three leading spaces, and excludes backticks in backtick-fence info strings. These facts inform the bounded section extractor; this is not a general Markdown renderer.

## Changes and falsification

The actual guard RED had three failing glob subcases: a reader-proof failure discarded detected GitHub operations and let a later close borrow the first reader's legacy classification. Separate effect collection from proof construction. Preserve every detected invocation even when a glob or unsupported output prevents the reader exemption. The original command is never executed or rewritten; Task and filesystem scope remain independently enforced.

The initial fence RED had eight failures across two maintained methods. A fenced level-two heading ended the Findings section and hid later real unresolved P1 rows. Both adapters now track fenced examples before section headings, ignore their sample rows, and resume real Findings on the matching closing fence. Root identified an additional zero-to-three-space Findings heading bypass; the authored supplemental-heading regression reproduced it. Matching and section boundaries now share that narrow indentation support. Existing required-section contracts remain unchanged. Invalid backtick-info strings do not start a fence.

A targeted rerun exposed an identical-artifact Git fixture commit, not an admission failure. The fixture now includes its tier so B and C cases have distinct source data.

## Findings

The reproduced mixed-command, fenced-heading and indented-heading defects are fixed by the source changes above. No unresolved P1 remains in this bounded slice.

## Independent review

Root inspected the actual source diff, independently ran seven coordinator methods (PASS3.883s) and three fence methods (PASS16.365s) before the final indentation correction, and reviewed the latter correction. Those results are scoped to their actual snapshots. Final author-suite results are recorded below after completion. No hosted CI, installed-runtime delivery, or scanner-lane review is claimed here.

## Test plan

Final author coordinator suite: seven methods PASS3.686s. The canonical unbound test-evidence producer reran them: PASS3.713s, bound to the five changed code/test sources. Final publication suite: 34 methods PASS57.720s, including fenced example positives and unresolved findings after closing fences or indented headings. Root independently reran the final indented-heading method across three tiers: PASS2.800s, inspected the staged source and accepted the repair. Bash syntax and diff checks passed. Existing helper invocation sites still match their maintained digest; no registry change is required. The staged scan completed clean with exit0. The cohort composer owns official generation and combined CI; these results do not substitute for that delivery.
