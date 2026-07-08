---
ticket_refs:
  - siege-analytics/claude-configs-public#457
---

# Pre-Mortem - #457 Cursor consumer package

Task: Add first-class Cursor IDE consumer package alongside Claude Code and Craft Agent.
Ticket: siege-analytics/claude-configs-public#457
Design note: `plans/self-review-457-cursor-consumer.md`

## Tigers

### Tiger 1: Install overwrites operator skill edits

- Scenario: `install-cursor.sh` rsyncs skill directories and clobbers local edits under `~/.cursor/skills/<slug>/`.
- Evidence: flat-layout install copies whole directories; operators may have customized skill bodies after a prior manual install.
- **Severity:** MEDIUM
- Mitigation: rsync without `--delete`; document backup in `cursor/CURSOR.md`; merge per-directory rather than wiping the tree.
- Status: Mitigated by implementation.

### Tiger 2: Accidental touch of Cursor built-in skills

- Scenario: installer targets `~/.cursor/skills-cursor/` and corrupts Cursor-managed built-ins.
- Evidence: prior manual install used wrong paths; `skills-cursor/` is reserved per Cursor docs.
- **Severity:** HIGH
- Mitigation: hardcode destination as `~/.cursor/skills/`; explicit guard in `install-cursor.sh` refusing paths under `skills-cursor`.
- Status: Mitigated by implementation.

### Tiger 3: Loose rule files at skills root confuse Cursor discovery

- Scenario: `release/flat` includes `_*-rules.md` at `skills/` root; copying them into `~/.cursor/skills/` pollutes discovery (observed in manual install).
- Evidence: flat layout ships rules alongside skills; Cursor expects skill directories with `SKILL.md`.
- **Severity:** MEDIUM
- Mitigation: `build_cursor_package()` excludes `_*-rules.md`, `RULES.md`, `_coverage.md`; `validate-cursor.py` fails if loose rules present.
- Status: Mitigated by implementation.

### Tiger 4: Claude-only frontmatter leaks into Cursor skills

- Scenario: `allowed-tools` / `argument-hint` keys confuse Cursor or waste context without effect.
- Evidence: skills authored for Claude Code CLI frontmatter conventions.
- **Severity:** LOW
- Mitigation: `strip_cursor_incompatible_keys()` at build time.
- Status: Mitigated by implementation.

### Tiger 5: CI publish race on release/cursor branch

- Scenario: concurrent publish runs lose `release/cursor` force-push race like prior flat/nested incidents.
- Evidence: `build-and-publish.yml` concurrency group already serializes branch publishes.
- **Severity:** LOW
- Mitigation: reuse existing `publish-release-branches` concurrency group; add `-cursor` tag in same publish job.
- Status: Mitigated by implementation.

## Launch-Blocking Assessment

- [x] No Launch-Blocking Tigers remain unmitigated.
- Implementation may proceed: YES.
