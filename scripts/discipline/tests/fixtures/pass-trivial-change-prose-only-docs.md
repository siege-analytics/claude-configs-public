# Fixture — PASS

Trivial-change with valid writing-rules:5 Category `prose-only-docs` and
full evidence chain. Ensures the existing Trivial-change validation is
not regressed by PR A's changes.

## Trivial-change declaration

Category: prose-only-docs
Cannot produce error: One paragraph clarifying intent in docs/architecture.md; no behavior, invariant, or API contract is described in the modified text.
Evidence: `git diff --stat` shows 1 file (docs/architecture.md), 4 insertions, 0 deletions.
Falsification: A future agent reads this paragraph and acts on it as a behavior specification.
