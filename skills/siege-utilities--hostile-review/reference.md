# Hostile Review -- Check Catalog

Detailed check procedures for each priority level in the hostile review.
Each check includes the grep commands or inspection steps the Adversary
runs, the shelf rule it enforces, and examples of the failure shape.

## SU-1 checks: Errors as data

### Tier 1 (lintable -- confirm linter caught these)

```bash
grep -rn "except:$\|except Exception:" siege_utilities/ --include="*.py" | grep -v "# noqa"
```

### Tier 2 (hostile review -- narrowed except blocks with bad returns)

```bash
# Return statements inside except blocks
grep -rn -A3 "except \w" siege_utilities/ --include="*.py" | grep "return \[\]\|return {}\|return \"\"\|return 0\b\|return 0\.0\|return None"
```

For each hit: does the function's return type annotation include `Optional`?
Does the docstring document `None` as a failure indicator? Does at least
one caller check for it? If no to all three: SU-1 Tier 2 violation.

### Tier 3 (hostile review -- non-error paths returning wrong types)

No grep shortcut. Read the function body. Does it compute a meaningful
value, then return something else? Example: computes `rowcount` but
returns `pd.DataFrame()`. This is a logic bug producing the same
symptom as SU-1.

## SU-2 checks: Contract lies

### Silently dropped parameters (writing-code:9)

For each function in the diff, compare the signature against the body:

```bash
# List all parameters for the function, then grep the body for each
# Flag: parameter has a non-None default, is not referenced in the body,
# and is not forwarded via **kwargs
```

Manual inspection required. The AST scanner handles some cases but
not all (decorator-consumed parameters, **kwargs forwarding).

### Capability registry mismatches (writing-code:10)

```bash
# Find capability registries
grep -rn "SUPPORTED\|_SUPPORTED\|VALID_\|ALLOWED_" siege_utilities/ --include="*.py" | grep -i "frozenset\|set(\|dict("
```

For each registry: does every implementation gated by the registry
actually support every item in it? A validator that accepts
`approx_count_distinct` but a pandas backend that doesn't implement
it is a registry lie.

### Enumerated parameter validation

For each function with a docstring listing valid parameter values:
does the implementation validate at the top and raise `ValueError`
for unrecognized inputs? Or do invalid values silently fall through
to a default code path?

## Composition seam checks

### CRS assumption propagation

```bash
# Find hardcoded CRS assumptions
grep -rn "4326\|3857\|epsg\|EPSG" siege_utilities/ --include="*.py" | grep -v test | grep -v "#"
```

For each: is the CRS documented in the function's contract? Can a
caller pass a different CRS without the function noticing and
producing wrong results?

### Optional dependency guard completeness (writing-code:8)

```bash
# Find availability flags
grep -rn "_AVAILABLE\|_INSTALLED\|HAS_" siege_utilities/ --include="*.py" | grep "= False"
```

For each flag: grep for usages of the guarded library in the same
module. Every usage outside a guarded block is a violation.

### Engine abstraction consistency

For each operation claimed by the engine abstraction layer: does
every engine actually implement it? Does every engine fail the same
way when it can't?

```bash
# Find engine-specific implementations
grep -rn "class.*Engine.*:" siege_utilities/ --include="*.py"
```

Compare method sets across engines. Missing methods that the base
class declares are SU-2 violations. Methods that silently return
different types across engines are composition seam failures.

### Failure mode consistency (writing-code:13)

For each class with sibling methods (same prefix, same verb pattern):
do they all fail the same way? One raises, another returns None, a
third logs and continues -- three failure modes in one family.

### Exception-as-dispatch (writing-code:14)

```bash
# Find try/except blocks that return a different valid result in except
grep -rn -A5 "try:" siege_utilities/ --include="*.py" | grep -B5 "except.*:" | grep -A2 "return "
```

For each: is the input content-distinguishable? Can you inspect the
input (regex, type check, leading bytes) instead of catching?

### Blocking I/O without timeout (writing-code:15)

```bash
grep -rn "requests\.\(get\|post\|put\|delete\|head\|patch\)\|subprocess\.\(run\|call\|check_call\|check_output\)\|urlopen\|socket\.create_connection" siege_utilities/ --include="*.py" | grep -v "timeout"
```

Every hit without `timeout=` is a violation.

## Coverage checks

### SU-4a: Notebook drift

For each function signature change in the diff:

```bash
# Check if any notebook calls the changed function
grep -rn "function_name" notebooks/ --include="*.ipynb"
```

If a notebook calls it: does the notebook use the old or new signature?

### SU-4b: Error-path test coverage

For each module in the diff:

```bash
# Count except/raise sites
grep -c "except \|raise " siege_utilities/module.py

# Count error-themed tests
grep -c "def test.*\(error\|fail\|invalid\|missing\|raises\)" tests/test_module.py
```

If the second count is significantly less than the first: P2 finding.

### Mock fidelity (writing-tests:4)

```bash
# Find MagicMock without spec
grep -rn "MagicMock()" tests/ --include="*.py" | grep -v "spec"
grep -rn "Mock()" tests/ --include="*.py" | grep -v "spec"
```

Each unspec'd mock standing in for an external library object is a
violation unless commented with rationale.

## Migration checks

### Migration completeness (writing-code:16)

After any module move or rename:

```bash
grep -rn "old_module_path" . --include="*.py" | grep -v __pycache__
```

Non-empty output means incomplete migration.

### Deprecation shim follow-up (writing-code:17)

For each deprecation shim in the diff:

```bash
# Find DeprecationWarning
grep -rn "DeprecationWarning" siege_utilities/ --include="*.py"
```

Each shim must have a companion ticket listing remaining consumers
and a removal version.

## Process audit checks

### Ticket assumption verification

Read the ticket's Assumptions section. For each factual claim:

```bash
# Verify against target branch
git show origin/develop:path/to/file.py | grep "claimed_pattern"
```

If the claim doesn't match current develop: Assumption falsified.

### Investigation artifact quality

Read the Fact Sheet. Check:
- Do file:line citations resolve? (`git show origin/develop:file | sed -n 'Np'`)
- Is the impact chain complete? (upstream callers, downstream consumers)
- Are the findings mechanically verifiable or opinion?

### Knowledge propagation

For each behavior change in the diff:

```bash
# Find docs that reference the changed symbol
grep -rn "changed_function_name" **/*.md notebooks/**/*.ipynb
```

Each hit is a doc that may need updating. If the diff doesn't update
it and no follow-up ticket exists: Knowledge debt.

### Quantified claims (writing-claims:8)

For each specific count in the PR body or commit messages:

```bash
# The count must have a producing command cited
# "all 21 subpackages" -> ls -d siege_utilities/*/ | wc -l
# "15 import sites" -> grep -rn "old_path" --include="*.py" | wc -l
```

Count without command: writing-claims:8 violation.

## Boundary-value edge cases for geo

These are the geo-specific edge cases the Adversary should probe
when reviewing changes to the geo package:

| Edge case | What breaks |
|---|---|
| FIPS code "00" | Some lookups treat this as invalid; others as "all states" |
| Year before 1990 | TIGER data doesn't exist; providers should fail clearly |
| Negative longitude > -180 | Antimeridian crossing breaks naive bounding box logic |
| Empty geometry column | Spatial joins produce silent wrong results or crash |
| None in geometry column | Different engines handle this differently |
| Mixed CRS in a merge | Silent wrong results if not caught before join |
| State FIPS as int vs string | "06" vs 6 -- leading zero matters |
| Congressional district with congress_number | Must match the vintage year |
| Provider returns 0 features | Is this "no data" or "query failed"? (SU-1) |
| GeoDataFrame with no CRS set | Operations assume 4326; may be wrong |

## Supplementary references

These free/open-source references provide authoritative grounding for
specific hostile-review checks. They supplement the existing shelf rules
(`_robustness-rules.md`, `_principles-rules.md`, `_property-testing-rules.md`,
`_architecture-patterns-rules.md`, `_packaging-rules.md`, `_scipy-spec-rules.md`)
and the spatial analysis references already in the skills tree.

### Composition and architecture

| Reference | URL | What it grounds |
|---|---|---|
| Geographic Data Science with Python (Rey, Arribas-Bel, Wolf) | geographicdata.science/book | Engine-agnostic spatial analysis; PySAL composition patterns; what the library's spatial primitives should compose into |
| Architecture of Open Source Applications (Brown & Wilson) | aosabook.org | Architecture decision documentation; why systems are built the way they are -- context for Layer 2 audit |
| The Turing Way (Alan Turing Institute) | the-turing-way.netlify.app | Reproducible research; notebook reproducibility; knowledge propagation -- context for Layer 3 process audit |
| Cosmic Python (Percival & Gregory) | cosmicpython.com | Already cited in `_architecture-patterns-rules.md`; "test business logic against fakes, not mocks of the ORM" grounds writing-tests:4 |

### Spatial correctness

| Reference | URL | What it grounds |
|---|---|---|
| OGC Simple Features Access spec | ogc.org/standards/sfa | Canonical spatial predicate semantics (contains, within, intersects boundary behavior); grounds multi-engine consistency checks |
| PROJ documentation | proj.org/en/stable | CRS transformation semantics, epoch handling, datum shifts; grounds CRS assumption propagation checks |
| Shapely 2.0 migration guide | shapely.readthedocs.io/en/stable/migration.html | Silent behavior changes between Shapely 1.x and 2.0 (array interface, GEOSException hierarchy, coordinate sequences) |
| PostGIS documentation | postgis.net/docs | Authoritative reference for ST_* function semantics; supplements the postgis/references/ skill directory |

### Code robustness (already in shelf system, cross-referenced here)

| Shelf file | Source | Hostile-review application |
|---|---|---|
| `_robustness-rules.md` | Robust Python (Viafore) | SU-1 (fail fast, invariant enforcement), SU-2 (protocol-based dispatch, type safety) |
| `_principles-rules.md` | Clean Code (Martin) | SU-1 (exceptions over error codes), SU-2 (intention-revealing names) |
| `_packaging-rules.md` | PyPA Packaging Guide | SU-3 (no undeclared dependencies, entry points over scripts) |
| `_scipy-spec-rules.md` | Scientific Python SPECs | SU-3 (deprecation warnings name the replacement), SU-4a (lazy registry sync) |
| `_property-testing-rules.md` | Hypothesis docs | SU-4b (round-trip properties, no-crash invariants, oracle comparison) |
| `_architecture-patterns-rules.md` | Cosmic Python (Percival & Gregory) | SU-4b (test business logic against fakes, not mocks) |
| `_python-rules.md` | Effective Python (Slatkin, 3rd ed) | Pythonic patterns, generator discipline, descriptor protocol |
| `_data-trust-rules.md` | (internal) | Default assumption: tabular data lies -- edge case hunting mindset |
