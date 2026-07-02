---
ticket_refs:
  - siege-analytics/claude-configs-public#609
---

# Pre-Mortem - #609 coordinator status guard

Task: Add a hard guard for coordinator status transitions lacking evidence.
Ticket: siege-analytics/claude-configs-public#609
Fact Sheet: `plans/investigate-609-coordinator-status-guard.md`
Design note: `plans/design-609-coordinator-status-guard.md`

## Tigers

### Tiger 1: Guard blocks ordinary investigation comments

- Scenario: the hook treats every `gh issue comment` as a status transition and blocks normal coordination comments.
- Evidence: issue updates are broad; ordinary comments use the same `gh issue comment` command as lane status updates.
- Severity: MEDIUM
- Urgency: Launch-Blocking
- Trigger condition: no status/lane marker scope check.
- Mitigation: guard engages only for direct state actions or body text containing status/lane/completion/blocker markers; test ordinary non-status comment passes.
- Status: Mitigated.

### Tiger 2: Guard permits implied completion while blockers remain unresolved

- Scenario: a comment says a lane is complete while also saying owner response is missing.
- Evidence: #609 impact explicitly names blocker/completion transitions implied before signoff evidence.
- Severity: HIGH
- Urgency: Launch-Blocking
- Trigger condition: completion and blocker words coexist but are not treated as conflict.
- Mitigation: block any completion claim that also names unresolved blocker language; test covers `Status: complete. Blocked with no owner response.`
- Status: Mitigated.

### Tiger 3: Codex package misses the guard

- Scenario: hook exists locally but is not wired into `settings-snippet.json`, so Codex/Claude consumers never run it.
- Evidence: Codex sessions execute Bash commands through package settings; unreferenced hooks do not enforce anything.
- Severity: HIGH
- Urgency: Launch-Blocking
- Trigger condition: hook file added without settings wiring.
- Mitigation: insert hook into Bash PreToolUse settings and run `validate-hooks.py` plus package builds.
- Status: Mitigated.

## Paper Tigers

### Paper Tiger 1: The guard must understand every project-specific rollout shape

- Scenario: different projects have deploy/UAT/backfill/reindex gates.
- Why handled: the guard does not decide project readiness. It requires evidence classes or N/A. Project-specific details remain in the comment body and reviewer judgment.

## Elephants

### Elephant 1: Prose-only assistant responses are outside Bash PreToolUse

- What it is: a model can verbally imply completion in chat without calling `gh`. This hook blocks external state mutation, not all natural language.
- Why deferred: #609 acceptance requires hard guard for status transition and unit/integration check. Chat-output scanning would require a separate Stop/Post-response surface.
- Cost of deferral: purely conversational drift remains possible until a post-claim/Stop hook exists.
- Trigger for revisiting: recurrence where no GitHub/API state was mutated but chat-only completion caused operational harm.

## Launch-Blocking Assessment

- [x] No Launch-Blocking Tigers remain unmitigated by the implementation plan.
- [x] All Tiger mitigations are grounded in investigated facts.
- [x] Elephant has deferral rationale and revisit trigger.
- Implementation may proceed: YES.
