---
propagation-deferred: will post to ticket after implementation complete
---

# Pre-mortem: Inventoried-shape trailer enforcement (#205)

Ticket: siege-analytics/claude-configs-public#205

## Context

Add v2.4 check to self-review.sh requiring Inventoried-shape commit
trailer when executable code is in the diff. Trivial-against-state
exemption already exists via v1.2.

## Tigers

**Tiger 1: Existing commits without Inventoried-shape trailer will fail push**
**Severity:** MEDIUM
**Likelihood:** Certain for first push after deployment
**Mitigation:** The check only fires when executable code is in the diff AND
no Trivial-against-state declaration exists. Existing workflows already
produce self-review artifacts with Pre-author-inventory:. Adding
Inventoried-shape to the commit message is a one-line addition.
Operators can always add Trivial-against-state to the self-review
artifact as an escape hatch. Not a launch blocker.

**Tiger 2: False positives on purely-generated code**
**Severity:** LOW
**Likelihood:** Rare
**Mitigation:** Generated code (e.g., protobuf stubs, auto-formatters) can
use Inventoried-shape: N/A with justification or
the Trivial-against-state declaration. The trailer accepts any non-empty
value, including N/A with justification.

**Tiger 3: EXEC_RE_V24 duplicates v2.3 EXEC_RE**
**Severity:** LOW
**Likelihood:** Already present (same pattern defined twice)
**Mitigation:** Intentional. Each version block is self-contained so
future editors can modify one without breaking the other. The regex is
5 characters; duplication cost is negligible vs coupling risk.

## Implementation may proceed: yes

Low-risk addition following established patterns. Trivial-against-state
escape hatch prevents false-positive lockout.
