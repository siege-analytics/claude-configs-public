---
ticket_refs:
  - siege-analytics/claude-configs-public#571: comment pending
type: pre-mortem
---

# Pre-mortem: Mission-alignment gate (#571)

## Risk classification

Severity: Medium

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Agents produce formulaic Project-contribution that passes hook but adds no value | High | Medium | Hook rejects echo of ticket title; hostile reviewer checks substance |
| Projects without mission field break the gate | Medium | High | Gate only enforces when mission field exists; no mission = no check |
| Self-review hook regex is too strict (false rejects on valid contributions) | Low | Medium | Pattern is simple presence check, not content validation |
| Existing self-review artifacts retroactively fail with new field | None | High | New field is additive — old artifacts missing it get a warning, not a block |

## Tiger / Elephant classification

No Launch-Blocking Tigers. The gate is additive — it adds a required field to new self-review artifacts. Existing artifacts are grandfathered. The hook enforcement is a presence check, not content validation. The hostile reviewer provides the substance check as a non-mechanical layer.
