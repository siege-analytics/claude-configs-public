# Craft Agent enforcement

This directory holds the Craft Agent (CA) enforcement artifacts and the model
they implement. Read this before wiring a CA workspace, and before assuming a
skills sync gave you enforcement. It did not.

## The one thing to internalise

**Syncing `skills/` is not enforcement.** Skills and rules are advisory: they
tell a compliant agent what to do. A workspace that only copies `skills/` gets
a complete, current skills pane and zero compellability. The gates that make
`think`, `investigate`, pre-mortem, and self-review mandatory live in the hook
and automation wiring, not in the markdown. A sync that stops at `cp skills/`
leaves every gate dark while looking fully installed.

To wire enforcement into a CA workspace, run the installer, never a bare copy:

```bash
bash bin/install.sh --workspace <slug>     # one-shot
bash bin/harmonize.sh --workspace <slug>   # recurring / unattended (idempotent)
```

Both end by running `bin/verify-enforcement.sh`, which fails loudly if
enforcement did not actually come up. That probe is the contract: green means
live, not merely present.

## How CA blocking works

Craft Agent passes `UserPromptSubmit` and `PreToolUse` to the Claude Agent SDK.
A `command` hook can hard-block by emitting a single `{"continue": false,
"systemMessage": "..."}` object as its sole stdout. Mixed human text plus a
later JSON line does not parse and does not block (verified in #416); the JSON
must be the only thing on stdout.

`hooks/resolver/ca-enforcement-gate.sh` is that wrapper. It runs the advisory
gates (`think-gate-guard`, `investigate-gate-guard`, `skill-enforcement-gate`),
scans their output for blocking signals (STALE DESIGN, BLOCKED, missing
investigation, and similar), and converts a block into `continue:false`. It is
always active; the opt-in env switch was removed in #572 because an opt-in
enforcement gate is itself an honor-system hole.

CA does not expose a first-class end-of-turn or PreToolUse deny action through
`automations.json` (only `prompt` and `webhook` actions). Push-time gates that
need a hard block therefore run as native git `pre-push` hooks, and turn-level
gates run as the `UserPromptSubmit` `continue:false` wrapper above.

## Rules reach the model through CLAUDE.md

CA auto-injects `CLAUDE.md` / `AGENTS.md` content from the session working
directory and its subdirectories into the system prompt. The installer wires
the always-on rules into that mechanism by symlinking
`CLAUDE.md -> RULES_BUNDLE.md` at the workspace root. Point the workspace
Default Working Directory at the workspace root so new sessions pick it up.
Without this symlink the rules never enter the system prompt, no matter how
current `skills/` is.

## Artifacts in this directory

| File | Purpose |
|---|---|
| `automations-snippet.json` | The standing-order watchdog (`SchedulerTick`) and completion audit (`SessionStatusChange`). Registered into the workspace `automations.json` by `bin/wire-enforcement.py`. Merged by (event, name): re-runs replace in place and never drop a consumer's own automations. |
| `standing-order-watchdog.json` | Reference spec for the watchdog: the failure case, signal-file schema, completion criteria, and the runtime split between Claude Code (hook) and Craft Agent (automation). |

Generated artifacts (`enforcement-manifest.json`, `settings-enforcement.json`,
`.githooks/pre-push`) are emitted under `dist/craft-agent/` by
`build_ca_enforcement()` and deployed by `deploy_to_workspace()`.

## Automation permission mode

The watchdog and completion-audit automations run in `allow-all` (execute)
mode, not `safe`. They set session status to `done` and send continuation
prompts to other sessions -- both are mutations that `safe` (read-only /
Explore) mode blocks, so a `safe` watchdog finishes its inspection and then
cannot set its own status, stalling in a can't-finish state. Their prompts are
constrained to inspection + continuation and to not modifying user files, so
`allow-all` is the correct level: enough privilege to act, narrowed by prompt.
This matches the session-coordination spawn discipline -- an automation that
must act runs with execute permission, never read-only. Do not lower these back
to `safe`.

## The install / harmonise contract

1. `bin/build.py --layout flat --deploy --craft-workspace <ws>` builds and
   deploys skills, hooks, `RULES_BUNDLE.md`, the `CLAUDE.md` symlink, the
   enforcement manifest, and the native git hook.
2. `bin/install-hooks.sh` writes `.claude/settings.json` from the base snippet.
   It overwrites that file, so it must run before the enforcement merge.
3. `bin/wire-enforcement.py --workspace <ws>` merges the blocking
   `ca-enforcement-gate.sh` wrapper into `.claude/settings.json` and registers
   the watchdog automations. This is the last writer to settings.json, which is
   why the merge cannot be clobbered. It is idempotent.
4. `bin/verify-enforcement.sh --target <ws> --mode craft-agent` proves it is
   live: a real block test plus the wiring assertions. Non-zero means dark.

`bin/install.sh` runs steps 1 to 4 in order. `bin/harmonize.sh` is the
idempotent wrapper a recurring job should call so that harmonisation re-wires
and re-verifies enforcement on every run instead of silently drifting to
advisory-only.

Refs: #96, #261, #380, #409, #416, #572.
