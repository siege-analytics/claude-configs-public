---
name: hostile-review
description: "Full-codebase adversarial audit across 9 attack categories. Unlike code-review (which reviews a diff against a ticket), hostile-review scans the ENTIRE codebase for latent defects using mechanical grep patterns + domain reasoning. Produces a findings report with file:line citations and severity ratings. Use when inheriting a codebase, after major refactors, or on a cadence (quarterly). Each category has a defined scan methodology so reviews are repeatable and comparable across rounds."
allowed-tools: Read Grep Glob
---

# Hostile Review

A hostile review is a full-codebase adversarial audit. It assumes the code
is guilty until proven innocent. Unlike code-review (which reviews a diff
against a ticket's intent), hostile-review scans the ENTIRE codebase for
latent defects using mechanical grep patterns followed by contextual
reasoning.

Hostile reviews are normally performed by a fresh agent session, not by the
author in the same session and not by a human reviewer. Human hostile reviews
are exceptional override cases; record why an agent review was unavailable if a
human review is used. The author agent and reviewer agent must coordinate on
findings and come to consensus on fixes before the work is considered reviewed.
The reviewer is not done when it posts findings, and the author is not done when
it patches code. The hostile-review task is complete only after the agreed fixes
are deployed to the production target and production UAT evidence is recorded,
or after the review artifact records that production UAT is not applicable with
a falsifiable reason.

## When to Use

- Inheriting a codebase (first week)
- After a major refactor or sweep (verify completeness)
- Quarterly cadence (prevent drift)
- Before a release with security or correctness implications
- When the question is "what's wrong?" not "is this PR okay?"

## Severity Scale

| Level | Meaning | Threshold |
|-------|---------|-----------|
| **S1** | Exploitable in production OR silently wrong answers on normal input | Must fix before next release |
| **S2** | Silent data issues in edge cases, resource leaks under load, missing validation at boundaries | Should fix; file ticket |
| **S3** | Design debt, defense-in-depth gaps, impedance mismatches | Track; fix opportunistically |

## Attack Categories

Nine categories, each with a defined grep-based scan methodology. Run all
categories; report findings per category with file:line citations.

---

### Category 1: Engineering Discipline (SU-1 / SU-2 / SU-3)

The foundation. Three rules that ensure code is honest about its behavior.

**SU-1: Errors are not data.**
Functions must not return valid-shaped empty results on failure.

```bash
# Scan: except blocks that return empty containers
git grep -n "except.*:" -- "*.py" | xargs grep -l "return \[\]\|return {}\|return None\|return 0\|return \"\""
# Confirm: is the return inside an except block? Does the caller distinguish it from success?
```

**SU-2: Does it do what it says?**
Type hints, docstrings, and function names must match implementation.

```bash
# Scan: functions with Optional return type that never return None (or vice versa)
git grep -n "-> Optional\[" -- "*.py"
# Confirm: does the function actually have a None-return path?

# Scan: parameters accepted but never used
git grep -n "def.*kwargs" -- "*.py"
# Confirm: is **kwargs forwarded or silently dropped?
```

**SU-3: No demo exemptions.**
Code under examples/ and notebooks/ ships with the package.

```bash
# Scan: bare except, hardcoded paths, silent returns in examples
git grep -rn "except:" -- "examples/" "notebooks/"
git grep -rn "Users/\|C:\\\\" -- "examples/" "notebooks/"
```

**External-binary dependency audit.**
Scripts and hooks that call external binaries must verify presence or fail loudly.

```bash
# Scan: external binary invocations in hooks and scripts
git grep -rn 'which \|command -v \|$(.*)\|`.*`' -- "*.sh"
# Scan: optional imports with silent fallback
git grep -rn "except ImportError" -- "*.py" | grep -i "pass\|None\|return"
# Confirm: is every external binary either (a) guaranteed-present (bash, git, python3)
# or (b) guarded with a loud error on absence? Silent skip = S2.
# Ref: #280 (14 jq calls silently failing), #286
```

---

### Category 2: Security

Could this code be exploited or leak sensitive data?

**Command injection:**
```bash
git grep -n "subprocess\.\|os\.system\|os\.popen" -- "*.py"
# Flag: shell=True with string interpolation, user input in command args
```

**SQL injection:**
```bash
git grep -n 'f".*SELECT\|f".*INSERT\|f".*UPDATE\|f".*DELETE\|\.format(.*SELECT' -- "*.py"
# Flag: user-controlled values interpolated without parameterization or validation
# Safe: parameterized queries (%s, ?), validated identifiers via allowlist
```

**Path traversal:**
```bash
git grep -n "os\.path\.join\|Path(" -- "*.py" | grep -i "user\|input\|param\|arg\|request"
# Flag: user input in file paths without validation that result stays within target dir
# Critical: ZipFile.extract() without path validation (zip slip)
```

**Credential leakage:**
```bash
git grep -n "password\|secret\|token\|api_key\|credential" -- "*.py" | grep -i "log\|print\|format"
# Flag: secrets appearing in log output, tracebacks, or serialized objects
```

**SSRF:**
```bash
git grep -n "requests\.get\|requests\.post\|urlopen\|httpx" -- "*.py"
# Flag: URL constructed from user input without allowlist validation
```

**Insecure deserialization:**
```bash
git grep -n "pickle\.load\|yaml\.load\|eval(\|exec(" -- "*.py"
# Flag: any of these on data from external sources
# Safe: pickle.load on self-written data, yaml.safe_load, ast.literal_eval
```

---

### Category 3: Domain Correctness

Does the code produce correct answers in its problem domain? These are
SILENTLY WRONG ANSWERS -- the worst bug class because no error is raised.

**CRS agreement (geospatial):**
```bash
git grep -n "\.intersection(\|\.union(\|\.contains(\|\.distance(\|sjoin(\|gpd\.overlay(" -- "*.py"
# Flag: geometry operations without CRS alignment check before the operation
# The two inputs MUST have the same CRS or the result is nonsense
```

**Unprojected calculations (geospatial):**
```bash
git grep -n "\.area\|\.length\|\.distance(" -- "*.py"
# Flag: area/length/distance on EPSG:4326 (WGS84) geometries
# These return degrees or degrees-squared, not meters -- meaningless for measurement
# Safe: explicit reprojection to equal-area CRS before calculation
```

**Timezone confusion (temporal):**
```bash
git grep -n "datetime\.now()\|datetime\.utcnow()" -- "*.py"
# Flag: now() without tz= parameter (naive local time)
# Flag: utcnow() (deprecated, returns naive UTC)
# Any system with temporal semantics (effective dates, event ordering) needs aware datetimes
```

**Impossible model states (domain models):**
```bash
git grep -n "null=True\|blank=True\|Optional\[" -- "*.py" | grep -i "model\|field"
# Flag: nullable fields where NULL is semantically impossible
# Check: does the schema enforce domain invariants or allow nonsense states?
# Example: a congressional district without a state, overlapping effective dates
```

**Coordinate order confusion (geospatial):**
```bash
git grep -n "Point(\|POINT(" -- "*.py"
# Verify: consistent (lon, lat) ordering per GeoJSON standard
# Shapely Point(x, y) = Point(lon, lat) -- confirm all call sites agree
```

---

### Category 4: Data Integrity

Will this code silently lose, corrupt, or duplicate data?

**Non-atomic writes:**
```bash
git grep -n "\.to_csv(\|\.to_parquet(\|\.to_file(\|open(.*'w'" -- "*.py"
# Flag: direct write to final destination without tmp-file + os.replace()
# If process dies mid-write, file is corrupted. Atomic pattern:
#   write to tmp -> os.replace(tmp, final) (atomic on same filesystem)
```

**Silent row loss:**
```bash
git grep -n "dropna(\|drop_duplicates(" -- "*.py"
# Flag: dropping rows without logging count before/after
# The user must know data was lost and how much
```

**Cartesian join bombs:**
```bash
git grep -n "\.merge(\|\.join(" -- "*.py" | grep -v "validate="
# Flag: merge/join without validate='one_to_one' or 'many_to_one'
# If keys aren't unique, silent row explosion (N*M instead of max(N,M))
```

**Partial write without rollback (databases):**
```bash
git grep -n "cursor\.execute\|session\.add\|bulk_create" -- "*.py"
# Flag: multiple mutations without explicit transaction boundary
# If step 2 fails after step 1 commits, you get inconsistent state
```

**Unbounded accumulation:**
```bash
git grep -n "\.append(\|\.extend(" -- "*.py" | grep -i "for\|while\|loop"
# Flag: growing lists inside loops without size bounds
# Also: pd.concat inside loops (quadratic copy behavior)
```

---

### Category 5: Resource Management

Will this code leak resources under sustained use?

**Unclosed file handles:**
```bash
git grep -n "open(" -- "*.py" | grep -v "with "
# Flag: open() not in a with statement or without explicit close in finally
```

**Unclosed connections/sessions:**
```bash
git grep -n "requests\.Session()\|\.connect(\|create_engine(" -- "*.py"
# Flag: connection created in __init__ without __del__ or mandatory context manager
# Pattern that leaks: convenience functions that instantiate, use, discard
```

**Missing timeouts:**
```bash
git grep -n "requests\.get\|requests\.post\|urlopen" -- "*.py" | grep -v "timeout"
# Flag: network calls without timeout= parameter
# Without timeout, a hung server blocks the caller forever
```

**Unbounded downloads:**
```bash
git grep -n "requests\.get\|urlopen" -- "*.py" | grep -v "stream=True"
# Flag: HTTP GET without streaming + size limit
# A malicious or broken server can stream data until OOM
```

**Module-level caches without eviction:**
```bash
git grep -n "_cache\s*=\s*{}\|_registry\s*=\s*{}" -- "*.py"
# Flag: module-level dicts that grow without bounds or TTL
# Long-running processes accumulate until OOM
```

---

### Category 6: Packaging Truth

Does what's declared match what's needed at runtime?

**Undeclared imports:**
```bash
# Extract all third-party imports, cross-reference against declared dependencies
git grep -n "^import \|^from " -- "*.py" | grep -v "siege_utilities\|test_\|conftest"
# Compare against: setup.py install_requires + extras_require (or pyproject.toml)
# Flag: package imported but not in any dependency group
```

**Wrong extras group:**
```bash
# For each extras group (e.g., [geo], [analytics]), verify imports only happen
# in modules that belong to that group
# Flag: geo dependency imported in analytics/ code (would fail without [geo] extra)
```

**Lazy-loading correctness:**
```bash
git grep -n "__getattr__" -- "*/__init__.py"
# Verify: deferred names actually exist in the target module
# Verify: no import-time side effects in __init__.py files
# Flag: __getattr__ that catches ImportError and returns a stub (violates SU-1)
```

**Phantom __all__ exports:**
```bash
git grep -n "__all__" -- "*.py"
# For each __all__ declaration, verify every name exists in the module
# Flag: names in __all__ that don't exist (NameError on from X import *)
```

---

### Category 7: Composability

Can the pieces of the library actually be connected without manual glue?

**Return type consistency across providers:**
```bash
# For each abstract interface (Provider, Connector, etc.):
git grep -n "class.*Provider\|class.*Connector\|class.*Client" -- "*.py"
# Verify: all implementations return the same shape (same columns, same CRS, same types)
# Flag: provider A returns GeoDataFrame, provider B returns None, provider C returns dict
```

**Column name conventions:**
```bash
git grep -n "geoid\|GEOID\|geo_id\|GEO_ID\|fips\|FIPS" -- "*.py"
# Flag: inconsistent naming for the same concept across modules
# If a utility function like find_geoid_column() exists, that proves the naming is broken
```

**Type seam mismatches:**
```bash
# Trace the canonical composition chain: does output of stage N match input of stage N+1?
# Flag: stage N returns dataclass but stage N+1 expects DataFrame
# Flag: stage N returns Optional[X] but stage N+1 doesn't null-check
# Flag: stage N uses column name "tract_geoid" but stage N+1 expects "geoid"
```

**Import discoverability:**
```bash
# Check top-level __init__.py exports
git grep -n "_LAZY_IMPORTS\|__all__" -- "*/__init__.py"
# Flag: key public functions that require deep import paths (not exported at package level)
```

---

### Category 8: Performance at Scale

Will this code degrade at production data volumes?

**N+1 query patterns:**
```bash
git grep -n "for.*in.*:" -- "*.py" | xargs grep -l "\.query\|\.execute\|\.get("
# Flag: database/API call inside a loop body
# Should be: batch query with IN clause or bulk operation
```

**Quadratic operations:**
```bash
git grep -n "\.iterrows(\|\.itertuples(" -- "*.py"
# Flag: row-by-row iteration on DataFrames (quadratic with vectorized alternative)
# Count total instances to size the remediation effort
```

**Collect-to-driver anti-pattern (Spark):**
```bash
git grep -n "\.collect(\|\.toPandas(" -- "*.py"
# Flag: collecting large distributed datasets to a single machine
# Safe: small lookup tables, pre-filtered results with known bounds
```

---

### Category 9: Test Adequacy

Do the tests actually catch the bugs the code could have?

**Exception paths untested:**
```bash
git grep -n "except.*:" -- "*.py" | grep -v "test_"
# Cross-reference: for each except block, does a test exercise it?
# Flag: except blocks with no corresponding pytest.raises() in tests
```

**Mocks hiding real behavior:**
```bash
git grep -n "@mock\|@patch\|Mock()\|MagicMock(" -- "test_*.py" "tests/"
# Flag: mocking the thing being tested (tests pass but code is broken)
# Flag: mock return values that don't match real API shapes
```

**Missing boundary tests:**
```bash
# For each public function, check if tests cover:
# - Empty input
# - Single element
# - Null/None input
# - Maximum expected input size
# Flag: functions with only "happy path" tests
```

---

## Methodology

### Execution Order

1. **Pin the commit.** All findings must cite a specific commit hash.
2. **Run mechanical scans.** Grep patterns first; they produce the candidate list.
3. **Read context.** For each grep hit, read surrounding code to confirm/dismiss.
4. **Rate severity.** S1/S2/S3 based on the scale above.
5. **Cluster findings.** Group by root cause, not by file. A class of bug is one finding with N instances.
6. **Report.** File:line, severity, what's wrong, what wrong answer/failure it produces.

### Output Format

```markdown
## Hostile Review Round N -- Findings

**Pinned to:** <branch> @ <commit>
**Reviewed:** <date>
**Total findings:** N across M categories

### Category K: <name> (N findings)

| # | Severity | File | Line | Finding |
|---|----------|------|------|---------|
| K-1 | S1 | path/to/file.py | 42 | One-line description |

#### K-1: <detailed title>

**File:** `path/to/file.py:42`
**Code:** (relevant snippet)
**Problem:** What's wrong and what failure/wrong answer it produces
**Remediation:** What the fix looks like (not the fix itself)
```

### Post-Review Actions

1. **Post findings to a ticket** (file one if none exists)
2. **File remediation tickets** per finding cluster (not per instance)
3. **Update the codebase's rules** if a new recurring pattern was found
4. **Compare to prior round** -- what's fixed, what's new, what regressed?

## Relationship to code-review

| Dimension | hostile-review | code-review |
|-----------|---------------|-------------|
| Scope | Entire codebase | One PR/diff |
| Trigger | Cadence or event | Every PR |
| Assumption | Code is guilty | Code is good-faith |
| Output | Findings report + tickets | Review comments |
| Methodology | Grep patterns + reasoning | Read diff + ticket intent |

Use hostile-review to find latent defects. Use code-review to prevent new ones.

## Attribution Policy

NEVER include AI or agent attribution in review reports, tickets, or remediation commits.
