---
ticket_refs:
  - siege-analytics/claude-configs-public#1099: session resolution trusts a mis-tagged CRAFT_SESSION_DIR over the payload's session
---

# Self-review: #1099 a mis-tagged session dir cannot borrow another session's gates

## Assumptions

Pre-author-inventory: in the electinfo#375 review, session A's turn, handed session B's directory, wrote under B's implementing gate. electinfo's retired override blocked it.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1099
Pre-mortem-artifact: plans/pre-mortem-1099-session-anchor.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1099#issuecomment-6289066846
Project-contribution: the task-keyed gate's per-session authority holds even when the host mislabels the session.

- The fix is `hooks/lib/session_anchor.py`, one helper for three call sites:
  - `resolve-think-gate.py` corrects its own environment at import, so every resolver path and every child process sees the verified directory;
  - the mutation gate's pre-mortem lookup uses the verified directory;
  - the hub gate's own-state directory uses the verified directory.
- The correction is reported on stderr.

## Peer review

- **writing-code:** `verified_session_dir` keeps the env dir unless its anchor proves it belongs to another session. Otherwise it takes the sibling whose anchor matches, or a session that exists in name only.
- **writing-tests:** `session_anchor_mistag.test.sh` has 13 cases, using Craft's real anchor format (`{"anchors": {msg-id: {"sdkSessionId": ...}}}`, appended per final message and never pruned):
  - the no-anchor fallback, the controls, and the mis-tag;
  - a mis-tag to an unknown session, and a mis-tag onto an un-anchored sibling;
  - an SDK id rotation, and the first turn after one;
  - a FIFO at an anchor path;
  - recovery to the turn's own gate, and the report.

  Develop fails the mis-tag cases.
- **Hostile review (first version: NOT-MERGE-SAFE), all fixed here:**
  - **Blocker:** only the first UUID was read, so a session lost its own gate after Craft rotated its SDK id. Every recorded `sdkSessionId` now counts.
  - **Should-fix:** a mis-tag onto an un-anchored sibling was accepted. A sibling whose anchors claim the payload id now wins even when the env dir has none.
  - **Should-fix:** a FIFO at an anchor path hung the hook. Anchors are now read non-blocking, regular files only, with a 4 MiB cap.
  - **Should-fix:** `session_anchor.py` is now a Tier C path in `catalog/review-risk-policy.json`.

  Accepted rather than fixed:
  - the first turn after a rotation, before Craft records the new id, fails closed;
  - the hub cap stays fail-open for a session in name only, by its own design: unknown roles are not capped;
  - `skill-enforcement-gate.sh` (advisory) still reads the raw env dir.

- **Verification review:** a second reviewer re-ran the first review's attack script. Every blocker and should-fix is resolved, and nothing is looser than develop. Its one open item, the cost of scanning siblings when the session has no anchors, was measured here: about 128 ms per gate call at 500 sessions × 200 anchors. A substring prefilter cut that to about 20 ms.

## Test plan

- `bash hooks/_test/session_anchor_mistag.test.sh`: 13/0 here; the mis-tag cases fail on develop.
- `python3 hooks/_test/task_keyed_gates.py`: 50/50.
- The hub_concurrency_gate, session_signal_resolution, universal_mutation_gate and read_allowlist suites.
- The full CI validate job, run locally.

## Lead review

- **Solves #1099:** yes.
- **Out of scope:** `skill-enforcement-gate.sh` reads `CRAFT_SESSION_DIR` for advisory state only.

## Quantified claims

- 13 cases. The existing suites pass: 50 + 26 + 18 + 29 + 267.
