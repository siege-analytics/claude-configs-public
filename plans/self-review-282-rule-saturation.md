---
ticket_refs:
  - siege-analytics/claude-configs-public#282
---

# Self-Review - rule saturation citation guard

## Assumptions

Goal source: siege-analytics/claude-configs-public#282.
Role(s): implementer and reviewer-coordinator.
Pre-author-inventory: issue #282 identifies citation-as-compliance as the structural failure: rule citations were treated as evidence of execution.
Hostile-review-artifact: pending.
Inventoried-shape: `skills/detect-ai-fingerprints/scan.sh`, scanner skill docs, scanner regression tests.

## Peer review

Shelf checks:

- Added message-level scanner detection for rule citations such as `writing-code:19` and `[rule:writing-claims]`.
- A message that cites a rule must include `Rule-executed: <rule-id> <artifact>`.
- Added focused regression tests for blocked citation-only messages, blocked mismatched `Rule-executed` trailers, blocked same-line rule-id smuggling, passing citation-with-matching-artifact messages, and ordinary colon tokens such as `localhost:8000` / `python:3.12`.
- Documented the guard in `[skill:detect-ai-fingerprints]`.

## Lead review

[Lead] This avoids adding another always-on rule. It changes the scanner relationship to existing rules: citing a rule now creates a requirement to point at execution evidence.

[Lead] The guard is message-level, where the failure manifested: commit/PR bodies using rule names as prose compliance tokens.

## Quantified claims

- Scanner guard call sites added: 1 message-level pass.
- Regression test scripts added: 1.
- New always-on rule files added: 0.

## Verification commands

```text
bash skills/detect-ai-fingerprints/test_rule_citations.sh
bash skills/detect-ai-fingerprints/scan.sh --message-file /tmp/rule-citation-bad.txt
bash skills/detect-ai-fingerprints/scan.sh --message-file /tmp/rule-citation-good.txt
bash skills/detect-ai-fingerprints/scan.sh
python3 bin/sync-skill-references.py --check
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
```

## Result

Passed locally:

- `bash skills/detect-ai-fingerprints/test_rule_citations.sh`: passed, including mismatched-trailer, same-line smuggling, and ordinary-colon regression cases.
- `bash skills/detect-ai-fingerprints/scan.sh`: clean.
- `python3 bin/sync-skill-references.py --check`: clean.
- `python3 bin/build.py`: succeeded.
- `python3 bin/validate-hooks.py dist/claude-code/`: all hooks valid, existing warnings only.
- `python3 bin/validate-hooks.py dist/craft-agent/`: all hooks valid, existing warnings only.
