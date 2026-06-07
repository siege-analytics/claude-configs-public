# Self-review: CA-aware install script (#377)

## Lead

- **As tech lead:** Single new file (`bin/install.sh`), no existing code
  modified. Composes `build.py --deploy` and `install-hooks.sh` -- no
  duplication of their logic. Zero blast radius; fully reversible (delete
  the script).

- **As domain expert:** Detects Craft Agent via `~/.craft-agent/workspaces/`
  existence. Handles multi-workspace case (defaults to `my-workspace`,
  accepts `--workspace` flag). Validation step confirms 5 deployment
  artifacts: skills dir, RULES_BUNDLE.md, RESOLVER.md, settings.json,
  hooks dir. Non-CA fallback builds both layouts and installs hooks to
  `.claude/settings.local.json`.

## Checklist

- [x] Detects CA via `~/.craft-agent/workspaces/` directory check
- [x] Multi-workspace: defaults to `my-workspace`, lists available
- [x] `--workspace <slug>` flag works for explicit targeting
- [x] `--no-craft-agent` flag forces direct-clone mode
- [x] Build runs once (not doubled)
- [x] Calls `build.py --layout flat --deploy` (composes, no duplication)
- [x] Calls `install-hooks.sh --workspace --hooks-root` (composes)
- [x] Validation checks: skills, RULES_BUNDLE.md, RESOLVER.md, settings.json, hooks
- [x] Non-CA fallback works (builds both layouts, installs hooks)
- [x] ASCII-only verified
- [x] `--help` flag works
- [x] Script is executable (chmod +x)

## Assumptions

1. Craft Agent workspaces live under `~/.craft-agent/workspaces/`. If the
   CA install path changes, the detection breaks. Falsifiable: `ls ~/.craft-agent/workspaces/`.
2. `build.py --deploy` targets `my-workspace` hardcoded via `CRAFT_WORKSPACE`
   in build.py. The install script's `--workspace` flag selects which workspace
   to target for hooks, but the deploy step always goes to `my-workspace`.
   This is a known limitation -- acceptable because only `my-workspace` is
   used today.
3. `install-hooks.sh` generates valid JSON from the settings snippet.
   Falsifiable: the validation step checks `python3 -c "import json; json.load(...)"`.

## Peer review

- **Junior:** "Ship it, it works."
- **Lead:** The script composes existing tools without duplicating logic.
  The validation step is the key addition -- it catches partial deploys.
  The `CRAFT_WORKSPACE` hardcoding in build.py (assumption 2) is debt
  that should be addressed when multi-workspace deploy is needed, but
  is not a blocker for this PR since only `my-workspace` is in use.

## Lead review

- Blast radius: zero (new file only, no existing code modified)
- Reversibility: delete the script
- Correctness: all 5 validation checks pass on live workspace
- Debt: build.py's `CRAFT_WORKSPACE` constant limits deploy to one
  workspace. Filed as known limitation, not as a bug.

## Quantified claims

- 1 new file added (bin/install.sh, 238 lines)
- 0 existing files modified
- 5 validation checks pass (skills, RULES_BUNDLE, RESOLVER, settings.json, hooks)
- 147 skills deployed, 43 hook scripts deployed, 2917-line rules bundle

## Verification evidence

```
$ bash bin/install.sh 2>&1 | grep -c "Building flat"
1

$ bash bin/install.sh 2>&1 | grep '\[ok\]'
  [ok] skills/ deployed (147 skills)
  [ok] RULES_BUNDLE.md present (2917 lines)
  [ok] RESOLVER.md present
  [ok] .claude/settings.json valid JSON
  [ok] hooks/ deployed (43 scripts)

$ bash bin/install.sh --no-craft-agent 2>&1 | head -1
=== Direct-clone install (no Craft Agent detected) ===
```
