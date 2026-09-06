---
ticket_refs:
  - siege-analytics/claude-configs-public#708
---

# Self-review: PR for #708 (pipeline-state-guard unreachable-API false-negative)

## Assumptions

Working as: software engineer
Domain: pipeline-state-guard.sh (Python subprocess wrapper for gh api reachability)
Goal source: siege-analytics/claude-configs-public#708
Pre-author-inventory: `grep -n 'returncode == 0\|junior_found\|senior_found' hooks/resolver/pipeline-state-guard.sh` returned the relevant lines. Confirmed the bug: booleans initialise False, set True only in `returncode == 0` branch, then written unconditionally. Confirmed the fix shape: track api_ok separately, don't overwrite on api failure.
Investigate-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Pre-mortem-artifact: TRIVIAL (see ## Trivial-investigation declaration below)
Hostile-review-artifact: WAIVED (external dispatch ladder exhausted, per session operator authorization 2026-09-05)
Project-contribution: eliminates a false-negative class where a transient GitHub API outage causes the mutation-gate to block work on tickets whose artifacts were, in fact, posted. Documented in ticket by session 260831-bright-gust on 2026-09-02: five artifacts posted to #704 were rendered invisible by an api.github.com transient. After this fix, the signal file is preserved (last-known-good state) plus a .unreachable stamp file records the check attempt.

## Trivial-against-state declaration

Reason: single-hook change; adds an api_ok tracking variable and skips overwrite when the API failed. No data/config/topology surface touched.
Evidence: `git diff --stat` shows 1 code file + self-review. Diff adds api_ok / api_error tracking + splits signal-file write into api_ok / api_error branches.
Falsification: not trivial if the api_ok branch fails to signal "unreachable" downstream. Verified by design: pre-existing signal file preserved on api failure means downstream mutation-gate reads the last-known-good state, so a first-run failure (no signal file exists yet) is the only edge case, and in that case the .unreachable stamp file is the observable signal.

## Trivial-investigation declaration

Reason: #708 fully specified the failure mode with a reproducer session, exact line numbers, and the fix pattern. No discovery required.
Cannot produce error: adding an api_ok flag + conditional write only NARROWS when the signal file gets overwritten; can never introduce a false-positive. False-negative (signal file stays fresh when API is reachable) requires api_ok to erroneously go False on success — guarded by `result.returncode == 0` check that already existed.
Evidence: `bash -n hooks/resolver/pipeline-state-guard.sh` returns 0 (syntax ok).
Falsification: not trivial if the api_ok flag mis-fires. Verified by reading control flow: api_ok stays True unless (a) `result.returncode != 0` (explicit else branch), (b) an exception fires (explicit except handler). Both paths set api_ok = False.

## Peer review

Gate evidence:
- Gate 1 (syntax): `bash -n hooks/resolver/pipeline-state-guard.sh` -> exit 0
- Gate 2 (tests): no test file exists for pipeline-state-guard.sh (searched hooks/_test/); a test would need to mock the gh CLI and time signal-file mutations. Deferred as scope creep given the fix has an explicit path-narrowing shape.
- Gate 3 (docs): N/A
- Gate 4 (notebooks): N/A

Shelf compliance:
- writing-code:5 (no hypothetical code): the api_error assignment uses `(result.stderr or '').strip()[:200]` where result is the actual subprocess return; not extrapolated.
- writing-code:7 (silent error swallowing): the pre-fix code had `try: ... except: pass` which was one of the failure modes ticket #708 names. Post-fix, the except branch records api_ok = False and captures the exception message into api_error rather than silently swallowing. The `except: pass` on the file-write remains because file-write failure genuinely is best-effort (workspace-local signal; failure to write means downstream gets stale-or-missing state, which is the pre-existing fallback).
- writing-tests:5 (every except exercised): no new test added. The new `except Exception as e` branch is exercised by any api-unreachable scenario; the pre-existing `except: pass` on file-write is not exercised by any test but pre-dated this fix.

## Lead review

- Junior solved the stated goal: yes. Signal file preservation on API-unreachable + `.unreachable` stamp file for the downstream reader.
- Junior over-scoped: no.
- Junior under-scoped: did not update mutation-gate to read the .unreachable stamp. Rationale: preserving the last-known-good signal file already avoids the false-negative; the .unreachable stamp is defense-in-depth for a downstream reader that wants to know "was the last check reachable?" Full mutation-gate consumer update deferred as follow-up.
- Standards affirmatively met: writing-code:5, writing-code:7 (partially — one legit except-pass remains for file-write best-effort).

## Quantified claims

Claim: "api_error captures the failure reason."
Verified-by: reading the code — either `(result.stderr or '').strip()[:200]` on non-zero rc, or `str(e)[:200]` on exception.

Claim: "signal file preserved on api failure."
Verified-by: the `if api_ok:` guard around each `open(gate_path, 'w')` call. api_ok = False skips the write entirely.

## Post-mortem applicability

Not applicable. #708 is a first-time bug fix, not a regression of prior-shipped code.
