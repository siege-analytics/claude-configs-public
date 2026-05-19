---
name: python-exceptions
description: "Exception handling discipline for Python. TRIGGER: writing try/except, seeing `except Exception: pass`, reviewing error paths, or a CR comment about silent failures. Decides when to catch, translate, re-raise, or let fly."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py"
---

# Python Exception Handling

## Companion shelves

For the *why* behind exception discipline (don't swallow, narrow except, fail loud), load:
- [`shelves/engineering-principles/clean-code/references/error-handling.md`](../../shelves/engineering-principles/clean-code/references/error-handling.md)

The rules below stay Python-specific (operational guidance for our codebase).

Apply these rules whenever a `try`/`except` is on screen. See [reference.md](reference.md) for custom exception hierarchy patterns, context managers, and batch-failure strategies.

## The one rule

**Every `except` block does exactly one of:**
1. Handle the failure and return a meaningful domain value.
2. Log and re-raise (`raise` or `raise NewError(...) from e`).
3. Translate to a more useful exception type (`raise DomainError(...) from e`).

Silently swallowing an exception — returning `None`, `{}`, `""`, or an error-string — is never option 4. Callers who get back a pretend-valid value debug the wrong problem.

## Decision tree

```
START: I need to wrap risky code in try/except
  │
  ├─ What specific exception can this code raise?
  │   ├─ I don't know → narrow the try block first; if still unclear, don't catch
  │   └─ I do know → list them explicitly, narrowest first
  │
  ├─ Can I actually recover?
  │   ├─ YES (e.g., fall back to cache, retry, use a default) → handle + log at INFO/WARN
  │   └─ NO → log + re-raise with context (raise ... from e)
  │
  ├─ Is this at a system boundary? (CLI entry, HTTP handler, job runner)
  │   ├─ YES → a broad except Exception that logs and returns a structured error is OK
  │   └─ NO → stay narrow
  │
  └─ Am I wrapping for a caller who shouldn't know about the underlying library?
      └─ Translate: raise MyDomainError(...) from e
```

## Catch table

| Catching | When it's right | When it's wrong |
|---|---|---|
| `except SpecificError` (e.g., `KeyError`, `ValueError`, `requests.Timeout`) | Default choice — name what you expect | Never — if nothing matches, nothing is caught |
| `except (ErrA, ErrB)` tuple | Multiple known failure modes, same handling | Mixing unrelated errors into one branch |
| `except Exception` | Boundary handler (CLI/HTTP/job) that must log and not crash the process | Library code masquerading as convenience |
| `except BaseException` | Almost never — catches `KeyboardInterrupt`, `SystemExit` | Anywhere outside explicit signal handlers |
| `except:` (bare) | Never in production code | Always |

## Anti-patterns

| Smell | Why bad | Fix |
|---|---|---|
| `except Exception: return {}` | Caller can't distinguish success-empty from failure | Raise; document the exception |
| `except Exception: return f"failed: {e}"` | String return type leaks failure into success channel | Raise `DomainError` from `e` |
| `except Exception: return None` (in library) | Ambiguous — `None` might be a valid result | Raise; reserve `None` for documented "not found" |
| `except Exception: pass` | Hides everything, including bugs you haven't discovered | Catch specific; if you really need silence, comment WHY |
| `except Exception as e: raise Exception(str(e))` | Destroys type; `from` clause missing | `raise` alone, or `raise New(...) from e` |
| `raise Exception("bad")` | No type to catch on | Use specific / custom class |
| `try: long block` with one risky line | Hides which call can fail | Scope try to the risky line |

## Chaining

Always preserve the original cause when translating:

```python
except requests.RequestException as e:
    raise BoundaryFetchError(f"failed to fetch {url}") from e
```

- `from e` → sets `__cause__`, shows full traceback chain.
- `from None` → intentionally hides the cause (rare; use only when the inner error is internal noise).
- Bare `raise NewError(...)` → `__context__` is set but `__cause__` is not; most tools treat it as implicit chaining, but being explicit with `from` is better.

## Custom exception classes

Define domain exceptions early, subclass the closest stdlib type:

```python
class BoundaryFetchError(RuntimeError):
    """Raised when boundary download fails after retries."""

class BoundaryInputError(ValueError):
    """Raised when required boundary parameters are missing or inconsistent."""
```

Why:
- Callers can write `except BoundaryFetchError` without importing deep internals.
- Subclassing stdlib means `except ValueError` still catches your input errors.
- One class per failure category, not per call site.

## Logging pattern

Use the project's logger (not `print`). Include the input context so the log alone is enough to reproduce:

```python
except (ValueError, KeyError) as e:
    log_error(f"polling summary failed (metric={metric!r}, keys={list(data)}): {e}")
    raise PollingAnalysisError(f"polling summary failed for metric={metric!r}") from e
```

Rules:
- Don't log and re-raise twice (once is enough; the traceback carries the rest).
- At system boundaries, use `logger.exception()` to capture the traceback automatically.
- Never log secrets/PII — names, addresses, tokens don't belong in error messages.

## Boundary handlers

At the edges of the system (CLI entry, web handler, job runner, thread pool worker), a broad catch that logs and returns a structured error is legitimate:

```python
def main(argv):
    try:
        return run(argv)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        logger.exception("unhandled")
        sys.exit(1)
```

This is the exception (pun intended) to the "never `except Exception`" rule. Document each such handler with a comment explaining it's a boundary.

## Gotchas

- `NotImplementedError` is not a placeholder — callers catching `Exception` will skip it. Use `raise NotImplementedError(...)` only when a caller should know to fall back.
- `OSError` is a union of `FileNotFoundError`, `PermissionError`, `ConnectionError`, and a dozen others. Catch it when you genuinely mean "any filesystem or I/O failure"; otherwise narrow.
- `asyncio.CancelledError` inherits from `BaseException` in 3.8+. Never swallow it in async code.
- `pandas.errors.*` are the right catches for DataFrame operations, not generic `Exception`.
- In test code, use `pytest.raises(DomainError)` to pin the expected type — `pytest.raises(Exception)` passes on any error and misses regressions.

## When CodeRabbit flags this

CR typically flags three patterns:
1. `except Exception: return <sentinel>` — "silent swallow." Fix: raise or translate.
2. `except Exception: pass` — "bare swallow." Fix: narrow OR document why silence is correct.
3. `raise Exception(...)` — "vanilla raise." Fix: specific / domain class.

All three are 5–10 line edits. Resolve with a commit, not a reply.

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
