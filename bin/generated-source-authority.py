#!/usr/bin/env python3
"""Generate or check canonical-source to generated-artifact authority hashes.

Requires a completed ``python3 bin/build.py``. This command never builds or
repairs dist: missing, extra, colliding, or divergent consumer artifacts fail.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = Path("catalog/skills-inventory.json")
DEFAULT_CATALOG = Path("catalog/generated-source-authority.json")
FORMS = ("nested", "flat", "claude-code", "craft-agent")
SUPPORT_SOURCES = {
    "skills/KERNEL.md": "KERNEL.md",
    "skills/RULES.md": "RULES.md",
    "skills/_coverage.md": "_coverage.md",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def safe_repo_path(root: Path, value: str, *, must_exist: bool = True) -> Path:
    rel = Path(value)
    if rel.is_absolute() or ".." in rel.parts or any(c in value for c in "*?[]"):
        raise ValueError(f"unsafe authority path: {value}")
    raw = root / rel
    current = root
    for part in rel.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"authority path contains a symlink: {value}")
    path = raw.resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"authority path escapes repository: {value}")
    if must_exist and not path.exists():
        raise ValueError(f"authority path is missing: {value}")
    return path


def generated_path(dist_root: Path, value: str, form: str) -> Path:
    rel = Path(value)
    expected = ("dist", form, "skills")
    if (
        rel.is_absolute()
        or ".." in rel.parts
        or any(c in value for c in "*?[]")
        or len(rel.parts) < 4
        or rel.parts[:3] != expected
    ):
        raise ValueError(f"generated destination must be under dist/{form}/skills: {value}")
    relative = Path(*rel.parts[1:])
    raw = dist_root / relative
    current = dist_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated destination contains a symlink: {value}")
    resolved = raw.resolve()
    form_root = (dist_root / form / "skills").resolve()
    if not resolved.is_relative_to(form_root):
        raise ValueError(f"generated destination escapes {form} skills root: {value}")
    if not resolved.exists():
        raise ValueError(f"generated destination is missing: {value}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_hash(files: list[tuple[str, Path]]) -> str:
    digest = hashlib.sha256()
    for rel, path in sorted(files):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def source_owned_files(source: Path) -> tuple[Path, list[tuple[str, Path]]]:
    """Return source root and files, excluding nested child-skill subtrees."""
    if source.name != "SKILL.md":
        return source.parent, [(source.name, source)]
    source_root = source.parent
    nested_roots = {
        candidate.parent.resolve()
        for candidate in source_root.rglob("SKILL.md")
        if candidate.resolve() != source.resolve()
    }
    files: list[tuple[str, Path]] = []
    for candidate in sorted(source_root.rglob("*")):
        if candidate.is_symlink():
            raise ValueError(f"canonical source contains a symlink: {candidate}")
        if not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if any(resolved.is_relative_to(nested) for nested in nested_roots):
            continue
        files.append((candidate.relative_to(source_root).as_posix(), candidate))
    if not files or "SKILL.md" not in {rel for rel, _ in files}:
        raise ValueError(f"canonical skill has no owned SKILL.md: {source}")
    return source_root, files


def output_files(destination: Path, source_files: list[tuple[str, Path]]) -> list[tuple[str, Path]]:
    if destination.is_symlink():
        raise ValueError(f"generated destination is a symlink: {destination}")
    if destination.is_file():
        if len(source_files) != 1:
            raise ValueError(f"file destination cannot represent multiple source files: {destination}")
        return [(destination.name, destination)]
    if not destination.is_dir():
        raise ValueError(f"generated destination is missing: {destination}")
    outputs: list[tuple[str, Path]] = []
    for rel, _ in source_files:
        candidate = destination / rel
        if candidate.is_symlink():
            raise ValueError(f"generated output is a symlink: {candidate}")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(destination.resolve()):
            raise ValueError(f"generated output escapes destination: {candidate}")
        if not candidate.is_file():
            raise ValueError(f"generated output is missing: {candidate}")
        outputs.append((rel, candidate))
    return outputs


def consumer_destination_value(flat_value: str, consumer: str) -> str:
    prefix = "dist/flat/skills/"
    if not flat_value.startswith(prefix):
        raise ValueError(f"flat generated destination has unexpected shape: {flat_value}")
    return f"dist/{consumer}/skills/{flat_value[len(prefix):]}"


def build_catalog(root: Path, inventory_path: Path, dist_path: Path) -> dict[str, Any]:
    root = root.resolve()
    dist_path = dist_path.resolve()
    if not dist_path.is_dir():
        raise ValueError(f"completed isolated build is required: {dist_path}")
    inventory = read_json(inventory_path)
    items = inventory["items"]
    if inventory["diagnostics"]["discovery_parity"]["status"] != "matched":
        raise ValueError("inventory discovery parity is not matched")
    if inventory["diagnostics"]["generated_output_plan"]["status"] != "derived-from-build.py":
        raise ValueError("inventory generated output plan is not authoritative")

    records: list[dict[str, Any]] = []
    claimed_outputs: dict[str, str] = {}
    source_paths: set[str] = set()
    total_source_files = 0
    total_output_files = 0

    for item in sorted(items, key=lambda value: value["canonical_source"]):
        source_value = item["canonical_source"]
        if source_value in source_paths:
            raise ValueError(f"duplicate canonical source: {source_value}")
        source_paths.add(source_value)
        source = safe_repo_path(root, source_value)
        _, owned = source_owned_files(source)
        total_source_files += len(owned)

        destinations = item["generated_outputs"]
        if len(destinations) != 2:
            raise ValueError(f"canonical source must have nested and flat destinations: {source_value}")
        by_layout = {Path(value).parts[1]: value for value in destinations}
        if set(by_layout) != {"nested", "flat"}:
            raise ValueError(f"unexpected generated layouts for {source_value}: {sorted(by_layout)}")

        form_values = {
            "nested": by_layout["nested"],
            "flat": by_layout["flat"],
            "claude-code": consumer_destination_value(by_layout["flat"], "claude-code"),
            "craft-agent": consumer_destination_value(by_layout["flat"], "craft-agent"),
        }
        artifacts: dict[str, dict[str, Any]] = {}
        for form in FORMS:
            destination = generated_path(dist_path, form_values[form], form)
            generated = output_files(destination, owned)
            for _, output in generated:
                output_value = f"dist/{output.relative_to(dist_path).as_posix()}"
                prior = claimed_outputs.get(output_value)
                if prior and prior != source_value:
                    raise ValueError(
                        f"generated output collision: {output_value} claimed by {prior} and {source_value}"
                    )
                claimed_outputs[output_value] = source_value
            total_output_files += len(generated)
            artifacts[form] = {
                "destination": form_values[form],
                "file_count": len(generated),
                "tree_sha256": tree_hash(generated),
            }
        records.append({
            "canonical_source": source_value,
            "kind": item["kind"],
            "slug": item["slug"],
            "source_file_count": len(owned),
            "source_tree_sha256": tree_hash(owned),
            "artifacts": artifacts,
        })

    expected_count = inventory["diagnostics"]["discovery_parity"]["source_count"]
    if len(records) != expected_count:
        raise ValueError(f"authority source count {len(records)} != inventory count {expected_count}")

    support_records: list[dict[str, Any]] = []
    for source_value, output_name in sorted(SUPPORT_SOURCES.items()):
        source = safe_repo_path(root, source_value)
        owned = [(source.name, source)]
        total_source_files += 1
        artifacts: dict[str, dict[str, Any]] = {}
        for form in FORMS:
            output_value = f"dist/{form}/skills/{output_name}"
            destination = generated_path(dist_path, output_value, form)
            generated = output_files(destination, owned)
            logical_file = f"dist/{generated[0][1].relative_to(dist_path).as_posix()}"
            prior = claimed_outputs.get(logical_file)
            if prior:
                raise ValueError(
                    f"generated output collision: {logical_file} claimed by {prior} and {source_value}"
                )
            claimed_outputs[logical_file] = source_value
            total_output_files += 1
            artifacts[form] = {
                "destination": output_value,
                "file_count": 1,
                "tree_sha256": tree_hash(generated),
            }
        support_records.append({
            "canonical_source": source_value,
            "source_file_count": 1,
            "source_tree_sha256": tree_hash(owned),
            "artifacts": artifacts,
        })

    unowned: list[str] = []
    for form in FORMS:
        skills_root = dist_path / form / "skills"
        if not skills_root.is_dir():
            raise ValueError(f"generated skills root is missing: {skills_root}")
        for candidate in sorted(skills_root.rglob("*")):
            if candidate.is_symlink():
                raise ValueError(f"generated skills tree contains a symlink: {candidate}")
            if not candidate.is_file():
                continue
            value = f"dist/{candidate.relative_to(dist_path).as_posix()}"
            if value not in claimed_outputs:
                unowned.append(value)
    if unowned:
        raise ValueError(f"generated skill/rule files lack canonical owners: {unowned}")

    return {
        "schema_version": 1,
        "authority": {
            "canonical_source": "catalog/skills-inventory.json backed by bin/build.py discovery",
            "generated_artifacts_are_authoring_sources": False,
            "consumer_packages_are_build_derived": True,
            "consumer_transformations_may_change_bytes": True,
            "wildcards_allowed": False,
        },
        "summary": {
            "canonical_source_count": len(records),
            "support_source_count": len(support_records),
            "source_owned_file_count": total_source_files,
            "artifact_snapshot_count": (len(records) + len(support_records)) * len(FORMS),
            "generated_file_mapping_count": total_output_files,
            "destination_collision_count": 0,
            "unowned_generated_file_count": 0,
        },
        "items": records,
        "support_artifacts": support_records,
    }


def serialize(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def build_fresh_catalog(root: Path, inventory_path: Path) -> dict[str, Any]:
    inventory_check = subprocess.run(
        [sys.executable, str(root / "bin" / "skill-inventory.py"), "--check"],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=120,
    )
    if inventory_check.returncode != 0:
        detail = (inventory_check.stderr or inventory_check.stdout).strip()
        raise ValueError(f"authoritative inventory is stale: {detail}")
    with tempfile.TemporaryDirectory(prefix="generated-source-authority-") as td:
        fresh_dist = Path(td).resolve()
        build = subprocess.run(
            [sys.executable, str(root / "bin" / "build.py"), "--dist", str(fresh_dist)],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=300,
        )
        if build.returncode != 0:
            detail = (build.stderr or build.stdout)[-4000:].strip()
            raise ValueError(f"fresh isolated build failed: {detail}")
        return build_catalog(root, inventory_path, fresh_dist)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    inventory_path = args.inventory if args.inventory.is_absolute() else root / args.inventory
    catalog_path = args.catalog if args.catalog.is_absolute() else root / args.catalog
    try:
        expected = serialize(build_fresh_catalog(root, inventory_path))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"GENERATED SOURCE AUTHORITY ERROR: {exc}", file=sys.stderr)
        return 1
    if args.check:
        if not catalog_path.is_file() or catalog_path.read_text() != expected:
            print("STALE generated source authority catalog", file=sys.stderr)
            print("Run a full build, then: python3 bin/generated-source-authority.py", file=sys.stderr)
            return 1
        data = json.loads(expected)
        summary = data["summary"]
        print(
            "generated source authority: current "
            f"({summary['canonical_source_count']} sources, "
            f"{summary['artifact_snapshot_count']} artifact snapshots, "
            f"{summary['generated_file_mapping_count']} generated file mappings)"
        )
        return 0
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(expected)
    print(f"wrote {catalog_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
