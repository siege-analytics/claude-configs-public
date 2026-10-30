#!/usr/bin/env python3
"""Synthetic real-effects controls for #1122 and P0.9; never user remotes."""
import json
import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import unittest

import task_keyed_gates as fixture

ROOT = Path(__file__).resolve().parents[2]


class Safety(unittest.TestCase):
    def setUp(self):
        self.g = fixture.Gates(methodName="runTest")
        self.g.setUp()
        self.addCleanup(self.g.tearDown)
        self.repo = self.g.repo
        self.env = dict(self.g.env, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.org",
                        GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.org")
        self.git("checkout", "-q", "-B", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "seed")
        self.git("remote", "add", "origin", "https://github.com/siege-analytics/synthetic.git")

    def test_read_guard_and_native_shell_descendants_leave_inventory_unchanged(self):
        directory = self.repo.parent / "bytecode-control"
        directory.mkdir()
        for name in ("git_command.py", "task_actions.py"):
            shutil.copy2(ROOT / "hooks/lib" / name, directory / name)
        def inventory():
            return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
        env = dict(self.env)
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env.pop("PYTHONPYCACHEPREFIX", None)
        before = inventory()
        result = subprocess.run([sys.executable, str(directory / "git_command.py"), "--cwd", str(self.repo), "--policy", "branch"],
                                input="git status", env=env, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(inventory(), before)
        (directory / "payload.py").write_text("VALUE = 1\n")
        (directory / "child.py").write_text("import payload, sys; print(sys.dont_write_bytecode)\n")
        shell = directory / "child.sh"
        shell.write_text("#!/bin/sh\nexec " + shlex.join([sys.executable, str(directory / "child.py")]) + "\n")
        vector = ["sh", str(shell)]
        binding = json.dumps({"git_repo": str(self.repo), "hooks_root": str(directory)})
        driver = directory / "driver.py"
        driver.write_text("import sys, json\nsys.path.insert(0, " + repr(str(ROOT / "bin")) + ")\nimport native_git as n\n"
                          + "n.registration.git = lambda *a: 'missing-pending.json'\n"
                          + "n.registration.verify_runtime = lambda b: {'adapter': 'siege-compatibility'}\n"
                          + "n.ep.read_json = lambda p: {'hooks': {'PreToolUse': [{'hooks': [{'command': " + repr(shlex.join(vector)) + "}]}]}}\n"
                          + "raise SystemExit(n.main(['settings', '--binding', " + repr(binding) + ", '--command', " + repr(json.dumps(vector)) + "]))\n")
        before = inventory()
        # -B on the adapter alone is not inherited by its shell's Python child.
        result = subprocess.run([sys.executable, "-B", str(driver)], cwd=self.repo, env=env,
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")
        self.assertEqual(inventory(), before)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], env=self.env,
                                       text=True, stderr=subprocess.PIPE, timeout=120).strip()

    def hook(self, name, command, cwd=None):
        payload = fixture.craft_payload(tool_name="Bash", cwd=str(cwd or self.repo),
                                        tool_input={"command": command})
        return subprocess.run(["bash", str(ROOT / name)], input=json.dumps(payload),
                              env=self.env, text=True, capture_output=True, timeout=20)

    def assert_denied_without_effect(self, hook, command, path, cwd=None):
        before = path.read_bytes() if path.exists() else None
        result = self.hook(hook, command, cwd)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        # This is the actual dispatch boundary: denied candidates never run.
        if result.returncode == 0:
            subprocess.run(command, shell=True, cwd=cwd or self.repo, env=self.env, check=True, timeout=120)
        self.assertEqual(path.read_bytes() if path.exists() else None, before)

    def test_malformed_reader_syntax_grants_no_read_authority(self):
        from task_actions import _python_read, _reader_globs, UnknownShape
        self.assertFalse(_python_read(['python3', '-I', '-c', 'if']))
        spec = importlib.util.spec_from_file_location('reader_syntax_control', ROOT / 'hooks/lib/read-only-command.py')
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        self.assertEqual(reader.lead_verbs("cat '"), {'?'})
        self.assertNotEqual(reader.main("cat '"), 0)
        # Attached option values may contain patterns; expansion in the key is
        # never a value. This also exercises the nested offset capture.
        _reader_globs(['grep', '--include=*.py'], [(), (10,)])
        with self.assertRaises(UnknownShape):
            _reader_globs(['grep', '--include=*.py'], [(), (2,)])

    def test_base64_exact_option_grammar_is_portable(self):
        for command in ("base64 --decode input", "base64 -D -i input", "base64 --wrap=0 input", "base64 -w0 input"):
            result = subprocess.run([sys.executable, str(ROOT / "hooks/lib/read-only-command.py"), command], timeout=120)
            self.assertEqual(result.returncode, 0, command)
        for command in ("base64 -o foreign input", "base64 -oforeign input", "base64 --output=foreign input",
                        "base64 --out=foreign input", "base64 --unknown input", "git show --textc HEAD:file"):
            result = subprocess.run([sys.executable, str(ROOT / "hooks/lib/read-only-command.py"), command], timeout=120)
            self.assertEqual(result.returncode, 3, command)

    def test_darwin_base64_output_and_stdout(self):
        if sys.platform != "darwin":
            self.skipTest("Run on macOS for the Darwin base64 -o real-effects control")
        source = self.repo / "input.b64"
        source.write_text("YWJj\n")
        output = self.g.ws / "foreign-decoded"
        command = "base64 -D -i " + shlex.quote(str(source)) + " -o " + shlex.quote(str(output))
        subprocess.run(command, shell=True, cwd=self.repo, env=self.env, check=True, timeout=120)
        self.assertEqual(output.read_bytes(), b"abc")
        output.unlink()
        self.assert_denied_without_effect("hooks/bash/universal-mutation-gate.sh", command, output)
        read = "base64 -D -i " + shlex.quote(str(source))
        self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", read).returncode, 0)
        self.assertEqual(subprocess.check_output(read, shell=True, env=self.env, timeout=120), b"abc")

    def test_cp_abbreviated_output_controls(self):
        cp = shutil.which("gcp") or shutil.which("cp")
        version = subprocess.run([cp, "--version"], text=True, capture_output=True, timeout=120)
        if "GNU" not in version.stdout:
            self.skipTest("Install GNU coreutils cp for the real abbreviation effects control")
        bindir = self.g.ws / "bin"
        bindir.mkdir()
        (bindir / "cp").symlink_to(cp)
        self.env["PATH"] = str(bindir) + os.pathsep + self.env["PATH"]
        scratch = self.g.ws / "sessions/one/data"
        scratch.mkdir()
        (scratch / "notes.md").write_text("changed")
        foreign = self.g.ws / "foreign"
        foreign.mkdir()
        for command in ("cp notes.md " + shlex.quote(str(foreign / "f")) + " --su .bak",
                        "cp --target-d " + shlex.quote(str(foreign)) + " notes.md"):
            target = foreign / ("notes.md" if "--target-d" in command else "f")
            target.write_text("keep")
            subprocess.run(command, shell=True, cwd=scratch, env=self.env, check=True, timeout=120)
            self.assertEqual(target.read_text(), "changed")
            target.write_text("keep")
            self.assert_denied_without_effect("hooks/bash/universal-mutation-gate.sh", command, target, scratch)
        self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", "cp notes.md copy.md", scratch).returncode, 0)

    def test_textconv_is_execution_not_a_reader(self):
        marker = self.g.ws / "textconv-ran"
        converter = self.g.ws / "converter.sh"
        converter.write_text("#!/bin/sh\nprintf ran > " + shlex.quote(str(marker)) + "\ncat \"$1\"\n")
        converter.chmod(0o755)
        (self.repo / ".gitattributes").write_text("*.dat diff=fixture\n")
        (self.repo / "file.dat").write_text("contents")
        self.git("add", ".gitattributes", "file.dat")
        self.git("commit", "-q", "-m", "fixture")
        self.git("config", "diff.fixture.textconv", str(converter))
        command = "git show --textconv HEAD:file.dat"
        subprocess.run(command, shell=True, cwd=self.repo, env=self.env, check=True, stdout=subprocess.DEVNULL, timeout=120)
        self.assertTrue(marker.exists())
        marker.unlink()
        self.assert_denied_without_effect("hooks/bash/universal-mutation-gate.sh", command, marker)
        for safe in ("git show --no-textconv HEAD:file.dat", "git reflog -8 --date=iso",
                     "ls -d .; git reflog -8 --date=iso", "cat file.dat | head -1 | wc -l"):
            self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", safe).returncode, 0, safe)
        for unsafe in ("git reflog expire --expire=now --all", "git reflog delete HEAD@{0}"):
            self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", unsafe).returncode, 2, unsafe)
        self.g.task("o/r#textconv", self.repo)
        self.assert_denied_without_effect("hooks/bash/universal-mutation-gate.sh", command, marker)

    def test_test_modules_and_bytecode_are_not_ungated_diagnostics(self):
        for command in ("pytest tests/test_fixture.py", "python3 -m pytest tests/test_fixture.py",
                        "python3 -m py_compile fixture.py", "hostname synthetic-host"):
            self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", command).returncode, 2, command)
        for command in ("hostname", "hostname -s", "python3 -I -B -c 'import json; print(json.loads(\"{}\"))'"):
            self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", command).returncode, 0, command)

    def test_actual_git_target_and_authorized_trailer_are_not_borrowed(self):
        outer = self.g.ws / "outer"
        subprocess.run(["git", "init", "-q", "-b", "feature/outer", str(outer)], env=self.env, check=True, timeout=120)
        subprocess.run(["git", "-C", str(outer), "commit", "-q", "--allow-empty", "-m",
                        "outer\n\nAuthorized: unrelated fixture"], env=self.env, check=True, timeout=120)
        commit = "git -C " + shlex.quote(str(self.repo)) + " commit --allow-empty -m 'Refs: #1122'"
        force = "git -C " + shlex.quote(str(self.repo)) + " push --force local HEAD:main"
        self.assertEqual(self.hook("hooks/git/branch-guard.sh", commit, outer).returncode, 2)
        self.assertEqual(self.hook("hooks/bash/destructive-guard.sh", force, outer).returncode, 2)
        self.git("checkout", "-q", "-b", "feature/target")
        subprocess.run(["git", "-C", str(outer), "checkout", "-q", "-b", "main"], env=self.env, check=True, timeout=120)
        self.assertEqual(self.hook("hooks/git/branch-guard.sh", commit, outer).returncode, 0)

    def test_protected_git_variants_with_active_task_preserve_refs(self):
        self.g.task("o/r#1122", self.repo)
        self.git("config", "alias.ci", "commit")
        self.git("config", "alias.pf", "push --force")
        bare = self.g.ws / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], env=self.env, check=True, timeout=120)
        self.git("remote", "add", "local", str(bare))
        self.git("push", "-q", "local", "HEAD:main")
        before = subprocess.check_output(["git", "--git-dir=" + str(bare), "rev-parse", "refs/heads/main"], text=True, timeout=120).strip()
        self.git("commit", "-q", "--allow-empty", "-m", "new local head")
        head = self.git("rev-parse", "HEAD")
        prefixes = ["git", "git -C " + shlex.quote(str(self.repo)),
                    "git -C " + shlex.quote(str(self.g.ws)) + " -C repo",
                    "git -c color.ui=never", "g''it", '"git"', "g\\it", shlex.quote(shutil.which("git")),
                    "env LANG=C git -C " + shlex.quote(str(self.repo))]
        # A legitimate implementing task admits the ordinary canonical shape;
        # operation policy must still independently reject protected actions.
        self.assertEqual(self.hook("hooks/bash/universal-mutation-gate.sh", "git commit -m 'Refs: #1122'").returncode, 0)
        for prefix in prefixes:
            admitted = self.hook("hooks/bash/universal-mutation-gate.sh", prefix + " commit -m 'Refs: #1122'")
            self.assertEqual(admitted.returncode, 0, prefix + admitted.stderr)
            for hook, suffix in (("hooks/git/branch-guard.sh", " commit --allow-empty -m 'Refs: #1122'"),
                                 ("hooks/bash/destructive-guard.sh", " push --force local HEAD:main")):
                result = self.hook(hook, prefix + suffix)
                self.assertEqual(result.returncode, 2, prefix + suffix + result.stderr)
                if result.returncode == 0:
                    subprocess.run(prefix + suffix, shell=True, cwd=self.repo, env=self.env, check=True, timeout=120)
                self.assertEqual(self.git("rev-parse", "HEAD"), head)
                after = subprocess.check_output(["git", "--git-dir=" + str(bare), "rev-parse", "refs/heads/main"], text=True, timeout=120).strip()
                self.assertEqual(after, before)
        for hook, command in (("hooks/git/branch-guard.sh", "git ci --allow-empty -m 'Refs: #1122'"),
                              ("hooks/bash/destructive-guard.sh", "git pf local HEAD:main")):
            self.assertEqual(self.hook(hook, command).returncode, 2, command)
        marker = self.g.ws / "alias-executed"
        self.git("config", "alias.opaque", "!touch " + str(marker))
        for hook in ("hooks/git/branch-guard.sh", "hooks/bash/destructive-guard.sh"):
            self.assertEqual(self.hook(hook, "git opaque").returncode, 2)
        self.assertFalse(marker.exists())
        for command in ("git push --force local '+refs/heads/*:refs/heads/*'",
                        "git -c core.worktree=/other commit -m x",
                        "git -c core.bare=false commit -m x",
                        "git -c include.path=/other/config commit -m x",
                        "git -c includeIf.gitdir:*/.path=/other/config commit -m x",
                        "git -c core.hooksPath=/dev/null commit -m x"):
            self.assertEqual(self.hook("hooks/bash/destructive-guard.sh", command).returncode, 2, command)
        self.git("commit", "-q", "--allow-empty", "-m", "subject\n\nAuthorized: prose only\nnot a trailer block")
        self.assertEqual(self.hook("hooks/bash/destructive-guard.sh", "git -C " + shlex.quote(str(self.repo)) + " push --force local HEAD:main").returncode, 2)
        self.git("checkout", "-q", "-b", "feature/safety")
        command = "git -C " + shlex.quote(str(self.repo)) + " -c color.ui=never commit --allow-empty -m 'Refs: #1122'"
        self.assertEqual(self.hook("hooks/git/branch-guard.sh", command).returncode, 0)
        subprocess.run(command, shell=True, cwd=self.repo, env=self.env, check=True, stdout=subprocess.DEVNULL, timeout=120)
        command = "git -c color.ui=never push --force local HEAD:feature/safety"
        self.assertEqual(self.hook("hooks/bash/destructive-guard.sh", command).returncode, 0)
        subprocess.run(command, shell=True, cwd=self.repo, env=self.env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
        after = subprocess.check_output(["git", "--git-dir=" + str(bare), "rev-parse", "refs/heads/main"], text=True, timeout=120).strip()
        self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
