#!/usr/bin/env python3
"""Real-hook acceptance for the owned, task-bound test receipt execution lane."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = ROOT / "hooks/lib/test-evidence.py"


class ReceiptLane(unittest.TestCase):
    def setUp(self):
        self.g = fixture.Gates(methodName="runTest")
        self.g.setUp()
        self.addCleanup(self.g.tearDown)
        self.repo = self.g.repo
        self.env = dict(self.g.env, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.org",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.org")
        (self.repo / "app.py").write_text("VALUE = 1\n")
        (self.repo / "util.py").write_text("VALUE = 2\n")
        self.git("add", "app.py", "util.py")
        self.git("commit", "-q", "-m", "fixture")
        self.identity = "o/r#386"
        self.directory = self.g.ws / "sessions/one/tasks" / fixture.r.task_slug(self.identity)
        self.think = self.directory / "think-gate.json"
        self.output = self.directory / "test-gate.json"
        self.marker = self.repo / "tests-executed"

    def git(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], env=self.env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)

    def argv(self, *, producer=PRODUCER, think=None, output=None, repo=None, source="app.py"):
        return [sys.executable, "-B", str(producer), "record", "--repo", str(repo or self.repo),
                "--think-gate", str(think or self.think), "--output", str(output or self.output),
                "--source", source, "--framework", "fixture", "--", sys.executable, "-c",
                "from pathlib import Path; Path('tests-executed').write_text('ran')"]

    def command(self, argv):
        return "CCP_TASK_ID=" + shlex.quote(self.identity) + " " + shlex.join(argv)

    def hook(self, argv, *, command=None):
        payload = fixture.craft_payload(tool_name="Bash", cwd=str(self.repo),
                                        tool_input={"command": command or self.command(argv)})
        return subprocess.run(["bash", str(ROOT / "hooks/bash/universal-mutation-gate.sh")],
                              input=json.dumps(payload), text=True, capture_output=True,
                              env=self.env, timeout=20)

    def assert_denied(self, argv, *, command=None):
        before = self.output.read_bytes() if self.output.exists() else None
        result = self.hook(argv, command=command)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists())
        self.assertEqual(self.output.read_bytes() if self.output.exists() else None, before)
        return result

    def implementing(self, *, artifacts=True):
        self.g.task(self.identity, self.repo, artifacts=artifacts)

    def test_no_gate_designing_and_missing_tier_evidence_deny_before_execution(self):
        argv = self.argv()
        argv[argv.index("--"):argv.index("--")] = ["--source", "util.py"]
        self.assert_denied(argv)
        self.g.task(self.identity, self.repo, status="designing", artifacts=False)
        self.assertIn("implementing", self.assert_denied(argv).stderr)
        self.implementing(artifacts=False)
        data = json.loads(self.think.read_text())
        data["tier"] = "A"
        self.think.write_text(json.dumps(data))
        result = self.assert_denied(argv)
        self.assertIn("review tier", result.stderr)
        self.implementing()
        result = self.hook(argv)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        actual = subprocess.run(argv, env=self.env, cwd=self.repo, text=True, capture_output=True, timeout=120)
        self.assertEqual(actual.returncode, 0, actual.stdout + actual.stderr)
        self.assertEqual(self.marker.read_text(), "ran")
        receipt = json.loads(self.output.read_text())
        self.assertEqual(receipt["exit_code"], 0)
        self.assertEqual([entry["source"] for entry in receipt["evidence"]], ["app.py", "util.py"])
        self.assertEqual(receipt["ticket"], self.identity)

    def test_sibling_gate_and_receipt_cannot_borrow_selected_task(self):
        self.implementing()
        sibling = self.g.task("o/r#387", self.repo)
        for argv in (self.argv(think=sibling / "think-gate.json"),
                     self.argv(output=sibling / "test-gate.json"),
                     self.argv(think=sibling / "think-gate.json", output=sibling / "test-gate.json")):
            self.assertIn("ownership", self.assert_denied(argv).stderr)
        self.assertFalse((sibling / "test-gate.json").exists())

    def test_owned_runner_is_not_an_invented_write_or_scratch_read(self):
        from task_actions import action
        shape = action(self.command(self.argv()), str(self.repo))
        self.assertFalse(shape["read_only"])
        self.assertFalse(shape["investigation"])
        self.assertFalse(shape["self_managed_shape"])
        self.assertEqual(set(shape["paths"]), {str(self.repo), str(self.repo / "app.py")})
        self.assertNotIn(str(PRODUCER), shape["paths"])
        self.assertNotIn(str(self.output), shape["paths"])
        scratch_repo = self.g.ws / "sessions/one/data/repo"
        scratch_repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(scratch_repo)], env=self.env, check=True, timeout=120)
        (scratch_repo / "app.py").write_text("VALUE = 1\n")
        self.assert_denied(self.argv(repo=scratch_repo))

    def test_source_only_task_cannot_authorize_repository_computation(self):
        self.g.task(self.identity, self.repo / "app.py")
        self.assert_denied(self.argv())

    def test_producer_filename_as_mutation_operand_is_not_execution_intent(self):
        self.implementing()
        source = self.repo / "test-evidence.py"
        source.write_text("fixture")
        for command in ("touch " + shlex.quote(str(source)),
                        "rm " + shlex.quote(str(source)),
                        "mv " + shlex.quote(str(source)) + " renamed.py",
                        "chmod 600 " + shlex.quote(str(source))):
            result = self.hook([], command="CCP_TASK_ID=" + shlex.quote(self.identity) + " " + command)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_foreign_copied_renamed_and_symlink_runner_do_not_acquire_lane(self):
        self.implementing()
        copied = self.repo / "test-evidence.py"
        renamed = self.repo / "renamed.py"
        alias = self.repo / "producer-alias.py"
        shutil.copy2(PRODUCER, copied)
        shutil.copy2(PRODUCER, renamed)
        alias.symlink_to(PRODUCER)
        for producer in (copied, renamed, alias):
            self.assertIn("exact", self.assert_denied(self.argv(producer=producer)).stderr)
        fake_interpreter = self.repo / "python3"
        fake_interpreter.write_text("#!/bin/sh\ntouch tests-executed\n")
        fake_interpreter.chmod(0o755)
        argv = self.argv()
        argv[0] = str(fake_interpreter)
        self.assertIn("known Python", self.assert_denied(argv).stderr)

    def test_source_and_receipt_aliases_and_noncanonical_cli_deny(self):
        self.implementing()
        foreign = self.g.ws / "foreign.json"
        foreign.write_text("preserve")
        self.output.symlink_to(foreign)
        self.assert_denied(self.argv())
        self.assertEqual(foreign.read_text(), "preserve")
        self.output.unlink()
        os.link(foreign, self.output)
        self.assert_denied(self.argv())
        self.assertEqual(foreign.read_text(), "preserve")
        self.output.unlink()
        alias_gate = self.directory / "gate-alias.json"
        alias_gate.symlink_to(self.think)
        self.assert_denied(self.argv(think=alias_gate))
        for source in ("../outside.py", "/outside.py", "./app.py", "sub/../app.py"):
            self.assert_denied(self.argv(source=source))
        malformed = self.argv()
        malformed[malformed.index("--"):malformed.index("--")] = ["--output", str(self.output)]
        self.assert_denied(malformed)
        self.assert_denied(self.argv(), command=self.command(self.argv()) + " && echo opaque")
        other = self.g.ws / "other"
        other.mkdir()
        (self.repo / "linked").symlink_to(other, target_is_directory=True)
        self.assert_denied(self.argv(source="linked/app.py"))


if __name__ == "__main__":
    unittest.main()
