---
description: Always-on packaging standards from the PyPA Packaging Guide. Apply when modifying pyproject.toml, managing dependencies, or publishing packages.
---

# PyPA Packaging Standards

Apply these standards from the [PyPA Packaging Guide](https://packaging.python.org/) to package configuration and distribution.

## pyproject.toml as single source of truth

- All package metadata belongs in `pyproject.toml`, not `setup.py` or `setup.cfg`. If `setup.py` exists, it should be a shim that calls `setuptools.setup()` with no arguments.
- Use `[project]` table for metadata (name, version, description, dependencies). Use `[tool.*]` tables for tool-specific configuration (pytest, ruff, mypy, bandit).
- Never duplicate metadata between `pyproject.toml` and `__init__.py`. Use dynamic version discovery (`[project] dynamic = ["version"]`) if the version lives in code.

## Dependency specification

- Declare runtime dependencies in `[project] dependencies`. Use `>=` lower bounds, not `==` pins. Exact pins belong in lock files, not in package metadata.
- Group optional dependencies by use case: `[project.optional-dependencies] geo = [...]`, `dev = [...]`, `test = [...]`. Do not put test dependencies in runtime dependencies.
- Avoid undeclared dependencies. If a module imports `requests`, `requests` must appear in `dependencies` or an `optional-dependencies` group. Silent reliance on transitive dependencies breaks when the intermediary drops the dep.

## Entry points and scripts

- Use `[project.scripts]` for CLI entry points, not `bin/` scripts or `__main__.py` hacks.
- Use `[project.entry-points]` for plugin registration. Plugins should be discoverable without importing the plugin package.

## Build system

- Declare the build backend in `[build-system]`. For pure-Python packages, `setuptools` with `build-meta` or `hatchling` are standard choices.
- Do not commit build artifacts (`dist/`, `*.egg-info/`, `build/`). Add them to `.gitignore`.
- Use `python -m build` to produce sdist and wheel. Do not invoke `setup.py` directly.

## Version management

- Use a single version source. Either `pyproject.toml` `[project] version = "X.Y.Z"` or dynamic discovery from a `__version__` attribute.
- Follow semantic versioning: breaking changes bump major, new features bump minor, bug fixes bump patch. For pre-1.0 packages, minor bumps may contain breaking changes but must be documented.


---

## Attribution

Principles distilled from the [Python Packaging User Guide](https://packaging.python.org/). The guide is maintained by the Python Packaging Authority (PyPA) and is public domain.
