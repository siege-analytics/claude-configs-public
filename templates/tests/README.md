# Test stub templates

Skeleton templates used by the scaffold hook (`hooks/create-ticket/scaffold-test-stub.sh`, #661) to generate a failing test file per acceptance criterion when a ticket is created. Part of epic #655 (falsifiable acceptance criteria + auto-gen test stubs).

## Parameters

Every template uses three placeholders. The renderer substitutes them with values from the ticket:

| Placeholder | Source | Example |
|---|---|---|
| `{ticket_id}` | GitHub issue number | `656` |
| `{ac_id}` | Numeric identifier of the AC on the ticket (`AC1` → `1`) | `1` |
| `{feature}` | Short slug for the feature under test | `paginated_search` |

Substitution is plain string replacement; no conditional logic in templates.

## Contract per template

Each rendered stub MUST fail with a message naming the AC when run against an unimplemented target. A green test that hides missing implementation is worse than no test.

The failure message MUST include the ticket ID, the AC number, and the feature name so the reader can locate the ticket and Falsifiable-by clause without extra hunting.

## Templates shipped

| Template | Layer | Framework | File extension |
|---|---|---|---|
| `pytest-unit.py.tmpl` | backend / library | pytest | `.py` |
| `pytest-integration.py.tmpl` | backend / integration | pytest + fixture | `.py` |
| `playwright-e2e.spec.ts.tmpl` | e2e / browser | Playwright | `.spec.ts` |
| `vitest-component.spec.ts.tmpl` | frontend / component | Vitest | `.spec.ts` |
| `schemathesis-contract.yaml.tmpl` | API contract | Schemathesis | `.yaml` |
| `great-expectations-suite.json.tmpl` | data pipeline | Great Expectations | `.json` |
| `k6-scenario.js.tmpl` | performance | k6 | `.js` |

## Adding a new template

Naming convention: `<framework>-<kind>.<ext>.tmpl` (e.g. `zap-baseline.yaml.tmpl`, `terratest-module_test.go.tmpl`).

Requirements:
1. Use `{ticket_id}`, `{ac_id}`, `{feature}` for all substitutable values.
2. Must fail when run against an unimplemented target (throw / assert / raise / fail depending on framework).
3. Must include the ticket ID and AC number in the failure message.
4. Add a row to this README's table.
5. Add the template path as a value in the appropriate layer's `assertion_tools` / `automation_template` recommendation inside `skills/testing-frameworks/SKILL.md`.

## Cross-references

- `[skill:testing-frameworks]` — the layer schema (`assertion_tools`, `automation_template`) that references these templates. Schema landed via #659.
- `[rule:writing-tests]` writing-tests:7 — the rule requiring every AC name a `Falsifiable-by:` observable and a tool from the layer's `assertion_tools`. Landed via #656.
- Epic #655 — the falsifiable-AC + auto-gen initiative these templates are part of.
- `[skill:tool-availability-probe]` (#662) — checks whether the named tool is installed before the scaffold hook renders the stub.
- Scaffold hook (#661) — the renderer that turns these templates into real test files at ticket-creation time.
