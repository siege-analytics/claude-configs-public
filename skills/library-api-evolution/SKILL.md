---
name: library-api-evolution
description: "Changing public APIs without breaking users. TRIGGER: renaming a public function, changing a default, altering a return type, dropping a column, bumping a version. Decides which path of deprecation vs. break is safe."
user-invocable: false
paths: "src/**/*.py,siege_utilities/**/*.py,pyproject.toml,setup.cfg,CHANGELOG.md"
---

# Python Library API Evolution

Apply whenever changing anything a consumer could import, call, or depend on. See [reference.md](reference.md) for deprecation-warning templates, SemVer/CalVer comparison, and BC-break audit scripts.

## Step 1: What counts as "public"?

| Is it… | Public? |
|---|---|
| A function/class/method not prefixed `_` | **YES** |
| Exposed in `__all__` of a package `__init__.py` | **YES** |
| Documented in the library's README, Sphinx docs, or usage examples | **YES** |
| A default value on a public function | **YES** (changing it silently breaks callers who rely on it) |
| Column names / keys in a returned DataFrame / dict | **YES** (schema is part of the API) |
| An exception type a caller could `except` | **YES** |
| Internal helpers prefixed `_` | **NO** |
| Test fixtures and utilities | **NO** |

If yes to any — the change is a candidate for BC compliance.

## Step 2: Classify the change

```
CHANGE TYPE
  │
  ├─ Adding a new optional argument, a new function, a new module
  │   └─ ADDITIVE — no break, ship in a minor version
  │
  ├─ Renaming X to Y, removing X, reordering positional args
  │   └─ BREAKING — need a deprecation path OR a major version bump
  │
  ├─ Changing a default value (e.g., metric='sessions' → metric='value')
  │   └─ SOFT-BREAKING — silent behavior change for existing callers
  │      Safe only if: (a) audit shows no callers rely on the old default,
  │      OR (b) you emit a DeprecationWarning for one release cycle
  │
  ├─ Changing a return type/shape
  │   └─ BREAKING — callers will type-error or silently consume wrong shape
  │
  ├─ Changing a raised exception type
  │   └─ BREAKING — callers' `except` clauses may stop catching
  │
  └─ Tightening a validation (previously-accepted input now raises)
      └─ SOFT-BREAKING — callers may be relying on quiet acceptance
```

## Step 3: Audit the blast radius

Before you commit a rename or default change, run the blast-radius check:

```bash
# Explicit callers of the old name
rg '\bold_function_name\b' --glob '!tests/**' --glob '*.py'

# Callers that pass the old default value explicitly (safe, unaffected)
rg "old_function_name\([^)]*metric\s*=\s*['\"]sessions['\"]" --glob '*.py'

# Callers that rely on the default (affected, need to be found)
rg "old_function_name\([^)]*\)" --glob '*.py' | grep -v 'metric='
```

Follow with:
- Search notebooks (`*.ipynb`) — they use the API but tooling ignores them.
- Search other repos you own.
- Check the library's Sphinx docs and README code samples.
- If the library has external users, check GitHub code search for `<library_name> <func_name>`.

| Blast radius | Action |
|---|---|
| 0 external callers, 0 internal callers | Break freely. Note in CHANGELOG. |
| 0 external, N internal | Update internal call sites in the same PR. |
| Unknown external callers | Deprecate; don't break. |
| ≥ 1 high-value external caller | Deprecate with explicit migration guide in CHANGELOG. |

## Step 4: Choose a path

### Additive (no break)

```python
def foo(x, *, new_option=None):  # new kwarg with safe default
    ...
```

Ship in patch or minor. Mention in CHANGELOG under "Added."

### Rename via alias + deprecation

```python
def new_name(x):
    return _impl(x)

def old_name(x):
    warnings.warn(
        "old_name is deprecated; use new_name. "
        "old_name will be removed in v2.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_name(x)
```

- `stacklevel=2` — warning points at the caller, not the wrapper
- Keep alias for at least one minor version; remove on next major
- Document the migration in CHANGELOG

### Default-value change with compat shim

When `metric='sessions'` → `metric='value'` but the new column might not exist:

```python
def build(df, *, metric='value'):
    if metric not in df.columns:
        # Backward compat: fall back to old default if present
        if metric == 'value' and 'sessions' in df.columns:
            warnings.warn(
                "build() default column changed from 'sessions' to 'value'; "
                "falling back to 'sessions' for this call. Rename your column "
                "or pass metric='sessions' explicitly.",
                DeprecationWarning,
                stacklevel=2,
            )
            metric = 'sessions'
        else:
            raise KeyError(f"column {metric!r} not found in DataFrame")
    ...
```

Remove the shim in the next major.

### Clean break (with version bump)

Only when:
- Blast radius is bounded (internal + known external callers)
- The old behavior was wrong (security, correctness)
- You can communicate the change to affected users

Process:
1. Bump major version.
2. Document in CHANGELOG under **Breaking changes** with a migration example.
3. Remove old name; don't leave a confusingly-renamed alias.

## Step 5: Version the result

| You did… | Patch? Minor? Major? |
|---|---|
| Bug fix, no signature change | Patch |
| Added a new function/kwarg/module | Minor |
| Deprecation added (old still works) | Minor |
| Breaking change shipped | Major |
| Behavior change users would notice | At least minor — consider major |

Use what the project uses. If pyproject.toml says SemVer, follow SemVer. If CalVer, follow CalVer. Don't mix.

**The SemVer critique is real**: a deprecation that emits a warning can break users running with `-W error`. Treat *any* observable behavior change as potentially breaking, even if the signature is identical. This is why audit matters more than version math.

## Documenting the change

Every public-API change lands with:

- [ ] Commit message names the change specifically (`rename X to Y`, not `refactor`)
- [ ] CHANGELOG entry under the right section (Added / Changed / Deprecated / Removed / Fixed)
- [ ] Migration guide if the change is breaking (before/after code)
- [ ] Updated docstring reflecting the new behavior
- [ ] Updated tests — including a negative test that exercises the old path and documents why it no longer works

## Schema-level changes (DataFrames, dicts, models)

A function returning a DataFrame is promising a *schema*. Column additions are additive; renames, removals, and type changes are breaking.

| Change | Classification |
|---|---|
| Adding a new column | Additive |
| Renaming a column | Breaking |
| Dropping a column | Breaking |
| Changing a column's dtype | Breaking |
| Reordering columns | Usually breaking (positional access dies) |
| Changing index → column or vice versa | Breaking |

## Gotchas

- **Re-exports are public.** If `from mypkg import Foo` worked before, it's public. Moving `Foo` to a submodule is a break unless you keep the re-export.
- **Private attributes accessed via `_foo`** from user code *count* as public use if you've been tolerating it. Consider deprecating the access pattern.
- **Pickle compatibility.** If users pickle objects of your classes, renaming/moving a class silently breaks unpickling.
- **Default mutation.** Changing `def f(x, opts=None)` internals to mutate `opts` in-place is a breaking behavior change even with no signature change.
- **Warnings are cheap to emit but easy to miss.** Silence them with `warnings.filterwarnings('error', category=DeprecationWarning)` in your own test suite so you catch self-inflicted deprecations.

## Audit checklist before merging a public-API change

- [ ] Blast-radius check run (`rg` across this repo + any dependent repos)
- [ ] Notebooks searched separately
- [ ] External docs / README updated
- [ ] CHANGELOG updated
- [ ] Deprecation warning emitted (if applicable) with `stacklevel=2`
- [ ] At least one test exercises the new name/behavior
- [ ] At least one test exercises the deprecation path (if applicable)
- [ ] PR description names this as a BC consideration

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
