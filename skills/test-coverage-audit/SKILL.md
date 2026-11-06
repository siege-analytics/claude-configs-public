---
name: "Test Coverage Audit"
description: "Audit error-path test coverage. Cross-references except/raise sites in source against error-path tests. Enforces writing-tests:5."
globs: ["**/*.py"]
user-invocable: false
---

# Test Coverage Audit

Audit error-path test coverage for a Python module. This skill cross-references exception-handling sites in production code against tests that exercise those paths. It enforces `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:5: every `except` block in production code must be exercised by a test that forces it to fire.

## When this skill applies

Load this skill when:
- Reviewing a module's test coverage after changes to error-handling code
- A hostile review or code review flags missing error-path tests
- Preparing a module for promotion from "happy-path tested" to "fully tested"
- A new `except` or `raise` is introduced in a PR

## Procedure

### Step 1: Inventory error sites in the source module

AST-walk the module (or manually scan it) to count every error site. An error site is one of:

1. **`except` blocks** -- each `except` clause is one site, even if the `try` has multiple handlers
2. **`raise` statements** -- each explicit `raise` is one site
3. **Error-return paths** -- `return None`, `return []`, `return pd.DataFrame()`, `return {}`, `return ""`, `return 0.0` inside a conditional or `except` block where the intent is to signal failure

Record each site as a row:

| # | File:Line | Type | Exception class / return shape | Handler behavior |
|---|-----------|------|-------------------------------|-----------------|
| 1 | `module.py:42` | except | `requests.RequestException` | logs warning, returns `None` |
| 2 | `module.py:58` | raise | `ValueError` | raised on invalid input |
| 3 | `module.py:73` | except | `KeyError` | falls back to default provider |

### Step 2: Inventory error-path tests

Find the test file(s) for the module using the mapping heuristic (Step 5 below). In each test file, count error-path tests. An error-path test is one that:

- Uses `pytest.raises(ExcClass)` or `assertRaises(ExcClass)` or `with raises(ExcClass)`
- Has a name containing `error`, `fail`, `invalid`, `missing`, `raises`, `bad`, `empty`, `none`, or `corrupt`
- Contains a monkeypatch or mock that induces a failure (e.g., `side_effect=ConnectionError`)
- Asserts on behavior after an induced failure (return value, log message, re-raised exception)

Record each test:

| # | Test file:line | Test name | What it exercises |
|---|---------------|-----------|-------------------|
| 1 | `test_module.py:15` | `test_network_failure_raises` | Forces `ConnectionError`, asserts `RuntimeError` propagated |
| 2 | `test_module.py:30` | `test_empty_input_returns_none` | Passes `None`, asserts documented `None` return |

### Step 3: Cross-reference

For each error site from Step 1, check whether at least one test from Step 2 exercises it. "Exercises it" means:

- **For `except` blocks:** a test induces the caught exception class (via monkeypatch, dependency injection, or real-but-failing input) AND asserts on the handler's behavior (return value, re-raised exception, log entry).
- **For `raise` statements:** a test triggers the condition that causes the raise AND asserts the exception type via `pytest.raises`.
- **For error-return paths:** a test triggers the error condition AND asserts the return value matches the documented error shape, proving callers can distinguish it from success.

A test that exercises only the happy path and incidentally passes through the wrapped call does NOT count. The test must name the exception class or explicitly induce the failure.

Mark each error site as:

| Status | Meaning |
|--------|---------|
| **Covered** | At least one test exercises this exact path |
| **Uncovered** | No test exercises this path |
| **Carved out** | Falls under a writing-tests:5 carve-out (see below) |

### Step 4: Report

Produce a summary table of uncovered error paths:

| File:Line | Type | Exception class | Handler behavior | Missing test |
|-----------|------|----------------|-----------------|--------------|
| `module.py:42` | except | `RequestException` | logs + returns None | Need test that monkeypatches the HTTP call to raise `RequestException`, then asserts `None` return and warning log |
| `module.py:73` | except | `KeyError` | falls back to default | Need test that passes dict missing expected key, then asserts fallback behavior |

Also report the coverage ratio: `{covered} / {total} error sites covered ({percent}%)`.

If the module has zero uncovered error sites, state that explicitly. Do not report partial coverage as "good enough."

## Source-to-test file mapping heuristic

The standard mapping for finding test files:

1. **Direct name mapping:** `siege_utilities/geo/census_geocoder.py` maps to `tests/geo/test_census_geocoder.py`
2. **Flat test directory:** if no subdirectory structure, look for `tests/test_census_geocoder.py`
3. **Module-level test file:** `tests/test_geo.py` may contain tests for multiple modules under `siege_utilities/geo/`
4. **Grep fallback:** search test files for `from siege_utilities.geo.census_geocoder import` or `import siege_utilities.geo.census_geocoder`

If no test file exists at all, that is the finding: the module has zero error-path coverage.

## What "exercising an except block" means

An `except` block is exercised when a test forces the guarded code to raise the caught exception, and the test asserts on what the handler does.

### Example: exercising a network-failure handler

Production code:
```python
def fetch_data(url):
    try:
        response = requests.get(url, timeout=30)
        return response.json()
    except requests.RequestException as e:
        logger.warning("Fetch failed for %s: %s", url, e)
        return None
```

Test that exercises the `except` block:
```python
def test_fetch_data_network_failure(monkeypatch):
    """Forces RequestException to verify the handler logs and returns None."""
    monkeypatch.setattr(
        "requests.get",
        Mock(side_effect=requests.RequestException("connection refused")),
    )
    result = fetch_data("http://example.com/api")
    assert result is None
```

### Example: exercising a raise statement

Production code:
```python
def validate_fips(code):
    if not isinstance(code, str) or len(code) not in (2, 5):
        raise ValueError(f"Invalid FIPS code: {code!r}. Must be 2 or 5 digit string.")
    return code.zfill(5)
```

Test that exercises the `raise`:
```python
def test_validate_fips_rejects_invalid_length():
    with pytest.raises(ValueError, match="Invalid FIPS code"):
        validate_fips("1234")
```

### What does NOT count

- A test that mocks the dependency to always succeed -- this only exercises the happy path
- A test that catches the exception in the test body instead of using `pytest.raises` -- this swallows the signal
- A test that calls the function with valid input and asserts it does not raise -- this is a happy-path test, not an error-path test

## Carve-outs from writing-tests:5

Two categories of `except` blocks are exempt from the coverage requirement:

1. **`finally`-cleanup code** -- `except` in best-effort cleanup (closing a file handle, removing a temp directory) where the failure is documented as ignorable. The handler must have a comment explaining why no test exists.

2. **`__del__` or signal handlers** -- `except` in `__del__` methods or signal handlers where inducing the exception in a test is unsafe or non-deterministic. The handler must have a comment explaining why no test exists.

Both carve-outs require a one-line comment in the source code naming why no test exists. Without the comment, the handler counts as untested and must be reported as uncovered.

## Cross-references

- `[`writing-tests`](../_writing-tests-rules.md)` writing-tests:5 -- the rule this skill enforces
- ``hostile-review` (planned)` -- uses this audit as input for Priority 4 (SU-4b) findings
- `[`code-review`](../code-review/SKILL.md)` -- review checklist item for `except` block coverage
