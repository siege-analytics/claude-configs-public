#!/usr/bin/env python3
"""Regression tests for the compact-kernel Craft Agent auto-mount."""
import importlib.util
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("progressive_build", ROOT / "bin" / "build.py")
build = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = build
spec.loader.exec_module(build)


def deploy(workspace: Path) -> None:
    with redirect_stdout(io.StringIO()):
        build.deploy_to_workspace(workspace)


def main() -> None:
    if not (ROOT / "dist" / "flat" / "skills" / "KERNEL.md").is_file():
        raise AssertionError("full build required before progressive mount test")
    with tempfile.TemporaryDirectory() as raw:
        base = Path(raw)

        migrated = base / "migrated"
        migrated.mkdir()
        (migrated / "CLAUDE.md").symlink_to("RULES_BUNDLE.md")
        deploy(migrated)
        assert (migrated / "CLAUDE.md").is_symlink()
        assert (migrated / "CLAUDE.md").readlink() == Path("KERNEL.md")
        assert (migrated / "KERNEL.md").is_file()
        assert (migrated / "RULES_BUNDLE.md").is_file()
        assert (migrated / "bin" / "review-risk.py").is_file()
        assert (migrated / "catalog" / "review-risk-policy.json").is_file()

        operator_link = base / "operator-link"
        operator_link.mkdir()
        (operator_link / "CLAUDE.md").symlink_to("CUSTOM.md")
        deploy(operator_link)
        assert (operator_link / "CLAUDE.md").readlink() == Path("CUSTOM.md")

        operator_file = base / "operator-file"
        operator_file.mkdir()
        (operator_file / "CLAUDE.md").write_text("operator policy\n")
        deploy(operator_file)
        assert (operator_file / "CLAUDE.md").read_text() == "operator policy\n"

    print("progressive_mount_test: PASS")


if __name__ == "__main__":
    main()
