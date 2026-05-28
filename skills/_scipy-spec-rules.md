---
description: Always-on standards from Scientific Python SPECs 0, 4, and 6. Apply when managing dependency versions, deprecation timelines, or lazy-loading conventions.
---

# Scientific Python SPEC Standards

Apply these standards from the [Scientific Python SPECs](https://scientific-python.org/specs/) to dependency management and API lifecycle.

## SPEC 0: Minimum supported versions

- Support the two most recent minor versions of core dependencies (NumPy, pandas, Python itself). Drop support for older versions on a rolling 24-month window.
- Pin minimum versions in `pyproject.toml`, not maximum versions. Upper bounds cause resolver conflicts across the ecosystem.
- When a minimum version bump is required, document the reason (new API used, security fix, upstream deprecation) in the changelog.

## SPEC 4: Deprecation and removal

- Deprecations last at least two minor releases before removal. A function deprecated in 0.8.0 can be removed no earlier than 0.10.0.
- Use `warnings.warn(..., DeprecationWarning, stacklevel=2)` so the warning points to the caller, not the deprecated function itself.
- Deprecation warnings must name the replacement: "Use `fetch_geographic_boundaries` instead of `get_census_boundaries`." A warning that says only "deprecated" is not actionable.
- Never remove a public symbol without a deprecation period. If it was in `__all__` or `_LAZY_IMPORTS`, it had users.

## SPEC 6: Lazy loading

- Top-level `__init__.py` should not eagerly import submodules with heavy dependencies. Use `__getattr__` with `_LAZY_IMPORTS` to defer until first access.
- Lazy loading must be transparent: `from package import symbol` works the same whether the import is eager or lazy. The registry must stay in sync with the actual module paths.
- Test the lazy registry (e.g., `scripts/check_lazy_imports.py`) in CI. A stale registry entry that maps to a renamed or removed module is a broken public API.

## Version support matrix

- Maintain a tested version matrix in CI for Python version x {min supported dependencies, current dependencies}. Testing only against latest hides compatibility breaks.
- When dropping a Python or dependency version, update `pyproject.toml` `requires-python` and dependency lower bounds in the same commit.


---

## Attribution

Principles distilled from [Scientific Python SPECs](https://scientific-python.org/specs/) 0, 4, and 6. SPECs are community standards, not copyrighted text.
