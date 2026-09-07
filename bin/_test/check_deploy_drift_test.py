#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "check-deploy-drift.py"


def run(repo: Path, ws: Path):
    return subprocess.run(
        ["python3", str(SCRIPT), "--repo-root", str(repo), "--workspace", str(ws), "--scope", "hooks", "--verbose", "--json"],
        text=True,
        capture_output=True,
    )


def make_repo(base: Path) -> Path:
    repo = base / "repo"
    (repo / "hooks" / "bash").mkdir(parents=True)
    (repo / "hooks" / "_test").mkdir(parents=True)
    (repo / "hooks" / "bash" / "a.sh").write_text("#!/bin/sh\necho a\n")
    (repo / "hooks" / "_test" / "a.test.sh").write_text("#!/bin/sh\necho test\n")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=repo, check=True)
    subprocess.run(["git", "add", "hooks"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    return repo


def deploy(repo: Path, ws: Path):
    if (ws / "hooks").exists():
        shutil.rmtree(ws / "hooks")
    shutil.copytree(repo / "hooks", ws / "hooks")
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    (ws / "deploy-stamp.json").write_text(json.dumps({"commit": head, "timestamp": "now", "repo_root": str(repo)}) + "\n")


def assert_type(result, expected_type):
    data = json.loads(result.stdout)
    assert any(e["type"] == expected_type for e in data["errors"]), data


def main():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        repo = make_repo(base)
        ws = base / "workspace"
        ws.mkdir()
        deploy(repo, ws)
        r = run(repo, ws)
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)

        (ws / "hooks" / "bash" / "a.sh").unlink()
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "missing")
        deploy(repo, ws)

        (ws / "hooks" / "bash" / "a.sh").write_text("stale\n")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "hash-different")
        deploy(repo, ws)

        (ws / "deploy-stamp.json").unlink()
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "missing-stamp")
        deploy(repo, ws)

        (ws / "deploy-stamp.json").write_text(json.dumps({"commit": "old", "timestamp": "now", "repo_root": str(repo)}) + "\n")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "stamp-mismatch")
        deploy(repo, ws)

        (ws / "hooks" / "extra.sh").write_text("extra\n")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "extra")
        deploy(repo, ws)

        shutil.rmtree(ws / "hooks")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "missing-hooks")
        deploy(repo, ws)

        (ws / "deploy-stamp.json").write_text("{not json\n")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "bad-stamp")
        deploy(repo, ws)

        head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
        (ws / "deploy-stamp.json").write_text(json.dumps({"commit": head, "timestamp": "now"}) + "\n")
        r = run(repo, ws)
        assert r.returncode == 1
        assert_type(r, "stamp-incomplete")

        sync = ROOT / "bin" / "sync-workspace-hooks.sh"
        r = subprocess.run(["bash", str(sync), "--workspace", str(ws)], text=True, capture_output=True)
        assert r.returncode == 2, (r.returncode, r.stdout, r.stderr)
        assert "--yes is required" in r.stderr

    print("check_deploy_drift_test: PASS")


if __name__ == "__main__":
    main()
