#!/usr/bin/env python3
"""Exercise real shell orchestration with disposable, logged local dependencies."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def fixture(base: Path) -> tuple[Path, Path, dict]:
    repo = base / "source"
    scripts = repo / "bin"
    scripts.mkdir(parents=True)
    home = base / "operator's home"
    workspace = home / ".craft-agent/workspaces/test"
    workspace.mkdir(parents=True)
    log = base / "commands.jsonl"
    env = dict(os.environ, HOME=str(home), WIRING_LOG=str(log))
    for name in ("install.sh", "sync-workspace-hooks.sh"):
        shutil.copy2(ROOT / "bin" / name, scripts / name)
    driver = '''import json, os, sys
from pathlib import Path
name=Path(sys.argv[0]).name
with open(os.environ["WIRING_LOG"], "a") as output:
    output.write(json.dumps([name, *sys.argv[1:]])+"\\n")
if name=="build.py":
    ws=Path(sys.argv[sys.argv.index("--craft-workspace")+1])
    for relative in ("skills/think/SKILL.md", "RULES_BUNDLE.md", "KERNEL.md", "RESOLVER.md", "hooks/example.sh", "bin/resolve-load-set.py", "catalog/resolver-manifest.json", "bin/review-risk.py", "catalog/review-risk-policy.json", ".githooks/pre-push"):
        path=ws/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("fixture\\n")
    (ws/"CLAUDE.md").symlink_to("KERNEL.md")
    (ws/"enforcement-manifest.json").write_text('{"gates": []}')
if name=="install-hooks.py":
    path=Path(sys.argv[sys.argv.index("--target-file")+1]);path.parent.mkdir(parents=True,exist_ok=True);path.write_text("{}")
if name=="verify-enforcement.py" and os.environ.get("FAIL_VERIFY"):sys.exit(1)
'''
    for name in ("frontmatter_validation.py", "build.py", "wire-enforcement.py", "check-deploy-drift.py", "install-craft-hook-router.py", "install-hooks.py", "verify-enforcement.py"):
        (scripts / name).write_text(driver)
    for name in ("install-hooks", "verify-enforcement"):
        (scripts / (name + ".sh")).write_text(
            '#!/bin/bash\nexec "' + sys.executable + '" "$(dirname "$0")/' + name + '.py" "$@"\n'
        )
    return repo, workspace, env


def run(repo: Path, workspace: Path, env: dict, name: str):
    args = ["--workspace", "test"] if name == "install.sh" else ["--yes", "--workspace", str(workspace)]
    return subprocess.run(["bash", str(repo / "bin" / name), *args], env=env,
                          text=True, capture_output=True, timeout=30)


def records(env: dict) -> list:
    path = Path(env["WIRING_LOG"])
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def main() -> None:
    for name in ("install.sh", "sync-workspace-hooks.sh"):
        with tempfile.TemporaryDirectory() as raw:
            repo, ws, env = fixture(Path(raw))
            result = run(repo, ws, env, name)
            assert result.returncode == 0, result.stdout + result.stderr
            rows = records(env)
            policy = str(ws / ".claude/craft-settings.json")
            for script, option in (("install-hooks.py", "--target-file"), ("wire-enforcement.py", "--settings-file"), ("verify-enforcement.py", "--settings-file")):
                row = next(row for row in rows if row[0] == script)
                assert row[row.index(option) + 1] == policy, row
            router = [row for row in rows if row[0] == "install-craft-hook-router.py"]
            assert router == [["install-craft-hook-router.py", "--workspace", str(ws), "--apply"],
                              ["install-craft-hook-router.py", "--workspace", str(ws), "--verify-registration"]]
            assert rows.index(router[0]) > next(i for i, row in enumerate(rows) if row[0] == "verify-enforcement.py")
        with tempfile.TemporaryDirectory() as raw:
            repo, ws, env = fixture(Path(raw))
            (repo / "bin/install-craft-hook-router.py").unlink()
            result = run(repo, ws, env, name)
            assert result.returncode != 0 and "router installer missing" in result.stderr
            assert not any(row[0] == "build.py" for row in records(env)), records(env)
        with tempfile.TemporaryDirectory() as raw:
            repo, ws, env = fixture(Path(raw))
            env["FAIL_VERIFY"] = "1"
            result = run(repo, ws, env, name)
            assert result.returncode != 0, result.stdout + result.stderr
            assert not any(row[0] == "install-craft-hook-router.py" for row in records(env))
    print("craft_installer_wiring_test: PASS")


if __name__ == "__main__":
    main()
