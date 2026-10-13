#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("build_module", ROOT / "bin" / "build.py")
assert SPEC and SPEC.loader
BUILD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD
SPEC.loader.exec_module(BUILD)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        remote = base / "remote.git"
        repo = base / "repo"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
        git(repo, "config", "user.email", "test@example.test")
        git(repo, "config", "user.name", "Test")
        git(repo, "remote", "add", "origin", str(remote))

        (repo / ".claude").mkdir()
        (repo / ".claude" / "deploy-model").write_text("merge-then-deploy\n")
        (repo / "README.md").write_text("baseline\n")
        main_sha = commit(repo, "baseline")
        git(repo, "push", "-q", "-u", "origin", "main")
        assert BUILD.validate_deploy_source(repo) == main_sha

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
        subprocess.run(["git", "init", "-q", "--bare", str(legacy_remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(legacy)], check=True)
        git(legacy, "config", "user.email", "test@example.test")
        git(legacy, "config", "user.name", "Test")
        git(legacy, "remote", "add", "origin", str(legacy_remote))
        (legacy / "README.md").write_text("legacy\n")
        commit(legacy, "legacy")
        git(legacy, "push", "-q", "-u", "origin", "main")
        (legacy / ".claude").mkdir()
        (legacy / ".claude" / "deploy-model").write_text("merge-then-deploy\n")
        assert BUILD.validate_deploy_source(legacy) is None, "uncommitted marker must not activate policy"

    print("deploy_source_policy_test: PASS")


if __name__ == "__main__":
    main()
