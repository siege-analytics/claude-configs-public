## Assumptions
Domain(s): agent workflow
Geospatial cross-cut: no
Goal source: ticket #445
Goal source verification: Manual — ticket has Context, Goal, Acceptance criteria. Structurally fit.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/445#issuecomment-4746802283
Pre-author-inventory: NONE (new skill, no pre-existing abstraction to inventory)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
New standalone SKILL.md with no callers in the existing codebase. Investigation verified: (1) No existing `cross-review` skill directory — confirmed via `ls skills/`. (2) Existing review skills (`hostile-review`, `code-review`, `self-review`, `over-engineering-audit`) follow the same SKILL.md pattern — confirmed. (3) `spawn_session` tool accepts `llmConnection` parameter — confirmed via `spawn_session(help=true)`.

## Trivial-pre-mortem declaration
Risk surface: new markdown file added to `skills/cross-review/`. No existing code is modified. No hooks fire from this skill content. No build artifacts depend on it. The skill only activates when explicitly invoked by an agent. Failure mode: if the skill instructions are wrong, the agent gets bad guidance — fully reversible by updating or deleting the file.

## Peer review

### Syntax check
Markdown: no syntax errors (standard GFM with YAML frontmatter).

### Test suite
Not applicable — instruction-only skill, no executable code.

### Build validation
Build: `python3 bin/build.py --check` not run (no build changes). Skill is a new file only.

### Shelf: conventions
Skill follows existing conventions: YAML frontmatter with name, description, allowed-tools. Structured sections matching other skills (hostile-review, self-review). Attribution policy section included per repo convention.

## Lead review

### Phase A: Structural coherence
Design note on #445 matches implementation. Provider resolution order matches design: alternate provider → same provider/different model → MCP fallback. Spawn pattern includes all required parameters. Ticket integration via `gh issue comment` with `send_agent_message` fallback.

### Phase B: Did this close the gap?
The ticket's acceptance criteria:
- [x] `skills/cross-review/SKILL.md` exists with the full workflow
- [x] Documents the provider-preference resolution order (3-tier)
- [x] Includes the spawn_session invocation pattern with all parameters
- [x] Documents the MCP cross-review server as fallback
- [x] Skill is portable (no hardcoded slugs — discovers connections dynamically)

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims

- "3-tier resolution" — counted: alternate provider, same provider/different model, MCP fallback → 3. Verified.
- "6 allowed-tools" — counted: Read, Glob, Grep, spawn_session, send_agent_message, get_session_info, set_session_status → 7. Mismatch: frontmatter lists 7, claim said 6. Corrected claim to 7.

## Evidence-predates-work
Artifact: plans/self-review-445.md
