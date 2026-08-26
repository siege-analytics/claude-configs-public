#!/usr/bin/env python3
"""probe-runner.py — execute a probe matrix manifest, write machine-generated results.

Usage:
    probe-runner.py <matrix.toml> [--output <result.json>] [--session-id <id>]

The agent authors a TOML probe-matrix manifest listing load-bearing
data-shape assumptions. Each [[assumption]] is one of three shapes:

  (a) Shell probe (default):
        probe     = "spark-sql -e '...'"
        threshold = { type = "int_lt", value = 50 }

  (b) Manual attestation (semantic claims that can't be probed mechanically):
        probe_type      = "manual_attestation"
        required_fields = ["meaning", "source", "value_examples"]
        fields = { meaning = "...", source = "<file:line or URL>", value_examples = "..." }

  (c) Explicit skip (agent attests this assumption doesn't apply):
        skip = "<non-trivial justification, >=20 chars, not 'n/a' / 'trivial'>"

The Sagan-parody design intent (#284): the starter matrix contains the
FULL universe of assumptions for an operation class. The agent fills in
each entry by probing, attesting, or skipping with justification. Deletion
is not allowed; reduction is by justification. Compliance cost is asymmetric
in favor of leaving the universe alone.

The runner executes each entry and writes a JSON result document the agent
cannot author by hand (`generator`, `generated_at`, and per-result `output`
or `fields` come from this script).

The PR's `Probe-Matrix:` trailer points at the result JSON. The companion
self-review.sh check validates the trailer, the file's signature, that
all results are PASS, and that the file was generated this session.

Threshold types:
    int_gt / int_lt / int_ge / int_le / int_eq — last whitespace-separated
        token of stdout is parsed as int and compared to `value`.
    string_contains — stdout contains the literal `value`.
    regex_match — `re.search(value, stdout)` matches.
    not_empty — stdout (stripped) is non-empty.

Exit codes:
    0 — all assumptions PASS
    1 — at least one BLOCK (a threshold rejected the result)
    2 — bad input or runtime error
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tomllib


GENERATOR = "probe-runner.py"
GENERATOR_VERSION = "1.0"
SCHEMA_VERSION = 1
DEFAULT_OUTPUT_DIR = "/tmp/probes"


def now_utc() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def resolve_session_id(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("CRAFT_AGENT_SESSION_ID")
    if env:
        return env
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return f"git-{result.stdout.strip()}"
    except Exception:
        return "unknown"


def evaluate_threshold(stdout: str, threshold: dict | None) -> tuple[str, str]:
    """Return (status, reason). status is PASS or BLOCK."""
    if threshold is None:
        return "PASS", "no threshold (informational probe)"

    t_type = threshold.get("type")
    t_val = threshold.get("value")
    stripped = stdout.strip()

    try:
        if t_type in ("int_gt", "int_lt", "int_ge", "int_le", "int_eq"):
            tokens = stripped.split()
            if not tokens:
                return "BLOCK", "empty output, cannot evaluate int threshold"
            try:
                num = int(tokens[-1])
            except ValueError:
                return "BLOCK", f"output tail {tokens[-1]!r} is not an int"
            checks = {
                "int_gt": (num > t_val, f"{num} > {t_val}"),
                "int_lt": (num < t_val, f"{num} < {t_val}"),
                "int_ge": (num >= t_val, f"{num} >= {t_val}"),
                "int_le": (num <= t_val, f"{num} <= {t_val}"),
                "int_eq": (num == t_val, f"{num} == {t_val}"),
            }
            ok, expr = checks[t_type]
            return ("PASS", expr) if ok else ("BLOCK", f"not ({expr})")
        if t_type == "string_contains":
            if t_val in stdout:
                return "PASS", f"contains {t_val!r}"
            return "BLOCK", f"output does not contain {t_val!r}"
        if t_type == "regex_match":
            if re.search(t_val, stdout):
                return "PASS", f"matches /{t_val}/"
            return "BLOCK", f"output does not match /{t_val}/"
        if t_type == "not_empty":
            if stripped:
                return "PASS", "non-empty"
            return "BLOCK", "empty output"
        return "BLOCK", f"unknown threshold type {t_type!r}"
    except Exception as e:
        return "BLOCK", f"threshold evaluation error: {e}"


SOURCE_RE = re.compile(r"(^https?://|^[^\s]+:\d+|^/|^\.{1,2}/)")


def evaluate_manual_attestation(assumption: dict) -> dict:
    """Manual-attestation assumption: no shell probe; validate that `fields`
    are filled with non-trivial values. Used for semantic claims that can't
    be probed mechanically (column meaning, business intent, etc.)."""
    aid = assumption.get("id", "<unnamed>")
    fields = assumption.get("fields", {})
    required = assumption.get("required_fields", ["meaning", "source"])

    if not isinstance(fields, dict):
        return {
            "id": aid, "probe_type": "manual_attestation", "status": "BLOCK",
            "reason": "fields must be a TOML table", "ran_at": now_utc(),
        }

    missing = []
    for k in required:
        v = fields.get(k)
        if v is None or not str(v).strip():
            missing.append(k)
    if missing:
        return {
            "id": aid, "probe_type": "manual_attestation", "status": "BLOCK",
            "reason": f"missing or empty required fields: {missing}",
            "ran_at": now_utc(),
        }

    # `source` (if required) must look like a file:line, URL, or path —
    # not prose. This is the load-bearing check: the source must be
    # something the operator can grep / open / click.
    if "source" in required:
        source = str(fields["source"]).strip()
        if not SOURCE_RE.search(source):
            return {
                "id": aid, "probe_type": "manual_attestation",
                "fields": fields, "status": "BLOCK",
                "reason": f"source field {source!r} does not look like a path / URL / file:line",
                "ran_at": now_utc(),
            }

    return {
        "id": aid, "probe_type": "manual_attestation", "fields": fields,
        "status": "PASS",
        "reason": f"attested fields filled: {sorted(fields.keys())}",
        "ran_at": now_utc(),
    }


def evaluate_skip(assumption: dict) -> dict:
    """Skipped assumption: agent asserts this doesn't apply to the current
    operation. The skip reason is recorded but the validator (hook side)
    enforces non-triviality."""
    return {
        "id": assumption.get("id", "<unnamed>"),
        "status": "SKIPPED",
        "skip_reason": assumption["skip"],
        "ran_at": now_utc(),
    }


def run_probe(assumption: dict, timeout_sec: int) -> dict:
    aid = assumption.get("id", "<unnamed>")
    probe = assumption.get("probe", "")
    if not probe:
        return {"id": aid, "status": "ERROR", "reason": "no probe command", "ran_at": now_utc()}

    started = now_utc()
    try:
        result = subprocess.run(
            probe, shell=True, capture_output=True, text=True, timeout=timeout_sec,
        )
        if result.returncode != 0:
            return {
                "id": aid,
                "probe": probe,
                "output": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "exit_code": result.returncode,
                "status": "ERROR",
                "reason": f"probe exited {result.returncode}",
                "ran_at": started,
            }
        threshold = assumption.get("threshold")
        status, reason = evaluate_threshold(result.stdout, threshold)
        entry = {
            "id": aid,
            "probe": probe,
            "output": result.stdout.strip(),
            "status": status,
            "ran_at": started,
        }
        if threshold is not None:
            entry["threshold"] = f"{threshold.get('type')}({threshold.get('value')})"
            entry["reason"] = reason
        else:
            entry["reason"] = reason
        return entry
    except subprocess.TimeoutExpired:
        return {
            "id": aid,
            "probe": probe,
            "status": "ERROR",
            "reason": f"probe timed out after {timeout_sec}s",
            "ran_at": started,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a probe-matrix manifest.")
    parser.add_argument("matrix", help="Path to TOML probe-matrix manifest")
    parser.add_argument("--output", help="Output JSON path (default: /tmp/probes/<basename>-result.json)")
    parser.add_argument("--session-id", help="Override session id (default: $CRAFT_AGENT_SESSION_ID or git-<short-sha>)")
    parser.add_argument("--timeout", type=int, default=120, help="Per-probe timeout in seconds (default 120)")
    parser.add_argument("--stop-on-block", action="store_true",
                        help="Skip downstream probes once one BLOCKs (default: run all)")
    args = parser.parse_args()

    if not os.path.isfile(args.matrix):
        print(f"ERROR: matrix file not found: {args.matrix}", file=sys.stderr)
        return 2

    try:
        with open(args.matrix, "rb") as f:
            manifest = tomllib.load(f)
    except Exception as e:
        print(f"ERROR: failed to parse {args.matrix}: {e}", file=sys.stderr)
        return 2

    assumptions = manifest.get("assumption", [])
    if not isinstance(assumptions, list) or not assumptions:
        print("ERROR: manifest has no [[assumption]] entries", file=sys.stderr)
        return 2

    session_id = resolve_session_id(args.session_id)
    output_path = args.output
    if not output_path:
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        base = os.path.splitext(os.path.basename(args.matrix))[0]
        output_path = f"{DEFAULT_OUTPUT_DIR}/{base}-result.json"

    results = []
    overall = "PASS"
    for a in assumptions:
        if overall == "BLOCK" and args.stop_on_block:
            results.append({
                "id": a.get("id", "<unnamed>"),
                "status": "NOT_RUN",
                "reason": "prior assumption blocked and --stop-on-block set",
            })
            continue

        # Dispatch based on which field is present:
        #   `skip = "..."` -> agent attests this doesn't apply (SKIPPED)
        #   `probe_type = "manual_attestation"` + `fields` -> semantic attestation
        #   `probe = "..."` -> shell-runnable probe (original v1.0 path)
        if "skip" in a:
            entry = evaluate_skip(a)
        elif a.get("probe_type") == "manual_attestation":
            entry = evaluate_manual_attestation(a)
        else:
            entry = run_probe(a, timeout_sec=args.timeout)

        results.append(entry)
        if entry["status"] == "BLOCK":
            overall = "BLOCK"
        elif entry["status"] == "ERROR" and overall != "BLOCK":
            overall = "ERROR"
        # PASS, SKIPPED, NOT_RUN are neutral on overall_status.

    result_doc = {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "generator_version": GENERATOR_VERSION,
        "generated_at": now_utc(),
        "session_id": session_id,
        "matrix_path": os.path.abspath(args.matrix),
        "operation": manifest.get("operation", "<unspecified>"),
        "target_repo": manifest.get("target_repo"),
        "target_pr": manifest.get("target_pr"),
        "results": results,
        "overall_status": overall,
    }

    with open(output_path, "w") as f:
        json.dump(result_doc, f, indent=2)
        f.write("\n")

    print(f"probe-runner: wrote {output_path} | overall_status={overall}", file=sys.stderr)
    for r in results:
        print(f"  [{r['status']:8}] {r['id']}: {r.get('reason', '-')}", file=sys.stderr)

    if overall == "PASS":
        return 0
    if overall == "BLOCK":
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
