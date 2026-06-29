---
ticket_refs:
  - siege-analytics/claude-configs-public#411
---
# Investigation: #411 — KB and testing-frameworks as blocking gates

## Fact Sheet

### Finding 1: KB warnings are advisory, not blocking
**File:** `hooks/resolver/think-gate-guard.sh` (lines 400-436)
**Evidence:** KB warnings printed without `BLOCKED:` prefix, output tagged as "advisory" in the cat heredoc.
**Impact:** ca-enforcement-gate.sh BLOCK_PATTERNS includes `"^BLOCKED:"` but KB warnings don't match.
**Fix:** Add `BLOCKED: knowledge-base consultation required.` prefix to KB warnings.

### Finding 2: test-guard.sh not in native pre-push hook
**File:** `bin/build.py` CA_ENFORCEMENT_GATES (lines 960-995)
**Evidence:** Only self-review and branch-guard have `"surface": "native-git-pre-push"`. test-guard is absent.
**Impact:** In CA sessions where PreToolUse doesn't fire, test-guard enforcement is completely absent.
**Fix:** Add test-guard to CA_ENFORCEMENT_GATES with native-git-pre-push surface.

### Finding 3: Native pre-push hook is a no-op for PreToolUse-designed hooks
**File:** `hooks/git/self-review.sh` (line 53), `hooks/git/test-guard.sh` (line 28)
**Evidence:** Both hooks parse stdin as PreToolUse JSON (`INPUT=$(cat)` + `extract-json.py`). When called from native .githooks/pre-push, stdin is git ref list. JSON extraction fails → COMMAND empty → exit 0.
**Impact:** The native pre-push hook installed by build.py provides ZERO enforcement — all gates exit 0.
**Fix:** Add native-hook detection: if COMMAND extraction fails but we're in a git repo, set COMMAND="git push" and CWD from git.

## Disposition
Four changes:
1. think-gate-guard.sh: prefix KB warnings with `BLOCKED:`
2. build.py: add test-guard to CA_ENFORCEMENT_GATES
3. self-review.sh: add native-hook detection path
4. test-guard.sh: add native-hook detection path
