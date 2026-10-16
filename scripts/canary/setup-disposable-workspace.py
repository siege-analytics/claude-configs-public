#!/usr/bin/env python3
"""Install one approved canary payload into its exact disposable workspace.

This is not a general installer. It accepts only the immutable #1003 manifest,
materialized payload and workspace paths, creates no production deploy stamp,
and registers native hooks only in the packet's local fixture repository.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CANARY_PATH = HERE / "craft-backend-canary.py"
RESIDENT_ADAPTER_PATH = HERE / "inject-composed-resident.sh"
ALLOWED_PAYLOAD_ENTRIES = {
    ".githooks",
    "CLAUDE.md",
    "KERNEL.md",
    "RESOLVER.md",
    "RULES_BUNDLE.md",
    "bin",
    "catalog",
    "composition.json",
    "enforcement-manifest.json",
    "hooks",
    "skills",
}


def load_canary() -> Any:
    spec = importlib.util.spec_from_file_location("craft_backend_canary_setup", CANARY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canary validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def validate_payload(canary: Any, payload: Path, expected_digest: str) -> None:
    if not payload.is_dir() or payload.is_symlink():
        raise canary.PacketError("workspace payload is absent or symlinked")
    entries = {path.name for path in payload.iterdir()}
    if entries != ALLOWED_PAYLOAD_ENTRIES:
        raise canary.PacketError(
            f"workspace payload allowlist mismatch: missing={sorted(ALLOWED_PAYLOAD_ENTRIES - entries)} "
            f"unexpected={sorted(entries - ALLOWED_PAYLOAD_ENTRIES)}"
        )
    if (payload / "deploy-stamp.json").exists():
        raise canary.PacketError("disposable payload must not contain a production deploy stamp")
    for path in payload.rglob("*"):
        if path.is_symlink() and not (path == payload / "CLAUDE.md" and os.readlink(path) == "KERNEL.md"):
            raise canary.PacketError(f"unsupported payload symlink: {path.relative_to(payload)}")
    if canary.tree_digest(payload) != expected_digest:
        raise canary.PacketError("workspace payload differs from approved exact digest")


def copy_payload(canary: Any, payload: Path, workspace: Path) -> None:
    for source in sorted(payload.iterdir(), key=lambda path: path.name):
        target = workspace / source.name
        if target.exists() or target.is_symlink():
            raise canary.PacketError(f"refusing existing workspace payload target: {target}")
    for source in sorted(payload.iterdir(), key=lambda path: path.name):
        target = workspace / source.name
        if source.is_symlink():
            target.symlink_to(os.readlink(source))
        elif source.is_dir():
            shutil.copytree(source, target, symlinks=True)
        else:
            shutil.copy2(source, target)


def register_resident_adapter(canary: Any, manifest: dict[str, Any], workspace: Path) -> tuple[Path, str]:
    expected = manifest["pins"]["workspace_resident_adapter_sha256"]
    if canary.sha256_bytes(RESIDENT_ADAPTER_PATH.read_bytes()) != expected:
        raise canary.PacketError("resident adapter differs from approved exact digest")
    target = workspace / "hooks/resolver/cc1003-inject-composed-resident.sh"
    if target.exists() or target.is_symlink():
        raise canary.PacketError("refusing pre-existing resident adapter target")
    shutil.copy2(RESIDENT_ADAPTER_PATH, target)
    target.chmod(0o755)
    settings_path = workspace / ".claude/settings.json"
    settings = canary.load_json(settings_path)
    canonical = str(workspace / "hooks/resolver/inject-resolver.sh")
    replacement = str(target)
    replaced = 0
    for entry in settings.get("hooks", {}).get("UserPromptSubmit", []):
        for hook in entry.get("hooks", []):
            if hook.get("command") == canonical:
                hook["command"] = replacement
                replaced += 1
    if replaced != 1:
        raise canary.PacketError(f"expected exactly one canonical resolver registration, found {replaced}")
    settings_path.write_bytes(canary.canonical_bytes(settings))
    return target, replacement


def probe_registered_resident(canary: Any, manifest: dict[str, Any], workspace: Path, fixture: Path, command: str) -> dict[str, Any]:
    settings = canary.load_json(workspace / ".claude/settings.json")
    commands = [
        hook.get("command")
        for entry in settings.get("hooks", {}).get("UserPromptSubmit", [])
        for hook in entry.get("hooks", [])
        if isinstance(hook, dict)
    ]
    if commands.count(command) != 1:
        raise canary.PacketError("resident adapter is not registered exactly once")
    payload = canary.canonical_bytes({"prompt": "review candidate strict release checks", "cwd": str(fixture)})
    result = subprocess.run(
        shlex.split(command), cwd=fixture, input=payload, capture_output=True, check=False, timeout=60,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode:
        raise canary.PacketError(f"registered resident adapter failed: {result.stderr.decode(errors='replace').strip()}")
    output = result.stdout.decode("utf-8")
    marker = manifest["fixture"]["resident_marker"]
    if output.count(marker) != 1:
        raise canary.PacketError(f"registered resident marker count is {output.count(marker)}, expected 1")
    for expected in ("project: strict-release", "strict-release--review", "strict-release--checks"):
        if expected not in output:
            raise canary.PacketError(f"registered resident output lacks {expected}")
    for forbidden in ("FOREIGN_PROJECT_CONTROL_MUST_NOT_BE_INJECTED", "GLOBAL_BUNDLE_CONTROL_MUST_NOT_BE_INJECTED"):
        if forbidden in output:
            raise canary.PacketError("registered resident output contains a negative-control marker")
    return {
        "command": command,
        "command_count": 1,
        "output_sha256": canary.sha256_bytes(result.stdout),
        "resident_marker_count": 1,
        "selected_project": "strict-release",
        "selected_skills": ["strict-release--review", "strict-release--checks"],
        "negative_controls_absent": True,
        "authorization_effect": "none",
    }


def run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, timeout=180)
    if result.returncode:
        raise RuntimeError(
            f"setup command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    canary = load_canary()
    try:
        manifest = canary.load_json(args.manifest)
        facts = canary.validate_manifest(manifest, require_approval_record=True)
        source: Path = facts["source_root"]
        payload = facts["temp_root"] / "workspace-payload"
        workspace: Path = facts["workspace_root"]
        fixture = facts["temp_root"] / "fixture" / "repo"
        validate_payload(canary, payload, manifest["pins"]["workspace_payload_tree_sha256"])
        if not workspace.is_dir() or workspace.is_symlink() or workspace.resolve() != workspace:
            raise canary.PacketError("exact disposable workspace must already exist as a real directory")
        if not fixture.is_dir() or fixture.is_symlink():
            raise canary.PacketError("exact disposable fixture repository is absent")
        if (workspace / "deploy-stamp.json").exists():
            raise canary.PacketError("refusing workspace with a production deploy stamp")
        copy_payload(canary, payload, workspace)
        outputs = []
        outputs.append(run([
            "bash", "bin/install-hooks.sh", "--workspace", str(workspace),
            "--hooks-root", str(workspace), "--git-repo", str(fixture),
        ], cwd=source))
        outputs.append(run([
            sys.executable, "bin/wire-enforcement.py", "--workspace", str(workspace),
            "--dist", str(source / "dist"),
        ], cwd=source))
        outputs.append(run([
            "bash", "bin/verify-enforcement.sh", "--target", str(workspace),
            "--mode", "craft-agent", "--git-repo", str(fixture),
        ], cwd=source))
        adapter, registered_command = register_resident_adapter(canary, manifest, workspace)
        registered_probe = probe_registered_resident(canary, manifest, workspace, fixture, registered_command)
        if (workspace / "deploy-stamp.json").exists():
            raise canary.PacketError("disposable setup created a forbidden production deploy stamp")
        receipt = {
            "schema_version": canary.SCHEMA_VERSION,
            "run_id": facts["run_id"],
            "manifest_sha256": facts["manifest_sha256"],
            "workspace": str(workspace),
            "fixture": str(fixture),
            "fixture_identity": manifest["fixture"]["canonical_identity"],
            "workspace_payload_tree_sha256": canary.tree_digest(payload),
            "resident_adapter_sha256": canary.sha256_bytes(adapter.read_bytes()),
            "registered_resident_probe": registered_probe,
            "production_deploy_stamp": False,
            "standing_order_automations_enabled": False,
            "authorization_effect": "none",
            "command_output_sha256": canary.sha256_bytes("\n".join(outputs).encode()),
        }
        destination = facts["evidence_root"] / "workspace-setup.json"
        destination.write_bytes(canary.canonical_bytes(receipt))
        print(json.dumps({
            "status": "disposable-workspace-configured-unverified",
            "authorization_effect": "none",
            "receipt": str(destination),
            "receipt_sha256": canary.sha256_bytes(destination.read_bytes()),
        }, sort_keys=True))
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, canary.PacketError, ValueError, TypeError) as exc:
        print(f"CANARY SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
