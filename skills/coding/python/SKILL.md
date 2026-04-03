---
name: python
description: Python style and conventions for clean, maintainable code. Covers naming, structure, error handling, type hints, and modern Python (3.11+) idioms.
---

# Python Style

## When to Use This Skill

When writing or reviewing Python code. Apply these conventions unless the project has its own documented style that contradicts them.

## Language Version

Target **Python 3.11+**. Use modern features when they improve clarity:

| Feature | Use When | Example |
|---------|----------|---------|
| `match`/`case` | Dispatching on type or structure | Replacing `if/elif` chains on `.type` fields |
| `tomllib` | Reading TOML config | `tomllib.load(f)` instead of third-party toml |
| `ExceptionGroup` | Multiple simultaneous failures | Batch operations where partial failure is expected |
| `TaskGroup` | Structured concurrency | `async with asyncio.TaskGroup() as tg:` |
| `StrEnum` | String enumerations | Status codes, API response types |
| `Self` type | Return type is the class | `def copy(self) -> Self:` |

Do **not** use features just because they exist. A simple `if/elif` is fine for 2-3 branches.

## Naming

```python
# Modules and packages: short, lowercase, no underscores if possible
import parsers        # good
import fec_parsers    # acceptable if disambiguation needed

# Functions and variables: snake_case, verb phrases for functions
def load_filings(path: Path) -> list[Filing]:
    raw_text = path.read_text()

# Classes: PascalCase, noun phrases
class DonationRecord:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3
DEFAULT_TIMEOUT = 30

# Private: single leading underscore
def _parse_header(line: str) -> dict:
    pass

# Boolean variables/parameters: read as a question
is_valid = True
has_header = False
should_retry = attempt < MAX_RETRY_COUNT
```

**Avoid:**
- `data`, `info`, `stuff`, `thing`, `item` as variable names — name what it actually is
- Hungarian notation (`str_name`, `lst_items`)
- Abbreviations that aren't universally known (`fn`, `cb`, `ctx` — use `function`, `callback`, `context`)
- Single-letter names outside of comprehensions and lambdas

## Imports

Order: stdlib, third-party, local. One blank line between groups. Alphabetical within groups.

```python
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from pydantic import BaseModel

from myproject.config import settings
from myproject.parsers import load_filing
```

**Rules:**
- Never use `from module import *`
- Prefer `from x import Y` over `import x` when you use `Y` more than twice
- Never import inside a function unless there is a genuine circular import or heavy-import-cost reason — and document why

## Function Design

```python
# Good: does one thing, clear inputs and outputs
def geocode_address(street: str, city: str, state: str, zip_code: str) -> Coordinate | None:
    """Return lat/lng for an address, or None if geocoding fails."""

# Bad: does too many things, unclear what it returns
def process(data):
    ...
```

**Rules:**
- Functions should do one thing. If you need a comment saying "now do the second part", split it.
- Return early for guard clauses instead of deep nesting.
- Limit parameters to 5. Beyond that, use a dataclass or TypedDict as input.
- Avoid mutable default arguments (`def f(items=[])`). Use `None` and create inside.
- Prefer returning values over mutating arguments.

```python
# Early return pattern
def find_committee(committee_id: str) -> Committee | None:
    if not committee_id:
        return None

    if not committee_id.startswith("C"):
        return None

    return db.query(Committee).filter_by(id=committee_id).first()
```

## Error Handling

```python
# Good: catch specific exceptions, handle meaningfully
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.Timeout:
    logger.warning("Request to %s timed out", url)
    return None
except requests.HTTPError as e:
    logger.error("HTTP %d from %s", e.response.status_code, url)
    raise

# Bad: bare except, catch-all, swallowing errors
try:
    do_something()
except:        # catches SystemExit, KeyboardInterrupt
    pass       # silently swallows the error
```

**Rules:**
- Never use bare `except:` — it catches `SystemExit` and `KeyboardInterrupt`
- Never use `except Exception: pass` — at minimum log the error
- Catch the most specific exception possible
- Let unexpected exceptions propagate — don't hide bugs
- Use `raise` (no argument) to re-raise; use `raise X from Y` to chain

## Type Hints

Use type hints where they **add information** a reader wouldn't already know.

```python
# Helpful: clarifies what goes in and comes out
def merge_records(
    existing: dict[str, DonorRecord],
    incoming: list[RawDonation],
) -> dict[str, DonorRecord]:

# Unnecessary: obvious from context
count: int = 0              # just use: count = 0
name: str = "default"       # just use: name = "default"
```

**Rules:**
- Always annotate function signatures (parameters + return)
- Skip annotations for local variables when the type is obvious
- Use `X | None` over `Optional[X]` (3.10+)
- Use `list[X]`, `dict[K, V]`, `tuple[X, Y]` (lowercase, 3.9+)
- Use `Self` for methods that return their own class
- Complex types get a `TypeAlias`: `Coordinate: TypeAlias = tuple[float, float]`

## Data Structures

Choose the right one:

| Need | Use | Not |
|------|-----|-----|
| Structured record with named fields | `dataclass` or `NamedTuple` | Plain `dict` or `tuple` |
| Validated external input | `pydantic.BaseModel` | `dataclass` with manual validation |
| Immutable config | `NamedTuple` or frozen `dataclass` | Regular `dataclass` |
| Simple key-value lookup | `dict` | `dataclass` with dynamic fields |
| Ordered unique items | `dict` (insertion-ordered) | `list` with manual dedup |
| Set membership testing | `set` or `frozenset` | `list` with `in` checks |

```python
# Good: structured, self-documenting
@dataclass
class Filing:
    committee_id: str
    amount: Decimal
    date: date
    filing_type: str

# Bad: anonymous, error-prone
filing = ("C00703975", Decimal("250.00"), date(2024, 3, 15), "SA11AI")
```

## String Formatting

Use f-strings for interpolation. Use `.format()` only for deferred templates.

```python
# f-string for immediate use
logger.info(f"Loaded {count} records from {path}")

# .format() for reusable templates
QUERY_TEMPLATE = "SELECT * FROM {schema}.{table} WHERE date >= '{cutoff}'"
query = QUERY_TEMPLATE.format(schema=schema, table=table, cutoff=cutoff)

# Triple-quoted for multiline
message = f"""
Filing {filing_id} failed validation:
  Committee: {committee_id}
  Error: {error}
"""
```

## File and Path Handling

Always use `pathlib.Path` over `os.path`.

```python
from pathlib import Path

data_dir = Path("/data/bronze/filings")
output = data_dir / "processed" / f"{filing_id}.parquet"

# Read/write
text = output.read_text(encoding="utf-8")
output.write_bytes(compressed)

# Glob
for csv in data_dir.glob("**/*.csv"):
    process(csv)
```

## Logging

Use `logging`, not `print`, for anything that runs in production.

```python
import logging

logger = logging.getLogger(__name__)

# Levels: DEBUG < INFO < WARNING < ERROR < CRITICAL
logger.info("Processing %d filings", len(filings))
logger.warning("Skipping %s: no committee ID", filing.path)
logger.error("Failed to parse %s: %s", filing.path, exc)

# Use lazy formatting (% style), not f-strings in log calls
# This avoids string construction if the level is filtered out
logger.debug("Record details: %r", record)  # good
logger.debug(f"Record details: {record!r}")  # wasteful if DEBUG is off
```

## Testing

```python
# Name tests as: test_<what>_<condition>_<expected>
def test_geocode_valid_address_returns_coordinate():
    result = geocode_address("123 Main St", "Austin", "TX", "78701")
    assert result is not None
    assert -90 <= result.lat <= 90

def test_geocode_empty_address_returns_none():
    assert geocode_address("", "", "", "") is None

# Use fixtures for shared setup, not inheritance
@pytest.fixture
def sample_filing():
    return Filing(committee_id="C00703975", amount=Decimal("250"), ...)

def test_validate_filing_accepts_valid(sample_filing):
    assert validate(sample_filing) is True
```

**Rules:**
- One assertion concept per test (multiple `assert` lines testing the same thing is fine)
- Tests should be independent — no ordering dependencies
- Test behavior, not implementation — if you refactor internals, tests should still pass
- Name tests so a failure message tells you what broke

## Project Structure

```
myproject/
├── pyproject.toml          # Package metadata, dependencies, tool config
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── config.py       # Settings, constants
│       ├── models.py       # Data structures
│       ├── parsers/        # Subpackage for complex modules
│       │   ├── __init__.py
│       │   └── fec.py
│       └── cli.py          # Entry points
├── tests/
│   ├── conftest.py         # Shared fixtures
│   ├── test_models.py
│   └── test_parsers/
│       └── test_fec.py
└── README.md
```

## Anti-Patterns

| Anti-Pattern | Problem | Instead |
|-------------|---------|---------|
| God class with 20+ methods | Impossible to test or reuse | Split by responsibility |
| Utility module that grows forever | Becomes a junk drawer | Group by domain |
| `**kwargs` everywhere | Hides the actual interface | Spell out parameters |
| Global mutable state | Invisible coupling, test pollution | Pass dependencies explicitly |
| Premature abstraction | Complexity for one use case | Write it inline, extract later |
| Defensive copying everywhere | Performance cost, code noise | Trust internal callers |
| Comments that restate code | Noise; goes stale | Delete them; rename the code |

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
