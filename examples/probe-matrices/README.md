# Probe matrices

Machine-generated assumption matrices for transformation-code dry-runs. Ships
the primitive proposed in siege-analytics/claude-configs-public#284.

## Why this exists

`self-review.sh` v1.6 (PR #276 Level 3) requires a `Pre-ship-dry-run:` trailer
on commits touching transformation code. The check is presence-only — any
non-empty trailer passes. The failure shape that motivated #284 was:

- The trailer body narrated compliance ("by construction", "schema reconciliation guaranteed")
- The 30-second probe that would have caught the assumption (cardinality of the partition key) was never run
- Three same-shape PRs shipped on the same unverified assumption

A probe matrix forces the agent to enumerate data-shape assumptions in a
TOML manifest, then runs each probe via `hooks/lib/probe-runner.py`. The
runner writes a JSON result file with machine-generated fields the agent
cannot author by hand. `self-review.sh` v1.7 validates the trailer points
at a result file with a runner signature, current session id, all results
PASS, and a PASS overall_status.

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

```toml
version = 1
operation = "<one-line description of the operation>"
target_repo = "<owner/repo>"           # optional, informational
target_pr = 0                           # optional, informational

[[assumption]]
id = "<short-identifier>"               # required, unique within matrix
description = "<why this matters>"      # required, human-readable
probe = "<shell command>"               # required, runs via subprocess shell=True
threshold = { type = "<type>", value = <value> }  # optional; absent = informational
```

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
