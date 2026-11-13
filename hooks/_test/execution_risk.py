#!/usr/bin/env python3
"""Real hook decisions for task-owned pytest execution; never run pytest."""
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
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

    def assert_c_risk_with_owned_execution(self, command="pytest"):
        data = json.loads((self.gate / "think-gate.json").read_text())
        verdict = f.r.task_tier(data, [str(self.repo)], command, str(self.repo))
        self.assertEqual(verdict['effective'], 'C', verdict)
        self.hook(command)

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
        self.assert_c_risk_with_owned_execution()
        self.git("add", ".github/workflows/ci.yml")
        self.assert_c_risk_with_owned_execution()
        self.git("reset", "-q", "HEAD", "--", ".github/workflows/ci.yml")
        workflow.write_text("name: fixture\n")
        (self.repo / ".github/workflows/new.yml").write_text("name: new\n")
        self.assert_c_risk_with_owned_execution()

    def test_committed_c_delta_and_deleted_c_stay_c(self):
        workflow = self.repo / ".github/workflows/ci.yml"
        workflow.write_text("name: changed\n")
        self.git("add", ".github/workflows/ci.yml")
        self.git("commit", "-qm", "fixture critical change")
        self.assert_c_risk_with_owned_execution()
        workflow.unlink()
        self.assert_c_risk_with_owned_execution()

    def test_declared_c_and_missing_baseline_stay_c(self):
        data = json.loads((self.gate / "think-gate.json").read_text())
        data["tier"] = "C"
        f.write(self.gate / "think-gate.json", data)
        self.assert_c_risk_with_owned_execution()
        data["tier"] = "B"
        f.write(self.gate / "think-gate.json", data)
        self.git("update-ref", "-d", "refs/remotes/origin/main")
        self.assert_c_risk_with_owned_execution()

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
        self.assert_c_risk_with_owned_execution()

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

    def test_execution_risk_does_not_authorize_foreign_effects_or_unresolved_shapes(self):
        owned = ["env pytest", "env -i CI=1 pytest", "timeout 5 pytest", "nice pytest", "pytest -p arbitrary", "pytest -c pytest.ini",
                 "pytest --junitxml=out.xml", "pytest && touch app.py", "pytest > result.txt"]
        for command in owned:
            with self.subTest(command=command):
                self.assert_c_risk_with_owned_execution(command)
        foreign = str(self.f.ws / 'outside-task.xml')
        for command in ['env unknown-runner test', "python3 -c 'import pytest; pytest.main()'", 'pytest tests/*.py',
                        'pytest --junitxml=' + foreign, 'pytest > ' + foreign, 'pytest && touch ' + foreign,
                        'env pytest --junitxml=' + foreign, 'env pytest > ' + foreign,
                        'env HOME=' + str(self.f.ws / 'outside-home') + ' pytest']:
            with self.subTest(command=command):
                self.hook(command, 2)
        self.assertIsNone(f.r._pytest_execution_targets('pytest "', str(self.repo), str(self.repo)))

    def test_ordinary_changes_and_c_selector(self):
        (self.repo / "app.py").write_text("value = 2\n")
        self.hook()
        self.assert_c_risk_with_owned_execution("pytest .github/workflows/ci.yml")

    def test_ignored_directory_selectors_include_c_and_preserve_b(self):
        critical = self.repo / 'hooks/bash'
        benign = self.repo / 'tests/ignored-only'
        critical.mkdir(parents=True); benign.mkdir()
        (critical / 'test_risk.py').write_text('def test_risk(): pass\n')
        (benign / 'test_local.py').write_text('def test_local(): pass\n')
        (self.repo / '.gitignore').write_text('hooks/bash/\ntests/ignored-only/\n')
        self.git('add','.gitignore'); self.git('commit','-qm','fixture ignore selected tests')
        self.hook('pytest tests/ignored-only')
        self.assert_c_risk_with_owned_execution('pytest hooks')
        paths = f.r._pytest_execution_targets('pytest hooks',str(self.repo),str(self.repo))
        self.assertIn('hooks/bash/test_risk.py',paths)

    def test_explicit_directory_listing_failure_cannot_lower_floor(self):
        original = f.r._git_lines
        def listing(repo,*arguments):
            if arguments[:4] == ('ls-files','--cached','--others','-z'):
                return None
            return original(repo,*arguments)
        data = json.loads((self.gate / 'think-gate.json').read_text())
        with patch.object(f.r,'_git_lines',side_effect=listing):
            verdict=f.r.task_tier(data,[str(self.repo)],'pytest tests',str(self.repo))
        self.assertEqual(verdict['floor'],'C')
        self.assertIn('cannot list explicit test selector',' '.join(verdict['reasons']))

    def reported_1171_forms(self):
        """Forms reported in #1171 that the bounded pytest risk view does not model."""
        interpreter = shlex.quote(os.path.realpath(sys.executable))
        cd = "cd " + str(self.repo) + " && "
        flagged = 'python3 -m pytest -o addopts="" -p no:cacheprovider -q -W ignore tests/test_app.py'
        return [
            (interpreter + ' -B -m pytest -p no:cacheprovider -o addopts="" -q', self.repo),
            (cd + interpreter + ' -B -m pytest -p no:cacheprovider -o addopts="" tests/test_app.py -q --no-header -x', self.repo),
            (flagged, self.repo),
            (cd + flagged, self.f.ws),  # session cwd outside the task's checkout
            ("gh issue close 5", self.repo),
        ]

    def test_reported_1171_forms_need_only_owned_implementing_task(self):
        # The fixture task has no junior/senior or artifacts-posted companion.
        # Whole-tree risk for an unmodeled shape is not a refusal by itself.
        self.assertFalse((self.gate / "junior-senior-gate.json").exists())
        self.assertFalse((self.gate / "artifacts-posted-gate.json").exists())
        for command, cwd in self.reported_1171_forms():
            with self.subTest(command=command):
                result = self.f.hook(command, cwd=cwd)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_reported_1171_forms_keep_task_lifecycle_and_scope(self):
        data = json.loads((self.gate / "think-gate.json").read_text())
        for status, scope, reason in (("designing", [str(self.repo)], "not allowed during designing"),
                                      ("implementing", [str(self.repo / "tests")], "Unscoped mutation")):
            f.write(self.gate / "think-gate.json", {**data, "status": status, "scope_paths": scope})
            for command, cwd in self.reported_1171_forms():
                with self.subTest(status=status, scope=scope, command=command):
                    result = self.f.hook(command, cwd=cwd)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertIn(reason, result.stderr)

    def test_reported_1171_forms_cannot_borrow_a_foreign_session_task(self):
        # Another session's Task, even with every companion present, lends no authority.
        shutil.rmtree(self.gate)
        self.f.task("example/app#1171", self.repo, sid="two")
        for command, cwd in self.reported_1171_forms():
            with self.subTest(owner="two", command=command):
                result = self.f.hook(command, cwd=cwd)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertIn("Unscoped mutation", result.stderr)
        # Control: the identical Task in the current session does authorize, so
        # session ownership is the only difference behind the refusal above.
        self.f.task("example/app#1171", self.repo, sid="one")
        for command, cwd in self.reported_1171_forms():
            with self.subTest(owner="one", command=command):
                result = self.f.hook(command, cwd=cwd)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_inline_python_import_remains_opaque_execution(self):
        # Reported with #1171, but refused by the inline-execution boundary, not by risk tier.
        result = self.hook('python -c "import app; print(app.__file__)"', 2)
        self.assertIn("opaque inline execution", result.stderr)

    def test_task_lifecycle_and_cross_task_authority_unchanged(self):
        data = json.loads((self.gate / "think-gate.json").read_text())
        data["status"] = "designing"
        f.write(self.gate / "think-gate.json", data)
        self.hook(code=2)
        self.hook("env pytest", code=2)
        data["status"] = "implementing"
        data["scope_paths"] = [str(self.repo / "tests")]
        f.write(self.gate / "think-gate.json", data)
        self.hook(code=2)
        self.hook("env pytest", code=2)


if __name__ == "__main__":
    unittest.main()
