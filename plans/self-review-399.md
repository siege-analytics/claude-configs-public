---
propagation-deferred: will post to ticket with PR
---

# Self-review: test smell vocabulary (#399)

Self-Review: 6 structural test smells with detection heuristics and cross-references
Self-Review-Source: plans/self-review-399.md
Design-Note-Source: https://github.com/siege-analytics/claude-configs-public/issues/399
Hostile-review-artifact: WAIVED

## Hostile-review-waiver
Reason: Pure documentation addition to existing rules file, no executable code
Scope: skills/_writing-tests-rules.md (new Structural test smells section)
Compensating-control: text-only changes; detection heuristics are examples, not enforced

## Trivial-investigation declaration
Category: documentation addition
Cannot produce error: no executable code modified; _writing-tests-rules.md is instruction text
Reason: Adding named patterns and grep examples to an existing rules file
Evidence: git diff --stat shows only .md files changed
Falsification: If a hook parses the rules file and the new section breaks parsing, investigation would be required

## Assumptions
Goal source: https://github.com/siege-analytics/claude-configs-public/issues/399
Pre-author-inventory: NONE
Trivial-against-state: documentation addition, no state contact
Working as: software engineer
Roles: Junior (wrote the smell definitions), Senior (verified cross-references and severity classifications)

## Peer review

Shelves checked: writing-prose:1, writing-claims:1

### Gate evidence
- N/A — no executable files, no tests, no notebooks, no doc build

### Content verified
- 6 smells: sleepy_test, conditional_test_logic, missing_assertions, giant_test, mock_heavy, shared_mutable_state
- Each has: name, description, detection heuristic, severity, remediation
- missing_assertions and mock_heavy have grep-based detection ready for integration
- Cross-reference table links 4 smells to existing writing-tests rules

## Lead review

**[Senior]** Solid vocabulary addition. The cross-reference table is
the key structural contribution — it connects smells to existing rules
so reviewers know which rule the smell violates. The severity
classifications are appropriate: only missing_assertions is a block
(it's a direct writing-tests:1 violation).

## Quantified claims

- 1 file modified: skills/_writing-tests-rules.md
- 6 test smells documented
- 4 cross-references to existing rules
- 2 smells with grep-ready detection (missing_assertions, mock_heavy)

## Findings

No findings.
