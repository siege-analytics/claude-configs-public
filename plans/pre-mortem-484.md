---
ticket_refs:
  - siege-analytics/claude-configs-public#484: comment pending
---
# Pre-Mortem: #484 — Artifact gates must verify ticket association

## What could go wrong

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | `file_references_ticket` false negative: pre-mortem uses ticket format the function doesn't recognize | Medium | Gate blocks valid artifacts, agent stuck | Function checks both full ref (`siege-analytics/repo#N`) and slug (`#N`); most formats covered. If a new format appears, add it to the check. |
| 2 | `file_references_ticket` false positive: file mentions ticket number coincidentally (e.g. "see #484 in the changelog") | Low | Gate passes an unrelated artifact | Acceptable — the file at least references the ticket number. The enforcement is "does this artifact acknowledge this ticket exists," not "is this the canonical artifact." |
| 3 | Python subprocess in mutation gate adds latency to every implementing-status Bash command | Medium | Every Bash command during implementation takes 50-200ms longer | Python reads only 4096 bytes per file, searches at most ~10 pre-mortem candidates. Profile if latency complaints arise. |
| 4 | `CRAFT_AGENT_WORKSPACE` env var not set in Claude Code sessions | High | `ca_plans` path is empty string, plans dir not found, pre-mortem check falls through to repo plans only | Acceptable — Claude Code sessions use repo plans/, not workspace plans/. The `WORKSPACE_CANDIDATE` fallback (derived from hook script location) covers the Claude Code case. |
| 5 | Backwards-compat breakage: old think-gate.json without `ticket` field | Medium | Gate could reject valid artifacts from sessions that predate the ticket field | Mitigated: when `current_ticket` is empty, `file_references_ticket` returns True and `invest_found` accepts any ticket. Tested as case 3. |
| 6 | Pipeline-state-guard fix not deployed to workspace — live guard still accepts wrong-ticket artifacts | **Certain** | The fix exists in the git clone but the workspace runs the old guard until next `--deploy` | Must run `build.py --deploy` after merge to actually close the hole. Until then, the workspace pipeline-gate is cosmetic. |

## What would make us revert

- Gate produces false negatives on correctly-associated artifacts (blocks legitimate work)
- Python subprocess errors crash the mutation gate (should be caught by `2>/dev/null || true` but verify)
- Latency exceeds 500ms per Bash command during implementation

## Rollback plan

Revert `d618932`. Artifact checks return to existence-only (glob match). One commit, no dependencies.

## Pre-mortem verdict

Risk #6 is the critical one: the fix doesn't take effect until deployed. The canonical clone has the fix, but the workspace runs the old guard. This is the recursive enforcement problem — fixing enforcement requires deploying the fix, and deployment is a separate step that can be forgotten.
