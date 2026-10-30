#!/usr/bin/env python3
"""Supported workspace trust updates use synthetic config only, never user state."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin/craft-workspace-trust.py"
spec = importlib.util.spec_from_file_location("workspace_trust", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
REV = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, timeout=30).strip()


class Trust(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="craft-trust-", dir="/private/tmp" if Path("/private/tmp").exists() else None)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir(mode=0o700)
        self.config = self.home / ".claude.json"
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        (self.workspace / ".claude").mkdir()
        hooks = {}
        for event, relative in m.CORE_HOOKS.items():
            path = self.workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(m.reviewed_bytes(REV, relative))
            path.chmod(0o755)
            groups = []
            tools = [None] if event == "UserPromptSubmit" else ["Bash", "Edit", "MultiEdit", "NotebookEdit", "Write"]
            for tool in tools:
                group = {"hooks": [{"type": "command", "command": str(path)}]}
                if tool:
                    group["matcher"] = tool
                groups.append(group)
            hooks[event] = groups
        self.settings = self.workspace / ".claude/settings.json"
        self.settings.write_text(json.dumps({"hooks": hooks, "operatorSetting": "keep"}))
        self.stamp = self.workspace / "deploy-stamp.json"
        self.stamp.write_text(json.dumps({"commit": REV, "immutable_source": True,
                                         "repo_root": str(ROOT), "timestamp": "2026-10-30T00:00:00Z",
                                         "verification": {"stage": "artifact-bytes", "file_count": 42,
                                                          "files_sha256": "a" * 64}}))
        self.original = {"oauthAccount": {"token": "synthetic-operator-secret"}, "numStartups": 8,
                         "projects": {str(self.workspace): {"hasTrustDialogAccepted": False, "allowedTools": ["Read"]},
                                      "/synthetic/cli-only": {"hasTrustDialogAccepted": False, "operator": True}}}
        self.config.write_text(json.dumps(self.original, indent=4))
        self.config.chmod(0o600)
        (self.home / ".claude").mkdir()
        self.user_settings = self.home / ".claude/settings.json"
        self.user_settings.write_text('{"hooks":{},"permissions":{"mode":"operator"}}')
        self.auth = self.home / ".claude/credentials.json"
        self.auth.write_text('{"credential":"synthetic"}')

    def apply(self):
        with patch.object(m, "source_authority", return_value=REV):
            return m.enable(self.workspace, self.config, apply=True)

    def test_preview_and_real_cli_preview_do_not_write_or_expose_config(self):
        raw = self.config.read_bytes()
        with patch.object(m, "source_authority", side_effect=AssertionError("preview queried main")):
            result = m.enable(self.workspace, self.config)
        self.assertEqual(result["mode"], "preview")
        self.assertTrue(result["changed"])
        self.assertEqual(self.config.read_bytes(), raw)
        self.assertFalse((self.home / ".claude-workspace-trust-backups").exists())
        cli = subprocess.run([sys.executable, str(SCRIPT), "--workspace", str(self.workspace), "--config", str(self.config)],
                             text=True, capture_output=True, env={**os.environ, "HOME": str(self.home)}, timeout=15)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertNotIn("synthetic-operator-secret", cli.stdout + cli.stderr)
        self.assertEqual(self.config.read_bytes(), raw)

    def test_apply_changes_one_field_preserves_cli_auth_and_private_backup(self):
        raw = self.config.read_bytes()
        other_files = (self.user_settings.read_bytes(), self.auth.read_bytes(), self.settings.read_bytes())
        with patch.object(m, "source_authority", return_value=REV) as authority:
            result = m.enable(self.workspace, self.config, apply=True)
        self.assertEqual(authority.call_count, 2)
        expected = copy.deepcopy(self.original)
        expected["projects"][str(self.workspace)]["hasTrustDialogAccepted"] = True
        self.assertEqual(json.loads(self.config.read_text()), expected)
        self.assertEqual((self.user_settings.read_bytes(), self.auth.read_bytes(), self.settings.read_bytes()), other_files)
        backup = Path(result["backup"])
        self.assertEqual((backup / "before.json").read_bytes(), raw)
        self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((backup / "before.json").stat().st_mode), 0o600)
        self.assertTrue(result["verified"])
        after = self.config.read_bytes()
        count = len(list(backup.parent.iterdir()))
        second = self.apply()
        self.assertFalse(second["changed"])
        self.assertEqual(self.config.read_bytes(), after)
        self.assertEqual(len(list(backup.parent.iterdir())), count)

    def test_missing_config_can_be_created_without_inventing_other_fields(self):
        self.config.unlink()
        result = self.apply()
        self.assertEqual(json.loads(self.config.read_text()), {"projects": {str(self.workspace): {"hasTrustDialogAccepted": True}}})
        receipt = json.loads((Path(result["backup"]) / "receipt.json").read_text())
        self.assertFalse(receipt["before_exists"])

    def test_malformed_duplicate_and_nonregular_config_fail_closed(self):
        for raw in (b"{", b"[]", b'{"projects":[],"operator":true}', b'{"projects":{},"projects":{}}', b'{"x":NaN}'):
            self.config.write_bytes(raw)
            with self.assertRaises((ValueError, OSError)):
                self.apply()
            self.assertEqual(self.config.read_bytes(), raw)
        self.config.unlink()
        foreign = self.home / "operator.json"
        foreign.write_text(json.dumps(self.original))
        self.config.symlink_to(foreign)
        with self.assertRaises((ValueError, OSError)):
            self.apply()
        self.config.unlink()
        os.link(foreign, self.config)
        with self.assertRaises((ValueError, OSError)):
            self.apply()
        self.config.unlink()
        os.mkfifo(self.config)
        with self.assertRaises((ValueError, OSError)):
            self.apply()
        self.assertEqual(json.loads(foreign.read_text()), self.original)

    def test_prewrite_concurrent_cli_change_is_preserved_and_not_published_over(self):
        stage = m.stage_config
        concurrent = {**self.original, "concurrentCliCounter": 99}
        def race(path, value):
            staged = stage(path, value)
            path.write_text(json.dumps(concurrent))
            return staged
        with patch.object(m, "stage_config", side_effect=race), self.assertRaisesRegex(ValueError, "concurrent"):
            self.apply()
        self.assertEqual(json.loads(self.config.read_text()), concurrent)
        self.assertFalse(any(path.is_file() for path in self.home.glob(".claude-workspace-trust-*")))

    def test_postwrite_concurrent_change_is_not_blindly_rolled_back(self):
        exchange = m.exchange_paths
        def race(source, target):
            exchange(source, target)
            current = json.loads(self.config.read_text())
            current["concurrentCliCounter"] = 100
            self.config.write_text(json.dumps(current))
        with patch.object(m, "exchange_paths", side_effect=race), self.assertRaisesRegex(ValueError, "without blind rollback"):
            self.apply()
        self.assertEqual(json.loads(self.config.read_text())["concurrentCliCounter"], 100)

    def test_atomic_exchange_detects_last_moment_writer_and_restores_it(self):
        exchange = m.exchange_paths
        concurrent = {**self.original, "concurrentCliCounter": 101}
        calls = []
        def race(source, target):
            if not calls:
                target.write_text(json.dumps(concurrent))
            calls.append(1)
            exchange(source, target)
        with patch.object(m, "exchange_paths", side_effect=race), self.assertRaisesRegex(ValueError, "concurrent"):
            self.apply()
        self.assertEqual(json.loads(self.config.read_text()), concurrent)
        self.assertEqual(len(calls), 2)

    def test_atomic_create_does_not_overwrite_racing_creator(self):
        path = self.home / "absent.json"
        staged = m.stage_config(path, {"ours": True})
        link = os.link
        concurrent = b'{"operator":true}'
        def race(source, target):
            target.write_bytes(concurrent)
            link(source, target)
        try:
            with patch.object(m.os, "link", side_effect=race), self.assertRaisesRegex(ValueError, "concurrent"):
                m.publish_staged(path, {"raw": None, "fingerprint": None}, staged)
            self.assertEqual(path.read_bytes(), concurrent)
        finally:
            staged.unlink(missing_ok=True)

    def test_third_writer_during_compensation_is_preserved_with_prior_version(self):
        path = self.home / "exchange.json"
        path.write_bytes(b"initial")
        before = m.snapshot(path)
        staged = m.stage_config(path, {"ours": True})
        exchange = m.exchange_paths
        calls = []
        def race(source, target):
            if len(calls) == 0:
                target.write_bytes(b"first-operator")
            elif len(calls) == 1:
                target.write_bytes(b"third-writer")
            calls.append(1)
            exchange(source, target)
        try:
            with patch.object(m, "exchange_paths", side_effect=race), self.assertRaisesRegex(ValueError, "retained"):
                m.publish_staged(path, before, staged)
            self.assertEqual(path.read_bytes(), b"third-writer")
            retained = [p.read_bytes() for folder in self.home.glob(".craft-publish-recovery-*") for p in folder.iterdir() if p.is_file()]
            self.assertIn(b"first-operator", retained)
            self.assertEqual(len(calls), 3)
        finally:
            staged.unlink(missing_ok=True)

    def test_racing_symlink_is_retained_without_following_external_bytes(self):
        path = self.home / "symlink-race.json"
        path.write_bytes(b"initial")
        before = m.snapshot(path)
        staged = m.stage_config(path, {"ours": True})
        external = self.home / "operator-external.json"
        external.write_bytes(b"private-operator-version")
        exchange = m.exchange_paths
        def race(source, target):
            target.unlink()
            target.symlink_to(external)
            exchange(source, target)
        try:
            with patch.object(m, "exchange_paths", side_effect=race), self.assertRaisesRegex(ValueError, "retained"):
                m.publish_staged(path, before, staged)
            links = [p for folder in self.home.glob(".craft-publish-recovery-*") for p in folder.iterdir() if p.is_symlink()]
            self.assertEqual(len(links), 1)
            self.assertEqual(os.readlink(links[0]), str(external))
            self.assertEqual(external.read_bytes(), b"private-operator-version")
        finally:
            staged.unlink(missing_ok=True)

    def test_legacy_project_environment_retires_only_exact_owned_flag(self):
        spec = importlib.util.spec_from_file_location("legacy_environment_installer", ROOT / "bin/install-craft-hook-router.py")
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        original = {"env": {"CLAUDE_CA_ENFORCE": "1", "OPERATOR_OPTION": "keep"}, "permissions": {"allow": ["keep"]}}
        self.assertEqual(installer.retire_project(original, set()),
                         {"env": {"OPERATOR_OPTION": "keep"}, "permissions": {"allow": ["keep"]}})
        self.assertEqual(original["env"]["CLAUDE_CA_ENFORCE"], "1")
        self.assertEqual(installer.retire_project({"env": {"CLAUDE_CA_ENFORCE": "1"}}, set()), {})
        for value in ("0", "operator-value", 1, True):
            altered = {"env": {"CLAUDE_CA_ENFORCE": value, "OPERATOR_OPTION": "keep"}}
            self.assertEqual(installer.retire_project(altered, set()), altered)

    def test_exchange_then_interrupt_retains_displaced_operator_version(self):
        path = self.home / "interrupted-exchange.json"
        path.write_bytes(b"operator-original")
        before = m.snapshot(path)
        staged = m.stage_config(path, {"ours": True})
        exchange = m.exchange_paths
        def interrupted(source, target):
            exchange(source, target)
            raise KeyboardInterrupt()
        try:
            with patch.object(m, "exchange_paths", side_effect=interrupted), self.assertRaisesRegex(ValueError, "not verified.*retained"):
                m.publish_staged(path, before, staged)
            self.assertEqual(json.loads(path.read_text()), {"ours": True})
            versions = [p.read_bytes() for folder in self.home.glob(".craft-publish-recovery-*") for p in folder.iterdir() if p.name.startswith("displaced-")]
            self.assertIn(b"operator-original", versions)
        finally:
            staged.unlink(missing_ok=True)

    def test_displaced_version_is_rechecked_before_success_cleanup(self):
        path = self.home / "cleanup-race.json"
        path.write_bytes(b"operator-original")
        before = m.snapshot(path)
        staged = m.stage_config(path, {"ours": True})
        exchange, snapshot = m.exchange_paths, m.snapshot
        swapped = []
        def mark(source, target):
            exchange(source, target)
            swapped.append(source)
        def race(target, **kwargs):
            value = snapshot(target, **kwargs)
            if target == path and swapped:
                swapped[0].write_bytes(b"late-operator-version")
            return value
        try:
            with patch.object(m, "exchange_paths", side_effect=mark), patch.object(m, "snapshot", side_effect=race), self.assertRaisesRegex(ValueError, "retained"):
                m.publish_staged(path, before, staged)
            versions = [p.read_bytes() for folder in self.home.glob(".craft-publish-recovery-*") for p in folder.iterdir() if p.name.startswith("displaced-")]
            self.assertIn(b"late-operator-version", versions)
        finally:
            staged.unlink(missing_ok=True)

    def test_unsupported_exchange_does_not_replace_target(self):
        before = self.config.read_bytes()
        with patch.object(m, "exchange_paths", side_effect=OSError("unsupported filesystem")), self.assertRaisesRegex(ValueError, "retained"):
            self.apply()
        self.assertEqual(self.config.read_bytes(), before)

    def test_stale_stamp_changed_hook_and_incomplete_registration_are_not_trusted(self):
        before = self.config.read_bytes()
        stamp = json.loads(self.stamp.read_text())
        stamp["commit"] = "b" * 40
        self.stamp.write_text(json.dumps(stamp))
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.apply()
        stamp["commit"] = REV
        self.stamp.write_text(json.dumps(stamp))
        path = self.workspace / m.CORE_HOOKS["PreToolUse"]
        original = path.read_bytes()
        path.write_bytes(original + b"\n# unreviewed\n")
        with self.assertRaisesRegex(ValueError, "differ"):
            self.apply()
        path.write_bytes(original)
        settings = json.loads(self.settings.read_text())
        settings["hooks"]["PreToolUse"].pop()
        self.settings.write_text(json.dumps(settings))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            self.apply()
        self.assertEqual(self.config.read_bytes(), before)

    def test_source_change_and_workspace_change_abort_before_config_replace(self):
        before = self.config.read_bytes()
        with patch.object(m, "source_authority", side_effect=[REV, "b" * 40]), self.assertRaisesRegex(ValueError, "source changed"):
            m.enable(self.workspace, self.config, apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        stage = m.stage_config
        def race(path, value):
            staged = stage(path, value)
            self.settings.write_text(self.settings.read_text() + "\n")
            return staged
        with patch.object(m, "stage_config", side_effect=race), self.assertRaisesRegex(ValueError, "workspace changed"):
            self.apply()
        self.assertEqual(self.config.read_bytes(), before)

    def test_real_cli_branch_apply_cannot_write_config_or_backups(self):
        before = self.config.read_bytes()
        source = self.base / "unmerged-source"
        (source / "bin").mkdir(parents=True)
        (source / ".claude").mkdir()
        for name in ("build.py", "craft-workspace-trust.py"):
            (source / "bin" / name).write_bytes((ROOT / "bin" / name).read_bytes())
        (source / ".claude/deploy-model").write_text("merge-then-deploy\n")
        git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        def git(*args):
            subprocess.run(["git", "-C", str(source), *args], env=git_env, check=True, capture_output=True, timeout=30)
        git("init", "-b", "main")
        git("config", "user.name", "Fixture")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "core.hooksPath", os.devnull)
        git("add", ".")
        git("commit", "-m", "fixture main")
        git("update-ref", "refs/remotes/origin/main", "HEAD")
        git("commit", "--allow-empty", "-m", "unmerged fixture")
        cli = subprocess.run([sys.executable, str(source / "bin/craft-workspace-trust.py"), "--workspace", str(self.workspace), "--config", str(self.config), "--apply"],
                             text=True, capture_output=True, env={**os.environ, "HOME": str(self.home)}, timeout=45)
        self.assertEqual(cli.returncode, 2, cli.stdout + cli.stderr)
        self.assertNotIn("Traceback", cli.stderr)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.home / ".claude-workspace-trust-backups").exists())


if __name__ == "__main__":
    unittest.main()
