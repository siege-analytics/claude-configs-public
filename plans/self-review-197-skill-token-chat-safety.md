---
ticket_refs:
  - siege-analytics/claude-configs-public#197
---

# Self-Review - skill-token chat safety

## Assumptions

Goal source: siege-analytics/claude-configs-public#197.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: host parser can treat raw bracketed skill/rule tokens in chat as resolver directives even when they are examples or Markdown-formatted text. CCP cannot patch the host parser, so this change provides package-side prevention guidance and a sanitizer utility.
Hostile-review-artifact: not required for small docs/script utility; local regression test covers the transformation.
Inventoried-shape: docs guidance, skillbuilder authoring guidance, sanitizer script, shell regression test, changelog.

## Peer review

Shelf checks:

- Added `docs/skill-token-chat-safety.md` with safe forms for operator-facing explanatory text.
- Added `scripts/discipline/skill-token-chat-safe.py` to rewrite raw bracketed skill/rule references to display-only text.
- Added `scripts/discipline/test_skill_token_chat_safe.sh` regression test for skill/rule examples and non-target strings.
- Updated `skills/skillbuilder/SKILL.md` so future skill authoring and postmortem text avoids the host-parser trap.
- Added current changelog entry.

## Lead review

[Lead] This does not claim to fix the host parser. It gives CCP consumers a reliable mitigation and prevents repo-authored instructions from teaching agents to emit parser-triggering text in ordinary chat.

[Lead] The sanitizer is conservative: it rewrites only raw bracketed `skill:` and `rule:` token shapes and leaves slash commands or plain `skill:foo` text alone.

## Quantified claims

- Token classes sanitized: 2 (`skill`, `rule`).
- Regression examples covered: 5 input references/strings in one shell test.
- Operator-facing guidance surfaces updated: dedicated doc and skillbuilder skill.

## Hook-Dependencies

- `scripts/discipline/skill-token-chat-safe.py`: safe dependencies: python3; fallback behavior: loud error if Python is unavailable.
- `scripts/discipline/test_skill_token_chat_safe.sh`: safe dependencies: bash, python3, grep; fallback behavior: loud non-zero exit.

## Verification commands

```text
python3 -m py_compile scripts/discipline/skill-token-chat-safe.py
bash scripts/discipline/test_skill_token_chat_safe.sh
bash skills/detect-ai-fingerprints/scan.sh
python3 scripts/ci/release-notes.py --version 3.5.25 --check
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `python3 -m py_compile scripts/discipline/skill-token-chat-safe.py`: passed.
- `bash scripts/discipline/test_skill_token_chat_safe.sh`: passed.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean; emitted known `config_arg[@]: unbound variable` warning before clean result.
- `python3 scripts/ci/release-notes.py --version 3.5.25 --check`: passed.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded after moving stale local `dist` aside to avoid pre-existing duplicate-directory clutter.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
