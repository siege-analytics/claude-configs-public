#!/usr/bin/env python3
"""Install one approved canary payload into its exact disposable workspace.

This is not a general installer. It accepts only the immutable #1003 manifest,
materialized payload and workspace paths, creates no production deploy stamp,
and registers native hooks only in the packet's local fixture repository.
"""
from __future__ import annotations

import argparse
import importlib.util
import copy
import json
import os
import secrets
import shlex
import shutil
import stat
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


def _json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _json_object_snapshot(path: Path, label: str) -> tuple[dict[str, Any], bytes, os.stat_result]:
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"{label} must be a regular non-symlink file: {path}")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError(f"{label} path changed while opening: {path}")
        raw = handle.read()
        after_read = os.fstat(handle.fileno())
    identity = lambda value: (
        value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns,
    )
    if identity(after_read) != identity(before):
        raise ValueError(f"{label} changed while reading: {path}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value, raw, before


def _assert_snapshot_unchanged(path: Path, raw: bytes, before: os.stat_result, label: str) -> None:
    try:
        current = path.lstat()
    except FileNotFoundError as exc:
        raise ValueError(f"{label} path disappeared during validation: {path}") from exc
    identity = lambda value: (
        value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns,
    )
    if not stat.S_ISREG(current.st_mode) or identity(current) != identity(before) or path.read_bytes() != raw:
        raise ValueError(f"{label} path or bytes changed during validation: {path}")


def _resolved_base_settings(payload: Path, workspace: Path) -> dict[str, Any]:
    snippet = _json_object(payload / "hooks/settings-snippet.json", "pinned base settings")
    if set(snippet) != {"_comment_", "hooks"} or not isinstance(snippet["hooks"], dict):
        raise ValueError("pinned base settings shape differs from the reviewed canonical artifact")
    expected = {"hooks": copy.deepcopy(snippet["hooks"])}
    prefix = "/path/to/claude-configs-public/"
    for groups in expected["hooks"].values():
        if not isinstance(groups, list):
            raise ValueError("pinned base settings hook groups must be arrays")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise ValueError("pinned base settings contains an invalid hook group")
            for hook in group["hooks"]:
                command = hook.get("command") if isinstance(hook, dict) else None
                if not isinstance(command, str) or not command.startswith(prefix):
                    raise ValueError("pinned base settings contains an unsupported command")
                relative = command[len(prefix):]
                hook["command"] = shlex.quote(str(workspace / relative))
    return expected


def _expected_wired_settings(payload: Path, workspace: Path, source: Path) -> dict[str, Any]:
    expected = _resolved_base_settings(payload, workspace)
    generated = _json_object(
        source / "dist/craft-agent/settings-enforcement.json", "pinned generated enforcement settings",
    )
    if set(generated) != {"_comment_", "_gate_contract", "hooks", "env"}:
        raise ValueError("generated enforcement settings shape differs from the reviewed canonical artifact")
    generated_hooks = generated.get("hooks")
    if not isinstance(generated_hooks, dict) or set(generated_hooks) != {"UserPromptSubmit"}:
        raise ValueError("generated enforcement settings must contain only UserPromptSubmit hooks")
    additions = copy.deepcopy(generated_hooks["UserPromptSubmit"])
    if not isinstance(additions, list):
        raise ValueError("generated enforcement UserPromptSubmit groups must be an array")
    for group in additions:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            raise ValueError("generated enforcement settings contains an invalid hook group")
        for hook in group["hooks"]:
            command = hook.get("command") if isinstance(hook, dict) else None
            if not isinstance(command, str) or not command.startswith("/path/to/"):
                raise ValueError("generated enforcement settings contains an unsupported command")
            hook["command"] = command.replace("/path/to", str(workspace), 1)
    expected["hooks"].setdefault("UserPromptSubmit", []).extend(additions)
    return expected


def verify_wired_settings(
    canary: Any, payload: Path, workspace: Path, source: Path,
    *, _test_after_snapshot: Any | None = None,
) -> tuple[bytes, str, list[dict[str, Any]]]:
    settings_path = workspace / ".claude/settings.json"
    actual, settings_bytes, settings_stat = _json_object_snapshot(
        settings_path, "wired workspace assembly settings",
    )
    if _test_after_snapshot is not None:
        _test_after_snapshot()
    expected = _expected_wired_settings(payload, workspace, source)
    if actual != expected:
        raise canary.PacketError("wired settings registration inventory differs from canonical pinned artifacts")
    inventory: list[dict[str, Any]] = []
    for event, groups in actual["hooks"].items():
        for group_index, group in enumerate(groups):
            matcher = group.get("matcher")
            for hook_index, hook in enumerate(group["hooks"]):
                command = hook["command"]
                argv = shlex.split(command)
                if len(argv) != 1:
                    raise canary.PacketError(f"registered hook command must be one exact executable: {command}")
                executable = Path(argv[0])
                try:
                    relative = executable.relative_to(workspace)
                except ValueError as exc:
                    raise canary.PacketError(f"registered hook executable escapes pinned workspace payload: {command}") from exc
                payload_executable = payload / relative
                if (
                    not executable.is_file() or executable.is_symlink() or not os.access(executable, os.X_OK)
                    or not payload_executable.is_file() or payload_executable.is_symlink()
                    or not os.access(payload_executable, os.X_OK)
                ):
                    raise canary.PacketError(f"registered hook executable is not present in the pinned payload: {relative}")
                if executable.read_bytes() != payload_executable.read_bytes():
                    raise canary.PacketError(f"registered hook executable differs from pinned payload: {relative}")
                inventory.append({
                    "event": event,
                    "matcher": matcher,
                    "group_index": group_index,
                    "hook_index": hook_index,
                    "argv": argv,
                    "payload_relative_path": relative.as_posix(),
                    "executable_sha256": canary.sha256_bytes(executable.read_bytes()),
                })
    _assert_snapshot_unchanged(
        settings_path, settings_bytes, settings_stat, "wired workspace assembly settings",
    )
    return settings_bytes, canary.sha256_bytes(settings_bytes), inventory


def preflight_fixture_settings_target(canary: Any, fixture: Path) -> tuple[Path, Path]:
    if not fixture.is_dir() or fixture.is_symlink() or fixture.resolve() != fixture:
        raise canary.PacketError("exact disposable fixture repository must be a real directory")
    settings_dir = fixture / ".claude"
    target = settings_dir / "settings.json"
    if settings_dir.is_symlink():
        raise canary.PacketError("fixture .claude directory must not be a symlink")
    if settings_dir.exists() and not settings_dir.is_dir():
        raise canary.PacketError("fixture .claude path must be absent or a real directory")
    if target.exists() or target.is_symlink():
        raise canary.PacketError("refusing existing fixture Claude settings target")
    return settings_dir, target


def register_fixture_settings(
    canary: Any, source_settings: Path, fixture: Path, expected_sha256: str,
    *, _test_before_link: Any | None = None,
) -> dict[str, Any]:
    settings_dir, target = preflight_fixture_settings_target(canary, fixture)
    source_bytes = source_settings.read_bytes()
    if canary.sha256_bytes(source_bytes) != expected_sha256:
        raise canary.PacketError("wired settings changed before fixture registration")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    file_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    parent_fd = fixture_fd = settings_fd = None
    temporary_name: str | None = None
    linked = False
    created_dir = False

    def same_directory(left: os.stat_result, right: os.stat_result) -> bool:
        return stat.S_ISDIR(left.st_mode) and stat.S_ISDIR(right.st_mode) and (
            left.st_dev, left.st_ino
        ) == (right.st_dev, right.st_ino)

    try:
        parent_fd = os.open(fixture.parent, directory_flags)
        fixture_fd = os.open(fixture.name, directory_flags, dir_fd=parent_fd)
        fixture_stat = os.fstat(fixture_fd)
        try:
            settings_fd = os.open(".claude", directory_flags, dir_fd=fixture_fd)
        except FileNotFoundError:
            os.mkdir(".claude", mode=0o700, dir_fd=fixture_fd)
            created_dir = True
            settings_fd = os.open(".claude", directory_flags, dir_fd=fixture_fd)
        settings_stat = os.fstat(settings_fd)
        try:
            os.stat("settings.json", dir_fd=settings_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise canary.PacketError("refusing existing fixture Claude settings target")

        for _ in range(32):
            candidate = ".cc-1003-settings-" + secrets.token_hex(12)
            try:
                fd = os.open(candidate, file_flags, 0o600, dir_fd=settings_fd)
                temporary_name = candidate
                break
            except FileExistsError:
                continue
        else:
            raise canary.PacketError("could not allocate exclusive fixture settings temporary file")
        with os.fdopen(fd, "wb") as handle:
            handle.write(source_bytes)
            handle.flush()
            os.fsync(handle.fileno())

        if _test_before_link is not None:
            _test_before_link()
        if source_settings.read_bytes() != source_bytes:
            raise canary.PacketError("wired settings changed during fixture registration")

        try:
            current_fixture_fd = os.open(fixture.name, directory_flags, dir_fd=parent_fd)
            current_fixture_stat = os.fstat(current_fixture_fd)
            os.close(current_fixture_fd)
            current_settings_fd = os.open(".claude", directory_flags, dir_fd=fixture_fd)
            current_settings_stat = os.fstat(current_settings_fd)
            os.close(current_settings_fd)
        except OSError as exc:
            raise canary.PacketError("fixture Claude settings parent changed during registration") from exc
        if not same_directory(fixture_stat, current_fixture_stat) or not same_directory(settings_stat, current_settings_stat):
            raise canary.PacketError("fixture Claude settings parent identity changed during registration")

        try:
            os.link(
                temporary_name, "settings.json",
                src_dir_fd=settings_fd, dst_dir_fd=settings_fd, follow_symlinks=False,
            )
            linked = True
        except FileExistsError as exc:
            raise canary.PacketError("fixture Claude settings target appeared during registration") from exc
        target_fd = os.open("settings.json", os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=settings_fd)
        try:
            target_stat = os.fstat(target_fd)
            with os.fdopen(target_fd, "rb", closefd=False) as handle:
                target_bytes = handle.read()
        finally:
            os.close(target_fd)
        if not stat.S_ISREG(target_stat.st_mode) or target_bytes != source_bytes:
            os.unlink("settings.json", dir_fd=settings_fd)
            linked = False
            raise canary.PacketError("fixture Claude settings bytes differ after atomic registration")

        visible_fixture = fixture.lstat()
        visible_settings = settings_dir.lstat()
        visible_target = target.lstat()
        if (
            not same_directory(fixture_stat, visible_fixture)
            or not same_directory(settings_stat, visible_settings)
            or not stat.S_ISREG(visible_target.st_mode)
            or (visible_target.st_dev, visible_target.st_ino) != (target_stat.st_dev, target_stat.st_ino)
        ):
            os.unlink("settings.json", dir_fd=settings_fd)
            linked = False
            raise canary.PacketError("fixture Claude registration path identity changed before receipt")
        destination_sha256 = canary.sha256_bytes(target_bytes)
    except Exception:
        if linked and settings_fd is not None:
            try:
                os.unlink("settings.json", dir_fd=settings_fd)
            except FileNotFoundError:
                pass
        raise
    finally:
        if temporary_name is not None and settings_fd is not None:
            try:
                os.unlink(temporary_name, dir_fd=settings_fd)
            except FileNotFoundError:
                pass
        if settings_fd is not None:
            os.close(settings_fd)
        if created_dir and fixture_fd is not None:
            try:
                os.rmdir(".claude", dir_fd=fixture_fd)
            except OSError:
                pass
        if fixture_fd is not None:
            os.close(fixture_fd)
        if parent_fd is not None:
            os.close(parent_fd)
    return {
        "source_path": str(source_settings),
        "destination_path": str(target),
        "source_sha256": expected_sha256,
        "destination_sha256": destination_sha256,
    }


def configure(
    canary: Any, manifest: dict[str, Any], *, _test_discovery_reader: Any | None = None,
    _test_expected_temp_base: Path = Path("/private/tmp"),
) -> dict[str, Any]:
    facts = canary.validate_manifest(manifest, require_approval_record=True, _test_expected_temp_base=_test_expected_temp_base)
    source: Path = facts["source_root"]
    payload = facts["temp_root"] / "workspace-payload"
    workspace: Path = facts["workspace_root"]
    fixture = facts["temp_root"] / "fixture" / "repo"
    validate_payload(canary, payload, manifest["pins"]["workspace_payload_tree_sha256"])
    # Fresh shared attestation is the mutation boundary. An earlier receipt is
    # never trusted: source/package/composition/payload and fixture identity/
    # local transport are re-read immediately before any workspace copy or
    # install/wire/verify command.
    attestation = (
        canary.attest_materialized(manifest, _test_expected_temp_base=_test_expected_temp_base)
        if _test_discovery_reader is None
        else canary.attest_materialized(
            manifest, _test_discovery_reader=_test_discovery_reader, _test_expected_temp_base=_test_expected_temp_base,
        )
    )
    if not workspace.is_dir() or workspace.is_symlink() or workspace.resolve() != workspace:
        raise canary.PacketError("exact disposable workspace must already exist as a real directory")
    if not fixture.is_dir() or fixture.is_symlink():
        raise canary.PacketError("exact disposable fixture repository is absent")
    preflight_fixture_settings_target(canary, fixture)
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
    settings_bytes, settings_sha256, command_inventory = verify_wired_settings(canary, payload, workspace, source)
    registration = register_fixture_settings(
        canary, workspace / ".claude/settings.json", fixture, settings_sha256,
    )
    if (workspace / "deploy-stamp.json").exists():
        raise canary.PacketError("disposable setup created a forbidden production deploy stamp")
    if settings_bytes != (fixture / ".claude/settings.json").read_bytes():
        raise canary.PacketError("fixture Claude registration no longer matches workspace assembly settings")
    receipt = {
        "schema_version": canary.SCHEMA_VERSION,
        "run_id": facts["run_id"],
        "manifest_sha256": facts["manifest_sha256"],
        "mutation_boundary_attestation_sha256": attestation["receipt_sha256"],
        "workspace": str(workspace),
        "fixture": str(fixture),
        "fixture_identity": manifest["fixture"]["canonical_identity"],
        "workspace_payload_tree_sha256": canary.tree_digest(payload),
        "workspace_settings_role": "assembly-evidence-only",
        "claude_project_registration": {
            **registration,
            "sdk_cwd": str(fixture),
            "registration_state": "configured-unverified",
            "host_invocation_observed": False,
            "command_inventory": command_inventory,
        },
        "production_deploy_stamp": False,
        "standing_order_automations_enabled": False,
        "pi_capability_state": "unsupported-unverified",
        "authorization_effect": "none",
        "command_output_sha256": canary.sha256_bytes("\n".join(outputs).encode()),
    }
    destination = facts["evidence_root"] / "workspace-setup.json"
    destination.write_bytes(canary.canonical_bytes(receipt))
    return {
        "status": "disposable-workspace-configured-unverified",
        "authorization_effect": "none",
        "receipt": str(destination),
        "receipt_sha256": canary.sha256_bytes(destination.read_bytes()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    canary = load_canary()
    try:
        result = configure(canary, canary.load_json(args.manifest))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError, canary.PacketError, ValueError, TypeError) as exc:
        print(f"CANARY SETUP ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
