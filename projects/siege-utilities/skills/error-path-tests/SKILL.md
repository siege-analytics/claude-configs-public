---
name: "Error Path Test Generator (siege-utilities)"
description: "Generate error-path tests for siege_utilities modules. Enforces SU-4b."
globs: ["siege_utilities/**/*.py", "tests/**/*.py"]
---

# Error Path Test Generator — siege-utilities

Generate error-path tests for modules in the `siege_utilities` package. This skill produces tests that exercise `except` blocks, `raise` statements, and error-return paths, enforcing rule SU-4b from the project's error-handling philosophy.

## When to use

- After a hostile review flags missing error-path tests (SU-4b violation)
- When adding new `except` or `raise` statements to a module
- When backfilling error-path coverage for an existing module
- When the CI coverage check (`scripts/check_error_path_coverage.py`) reports gaps

## Background

Round 7 hostile review (2026-05-28) found 10 real bugs that survived 6 prior review rounds because 90% of the 380-test suite only exercised happy paths. The bugs lived in error paths that no test ever reached. This skill codifies the 8 test patterns identified during that round to prevent recurrence.

## Test file naming convention

siege-utilities test files follow this layout:

```
tests/
├── geo/
│   ├── test_census_geocoder.py      # tests for siege_utilities/geo/census_geocoder.py
│   ├── test_codification.py         # tests for siege_utilities/geo/codification.py
│   └── overlays/
│       └── test_seats.py            # tests for siege_utilities/geo/overlays/seats.py
├── test_cache.py                    # tests for siege_utilities/cache.py
└── ...
```

Mapping rule: replace `siege_utilities/` with `tests/` and prepend `test_` to the filename. Preserve the subdirectory structure. If the test file does not exist, create it with the standard imports:

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
```

Error-path test names must contain one of: `error`, `fail`, `invalid`, `missing`, `raises`, `bad`, `empty`, `none`, or `corrupt`. This is required for the mechanical detection heuristic in SU-4b.

## The 8 error-path test patterns

These patterns were identified from round 7 and cover the recurring failure shapes in siege-utilities modules.

### Pattern 1: provider=None raises RuntimeError

Many siege-utilities modules accept a provider/client dependency. When the provider is `None` (not configured, not injected), the module must fail loudly rather than producing empty results.

```python
def test_geocode_provider_none_raises():
    """Provider=None must raise, not return empty results (SU-1)."""
    with pytest.raises(RuntimeError, match="[Pp]rovider.*not configured"):
        geocode_address("123 Main St", provider=None)
```

### Pattern 2: provider raises propagates or wraps

When the underlying provider raises an exception, the module must either propagate it or wrap it in a documented exception type. It must not swallow the error and return empty data.

```python
def test_geocode_provider_error_propagates(monkeypatch):
    """Transport errors from the provider must not be swallowed (SU-1)."""
    mock_provider = Mock()
    mock_provider.geocode.side_effect = ConnectionError("timeout")
    with pytest.raises((ConnectionError, RuntimeError)):
        geocode_address("123 Main St", provider=mock_provider)
```

### Pattern 3: provider returns unexpected shape is handled

When the provider returns data in an unexpected shape (wrong keys, wrong types, truncated response), the module must detect and report the problem rather than producing silently wrong results.

```python
def test_geocode_bad_provider_response(monkeypatch):
    """Malformed provider response must not produce silent wrong results."""
    mock_provider = Mock()
    mock_provider.geocode.return_value = {"unexpected": "shape"}
    with pytest.raises((KeyError, ValueError, RuntimeError)):
        geocode_address("123 Main St", provider=mock_provider)
```

### Pattern 4: empty input has documented behavior

Empty lists, empty strings, `None` arguments, and zero-row DataFrames must produce documented behavior: either a clear exception or a documented empty result that callers can distinguish from "query succeeded but found nothing."

```python
def test_geocode_empty_string_raises():
    """Empty address string must raise, not return a fake result."""
    with pytest.raises(ValueError, match="[Aa]ddress.*empty"):
        geocode_address("")

def test_overlay_empty_dataframe():
    """Empty input DataFrame must return empty DataFrame, not raise."""
    result = compute_overlay(gpd.GeoDataFrame())
    assert isinstance(result, gpd.GeoDataFrame)
    assert len(result) == 0
```

### Pattern 5: missing credentials raises ValueError

Modules that require API keys, database credentials, or authentication tokens must raise a clear `ValueError` when credentials are absent, not silently fall back to unauthenticated access or return empty results.

```python
def test_census_api_missing_key_raises(monkeypatch):
    """Missing API key must raise ValueError with install instructions."""
    monkeypatch.delenv("CENSUS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CENSUS_API_KEY"):
        fetch_census_data("B01001_001E", state="06")
```

### Pattern 6: network failure raises ConnectionError

HTTP clients and API wrappers must propagate network failures as `ConnectionError` (or a documented wrapper). They must not catch `requests.RequestException` and return empty data.

```python
def test_fetch_network_failure_propagates(monkeypatch):
    """Network failure must raise, not return empty DataFrame (SU-1)."""
    monkeypatch.setattr(
        "requests.get",
        Mock(side_effect=requests.ConnectionError("DNS resolution failed")),
    )
    with pytest.raises((ConnectionError, requests.ConnectionError)):
        fetch_boundary_data(state_fips="06")
```

### Pattern 7: invalid identifiers raise ValueError

Bad table IDs, bad variable codes, malformed FIPS codes, and invalid GEOID values must raise `ValueError` with a message naming the bad input. They must not silently return empty results or fall through to a network call that will fail with an opaque error.

```python
def test_bad_table_id_raises():
    """Invalid Census table ID must raise ValueError, not hit the API."""
    with pytest.raises(ValueError, match="INVALID_TABLE"):
        fetch_census_data("INVALID_TABLE", state="06")

def test_bad_fips_code_raises():
    """FIPS code with wrong length must raise ValueError."""
    with pytest.raises(ValueError, match="[Ii]nvalid FIPS"):
        lookup_county("1234")  # not 2 or 5 digits
```

### Pattern 8: boundary conditions

Date before all plans, zero totals, negative values, single-element inputs, and other boundary conditions must produce correct results or documented exceptions. These are the bugs that survive happy-path testing because the happy path never hits the boundary.

```python
def test_apportionment_zero_total():
    """Zero total population must not cause ZeroDivisionError."""
    with pytest.raises(ValueError, match="[Tt]otal.*zero"):
        apportion_seats(populations={"A": 0, "B": 0}, seats=5)

def test_date_before_all_plans():
    """Date before any redistricting plan must raise, not return stale plan."""
    with pytest.raises(ValueError, match="[Nn]o plan"):
        get_plan_for_date(date(1700, 1, 1))

def test_single_element_list():
    """Single-element input must work, not assume len >= 2."""
    result = compute_ranking([42.0])
    assert result == [1]
```

## Procedure for generating tests

### Step 1: Audit the module

Run the `[skill:test-coverage-audit]` procedure to inventory error sites and identify uncovered paths. This gives you the list of `except` blocks, `raise` statements, and error-return paths that need tests.

### Step 2: Classify each uncovered path

For each uncovered error site, determine which of the 8 patterns above applies. Most error sites map to exactly one pattern. If a site does not fit any pattern, write a custom test that induces the specific exception and asserts on the handler's behavior.

### Step 3: Write the tests

For each uncovered path, write a test following the matching pattern. Every test must:

1. **Import the module under test** — `from siege_utilities.geo.module import function_name`. A test that reimplements the logic is theater (writing-tests:1).
2. **Induce the failure** — via monkeypatch, dependency injection, or real-but-failing input. Do not rely on mocking the function itself.
3. **Assert on the handler's behavior** — use `pytest.raises` for exceptions, direct assertion for return values, or log capture for logged errors.
4. **Name the exception class** — `pytest.raises(ValueError)`, not just `pytest.raises(Exception)`.
5. **Have a descriptive name** — containing one of: `error`, `fail`, `invalid`, `missing`, `raises`, `bad`, `empty`, `none`, or `corrupt`.
6. **Have a docstring** — one line explaining what production behavior the test verifies and which rule it enforces.

### Step 4: Verify

Run the tests:

```bash
pytest tests/path/to/test_module.py -v
```

Then re-run the coverage audit to confirm all error sites are now covered.

### Step 5: Check against CI

The CI script `scripts/check_error_path_coverage.py` performs the mechanical check described in SU-4b: for a module with M `except`/`raise` sites, at least M tests must have error-path keywords in their names. Run it locally before pushing:

```bash
python scripts/check_error_path_coverage.py siege_utilities/geo/module.py
```

## Concrete example: transforming an except block into a test

### Production code (siege_utilities/geo/rdh_catalog.py:87)

```python
def fetch_plan(state_fips, plan_type="sldl"):
    url = f"{RDH_BASE_URL}/plans/{state_fips}/{plan_type}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("RDH fetch failed for %s/%s: %s", state_fips, plan_type, e)
        return pd.DataFrame()  # SU-1 violation: error disguised as empty data
```

### The bug

The `except` block returns `pd.DataFrame()` on network failure. The caller cannot distinguish "no plans exist for this state" from "the network request failed." This is an SU-1 violation.

### The fix (production code)

```python
def fetch_plan(state_fips, plan_type="sldl"):
    url = f"{RDH_BASE_URL}/plans/{state_fips}/{plan_type}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise RuntimeError(
            f"RDH fetch failed for {state_fips}/{plan_type}: {e}"
        ) from e
```

### The test (tests/geo/test_rdh_catalog.py)

```python
def test_fetch_plan_network_failure_raises(monkeypatch):
    """Network failure must raise RuntimeError, not return empty DataFrame (SU-1)."""
    monkeypatch.setattr(
        "siege_utilities.geo.rdh_catalog.requests.get",
        Mock(side_effect=requests.ConnectionError("DNS failed")),
    )
    with pytest.raises(RuntimeError, match="RDH fetch failed"):
        fetch_plan("06", "sldl")
```

The test induces the exact exception class (`ConnectionError`, a subclass of `RequestException`) that the handler catches, then asserts the handler now raises `RuntimeError` instead of returning empty data.

## Cross-references

- `[skill:test-coverage-audit]` — the audit procedure this skill builds on
- `[rule:writing-tests]` writing-tests:5 — the general rule requiring every `except` block to be tested
- `[skill:hostile-review]` — Priority 4 (SU-4b) uses this skill's output
- Project rule SU-4b in `_rules.md` — the project-specific error-path coverage requirement
- Project rule SU-1 in `_rules.md` — errors are not data; the principle that motivates most of these tests
