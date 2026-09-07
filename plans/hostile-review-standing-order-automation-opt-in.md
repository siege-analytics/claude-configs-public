# Hostile review: standing-order automation opt-in hotfix

Reviewer source: independent secondary model, Sonnet-class with extended reasoning.

## Initial review

Verdict: BLOCK.

Finding:
- HIGH: `CHANGELOG.md` was corrupted because the hotfix entry had been inserted into many historical `### Fixed` sections instead of only the current section.

## Fix

Removed all accidental duplicate changelog entries and inserted exactly one current hotfix entry.

## Final review

Verdict: PASS.

Findings:
- Changelog entry is clean and not duplicated/corrupted.
- Default `wire-enforcement.py` still merges CA blocking enforcement before automation handling.
- Default path skips standing-order automations and emits an opt-in message.
- `--include-standing-order-automations` preserves prior registration behavior.
- Regression test covers default skip and explicit opt-in registration.
