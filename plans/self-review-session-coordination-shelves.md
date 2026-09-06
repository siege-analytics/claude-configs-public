# Self-review: session coordination and rule typography sweep

## Assumptions

Goal source: operator instruction in Craft Agent session 260905-clever-quasar to put the hub decision checklist/control-surface behavior into the rule, then review rules thoroughly and fix discovered rule problems.
Working as: tech lead for rules and skill governance.
Pre-author-inventory: same-turn audit over `skills/_*rules.md`, `skills/RULES.md`, and `skills/_coverage.md` for conflict markers, token regressions, raw rule links, typographic Unicode, coverage TOML validity, duplicate coverage names, and build/reference validation.
Investigation-artifact: TRIVIAL
Pre-mortem-artifact: TRIVIAL
Project-contribution: strengthens the always-on rule corpus by making hub/spoke coordination preserve the operator control surface and making existing rule files comply with their own typography rule.

## Peer review

Shelf checks: writing-prose:1, session-coordination:5, session-coordination:6, writing-rules:2, writing-claims:2.

Gate evidence:

- Rule hygiene scanner: `rule_files 35 issues 0`.
- Coverage parse: `coverage_entries 37 duplicates 0`.
- `python3 bin/build.py --check` passed; discovered 155 leaf skills, 35 rules, 3 project skills, 1 project rules.
- `python3 bin/sync-skill-references.py --check` passed; `Summary: 0 files, 0 skill refs, 0 rule refs converted`.

Review findings:

- The initial copy from the stale workspace would have regressed token references and overwritten the `acceptance-criterion-without-falsifying-observable-or-tool` coverage row. Corrected by restoring from the clean develop-sync branch and reapplying only the intended rule changes.
- All banned typographic Unicode discovered in rule files was swept as part of the same branch, rather than leaving a known rules-corpus violation.
- Shelf readiness: the new session-coordination rules are in an always-on rule file and indexed from `skills/RULES.md`; peer-review shelf citations in this artifact make the rule path visible to rule-review workflow. No new bookshelf entry is required for this operational coordination rule.

## Trivial-investigation declaration

Category: rule text and hygiene-only change after direct inventory.
Cannot produce error: no runtime code path is modified in this branch; behavior change is instructional policy and ASCII typography cleanup in markdown rule files.
Evidence: build/reference checks and coverage TOML parse passed after edits.
Falsification: a conflict marker, token regression, duplicate coverage row, build failure, or remaining banned typographic Unicode in `skills/_*rules.md` would falsify this declaration.
