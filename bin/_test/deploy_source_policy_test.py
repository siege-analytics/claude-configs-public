#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("build_module", ROOT / "bin" / "build.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD
SPEC.loader.exec_module(BUILD)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, timeout=120).strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def immutable_activation_checks(base: Path) -> None:
    """Exercise real private building, untracked isolation and stamp timing."""
    source = base / "complete-source"
    subprocess.run(["git", "clone", "-q", "--no-local", str(ROOT), str(source)], check=True, timeout=120)
    git(source, "config", "core.hooksPath", os.devnull)
    git(source, "config", "user.email", "test@example.test")
    git(source, "config", "user.name", "Test")
    # The fixture must include this working candidate before it is committed in
    # the outer repository; the fixture's own commit is its accepted main.
    changed = subprocess.check_output(
        ["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"], text=True,
        timeout=120,
    ).splitlines()
    for name in changed:
        path = ROOT / name
        if path.is_file():
            shutil.copy2(path, source / name)
    legacy_bytes = b"fixture observed legacy dispatcher\n"
    manifest_path = source / "catalog/legacy-owned-artifacts.json"
    # A committed fixture policy proves retirement without vendoring private
    # observed installation bytes. Production retains its exact observed hash.
    manifest = json.loads((ROOT / "catalog/legacy-owned-artifacts.json").read_text())
    manifest["artifacts"][0]["sha256"] = hashlib.sha256(legacy_bytes).hexdigest()
    manifest["artifacts"][0]["size_bytes"] = len(legacy_bytes)
    manifest_path.write_text(json.dumps(manifest))
    revision = commit(source, "candidate deployment fixture")
    remote = base / "complete-remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=120)
    git(source, "remote", "set-url", "origin", str(remote))
    git(source, "push", "-q", "origin", "HEAD:main")
    untracked = source / "hooks/resolver/untracked-local.sh"
    untracked.write_text("#!/bin/sh\necho must-not-be-deployed\n")
    ignored = source / "dist/local-output.txt"
    ignored.parent.mkdir(exist_ok=True)
    ignored.write_text("old generated outputs are not build inputs\n")
    assert BUILD.validate_deploy_source(source) == revision
    workspace = base / "complete-workspace"
    workspace.mkdir()
    custom = workspace / "skills/operator-only/custom.bin"
    custom.parent.mkdir(parents=True)
    custom.write_bytes(b"operator binary\x00")
    nested = workspace / "skills/think/operator-notes.txt"
    nested.parent.mkdir(parents=True)
    nested.write_text("operator nested notes\n")
    legacy = workspace / "skills/RESOLVER.md"
    legacy.write_bytes(legacy_bytes)
    unknown = workspace / "skills/unknown-root.md"
    unknown.write_text("operator root notes\n")
    result = subprocess.run(
        [sys.executable, str(source / "bin/build.py"), "--layout", "flat", "--deploy",
         "--craft-workspace", str(workspace)], cwd=source, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout[-1500:] + result.stderr[-1500:]
    assert custom.read_bytes() == b"operator binary\x00"
    assert nested.read_text() == "operator nested notes\n"
    assert unknown.read_text() == "operator root notes\n"
    assert not legacy.exists(), "exact known legacy dispatcher was not retired"
    # A same-name operator modification survives every subsequent activation.
    modified_legacy = legacy_bytes.replace(b"fixture", b"custom!")
    assert len(modified_legacy) == len(legacy_bytes)
    legacy.write_bytes(modified_legacy)
    stamp = json.loads((workspace / "deploy-stamp.json").read_text())
    assert stamp["commit"] == revision and stamp["repo_root"] == str(source.resolve())
    assert stamp["immutable_source"] is True and stamp["verification"]["stage"] == "artifact-bytes"
    assert stamp["verification"]["file_count"] > 0
    assert not (workspace / "hooks/resolver/untracked-local.sh").exists()
    assert not (workspace / "local-output.txt").exists()

    # Change the original source after immutable bytes have reached the target.
    # Final validation must refuse certification and invalidate the old stamp.
    verify = BUILD._verify_deployed_generation
    tracked = source / "hooks/resolver/standing-order-guard.sh"
    canonical = tracked.read_bytes()

    def mutate_after_copy(builder, target):
        assert not (target / "deploy-stamp.json").exists(), "old authority survived activation start"
        receipt = verify(builder, target)
        tracked.write_bytes(canonical + b"\n# concurrent unreviewed edit\n")
        return receipt

    with patch.object(BUILD, "_verify_deployed_generation", side_effect=mutate_after_copy):
        try:
            BUILD.deploy_exact_revision(source, revision, workspace, "flat")
        except BUILD.BuildError as exc:
            assert "tracked deployment inputs differ" in str(exc), str(exc)
        else:
            raise AssertionError("source mutation during activation was certified")
    assert legacy.read_bytes() == modified_legacy
    assert custom.exists() and nested.exists() and unknown.exists()
    assert not (workspace / "deploy-stamp.json").exists()
    assert (workspace / "hooks/resolver/standing-order-guard.sh").read_bytes() == canonical
    tracked.write_bytes(canonical)

    def corrupt_after_copy(builder, target):
        deployed = target / "hooks/resolver/standing-order-guard.sh"
        deployed.write_bytes(deployed.read_bytes() + b"\n# corrupted copy\n")
        return verify(builder, target)

    with patch.object(BUILD, "_verify_deployed_generation", side_effect=corrupt_after_copy):
        try:
            BUILD.deploy_exact_revision(source, revision, workspace, "flat")
        except BUILD.BuildError as exc:
            assert "deployed artifact verification failed" in str(exc), str(exc)
        else:
            raise AssertionError("corrupt installed bytes were certified")
    assert not (workspace / "deploy-stamp.json").exists()


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = base / "remote.git"
        repo = base / "repo"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, timeout=120)
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, timeout=120)
        git(repo, "config", "user.email", "test@example.test")
        git(repo, "config", "user.name", "Test")
        git(repo, "remote", "add", "origin", str(remote))

        (repo / ".claude").mkdir()
        (repo / ".claude" / "deploy-model").write_text("merge-then-deploy\n")
        (repo / "bin").mkdir()
        reader = repo / "bin/source_snapshot.py"
        trusted_reader = (ROOT / "bin/source_snapshot.py").read_bytes()
        reader.write_bytes(trusted_reader)
        (repo / "README.md").write_text("baseline\n")
        main_sha = commit(repo, "baseline")
        git(repo, "push", "-q", "-u", "origin", "main")
        assert BUILD.validate_deploy_source(repo) == main_sha

        try:
            BUILD._deploy_source_files(repo, "--output=not-a-revision")
        except BUILD.BuildError as exc:
            assert "exact commit ID" in str(exc)
        else:
            raise AssertionError("non-object deployment revision accepted")

        def rejects_dirty(label):
            try:
                BUILD.validate_deploy_source(repo)
            except BUILD.BuildError as exc:
                assert "tracked deployment inputs differ" in str(exc), (label, str(exc))
            else:
                raise AssertionError(f"dirty {label} source was certified as exact main")

        readme = repo / "README.md"
        sentinel_reader = base / "dirty-reader-executed"
        reader.write_bytes(trusted_reader + ("\nPath(" + repr(str(sentinel_reader))
                           + ").write_text('must not execute')\n").encode())
        rejects_dirty("reader helper")
        assert not sentinel_reader.exists(), "dirty source helper executed during validation"
        reader.write_bytes(trusted_reader)
        readme.write_text("uncommitted runtime input\n")
        rejects_dirty("unstaged")
        git(repo, "add", "README.md")
        rejects_dirty("staged")
        readme.write_text("baseline\n")
        rejects_dirty("staged change with clean working bytes")
        git(repo, "restore", "--staged", "--worktree", "README.md")
        for flag in ("assume-unchanged", "skip-worktree"):
            git(repo, "update-index", "--" + flag, "README.md")
            readme.write_text("hidden dirty input\n")
            rejects_dirty(flag)
            git(repo, "update-index", "--no-" + flag, "README.md")
            git(repo, "restore", "--worktree", "README.md")
        git(repo, "config", "core.fileMode", "false")
        readme.chmod(0o755)
        rejects_dirty("executable mode hidden by core.fileMode")
        readme.chmod(0o644)
        git(repo, "config", "--unset", "core.fileMode")
        readme.unlink()
        rejects_dirty("deleted")
        git(repo, "restore", "--worktree", "README.md")
        addition = repo / "new-input.py"
        addition.write_text("untracked content is never exported\n")
        assert BUILD.validate_deploy_source(repo) == main_sha
        assert "new-input.py" not in BUILD._deploy_source_files(repo, main_sha)
        git(repo, "add", "new-input.py")
        rejects_dirty("staged addition")
        git(repo, "rm", "--cached", "new-input.py")
        addition.unlink()
        # A modified tracked special file must fail without waiting for input.
        readme.unlink()
        os.mkfifo(readme)
        rejects_dirty("FIFO")
        readme.unlink()
        git(repo, "restore", "--worktree", "README.md")
        # Local replacement refs must not redefine the bytes named by main.
        readme.write_text("replacement bytes\n")
        git(repo, "add", "README.md")
        tree = git(repo, "write-tree")
        replacement = git(repo, "commit-tree", tree, "-m", "local replacement")
        git(repo, "replace", main_sha, replacement)
        git(repo, "reset", "--hard", "-q", main_sha)
        assert BUILD._deploy_source_files(repo, main_sha)["README.md"][0] == b"baseline\n"
        rejects_dirty("Git replacement")
        git(repo, "replace", "-d", main_sha)
        git(repo, "reset", "--hard", "-q", main_sha)
        with patch.dict(os.environ, {"GIT_DIR": str(remote), "GIT_INDEX_FILE": str(base / "foreign-index")}):
            assert BUILD.validate_deploy_source(repo) == main_sha
        for target in (repo, repo / "nested", base):
            target.mkdir(exist_ok=True)
            try:
                BUILD._validate_deploy_target(repo, target)
            except BUILD.BuildError as exc:
                assert "overlap" in str(exc), (target, str(exc))
            else:
                raise AssertionError(f"overlapping target accepted: {target}")
        alias = base / "source-alias"
        alias.symlink_to(repo, target_is_directory=True)
        try:
            BUILD._validate_deploy_target(repo, alias)
        except BUILD.BuildError as error:
            assert "deployment" in str(error)
        else:
            raise AssertionError("source target alias accepted")
        target = base / "workspace"
        target.mkdir()
        assert BUILD._validate_deploy_target(repo, target) == target.resolve()
        sentinel = target / "keep.md"
        sentinel.write_text("do not remove\n")
        for output in (repo, target, base):
            try:
                BUILD._validate_deploy_output(repo, target, output)
            except BUILD.BuildError as error:
                assert "deployment" in str(error)
            else:
                raise AssertionError(f"unsafe deployment output accepted: {output}")
            result = subprocess.run(
                [sys.executable, str(ROOT / "bin/build.py"), "--deploy", "--dist", str(output),
                 "--craft-workspace", str(target)], capture_output=True, text=True,
                timeout=120,
            )
            assert result.returncode != 0 and "--dist cannot be combined with --deploy" in result.stderr
            assert sentinel.read_text() == "do not remove\n"
            assert readme.read_text() == "baseline\n"
        output_alias = base / "output-alias"
        output_alias.symlink_to(repo / "dist", target_is_directory=True)
        try:
            BUILD._validate_deploy_output(repo, target, output_alias)
        except BUILD.BuildError as error:
            assert "deployment" in str(error)
        else:
            raise AssertionError("deployment output alias accepted")
        assert BUILD._validate_deploy_output(repo, target, repo / "dist") == repo.resolve() / "dist"
        (target / "bin").symlink_to(repo, target_is_directory=True)
        try:
            BUILD._validate_deploy_paths(target, ["bin/runtime.py"])
        except BUILD.BuildError as exc:
            assert "symlink" in str(exc)
        else:
            raise AssertionError("managed parent symlink accepted")
        (target / "bin").unlink()
        outside = base / "operator-settings.json"
        outside.write_text("outside content must survive\n")
        (target / ".claude").mkdir()
        os.link(outside, target / ".claude/settings.json")
        try:
            BUILD._validate_deploy_paths(target, ["KERNEL.md"])
        except BUILD.BuildError as exc:
            assert "hardlink" in str(exc)
        else:
            raise AssertionError("hardlinked settings target accepted")
        assert outside.read_text() == "outside content must survive\n"
        (target / ".claude/settings.json").unlink()
        for name in ("RESOLVER.md", ".claude/settings.json"):
            special = target / name
            os.mkfifo(special)
            try:
                BUILD._validate_deploy_paths(target, ["RESOLVER.md"])
            except BUILD.BuildError as exc:
                assert "regular" in str(exc)
            else:
                raise AssertionError(f"managed FIFO accepted: {name}")
            special.unlink()
        (target / "bin").write_text("not a directory\n")
        try:
            BUILD._validate_deploy_paths(target, ["bin/runtime.py"])
        except BUILD.BuildError as exc:
            assert "parent must be a directory" in str(exc)
        else:
            raise AssertionError("regular file parent accepted")
        (target / "bin").unlink()

        git(repo, "switch", "-q", "-c", "feature/not-main")
        (repo / "README.md").write_text("unreleased\n")
        feature_sha = commit(repo, "unreleased")
        try:
            BUILD.validate_deploy_source(repo)
        except BUILD.BuildError as exc:
            assert "is not current origin/main" in str(exc)
        else:
            raise AssertionError("non-main feature revision was allowed to deploy")

        git(repo, "push", "-q", "origin", "HEAD:main")
        assert BUILD.validate_deploy_source(repo) == feature_sha

        (repo / ".claude" / "deploy-model").unlink()
        commit(repo, "attempt to remove deployment policy")
        try:
            BUILD.validate_deploy_source(repo)
        except BUILD.BuildError as exc:
            assert "is not current origin/main" in str(exc)
        else:
            raise AssertionError("deleting the marker disabled main-only deployment")

        git(repo, "remote", "set-url", "origin", str(base / "missing-remote.git"))
        try:
            BUILD.validate_deploy_source(repo)
        except BUILD.BuildError as exc:
            assert "failed closed" in str(exc)
        else:
            raise AssertionError("active deployment policy failed open when origin was unreachable")
        git(repo, "remote", "set-url", "origin", str(remote))

        legacy_remote = base / "legacy-remote.git"
        legacy = base / "legacy"
        subprocess.run(["git", "init", "-q", "--bare", str(legacy_remote)], check=True, timeout=120)
        subprocess.run(["git", "init", "-q", "-b", "main", str(legacy)], check=True, timeout=120)
        git(legacy, "config", "user.email", "test@example.test")
        git(legacy, "config", "user.name", "Test")
        git(legacy, "remote", "add", "origin", str(legacy_remote))
        (legacy / "README.md").write_text("legacy\n")
        commit(legacy, "legacy")
        git(legacy, "push", "-q", "-u", "origin", "main")
        (legacy / ".claude").mkdir()
        (legacy / ".claude" / "deploy-model").write_text("merge-then-deploy\n")
        assert BUILD.validate_deploy_source(legacy) is None, "uncommitted marker must not activate policy"

        immutable_activation_checks(base)

    print("deploy_source_policy_test: PASS")


if __name__ == "__main__":
    main()
