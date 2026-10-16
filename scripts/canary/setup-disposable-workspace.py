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
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
CANARY_PATH = HERE / "craft-backend-canary.py"
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
