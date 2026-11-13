## Assumptions
Goal source: issue #1351 and the scanner fixture review on promotion PR #1335. Read ScannerExecution fixture setup and Git operations, shared Gates setup, the private-index scanner test and explicit hostile-environment callbacks. Fixture-owned Git must not inherit caller repository, index, object or configuration routing. Explicit hostile inputs to the actual scanner and hook remain intact.

## Test plan
Controlled red: an owned outer temporary repository received the scanner fixture origin through inherited GIT_DIR. The permanent snapshot regression failed on changed outer configuration; its second routing-vector case encountered that first mutation's duplicate origin. After correction, the regression preserves outer worktree/config/index/object bytes and modes through nested initialization, remote changes, staging and commit. It reintroduces poisoned ambient and explicit environments after setup, so clearing the default fixture environment cannot hide later Git-helper behavior.

The actual scanner suite passed 19 tests in 33.871 seconds through the supported unbound content-bound producer. The shared Task suite passed all 97 tests in 287.380 seconds. Private-index construction remains explicit; its inherited-index denial and other actual hostile-environment/foreign-scope controls still pass. Full build and official inventory/authority/language/data generation passed. Final freshness and scanner results are recorded before publication. No production policy, live caller repository, global Git configuration or runtime installation changed.

## Findings
Use one reusable fixture_git helper to remove inherited GIT_ variables before the first Git init and every scanner-fixture Git call. The only intentional routing override is the existing owned private index passed as index_file. The default shared fixture environment also removes inherited Git values; callbacks supplying hostile environments are unchanged. The regression independently snapshots the outer repository rather than asserting the helper's implementation.

## Independent review
Root read the full two-file source diff and accepted the bounded test-only change. Root ran the re-poisoned outer-repository preservation regression: it passed in 0.407 seconds. Root did not independently rerun the shared 97-test suite. Required exact-head CI and a direct PR review remain separate from these local results.
