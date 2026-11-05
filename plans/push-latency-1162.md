---
ticket_refs:
  - siege-analytics/claude-configs-public#1162: comment posted
  - siege-analytics/claude-configs-public#1163: comment pending
---

# Self-review: hook push latency and router timeout message (#1162, #1163)

## Assumptions

Goal source: #1162
Working as: software engineer, tech lead
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1162#issuecomment-6650243266
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1162#issuecomment-6650243266
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1162#issuecomment-6650243266
Hostile-review-artifact: PENDING. The cross-family hostile review is commissioned by the Siege Claude Hub at this PR's head. It has not run, and nothing in this artifact claims it has.
Project-contribution: agents on macOS can push again without hook timeouts, and a hook timeout names the slow hook instead of sending people after a reinstall.

- The hooks need `/home/craftagents/bin` only on the Linux host where it exists. On macOS `/home` is an autofs mount and the directory is absent, so each command lookup through it pays an automount miss (#1162 fact sheet F1, F2).
- A quoted or heredoc mention of a push is data, not a push. `hooks/lib/command-text.sh` already draws that line for other guards and falls back to the raw text when its helper cannot run (F4).
- Only receipt, router copy, generation and global registration faults are repaired by the exact-main installer (F6, F7).
- Hook timeouts and `TOTAL_SECONDS` stay unchanged. The fix removes cost instead of raising limits.

## Peer review

Shelves: writing-code:1 (one shared helper instead of 25 copies), writing-tests:2 (each fix has a negative and a positive case), writing-claims:1 (every timing below was measured on this machine).

Gate evidence, all run in this worktree on macOS with Python 3.11.11 and PyYAML 6.0.3:

- `bash -n` on every changed hook: exit 0.
- `hooks/_test/hook_path.test.sh`: 10 passed, 0 failed.
- `hooks/_test/test_tracking_guard.test.sh`: 19 passed, 0 failed (11 new cases).
- `bin/_test/craft_hook_router_test.py`: 36 tests OK (5 new).
- `hooks/_test/catalog_guard.test.sh`: 398 passed, 0 failed.
- `hooks/_test/git_hook_fast_skip.test.sh`: 327 passed, 0 failed.
- `bin/_test/review_risk_test.py`: PASS.
- `bin/validate-local.py --mode refresh`: passed (regenerated `catalog/skills-inventory.json` and `catalog/review-risk-metrics.json`).
- Mutation checks, each in a fresh scratch copy (`cache/mutation_proofs.py`, not committed). Every one made its test fail:
  - M1: raw PATH prefix restored.
  - M2: fatal helper source line.
  - M3: raw-text trigger.
  - M4: listing failure ignored.
  - M5: installer advice on every error.
  - M6: anonymous timeout message.

Full suite status, stated as it is:

- `bin/validate-local.py --mode full` FAILED at "Project procedure and resident composition".
  - 12 failures in `bin/_test/selected_registration_test.py`.
  - 9 come from macOS temp paths under the `/var` symlink. They pass with `TMPDIR=/private/tmp`.
  - 3 ("managed settings command has wrong vector or event") fail identically on unmodified develop 94dd034f2c.
  - That run stopped at that step, so later steps did not run in it.
- A direct run of every `hooks/_test/*.test.sh`, every `bin/_test/*_test.py` and `bin/validate-hooks.py` was still running when this commit was made.
  - So far its only failure is `hooks/_test/ca_enforcement_runtime.test.sh`.
  - The 4 failing cases check that a spoofed Craft environment is not trusted. This session runs inside a real Craft process, so the ancestry probe finds real Craft.
  - My diff does not touch `detect-host.sh` or `ca-enforcement-gate.sh`.
- Protected CI on the exact head is the required full run.

Defect found by the existing suite and fixed before commit:

- `catalog-guard.sh` runs `set -e`, so a plain `source` of a missing helper exited 1. That is a non-blocking hook error, which would have failed open.
- `|| true` does not help under macOS bash 3.2.
- Every hook now sources `/dev/null` when the helper file is absent.

## Lead review

- Every guard stays fail-closed.
  - A missing command-text library leaves the raw command as the match text.
  - A missing PATH helper leaves PATH unchanged and the hook reaches its own decision.
  - A listing that fails or passes its 6 s bound blocks with its reason. Before, `|| echo ""` read a failed listing as "no offenders".
- `hooks/bash/universal-mutation-gate.sh` changes only at its PATH line (coordination with the #1160 worker). `hooks/lib/task_actions.py` and `hooks/lib/resolve-think-gate.py` are untouched.
- `RegistrationError` and `HookTimeout` subclass `RoutingError`, so callers that catch `RoutingError` behave as before.
- Known limit: `scan.sh` still starts processes per message line. A message far longer than 75 lines can still approach 15 s; that cost is #1150.
- Known limit: the timing case proves the speedup only where the slow directory lookup exists (macOS). On Linux CI the helper and structural checks carry the protection.
- Known limit: the tracking-guard deny on a slow listing blocks a push from a repository whose ignored tree takes over 6 s to walk. That push was already denied by the router timeout before this change; the new message names the repo and the bound.

## Quantified claims

All measured on this Mac with `cache/probe_fp.sh` and `cache/probe_ttg*.sh` against the hub's 75-line message (`msg-hookform.txt`) and the Craft workspace repository:

- `detect-ai-fingerprints.sh`, 75-line message: before 16.68 s, 17.79 s, 17.21 s (timeout 15 s); after 5.93 s, 5.71 s, 5.98 s.
- `test-tracking-guard.sh`, quoted issue title mentioning a push, workspace repo: before 46.97 s and exit 2; after 0.16 s and exit 0.
- `test-tracking-guard.sh`, real push shape, workspace repo: before 43.68 s; after 3.86 s, still exit 2 (7,033 ignored test files under `tests/`).
- Pathspec listing alone in that repo: 3.3 s for 7,033 paths, against 5.9 s for all 78,943 ignored paths.
