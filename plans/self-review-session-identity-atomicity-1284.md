---
ticket_refs:
  - siege-analytics/claude-configs-public#1284: self-review posted
---

# Self-review: bounded own-dir ENOENT retry for session binding (#1284)

## Assumptions
Working as: software engineer (implementer), tech lead (lead review); independent review still required on the PR
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket siege-analytics/claude-configs-public#1284 (hook-side fix lane 1 and its Acceptance section)
Goal source verification: `scripts/discipline/evaluate-ticket.sh siege-analytics/claude-configs-public#1284` → BLOCK (missing Context/Goal headings, design reference, Assumptions block); see the exemption block below.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6784832751
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6784832751
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6784832751
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6784832751
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6785390128
Project-contribution: removes spurious own-session fail-closed refusals caused by Craft's non-atomic session.jsonl replacement, without changing any authority outcome, and makes the failed binding check visible to callers and in bound router events.

The hostile review linked above is a fresh-context adversarial pass started by this worker session. It is not an independent approval; independent review on the PR is still required.

## Exemption: evaluate-ticket structural sections

Reason: the issue body states context ("Observed", "Measurement", "Mechanism"), the goal ("Fix lanes" 1) and acceptance ("Acceptance"), but not under the rubric's literal headings. The worker's scope permits comments on #1284 only, not edits to the issue body.
Evidence: https://github.com/siege-analytics/claude-configs-public/issues/1284 has the sections `### Observed`, `### Measurement`, `### Mechanism`, `### Fix lanes` and `### Acceptance` (`gh issue view 1284 -R siege-analytics/claude-configs-public`). The design, investigation, pre-mortem, Junior description and Senior checklist are at https://github.com/siege-analytics/claude-configs-public/issues/1284#issuecomment-6784832751.
Falsification: the exemption is wrong if #1284's body lacks an acceptance criterion this diff can be tested against. The criterion is "with the own session.jsonl briefly absent ... the binding still resolves; absent beyond the bound, or a foreign/multi match, it still fails closed".

## Test plan
- `bin/_test/session_anchor_enoent_test.py` (13 tests): transient own ENOENT x1-4 binds; x5 and x1000 fail closed after exactly 5 opens; a real filesystem move-aside window binds; a real missing header fails closed; EACCES/ELOOP/EIO, nlink=2, parse, duplicate-field, id-mismatch and invalid-sdk-id are never retried; a non-env directory's ENOENT is never retried; the retry reproduces the race-free result for mis-tag correction, no-claim and multi-match layouts; multi-match with own ENOENT still fails closed; router-bound child-hook re-verification (`verified_session_dir`) survives the window and sets UNRESOLVED beyond it; the diagnostic carries no paths; the backoff stays fixed and at most 30 ms.
- `bin/_test/craft_hook_router_test.py`: 4 new tests. Transient own ENOENT binds and records `own_enoent_retries` in the router event. Beyond the bound it fails closed, names `Binding check: enoent.` and writes no event. Multi-match names its check and writes no event. A mis-tagged env dir whose header fails any check (`id-mismatch`, `parse`, `sdk-id-invalid`, `no-match`, `nlink`, `enoent`) receives no event.
- Revert proofs: (1) with the retry disabled (`OWN_HEADER_ENOENT_BACKOFF = ()`), there are 13 failures (subtests included) across 9 of the 13 anchor tests, covering every retry-dependent case, and the router retry test fails. The 4 fail-closed negative tests still pass, as intended. (2) The pre-review router (unbound audit to the env dir) fails the 3 no-foreign-write router tests.
- Full hook scenario loop (CI step "Hook scenario tests").

## Peer review
- Gates: `python3 -m py_compile hooks/lib/session_anchor.py hooks/lib/craft-settings-router.py` → exit 0; `session_anchor_enoent_test.py` → 13 passed; `craft_hook_router_test` → 40 passed; `bin/skill-inventory.py --check` → current; `bin/generated-source-authority.py --check` → current; docs/notebooks N/A (none affected).
- writing-code:1 (smallest correct change): the retry is confined to one loop in `registered_session_binding`. The existing helpers keep their contracts and become thin wrappers.
- writing-tests:1 (failure cases first): every negative path in the pre-mortem has a fixture, and both revert proofs show the new tests fail without the fix.
- writing-claims:3 (no class over-claim): the artifact claims only the ENOENT window. The partial-header (`parse`) window is reported as uncovered (H5).
- Correctness: only `errno.ENOENT` from `os.open` maps to `enoent`. `fstat`/`readline` errors map to `oserror`. The `path` checks run before `open`, so a symlinked or escaped path never reaches the retry. Evidence: `test_non_enoent_oserror_is_not_retried` and `test_nlink_parse_and_identity_failures_are_not_retried`.
- Boundedness: the retry loop is `while check == 'enoent' and retries < len(OWN_HEADER_ENOENT_BACKOFF)`, with a 4-entry tuple and a `_sleep` call per iteration. Evidence: `test_enoent_beyond_the_bound_fails_closed_after_fixed_attempts` asserts exactly 5 opens and the exact sleep sequence.
- Authority: match counting is the same code as on base. The retry only replaces an ENOENT read of the env-named directory with a later read of that same directory. Evidence: `test_retry_reproduces_the_race_free_read_only`.
- API compatibility: `_registered_header` and `registered_session_dir` keep their signatures and return values. `session_context` keeps its 3-tuple and only gains an optional `diagnostics=None` parameter. All 36 pre-existing router tests still pass.
- Logging: `binding_audit` whitelists 6 fields by exact type, and string values must match `[a-z-]{1,32}`. Unbound decisions write nothing (Finding H1).
- Resource handling: the fd from `os.open` is wrapped by `os.fdopen` in a `with` block, the same as on base.

## Lead review
Approach fit: the hook-side lane is a mitigation, not the root fix. The app-side atomic rename (craft-agents-oss) remains the root fix and also removes the H5 partial-header window. A retry confined to the env-named header is the smallest change that removes the measured ENOENT-only failure without a new authority path.
Class vs instance: all three consumers — router `session_context`, `registered_test_provider`, and child-hook `verified_session_dir` (the "Session id unresolved" variant) — go through `registered_session_binding`, so the class is closed for the ENOENT window. Foreign-directory windows (Elephant 1, pre-existing) are deliberately not retried.
Blast radius: `registered_session_dir` HIGH (router x2, `verified_session_dir` → universal-mutation-gate and hub-concurrency-gate); `_registered_header` MEDIUM. Installed workspaces receive the change only through exact-main registration, because the receipt pins `session_anchor_sha256` and `router_sha256`.
Post-mortem applicability: not triggered. This is a mitigation for a host behaviour (non-atomic session.jsonl replacement), not a revert or a regression in shipped scaffold code. No pre-mortem Tiger materialized in shipped code; H1 was caught before commit.
Sequencing assumption: Craft's replacement window stays well under 30 ms. The issue's measurement implies about 2 ms; if it grows, the binding fails closed exactly as on base.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| H1 | P1 | Unbound router events could be written into a mis-tagged foreign env dir | fixed |
| H2 | P2 | No-foreign-write test covered only the safe case | fixed (H1 tests) |
| H3 | P3 | The retry keys on the env-named dir, not necessarily the caller's own | noted; comment corrected; outcome equals the race-free read |
| H4 | P3 | Misleading test name | fixed |
| H5 | P3 | A partial-header (`parse`) window is not retried | noted; app-side atomic rename lane |
| H6 | P3 | Up to 30 ms per re-verification when a header is persistently missing | noted |
| H7 | P3 | Pending own-header-ok case is diagnosed only in the refusal note | noted |
| H8 | P3 | Test wrapper uses `python3` from PATH | noted; matches existing wrappers |

## Adversarial shape audit

Shape space: the states of `sessions/<id>/session.jsonl` that a header read can observe — present and valid; absent (ENOENT); other open errors; non-regular; hard-linked; oversize; unparseable or duplicate-field; wrong id; invalid SDK id — crossed with directory role (env-named or not) and match multiplicity (0, 1, more than 1).
Fixture-covered shapes: valid (1, `test_happy_path_binds_without_any_sleep`); ENOENT transient (4, `test_transient_own_enoent_within_the_bound_binds`) and persistent (2 injected plus 1 real, `test_enoent_beyond_the_bound_*`, `test_real_missing_header_*`); real rename window (1); other errno (3, EACCES/ELOOP/EIO); nlink (1); parse (2); id-mismatch (1); sdk-id-invalid (1); non-env ENOENT (1); mis-tag/no-claim/multi-match layouts (3); router mis-tag headers (6 checks).
Prose-vs-implementation gap: `oversize` and `not-regular` are classified but not separately exercised in the new tests. Their pre-existing fail-closed behaviour is unchanged, and they never retry because only `enoent` loops.
Adversarial frame this round: security engineer
Adversarial fixture from frame: `test_mistagged_env_dir_with_failing_header_receives_no_event` in `bin/_test/craft_hook_router_test.py`. It models a #1099 mis-tag in which an attacker-shaped or half-written sibling header tries to attract the caller's audit write or binding.

## Quantified claims
- "13 tests" in `session_anchor_enoent_test.py": `/usr/bin/python3 bin/_test/session_anchor_enoent_test.py` → `Ran 13 tests ... OK`
- "40/40 router tests" and "36 pre-existing": `cd bin/_test && /usr/bin/python3 -m unittest craft_hook_router_test` → `Ran 40 tests ... OK`; `git diff bin/_test/craft_hook_router_test.py | grep -c '^+    def test_'` → 4
- "77 files, 73 pass, 4 fail": `debug/run-hook-suite.sh` → `files=77 failed=[ ca_enforcement_runtime session_signal_resolution universal_mutation_gate universal_mutation_gate_empty_reporoot]`; `grep -c '^PASS'` → 73
- "18/18, 31/31, PASS" with host session env unset: `debug/run-one-clean.sh <tree> hooks/_test/<file>` → `Results: 18 passed, 0 failed`; `Results: 31 passed, 0 failed`; `universal_mutation_gate_empty_reporoot.test: PASS`
- "ca_enforcement_runtime fails identically on base": `debug/run-one.sh <clean base extract> hooks/_test/ca_enforcement_runtime.test.sh` → `Results: 12 passed, 4 failed` (the same 4 names)
- "127/127 ENOENT", "~2 ms window": from the issue's Measurement section (127 of 319,639 reads failed, all ENOENT; 13 replacements in 60 s); the window is an inference: 127/13 ≈ 10 failing reads at about 0.19 ms spacing.
- "0.1 ms" and "7.8 ms": `debug/repro_1284.py` output on base and on the fix.
- "13 failures across 9 of the 13 anchor tests": the mutation tree run `session_anchor_enoent_test.py` → `Ran 13 tests ... FAILED (failures=13)`, with failure lines in 9 distinct test names (backoff, beyond-bound x2, multi-match, real window, real missing, race-free x2, child hook, within-bound x4)

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Hostile review H1 (unbound audit to env dir) | designed the unbound-logging rule without modelling the #1099 mis-tag as hostile | 1 adversarial read | 4 router Edits, 3 tests, a second full suite | about 1:10 |
| Mutation proof showed a vacuous loop (`ATTEMPTS` derived from the tuple) | derived the expectation from the code under test | 1 mutation run | 1 test edit | about 1:2 |
| Junior heading not recognized | did not check the detector's heading vocabulary | 1 grep | 1 comment edit | about 1:2 |
