# Pipeline Jobs Reference

Rundeck YAML template and nohup wrapper pattern.

## Rundeck YAML Template

```yaml
- defaultTab: output
  description: |
    One-line description.

    What this job does, what it reads, what it writes.
    Any dependencies or prerequisites.
  executionEnabled: true
  loglevel: INFO
  group: my-group
  name: MyJobName
  nodeFilterEditable: false
  nodefilters:
    dispatch:
      excludePrecedence: true
      keepgoing: false
      rankOrder: ascending
      successOnEmptyNodeFilter: false
      threadcount: '1'
    filter: 'name:my-runner.* status:running'
  nodesSelectedByDefault: true
  schedule:
    time:
      hour: '07'
      minute: '00'
      seconds: '0'
    month: '*'
    dayofmonth:
      day: '*'
    year: '*'
    weekday:
      day: '*'
  scheduleEnabled: true
  options:
  - description: Show planned steps without executing
    enforced: true
    label: Dry Run
    name: dry-run
    required: false
    value: 'false'
    values:
    - 'true'
    - 'false'
    valuesListDelimiter: ','
  plugins:
    ExecutionLifecycle: {}
  sequence:
    commands:
    - description: Run the job (nohup-wrapped)
      script: |
        #!/bin/bash
        set -e

        DRY_RUN="@option.dry-run@"
        LOGFILE="/tmp/my-job-$(date +%Y%m%d-%H%M%S).log"
        PIDFILE="/tmp/my-job.pid"

        echo "=============================================="
        echo "My Job Name"
        echo "=============================================="
        echo "Dry Run: $DRY_RUN"
        echo "Log: $LOGFILE"
        echo "=============================================="

        CMD="python3 /path/to/script.py --arg1 value1"

        if [ "$DRY_RUN" = "true" ]; then
          CMD="$CMD --dry-run"
        fi

        echo "Running: $CMD"
        echo "=============================================="

        # nohup pattern: survives websocket drops
        nohup bash -c "$CMD" > "$LOGFILE" 2>&1 &
        PID=$!
        echo $PID > "$PIDFILE"
        echo "Started PID $PID, logging to $LOGFILE"

        # Tail log until process finishes
        while kill -0 $PID 2>/dev/null; do
          if [ -f "$LOGFILE" ]; then
            tail -1 "$LOGFILE" 2>/dev/null || true
          fi
          sleep 10
        done

        # Check exit code
        wait $PID
        EXIT_CODE=$?

        echo ""
        echo "=============================================="
        if [ $EXIT_CODE -eq 0 ]; then
          echo "Job completed successfully"
        else
          echo "Job FAILED (exit code: $EXIT_CODE)"
          tail -20 "$LOGFILE"
        fi
        echo "=============================================="

        exit $EXIT_CODE
    keepgoing: false
    strategy: node-first
```

## nohup Wrapper Explained

The Rundeck K8s executor websocket drops after ~7 minutes. Without nohup, a long-running job dies when the connection drops. The pattern:

1. **`nohup bash -c "$CMD" > "$LOGFILE" 2>&1 &`** — starts the job in the background, immune to hangup signals, logging to a file
2. **`echo $PID > "$PIDFILE"`** — saves the PID for monitoring
3. **`while kill -0 $PID`** — polls until the process finishes, tailing the log for Rundeck output
4. **`wait $PID; EXIT_CODE=$?`** — captures the exit code after the process finishes
5. **`exit $EXIT_CODE`** — propagates the exit code to Rundeck

If Rundeck disconnects during step 3, the process continues via nohup. The log file persists on the pod.

## Fetch Script Template

```python
#!/usr/bin/env python3
"""Check [source] for new data and download if available.

Reads from: [source URL/FTP]
Writes to:  [local path or S3]
Schedule:   [frequency]
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def check_for_updates(source: str, state_file: Path) -> bool:
    """Check if source has new data since last fetch.

    Compares Last-Modified header (or equivalent) against
    the timestamp stored in state_file.
    """
    import requests

    resp = requests.head(source, timeout=30)
    remote_modified = resp.headers.get("Last-Modified", "")

    if state_file.exists():
        local_modified = state_file.read_text().strip()
        if remote_modified == local_modified:
            logger.info("No new data (Last-Modified: %s)", remote_modified)
            return False

    logger.info("New data available (Last-Modified: %s)", remote_modified)
    return True


def fetch(source: str, output_dir: Path) -> Path:
    """Download data from source."""
    import requests

    output_dir.mkdir(parents=True, exist_ok=True)
    filename = source.rsplit("/", 1)[-1]
    output_path = output_dir / filename

    logger.info("Downloading %s → %s", source, output_path)
    resp = requests.get(source, stream=True, timeout=300)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info("Downloaded %d bytes", output_path.stat().st_size)
    return output_path


def load(file_path: Path, command: str) -> None:
    """Call a Django management command to load the data."""
    import subprocess

    logger.info("Loading via: python manage.py %s", command)
    subprocess.run(
        ["python", "manage.py"] + command.split(),
        check=True,
    )


def update_state(state_file: Path, timestamp: str) -> None:
    """Record the last-fetched timestamp."""
    state_file.write_text(timestamp)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("/data/spatial"))
    parser.add_argument("--state-file", type=Path, default=Path("/tmp/fetch-state.txt"))
    parser.add_argument("--load-command", help="Django management command to run after download")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    has_updates = check_for_updates(args.source, args.state_file)

    if args.check_only:
        sys.exit(0 if has_updates else 1)

    if not has_updates:
        logger.info("No updates — nothing to do")
        sys.exit(0)

    if args.dry_run:
        logger.info("DRY RUN: would fetch %s", args.source)
        sys.exit(0)

    file_path = fetch(args.source, args.output_dir)

    if args.load_command:
        load(file_path, args.load_command)

    update_state(args.state_file, datetime.utcnow().isoformat())
    logger.info("Done")


if __name__ == "__main__":
    main()
```
