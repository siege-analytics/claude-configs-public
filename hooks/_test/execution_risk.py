#!/usr/bin/env python3
"""Real hook decisions for task-owned pytest execution; never run pytest."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("task_fixture", ROOT / "hooks/_test/task_keyed_gates.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


class ExecutionRisk(unittest.TestCase):
    def setUp(self):
        self.f = f.Gates()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.repo = self.f.repo
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.test")
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/ci.yml").write_text("name: fixture\n")
        (self.repo / "app.py").write_text("value = 1\n")
        (self.repo / "tests").mkdir()
        (self.repo / "tests/test_app.py").write_text("def test_value(): pass\n")
        self.git("add", "-f", ".")
        self.git("commit", "-qm", "fixture baseline")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/remotes/origin/main", self.base)
        self.gate = self.f.task("example/app#1171", self.repo)
        for name in ("junior-senior-gate.json", "artifacts-posted-gate.json"):
            (self.gate / name).unlink()
        data = json.loads((self.gate / "think-gate.json").read_text())
        data["tier"] = "B"
        f.write(self.gate / "think-gate.json", data)

    def git(self, *args):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", str(self.repo), *args], capture_output=True, text=True, check=True, timeout=10)

    def hook(self, command="pytest", code=0, env=None):
        result = self.f.hook(command, env=env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def test_root_no_selector_uses_execution_floor(self):
        self.hook()
        self.hook("python3 -m pytest -q")
        self.hook("pytest --maxfail=1 -k 'value or other'")
        shape = f.r.action("pytest", str(self.repo))
        self.assertFalse(shape["read_only"])
        self.assertFalse(shape.get("investigation"))

    def test_fixed_cd_and_literal_selectors(self):
        self.hook("cd " + str(self.repo) + " && python3 -m pytest tests/test_app.py -q")
        self.hook("pytest tests -q")

    def test_actual_c_working_staged_and_untracked_changes_stay_c(self):
        workflow = self.repo / ".github/workflows/ci.yml"
        workflow.write_text("name: changed\n")
        self.hook(code=2)
        self.git("add", ".github/workflows/ci.yml")
        self.hook(code=2)
        self.git("reset", "-q", "HEAD", "--", ".github/workflows/ci.yml")
        workflow.write_text("name: fixture\n")
        (self.repo / ".github/workflows/new.yml").write_text("name: new\n")
        self.hook(code=2)

    def test_committed_c_delta_and_deleted_c_stay_c(self):
        workflow = self.repo / ".github/workflows/ci.yml"
        workflow.write_text("name: changed\n")
        self.git("add", ".github/workflows/ci.yml")
        self.git("commit", "-qm", "fixture critical change")
        self.hook(code=2)
        workflow.unlink()
        self.hook(code=2)

    def test_declared_c_and_missing_baseline_stay_c(self):
        data = json.loads((self.gate / "think-gate.json").read_text())
        data["tier"] = "C"
        f.write(self.gate / "think-gate.json", data)
        self.hook(code=2)
        data["tier"] = "B"
        f.write(self.gate / "think-gate.json", data)
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        self.hook(code=2)

    def test_missing_baseline_is_c_even_without_any_c_source(self):
        self.git("rm", ".github/workflows/ci.yml")
        self.git("commit", "-qm", "fixture remove critical source")
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        data = json.loads((self.gate / "think-gate.json").read_text())
        verdict = f.r.task_tier(data, [str(self.repo)], "pytest", str(self.repo))
        self.assertEqual(verdict["floor"], "C")
        self.assertIn("baseline", " ".join(verdict["reasons"]))

    def test_incomparable_protected_bases_stay_c(self):
        (self.repo / "app.py").write_text("value = 2\n")
        self.git("add", "app.py")
        self.git("commit", "-qm", "fixture left")
        left = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/remotes/origin/main", left)
        self.git("checkout", "-qb", "fixture-right", self.base)
        (self.repo / "tests/test_app.py").write_text("def test_other(): pass\n")
        self.git("add", "tests/test_app.py")
        self.git("commit", "-qm", "fixture right")
        right = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/remotes/origin/develop", right)
        self.git("merge", "--no-ff", "--no-edit", left)
        self.hook(code=2)

    def test_listing_failure_is_c(self):
        original = f.r._git_lines
        def listing(repo, *arguments):
            if arguments[:2] == ("ls-files", "--others"):
                return None
            return original(repo, *arguments)
        data = json.loads((self.gate / "think-gate.json").read_text())
        with patch.object(f.r, "_git_lines", side_effect=listing):
            verdict = f.r.task_tier(data, [str(self.repo)], "pytest", str(self.repo))
        self.assertEqual(verdict["floor"], "C")
        self.assertIn("cannot enumerate", " ".join(verdict["reasons"]))

    def test_unknown_options_wrappers_and_mixed_mutations_stay_conservative(self):
        for command in ["pytest -p arbitrary", "pytest -c pytest.ini", "pytest --junitxml=out.xml", "env pytest", "python3 -c 'import pytest; pytest.main()'", "pytest && touch app.py", "pytest > result.txt", "pytest tests/*.py"]:
            with self.subTest(command=command):
                self.hook(command, 2)

        self.assertIsNone(f.r._pytest_execution_targets('pytest "', str(self.repo), str(self.repo)))

    def test_ordinary_changes_and_c_selector(self):
        (self.repo / "app.py").write_text("value = 2\n")
        self.hook()
        self.hook("pytest .github/workflows/ci.yml", 2)

    def test_task_lifecycle_and_cross_task_authority_unchanged(self):
        data = json.loads((self.gate / "think-gate.json").read_text())
        data["status"] = "designing"
        f.write(self.gate / "think-gate.json", data)
        self.hook(code=2)
        data["status"] = "implementing"
        data["scope_paths"] = [str(self.repo / "tests")]
        f.write(self.gate / "think-gate.json", data)
        self.hook(code=2)


if __name__ == "__main__":
    unittest.main()
