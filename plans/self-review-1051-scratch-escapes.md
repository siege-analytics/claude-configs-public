---
ticket_refs:
  - siege-analytics/claude-configs-public#1051: gates must be task-keyed
---

# Self-review: pin scratch-folder escapes (#1051 B1)

## Assumptions

Pre-author-inventory: on v3.5.73, a peer session probed escapes from a session's own `data/` folder. All of them were blocked (rc=2), but only `.''./` and `env -C` were pinned in `read_allowlist`.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1051
Project-contribution: the scratch allowance cannot widen silently; every probed escape shape is now a must-block fixture.

- Test-only change. No hook behaviour changes.

## Peer review

- **writing-tests:**
  - 17 must-block cases: relative, home, absolute and `/tmp` targets for touch, redirect, cp, ln, mv, tee and mkdir; `cd ..` compounds; and five `rm -rf` escape forms.
  - 2 allow cases: `echo x > out.txt` and `mkdir sub` inside scratch.
- **Gate evidence:** read_allowlist 267/267.

## Test plan

- Run `bash hooks/_test/read_allowlist.test.sh`. All 267 cases must pass.
- The 17 new must-block cases run with the session's own `data/` folder as cwd, so a loosening of the scratch allowance turns them red.

## Lead review

- Closes the coverage gap. The behaviour was already correct.

## Quantified claims

- New cases: 19 (17 block, 2 allow).
