#!/usr/bin/env python3
"""Validate the compact safety kernel structure and hard size budgets."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path("skills/KERNEL.md")
DEFAULT_CATALOG = Path("catalog/kernel-budget.json")
DEFAULT_AUTHORITY = Path("catalog/generated-source-authority.json")
CHAR_LIMIT = 80_000
TOKEN_LIMIT = 20_000
FORMS = ("nested", "flat", "claude-code", "craft-agent")
REQUIRED_IDS = [f"K{i}" for i in range(1, 11)]
REQUIRED_BOUNDARY_TERMS = (
    "permission",
    "credential",
    "destructive",
    "branch topology",
    "exact-main deployment",
    "evidence",
)
PROHIBITED_SHELF_LOAD_MARKERS = ("[skill:shelves", "skills/shelves/")
SHELF_GLOBALIZATION = re.compile(
    r"(?:load|inject|include)\b.{0,60}\b(?:all\s+)?(?:reference\s+)?shelves?\b.{0,30}\b(?:globally|always|every\s+session)\b",
    flags=re.IGNORECASE | re.DOTALL,
)


def measure(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    return {
        "characters": len(text),
        "estimated_tokens": math.ceil(len(text) / 4),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def validate_text(text: str) -> list[str]:
    ids = re.findall(r"^## (K(?:10|[1-9])):", text, flags=re.MULTILINE)
    all_kernel_ids = re.findall(r"^## (K\d+)\b", text, flags=re.MULTILINE)
    if ids != REQUIRED_IDS or all_kernel_ids != REQUIRED_IDS:
        raise ValueError(
            "kernel invariant IDs must appear exactly once in order with '<ID>:' headings: "
            f"valid={ids}, all={all_kernel_ids}"
        )
    lowered = text.lower()
    if "always-loaded runtime constitution" not in lowered:
        raise ValueError("kernel must state the active progressive-loading runtime contract")
    if "non-overridable boundary" not in lowered:
        raise ValueError("kernel must declare the non-overridable boundary")
    missing = [term for term in REQUIRED_BOUNDARY_TERMS if term not in lowered]
    if missing:
        raise ValueError(f"kernel non-overridable boundary is incomplete: {missing}")
    prohibited = [marker for marker in PROHIBITED_SHELF_LOAD_MARKERS if marker in lowered]
    if prohibited or SHELF_GLOBALIZATION.search(text):
        raise ValueError(f"kernel must not load or embed shelf sources: {prohibited or ['global shelf instruction']}")
    return ids


def enforce_budget(label: str, metrics: dict[str, Any], char_limit: int, token_limit: int) -> None:
    if metrics["characters"] > char_limit:
        raise ValueError(f"{label} exceeds character budget: {metrics['characters']} > {char_limit}")
    if metrics["estimated_tokens"] > token_limit:
        raise ValueError(f"{label} exceeds token budget: {metrics['estimated_tokens']} > {token_limit}")


def build_catalog(
    root: Path,
    source_path: Path,
    char_limit: int = CHAR_LIMIT,
    token_limit: int = TOKEN_LIMIT,
    authority_path: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    raw_source = source_path
    try:
        rel_source = raw_source.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"kernel source must be inside repository: {raw_source}") from exc
    current = root
    for part in rel_source.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"kernel source path contains a symlink: {raw_source}")
    source_path = raw_source.resolve()
    if not source_path.is_relative_to(root) or not source_path.is_file():
        raise ValueError(f"kernel source must be a regular repository file: {source_path}")
    text = source_path.read_text()
    invariant_ids = validate_text(text)
    source_metrics = measure(source_path)
    enforce_budget("source", source_metrics, char_limit, token_limit)

    authority_artifacts: dict[str, Any] | None = None
    if authority_path is not None:
        authority = json.loads(authority_path.read_text())
        matches = [
            entry for entry in authority.get("support_artifacts", [])
            if entry.get("canonical_source") == "skills/KERNEL.md"
        ]
        if len(matches) != 1:
            raise ValueError("generated source authority must contain exactly one kernel support record")
        authority_artifacts = matches[0]["artifacts"]

    artifacts: dict[str, dict[str, Any]] = {}
    for form in FORMS:
        artifact = root / "dist" / form / "skills" / "KERNEL.md"
        if artifact.is_symlink() or not artifact.is_file():
            raise ValueError(f"generated kernel artifact is missing or symlinked: {artifact}")
        metrics = measure(artifact)
        enforce_budget(form, metrics, char_limit, token_limit)
        if authority_artifacts is not None:
            tree = hashlib.sha256()
            tree.update(b"KERNEL.md\0")
            tree.update(metrics["sha256"].encode("ascii"))
            tree.update(b"\n")
            expected = authority_artifacts.get(form, {}).get("tree_sha256")
            if tree.hexdigest() != expected:
                raise ValueError(f"generated kernel artifact differs from fresh-build authority: {form}")
        artifacts[form] = metrics

    return {
        "schema_version": 1,
        "runtime_state": "active; compact kernel globally mounted with deterministic progressive loading",
        "shelf_isolation_validation": "heuristic text guard; deterministic resolver enforcement belongs to progressive loading",
        "limits": {
            "characters": char_limit,
            "estimated_tokens": token_limit,
            "estimation": "ceil(decoded UTF-8 character count / 4)",
        },
        "required_invariants": invariant_ids,
        "source": {"path": source_path.relative_to(root).as_posix(), **source_metrics},
        "artifacts": artifacts,
    }


def serialize(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def verify_authority_fresh(root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(root / "bin" / "generated-source-authority.py"), "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=360,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout)[-4000:].strip()
        raise ValueError(f"fresh generated-source authority is required: {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--authority", type=Path, default=DEFAULT_AUTHORITY)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    source = args.source if args.source.is_absolute() else root / args.source
    catalog = args.catalog if args.catalog.is_absolute() else root / args.catalog
    authority = args.authority if args.authority.is_absolute() else root / args.authority
    try:
        verify_authority_fresh(root)
        expected = serialize(build_catalog(root, source, authority_path=authority))
    except (
        OSError,
        UnicodeError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"KERNEL BUDGET ERROR: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not catalog.is_file() or catalog.read_text() != expected:
            print("STALE kernel budget catalog", file=sys.stderr)
            print("Run a full build, then: python3 bin/kernel-budget.py", file=sys.stderr)
            return 1
        data = json.loads(expected)
        print(
            "kernel budget: current "
            f"({data['source']['characters']} chars, "
            f"{data['source']['estimated_tokens']} estimated tokens)"
        )
        return 0
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(expected)
    print(f"wrote {catalog.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
