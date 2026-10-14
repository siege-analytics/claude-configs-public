#!/usr/bin/env python3
"""Non-authorizing billing diagnostic. Always exits nonzero; never grants admin merge."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone

BILLING_REASON = "The job was not started because recent account payments have failed or your spending limit needs to be increased."
BILLING = BILLING_REASON + " Please check the 'Billing & plans' section in your settings."
# Only these exact display prefixes are recognized; arbitrary surrounding text is not.
BILLING_PREFIXES = ("", "Error: ", "GitHub Actions: ")
SHA = re.compile(r"^[0-9a-fA-F]{40}$")
IDENTITY = re.compile(r"^[A-Za-z0-9_.-]+$")


def billing_message(value: str) -> bool:
    """Recognize the full documented GitHub message, optionally with a declared prefix."""
    normalized = " ".join(value.split())
    return any(normalized == f"{prefix}{BILLING}" for prefix in BILLING_PREFIXES)


def gh(*args: str):
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=True, timeout=30)
    return json.loads(result.stdout)


def seconds(run: dict) -> float:
    def parse(value):
        if not isinstance(value, str) or not value:
            raise ValueError("missing timestamp")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timestamp lacks timezone")
        return parsed.astimezone(timezone.utc)
    duration = (parse(run.get("completed_at")) - parse(run.get("started_at"))).total_seconds()
    if duration < 0 or duration > 5:
        raise ValueError("negative or too-long check duration")
    return duration


def evaluate(pr: dict, runs: dict, required: dict, statuses: dict, annotations: dict[int, list[dict]], latest: dict) -> list[str]:
    gaps = []
    sha = pr.get("headRefOid")
    if not isinstance(sha, str) or not SHA.fullmatch(sha) or latest.get("headRefOid") != sha:
        gaps.append("missing or changed head SHA")
    if pr.get("reviewDecision") in ("CHANGES_REQUESTED", "REVIEW_REQUIRED") or latest.get("reviewDecision") in ("CHANGES_REQUESTED", "REVIEW_REQUIRED"):
        gaps.append("reviewer block or required review pending")
    if pr.get("reviewDecision") != latest.get("reviewDecision"):
        gaps.append("review decision changed during inspection")
    checks = runs.get("check_runs")
    if not isinstance(checks, list) or not checks or type(runs.get("total_count")) is not int or runs["total_count"] != len(checks):
        gaps.append("incomplete/missing check-run pagination")
        checks = checks if isinstance(checks, list) else []
    contexts = required.get("contexts")
    required_checks = required.get("checks")
    if not isinstance(contexts, list) or not isinstance(required_checks, list):
        gaps.append("required branch-protection checks unavailable")
        contexts, required_checks = [], []
    expected = {(c, None) for c in contexts if isinstance(c, str)}
    for check in required_checks:
        if isinstance(check, dict) and isinstance(check.get("context"), str):
            expected.add((check["context"], check.get("app_id")))
        else:
            gaps.append("malformed required check")
    observed = {(r.get("name"), r.get("app", {}).get("id")) for r in checks if isinstance(r, dict) and isinstance(r.get("app"), dict)}
    for name, app in expected:
        if not any(n == name and (app is None or app == a) for n, a in observed):
            gaps.append(f"missing required check: {name} ({app})")
    for run in checks:
        if not isinstance(run, dict):
            gaps.append("malformed check run")
            continue
        name = run.get("name", "unnamed")
        conclusion = run.get("conclusion")
        if run.get("status") != "completed" or conclusion is None:
            gaps.append(f"pending check: {name}")
        elif conclusion in ("failure", "timed_out", "cancelled", "action_required"):
            try:
                duration = seconds(run)
            except (ValueError, TypeError, OverflowError):
                gaps.append(f"malformed/negative duration: {name}")
                continue
            output = run.get("output")
            if not isinstance(output, dict):
                gaps.append(f"missing check output: {name}")
                continue
            annotation_list = annotations.get(run.get("id"))
            if not isinstance(annotation_list, list) or any(not isinstance(a, dict) for a in annotation_list):
                gaps.append(f"incomplete annotations: {name}")
                continue
            messages = [output.get(key, "") for key in ("summary", "title", "text")]
            messages += [a.get(key, "") for a in annotation_list for key in ("message", "title", "raw_details")]
            if any(s is not None and not isinstance(s, str) for s in messages):
                gaps.append(f"malformed check output: {name}")
                continue
            nonempty = [s for s in messages if isinstance(s, str) and s.strip()]
            if conclusion != "failure" or not nonempty or any(not billing_message(s) for s in nonempty):
                gaps.append(f"nonbilling or conflicting failure: {name}")
            else:
                print(f"BILLING SIGNAL: {name} ({duration:g}s)")
        elif conclusion not in ("success", "neutral", "skipped"):
            gaps.append(f"unknown conclusion: {name}")
    status_list = statuses.get("statuses")
    if not isinstance(status_list, list) or statuses.get("sha") != sha:
        gaps.append("commit status contexts unavailable or stale")
    else:
        by_context = {s.get("context"): s.get("state") for s in status_list if isinstance(s, dict)}
        for name in contexts:
            if name not in by_context and not any(r.get("name") == name for r in checks if isinstance(r, dict)):
                gaps.append(f"missing required status context: {name}")
            if name in by_context and by_context[name] != "success":
                gaps.append(f"required status not successful: {name}")
        if any(s.get("state") in ("failure", "error", "pending") for s in status_list if isinstance(s, dict)):
            gaps.append("failing/pending commit status")
    if not any(isinstance(r, dict) and r.get("conclusion") == "failure" for r in checks):
        gaps.append("no failed billing checks")
    return gaps


def main(argv: list[str]) -> int:
    if len(argv) != 3 or not IDENTITY.fullmatch(argv[0]) or not IDENTITY.fullmatch(argv[1]) or not argv[2].isdigit() or int(argv[2]) < 1:
        print("Usage: verify-billing-block.sh <owner> <repo> <positive-pr-number>")
        return 1
    owner, repo, number = argv
    scope = f"{owner}/{repo}"
    print(f"DIAGNOSTIC ONLY: {scope} PR #{number}; no project allowlist or PR-specific operator approval is provided here")
    try:
        pr = gh("pr", "view", number, "--repo", scope, "--json", "headRefOid,baseRefName,reviewDecision")
        sha, base = pr["headRefOid"], pr["baseRefName"]
        if not SHA.fullmatch(sha) or not IDENTITY.fullmatch(base):
            raise ValueError("invalid head or base")
        runs = gh("api", f"repos/{scope}/commits/{sha}/check-runs?per_page=100", "--paginate", "--slurp")
        if not isinstance(runs, list) or not runs or any(not isinstance(p, dict) for p in runs):
            raise ValueError("incomplete check-run pagination")
        # Every page reports the same total_count; require that all pages add up.
        all_runs = [r for p in runs for r in p.get("check_runs", [])]
        if any(p.get("total_count") != runs[0].get("total_count") for p in runs):
            raise ValueError("inconsistent pagination totals")
        required = gh("api", f"repos/{scope}/branches/{base}/protection/required_status_checks")
        statuses = gh("api", f"repos/{scope}/commits/{sha}/status")
        annotations = {}
        for run in all_runs:
            if run.get("conclusion") in ("failure", "timed_out", "cancelled", "action_required"):
                annotations[run["id"]] = gh("api", f"repos/{scope}/check-runs/{run['id']}/annotations", "--paginate", "--slurp")
                annotations[run["id"]] = [a for page in annotations[run["id"]] for a in page]
        latest = gh("pr", "view", number, "--repo", scope, "--json", "headRefOid,baseRefName,reviewDecision")
        gaps = evaluate(pr, {"check_runs": all_runs, "total_count": runs[0].get("total_count")}, required, statuses, annotations, latest)
        if latest.get("baseRefName") != base:
            gaps.append("base branch changed during inspection")
        for gap in gaps:
            print(f"GAP: {gap}")
        if not gaps:
            print("Observed check evidence has billing-only signals; this does not verify an override scope.")
    except (OSError, subprocess.SubprocessError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"GAP: verification unavailable: {exc}")
    print("GAP: exact project host/repo/path allowlist and PR-specific operator approval are not declared here")
    print("STOP: diagnostic only; NEVER authorizes --admin or protected-check bypass")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
