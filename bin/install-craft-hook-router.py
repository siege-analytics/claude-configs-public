#!/usr/bin/env python3
"""Preview/install one host-scoped SDK bootstrap for an enrolled Craft workspace.

Policy remains at workspace/.claude/craft-settings.json, outside SDK discovery.
Only exact owned entries are replaced; other global/project hooks survive.
Activation is ordered, not multi-file atomic. The receipt becomes active last.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
ROUTER_SOURCE = "hooks/lib/craft-settings-router.py"
ANCHOR_SOURCE = "hooks/lib/session_anchor.py"


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


trust = load("bin/craft-workspace-trust.py", "craft_router_install_primitives")
router = load(ROUTER_SOURCE, "craft_router_registration_protocol")


def saved(path: Path):
    parent = path.parent
    while not parent.exists():
        if parent.is_symlink():
            raise ValueError("managed parent cannot be a dangling symlink")
        parent = parent.parent
    trust.physical_directory(parent)
    if not path.parent.exists():
        return {"raw": None, "fingerprint": None}
    return trust.snapshot(path, missing=True)


def source_bytes(revision: str, relative: str, *, apply: bool):
    return trust.reviewed_bytes(revision, relative) if apply else (ROOT / relative).read_bytes()


def managed_commands(policy: dict, workspace: Path) -> set[str]:
    """Exact commands from this policy, with a literal owned hooks executable."""
    return router.workspace_policy_commands(policy, workspace)


def retire_project(existing: dict, commands: set[str]) -> dict:
    result = copy.deepcopy(existing)
    hooks = result.get("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("legacy project hooks must be an object")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError("legacy project hook events must be arrays")
        retained = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError("legacy project hook group is malformed")
            kept = [hook for hook in group["hooks"] if not (isinstance(hook, dict) and hook.get("type") == "command" and hook.get("command") in commands)]
            if kept or set(group) - {"matcher", "hooks"}:
                retained.append({**group, "hooks": kept})
        hooks[event] = retained
    environment = result.get("env")
    if isinstance(environment, dict) and environment.get("CLAUDE_CA_ENFORCE") == "1":
        del environment["CLAUDE_CA_ENFORCE"]
        if not environment:
            del result["env"]
    return result


def merge_global(existing: dict, target: Path, workspace: Path, *, policy=None) -> dict:
    result = copy.deepcopy(existing)
    hooks = result.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError("global hooks must be an object")
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise ValueError("global hook events must be arrays")
        retained = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError("global hook group is malformed")
            kept = []
            for hook in group["hooks"]:
                if not isinstance(hook, dict):
                    raise ValueError("global hook entry is malformed")
                if hook.get("type") == "command" and (router.own_registration(hook.get("command"), target, workspace)
                        or router.legacy_own_registration(hook.get("command"), target, workspace)):
                    continue
                kept.append(hook)
            if kept or set(group) - {"matcher", "hooks"}:
                retained.append({**group, "hooks": kept})
        hooks[event] = retained
    for event in router.EVENTS:
        entry = {"hooks": [{"type": "command", "command": router.command_for(target, workspace, event), "timeout": 120}]}
        if event != "UserPromptSubmit":
            entry["matcher"] = ".*"
        hooks.setdefault(event, []).append(entry)
    router.verify_global(result, target, workspace, policy=policy)
    return result


def ensure_directories(home: Path, relative: Path):
    current = home
    for part in relative.parts:
        current = current / part
        if current.exists() or current.is_symlink():
            trust.physical_directory(current)
        else:
            current.mkdir(mode=0o700)


def private_backups(home: Path, snapshots: dict) -> Path:
    parent = home / ".claude/.craft-hook-router-backups"
    parent.mkdir(mode=0o700, exist_ok=True)
    trust.physical_directory(parent)
    if parent.stat().st_mode & 0o077:
        raise ValueError("router backup directory must be private (0700)")
    destination = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex)
    destination.mkdir(mode=0o700)
    metadata = {}
    for name, (path, snapshot) in snapshots.items():
        metadata[name] = {"path": str(path), "existed": snapshot["raw"] is not None}
        if snapshot["raw"] is not None:
            fd = os.open(destination / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as target:
                target.write(snapshot["raw"])
    fd = os.open(destination / "receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as target:
        json.dump(metadata, target, indent=2)
        target.write("\n")
    return destination


def publish(path: Path, before: dict, raw: bytes):
    """Publish with the shared version-preserving atomic exchange primitive."""
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix=".craft-router-stage-", dir=path.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(raw)
            target.flush()
            os.fsync(target.fileno())
        trust.publish_staged(path, before, staged)
    finally:
        staged.unlink(missing_ok=True)


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode()


def verify_registration(workspace: Path, home: Path):
    target = router.router_path(home, workspace)
    receipt, policy = router.registration(workspace, router_path_override=target)
    owned = managed_commands(policy, workspace)
    legacy = saved(workspace / ".claude/settings.json")
    if legacy["raw"] is not None:
        original = trust.document(legacy)
        if retire_project(original, owned) != original:
            raise ValueError("managed project registrations/environment remain in SDK auto-discovery")
    return {"local_registration_verified": True, "workspace": str(workspace), "router": str(target),
            "source_revision": receipt["source_revision"], "owned_event_count": len(router.EVENTS),
            "host_callback_delivery": "requires separate live allow/deny/no-op canaries"}


def install(workspace: Path, home: Path, *, apply=False):
    trust.physical_directory(home)
    trust.physical_directory(workspace)
    policy_path = workspace / ".claude/craft-settings.json"
    revision = trust.source_authority() if apply else None
    inspected = trust.inspect_workspace(workspace, revision, settings_file=policy_path)
    revision = revision or inspected["commit"]
    policy_snapshot = saved(policy_path)
    policy = trust.document(policy_snapshot)
    owned = managed_commands(policy, workspace)
    target = router.router_path(home, workspace)
    global_path = home / ".claude/settings.json"
    legacy_path = workspace / ".claude/settings.json"
    receipt_path = workspace / ".claude/craft-hook-registration.json"
    snapshots = {"global-settings.json": (global_path, saved(global_path)),
                 "legacy-project.json": (legacy_path, saved(legacy_path)),
                 "router.py": (target, saved(target)),
                 "registration.json": (receipt_path, saved(receipt_path))}
    old_router = snapshots["router.py"][1]["raw"]
    if old_router is not None and b"# Managed bootstrap: siege-craft-settings-router/v1\n" not in old_router.splitlines(keepends=True)[:3]:
        raise ValueError("router destination is operator-owned; refusing to overwrite it")
    merged = merge_global(trust.document(snapshots["global-settings.json"][1]), target, workspace, policy=policy)
    router.verify_global(merged, target, workspace, policy=policy)
    legacy_original = trust.document(snapshots["legacy-project.json"][1])
    legacy = retire_project(legacy_original, owned)
    router_bytes = source_bytes(revision, ROUTER_SOURCE, apply=apply)
    anchor_bytes = source_bytes(revision, ANCHOR_SOURCE, apply=apply)
    read_bytes = source_bytes(revision, "hooks/lib/read-only-command.py", apply=apply)
    if saved(workspace / "hooks/lib/read-only-command.py")["raw"] != read_bytes:
        raise ValueError("installed read classifier differs from accepted source")
    if saved(workspace / ANCHOR_SOURCE)["raw"] != anchor_bytes:
        raise ValueError("installed session identity helper differs from the accepted source; reinstall first")
    resolver_bytes = source_bytes(revision, "hooks/lib/resolve-think-gate.py", apply=apply)
    if saved(workspace / "hooks/lib/resolve-think-gate.py")["raw"] != resolver_bytes:
        raise ValueError("installed task resolver differs from accepted source")
    receipt = {"schema_version": 1, "state": "active", "source_revision": revision,
               "workspace": str(workspace), "policy_path": str(policy_path),
               "policy_sha256": hashlib.sha256(policy_snapshot["raw"]).hexdigest(),
               "router_path": str(target), "router_sha256": hashlib.sha256(router_bytes).hexdigest(),
               "session_anchor_sha256": hashlib.sha256(anchor_bytes).hexdigest(),
               "read_classifier_sha256": hashlib.sha256(read_bytes).hexdigest(),
               "task_resolver_sha256": hashlib.sha256(resolver_bytes).hexdigest(),
               "global_settings_path": str(global_path)}
    summary = {"mode": "apply" if apply else "preview", "workspace": str(workspace),
               "router_path": str(target), "policy_path": str(policy_path), "owned_event_count": len(router.EVENTS),
               "retire_project_managed_commands": legacy != legacy_original,
               "concurrency": "ordered activation and best-effort snapshot CAS; not a multi-file/cross-writer transaction"}
    try:
        old_receipt = trust.document(snapshots["registration.json"][1])
    except (ValueError, TypeError):
        old_receipt = None  # Reserved owned metadata is repairable after main/profile verification.
    changed = (merged != trust.document(snapshots["global-settings.json"][1]) or legacy != legacy_original
               or old_router != router_bytes or old_receipt != receipt)
    summary["changed"] = changed
    if not apply or not changed:
        if apply:
            summary.update(verify_registration(workspace, home))
        return summary
    ensure_directories(home, target.parent.relative_to(home))
    with trust.activation_lock(global_path):
        # Re-read global settings after cooperating installer serialization.
        snapshots["global-settings.json"] = (global_path, saved(global_path))
        merged = merge_global(trust.document(snapshots["global-settings.json"][1]), target, workspace, policy=policy)
        backup = private_backups(home, snapshots)
        if trust.source_authority() != revision:
            raise ValueError("exact-main source changed before bootstrap activation")
        for relative, snapshot in inspected["watched"].items():
            if saved(workspace / relative)["fingerprint"] != snapshot["fingerprint"]:
                raise ValueError("workspace policy changed before bootstrap activation")
        publish(receipt_path, snapshots["registration.json"][1], json_bytes({"schema_version": 1, "state": "staging"}))
        staging_receipt = saved(receipt_path)
        # Policy exists and is locally verified before global discovery points
        # at the router. Missing/incomplete enrollment fails closed in Craft.
        publish(target, snapshots["router.py"][1], router_bytes)
        publish(global_path, snapshots["global-settings.json"][1], json_bytes(merged))
        if legacy != legacy_original:
            publish(legacy_path, snapshots["legacy-project.json"][1], json_bytes(legacy))
        if trust.source_authority() != revision or saved(policy_path)["raw"] != policy_snapshot["raw"]:
            raise ValueError("source/policy changed during bootstrap activation; registration remains staging")
        router.verify_global(trust.document(saved(global_path)), target, workspace, policy=policy)
        if saved(target)["raw"] != router_bytes or saved(workspace / ANCHOR_SOURCE)["raw"] != anchor_bytes:
            raise ValueError("router/session generation changed during activation; registration remains staging")
        actual_legacy = trust.document(saved(legacy_path))
        if retire_project(actual_legacy, owned) != actual_legacy:
            raise ValueError("project managed policy retirement is incomplete; registration remains staging")
        publish(receipt_path, staging_receipt, json_bytes(receipt))
        summary.update(backup=str(backup), **verify_registration(workspace, home))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--home", type=Path, default=Path.home(), help="explicit home, primarily for disposable acceptance")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--verify-registration", action="store_true")
    args = parser.parse_args()
    try:
        result = verify_registration(args.workspace, args.home) if args.verify_registration else install(args.workspace, args.home, apply=args.apply)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, TypeError, ImportError, subprocess.SubprocessError) as error:
        print("Craft hook registration not verified: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
