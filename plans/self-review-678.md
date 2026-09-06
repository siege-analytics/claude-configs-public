---
ticket_refs:
  - siege-analytics/claude-configs-public#678
  - siege-analytics/claude-configs-public#668
  - siege-analytics/claude-configs-public#655
---

# Self-review: PR for #678 (CHECK_FN replaces sentinel BIN_NAME)

## Assumptions

Working as: software engineer
Domain: probe orchestration (probe_run + wrappers)
Goal source: siege-analytics/claude-configs-public#678 (Part-of: #668 / #655)
Pre-author-inventory: `grep -n '__.*_absent__' scripts/probe/*.sh` returned matches in playwright.sh and vitest.sh + a comment mention in _common.sh. `grep -n probe_run scripts/probe/*.sh` returned 6 wrappers using it; playwright/vitest pass sentinel bin names as arg 2. probe_run at _common.sh:214 (pre-fix) called _probe_check_bin for both pre-check and post-install re-check with the same BIN_NAME.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates a P0 false-negative class where playwright/vitest post-install re-check always reported "not installed" because the sentinel bin name was unresolvable by construction. Under `tool_install_policy: allow` (SKILL.md's CI recommendation), the runner installed the tool successfully but the probe re-checked against sentinel, saw "absent", and filed a public infra ticket — every CI run adds another duplicate (pre-#680) or now returns reused=true (post-#680), but either way the probe never observes the successful install.

## Trivial-against-state declaration

Reason: adds two dispatch helpers (_probe_check_target, _probe_get_version_target) + replaces 2 sentinel-based wrapper invocations + one new test scenario. No data/config/topology surface.
Evidence: `git diff --stat` shows scripts/probe/_common.sh (helpers + probe_run bin_name -> target rename), scripts/probe/playwright.sh (drop inline pre-check + sentinel; call probe_run with CHECK_FN), scripts/probe/vitest.sh (same shape), scripts/probe/_test_probe_common.sh (AC10), plans/self-review-678.md.
Falsification: not trivial if the bash `declare -F` + function-reference call pattern doesn't work portably. Verified against bash 3.2 (macOS default) and 5.x via existing test suite (function-body call pattern is bash builtin, portable).

## Trivial-investigation declaration

Reason: #678 named the design directly (CHECK_FN as second arg, replaces sentinel, both pre-check and re-check use it). No discovery required.
Cannot produce error: the dispatch is fail-open. If the second arg happens to be a real binary name, _probe_check_target falls through to _probe_check_bin exactly as before. If it's a function name, the function is called. The failure mode "CHECK_FN name typo" would surface as a runtime "command not found" INSIDE probe_run, which becomes a return-1, which flows through to the absent branch (same as before). Not a regression.
Evidence: `bash scripts/probe/_test_probe_common.sh` returns "10 passed, 0 failed" (9 pre-#678 + AC10 new).
Falsification: not trivial if the change breaks the wrappers that still pass bin names (pytest, schemathesis, great-expectations, k6). Verified by reading each wrapper: all pass a real bin name, none uses declare -F to disambiguate; probe_run's _probe_check_target correctly falls through to _probe_check_bin for those.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n scripts/probe/_common.sh scripts/probe/playwright.sh scripts/probe/vitest.sh` -> exit 0
- Gate 2 (tests): `bash scripts/probe/_test_probe_common.sh` -> "10 passed, 0 failed"
- Gate 2b (AC2 mechanical grep): `grep -c '__.*_absent__' scripts/probe/*.sh` returns 0 across all wrappers (was 2 pre-#678: playwright.sh and vitest.sh; the earlier comment in _common.sh was rephrased to remove the literal token)
- Gate 3 (docs): the new dispatch helpers carry inline comments naming #678 and the CHECK_FN semantics
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical): AC10 exercises the CHECK_FN dispatch with a real toggle-file check function; the install command actually touches the file; the post-check actually flips.
- writing-code:7 (no silent swallow): dispatch is explicit (if declare -F succeeds, call the function; else _probe_check_bin). Failure returns 1 through normal control flow.
- writing-tests:1 (tests fail on revert): AC10 uses a synthetic check function that returns 1 pre-flag and 0 post-flag; reverting _probe_check_target to always call _probe_check_bin makes AC10 fail because "_probe_check_fake_tool" isn't a binary.
- writing-claims:8 (specific counts): "6 wrappers use probe_run; 2 (playwright, vitest) pass CHECK_FN; 4 (pytest, schemathesis, great-expectations, k6) pass bin names" — verified by grep at HEAD.

## Lead review

- Junior solved the stated goal: yes. AC1 (playwright install-then-detect) demonstrated by AC10 with a synthetic tool; AC2 (no sentinel bin names) verified by grep.
- Junior over-scoped: no. Kept the other 4 wrappers unchanged (they pass real bin names; nothing to change).
- Junior under-scoped: didn't add a real playwright integration test. Rationale: real playwright install would need an npm cache + network, outside the test-harness's fail-fast contract. The synthetic AC10 covers the dispatch logic; the ticket's own AC1 with real playwright is deferred to a full-CI environment.
- Standards affirmatively met: writing-code:5, writing-code:7, writing-tests:1, writing-claims:8.

## Quantified claims

Claim: "10/10 tests pass."
Verified-by: `bash scripts/probe/_test_probe_common.sh` returns "Summary: 10 passed, 0 failed."

Claim: "no sentinel bin names remain."
Verified-by: `grep -c '__.*_absent__' scripts/probe/*.sh` returns 0 across all 6 wrappers + _common.sh + _test_probe_common.sh.

Claim: "4 wrappers still use real bin names (pytest, schemathesis, great-expectations, k6); 2 now use CHECK_FN (playwright, vitest)."
Verified-by: `grep 'probe_run ' scripts/probe/{pytest,schemathesis,great-expectations,k6,playwright,vitest}.sh` shows the split.

## Post-mortem applicability

Not applicable. First-time fix for P0 finding; the sentinel pattern was the original design and needed structural replacement, not revert.
