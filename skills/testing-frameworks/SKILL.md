---
name: testing-frameworks
description: "Framework guidance for test writing. Projects declare their test frameworks per architectural layer in PROJECT.md; this skill recommends frameworks by language ecosystem and enforces consistent usage. Pairs with _testing-frameworks-rules.md (always-on) and hooks/git/test-guard.sh (mechanical enforcement at push time). The optional per-layer source globs additionally drive hooks/git/decomposition-guard.sh (one-PR-per-layer warning)."
allowed-tools: Read Grep Glob Bash
---

# Testing Frameworks

This skill answers: **which test framework, for which layer, and why.**

The existing test-writing rules (`[`writing-tests`](../_writing-tests-rules.md)`) govern test _quality_ — what makes a good test. This skill governs test _infrastructure_ — which frameworks to use, how to declare them, and how the pipeline verifies they ran.

## Why this exists

The affected-tests gate (`[`commit`](../commit/SKILL.md)` step 4) runs tests at commit time, but two gaps remain:

1. **No framework guidance.** An agent writing tests for a new module has no reference for which framework the project uses. It picks whatever it's seen in training data, producing inconsistent test stacks.
2. **No push-time verification.** The commit skill's step 4 is behavioral — the agent can skip it. The `test-guard.sh` hook closes this gap mechanically: projects that declare a `testing:` section in PROJECT.md _demand_ test evidence at push time.

## Declaring your frameworks

Every project that wants mechanical test enforcement adds a `testing:` section to its `PROJECT.md`:

```yaml
testing:
  layers:
    - name: backend
      framework: pytest
      test_dir: tests/
      pattern: "test_{stem}.py"
      source: ["src/**/*.py", "app/**/*.py"]
    - name: frontend
      framework: vitest
      test_dir: src/**/__tests__/
      pattern: "{stem}.spec.ts"
      source: ["src/**/*.vue", "src/**/*.ts"]
    - name: e2e
      framework: playwright
      test_dir: tests/e2e/
      pattern: "{stem}.spec.ts"
```

Each layer names:
- **name** — human-readable layer identifier
- **framework** — the test runner for this layer
- **test_dir** — where test files live (glob-compatible)
- **pattern** — naming convention (`{stem}` = source file basename without extension)
- **source** *(optional)* — glob list of production source files that belong to this layer. Drives `hooks/git/decomposition-guard.sh`: each touched file maps to exactly one layer (longest-literal-prefix wins), and a push or PR spanning more than one layer is flagged. Layers without `source:` (e.g. e2e/flow layers) are layer-neutral and never counted.

Projects without a `testing:` section are unaffected by the hook. Once declared, testing is demanded — the hook blocks pushes without test evidence.

## Source globs and decomposition enforcement

The optional `source:` field on each layer lists the production files that belong to that layer. It turns the prose `[`ticket-decomposition`](../ticket-decomposition/SKILL.md)` doctrine — *one ticket/PR per architectural layer* — into a mechanical check:

- `hooks/git/decomposition-guard.sh` maps every touched source file to exactly one layer (longest-literal-prefix wins) at push / PR time.
- When a single push or PR spans more than one layer, the hook **warns** (V1 is warning-only; it never blocks).
- Files matching no `source:` glob (tests, docs, config, scaffolding) are layer-neutral and never counted.
- Override an intentional multi-layer push with `[multi-layer-ok: <reason>]` in the latest commit body.

`source:` is optional and independent of `test_dir`/`pattern`: a project can adopt test enforcement (`test-guard.sh`) without decomposition enforcement, or both. Projects with no `source:` globs are unaffected by `decomposition-guard.sh`.

## Framework recommendations by ecosystem

### Python [PROVEN]

| Framework | Use when | Notes |
|---|---|---|
| **pytest** | Default for all Python testing | De facto standard. Fixtures, parametrize, plugins. |
| **pytest-cov** | Coverage measurement | Pairs with pytest. `--cov --cov-report=term-missing`. |
| **hypothesis** | Property-based testing | When the input space is large or the invariant is expressible as a property. Not a replacement for example-based tests — a complement. |
| **pytest-mock** with `spec=` | Mocking external libraries | Ties to `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:4. Always pass `spec=RealClass` to prevent mock drift. |

**Decision:** pytest is the only recommended Python test runner. unittest is accepted in legacy codebases but not recommended for new projects. nose/nose2 are deprecated.

### JavaScript / TypeScript [PROVEN]

| Framework | Use when | Notes |
|---|---|---|
| **Vitest** | Vue, React, or any Vite-based project | Fast, ESM-native, Jest-compatible API. |
| **Jest** | Node.js backend, non-Vite projects | Mature ecosystem. Use Vitest if the project uses Vite. |
| **Playwright** | End-to-end browser testing | Cross-browser. Prefer over Cypress for new projects (better parallelism, no same-origin restriction). |

**Decision:** Vitest for frontend unit/integration, Jest for Node backend, Playwright for E2E. Do not mix Vitest and Jest in the same project unless legacy constraints require it.

### SQL [RECOMMENDED]

| Framework | Use when | Notes |
|---|---|---|
| **dbt test** | Data quality on dbt-managed models | Schema tests (not_null, unique, relationships) and custom SQL tests. |
| **Great Expectations** | Data quality outside dbt | When the data pipeline is not dbt-managed. |
| **Assertion queries** | Stored procedure / function testing | Write SQL that asserts expected output and raises on failure. No framework needed — the database is the test runner. |

**Decision:** Use whatever the data pipeline already uses. dbt projects use dbt test. Non-dbt projects use Great Expectations or raw assertion queries. Do not introduce dbt solely for testing.

### JVM [RECOMMENDED]

| Framework | Use when | Notes |
|---|---|---|
| **JUnit 5 + Mockito** | Java projects | JUnit 5 for structure, Mockito for mocking. Prefer `@ExtendWith(MockitoExtension.class)` over manual mock setup. |
| **kotest** | Kotlin projects | Property-based testing built in. Coroutine-native. |
| **ScalaTest** | Scala projects | FlatSpec or FunSuite style. Pairs with ScalaCheck for property-based testing. |

**Decision:** Match the language. JUnit 5 for Java, kotest for Kotlin, ScalaTest for Scala. Do not use JUnit 4 for new projects.

### Rust [EXPERIMENTAL]

| Framework | Use when | Notes |
|---|---|---|
| **Built-in `#[test]`** | All Rust testing | Part of the language. No external dependency needed. |
| **proptest** | Property-based testing | Rust equivalent of hypothesis. Shrinking is built in. |

**Decision:** Use the built-in test framework. proptest when the input space warrants property-based testing. Limited direct validation in our projects — hence [EXPERIMENTAL].

## Decision tree: test type selection

```
Is this testing a contract between systems?
├── YES → Integration test (real dependencies, test containers or fixtures)
│   └── Does the contract cross a network boundary?
│       ├── YES → E2E test (Playwright, real HTTP)
│       └── NO → Integration test (real DB, real filesystem)
└── NO → Unit test (isolated, mocked dependencies)
    └── Is the input space large or continuous?
        ├── YES → Property-based test (hypothesis, proptest, kotest)
        └── NO → Example-based test (parametrize with specific cases)
```

**When property-based testing pays off:**
- Serialization/deserialization roundtrips
- Parsers (any input should either parse correctly or raise a defined error)
- Numeric computations with known invariants (e.g., area is always positive)
- Data transformations where output shape is predictable from input shape

**When property-based testing is overkill:**
- CRUD operations with fixed schemas
- UI component rendering
- Configuration validation with a small, enumerable input space

## What makes a good test

Three quality tests (apply to any framework):

1. **The revert test.** If I reverted the implementation, would this test go red? If no, the test verifies the mock setup, not the code. This is `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:1.

2. **The cold reader test.** Can someone unfamiliar with the codebase read this test and understand what behavior it verifies? If the test requires reading the implementation to understand what it asserts, the test name or arrangement is too opaque.

3. **The maintenance test.** Does this test break when I refactor the implementation without changing the behavior? If yes, the test is coupled to implementation details, not the contract. Refactoring should not require test rewrites unless the contract changes.

## Signal file: test-gate.json

After running affected tests (`[`commit`](../commit/SKILL.md)` step 4), write evidence to `test-gate.json` at the workspace root:

```json
{
  "ticket": "#386",
  "lastUpdated": "2026-06-09T14:30:00Z",
  "evidence": [
    {
      "source": "siege_utilities/geo/boundaries.py",
      "test": "tests/geo/test_boundaries.py",
      "result": "pass",
      "framework": "pytest",
      "timestamp": "2026-06-09T14:28:00Z"
    }
  ]
}
```

The `test-guard.sh` hook reads this file at push time and verifies evidence covers all touched source files.

## Cross-references

- `[`writing-tests`](../_writing-tests-rules.md)` — test quality rules (mock fidelity, no cargo-cult, etc.)
- `[`testing-frameworks`](../_testing-frameworks-rules.md)` — always-on rules for framework declaration and usage
- `[`commit`](../commit/SKILL.md)` step 4 — the affected-tests gate that runs tests and writes the signal file
- `hooks/git/test-guard.sh` — mechanical enforcement at push time
- `hooks/git/decomposition-guard.sh` — one-PR-per-layer warning at push time, driven by the per-layer `source:` globs
- `[`ticket-decomposition`](../ticket-decomposition/SKILL.md)` — the one-ticket/PR-per-layer doctrine that `source:` globs make mechanically checkable
