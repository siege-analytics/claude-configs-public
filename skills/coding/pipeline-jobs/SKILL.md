---
name: pipeline-jobs
description: Pipeline job pattern. TRIGGER: writing data pipeline scripts, Rundeck jobs, Airflow DAGs, or scheduled data processing. Python first, scheduler second.
routed-by: coding-standards
---

# Pipeline Jobs

## Companion shelves

For pipeline-design rationale and structural cleanliness:
- [`shelves/data-and-pipelines/data-pipelines/`](../../shelves/data-and-pipelines/data-pipelines/SKILL.md) — ingestion, scheduling, observability patterns.
- [`shelves/engineering-principles/clean-architecture/`](../../shelves/engineering-principles/clean-architecture/SKILL.md) — separate orchestration from transformation.

The logic lives in Python. The scheduler (Rundeck, Airflow, cron) is just the wrapper that calls it. If you move schedulers, the Python doesn't change.

## The Pattern

Every pipeline job has two parts:

1. **Python script** — standalone, testable, accepts CLI arguments, returns exit codes
2. **Scheduler config** — YAML/DAG that calls the Python script on a schedule

The Python script must work when called directly from a terminal. The scheduler config must never contain business logic — only environment setup, nohup wrapping, and the call to Python.

## Python Script Design

### Structure

```python
#!/usr/bin/env python3
"""One-line description of what this job does.

Reads from: [source]
Writes to:  [target]
Schedule:   [frequency]
"""

import argparse
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def check_for_updates(source_url: str) -> bool:
    """Check if new data is available without downloading."""
    ...


def fetch(source_url: str, output_dir: Path) -> Path:
    """Download new data. Returns path to downloaded file."""
    ...


def load(file_path: Path, target: str) -> int:
    """Load downloaded data into the target. Returns row count."""
    ...


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Source URL or path")
    parser.add_argument("--output-dir", type=Path, default=Path("/data"))
    parser.add_argument("--target", default="default_table")
    parser.add_argument("--check-only", action="store_true", help="Check for updates without downloading")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.check_only:
        has_updates = check_for_updates(args.source)
        print("NEW_DATA" if has_updates else "NO_UPDATES")
        sys.exit(0 if has_updates else 1)

    if args.dry_run:
        logger.info("DRY RUN: would fetch from %s to %s", args.source, args.output_dir)
        sys.exit(0)

    file_path = fetch(args.source, args.output_dir)
    count = load(file_path, args.target)
    logger.info("Loaded %d rows into %s", count, args.target)


if __name__ == "__main__":
    main()
```

### Rules

- **argparse for all inputs.** No hardcoded paths, URLs, or credentials.
- **Exit codes matter.** 0 = success, 1 = no updates (not an error), 2+ = failure.
- **`--check-only` flag.** Let the scheduler decide whether to proceed based on exit code.
- **`--dry-run` flag.** Show what would happen without doing it.
- **Logging, not print.** Use `logging` so the scheduler can control verbosity.
- **Idempotent.** Running the same job twice produces the same result (no duplicates).
- **One concern per script.** Fetch is separate from load. An orchestrator script calls both.

### Where scripts live

```
project/
├── scripts/            # Standalone fetch/check scripts
│   ├── fetch_census_tiger.py
│   ├── fetch_rdh_boundaries.py
│   └── fetch_state_boundaries.py
├── cli/commands/       # CLI commands (if the project has a CLI framework)
│   ├── download.py
│   ├── parse.py
│   └── load.py
```

## Scheduler Config (Rundeck)

See [reference.md](reference.md) for the full Rundeck YAML template.

### Rules

- **nohup pattern for long jobs.** Rundeck's K8s websocket dies after ~7 minutes. The nohup wrapper keeps the process alive.
- **Log to a timestamped file.** `/tmp/{job-name}-{date}.log` so you can find it later.
- **PID tracking.** Write PID to a file so monitoring can check if the job is still running.
- **Tail the log.** While the process runs, tail the last line every 10 seconds so Rundeck shows progress.
- **Propagate exit code.** `wait $PID` and `exit $EXIT_CODE` so Rundeck knows success vs failure.
- **Never put logic in bash.** Bash is for: setting env vars, calling Python, nohup wrapping. That's it.

### Scheduling conventions

| Frequency | When | Example |
|-----------|------|---------|
| Daily | After data source publishes (e.g., FEC overnight at 3 AM ET) | `hour: '07', minute: '00'` (UTC) |
| Weekly | Sunday early morning | `weekday: { day: 'SUN' }, hour: '08'` (UTC) |
| Monthly | 1st of month | `dayofmonth: { day: '1' }, hour: '08'` (UTC) |

Always schedule in UTC. Convert from local time in comments.

## When to Use Django Management Commands vs Standalone Scripts

| Situation | Use |
|-----------|-----|
| Needs Django ORM (models, querysets, migrations) | Management command |
| Needs PostGIS spatial queries | Management command |
| Pure HTTP fetch + file processing | Standalone script |
| Calls a management command after fetching | Standalone script that shells out to `python manage.py` |

Standalone scripts can call management commands:
```python
import subprocess
subprocess.run(["python", "manage.py", "populate_boundaries", "--year", "2020"], check=True)
```

## Attribution Policy

NEVER include AI or agent attribution in scripts, YAML, commits, or documentation.
