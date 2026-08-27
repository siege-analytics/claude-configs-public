---
description: Always-on. Test framework declaration and enforcement. Projects declare their test frameworks per architectural layer in PROJECT.md; agents must use the declared frameworks for new tests; the test-guard hook verifies test evidence at push time. Framework guidance lives in `skills/testing-frameworks/SKILL.md`; test quality rules live in `_writing-tests-rules.md`.
---

# Testing Frameworks

These rules enforce consistent test framework usage across projects. They complement the test-quality rules in `[`writing-tests`](_writing-tests-rules.md)` (which govern _how_ to write tests) with infrastructure rules governing _which frameworks_ to use and _how evidence is verified_.

The enforcement model follows the branch-guard pattern: the skill educates (`[`testing-frameworks`](testing-frameworks/SKILL.md)`), the rules define vocabulary (this file), and the hook blocks mechanically (`hooks/git/test-guard.sh`).

## The rules

**testing-frameworks:1. Projects MUST declare their test frameworks in PROJECT.md.**

The `testing:` section in `PROJECT.md` lists the project's architectural layers, the test framework for each layer, the test directory, and the file naming pattern. This section is the source of truth for which frameworks the project uses.

A project without a `testing:` section is not subject to mechanical test enforcement (the hook exits 0). But the absence is a gap to fill, not a design choice to accept. When starting work on a project without a `testing:` section, add one as part of the first PR that touches test files.

```yaml
testing:
  layers:
    - name: backend
      framework: pytest
      test_dir: tests/
      pattern: "test_{stem}.py"
```

**testing-frameworks:2. New test files MUST use the project's declared framework.**

When writing a new test file, use the framework declared in `PROJECT.md` for the relevant layer. Using an undeclared framework (e.g., writing a Jest test in a project that declares Vitest) requires updating `PROJECT.md` first — the declaration change is part of the PR, not a follow-up.

This prevents framework drift where different modules accumulate different test runners, making CI configuration increasingly complex and test maintenance increasingly expensive.

Enforcement: judgment-enforced via `[`code-review`](code-review/SKILL.md)` until a mechanical scanner lands. The code-review skill checks new `test_*.py` / `*.spec.ts` / `*.test.ts` files against the declared framework in `PROJECT.md`.

**testing-frameworks:3. Test evidence is recorded and mechanically verified.**

The affected-tests gate (`[`commit`](commit/SKILL.md)` step 4) writes test results to `test-gate.json` at the workspace root after tests pass. This signal file records which source files were tested, which test files ran, the framework used, and the result.

The `test-guard.sh` hook reads this signal file at push time and verifies that every touched source file has recorded test evidence. Projects that declare a `testing:` section in `PROJECT.md` demand test evidence — the hook blocks (exit 2) when evidence is missing.

Override: `[run-skip: reason]` in the commit body. The hook reads the latest commit message and allows the push with a warning when this override is present. Legitimate cases: test infrastructure under repair, external dependency unavailable. Using the override more than once per session is a smell — track frequency.

## Operationalization

| Rule | Enforcement |
|---|---|
| testing-frameworks:1 (declare frameworks) | `bin/build.py` validates `testing:` schema in PROJECT.md for active projects; `[`pre-work-check`](pre-work-check/SKILL.md)` warns on missing section |
| testing-frameworks:2 (use declared framework) | Judgment-enforced via `[`code-review`](code-review/SKILL.md)`; scanner deferred |
| testing-frameworks:3 (record and verify evidence) | `hooks/git/test-guard.sh` blocks pushes without evidence; `[`commit`](commit/SKILL.md)` step 4.6 writes `test-gate.json` |

## Cross-references

- `[`testing-frameworks`](testing-frameworks/SKILL.md)` — framework guidance, decision tree, quality tests
- `[`writing-tests`](_writing-tests-rules.md)` — test quality rules (mock fidelity, no cargo-cult, skip messages, untested except blocks, inspection vs behavioral)
- `[`commit`](commit/SKILL.md)` step 4 — the affected-tests gate that produces the evidence
- `hooks/git/test-guard.sh` — the mechanical enforcement at push time

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI/agent attribution in tests, fixtures, commits, or comments.
