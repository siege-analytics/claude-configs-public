# Self review: valid nested shelf references

## Assumptions

Goal source: operator report that other sessions failed with `Skill(s) not found: shelves--data-intensive, shelves--geospatial`; refs #842.
Working as: software engineer and tech lead
Pre-author-inventory: validated `shelves--data-intensive` is not resolvable by skill loader, listed actual nested shelf paths under `skills/shelves/`, grepped active skills for invalid references before editing.
Investigate-artifact: plans/self-review-valid-shelf-references.md
Pre-mortem-artifact: plans/self-review-valid-shelf-references.md
Hostile-review-artifact: plans/self-review-valid-shelf-references.md
Project-contribution: prevents collaborator sessions from choking on invalid nested shelf `[skill:]` slugs while preserving DDIA/geospatial shelf routing via explicit file paths.

## Peer review

- writing-rules:1 PASS — fixes guidance references; no new enforcement claimed.
- writing-rules:8 PASS — replaces invalid invocation slugs with valid parent skill plus exact nested file paths.
- shelf-readiness/routing PASS — DDIA is routed through [skill:shelves--systems-architecture] and `skills/shelves/systems-architecture/data-intensive/SKILL.md`; geospatial through `skills/shelves/geospatial/SKILL.md`.
- writing-claims:3 PASS — no claim that nested shelves are directly invokable as `[skill:]` slugs.

## Lead review

Approved. The patch removes the known collaborator-blocking invalid slugs from active skills and keeps the review requirement intact.

## Quantified claims

- 0 remaining active `shelves--data-intensive` / `shelves--geospatial` `[skill:]` refs after grep.
- Build/reference checks pass.
