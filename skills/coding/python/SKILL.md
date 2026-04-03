---
name: python
description: Python style and conventions for clean, maintainable code. Covers naming, structure, error handling, type hints, and 3.11+ idioms.
user-invocable: false
paths: "**/*.py"
---

# Python Style

Apply these conventions when writing or reviewing Python code. See [reference.md](reference.md) for data structure selection, string formatting, logging, testing, project structure, and anti-patterns.

## Language Version

Target **Python 3.11+**. Use modern features when they improve clarity:

| Feature | Use When | Example |
|---------|----------|---------|
| `match`/`case` | Dispatching on type or structure | Replacing `if/elif` chains on `.type` fields |
| `tomllib` | Reading TOML config | `tomllib.load(f)` instead of third-party toml |
| `ExceptionGroup` | Multiple simultaneous failures | Batch operations with partial failure |
| `TaskGroup` | Structured concurrency | `async with asyncio.TaskGroup() as tg:` |
| `StrEnum` | String enumerations | Status codes, API response types |
| `Self` type | Return type is the class | `def copy(self) -> Self:` |

Do **not** use features just because they exist. A simple `if/elif` is fine for 2-3 branches.

## Naming

```python
# Modules: short, lowercase
import parsers

# Functions: snake_case, verb phrases
def load_filings(path: Path) -> list[Filing]:

# Classes: PascalCase, noun phrases
class DonationRecord:

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# Private: single leading underscore
def _parse_header(line: str) -> dict:

# Booleans: read as a question
is_valid = True
has_header = False
should_retry = attempt < MAX_RETRY_COUNT
```

**Avoid:** `data`, `info`, `stuff` as names. Hungarian notation. Abbreviations that aren't universally known. Single-letter names outside of comprehensions and lambdas.

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

Never use `from module import *`. Never import inside a function unless there's a genuine circular import reason (and document why).

## Function Design

- Functions do one thing. If you need a comment saying "now do the second part", split it.
- Return early for guard clauses instead of deep nesting.
- Limit parameters to 5. Beyond that, use a dataclass or TypedDict.
- Avoid mutable default arguments (`def f(items=[])`). Use `None` and create inside.
- Prefer returning values over mutating arguments.

```python
def find_committee(committee_id: str) -> Committee | None:
    if not committee_id:
        return None
    if not committee_id.startswith("C"):
        return None
    return db.query(Committee).filter_by(id=committee_id).first()
```

## Error Handling

```python
# Good: specific, informative
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.Timeout:
    logger.warning("Request to %s timed out", url)
    return None
except requests.HTTPError as e:
    logger.error("HTTP %d from %s", e.response.status_code, url)
    raise
```

**Rules:**
- Never use bare `except:` — catches `SystemExit` and `KeyboardInterrupt`
- Never use `except Exception: pass` — at minimum log the error
- Catch the most specific exception possible
- Let unexpected exceptions propagate
- Use `raise X from Y` to chain exceptions

## Type Hints

Use type hints where they add information a reader wouldn't already know.

```python
# Helpful: clarifies the contract
def merge_records(
    existing: dict[str, DonorRecord],
    incoming: list[RawDonation],
) -> dict[str, DonorRecord]:

# Unnecessary: obvious from context
count: int = 0              # just use: count = 0
```

**Rules:**
- Always annotate function signatures (parameters + return)
- Skip annotations for local variables when obvious
- Use `X | None` over `Optional[X]`
- Use `list[X]`, `dict[K, V]`, `tuple[X, Y]` (lowercase, 3.9+)
- Complex types get a `TypeAlias`: `Coordinate: TypeAlias = tuple[float, float]`

## Further Reference

See [reference.md](reference.md) for:
- Data structure selection table (dataclass vs NamedTuple vs pydantic vs dict)
- String formatting conventions
- File and path handling with pathlib
- Logging patterns (lazy formatting, level selection)
- Testing patterns and naming conventions
- Project structure template
- Anti-patterns catalog

## Attribution Policy

NEVER include AI or agent attribution in code, commits, or documentation.
