---
name: ticket-decomposition
description: "Decompose multi-layer work into per-layer tickets before implementation. Reads architectural layers from PROJECT.md's testing.layers schema. Merges authoring-side (decomposition table, per-layer ticket filing) and consumer-side (picking up per-layer tickets) into one protocol. Includes assertion classification vocabulary (spec'd / current / invariant)."
allowed-tools: Read Grep Glob Bash
---

# Ticket Decomposition

This skill answers: **does this work touch more than one architectural layer, and if so, have you filed separate tickets for each?**

Multi-layer work (backend + frontend, library + notebook, service + migration) crammed into a single ticket produces reviews that are too large, tests that conflate layers, and merges that are hard to revert partially. Decomposition is the fix: one ticket per touched layer, linked under a parent epic.

## When this skill fires

- Filing a ticket for work that might touch multiple layers
- Creating an epic with child tickets
- Picking up a per-layer ticket that was decomposed by another agent

**Not required for:** single-layer work (only one declared layer touched), doc-only changes, config-only changes.

## Layer source: PROJECT.md

The project's architectural layers come from the `testing.layers` schema in `PROJECT.md` (defined by `[rule:testing-frameworks]` testing-frameworks:1):

```yaml
testing:
  layers:
    - name: library
      framework: pytest
      test_dir: tests/
      pattern: "test_{stem}.py"
      source: ["siege_utilities/**/*.py"]
    - name: frontend
      framework: vitest
      test_dir: src/__tests__/
      pattern: "{stem}.spec.ts"
      source: ["src/**/*.ts", "src/**/*.vue"]
    - name: e2e
      framework: playwright
      test_dir: tests/e2e/
      pattern: "{stem}.spec.ts"
```

If the project has no `testing.layers`, decomposition falls back to flat: file one ticket, no layer table. Decomposition is most valuable when layers are declared; without them, the skill degrades gracefully.

## Mechanical enforcement: decomposition-guard

When layers declare `source:` globs (the optional field documented in `[skill:testing-frameworks]`), the `hooks/git/decomposition-guard.sh` hook enforces this skill's one-ticket/PR-per-layer rule mechanically. At push / PR time it maps each touched source file to its layer (longest-literal-prefix wins) and **warns** when a single PR spans more than one layer. This is the push-time backstop for the authoring-time decomposition table below: the table is behavioral (the agent can skip it), the hook is mechanical. V1 is warning-only. Intentional multi-layer pushes (Step-1/2 plumbing, explicit cross-referenced waivers) carry `[multi-layer-ok: <reason>]` in the latest commit body. Projects without `source:` globs are unaffected.

## Authoring protocol

Follow this protocol when filing tickets for work that may touch multiple layers.

### Step 1: Fill the decomposition table

Create a table with one row per layer from `testing.layers`. Every row gets a verdict:

| Layer | Touched? | Why |
|---|---|---|
| library | yes | New function in `siege_utilities/geo/boundaries.py` |
| frontend | no | No UI changes |
| e2e | unclear | May need a new smoke test if boundary API changes |

**No blanks.** Every layer must have a verdict and a reason. "Not sure" is acceptable as `unclear` with a reason; an empty cell is not.

### Step 2: Self-check

If only ONE row says "yes," re-read the work description. Single-layer tickets are real but rare for non-trivial work. Common false-negatives:

- Backend change that affects API shape → frontend may need update
- Library change that affects public signature → notebooks may need update
- Schema migration → tests definitely need update

If after re-reading, only one layer is genuinely touched, proceed with a single ticket. The self-check exists to catch under-counting, not to force multi-ticket work.

### Step 3: Multi-option self-check

If framing any row as "decision between A/B/C," verify the options represent different user-visible outcomes, not just different code shapes. "Should we use a class or a function?" is a code shape decision within one layer. "Should the filter happen client-side or server-side?" crosses layers and affects user experience.

### Step 4: File per-layer tickets

For each layer marked "yes" or "unclear" (after investigation resolves to "yes"):

1. Create one ticket per touched layer
2. Link all per-layer tickets under a parent epic
3. Each ticket's acceptance criteria names:
   - The test framework (from `testing.layers`)
   - The test file path pattern (from `testing.layers`)
   - The assertion class for key tests (spec'd / current / invariant)

### Step 5: Post decomposition table

Post the filled decomposition table as a comment on the parent epic. Include a maintainer marker so the table is findable:

```markdown
## Decomposition table (maintainer)

| Layer | Touched? | Why | Ticket |
|---|---|---|---|
| library | yes | New boundary function | #401 |
| e2e | yes | Smoke test for new endpoint | #402 |
| frontend | no | No UI changes | -- |
```

## Consumer protocol

Follow this protocol when picking up a per-layer ticket that was decomposed by another agent.

### Step 1: Read the parent epic's decomposition table

Find the decomposition table on the parent epic. It tells you what layers are in scope, which tickets cover which layers, and why.

### Step 2: Validate, don't re-derive

The decomposition table was created at authoring time. Validate it against the current state of the codebase rather than re-deriving from scratch. Check:

- Is the layer assignment still correct? (Has the scope changed since authoring?)
- Are the assertion classifications still appropriate?
- Has another agent already completed work on a related layer ticket?

### Step 3: Pick per-layer framework

Read `testing.layers` in PROJECT.md to identify the correct test framework, test directory, and file naming pattern for your layer's ticket.

### Step 4: Classify assertions

For each test you write, classify the assertion:

| Class | Meaning | Example |
|---|---|---|
| **spec'd** | Verifies behavior defined in a spec or contract | "Function returns GeoDataFrame with 'geometry' column per the API contract" |
| **current** | Captures current behavior (regression test) | "Census API returns 52 states+territories; test locks this count" |
| **invariant** | Verifies a business rule that must always hold | "Area is always positive for valid geometries" |

The classification goes in the test's docstring or a comment on the assertion. It helps reviewers understand what the test is protecting.

### Step 5: Fresh-read before flagging

Before flagging concerns about another agent's decomposition or implementation, fresh-read the relevant files and the parent epic context. The decomposition table may reflect context you don't have.

## Assertion classification vocabulary

Three classes for test assertions, usable across all projects:

- **spec'd** -- the assertion verifies behavior defined in a specification, API contract, or interface definition. If the spec changes, the assertion must change. These are the most durable tests.
- **current** -- the assertion captures current behavior as a regression guard. The behavior is not derived from a spec; it is observed and locked. These tests are fragile by design -- they should break when behavior changes, forcing the author to decide whether the change is intentional.
- **invariant** -- the assertion verifies a property that must hold regardless of implementation. Mathematical invariants (area > 0), domain rules (GEOID format), and business constraints (unique per vintage) fall here. These tests should survive refactoring unchanged.

This vocabulary is documented here for reference. See `[rule:writing-tests]` for the test quality rules that govern how assertions are written.

## Cross-references

- `[rule:testing-frameworks]` testing-frameworks:1 -- projects declare layers in PROJECT.md
- `[skill:testing-frameworks]` -- framework guidance per layer, and the optional `source:` glob field
- `hooks/git/decomposition-guard.sh` -- push-time one-PR-per-layer warning (requires `source:` globs)
- `[rule:definition-of-done]` criterion (g) -- multi-layer decomposition (opt-in)
- `[skill:create-ticket]` -- ticket creation mechanics
- `[skill:pre-work-check]` -- pre-work verification including ticket existence
- `[skill:decision-to-ticket]` -- when decomposition reveals a scope decision
