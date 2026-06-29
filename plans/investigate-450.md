---
ticket_refs:
  - siege-analytics/claude-configs-public#450
---
# Investigation: #450 — advisory UserPromptSubmit hooks to JSON-blocking

## Fact Sheet

### Finding 1: pre-action-guard.sh is advisory-only in CA
**File:** `hooks/resolver/pre-action-guard.sh` (100 lines)
**Evidence:** Emits heredoc prose warnings via `cat <<EOF` for protected branch (line 46-60) and detached HEAD (line 30-42). No JSON emission. Always `exit 0`.
**Impact:** Craft Agent ignores prose output. Agents can commit directly to develop/main despite warnings.
**Citation:** #416 proved mixed prose doesn't parse as blocking signal.

### Finding 2: branch-state-guard.sh is advisory-only in CA
**File:** `hooks/resolver/branch-state-guard.sh` (42 lines)
**Evidence:** Emits `<branch-state>` tagged heredoc (line 27-38). No JSON emission. Always `exit 0`.
**Impact:** Duplicate of pre-action-guard for workspace-root detection. Same advisory-only gap.

### Finding 3: ca-enforcement-gate.sh missing SCOPE MISMATCH pattern
**File:** `hooks/resolver/ca-enforcement-gate.sh` (86 lines)
**Evidence:** BLOCK_PATTERNS at lines 38-44 include STALE DESIGN, STALE INVESTIGATION, ^BLOCKED:, EXPIRED SIGNAL. But think-gate-guard.sh emits "SCOPE MISMATCH" (line 242) when signal file ticket doesn't match branch. This is not in BLOCK_PATTERNS.
**Impact:** Agent can work on ticket X with a stale signal from ticket Y without being blocked.

### Finding 4: Hooks with enforcement via mutation gate (no change needed)
- `pipeline-state-guard.sh`: Writes signal files (junior-senior-gate.json, artifacts-posted-gate.json). Blocking enforced by universal-mutation-gate.sh reading these files.
- `review-gate-guard.sh`: Advisory output. Blocking enforced by universal-mutation-gate.sh reading review-gate.json (#526).

### Finding 5: Hooks that are advisory by design (no change needed)
- `inject-resolver.sh`: Injects RESOLVER.md content into context. Informational.
- `standing-order-guard.sh`: Injects standing-order directive. Informational.
- `think-gate-guard.sh`: Already wrapped by ca-enforcement-gate.sh for STALE DESIGN and EXPIRED SIGNAL. Only SCOPE MISMATCH is missing.

## Disposition

Three changes needed:
1. `pre-action-guard.sh` — emit `{"continue": false}` when `CLAUDE_CA_ENFORCE=1` and on protected branch or detached HEAD
2. `branch-state-guard.sh` — emit `{"continue": false}` when `CLAUDE_CA_ENFORCE=1` and on protected branch
3. `ca-enforcement-gate.sh` — add `"SCOPE MISMATCH"` to BLOCK_PATTERNS
