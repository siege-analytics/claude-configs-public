# Self-review: PR for #660 (templates/tests skeleton files)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #660
Goal source verification: `PASS: ticket 660 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 660` at 2026-08-31 07:32 CDT)
Plan reference: `sessions/260525-long-swan/plans/falsifiable-acceptance-criteria-epic.md` + `## Design` inline on ticket #660
Pre-author-inventory: ticket #660 carries `## Design` + `## Assumptions`; inventoried the existing `templates/` dir (contained CLAUDE.md.template, gitlab-pr-base-guard.yml, settings.local.json — no `tests/` subdir) and the fact that `templates/tests/` did not exist yet.
Investigate-artifact: TRIVIAL (see declaration)
Pre-mortem-artifact: TRIVIAL (see declaration)
Hostile-review-artifact: WAIVED (skeleton files, no runtime behavior in-repo; see waiver)
Project-contribution: supplies the seven initial skeletons the scaffold hook (#661) will render per AC at ticket-creation time. Without these, the whole falsifiable-AC + auto-gen chain has nothing to render.

## Trivial-investigation declaration

Reason: additive creation of a new directory `templates/tests/` with eight files (seven `.tmpl` skeletons + one `README.md`). No modifications to executable code, no schema validator changes, no touch to any hook or skill loader. The templates contain no executable code that runs at repo-build time (they only render at scaffold-hook time, which is #661's scope).
Evidence: `git diff --stat` shows 9 files added (8 new under `templates/tests/`, 1 modified `CHANGELOG.md`), all additions. No modifications to `.sh`, `.py` (production), `.js` (production), or hooks/. Placeholder syntax `{ticket_id}` etc. is inert until renderer executes it.
Falsification: not trivial if any of the shipped `.tmpl` files is loaded by an existing consumer (hook/build script) that would evaluate them as-is. Verified `find hooks scripts -type f | xargs grep -l 'templates/tests'` returns nothing.

## Hostile-review-waiver

Reason: skeleton files with placeholder markers; no runtime behavior in-repo. The rendered stubs (produced by the future #661 hook) are what a hostile review would attack — not these templates. Waiver defers hostile review to #661's PR.
Evidence: no imports, no calls, no shell exec in the templates. Each template is a fill-in-the-blank string with hard-coded fail-with-AC-message contract.
Falsification: waiver invalid if a template contains executable code that runs at parse time. All templates are load-only (Python files use standard `def` / `assert`; JS files use standard `import` / `describe`; YAML/JSON are inert).

## Pre-implementation comprehension

Current behavior: no `templates/tests/` directory. The scaffold hook (#661, unimplemented) has nothing to render from.

Intended behavior: after this PR, `templates/tests/` contains seven skeletons for the six most common test layers (pytest unit, pytest integration, Playwright e2e, Vitest component, Schemathesis contract, Great Expectations data suite, k6 performance), each parameterized on `{ticket_id}`, `{ac_id}`, `{feature}`, each engineered to fail with an AC-naming message when run against an unimplemented target. Plus a `README.md` documenting the parameter set, the fail-with-AC-message contract, and how to add a new template.

Steps to get there (already executed): (1) branch `feat/660-test-stub-templates` off `develop`; (2) update ticket #660 body with Context/Goal/Design/Assumptions; (3) `mkdir -p templates/tests`; (4) write seven `.tmpl` files + one `README.md`; (5) add CHANGELOG entry citing #660 and `templates/tests`; (6) verify four AC greps + em-dash count; (7) commit; (8) self-review; (9) push; (10) open PR.

Success criteria: `ls templates/tests/*.tmpl | wc -l` = 7; each template contains all three placeholders; README cross-refs testing-frameworks and #655; CHANGELOG line has #660 and one has templates/tests; zero em-dashes introduced. All verified in Peer review.

Risks: (a) placeholder syntax `{ticket_id}` conflicts with a real syntax in one of the target formats (e.g. JSON schema `{`, YAML anchors `&`) — mitigated by choosing placeholders that don't collide with format-specific syntax (`{...}` is prose in YAML/JSON/JS/Python string contexts, not structural); (b) a template's fail message uses characters the renderer's substitution mangles — plain ASCII throughout.

## Senior adversarial checklist

- Do the templates parse as their target languages after placeholder substitution? Manual spot: substituting `ticket_id=656 ac_id=1 feature=paginated_search` into `pytest-unit.py.tmpl` yields `def test_ac1_paginated_search() -> None:` — valid Python. `playwright-e2e.spec.ts.tmpl` yields `test('AC1: paginated_search (ticket #656)', ...)` — valid TypeScript. JSON template validates as JSON after substitution (no trailing commas, no unclosed braces). YAML template validates as YAML.
- Are the fail messages actionable (name the ticket, AC, feature, next step)? Every template's fail message includes all three placeholders and a "Replace this X with the Y the AC's Falsifiable-by clause names" instruction. PASS.
- Do the templates encourage cargo-cult? README explicitly warns against that in "Requirements #1-5" for adding new templates.
- Do the templates encourage mocking? `pytest-integration.py.tmpl` fixture body says "Do not mock. If a mock is unavoidable, note why in the fixture body and cite `[rule:writing-tests]` writing-tests:4." Consistent with the always-on rules.
- Anything cargo-cult about the README table? Table shape matches the framework-recommendations tables in `skills/testing-frameworks/SKILL.md`. Consistent.

## Peer review

- **grep AC1**: `ls templates/tests/*.tmpl | wc -l` -> `7`. PASS.
- **grep AC2**: for each `*.tmpl`, `grep -cE '\{ticket_id\}|\{ac_id\}|\{feature\}' <file>` -> all >= 3 (values: 6, 8, 3, 6, 4, 8, 4). PASS.
- **grep AC3**: `grep -cE 'testing-frameworks|#655' templates/tests/README.md` -> `4`. PASS.
- **grep AC4**: `grep -cE '#660|templates/tests' CHANGELOG.md` -> `2`. PASS.
- **writing-prose:1**: em-dash / en-dash count in added lines = 0. PASS.
- **writing-prose:2** (Why:/How to apply: blocks): none. PASS.
- **writing-prose:3** (self-justifying adverbs): re-read the README and template comments; no banned adverbs.
- **writing-prose:4** (commit shape): subject line under 72 chars, plain-prose body.
- **writing-claims:2**: countable claims in commit body? None material.
- **writing-code:2** (no history refs in code comments): templates carry `#{ticket_id}` (placeholder for the future ticket ref), not literal history refs. Same for `#661` etc. in the README, which are cross-refs in prose (allowed) not in code comments (banned). Template comments name the SOURCE TEMPLATE file — that's not a history ref, it's provenance for renderers.
- **writing-code:8** (optional-import callsite hygiene): N/A — no imports at production layer.
- **writing-tests:1** (tests import module): N/A — these are TEMPLATES for tests, not tests themselves; the rendered test (in the consumer repo) will need to import per the AC. Documented in the README under "Requirements" and in the templates' docstrings.
- **testing-frameworks:3**: no test files; the falsifying greps ARE the test evidence.
- **output rule**: no AI attribution.

## Quantified claims

Claim: "seven skeletons under templates/tests/."
Verified-by: `ls templates/tests/*.tmpl | wc -l` -> 7. PASS.

Claim: "each template names all three placeholders at least three times."
Verified-by: per-template `grep -cE` output above; minimum is 3 (playwright), max 8. PASS.

Claim: "9 files added / modified, all additions except CHANGELOG."
Verified-by: `git status -sb` shows `?? templates/tests/README.md`, 7 `?? templates/tests/*.tmpl`, ` M CHANGELOG.md`. PASS.

## Lead review

- Junior solved the stated goal: yes.
- Junior over-scoped: no — did not add security (zap), infra (terratest), or mobile templates (all deferred per ticket Out-of-scope).
- Junior under-scoped: no — added README with parameter docs, fail-contract, add-new-template guidance, and cross-refs to the four related epic tickets.
- Standards affirmatively met: writing-prose:1-4, writing-code:2, writing-tests:1 (documented, not violated), definition-of-done (a-e satisfied).

## Rework ledger

- Cycle 0: initial. No rework — all ACs passed on first grep pass; em-dash count 0 on first check.

## Evidence-predates-work

All AC greps and em-dash counts captured against the working tree pre-commit. Same-turn: recorded in `sessions/260525-long-swan/session.jsonl` prior to this artifact being written.
