# Scanner Git minimum and publication fixture causality

## Assumptions

The assigned follow-up is issue #1389. Read the two PR1335 review findings, `scan_snapshot.py`, scanner execution closure pins, the scanner skill, and both affected publication fixture methods. Git 2.45 introduced `--no-lazy-fetch`; retain that safety flag rather than silently attempting source selection on older Git. Official documentation: https://git-scm.com/docs/git/2.45.0.html . The published first cut and its immutable publisher are independent of this follow-up.

Pure message scanning must remain usable without Git. The minimum applies only inside source snapshot selection. A version diagnostic does not grant execution, Task scope, or network authority. Native host PATH/version still needs actual installation qualification; local CLI proof does not establish a GUI process environment.

## Test plan

A controlled Git 2.44 executable reports its version but writes a marker on every other invocation. Before the fix, all three source modes failed with the generic subprocess diagnostic and reached that marker. After the fix, staged, working and PR modes return actionable incomplete status before any source Git operation. Non-Git inline/file message scans retain findings/clean results without touching Git. Existing full source and typed scanner suites cover supported Git behavior and physical producer closure.

The two negative publication loops now construct real Tier B fixtures instead of accepting an unrelated downgrade denial. Both tool and native publication adapters run for each B/C compact/historical variant. The prior private corrected-oracle probe passed both methods in 11.718s before the follow-up was authored.

## Findings

No new exception handler, fallback, Git configuration mutation or receipt field is introduced. The four source-closure pins follow snapshot, capability, adapter and typed dispatcher content. Source 28 tests passed in 26.944s, publication 39 in 91.246s and typed scanner 30 in 42.942s. The full review-risk suite passed. All six official freshness checks passed. The staged scan completed nonclean with 43 findings: 42 inherited unchanged-handler diagnostics and one intentional banned-word message input, whose expected findings result is the regression oracle. Raw SHA256: dd089a2cacb561c4bd0f33aa9819b5deb37ac2ee4e7f3b32121a2769327e51a4. Individual dispositions and raw output are retained in the private evidence directory core1389-scanner-git-minimum-20261113; inherited debt remains issue #1329.

## Independent review

Root independently inspected the exact source, all closure pins and 43 findings and accepted their scoped dispositions. The unchanged authored suite counts above were not independently rerun by Root. The exact reviewer-authored acceptance is preserved in plans/scanner-git-minimum-1389-independent.json. No clean-scan or runtime-installation claim is made.
