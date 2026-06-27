---
ticket_refs:
  - siege-analytics/claude-configs-public#482: comment pending
---
# Pre-Mortem: #482 — Vergil Quote Hook

## What could go wrong

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | PostToolUse event not supported in Claude Code (only CA) | Medium | Hook silently never fires — no quotes, no errors | Verify by checking Claude Code hook docs; if unsupported, hook is dead code in claude-code package |
| 2 | Hook regex matches unintended commands (e.g. `gh pr review` without `--approve`) | Low | Quote fires on non-approval PR reviews | Regex is `gh\ pr\ (merge\|review\ --approve)` — the `--approve` is required in the match |
| 3 | `python3 "$EXTRACT"` fails if extract-json.py is missing in consumer package | Low | Hook errors on every Bash PostToolUse, stderr noise | validate-hooks.py checks hook existence; extract-json.py is in hooks/lib/ which is copied by build |
| 4 | `$RANDOM` not available in non-bash shells (sh, dash) | Low | Script errors on `$RANDOM % N` | Shebang is `#!/bin/bash`, not `#!/bin/sh` — bash is required |
| 5 | PostToolUse hook timeout (5s) exceeded if extract-json.py is slow | Very Low | Quote never prints, timeout error in tool output | extract-json.py is a simple JSON key extraction; 5s is generous |

## What would make us revert

- Hook produces non-zero exit code that blocks or confuses the agent
- Hook fires on commands it shouldn't (false positive regex match)
- Hook adds measurable latency to every Bash command (PostToolUse fires on ALL Bash, not just merge)

## Rollback plan

Remove the hook entry from `PostToolUse` in settings-snippet.json and delete `hooks/git/vergil-quote.sh`. One commit, no dependencies.

## Pre-mortem verdict

Low risk. The hook is cosmetic (exit 0 only), fires only on a narrow regex match, and the worst failure mode is "no quote appears." The real risk is #1 — PostToolUse may not exist in Claude Code, making the hook dead code in one of two consumer packages. This is acceptable for a pipeline integration test.
