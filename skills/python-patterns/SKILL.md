---
name: python-patterns
description: "Engineering principles for Python library code. TRIGGER: duplicated functions, undeclared attributes, ignored kwargs, unchecked types crossing module boundaries, or a CR comment about architectural smells. Covers DRY, dataclass discipline, interface integrity, and runtime type correctness."
routed-by: coding-standards
user-invocable: false
paths: "**/*.py"
---

# Python Engineering Patterns

## Companion shelves

Tier A delegation. The deep rationale lives in:
- [`effective-python`](../shelves/languages/effective-python/SKILL.md) — Pythonic structure.
- [`using-asyncio-python`](../shelves/languages/using-asyncio-python/SKILL.md) — async patterns.
- [`clean-code`](../shelves/engineering-principles/clean-code/SKILL.md) — DRY, function discipline.
- [`design-patterns`](../shelves/engineering-principles/design-patterns/SKILL.md) — GoF in Python.

Use the rules below for Siege-specific conventions; load the shelf books for principle-level reasoning.

Apply these to library code — things imported and called by other modules. See [reference.md](reference.md) for specific before/after refactors and the Geographic Data Science with Python ESDA patterns.

## DRY — extract when duplication is real

**Three similar lines is better than a premature abstraction.** Don't factor out a helper until you have three concrete call sites whose behavior actually converges.

Signs you should extract:
- Three+ functions that differ only in a lookup table, a constant, or a single line
- Copy-paste blocks with identical control flow
- Multiple `if/elif` branches that compute the same thing with different input names

Signs you should NOT extract yet:
- Two functions that look similar but have different failure modes
- "I might need this pattern later" speculation
- A helper that takes 7 parameters just to cover all the caller variations

### The shared-core pattern

When N functions share 90% of their logic with per-case dispatchers:

```python
# BEFORE — three near-duplicates
def _build_single_response(df, row_var, break_vars, metric, weight_var, top_n, geo_column):
    views = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            views[f"{bv}={bval}"] = _views_from_counts(counts, base)
    return Chain(row_var, break_vars, views, TableType.SINGLE_RESPONSE, geo_column=geo_column)

def _build_cross_tab(...):  # same body, different TableType
def _build_banner(...):      # same body, different TableType

# AFTER — one core + a per-type tail
def _build_grouped_counts(df, row_var, break_vars, metric, weight_var, top_n):
    """Shared implementation for SINGLE_RESPONSE, CROSS_TAB, BANNER."""
    views = {}
    for bv in break_vars:
        for bval in df[bv].dropna().unique():
            subset = df[df[bv] == bval]
            base = _base_respondents(subset, weight_var)
            counts = _weighted_counts(subset, row_var, metric, weight_var)
            if top_n:
                counts = counts.nlargest(top_n)
            views[f"{bv}={bval}"] = _views_from_counts(counts, base)
    return views

def _build_single_response(df, row_var, break_vars, metric, weight_var, top_n, geo_column) -> Chain:
    views = _build_grouped_counts(df, row_var, break_vars, metric, weight_var, top_n)
    return Chain(row_var, break_vars, views, TableType.SINGLE_RESPONSE, geo_column=geo_column)
```

Three call sites collapse to one, each 2 lines, total line count drops ~40%.

## Dataclass discipline — declared fields only

If you use `@dataclass`, **every attribute the class holds is a field**. Don't attach runtime attributes from sibling modules:

```python
# BAD
@dataclass
class Chain:
    row_var: str
    break_vars: list[str]

# somewhere else...
def compute_significance(chain):
    chain.chi_square_significant = True  # undeclared field!
```

Why bad:
- Attribute doesn't appear in `__annotations__`, so `asdict()`, `pickle`, `dataclasses.fields()`, and IDE autocomplete miss it
- With `slots=True` it raises `AttributeError` — protecting you
- Future readers can't tell what a `Chain` *actually* contains

Fix, in order of preference:

1. **Add to the dataclass** (with a sensible default):
   ```python
   @dataclass(slots=True)
   class Chain:
       row_var: str
       break_vars: list[str]
       chi_square_significant: bool | None = None
   ```

2. **Use a separate results object** if the field is computed, not stored:
   ```python
   @dataclass
   class ChainStats:
       chain: Chain
       chi_square_significant: bool
       p_value: float
   ```

3. **Return instead of mutate** — the compute function returns the new value; caller decides where to put it.

### When dynamic attributes ARE OK

- You're deliberately building a dict-like object (use `@dataclass` with a `dict[str, Any]` field, not raw attributes)
- Plugin/extension patterns where clients attach their own fields (use a namespace object or `weakref.WeakValueDictionary`)
- Interop with a legacy API that expects `setattr`

None of those apply to ordinary library code.

## Interface integrity — honor every kwarg

If a function accepts a parameter, use it. If you can't use it, raise.

```python
# BAD — caller pays for something they don't get
def create_report(title, *, chart_generator=None, map_generator=None):
    """Build a report. Accepts chart_generator and map_generator kwargs."""
    # ...neither kwarg is ever referenced in the body...

# BETTER — fail loudly on unsupported options
def create_report(title, *, chart_generator=None, map_generator=None):
    if chart_generator is not None:
        raise NotImplementedError("chart_generator injection not yet supported; see issue #123")
    if map_generator is not None:
        raise NotImplementedError("map_generator injection not yet supported; see issue #123")
    ...

# BEST — only accept what you handle
def create_report(title):
    ...
```

A silently-ignored kwarg is an undocumented bug: users pass it, believe it worked, and get wrong output. Worse than crashing.

## Runtime type correctness at module boundaries

Type hints are documentation. They don't check at runtime unless you do.

At module boundaries where wrong types cause confusing downstream failures, **add explicit `isinstance` checks** or use a validation library:

```python
# BAD — type hint is a lie
def stack_to_arguments(stack: Stack) -> list[Argument]:
    args = []
    for cluster in stack.clusters:
        for chain in cluster.chains:  # declared: list[Chain]
            args.append(chain.to_argument())
    cluster.chains = args  # now it's list[Argument] — caller gets wrong type
    return args
```

```python
# GOOD — separate input type from output type; don't mutate inputs
def stack_to_arguments(stack: Stack) -> list[Argument]:
    return [
        chain.to_argument()
        for cluster in stack.clusters
        for chain in cluster.chains
    ]
# Don't reassign cluster.chains; build a new structure if callers need it.
```

### Validating at module boundaries

When accepting user-provided data (or data crossing a trust boundary):

```python
def render(chain: Chain, *, layout: str) -> Argument:
    if not isinstance(chain, Chain):
        raise TypeError(f"render() expected Chain, got {type(chain).__name__}")
    if layout not in {"full_width", "side_by_side"}:
        raise ValueError(f"unknown layout {layout!r}; expected full_width | side_by_side")
    ...
```

For dataclasses specifically, consider `pydantic.BaseModel` or `attrs` with validators if you want automatic runtime checks without the `isinstance` boilerplate.

## Never-empty-success

Returning an empty result when a computation failed is worse than raising. Callers can't tell "no data" from "error hidden".

```python
# BAD — empty chain could mean "no matching rows" OR "metric column missing"
def _build_mean_scale(df, row_var, ...):
    if metric not in df.columns:
        return Chain(row_var, [], {}, TableType.MEAN_SCALE)
    ...

# GOOD — distinguish the cases
def _build_mean_scale(df, row_var, ...):
    if metric not in df.columns:
        raise MeanScaleError(f"column {metric!r} not found in input; got columns={list(df.columns)}")
    ...
```

Or, if "no data" is legitimate:

```python
# GOOD — return empty explicitly, document, log
def _build_mean_scale(df, row_var, ...):
    if metric not in df.columns:
        log_warning(f"metric {metric!r} missing; returning empty chain")
        return Chain(row_var, [], {}, TableType.MEAN_SCALE, base_note="NO DATA")
    ...
```

The `base_note="NO DATA"` is a breadcrumb a downstream reader can see. A naked empty chain is not.

## Module organization

- **Lazy imports** only when genuinely optional (geopandas in tests, reportlab in notebook envs). Pattern:
  ```python
  try:
      import geopandas as gpd
      HAS_GEOPANDAS = True
  except ImportError:
      HAS_GEOPANDAS = False
  ```
- **Forward references** with `from __future__ import annotations` + `TYPE_CHECKING`:
  ```python
  from __future__ import annotations
  from typing import TYPE_CHECKING
  if TYPE_CHECKING:
      from ..other_module import OtherType

  def f(x: OtherType) -> None: ...
  ```
- **No import-time side effects** in library modules. If a module imports pandas and configures `pd.options.display.max_rows`, you've broken every notebook that imports yours.
- **`__all__`** explicitly lists the public API. Re-exports in `__init__.py` go here. `F401` complaints get `# noqa: F401` with a reason comment.

## Mutable defaults

```python
# BAD — shared across all calls
def append(item, *, to=[]):
    to.append(item)
    return to

# GOOD
def append(item, *, to=None):
    to = to if to is not None else []
    to.append(item)
    return to
```

Any linter catches this. Still worth naming because it comes up in review.

## References

- **Brett Slatkin — *Effective Python* 3rd ed (2025)** — 125 specific items, many load-bearing here
- **Raymond Hettinger — PyCon talks on dataclasses, generators, `__init_subclass__`** — YouTube, annual
- **Martin Fowler — *Refactoring* 2nd ed** — the canonical refactoring catalog, language-agnostic but applicable
- **Will McGugan's textual blog** — pragmatic library-maintenance posts
- **Adam Johnson (adamj.eu)** — Python / Django patterns, current as of 2025

## Attribution Policy

See [`output`](../_output-rules.md). NEVER include AI or agent attribution.
