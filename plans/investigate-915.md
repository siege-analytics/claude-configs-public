---
ticket_refs:
  - siege-analytics/claude-configs-public#915: comment posted (https://github.com/siege-analytics/claude-configs-public/issues/915#issuecomment-5675253634)
---

# Investigation Fact Sheet: siege-analytics/claude-configs-public#915

Canonical copy: ticket comment linked above. This file mirrors it locally
so plans/investigate-*.md resolution finds it without re-deriving.

### Verified Shapes

- **ATTESTED** hook merge point: `hooks/agent-comms/hub-concurrency-gate.sh` landed at commit `831cb85`, confirmed via `git log --oneline` on the clone.
- **ATTESTED** no drain mechanism exists pre-fix: the continuing-thread branch and new-thread-append branch are the only two places that wrote `open_threads`; neither removed an entry. Confirmed by reading the full file before editing.
- **PROBED** manual-edit is the only pre-fix drain path: reproduced empirically this session (`260915-fluid-bear`) -- hit the cap at 3 open threads, hand-edited `hub-threads.json` to free a slot.
- **ATTESTED** #896 decision log: "Decisions locked in (operator-confirmed, 2026-09-14)" -- no work-type categorization, flat cap=3 no per-hub tuning, drain-don't-cutoff, board-backlog overflow destination, board (P2/P3) unstarted.
- **ATTESTED** #898 left "closes ... after some inactivity window" as a named-but-unimplemented candidate.
- **PROBED** baseline test suite: `bash hooks/_test/hub_concurrency_gate.test.sh` on develop HEAD -> `14 passed, 0 failed`.
- **PROBED** sibling-grep: `grep -rn "open_threads|hub-threads.json" --include="*.sh" .` -> only `hub-concurrency-gate.sh` and its test file.

### Impact chain

`mcp__session__send_agent_message` -> `PreToolUse` hook dispatch -> `hub-concurrency-gate.sh`. This task adds a time-based prune before the existing cap/allow decision and fixes the block message's `#899/#900` overclaim.
