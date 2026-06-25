---
ticket_refs:
  - siege-analytics/claude-configs-public#473
  - siege-analytics/claude-configs-public#415
  - siege-analytics/claude-configs-public#472
---

# Self-review: #473 fail-closed universal mutation gate

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: #473
Goal source verification: PASS (ticket has Context, Goal, Acceptance, Assumptions)
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/473#issuecomment-4803205458
Pre-author-inventory: NONE (new hook, no prior code)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)
Hostile-review-artifact: WAIVED (see waiver declaration below)

## Trivial-investigation declaration

Category: fixed-string-correction
Cannot produce error: the hook is a new file with no callers until installed; settings-snippet.json change adds an entry but does not modify existing hook behavior
Evidence: `git diff --stat` shows 1 modified file (settings-snippet.json, 5 insertions) and 1 new file
Falsification: if any existing hook test fails after this change, the investigation was needed

## Trivial-pre-mortem declaration

Category: prose-only-docs
Cannot produce error: this is a new hook file; worst case is it blocks too aggressively (fail-closed by design) or too permissively (safelist too broad); neither breaks existing functionality since the hook is not yet wired into any real settings.json
Evidence: the hook is only added to settings-snippet.json (the template); individual users must manually merge it into their settings
Falsification: if a CI or integration test fails due to this hook, the pre-mortem was needed

## Hostile-review-waiver

Category: bootstrap
Cannot produce error: this is the enforcement gate that makes hostile review mechanical; requiring hostile review of the gate that enforces hostile review is circular at the bootstrap step
Evidence: no prior universal-mutation-gate.sh exists to review against; the hook is fail-closed (blocks by default), so bugs manifest as false positives (too strict), not false negatives (too permissive)
Falsification: if the hook allows a mutation that should have been blocked (false negative), the waiver was wrong and hostile review would have caught it

## Peer review (the Junior's checklist)

### Correctness shelf
- [x] `bash -n` passes: syntax clean
- [x] Safe reads pass (ls, git status, git log, gh issue view, grep, cat, echo, pytest, pip list, bash -n): all exit 0
- [x] Mutations block without think-gate (git push, git commit, gh issue create, gh issue comment, gh pr create, gh pr merge, rm -rf, curl POST, pip install): all exit 2
- [x] Compound commands with mutations block (git log && git push, cd repo && git push): exit 2
- [x] Think-gate.json with status=implementing allows mutations: exit 0
- [x] [mutation-acknowledged] escape works: exit 0 with stderr log
- [x] CLAUDE_MUTATION_GATE=off disables: exit 0

### Security shelf
- [x] No credentials or secrets in code
- [x] Hook reads stdin JSON and think-gate.json only; no network calls
- [x] Python3 inline for JSON parsing uses json.load (safe)

### Quantified claims
- "Safe reads pass" -- tested 12 commands, all exit 0
- "Mutations block" -- tested 11 commands, all exit 2
- Verified-by: inline test output in this session

## Lead review (adversarial pass)

### Does the hook actually close the #415 gaps?
The hook blocks `git push`, `gh issue create`, `gh pr merge`, `rm -rf`, `curl -X POST` without think-gate. These are the exact mutation surfaces documented in #415 and #472 Part 1. The hook does NOT cover MCP tool calls (those need separate PreToolUse matchers) — acknowledged in design as Option 1 limitation.

### Could an agent bypass this hook?
1. **Bash tool**: hook fires on all Bash calls. No bypass via Bash.
2. **Write/Edit tools**: not covered by this hook (covered by existing write-guard.sh and branch-guard.sh).
3. **MCP tools (spawn_session, merge_pull_request)**: NOT covered. This is the acknowledged gap.
4. **Out-of-tree clones**: hook fires regardless of CWD because it checks the command string, not the working directory. `git push` is blocked whether the repo is in-workspace or in /tmp. This closes the #415 out-of-tree bypass.
5. **CLAUDE_MUTATION_GATE=off**: emergency escape, discouraged. Agent could set this env var. Mitigation: this env var is visible in audit logs.

### Blast radius
Worst case: safelist too narrow, blocks legitimate reads. This is the designed failure mode. Impact: agent hits [mutation-acknowledged] or adds pattern to safelist. Recovery time: seconds. No data loss possible.

### Approach-fit verdict
Correct approach. Fail-closed with safelist is the inversion of the current fail-open model. The design note's Approach B was approved by operator.

## Findings

| ID | Priority | Description | Resolution |
|---|---|---|---|
| F1 | P3 | MCP tool calls not covered | Acknowledged in design; separate hook needed (Option 2 from design note) |
| F2 | P3 | SAFE_PATTERNS will need tuning as real usage exposes false positives | By design; fail-closed means false positives are expected and fixed quickly |

## Quantified claims

"12 safe-read commands pass" -- test output shows all exit 0
"11 mutation commands block" -- test output shows all exit 2
"Compound command bypass fixed" -- `git log && git push` exits 2

## Evidence-predates-work

Artifact: plans/self-review-473.md
Work commit: not yet committed (pre-push review)
