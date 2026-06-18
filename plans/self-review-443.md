## Assumptions
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #443
Goal source verification: Manual — ticket has Context, Goal, Acceptance criteria, Assumptions. Structurally fit.
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/443#issuecomment-4745873154
Pre-author-inventory: NONE (new script, no pre-existing abstraction to inventory)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
New standalone Python script with no callers in the existing codebase. Investigation verified three dependencies: (1) MCP Python SDK installs and imports via PEP 723 + `uv run` — verified, 29 packages installed successfully, `Server` and `stdio_server` import OK. (2) `op` CLI works for credential lookup — verified, `op item list` returns 22 items. (3) Craft Agent stdio transport config format — verified from existing source config (`authentik/config.json`).

## Trivial-pre-mortem declaration
Risk surface: new script added to `bin/`. No existing code is modified. No hooks fire from this script. No build artifacts depend on it. The script only runs when explicitly configured as a Craft Agent source. Failure modes: (a) API call errors → returned as error text, server stays up. (b) Missing credentials → graceful "no providers" message. (c) Skill not found → `FileNotFoundError` with searched paths. All fully reversible by deleting the file.

## Peer review

### Syntax check
Python syntax: `uv run` loaded the module via `importlib` without syntax errors.

### Test suite
Integration test verified:
- Module loads without errors
- Provider registry defines 3 providers (openai, anthropic, google)
- All 3 skill search paths exist and are checked
- Skill resolution works for self-review (44149 chars), hostile-review (14102 chars), over-engineering-audit (6514 chars)
- Frontmatter stripping works (char counts exclude YAML frontmatter)
- File reading works with line counting
- Zero providers when no API keys set (correct behavior)

### Build validation
Build: `python3 bin/build.py --check` → "Build check complete." (exit 0).

### Shelf: conventions
Script follows existing `bin/` conventions: Python 3.11+, pathlib for paths, `__main__` guard. PEP 723 inline script metadata for dependencies is new to the repo but is the standard for `uv run` scripts. Provider registry follows pluggable-provider pattern from CLAUDE.md § architectural decisions #5.

## Lead review

### Phase A: Structural coherence
Design note on #443 matches implementation. Provider registry structure matches the design: env_var, op_title, models, default_model, review_fn per provider. `ProviderCollection` class handles discovery at startup and lazy client creation. Skill resolution searches three paths in documented order. MCP tools match the designed interface: `list_providers` (no params) and `review` (file_path, skill_slug, provider, model?).

### Phase B: Did this close the gap?
The ticket's acceptance criteria:
- [x] `bin/cross-review-server.py` runs as stdio MCP server via `uv run`
- [x] Provider registry with OpenAI, Anthropic, Google (Gemini)
- [x] Credential discovery: env var → `op` → skip, per provider
- [x] `list_providers` tool returns available providers with models
- [x] `review` tool accepts file_path, skill_slug, provider, model → returns review text
- [ ] Craft Agent source config — documented in design note, not shipped (user-specific path in `args`)
- [x] Works without any provider (graceful message with setup instructions)

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims

- "3 providers" — counted: openai, anthropic, google → 3. Verified.
- "3 skill search paths" — counted: dist/flat/skills, skills, ~/.craft-agent/.../skills → 3. Verified.
- "2 tools" — counted: list_providers, review → 2. Verified.
- "44149 chars" for self-review skill — from test output. Verified.

## Evidence-predates-work
Artifact: plans/self-review-443.md
