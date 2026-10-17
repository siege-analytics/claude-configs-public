#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "kernel-budget.py"
SPEC = importlib.util.spec_from_file_location("kernel_budget", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def kernel(extra: str = "") -> str:
    headings = "\n".join(f"## K{i}: invariant {i}\nbody" for i in range(1, 11))
    return (
        "# Safety Kernel\n\nThis is the always-loaded runtime constitution.\n"
        "The non-overridable boundary covers permission, credential, destructive action, "
        "branch topology, exact-main deployment, and evidence.\n"
        f"{headings}\n{extra}"
    )


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def materialize(root: Path, content: str) -> Path:
    source = root / "skills/KERNEL.md"
    write(source, content)
    for form in MODULE.FORMS:
        write(root / "dist" / form / "skills/KERNEL.md", content)
    return source


def expect_failure(root: Path, source: Path, phrase: str, **kwargs) -> None:
    try:
        MODULE.build_catalog(root, source, **kwargs)
    except ValueError as exc:
        assert phrase in str(exc), str(exc)
    else:
        raise AssertionError(f"expected failure containing {phrase!r}")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        source = materialize(root, kernel())
        result = MODULE.build_catalog(root, source)
        assert result["required_invariants"] == MODULE.REQUIRED_IDS
        assert result["source"]["characters"] < result["limits"]["characters"]
        assert set(result["artifacts"]) == set(MODULE.FORMS)
        assert MODULE.serialize(result) == MODULE.serialize(MODULE.build_catalog(root, source))

        authority_artifacts = {}
        for form, metrics in result["artifacts"].items():
            digest = hashlib.sha256()
            digest.update(b"KERNEL.md\0")
            digest.update(metrics["sha256"].encode("ascii"))
            digest.update(b"\n")
            authority_artifacts[form] = {"tree_sha256": digest.hexdigest()}
        authority = root / "catalog/generated-source-authority.json"
        write(authority, json.dumps({"support_artifacts": [{
            "canonical_source": "skills/KERNEL.md",
            "artifacts": authority_artifacts,
        }]}) + "\n")
        assert MODULE.build_catalog(root, source, authority_path=authority)

        changed_artifact = root / "dist/claude-code/skills/KERNEL.md"
        changed_artifact.write_text(kernel("\nsemantic drift\n"))
        expect_failure(root, source, "differs from fresh-build authority", authority_path=authority)
        changed_artifact.write_text(kernel())

        write(source, kernel("\n## K10: duplicate\n"))
        expect_failure(root, source, "exactly once in order")

        write(source, kernel().replace("## K7:", "## X7:"))
        expect_failure(root, source, "exactly once in order")

        write(source, kernel("\n## K11: extra invariant\n"))
        expect_failure(root, source, "exactly once in order")

        write(source, kernel("\nLoad [skill:shelves--security] globally.\n"))
        expect_failure(root, source, "must not load or embed shelf")

        write(source, kernel("\nInclude all reference shelves in every session.\n"))
        expect_failure(root, source, "must not load or embed shelf")

        write(source, kernel())
        expect_failure(root, source, "exceeds character budget", char_limit=100, token_limit=20_000)
        expect_failure(root, source, "exceeds token budget", char_limit=80_000, token_limit=10)

        missing = root / "dist/craft-agent/skills/KERNEL.md"
        missing.unlink()
        expect_failure(root, source, "missing or symlinked")
        write(missing, kernel())

        external = root.parent / f"{root.name}-kernel.txt"
        external.write_text(kernel())
        missing.unlink()
        missing.symlink_to(external)
        expect_failure(root, source, "missing or symlinked")
        missing.unlink()
        external.unlink()

        authority_checker = root / "bin/generated-source-authority.py"
        write(authority_checker, "raise SystemExit(1)\n")
        try:
            MODULE.verify_authority_fresh(root)
        except ValueError as exc:
            assert "fresh generated-source authority is required" in str(exc)
        else:
            raise AssertionError("stale generated-source authority was accepted")
        write(authority_checker, "raise SystemExit(0)\n")
        MODULE.verify_authority_fresh(root)

        source_content = source.read_text()
        source.unlink()
        external_source = root.parent / f"{root.name}-source-kernel.md"
        external_source.write_text(source_content)
        source.symlink_to(external_source)
        expect_failure(root, source, "source path contains a symlink")
        source.unlink()
        external_source.unlink()

    print("kernel_budget_test: PASS")


if __name__ == "__main__":
    main()
