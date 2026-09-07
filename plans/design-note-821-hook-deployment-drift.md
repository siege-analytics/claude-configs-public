# Design note: #821 workspace hook deployment drift

## Goal

Fix workspace hook deployment drift so hook changes merged to `main` or `develop` do not remain invisible to active Craft Agent workspace sessions without an explicit, auditable deployment signal.

Goal source: siege-analytics/claude-configs-public#821 and operator instruction in session 260905-clever-quasar to drive the repair to completion with Siege Utilities sessions.

## Current-state inventory

Inputs read:

- `bin/install.sh`
- `bin/install-hooks.sh`
- `bin/verify-enforcement.sh`
- `bin/build.py`
- `.claude/settings.json`
- issue #821 body
- live workspace report from session 260525-long-swan

Measured behavior:

- `bin/build.py --deploy --craft-workspace <workspace>` copies `dist/flat/hooks/` into `<workspace>/hooks/` and writes `<workspace>/deploy-stamp.json` with `commit`, `timestamp`, and `repo_root`.
- `bin/install.sh` is the full install path: build/deploy flat layout, install hook settings, wire enforcement, then verify enforcement.
- `.claude/settings.json` registers hook commands as paths under `hooks/...`, so active sessions use the workspace copy, not the repo checkout copy.
- Existing self-review enforcement checks `deploy-stamp.json` for hook/skill/rule commits before push, but that protects authorship/push claims. It does not warn active workspace sessions that their deployed hook copy is stale after a merge to `main`.
- `verify-enforcement.sh` proves enforcement is wired/live but does not compare deployed hook content against the repo copy or a requested source commit.

Observed failure:

- PR #817 landed the repo-side carve-out for evidence-bearing issue creation/comment.
- Session 260525-long-swan still hit the pre-#817 workspace copy of `hooks/bash/destructive-guard.sh`.
- The stale workspace hook blocked the first exercise of the newly merged carve-out, so the deployed runtime did not match repo `main`.

## Problem statement

Hook source and hook deployment are two separate states:

1. repo source state: `hooks/**` in `siege-analytics/claude-configs-public`
2. workspace runtime state: `~/.craft-agent/workspaces/<workspace>/hooks/**`

Merging a hook fix updates state 1 only. Active sessions execute state 2. Without a visible drift check, sessions can keep enforcing stale logic and reasonably believe a merged repair is live.

## Design constraints

- Do not silently auto-mutate the workspace on every hook invocation. Hook execution must remain fast and predictable.
- Do not block read/exploration because the deployed hooks are stale; that recreates workspace-wide deadlock.
- Do block claims that hook fixes are live/deployed unless deployment evidence exists.
- The repair must be auditable and testable without depending on network access.
- Prefer an explicit sync command/runbook over hidden magic.

## Proposed implementation

### 1. Add a deployment drift checker script

Add `bin/check-deploy-drift.py`.

Inputs:

- `--repo-root <path>`: repo checkout containing source hooks
- `--workspace <path>`: Craft Agent workspace containing deployed hooks
- `--scope hooks` for v1
- optional `--json`

Checks:

- workspace `deploy-stamp.json` exists and has non-empty `commit`, `timestamp`, and `repo_root`
- deployed `<workspace>/hooks` exists
- compare a small manifest of hook file hashes between repo `hooks/**` and workspace `hooks/**`, excluding `_test/**` if needed for runtime-only mode
- report files missing, extra, or hash-different
- report `stamp.commit != repo HEAD` separately from file hash drift

Exit codes:

- 0: no drift
- 1: drift detected
- 2: bad invocation / unreadable paths

### 2. Add an explicit sync command wrapper

Add `bin/sync-workspace-hooks.sh` as the operator/runbook command:

```sh
bash bin/sync-workspace-hooks.sh --yes --workspace ~/.craft-agent/workspaces/my-workspace
```

Behavior:

- runs `python3 bin/build.py --layout flat --deploy --craft-workspace <workspace>`
- runs `bash bin/install-hooks.sh --workspace <workspace> --hooks-root <workspace>`
- runs `python3 bin/wire-enforcement.py --workspace <workspace>` if present
- runs `bash bin/verify-enforcement.sh --target <workspace> --mode craft-agent`
- runs `python3 bin/check-deploy-drift.py --repo-root . --workspace <workspace> --scope hooks`

This makes the deployment action explicit, idempotent, and auditable.

### 3. Surface drift in resolver guidance

Update `RESOLVER.md` or install docs to include:

- when a hook PR merges, run `bin/sync-workspace-hooks.sh`
- if a session sees behavior inconsistent with merged hook code, run `bin/check-deploy-drift.py`
- active sessions may need restart/reload if the host caches hook settings, but copied hook files update in place

### 4. Hook-edit promotion gate

Keep existing self-review deploy-stamp check. Extend it only if needed after the drift checker exists:

- hook/skill/rule commits must cite deploy evidence before declaring runtime availability
- no read/exploration block solely for drift

This is intentionally narrower than adding a preamble to every hook. A per-hook preamble would duplicate I/O in every Bash/UserPrompt hook and could create startup deadlocks. V1 should provide an explicit checker plus sync command.

## Tests

Add `bin/_test/check_deploy_drift_test.py` covering:

1. matching repo/workspace hook tree exits 0
2. workspace missing a hook exits 1 and reports missing
3. workspace hook with stale content exits 1 and reports changed
4. missing deploy-stamp exits 1 with stamp diagnostic
5. `stamp.commit` differs from repo HEAD exits 1 with stamp diagnostic

Add a shell test for `sync-workspace-hooks.sh --dry-run` if a dry-run flag is included; otherwise keep the script simple and validate through `check_deploy_drift_test.py` plus existing build/install tests.

## Rollout

1. Implement checker and tests.
2. Add sync wrapper and docs.
3. Merge to `develop` and promote to `main`.
4. Run the sync command once for `my-workspace` so active sessions receive the new hooks.
5. Notify Siege Utilities sessions that #821 is resolved and they should re-test issue-reporting without evidence-chain override.

## Non-goals

- No symlink deployment in v1. Symlinks can be considered later, but copy deployment is the current build model.
- No automatic network pull or main-branch fetch inside hooks.
- No global block of all commands when drift is detected.
- No #819/#820 hook-logic fixes in this PR.

## Open questions for coordinator review

1. Should `_test/**` hooks be included in the hash drift manifest? My recommendation: include them for repo/workspace equality because tests are useful to deployed diagnostics, but allow a future `--runtime-only` flag if needed.
2. Should `sync-workspace-hooks.sh` default to `my-workspace` or require `--workspace`? Recommendation after hostile review: default path is acceptable for UX, but `--yes` is required before any workspace mutation so the target path is printed/auditable and accidental default mutation is blocked.
3. Should the final rollout run the sync command from this session after merge to `main`? My recommendation: yes, with `--yes --workspace ~/.craft-agent/workspaces/my-workspace`, because #821 is specifically about active workspace drift.
