# Focused self-review: coordination supervision alias

## Assumptions

Review tier: B
Domain(s): software engineering, session coordination
Working as: software engineer
Goal source: approved Skill Library Simplification Plan, Phase 6 session/coordination batch
Goal source verification: process small thematic batches and preserve compatibility aliases while consumers remain.
Affected consumers: `tandem-agent:4` remains present; `_coverage.md` retains its three-rule mapping. `session-coordination:9` becomes the canonical post-handoff supervision contract. Tandem-only resume/retire and bounded-batch refinements remain local.

## Test plan

- `hooks/_test/coordination_alias.test.sh` checks alias identifier, canonical target, retained refinements, and coverage mapping;
- run inventory/lifecycle/authority and all hook suites;
- verify kernel/load sets unchanged;
- rollback by reverting this commit.

Measured canonical source reduction: 6,204 -> 6,041 characters, down 163 characters / approximately 40 estimated tokens.
