---
name: siege-utilities
description: Project definition for the siege_utilities Python package — shared geo, reporting, config, and data utilities for Siege Analytics.
repo: siege-analytics/siege_utilities
scope:
  - "siege_utilities/**"
  - "tests/**"
  - "notebooks/**"
  - "docs/**"
  - "setup.cfg"
  - "pyproject.toml"
owners:
  - dheeraj@siegeanalytics.com
---

# siege-utilities

## What it is

`siege_utilities` is the shared Python utility library for Siege Analytics. It provides geo/spatial helpers, reporting tools, config management, data connectors, and convenience wrappers used across all Siege projects.

## Strategic goal

A library other Siege projects can depend on with confidence: functions do what they say, errors are not data, contracts are stable, and notebooks demonstrate every capability.

## Scope

This project definition activates when the working directory matches the `siege-analytics/siege_utilities` repository. All project-specific rules and skills below apply only within that scope.

Project-specific rules and skills live in this directory. They take precedence over general rules within this project's scope. See the Precedence Model section in the resolver for how conflicts are handled.

## Testing

```yaml
testing:
  layers:
    - name: library
      framework: pytest
      test_dir: tests/
      pattern: "test_{stem}.py"
```

## Knowledge base

```yaml
knowledge_base:
  - url: docs/
    scope: API reference, module documentation, changelog
  - url: CLAUDE.md
    scope: architecture decisions, conventions, package structure
  - url: notebooks/
    scope: integration examples, capability demonstrations
```

## Key invariants

1. **Errors are not data.** Functions must not return valid-shaped empty results (empty DataFrame, `[]`, `0.0`, `{}`, `""`) on failure. Raise or log — never lie to the caller.
2. **Does it do what it says?** If a function claims universality (any CRS, any geometry type, any database), it must handle the full domain or document the restriction.
3. **No demo exemptions.** Example and demo code ships with the package. Users copy patterns from it. It is held to the same standard as library code.
4. **Notebooks are the integration surface.** The `notebooks/` directory demonstrates library capabilities. Contract changes must propagate into affected notebooks.
