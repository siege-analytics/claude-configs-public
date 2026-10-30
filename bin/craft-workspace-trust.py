#!/usr/bin/env python3
"""Preview or activate supported Claude project trust for a verified Craft install.

Only projects[canonical_workspace].hasTrustDialogAccepted changes. Snapshot
checks and atomic exchange preserve displaced concurrent versions. This is not
a multiwriter transaction; conflicts abort with private recovery paths.
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 8 * 1024 * 1024
CORE_HOOKS = {"UserPromptSubmit": "hooks/resolver/ca-enforcement-gate.sh",
              "PreToolUse": "hooks/bash/universal-mutation-gate.sh"}


def physical_directory(path: Path) -> Path:
    if not path.is_absolute() or path.resolve(strict=True) != path or not path.is_dir():
        raise ValueError("use an explicit absolute physical directory without symlink aliases")
    return path


def snapshot(path: Path, *, missing=False) -> dict:
    physical_directory(path.parent)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        if missing and not path.is_symlink():
            return {"raw": None, "fingerprint": None}
        raise
    with os.fdopen(fd, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > LIMIT:
            raise ValueError("configuration/managed artifacts must be bounded regular singly linked files")
        raw = source.read(LIMIT + 1)
        after = os.fstat(source.fileno())
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if len(raw) > LIMIT or identity(before) != identity(after):
        raise ValueError("file changed while being read; retry after the writer finishes")
    return {"raw": raw, "fingerprint": (*identity(after), hashlib.sha256(raw).hexdigest())}


def document(saved: dict) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON keys are ambiguous; repair configuration first")
            result[key] = value
        return result
    if saved["raw"] is None:
        return {}
    data = json.loads(saved["raw"], object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON value")))
    if not isinstance(data, dict):
        raise ValueError("configuration must contain a JSON object")
    return data


def source_authority():
    # Use the established exact-main/clean-source policy, not a second Git rule.
    source = ROOT / "bin/build.py"
    sys.path.insert(0, str(source.parent))
    try:
        spec = importlib.util.spec_from_file_location("craft_trust_deploy_authority", source)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    try:
        revision = module.validate_deploy_source(ROOT)
    except module.BuildError as error:
        raise ValueError(str(error)) from error
    if not revision:
        raise ValueError("trust activation requires exact-main deployment authority")
    return revision


def reviewed_bytes(revision: str, relative: str) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
               GIT_NO_REPLACE_OBJECTS="1")
    result = subprocess.run(["git", "-C", str(ROOT), "show", revision + ":" + relative],
                            capture_output=True, check=False, env=env, timeout=10)
    if result.returncode:
        raise ValueError("reviewed managed-hook bytes are unavailable for the deployment revision")
    return result.stdout


def inspect_workspace(workspace: Path, revision=None, *, settings_file=None) -> dict:
    physical_directory(workspace)
    selected = settings_file or (workspace / ".claude/craft-settings.json" if (workspace / ".claude/craft-settings.json").exists() else workspace / ".claude/settings.json")
    if selected not in {workspace / ".claude/settings.json", workspace / ".claude/craft-settings.json"}:
        raise ValueError("use the fixed workspace managed policy location")
    settings_relative = selected.relative_to(workspace).as_posix()
    watched = {}
    for relative in ("deploy-stamp.json", settings_relative, *CORE_HOOKS.values()):
        watched[relative] = snapshot(workspace / relative)
    stamp = document(watched["deploy-stamp.json"])
    commit = stamp.get("commit", "")
    verification = stamp.get("verification", {})
    if (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit)
            or stamp.get("immutable_source") is not True or not isinstance(verification, dict)
            or verification.get("stage") != "artifact-bytes"
            or type(verification.get("file_count")) is not int or verification["file_count"] < 1
            or not isinstance(verification.get("files_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", verification["files_sha256"])):
        raise ValueError("workspace requires a valid verified immutable deployment stamp; reinstall exact main")
    if revision and commit != revision:
        raise ValueError("workspace deployment does not match current reviewed exact main; reinstall before trust activation")
    settings = document(watched[settings_relative])
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError("workspace has no managed hook registrations")
    for event, relative in CORE_HOOKS.items():
        if watched[relative]["raw"] != reviewed_bytes(commit, relative):
            raise ValueError("workspace core hooks differ from their reviewed deployment; reinstall before activation")
        groups = hooks.get(event)
        if not isinstance(groups, list):
            raise ValueError("workspace is missing a required managed hook event")
        tools = [None] if event == "UserPromptSubmit" else ["Bash", "Write", "Edit", "MultiEdit", "NotebookEdit"]
        for tool in tools:
            count = 0
            for group in groups:
                if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                    raise ValueError("workspace hook registration is malformed")
                matcher = group.get("matcher", ".*")
                if not isinstance(matcher, str):
                    raise ValueError("workspace hook matcher must be a regular expression")
                try:
                    if tool is not None and re.fullmatch(matcher, tool) is None:
                        continue
                except re.error as error:
                    raise ValueError("workspace hook matcher is malformed") from error
                for hook in group["hooks"]:
                    if not isinstance(hook, dict):
                        raise ValueError("workspace hook registration is malformed")
                    if hook.get("type") != "command":
                        continue
                    command = hook.get("command")
                    if not isinstance(command, str) or not command.strip():
                        raise ValueError("workspace command hook requires a nonempty command string")
                    tokens = shlex.split(command)
                    script = str(workspace / relative)
                    if tokens in ([script], ["bash", script], ["/bin/bash", script]):
                        count += 1
            if count != 1:
                raise ValueError("workspace requires exactly one managed prompt/mutation registration for each protected event/tool")
    return {"commit": commit, "watched": watched}


def proposed(document_before: dict, workspace: Path) -> dict:
    result = copy.deepcopy(document_before)
    projects = result.setdefault("projects", {})
    if not isinstance(projects, dict):
        raise ValueError("projects must be a JSON object; repair configuration first")
    project = projects.setdefault(str(workspace), {})
    if not isinstance(project, dict):
        raise ValueError("workspace project configuration must be an object")
    project["hasTrustDialogAccepted"] = True
    return result


def backup_parent(config: Path) -> Path:
    parent = config.parent / ".claude-workspace-trust-backups"
    if parent.exists():
        physical_directory(parent)
        if parent.stat().st_mode & 0o077:
            raise ValueError("workspace trust backup directory must be private (mode 0700)")
    else:
        parent.mkdir(mode=0o700)
    return parent


@contextmanager
def activation_lock(config: Path):
    import fcntl
    path = backup_parent(config) / "activation.lock"
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("activation lock must be a regular singly linked file")
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ValueError("another workspace trust update is active; retry after it finishes")
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


def private_backup(config: Path, before: dict, workspace: Path) -> Path:
    parent = backup_parent(config)
    folder = parent / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex)
    folder.mkdir(mode=0o700)
    if before["raw"] is not None:
        with open(folder / "before.json", "xb") as backup:
            os.chmod(backup.name, 0o600)
            backup.write(before["raw"])
            backup.flush()
            os.fsync(backup.fileno())
    metadata = {"config": str(config), "workspace": str(workspace), "before_exists": before["raw"] is not None,
                "before_sha256": hashlib.sha256(before["raw"]).hexdigest() if before["raw"] is not None else None}
    fd = os.open(folder / "receipt.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as receipt:
        json.dump(metadata, receipt, indent=2)
        receipt.write("\n")
    return folder


def stage_config(config: Path, value: dict) -> Path:
    fd, name = tempfile.mkstemp(prefix=".claude-workspace-trust-", dir=config.parent)
    with os.fdopen(fd, "w") as target:
        json.dump(value, target, indent=2, ensure_ascii=True, allow_nan=False)
        target.write("\n")
        target.flush()
        os.fsync(target.fileno())
    return Path(name)


def exchange_paths(left: Path, right: Path):
    """Atomic exchange preserves the exact displaced directory entry."""
    import ctypes
    import ctypes.util
    library = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
    if sys.platform == "darwin" and hasattr(library, "renamex_np"):
        call = library.renamex_np
        call.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        call.restype = ctypes.c_int
        result = call(os.fsencode(left), os.fsencode(right), 2)
    elif sys.platform.startswith("linux") and hasattr(library, "renameat2"):
        call = library.renameat2
        call.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        call.restype = ctypes.c_int
        result = call(-100, os.fsencode(left), -100, os.fsencode(right), 2)
    else:
        raise ValueError("atomic file exchange is unsupported; use a supported filesystem/platform")
    if result:
        error = ctypes.get_errno()
        raise OSError(error, "atomic exchange failed; no replacement fallback: " + os.strerror(error))


def same_version(first, second):
    """Rename changes ctime; inode identity and raw digest bind the version."""
    return (first["raw"] is not None and second["raw"] is not None
            and first["fingerprint"][:2] == second["fingerprint"][:2]
            and first["fingerprint"][-1] == second["fingerprint"][-1])


def recovery_manifest(directory: Path, target: Path):
    """Private identity/hash evidence only; never follow a displaced link."""
    entries = []
    for path in directory.iterdir():
        info = path.lstat()
        entry = {"name": path.name, "device": info.st_dev, "inode": info.st_ino,
                 "mode": stat.S_IFMT(info.st_mode), "size": info.st_size}
        if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            try:
                entry["sha256"] = snapshot(path)["fingerprint"][-1]
            except (OSError, ValueError):
                entry["read_state"] = "unverified"
        entries.append(entry)
    fd = os.open(directory / "recovery.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w") as output:
        json.dump({"target": str(target), "versions": entries, "state": "manual-recovery-required"}, output)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def publish_staged(path: Path, before: dict, staged: Path):
    """Validate publication at a point in time and preserve observed conflicts.

    Exchange is not a multiwriter transaction. Guarded compensation validates
    what it displaced too, retaining every unexpected version for recovery.
    """
    if snapshot(path, missing=True)["fingerprint"] != before["fingerprint"]:
        raise ValueError("concurrent file change detected before activation: " + path.name)
    ours = snapshot(staged)
    if before["raw"] is None:
        # link is atomic create-if-absent: a racing creator wins, never overwritten.
        try:
            os.link(staged, path)
        except FileExistsError as error:
            raise ValueError("concurrent file creation detected; current state retained") from error
        staged.unlink()
        if not same_version(snapshot(path), ours):
            raise ValueError("file changed after creation; current state retained without blind rollback")
        return
    recovery = Path(tempfile.mkdtemp(prefix=".craft-publish-recovery-", dir=path.parent))
    retained = recovery / "displaced-0"
    os.rename(staged, retained)
    try:
        # A raised call may already have exchanged entries (for example an
        # interrupt after the kernel returned). Always retain uncertain effects.
        exchange_paths(retained, path)
        displaced = snapshot(retained)
        if same_version(displaced, before):
            if not same_version(snapshot(path), ours):
                raise ValueError("file changed after activation; current state retained without blind rollback")
            if not same_version(snapshot(retained), before):
                raise ValueError("displaced version changed before cleanup; recovery required")
            # Point-in-time verification cannot prevent future in-place writes.
            retained.unlink()
            recovery.rmdir()
            return
        # Restore the concurrent writer only while target still names our
        # publication. Recheck what this compensation actually displaced.
        candidate, installed = retained, ours
        for attempt in range(2):
            if not same_version(snapshot(path), installed):
                break  # A newer writer already owns the current target.
            wanted = snapshot(candidate)
            exchange_paths(candidate, path)
            displaced_now = snapshot(candidate)
            if same_version(displaced_now, installed):
                break
            # A third writer raced the guarded swap. Keep its displaced bytes
            # and attempt to restore that newer version; retain earlier ones.
            newer = recovery / ("displaced-" + str(attempt + 1))
            os.rename(candidate, newer)
            candidate, installed = newer, wanted
        raise ValueError("concurrent file change detected at atomic exchange; recovery versions retained at " + str(recovery))
    except BaseException as error:
        if recovery.exists():
            try:
                recovery_manifest(recovery, path)
            except (OSError, ValueError):
                pass  # Retain every version even if optional metadata cannot be written.
            raise ValueError("concurrent publication not verified; current state retained without blind rollback; displaced versions retained at " + str(recovery)) from error
        raise


def enable(workspace: Path, config: Path, *, apply=False) -> dict:
    physical_directory(config.parent)
    revision = source_authority() if apply else None
    inspected = inspect_workspace(workspace, revision)
    before = snapshot(config, missing=True)
    original = document(before)
    proposal = proposed(original, workspace)
    changed = proposal != original
    result = {"mode": "apply" if apply else "preview", "workspace": str(workspace), "config": str(config),
              "deployment_revision": inspected["commit"], "changed": changed,
              "field": "projects[canonical_workspace].hasTrustDialogAccepted", "value": True,
              "concurrency": "version-preserving atomic exchange; not a multiwriter transaction"}
    if not apply or not changed:
        return result
    with activation_lock(config):
        # Cooperating helpers re-read under their own lock. The CLI does not
        # share this lock; atomic publication retains unexpected displaced versions.
        before = snapshot(config, missing=True)
        proposal = proposed(document(before), workspace)
        if proposal == document(before):
            result["changed"] = False
            return result
        backup = private_backup(config, before, workspace)
        staged = stage_config(config, proposal)
        try:
            if source_authority() != revision:
                raise ValueError("exact-main activation source changed before trust update")
            for relative, saved in inspected["watched"].items():
                if snapshot(workspace / relative)["fingerprint"] != saved["fingerprint"]:
                    raise ValueError("workspace changed before trust activation; rerun verification")
            publish_staged(config, before, staged)
            if document(snapshot(config)) != proposal:
                raise ValueError("Claude configuration changed during/after activation; retained current state without blind rollback")
        finally:
            staged.unlink(missing_ok=True)
        result["backup"] = str(backup)
        result["verified"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path.home() / ".claude.json")
    parser.add_argument("--apply", action="store_true", help="activate only from clean current origin/main")
    args = parser.parse_args()
    try:
        print(json.dumps(enable(args.workspace, args.config, apply=args.apply), indent=2))
        return 0
    except (OSError, ValueError, TypeError, ImportError, subprocess.SubprocessError) as error:
        print("Workspace trust not activated: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
