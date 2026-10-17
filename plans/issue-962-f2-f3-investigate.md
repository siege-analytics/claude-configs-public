# Issue #962 F2/F3 investigation

## Goal and reviewed boundary

Goal source: epic #962 latest handoff comment `issuecomment-6184498727`, findings F2 and F3. Exact implementation base: `0bae4ff108de5ad3b339a868818b05ea1e7c70bd`. Reviewed related findings: PR #957 review `5528052288` and PR #991 review `5528052460`.

The boundary is four supported hook-bearing distributions: `dist/nested`, `dist/flat`, `dist/claude-code`, and `dist/craft-agent`. No main promotion, release, publication, deployment, or installation is authorized.

## Current behavior reproduced before implementation

A clean full build at the exact base showed:

```text
nested:      four runtime files MISSING; prompt=KERNEL_ONLY_SELECTOR_UNAVAILABLE
flat:        four runtime files MISSING; prompt=KERNEL_ONLY_SELECTOR_UNAVAILABLE
claude-code: four runtime files present; prompt=MATCHED_SELECTOR
craft-agent: four runtime files present; prompt=MATCHED_SELECTOR
```

The four files were `bin/resolve-load-set.py`, `catalog/resolver-manifest.json`, `bin/review-risk.py`, and `catalog/review-risk-policy.json`.

A valid Tier A commit in a clean scoped repository produced:

```text
nested exit=2 output=BLOCKED: canonical review risk classifier is unavailable.
flat exit=2 output=BLOCKED: canonical review risk classifier is unavailable.
claude-code exit=0
craft-agent exit=0
```

Both dedicated packages selected the Siege Utilities overlay but returned canonical source paths absent from the package:

```text
projects/siege-utilities/_rules.md
projects/siege-utilities/skills/hostile-review/SKILL.md
```

## Intended observable behavior

1. A from-scratch build puts the four runtime dependencies in every supported package.
2. Every package manifest maps every canonical `source_path` to a readable layout-specific `package_path` and correct packaged byte cost.
3. Selector output retains canonical `source_path` and adds a distinct `load_path`.
4. Hook instructions resolve `load_path` against the installed package root, never the consumer repository cwd, and present only readable in-package paths.
5. The Siege Utilities rule and all three project skills are readable from each isolated installation.
6. Source and all four consumers retain identical route state, project identity, selected slugs, canonical sources, route, priority, and reasons.
7. Foreign host, explicit shelf, unknown prompt, and over-budget behavior remain fail-closed.
8. A valid Tier A push fixture succeeds through each installed package's actual self-review hook.

## Pre-author inventory

### Inputs read

- `bin/build.py`: `build_layout`, manifest generation, consumer package assembly, workspace deployment, and main build order.
- `bin/resolve-load-set.py`: inventory fallback, selection identity, budgets, and JSON output.
- `hooks/resolver/inject-resolver.sh`: package-root discovery and emitted instructions.
- `hooks/git/self-review.sh`, `hooks/lib/scope-check.sh`, `bin/review-risk.py`: push-hook runtime resolution and valid Tier A requirements.
- `bin/install.sh`, `README.md`, `.github/workflows/build-and-publish.yml`: installation, sync, publishing, and CI contracts.
- Existing resolver, mount, language-scope, data-scope, risk, hook, and workflow tests.

### Knowledge requirements

- Generated inventory outputs are authoritative for canonical source-to-package mapping.
- Project skills and rules are prefix-flattened in both layouts.
- Dedicated consumer archives use the flat skill tree; Craft Agent strips incompatible frontmatter, so package costs must be measured after final copy/transform.
- Hook root is `hooks/resolver/../..` or `hooks/git/../..`; consumer repository cwd is unrelated.
- Historical evidence ledgers attest only source/Claude/Craft forms and must not be silently rewritten to invent nested/flat history.

### Contact-point measurements

- Four distributions, four required runtime files each.
- Authoritative inventory: 198 canonical sources, 804 snapshots, 2,904 generated mappings.
- Language parity corpus: 51 fixtures.
- Data/geospatial parity corpus: 78 fixtures.
- Project overlay: one exact GitHub origin, one rule, three project skills.
- Hook scenarios: 36 suites before this change.

### Surface areas

- Build/check/package generation.
- Package manifest path and cost metadata.
- Selector JSON schema (additive field).
- Prompt-hook human-readable instructions.
- Workspace installer validation and manual flat sync documentation.
- CI test wiring and current scope/parity checks.

### Hypothesis

If runtime installation is centralized and parameterized by skill layout, then all hook-bearing packages can ship the same selector/classifier dependency set while each manifest derives its own `package_path` from authoritative inventory outputs. If `source_path` remains the dedupe/provenance key and the hook alone resolves `load_path` under its package root, selection semantics remain unchanged while emitted instructions become readable outside the source checkout.

### Verified Shapes

- PROBED: clean base build showed nested/flat missing all four runtime files while dedicated archives contained them.
- PROBED: clean scoped Tier A repository produced exit 2 for nested/flat and exit 0 for Claude Code/Craft Agent.
- ATTESTED: authoritative inventory supplies exactly one nested and one flat generated output per canonical source.
- PROBED: packaged project selection returned canonical `projects/...` paths absent from dedicated archives.
- ATTESTED: hook root is installation-relative (`hooks/<group>/../..`), while payload cwd belongs to the consumer repository.

### Conclusions

The defect class is package assembly plus runtime presentation, not route classification. The minimal complete fix therefore changes build/runtime/install/test surfaces but does not alter routes, budgets, project host identity, or shelf policy. Clean copied installations are required evidence because source-tree tests can accidentally satisfy missing dependencies.
