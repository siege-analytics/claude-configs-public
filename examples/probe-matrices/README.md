# Probe matrices

Machine-generated assumption matrices for transformation-code dry-runs. Ships
the primitive proposed in siege-analytics/claude-configs-public#284.

## Why this exists (and the Sagan-parody framing)

`self-review.sh` v1.6 (PR #276 Level 3) requires a `Pre-ship-dry-run:` trailer
on commits touching transformation code. The check is presence-only — any
non-empty trailer passes. The failure shape that motivated #284 was:

- The trailer body narrated compliance ("by construction", "schema reconciliation guaranteed")
- The 30-second probe that would have caught the cardinality assumption (179 vs assumed 24) was never run
- Even deeper: the *semantic* meaning of `cycle` (FEC filing cycle, not transaction year) was never written down anywhere

**Design intent — Carl Sagan parody:** "If you want to make an apple pie
from scratch, first you must invent the universe." Each starter matrix
contains the FULL UNIVERSE of assumptions for a transformation pattern,
across five layers (physical / schematic / semantic / operational /
correctness). The agent does NOT delete entries to reduce the matrix —
the agent JUSTIFIES omissions. Compliance is cheaper as "leave the
universe alone" than as "prove you considered everything."

Each entry is one of three shapes:

| Shape | When | Example |
|---|---|---|
| Shell probe with `threshold` | Mechanically checkable | `SELECT COUNT(DISTINCT year_month) ... → int_lt(50)` |
| `probe_type = "manual_attestation"` with `fields` | Semantic claim not mechanically probeable | "cycle means FEC filing cycle, source: docs/glossary.md:42" |
| `skip = "<≥20-char justification>"` | Truly N/A to this operation | "Target is new; no prior-state check applies." |

The runner executes / validates each entry and writes a JSON result file
with machine-generated fields the agent cannot author by hand.
`self-review.sh` v1.7 validates: runner signature, session id, all-PASS
overall_status, AND that every `SKIPPED` entry has a non-trivial reason
(≥20 chars, not "n/a" / "trivial" / etc.).

## How to use one

1. **Copy a starter matrix** matching your operation shape to your repo (or
   to `/tmp/probes/`). Starters available in this directory:
   - [`partition-migration.toml`](partition-migration.toml) — adding `PARTITIONED BY` to an existing table or changing partition scheme.

2. **Edit the `probe` commands** to point at your actual source/target. The
   starter probes are placeholders (`echo 'EDIT: ...'`) so a copy-paste
   without edits fails loudly rather than silently.

3. **Tune `threshold.value`** per the operation's resource budget. The
   defaults are conservative empirical floors; don't raise them without
   measuring the production behavior they're floors against.

4. **Run the matrix:**
   ```bash
   python3 hooks/lib/probe-runner.py path/to/your-matrix.toml
   ```
   Default output: `/tmp/probes/<basename>-result.json`. Override with
   `--output`. Exit code is 0 (PASS), 1 (BLOCK), or 2 (ERROR).

5. **Cite the result file in your PR's commit trailer:**
   ```
   Probe-Matrix: /tmp/probes/sb-partition-migration-result.json
   ```

   `self-review.sh` v1.7 validates the trailer at push time.

## Matrix schema

Every `[[assumption]]` is one of three shapes. The `id` and `description`
fields are required on all three; pick exactly one of `probe`,
`probe_type = "manual_attestation"`, or `skip`.

```toml
version = 1
operation = "<one-line description of the operation>"
target_repo = "<owner/repo>"           # optional, informational
target_pr = 0                           # optional, informational
starter_pattern = "<name>"             # optional; identifies which starter this matrix derives from

# Shape A: shell probe with optional threshold
[[assumption]]
id = "<short-identifier>"               # required, unique within matrix
description = "<why this matters>"      # required, human-readable
probe = "<shell command>"               # runs via subprocess shell=True
threshold = { type = "<type>", value = <value> }  # optional; absent = informational

# Shape B: manual attestation (semantic claims that can't be probed mechanically)
[[assumption]]
id = "..."
description = "..."
probe_type = "manual_attestation"
required_fields = ["meaning", "source", "value_examples"]   # default: ["meaning", "source"]
[assumption.fields]
meaning = "..."                         # plain-language description
source = "<file:line | URL | path>"     # required; validator checks it looks like a citable reference, not prose
value_examples = "..."                  # optional / per required_fields

# Shape C: explicit skip with justification
[[assumption]]
id = "..."
description = "..."
skip = "<>=20 char specific reason; rejected if 'n/a', 'not applicable', 'trivial', etc.>"
```

### When to use each shape

- **Shell probe** — anything you can ask the data to answer with a number or
  a string match. Row counts, distinct counts, schema presence, EXPLAIN-plan
  features. The cheapest and most-checkable shape.
- **Manual attestation** — semantic claims (what does this column mean? who
  consumes this output? what's the rollback path?). The runner doesn't
  execute the claim — it validates the matrix has the required fields filled
  with non-trivial values and that `source` looks like a citable reference.
- **Skip** — the assumption truly doesn't apply to this specific operation.
  The justification must be specific (≥20 chars, not on the trivial-phrases
  list). Deleting the entry is NOT an alternative; this is the Sagan-parody
  design intent.

### Threshold types

| `type`            | `value`     | Pass condition |
|-------------------|-------------|----------------|
| `int_gt`          | int         | `int(stdout_tail) > value` |
| `int_lt`          | int         | `int(stdout_tail) < value` |
| `int_ge`          | int         | `int(stdout_tail) >= value` |
| `int_le`          | int         | `int(stdout_tail) <= value` |
| `int_eq`          | int         | `int(stdout_tail) == value` |
| `string_contains` | str         | `value in stdout` |
| `regex_match`     | regex str   | `re.search(value, stdout)` matches |
| `not_empty`       | (ignored)   | `stdout.strip() != ""` |

`stdout_tail` is the last whitespace-separated token of the probe's stdout —
matches the natural output shape of `spark-sql -e 'SELECT COUNT(*) ...'`
which prints headers followed by the integer. Probes that print structured
output should use `string_contains` or `regex_match` with a sentinel.

## Result schema (machine-written)

```json
{
  "schema_version": 1,
  "generator": "probe-runner.py",
  "generator_version": "1.0",
  "generated_at": "2026-06-02T02:15:00.123456+00:00",
  "session_id": "260527-apt-ocean",
  "matrix_path": "/abs/path/to/matrix.toml",
  "operation": "INSERT OVERWRITE ...",
  "target_repo": "electinfo/airflow",
  "target_pr": 147,
  "results": [
    {
      "id": "partition_key_cardinality_bounded",
      "probe": "spark-sql -e '...'",
      "output": "179",
      "status": "BLOCK",
      "threshold": "int_lt(50)",
      "reason": "not (179 < 50)",
      "ran_at": "..."
    }
  ],
  "overall_status": "BLOCK"
}
```

The hook validates: `generator == "probe-runner.py"`, `session_id` matches
the current session, every result has a `status` of `PASS`, and
`overall_status == "PASS"`. Any deviation BLOCKS the push.

## Adding new starter matrices

Each new pattern lives as its own `.toml` file in this directory plus an
entry in the table above. Keep starter probes as **placeholders** (`echo
'EDIT: ...'`) so a copy-paste without edits fails. Include the empirical
threshold floor in the assumption's `description` so the agent knows what
to measure if they want to raise it.
