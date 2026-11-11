#!/usr/bin/env python3
"""Bounded own-directory ENOENT retry for registered session binding (#1284).

Craft replaces sessions/<id>/session.jsonl non-atomically, so for a few
milliseconds the path does not exist. Only the env-named directory's header,
and only ENOENT from opening it, is read again within a fixed backoff; every
other failure, foreign directory and multi-match keeps its fail-closed result.
"""
import errno
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("session_anchor_enoent_under_test", ROOT / "hooks/lib/session_anchor.py")
anchor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anchor)
SDK = "ffe0010a-0000-4000-8000-000000000000"
OTHER = "aaa0010a-0000-4000-8000-000000000000"
ATTEMPTS = 5  # one read plus four retries; pinned so a shrunken backoff cannot pass vacuously


class OwnHeaderEnoent(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = os.path.realpath(temporary.name)
        self.sessions = os.path.join(self.workspace, "sessions")
        self.own = self.session("one", SDK)
        self.payload = {"session_id": SDK}
        self.sleeps = []
        sleeper = patch.object(anchor, "_sleep", side_effect=self.sleeps.append)
        sleeper.start()
        self.addCleanup(sleeper.stop)

    def session(self, name, sdk_id=None, raw=None):
        directory = os.path.join(self.sessions, name)
        os.makedirs(directory, exist_ok=True)
        header = {"id": name} if sdk_id is None else {"id": name, "sdkSessionId": sdk_id}
        with open(os.path.join(directory, "session.jsonl"), "w") as stream:
            stream.write((json.dumps(header) + "\n") if raw is None else raw)
        return directory

    def failing_open(self, directory, count, code=errno.ENOENT):
        """Patch os.open to raise `code` for directory's header on its first `count` opens."""
        path = os.path.join(directory, "session.jsonl")
        real, calls = os.open, []

        def fake(target, flags, *args, **kwargs):
            if target == path:
                calls.append(target)
                if len(calls) <= count:
                    raise OSError(code, os.strerror(code), target)
            return real(target, flags, *args, **kwargs)
        return patch.object(anchor.os, "open", fake), calls

    def bind(self, env_dir=None):
        return anchor.registered_session_binding(self.workspace, env_dir or self.own, self.payload)

    def test_backoff_is_fixed_short_and_bounded(self):
        backoff = anchor.OWN_HEADER_ENOENT_BACKOFF
        self.assertEqual(len(backoff), ATTEMPTS - 1)
        self.assertTrue(all(0 < seconds <= 0.01 for seconds in backoff))
        self.assertLessEqual(sum(backoff), 0.03)

    def test_happy_path_binds_without_any_sleep(self):
        bound, diagnostic = self.bind()
        self.assertEqual(bound, self.own)
        self.assertEqual(self.sleeps, [])
        self.assertEqual(diagnostic, {"result": "bound", "check": "ok", "own_check": "ok",
                                      "own_enoent_retries": 0, "matches": 1, "env_matched": True})
        self.assertEqual(anchor.registered_session_dir(self.workspace, self.own, self.payload), self.own)

    def test_transient_own_enoent_within_the_bound_binds(self):
        for count in range(1, ATTEMPTS):
            with self.subTest(enoent=count):
                del self.sleeps[:]
                patcher, calls = self.failing_open(self.own, count)
                with patcher:
                    bound, diagnostic = self.bind()
                self.assertEqual(bound, self.own)
                self.assertEqual(len(calls), count + 1)
                self.assertEqual(self.sleeps, list(anchor.OWN_HEADER_ENOENT_BACKOFF[:count]))
                self.assertEqual((diagnostic["check"], diagnostic["own_enoent_retries"]), ("ok", count))

    def test_enoent_beyond_the_bound_fails_closed_after_fixed_attempts(self):
        self.assertLessEqual(sum(anchor.OWN_HEADER_ENOENT_BACKOFF), 0.03)
        for count in (ATTEMPTS, 1000):
            with self.subTest(enoent=count):
                del self.sleeps[:]
                patcher, calls = self.failing_open(self.own, count)
                with patcher:
                    bound, diagnostic = self.bind()
                self.assertEqual(bound, "")
                self.assertEqual(len(calls), ATTEMPTS)
                self.assertEqual(self.sleeps, list(anchor.OWN_HEADER_ENOENT_BACKOFF))
                self.assertEqual((diagnostic["result"], diagnostic["check"], diagnostic["own_check"]),
                                 ("unbound", "enoent", "enoent"))

    def test_real_filesystem_replacement_window_binds(self):
        header = os.path.join(self.own, "session.jsonl")
        aside = header + ".aside"
        os.rename(header, aside)

        def restore_on_second_sleep(seconds):
            self.sleeps.append(seconds)
            if len(self.sleeps) == 2:
                os.rename(aside, header)
        with patch.object(anchor, "_sleep", side_effect=restore_on_second_sleep):
            bound, diagnostic = self.bind()
        self.assertEqual(bound, self.own)
        self.assertEqual(diagnostic["own_enoent_retries"], 2)

    def test_real_missing_header_beyond_the_bound_fails_closed(self):
        os.unlink(os.path.join(self.own, "session.jsonl"))
        bound, diagnostic = self.bind()
        self.assertEqual((bound, diagnostic["check"], diagnostic["own_enoent_retries"]), ("", "enoent", ATTEMPTS - 1))

    def test_non_enoent_oserror_is_not_retried(self):
        for code in (errno.EACCES, errno.ELOOP, errno.EIO):
            with self.subTest(errno=errno.errorcode[code]):
                del self.sleeps[:]
                patcher, calls = self.failing_open(self.own, 1, code)
                with patcher:
                    bound, diagnostic = self.bind()
                self.assertEqual((bound, len(calls), self.sleeps), ("", 1, []))
                self.assertEqual(diagnostic["check"], "oserror")

    def test_nlink_parse_and_identity_failures_are_not_retried(self):
        header = os.path.join(self.own, "session.jsonl")
        os.link(header, os.path.join(self.workspace, "second-link"))
        self.assertEqual(self.bind()[1]["check"], "nlink")
        os.unlink(os.path.join(self.workspace, "second-link"))
        cases = {"parse": "{not json\n",
                 "id-mismatch": json.dumps({"id": "elsewhere", "sdkSessionId": SDK}) + "\n",
                 "sdk-id-invalid": json.dumps({"id": "one", "sdkSessionId": "not-a-uuid"}) + "\n"}
        cases["parse-duplicate"] = '{"id":"one","id":"one","sdkSessionId":"%s"}\n' % SDK
        for name, raw in cases.items():
            with self.subTest(check=name):
                self.session("one", raw=raw)
                bound, diagnostic = self.bind()
                self.assertEqual(bound, "")
                self.assertEqual(diagnostic["check"], name.split("-duplicate")[0])
        self.assertEqual(self.sleeps, [])

    def test_non_env_directory_enoent_is_never_retried(self):
        # The env names a sibling (#1099 mis-tag) while the payload's real
        # session is mid-replacement. Only the env-named header is ever retried,
        # so the real session is read once, the correction a race-free read
        # would make is missed, and the binding stays unresolved: fail closed,
        # exactly as on base.
        env_dir = self.session("two", OTHER)
        patcher, calls = self.failing_open(self.own, 1)
        with patcher:
            bound, diagnostic = self.bind(env_dir)
        self.assertEqual((bound, len(calls), self.sleeps), ("", 1, []))
        self.assertEqual((diagnostic["check"], diagnostic["own_check"], diagnostic["env_matched"]),
                         ("no-match", "ok", False))

    def test_retry_reproduces_the_race_free_read_only(self):
        # Whatever the env dir's header says, a transient ENOENT on it must give
        # exactly the race-free result: correction, no match or multi-match.
        layouts = {
            "mis-tag corrected": [("two", OTHER)],
            "mis-tag no claim": [("two", OTHER), ("one", None)],
            "multi-match": [("two", SDK)],
        }
        for label, sessions in layouts.items():
            with self.subTest(layout=label):
                for name, sdk_id in sessions:
                    self.session(name, sdk_id)
                env_dir = os.path.join(self.sessions, "two")
                clean = self.bind(env_dir)
                patcher, _ = self.failing_open(env_dir, 2)
                with patcher:
                    raced = self.bind(env_dir)
                self.assertEqual(raced[0], clean[0])
                self.assertEqual(raced[1]["check"], clean[1]["check"])
                self.session("one", SDK)
                os.unlink(os.path.join(env_dir, "session.jsonl"))
                os.rmdir(env_dir)

    def test_multi_match_still_fails_closed_with_transient_own_enoent(self):
        self.session("two", SDK)
        patcher, _ = self.failing_open(self.own, 2)
        with patcher:
            bound, diagnostic = self.bind()
        self.assertEqual(bound, "")
        self.assertEqual((diagnostic["check"], diagnostic["matches"], diagnostic["env_matched"]), ("multi-match", 2, True))

    def test_router_bound_child_hook_reverification_survives_the_window(self):
        environment = {"CCP_CRAFT_ROUTER_BOUND_SDK_ID": SDK, "CRAFT_AGENT_WORKSPACE": self.workspace}
        with patch.dict(os.environ, environment):
            os.environ.pop("CCP_CRAFT_ROUTER_SESSION_UNRESOLVED", None)
            patcher, _ = self.failing_open(self.own, 3)
            with patcher:
                self.assertEqual(anchor.verified_session_dir(self.own, self.payload), self.own)
            self.assertNotIn("CCP_CRAFT_ROUTER_SESSION_UNRESOLVED", os.environ)
            patcher, _ = self.failing_open(self.own, ATTEMPTS)
            with patcher:
                self.assertEqual(anchor.verified_session_dir(self.own, self.payload), "")
            self.assertEqual(os.environ.get("CCP_CRAFT_ROUTER_SESSION_UNRESOLVED"), "1")

    def test_diagnostic_carries_no_paths(self):
        os.unlink(os.path.join(self.own, "session.jsonl"))
        _, diagnostic = self.bind()
        self.assertNotIn(self.workspace, json.dumps(diagnostic))
        self.assertEqual(set(diagnostic), {"result", "check", "own_check", "own_enoent_retries", "matches", "env_matched"})


if __name__ == "__main__":
    unittest.main()
