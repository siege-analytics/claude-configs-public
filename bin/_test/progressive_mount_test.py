#!/usr/bin/env python3
"""Regression tests for the compact-kernel Craft Agent auto-mount."""
import importlib.util
import io
import json
import os
import subprocess
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
        (migrated / ".claude").mkdir()
        (migrated / ".claude" / "settings.json").write_text("{}\n")
        (migrated / "CLAUDE.md").symlink_to("RULES_BUNDLE.md")
        deploy(migrated)
        assert (migrated / "CLAUDE.md").is_symlink()
        assert (migrated / "CLAUDE.md").readlink() == Path("KERNEL.md")
        assert (migrated / "KERNEL.md").is_file()
        assert (migrated / "RULES_BUNDLE.md").is_file()
        assert (migrated / "bin" / "review-risk.py").is_file()
        assert (migrated / "catalog" / "review-risk-policy.json").is_file()
        assert (migrated / "bin" / "resolve-load-set.py").is_file()
        assert (migrated / "catalog" / "resolver-manifest.json").is_file()
        manifest = migrated / "hooks" / "enforcement-manifest.json"
        assert manifest.read_bytes() == (migrated / "enforcement-manifest.json").read_bytes()
        policy = subprocess.run(
            ["bash", "-c", '. "$1"; gate_runtime_policy_strict think-gate craft',
             "registry-probe", str(migrated / "hooks/lib/gate-registry.sh")],
            text=True, capture_output=True, check=True,
            env={key: value for key, value in os.environ.items()
                 if key != "CCP_ENFORCEMENT_MANIFEST"},
        )
        assert policy.stdout.strip() == "advisory", policy.stdout + policy.stderr
        hook = migrated / "hooks" / "resolver" / "inject-resolver.sh"
        routed = subprocess.run(
            ["bash", str(hook)],
            input=json.dumps({"prompt": "review this Python module", "cwd": str(migrated)}),
            text=True, capture_output=True, check=True,
        )
        assert "load: coding" in routed.stdout and "load: python" in routed.stdout
        boundary = subprocess.run(
            [sys.executable, str(migrated / "bin" / "resolve-load-set.py"),
             "--prompt", "[skill:merge] [skill:self-review]", "--repo", "other/repo"],
            text=True, capture_output=True, check=True,
        )
        boundary_result = json.loads(boundary.stdout)
        actual_characters = sum(
            len((migrated / "skills" / slug / "SKILL.md").read_text())
            for slug in ("merge", "self-review")
        )
        assert actual_characters > 80000
        assert boundary_result["state"] == "over-budget" and boundary_result["selected"] == []
        assert boundary_result["selected_content"]["characters"] == actual_characters
        verified = subprocess.run(
            ["bash", str(ROOT / "bin" / "verify-enforcement.sh"),
             "--target", str(migrated), "--mode", "craft-agent"],
            text=True, capture_output=True,
        )
        assert verified.returncode == 0, verified.stdout + verified.stderr

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
