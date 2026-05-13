# Python Reference

Detailed tables, templates, and patterns. Referenced by the main skill.

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

## Testing Patterns

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
