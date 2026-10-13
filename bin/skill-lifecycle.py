#!/usr/bin/env python3
"""Validate skill/rule lifecycle metadata through an exact migration allowlist."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = Path("catalog/skills-inventory.json")
DEFAULT_ALLOWLIST = Path("catalog/skill-lifecycle-legacy.json")
DEFAULT_SCHEMA = Path("catalog/skill-lifecycle-schema.json")
DEFAULT_BOOTSTRAP = Path("catalog/skill-lifecycle-bootstrap.json")
DEFAULT_APPROVALS = Path("catalog/skill-lifecycle-approved-exceptions.json")
DEFAULT_COMPLETED = Path("catalog/skill-lifecycle-completed.json")
BOOTSTRAP_SHA256 = "73e79ea93b12f3f5e8c0c7b3aacc67c41ec79af51ae520355f9de1f231e93b1c"
INITIAL_POLICY_BASE = "c2f27d00ce1e507176814307ba2a9252d7448ff8"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STRUCTURAL_TIERS = {"project", "reference", "on-demand"}


def load_inventory_module(root: Path) -> Any:
    path = root / "bin" / "skill-inventory.py"
    spec = importlib.util.spec_from_file_location("lifecycle_inventory_module", path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def valid_date(value: str) -> bool:
    if not DATE_RE.match(value):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def evaluate_item(
    root: Path,
    item: dict[str, Any],
    inventory_module: Any,
    schema: dict[str, Any],
) -> dict[str, Any]:
    source_path = str(item["source_path"])
    if any(char in source_path for char in "*?[]") or Path(source_path).is_absolute() or ".." in Path(source_path).parts:
        raise ValueError(f"unsafe inventory source_path: {source_path}")
    source = (root / source_path).resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise ValueError(f"inventory source escapes root or is missing: {source_path}")
    metadata = inventory_module.frontmatter(inventory_module.read_text(source))
    required = set(schema["required"])
    properties = schema["properties"]
    valid_tiers = set(properties["tier"]["enum"])
    valid_statuses = set(properties["status"]["enum"])
    missing: list[str] = []
    invalid: list[str] = []

    is_project = item.get("kind") in {"project-skill", "project-rule"} and bool(item.get("project"))
    raw_tier = metadata.get("tier", "")
    declared_tier = raw_tier.strip() if isinstance(raw_tier, str) else ""
    structural_tier = "project" if is_project else ""
    tier = declared_tier or structural_tier
    tier_source = "frontmatter" if declared_tier else ("project" if structural_tier else "missing")
    if raw_tier and not isinstance(raw_tier, str):
        invalid.append("tier:type")
    elif declared_tier and declared_tier not in valid_tiers:
        invalid.append(f"tier:{declared_tier}")
    elif is_project and declared_tier and declared_tier != "project":
        invalid.append(f"tier-conflict:{declared_tier}")
    elif not tier and "tier" in required:
        missing.append("tier")

    raw_owner = metadata.get("owner", "")
    declared_owner = raw_owner.strip() if isinstance(raw_owner, str) else ""
    inherited_owners = [owner for owner in item.get("owner", []) if owner != "unknown"] if is_project else []
    owners = [declared_owner] if declared_owner else inherited_owners
    owner_source = "frontmatter" if declared_owner else ("project" if inherited_owners else "missing")
    if raw_owner and not isinstance(raw_owner, str):
        invalid.append("owner:type")
    if not owners:
        missing.append("owner")

    raw_status = metadata.get("status", "")
    status = raw_status.strip() if isinstance(raw_status, str) else ""
    if raw_status and not isinstance(raw_status, str):
        invalid.append("status:type")
    elif not status:
        missing.append("status")
    elif status not in valid_statuses:
        invalid.append(f"status:{status}")

    raw_last_reviewed = metadata.get("last-reviewed", "")
    last_reviewed = raw_last_reviewed.strip() if isinstance(raw_last_reviewed, str) else ""
    if raw_last_reviewed and not isinstance(raw_last_reviewed, str):
        invalid.append("last-reviewed:type")
    if not last_reviewed:
        missing.append("last-reviewed")
    elif not valid_date(last_reviewed):
        invalid.append(f"last-reviewed:{last_reviewed}")

    raw_verification = metadata.get("verification", "")
    verification = raw_verification.strip() if isinstance(raw_verification, str) else ""
    if raw_verification and not isinstance(raw_verification, str):
        invalid.append("verification:type")
    elif not verification:
        missing.append("verification")

    superseded_raw = metadata.get("superseded-by", "")
    rationale_raw = metadata.get("retirement-rationale", "")
    superseded_by = superseded_raw.strip() if isinstance(superseded_raw, str) else ""
    retirement_rationale = rationale_raw.strip() if isinstance(rationale_raw, str) else ""
    if status == "deprecated" and not superseded_by:
        missing.append("superseded-by")
    if status == "retired" and not (superseded_by or retirement_rationale):
        missing.append("superseded-by-or-retirement-rationale")

    return {
        "source_path": item["source_path"],
        "slug": item["slug"],
        "kind": item["kind"],
        "project": item.get("project"),
        "effective_tier": tier or "unknown",
        "tier_source": tier_source,
        "owners": owners,
        "owner_source": owner_source,
        "status": status or "unknown",
        "last_reviewed": last_reviewed or "unknown",
        "verification": verification or "unknown",
        "missing_fields": sorted(missing),
        "invalid_fields": sorted(invalid),
    }


def json_at_ref(root: Path, ref: str, path: str) -> dict[str, Any] | None:
    if not ref:
        raise ValueError("previous lifecycle reference is required")
    commit = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{ref}^{{commit}}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
    )
    if commit.returncode != 0:
        raise ValueError(f"previous lifecycle reference is unavailable: {ref}")
    result = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{path}"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def completed_paths_at_ref(root: Path, ref: str) -> set[str]:
    data = json_at_ref(root, ref, "catalog/skill-lifecycle-completed.json")
    return {entry["source_path"] for entry in data["entries"]} if data else set()


def gap_state_at_ref(root: Path, ref: str) -> dict[str, set[str]] | None:
    data = json_at_ref(root, ref, "catalog/skill-lifecycle-legacy.json")
    if data is None:
        return None
    return {
        entry["source_path"]: {
            *(f"missing:{field}" for field in entry["missing_fields"]),
            *(f"invalid:{field}" for field in entry["invalid_fields"]),
        }
        for entry in data["entries"]
    }


def build_allowlist(
    root: Path,
    inventory_path: Path,
    schema_path: Path,
    bootstrap_path: Path,
    approvals_path: Path,
    completed_path: Path,
    verify_inventory: bool = True,
    enforce_bootstrap_digest: bool = True,
    previous_completed_paths: set[str] | None = None,
    previous_gap_state: dict[str, set[str]] | None = None,
    allow_initial_bootstrap: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    inventory = read_json(inventory_path)
    module = load_inventory_module(root)
    if verify_inventory:
        current_json, _ = module.serialized(module.build_inventory(root))
        if inventory_path.read_text() != current_json:
            raise ValueError("skill inventory is stale; run python3 bin/skill-inventory.py")
    schema = read_json(schema_path)
    if enforce_bootstrap_digest:
        digest = hashlib.sha256(bootstrap_path.read_bytes()).hexdigest()
        if digest != BOOTSTRAP_SHA256:
            raise ValueError(
                f"lifecycle bootstrap digest changed: {digest}; expected {BOOTSTRAP_SHA256}"
            )
    bootstrap = set(read_json(bootstrap_path)["source_paths"])
    approval_data = read_json(approvals_path)
    approvals = {entry["source_path"]: entry for entry in approval_data["entries"]}
    for path, approval in approvals.items():
        approved_gaps = approval.get("approved_gaps")
        if (
            not approval.get("reason")
            or not approval.get("approval_reference")
            or not valid_date(str(approval.get("approved_on", "")))
            or not isinstance(approved_gaps, list)
            or not approved_gaps
            or len(approved_gaps) != len(set(approved_gaps))
            or not all(isinstance(gap, str) and re.match(r"^(missing|invalid):.+", gap) for gap in approved_gaps)
        ):
            raise ValueError(f"invalid approved lifecycle exception: {path}")
    completed_data = read_json(completed_path)
    completed = {entry["source_path"]: entry for entry in completed_data["entries"]}
    prior_completed = previous_completed_paths or set()
    removed_completions = sorted(prior_completed - set(completed))
    if removed_completions:
        raise ValueError(f"completed lifecycle registry is append-only; removed: {removed_completions}")
    for path, record in completed.items():
        if path not in bootstrap:
            raise ValueError(f"completed migration was not a bootstrap path: {path}")
        if not record.get("completion_reference") or not valid_date(str(record.get("completed_on", ""))):
            raise ValueError(f"invalid completed lifecycle migration: {path}")
    evaluations = [evaluate_item(root, item, module, schema) for item in inventory["items"]]
    gaps = [result for result in evaluations if result["missing_fields"] or result["invalid_fields"]]
    gap_paths = {result["source_path"] for result in gaps}
    gap_state = {
        result["source_path"]: {
            *(f"missing:{field}" for field in result["missing_fields"]),
            *(f"invalid:{field}" for field in result["invalid_fields"]),
        }
        for result in gaps
    }
    mismatched_approvals = {
        path: {
            "approved_gaps": sorted(approval["approved_gaps"]),
            "current_gaps": sorted(gap_state.get(path, set())),
        }
        for path, approval in approvals.items()
        if set(approval["approved_gaps"]) != gap_state.get(path, set())
    }
    if mismatched_approvals:
        raise ValueError(f"approved lifecycle exceptions must bind the exact current gap set: {mismatched_approvals}")
    evaluation_paths = {result["source_path"] for result in evaluations}
    invalid_new_completions = sorted(
        path for path in (set(completed) - prior_completed)
        if path not in evaluation_paths or path in gap_paths
    )
    if invalid_new_completions:
        raise ValueError(
            "new completed migrations must still exist and be metadata-complete: "
            f"{invalid_new_completions}"
        )
    if previous_gap_state is None and not allow_initial_bootstrap:
        raise ValueError("previous lifecycle gap report is missing outside the initial bootstrap")
    if previous_gap_state is not None:
        expansions: dict[str, list[str]] = {}
        for result in gaps:
            current = {
                *(f"missing:{field}" for field in result["missing_fields"]),
                *(f"invalid:{field}" for field in result["invalid_fields"]),
            }
            added = sorted(current - previous_gap_state.get(result["source_path"], set()))
            if added and result["source_path"] not in approvals:
                expansions[result["source_path"]] = added
        if expansions:
            raise ValueError(f"lifecycle exception gap sets expanded without approval: {expansions}")
    regressions = sorted(gap_paths & set(completed))
    if regressions:
        raise ValueError(f"completed lifecycle metadata regressed: {regressions}")
    unrecorded_completions = sorted((bootstrap - gap_paths) - set(completed))
    if unrecorded_completions:
        raise ValueError(
            f"completed bootstrap migrations must be recorded before removing their exceptions: {unrecorded_completions}"
        )
    unapproved = sorted(result["source_path"] for result in gaps if result["source_path"] not in bootstrap and result["source_path"] not in approvals)
    if unapproved:
        raise ValueError(f"new lifecycle gaps require explicit approval records: {unapproved}")
    stale_approvals = sorted(set(approvals) - gap_paths)
    if stale_approvals:
        raise ValueError(f"stale approved lifecycle exceptions: {stale_approvals}")
    entries = [
        {
            "source_path": result["source_path"],
            "missing_fields": result["missing_fields"],
            "invalid_fields": result["invalid_fields"],
            "exception_origin": (
                {"kind": "bootstrap", "reference": read_json(bootstrap_path)["baseline_reference"]}
                if result["source_path"] in bootstrap
                else {"kind": "approved", **approvals[result["source_path"]]}
            ),
        }
        for result in gaps
    ]
    entries.sort(key=lambda entry: entry["source_path"])
    return {
        "schema_version": 1,
        "policy": {
            "exact_paths_only": True,
            "wildcards_allowed": False,
            "stale_entries_fail": True,
            "new_unlisted_gaps_fail": True,
            "note": "Temporary migration ratchet; bootstrap paths are historical and future gaps require explicit approval records.",
        },
        "summary": {
            "authoritative_item_count": len(evaluations),
            "metadata_complete_count": len(evaluations) - len(entries),
            "legacy_exception_count": len(entries),
        },
        "entries": entries,
    }


def serialize(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--bootstrap", type=Path, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--approvals", type=Path, default=DEFAULT_APPROVALS)
    parser.add_argument("--completed", type=Path, default=DEFAULT_COMPLETED)
    parser.add_argument("--previous-ref", default=os.environ.get("LIFECYCLE_PREVIOUS_REF", ""))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    inventory_path = args.inventory if args.inventory.is_absolute() else root / args.inventory
    allowlist_path = args.allowlist if args.allowlist.is_absolute() else root / args.allowlist
    schema_path = args.schema if args.schema.is_absolute() else root / args.schema
    bootstrap_path = args.bootstrap if args.bootstrap.is_absolute() else root / args.bootstrap
    approvals_path = args.approvals if args.approvals.is_absolute() else root / args.approvals
    completed_path = args.completed if args.completed.is_absolute() else root / args.completed
    previous_ref = args.previous_ref
    if not previous_ref:
        try:
            previous_ref = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD^"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
        except (OSError, subprocess.SubprocessError):
            previous_ref = ""
    try:
        previous_completed = completed_paths_at_ref(root, previous_ref)
        previous_gaps = gap_state_at_ref(root, previous_ref)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"SKILL LIFECYCLE ERROR: {exc}", file=sys.stderr)
        return 1
    initial_bootstrap = previous_ref == INITIAL_POLICY_BASE
    try:
        expected = serialize(build_allowlist(
            root,
            inventory_path,
            schema_path,
            bootstrap_path,
            approvals_path,
            completed_path,
            verify_inventory=True,
            enforce_bootstrap_digest=True,
            previous_completed_paths=previous_completed,
            previous_gap_state=previous_gaps,
            allow_initial_bootstrap=initial_bootstrap,
        ))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"SKILL LIFECYCLE ERROR: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not allowlist_path.exists() or allowlist_path.read_text() != expected:
            print("STALE skill lifecycle legacy allowlist", file=sys.stderr)
            print("Run: python3 bin/skill-lifecycle.py", file=sys.stderr)
            return 1
        data = json.loads(expected)
        print(
            "skill lifecycle: current "
            f"({data['summary']['metadata_complete_count']} complete, "
            f"{data['summary']['legacy_exception_count']} legacy exceptions)"
        )
        return 0
    allowlist_path.parent.mkdir(parents=True, exist_ok=True)
    allowlist_path.write_text(expected)
    print(f"wrote {allowlist_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
