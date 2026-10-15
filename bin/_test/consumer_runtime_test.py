#!/usr/bin/env python3
"""Installed-package integration coverage for F2/F3 consumer runtimes."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FORMS = ("nested", "flat", "claude-code", "craft-agent")
RUNTIME_FILES = (
    "bin/resolve-load-set.py",
    "catalog/resolver-manifest.json",
    "bin/review-risk.py",
    "catalog/review-risk-policy.json",
)
EXACT_REPO = "git@github.com:siege-analytics/siege_utilities.git"
PROJECT_SOURCES = {
    "projects/siege-utilities/_rules.md",
    "projects/siege-utilities/skills/hostile-review/SKILL.md",
    "projects/siege-utilities/skills/notebook-impact/SKILL.md",
    "projects/siege-utilities/skills/error-path-tests/SKILL.md",
}
CASES = (
    ("python", "review this Python diff", "other/repo"),
    ("project-all", "review this signature and error path", EXACT_REPO),
    ("foreign-host", "review this signature and error path", "git@other-host:siege-analytics/siege_utilities.git"),
    ("shelf", "[skill:shelves--clean-code]", "other/repo"),
    ("unknown", "write a friendly greeting", "other/repo"),
)


def run(command: list[str], *, cwd: Path | None = None, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=30,
    )


def resolve(script: Path, prompt: str, repo: str, *, cwd: Path | None = None) -> dict:
    proc = run([sys.executable, str(script), "--prompt", prompt, "--repo", repo], cwd=cwd)
    if proc.returncode:
        raise AssertionError(proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


def parity_shape(result: dict) -> dict:
    return {
        "state": result["state"],
        "project": result.get("project"),
        "selected": [
            {
                key: item[key]
                for key in ("slug", "source_path", "route", "priority", "reasons")
            }
            for item in result["selected"]
        ],
    }


def make_repo(path: Path) -> None:
    path.mkdir()
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "Fixture"],
        ["git", "config", "user.email", "fixture@example.com"],
        ["git", "remote", "add", "origin", "git@github.com:siege-analytics/f23-fixture.git"],
    ):
        subprocess.run(command, cwd=path, check=True)
    (path / "README.md").write_text("consumer runtime fixture\n")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(
        [
            "git",
            "commit",
            "-q",
            "-m",
            "docs: consumer runtime fixture #962\n\nReview-Tier: A\nSelf-Review: focused diff checked",
        ],
        cwd=path,
        check=True,
    )


def main() -> None:
    for form in FORMS:
        if not (ROOT / "dist" / form).is_dir():
            raise AssertionError("full build required before consumer runtime test")

    source_results = {
        case_id: parity_shape(resolve(ROOT / "bin" / "resolve-load-set.py", prompt, repo, cwd=ROOT))
        for case_id, prompt, repo in CASES
    }

    with tempfile.TemporaryDirectory(prefix="ccp-installed-consumers-") as raw:
        temp = Path(raw)
        repo = temp / "clean-repo"
        make_repo(repo)

        for form in FORMS:
            package = temp / "installed packages" / form
            package.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ROOT / "dist" / form, package)

            for relative in RUNTIME_FILES:
                assert (package / relative).is_file(), (form, relative)

            manifest = json.loads((package / "catalog" / "resolver-manifest.json").read_text())
            for source, metadata in manifest["known_by_source"].items():
                target = package / metadata["package_path"]
                assert target.is_file(), (form, source, target)
                characters = len(target.read_text())
                assert metadata["characters"] == characters, (form, source)
                assert metadata["estimated_tokens"] == (characters + 3) // 4, (form, source)

            script = package / "bin" / "resolve-load-set.py"
            results = {}
            for case_id, prompt, origin in CASES:
                result = resolve(script, prompt, origin, cwd=repo)
                results[case_id] = result
                assert parity_shape(result) == source_results[case_id], (form, case_id, result)
                for item in result["selected"]:
                    assert item["source_path"], (form, case_id, item)
                    assert item["load_path"], (form, case_id, item)
                    assert not Path(item["load_path"]).is_absolute(), (form, case_id, item)
                    assert (package / item["load_path"]).is_file(), (form, case_id, item)

            project = results["project-all"]
            assert project["project"] == "siege-utilities", (form, project)
            assert PROJECT_SOURCES <= {item["source_path"] for item in project["selected"]}, (form, project)
            for source in PROJECT_SOURCES:
                # Provenance is canonical and intentionally not the package location.
                assert not (package / source).exists(), (form, source)
            assert not any(
                item["source_path"].startswith("projects/")
                for item in results["foreign-host"]["selected"]
            ), (form, results["foreign-host"])
            assert results["shelf"]["state"] == "unknown" and results["shelf"]["selected"] == [], form
            assert results["unknown"]["state"] == "unknown" and results["unknown"]["selected"] == [], form

            subprocess.run(
                ["git", "remote", "set-url", "origin", EXACT_REPO],
                cwd=repo,
                check=True,
            )
            payload = json.dumps({"prompt": "review this signature and error path", "cwd": str(repo)})
            hook = run(
                ["bash", str(package / "hooks" / "resolver" / "inject-resolver.sh")],
                input_text=payload,
            )
            assert hook.returncode == 0, (form, hook.stdout, hook.stderr)
            assert "project: siege-utilities" in hook.stdout, (form, hook.stdout)
            emitted = re.findall(r"^(?:load|candidate): .*? \| path=(.*?) \| source=(.*?) \|", hook.stdout, re.MULTILINE)
            assert emitted, (form, hook.stdout)
            emitted_project_sources = set()
            for raw_path, source in emitted:
                runtime_path = Path(raw_path)
                assert runtime_path.is_absolute() and runtime_path.is_file(), (form, runtime_path)
                assert runtime_path.resolve().is_relative_to(package.resolve()), (form, runtime_path, package)
                if source.startswith("projects/"):
                    emitted_project_sources.add(source)
            assert PROJECT_SOURCES <= emitted_project_sources, (form, emitted_project_sources)

            push_payload = json.dumps(
                {"tool_input": {"command": "git push origin HEAD"}, "cwd": str(repo)}
            )
            push = run(
                ["bash", str(package / "hooks" / "git" / "self-review.sh")],
                input_text=push_payload,
            )
            assert push.returncode == 0, (form, push.stdout, push.stderr)

    print("consumer_runtime_test: PASS (4 isolated layouts, prompt/path/push/parity/negative coverage)")


if __name__ == "__main__":
    main()
