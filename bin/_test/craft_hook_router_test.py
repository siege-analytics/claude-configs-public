#!/usr/bin/env python3
"""Disposable registry/protocol controls; actual vendor delivery is separate UAT."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import craft_workspace_trust_test as fixtures

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("craft_router_installer_test", ROOT / "bin/install-craft-hook-router.py")
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)
r = install.router
SDK_ID = "ffe0010a-0000-4000-8000-000000000000"


class Router(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.Trust(methodName="runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home, self.workspace = self.fixture.home, self.fixture.workspace
        self.policy_path = self.workspace / ".claude/craft-settings.json"
        self.policy_path.write_bytes(self.fixture.settings.read_bytes())
        shutil.copytree(ROOT / "hooks", self.workspace / "hooks", dirs_exist_ok=True)
        legacy = json.loads(self.fixture.settings.read_text())
        self.foreign = {"type": "command", "command": "/operator/hooks/git/pre-push-self-review.sh"}
        legacy["hooks"]["PreToolUse"][0]["hooks"].append(self.foreign)
        self.fixture.settings.write_text(json.dumps(legacy))
        self.original_global = {"permissions": {"allow": ["operator-rule"]}, "operatorSecret": "synthetic-secret",
                                "hooks": {"PreToolUse": [{"matcher": "Bash", "operatorLabel": "keep",
                                                          "hooks": [copy.deepcopy(self.foreign)]}]}}
        self.fixture.user_settings.write_text(json.dumps(self.original_global))
        self.session = self.workspace / "sessions/one"
        self.session.mkdir(parents=True)
        (self.session / "session.jsonl").write_text(json.dumps({"id": "one", "sdkSessionId": SDK_ID}) + "\n")
        self.target = r.router_path(self.home, self.workspace)
        self.env = {**os.environ, "HOME": str(self.home), "CRAFT_SESSION_DIR": str(self.session), "CRAFT_IS_PACKAGED": "true"}
        self.receipt_path = self.workspace / ".claude/craft-hook-registration.json"
        self.authority = patch.object(install.trust, "source_authority", return_value=fixtures.REV)
        self.authority.start()
        self.addCleanup(self.authority.stop)
        self.pinned = patch.object(install, "source_bytes", side_effect=lambda revision, relative, apply: (ROOT / relative).read_bytes())
        self.pinned.start()
        self.addCleanup(self.pinned.stop)

    def activate(self):
        return install.install(self.workspace, self.home, apply=True)

    def payload(self, event="PreToolUse", tool="Bash", command="printf READ_OK"):
        value = {"hook_event_name": event, "session_id": SDK_ID, "cwd": str(self.workspace),
                 "tool_name": tool, "tool_use_id": "toolu_fixture", "tool_input": {"command": command},
                 "prompt": "PRIVATE_PROMPT_MARKER_DO_NOT_LOG"}
        return json.dumps(value).encode()

    def route(self, raw=None, event="PreToolUse", env=None):
        with patch.object(r, "craft_ancestry", return_value=True), patch.object(r, "RUNNING_ROUTER_PATH", self.target):
            return r.route(raw or self.payload(event), event, self.workspace, env or self.env)

    def main(self, raw, event="PreToolUse"):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(r, "craft_ancestry", return_value=True), patch.object(r, "RUNNING_ROUTER_PATH", self.target), \
             patch.object(sys, "argv", [str(self.target), "--workspace", str(self.workspace), "--event", event]), \
             patch.object(sys, "stdin", io.TextIOWrapper(io.BytesIO(raw))), patch.dict(os.environ, self.env, clear=True), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = r.main()
        return code, stdout.getvalue(), stderr.getvalue()

    def test_preview_preserves_all_files_and_native_cli_skips_before_policy(self):
        before = self.fixture.user_settings.read_bytes()
        result = install.install(self.workspace, self.home)
        self.assertEqual(result["mode"], "preview")
        self.assertEqual(self.fixture.user_settings.read_bytes(), before)
        self.assertFalse(self.target.exists())
        with patch.object(r, "registration", side_effect=AssertionError("policy read")), patch.object(r, "craft_ancestry", side_effect=AssertionError("ancestry read")):
            self.assertEqual(r.route(b"not JSON", "PreToolUse", self.workspace, {}), (0, None, ""))
            other = {"CRAFT_SESSION_DIR": str(self.fixture.base / "other/sessions/two")}
            self.assertEqual(r.route(b"not JSON", "PreToolUse", self.workspace, other), (0, None, ""))
        cli = subprocess.run([sys.executable, str(ROOT / install.ROUTER_SOURCE), "--workspace", str(self.workspace), "--event", "PreToolUse"],
                             input="not JSON", text=True, capture_output=True, env={"PATH": os.environ["PATH"], "HOME": str(self.home)}, timeout=30)
        self.assertEqual((cli.returncode, cli.stdout, cli.stderr), (0, "", ""))

    def test_native_bootstrap_skips_missing_router_and_enrolled_missing_denies(self):
        missing = self.fixture.base / "missing router's $literal.py"
        command = r.command_for(missing, self.workspace, "PreToolUse")
        native = {"PATH": os.environ["PATH"], "HOME": str(self.home)}
        result = subprocess.run(command, shell=True, input="not JSON", env=native,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        enrolled = {**native, "CRAFT_SESSION_DIR": str(self.session)}
        result = subprocess.run(command, shell=True, input="not JSON", env=enrolled,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("router missing", result.stderr)
        self.assertEqual(r.own_registration(command, missing, self.workspace), "PreToolUse")
        self.assertIsNone(r.own_registration(command + " ; true", missing, self.workspace))
        # Startup/import/interpreter failures happen before Python's guarded
        # main; the outer SDK bootstrap must still return the blocking code.
        missing.write_text('raise RuntimeError("synthetic startup failure")\n')
        for environment in (enrolled, {**enrolled, "PATH": ""}):
            result = subprocess.run(command, shell=True, input="not JSON", env=environment,
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
        result = subprocess.run(command, shell=True, input="not JSON", env=native,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_known_legacy_bootstrap_migrates_but_is_never_valid_registration(self):
        global_settings = copy.deepcopy(self.original_global)
        for event in r.EVENTS:
            entry = {"hooks": [{"type": "command", "command": shlex.join(
                ["python3", "-I", "-B", str(self.target), "--workspace", str(self.workspace), "--event", event]), "timeout": 120}]}
            if event != "UserPromptSubmit":
                entry["matcher"] = ".*"
            global_settings["hooks"].setdefault(event, []).append(entry)
        self.fixture.user_settings.write_text(json.dumps(global_settings))
        with self.assertRaises(r.RoutingError):
            r.verify_global(global_settings, self.target, self.workspace)
        self.activate()
        installed = json.loads(self.fixture.user_settings.read_text())
        r.verify_global(installed, self.target, self.workspace)
        self.assertNotIn('python3 -I -B ' + str(self.target), self.fixture.user_settings.read_text())

    def test_global_legacy_enforcement_flag_requires_operator_cleanup(self):
        global_settings = copy.deepcopy(self.original_global)
        global_settings["env"] = {"CLAUDE_CA_ENFORCE": "1", "OPERATOR_FLAG": "preserve"}
        before = json.dumps(global_settings).encode()
        self.fixture.user_settings.write_bytes(before)
        with self.assertRaisesRegex(r.RoutingError, "native CLI"):
            self.activate()
        self.assertEqual(self.fixture.user_settings.read_bytes(), before)
        self.assertFalse(self.receipt_path.exists())
        global_settings["env"]["CLAUDE_CA_ENFORCE"] = "operator-value"
        self.fixture.user_settings.write_text(json.dumps(global_settings))
        self.activate()
        self.assertEqual(json.loads(self.fixture.user_settings.read_text())["env"], global_settings["env"])

    def test_global_exact_policy_duplicate_refuses_before_mutation(self):
        policy = json.loads(self.policy_path.read_text())
        own = next(iter(r.workspace_policy_commands(policy, self.workspace)))
        duplicate = copy.deepcopy(self.original_global)
        duplicate["hooks"]["PreToolUse"].append({"matcher": ".*", "hooks": [{"type": "command", "command": own}]})
        before = json.dumps(duplicate).encode()
        self.fixture.user_settings.write_bytes(before)
        with self.assertRaises(r.RoutingError):
            self.activate()
        self.assertEqual(self.fixture.user_settings.read_bytes(), before)
        self.assertFalse(self.receipt_path.exists())

    def test_tool_matchers_use_whole_names(self):
        def selected(matcher, tool):
            policy = {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [{"type": "command", "command": "true"}]}]}}
            return [command for command, _ in r.matching_hooks(policy, "PreToolUse", {"tool_name": tool})]
        self.assertEqual(selected("Write", "Write"), ["true"])
        self.assertEqual(selected("Write", "TodoWrite"), [])
        for tool in ("MultiEdit", "NotebookEdit"):
            self.assertEqual(selected("Edit", tool), [])
        self.assertEqual(selected("Edit|MultiEdit", "MultiEdit"), ["true"])

    def test_pretool_json_denials_cannot_be_masked_by_allow(self):
        for denial in ({"decision": "block"}, {"continue": False}):
            output = (0, json.dumps(denial), "")
            code, value, _ = r.aggregate("PreToolUse", [output])
            self.assertEqual(code, 0)
            self.assertEqual(value["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertNotIn("decision", value)
            for decision in ("allow", "ask"):
                permission = (0, json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision}}), "")
                for outputs in ([output, permission], [permission, output]):
                    with self.assertRaises(r.RoutingError):
                        r.aggregate("PreToolUse", outputs)
        _, value, _ = r.aggregate("PreToolUse", [(2, json.dumps({"decision": "approve", "continue": True}), "denied")])
        self.assertEqual(value["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("decision", value)
        self.assertNotIn("continue", value)

    def test_enrollment_resolution_errors_fail_closed_inside_main(self):
        with patch.object(r, "maybe_enrolled", side_effect=OSError("enrollment path unavailable")):
            code, output, diagnostics = self.main(self.payload())
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("failed closed", diagnostics)
        with patch.dict(self.env, {}, clear=True), patch.object(r, "maybe_enrolled", side_effect=AssertionError("native path resolution")):
            self.assertEqual(self.main(b"not JSON"), (0, "", ""))

    def test_activation_migrates_only_owned_commands_and_is_idempotent(self):
        auth, cli_config = self.fixture.auth.read_bytes(), self.fixture.config.read_bytes()
        result = self.activate()
        self.assertTrue(result["local_registration_verified"])
        self.assertEqual(self.fixture.auth.read_bytes(), auth)
        self.assertEqual(self.fixture.config.read_bytes(), cli_config)  # Trust is optional, not blanket activation.
        global_settings = json.loads(self.fixture.user_settings.read_text())
        self.assertEqual(global_settings["permissions"], self.original_global["permissions"])
        self.assertEqual(global_settings["operatorSecret"], "synthetic-secret")
        self.assertEqual(global_settings["hooks"]["PreToolUse"][0], self.original_global["hooks"]["PreToolUse"][0])
        legacy = json.loads(self.fixture.settings.read_text())
        self.assertEqual(legacy["operatorSetting"], "keep")
        self.assertIn(self.foreign, legacy["hooks"]["PreToolUse"][0]["hooks"])
        for groups in legacy["hooks"].values():
            for group in groups:
                self.assertFalse(any(h.get("command", "").startswith(str(self.workspace / "hooks")) for h in group["hooks"]))
        self.assertFalse(self.activate()["changed"])
        r.verify_global(global_settings, self.target, self.workspace)

    def test_duplicate_owned_registrations_dedupe_but_other_workspace_survives(self):
        self.activate()
        settings = json.loads(self.fixture.user_settings.read_text())
        settings["hooks"]["PreToolUse"].append(copy.deepcopy(settings["hooks"]["PreToolUse"][-1]))
        other_ws = self.fixture.base / "other"
        other_target = r.router_path(self.home, other_ws)
        other_group = {"matcher": ".*", "hooks": [{"type": "command", "command": r.command_for(other_target, other_ws, "PreToolUse")}]}
        settings["hooks"]["PreToolUse"].append(other_group)
        self.fixture.user_settings.write_text(json.dumps(settings))
        self.activate()
        after = json.loads(self.fixture.user_settings.read_text())
        r.verify_global(after, self.target, self.workspace)
        self.assertIn(other_group, after["hooks"]["PreToolUse"])

    def test_corrupt_missing_and_changed_enrolled_generation_fail_closed(self):
        self.activate()
        self.receipt_path.write_text("{")
        code, stdout, stderr = self.main(self.payload())
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("PRIVATE_PROMPT", stdout + stderr)
        self.activate()  # Owned corrupt receipt is repairable from accepted source.
        self.receipt_path.unlink()
        self.assertEqual(self.main(self.payload())[0], 2)
        self.activate()
        self.policy_path.write_text(self.policy_path.read_text() + "\n")
        self.assertEqual(self.main(self.payload())[0], 2)

    def test_real_mutation_guard_receives_original_payload_and_denies_effect(self):
        self.activate()
        code, value, _ = self.route()
        self.assertEqual(code, 0, value)
        marker = self.workspace / "must-not-exist"
        command = "printf denied > " + str(marker)
        code, value, _ = self.route(self.payload(command=command))
        self.assertEqual(code, 2, value)
        self.assertEqual(value["hookSpecificOutput"]["permissionDecision"], "deny")
        if code == 0:
            subprocess.run(command, shell=True, check=True, timeout=30)
        self.assertFalse(marker.exists())
        audit = (self.session / "data/craft-hook-router-events.jsonl").read_text()
        self.assertNotIn("PRIVATE_PROMPT", audit)
        self.assertNotIn(command, audit)
        self.assertEqual(json.loads(audit.splitlines()[-1])["verdict"], "deny")

    def test_pending_identity_does_not_borrow_env_task_and_reads_remain_possible(self):
        self.activate()
        (self.session / "session.jsonl").write_text(json.dumps({"id": "one"}) + "\n")
        env = {**self.env, "CLAUDE_SESSION_ID": "another-session", "CCP_TASK_ID": "other/task#1"}
        code, value, _ = self.route(event="UserPromptSubmit", env=env)
        self.assertEqual(code, 0)
        self.assertIn("No task authority", value["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(self.route(env=env)[0], 0)
        self.assertEqual(self.route(self.payload(command="touch must-not-exist"), env=env)[0], 2)

    def test_unique_header_identity_corrects_stale_env_without_turn_anchor(self):
        self.activate()
        other = self.workspace / "sessions/two"
        other.mkdir()
        (other / "session.jsonl").write_text(json.dumps({"id": "two", "sdkSessionId": "aaa0010a-0000-4000-8000-000000000000"}) + "\n")
        with patch.object(r, "RUNNING_ROUTER_PATH", self.target):
            _, env, bound = r.session_context(self.payload(), "PreToolUse", {**self.env, "CRAFT_SESSION_DIR": str(other)})
        self.assertTrue(bound)
        self.assertEqual(env["CRAFT_SESSION_DIR"], str(self.session))
        (other / "session.jsonl").write_text(json.dumps({"id": "two", "sdkSessionId": SDK_ID}) + "\n")
        with patch.object(r, "RUNNING_ROUTER_PATH", self.target):
            _, env, bound = r.session_context(self.payload(), "PreToolUse", self.env)
        self.assertFalse(bound)
        self.assertNotIn("CRAFT_SESSION_DIR", env)

    def test_unbound_payload_aliases_cannot_authorize_mutations(self):
        self.activate()
        (self.session / "session.jsonl").write_text('{"id":"one"}\n')
        for alias in ({"craftSessionId": "one"}, {"transcript_path": str(self.session / "transcript.jsonl")}):
            value = json.loads(self.payload(tool="Write"))
            value.update(alias)
            value["tool_input"] = {"file_path": str(self.session / "tasks/bootstrap/think-gate.json"), "content": "{}"}
            self.assertEqual(self.route(json.dumps(value).encode())[0], 2)
            value["tool_name"] = "Bash"
            value["tool_input"] = {"command": "touch forbidden"}
            self.assertEqual(self.route(json.dumps(value).encode())[0], 2)
        self.assertEqual(self.route(self.payload(command="printf READ_OK"))[0], 0)

    def test_enrolled_missing_and_malformed_session_binding(self):
        self.activate()
        for marker in (None, "{{SESSION_PATH}}"):
            env = {**self.env, "CRAFT_AGENT_WORKSPACE": str(self.workspace)}
            env.pop("CRAFT_SESSION_DIR", None)
            if marker:
                env["CRAFT_SESSION_DIR"] = marker
            with patch.object(r, "craft_ancestry", return_value=True):
                with self.assertRaises(r.RoutingError):
                    r.route(self.payload(), "PreToolUse", self.workspace, env)
            with patch.object(r, "craft_ancestry", return_value=False):
                self.assertEqual(r.route(self.payload(), "PreToolUse", self.workspace, env), (0, None, ""))

    def test_registered_anchor_provenance_and_ambiguity(self):
        self.activate()
        other = self.workspace / "sessions/two"
        other.mkdir()
        other_id = "aaa0010a-0000-4000-8000-000000000000"
        (other / "session.jsonl").write_text(json.dumps({"id": "two", "sdkSessionId": other_id}) + "\n")
        meta = self.session / "meta"
        meta.mkdir(exist_ok=True)
        anchor = meta / "claude-turn-anchors.json"
        anchor.write_text("unexpected text " + other_id)
        payload = json.loads(self.payload())
        payload["session_id"] = other_id
        def binding():
            with patch.object(r, "RUNNING_ROUTER_PATH", self.target):
                return r.session_context(json.dumps(payload).encode(), "PreToolUse", self.env)
        self.assertEqual(binding()[1]["CRAFT_SESSION_DIR"], str(other))
        mutation = dict(payload, tool_name="Write", tool_input={"file_path": str(self.session / "tasks/borrowed/think-gate.json"), "content": "{}"})
        self.assertEqual(self.route(json.dumps(mutation).encode())[0], 2)
        anchor.write_text(json.dumps({"anchors": {"message": {"sdkSessionId": other_id}}}))
        self.assertFalse(binding()[2])
        anchor.unlink()
        external = self.fixture.base / "external-anchors.json"
        external.write_text(json.dumps({"anchors": {"message": {"sdkSessionId": other_id}}}))
        anchor.symlink_to(external)
        self.assertEqual(binding()[1]["CRAFT_SESSION_DIR"], str(other))

    def test_binding_becoming_ambiguous_cannot_create_uuid_scratch(self):
        self.activate()
        execute = r.execute_hook
        def race(*args, **kwargs):
            other = self.workspace / "sessions/two"
            other.mkdir(exist_ok=True)
            (other / "session.jsonl").write_text(json.dumps({"id": "two", "sdkSessionId": SDK_ID}) + "\n")
            return execute(*args, **kwargs)
        value = json.loads(self.payload(tool="Write"))
        value["craftSessionId"] = SDK_ID
        value["tool_input"] = {"file_path": str(self.workspace / "sessions" / SDK_ID / "tasks/borrowed/think-gate.json"), "content": "{}"}
        with patch.object(r, "execute_hook", side_effect=race):
            self.assertEqual(self.route(json.dumps(value).encode())[0], 2)

    def test_whole_invocation_output_is_bounded(self):
        self.activate()
        with patch.object(r, "matching_hooks", return_value=[("one", 5), ("two", 5)]), \
             patch.object(r, "execute_hook", return_value=(0, "x" * (r.LIMIT // 2 + 1), "")):
            with self.assertRaisesRegex(r.RoutingError, "invocation bound"):
                self.route()

    def test_owned_registration_execution_metadata_must_match(self):
        self.activate()
        original = json.loads(self.fixture.user_settings.read_text())
        for change in ({"type": "prompt"}, {"async": True}, {"timeout": 0.001}):
            value = copy.deepcopy(original)
            owned = value["hooks"]["PreToolUse"][-1]["hooks"][0]
            owned.update(change)
            self.fixture.user_settings.write_text(json.dumps(value))
            with self.assertRaises(r.RoutingError):
                install.verify_registration(self.workspace, self.home)
        disabled = copy.deepcopy(original)
        disabled["disableAllHooks"] = True
        self.fixture.user_settings.write_text(json.dumps(disabled))
        with self.assertRaises(r.RoutingError):
            install.verify_registration(self.workspace, self.home)
        prompt = copy.deepcopy(original)
        prompt["hooks"]["UserPromptSubmit"][-1]["matcher"] = "unexpected"
        self.fixture.user_settings.write_text(json.dumps(prompt))
        with self.assertRaises(r.RoutingError):
            install.verify_registration(self.workspace, self.home)
        self.fixture.user_settings.write_text(json.dumps(original))

    def test_protocol_context_dedupe_explicit_denials_and_conflicts(self):
        context = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "once"}})
        denial = json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "policy"}})
        code, value, stderr = r.aggregate("PreToolUse", [(0, context, "note"), (0, context, "note"), (0, denial, "")])
        self.assertEqual(code, 0)  # SDK JSON denial remains a denial without inventing exit status.
        self.assertEqual(value["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(value["hookSpecificOutput"]["additionalContext"], "once")
        self.assertEqual(stderr, "note")
        code, value, _ = r.aggregate("UserPromptSubmit", [(0, '{"continue":false,"stopReason":"hard stop"}', "")])
        self.assertFalse(value["continue"])
        for data in ({"unknown": True}, {"decision": {}}, {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": []}}):
            with self.assertRaises(r.RoutingError):
                r.aggregate("PreToolUse", [(0, json.dumps(data), "")])
        for field, values in (("updatedInput", [{"x": 1}, {"x": 2}]), ("permissionDecision", ["allow", "deny"])):
            outputs = [(0, json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", field: value}}), "") for value in values]
            with self.assertRaises(r.RoutingError):
                r.aggregate("PreToolUse", outputs)

    def test_policy_hook_env_is_delivered_but_cannot_override_verified_identity(self):
        policy = json.loads(self.policy_path.read_text())
        policy["env"] = {"MANAGED_FLAG": "arrived", "CLAUDE_CA_ENFORCE": "1", "CRAFT_SESSION_DIR": "/stale/session", "CCP_TASK_ID": "wrong/task#9"}
        self.policy_path.write_text(json.dumps(policy))
        self.activate()
        with patch.object(r, "RUNNING_ROUTER_PATH", self.target):
            _, env, bound = r.session_context(self.payload(), "PreToolUse", self.env)
        self.assertTrue(bound)
        self.assertEqual(env["MANAGED_FLAG"], "arrived")
        self.assertEqual(env["CLAUDE_CA_ENFORCE"], "1")
        self.assertEqual(env["CRAFT_SESSION_DIR"], str(self.session))
        self.assertNotIn("CCP_TASK_ID", env)
        code, stdout, _ = r.execute_hook("printf '%s' \"$MANAGED_FLAG\"", self.payload(), env, 2)
        self.assertEqual((code, stdout), (0, "arrived"))
        self.assertNotIn("MANAGED_FLAG", self.env)

    def test_whole_main_budget_covers_pathological_matcher(self):
        self.activate()
        policy = {"hooks": {"PreToolUse": [{"matcher": "(a+)+$", "hooks": [{"type": "command", "command": "true"}]}]}}
        self.policy_path.write_text(json.dumps(policy))
        receipt = json.loads(self.receipt_path.read_text())
        receipt["policy_sha256"] = hashlib.sha256(self.policy_path.read_bytes()).hexdigest()
        self.receipt_path.write_text(json.dumps(receipt))
        raw = self.payload(tool="a" * 80 + "!")
        start = time.monotonic()
        with patch.object(r, "TOTAL_SECONDS", 0.15):
            code, stdout, stderr = self.main(raw)
        self.assertEqual(code, 2)
        self.assertIn("budget", stderr)
        self.assertLess(time.monotonic() - start, 2)
        self.assertEqual(json.loads(stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_large_write_keeps_original_stdin_and_bounded_metadata_with_context(self):
        self.activate()
        (self.session / "data").mkdir(exist_ok=True)
        value = json.loads(self.payload(tool="Write"))
        value["tool_input"] = {"file_path": str(self.session / "data/large-positive.txt"), "content": "x" * 1040000}
        raw = json.dumps(value).encode()
        self.assertLessEqual(len(raw), r.LIMIT)
        environment = {**self.env, "VALID_CONTEXT_PADDING": "p" * 100000}
        execute, observed = r.execute_hook, []
        def capture(command, original, child_environment, timeout):
            self.assertEqual(original, raw)
            metadata = json.loads(child_environment["CCP_HOOK_INPUT_JSON"])
            self.assertEqual(metadata["tool_input"]["content"], "")
            self.assertEqual(metadata["tool_input"]["file_path"], value["tool_input"]["file_path"])
            self.assertLessEqual(len(child_environment["CCP_HOOK_INPUT_JSON"].encode()), 98304)
            self.assertEqual(child_environment["VALID_CONTEXT_PADDING"], "p" * 100000)
            observed.append(True)
            return execute(command, original, child_environment, timeout)
        with patch.object(r, "execute_hook", side_effect=capture):
            self.assertEqual(self.route(raw, env=environment)[0], 0)
        self.assertTrue(observed)
        outside = self.fixture.base / "outside/large-negative.txt"
        value["tool_input"]["file_path"] = str(outside)
        self.assertEqual(self.route(json.dumps(value).encode(), env=environment)[0], 2)
        self.assertFalse(outside.exists())

    def test_metadata_preserves_bash_command_and_enforces_byte_bounds(self):
        command = "echo " + "x" * 5000
        value = json.loads(self.payload(command=command))
        self.assertEqual(json.loads(r.metadata_environment(value))["tool_input"]["command"], command)
        value["tool_input"]["command"] = "é" * 32769
        with self.assertRaisesRegex(r.RoutingError, "64 KiB"):
            r.metadata_environment(value)
        value = json.loads(self.payload(tool="Write"))
        value["tool_input"]["many"] = ["x" * 4000] * 25
        self.assertNotIn("many", json.loads(r.metadata_environment(value))["tool_input"])
        value["cwd"] = "x" * 98305
        with self.assertRaisesRegex(r.RoutingError, "96 KiB"):
            r.metadata_environment(value)

    def test_many_small_edits_keep_original_stdin_and_scope(self):
        self.activate()
        value = json.loads(self.payload(tool="MultiEdit"))
        value['tool_input'] = {'file_path': str(self.session / 'data/large.txt'),
                              'edits': [{'old_string': 'a' * 4000, 'new_string': 'b' * 4000}] * 30}
        raw = json.dumps(value).encode()
        execute, observed = r.execute_hook, []
        def capture(command, original, environment, timeout):
            self.assertEqual(original, raw)
            self.assertEqual(json.loads(environment['CCP_HOOK_INPUT_JSON'])['tool_input']['edits'], [])
            observed.append(True)
            return execute(command, original, environment, timeout)
        with patch.object(r, 'execute_hook', side_effect=capture):
            self.assertEqual(self.route(raw)[0], 0)
        self.assertTrue(observed)
        value['tool_input']['file_path'] = str(self.fixture.base / 'outside.txt')
        self.assertEqual(self.route(json.dumps(value).encode())[0], 2)

    def test_metadata_helper_is_verified_before_import(self):
        self.activate()
        helper = self.workspace / 'hooks/lib/hook_payload.py'
        helper.write_text('raise AssertionError("unverified helper executed")\n')
        with self.assertRaises(r.RoutingError):
            self.route()

    def test_bounded_execution_handles_stdout_stderr_timeout_and_large_stdin(self):
        command = "python3 -c 'import sys; data=sys.stdin.read(); print(len(data)); print(\"diagnostic\", file=sys.stderr)'"
        code, stdout, stderr = r.execute_hook(command, b"x" * 200000, self.env, 3)
        self.assertEqual((code, stdout.strip(), stderr.strip()), (0, "200000", "diagnostic"))
        start = time.monotonic()
        with self.assertRaises(r.RoutingError):
            r.execute_hook("sleep 5", b"x" * 200000, self.env, 0.15)
        self.assertLess(time.monotonic() - start, 2)

    def test_concurrent_cli_change_preserved_and_receipt_stays_inactive(self):
        publish = install.publish
        concurrent = {**self.original_global, "concurrentCli": True}
        def race(path, before, raw):
            if path == self.fixture.user_settings:
                path.write_text(json.dumps(concurrent))
            return publish(path, before, raw)
        with patch.object(install, "publish", side_effect=race), self.assertRaisesRegex(ValueError, "concurrent"):
            self.activate()
        self.assertEqual(json.loads(self.fixture.user_settings.read_text()), concurrent)
        self.assertEqual(json.loads(self.receipt_path.read_text())["state"], "staging")


if __name__ == "__main__":
    unittest.main()
