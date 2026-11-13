#!/usr/bin/env python3
"""Real publication adapters distinguish literal metadata from executable effects."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ('self-review.sh', 'detect-ai-fingerprints.sh')

class QuotedPublicationMetadata(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='quoted-publication-1368-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo with spaces'; self.repo.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith(('CRAFT_', 'CLAUDE_', 'CCP_', 'GIT_'))}
        self.env.update(GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                        GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.git = shutil.which('git')
        for args in (('init', '-q'), ('remote', 'add', 'origin', 'https://github.com/siege-analytics/fixture.git')):
            subprocess.run([self.git, '-C', str(self.repo), *args], env=self.env, check=True, capture_output=True, timeout=20)
        (self.repo / 'sample.py').write_text('value = 1\n')
        subprocess.run([self.git, '-C', str(self.repo), 'add', 'sample.py'], env=self.env, check=True, timeout=20)
        # Fixture lacks publication review and violates the real fingerprint scanner.
        subprocess.run([self.git, '-C', str(self.repo), 'commit', '-qm', 'fix: fixture #1368\n\nBody has an em\u2014dash.'],
                       env=self.env, check=True, capture_output=True, timeout=20)
        self.log = self.root / 'git-calls'
        self.remote = self.root / 'unexpected-gh'
        binaries = self.root / 'bin'; binaries.mkdir()
        (binaries / 'git').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> ' + shlex.quote(str(self.log)) +
                                     '\nexec ' + shlex.quote(self.git) + ' "$@"\n')
        (binaries / 'gh').write_text('#!/bin/sh\ntouch ' + shlex.quote(str(self.remote)) + '\nexit 75\n')
        for name in ('git', 'gh'):
            (binaries / name).chmod(0o755)
        self.env['PATH'] = str(binaries) + os.pathsep + self.env['PATH']

    def hook(self, name, command):
        self.log.write_text('')
        result = subprocess.run(['bash', str(ROOT / 'hooks/git' / name)],
            input=json.dumps({'tool_name': 'Bash', 'cwd': str(self.repo), 'tool_input': {'command': command}}),
            cwd=self.repo, env=self.env, capture_output=True, text=True, timeout=30)
        self.assertFalse(self.remote.exists(), 'a publication predicate must never execute the candidate gh command')
        return result

    def classify(self, command):
        result = subprocess.run(['python3', str(ROOT / 'hooks/lib/command-text.py'), '--publication', str(self.repo)],
                                input=command, env=self.env, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_shell_publication_wrappers_and_continuations_keep_inspection(self):
        commands = ["# '\nPUBLISHER=git; command \"$PUBLISHER\" push", 'PUBLISHER=git; command "$PUBLISHER" push', 'time git push', 'time -p git push', 'env PUBLISHER=git command "$PUBLISHER" --no-pager push',
                    'gi\\\nt push', 'git pu\\\nsh', '# comment\\\ngit push',
                    'printf x >"$(git push)"', 'printf x 2>"`git push`"', '>"$(git push)"']
        for command in commands:
            with self.subTest(command=command):
                self.assertNotEqual(self.classify(command)['kind'], 'none')
                for hook in HOOKS:
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        for command in ['time git status', 'time -p git status', 'command "$TOOL" --version', 'printf x >"git push"', "printf '%s' 'gi\\\nt push'",
                        'printf "%s" "gi\\\nt push"']:
            with self.subTest(reader_or_data=command):
                self.assertEqual(self.classify(command)['kind'], 'none')

    def test_dynamic_executable_positions_survive_all_known_wrappers(self):
        wrappers = ['', 'command ', 'env ', 'env -i ', 'env --ignore-environment ',
                    'env -u HOME ', 'command env ', 'time ', 'time -p ', 'exec ', 'timeout 20 ',
                    'time exec ', 'timeout 20 command ']
        for wrapper in wrappers:
            for arguments in ('push', '"$VERB"'):
                command = wrapper + '"$PUBLISHER" ' + arguments
                with self.subTest(command=command):
                    self.assertEqual(self.classify(command)['kind'], 'unknown')
                    for hook in HOOKS:
                        result = self.hook(hook, command)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            harmless = wrapper + '"$TOOL" --version'
            with self.subTest(nonpublication=harmless):
                self.assertEqual(self.classify(harmless)['kind'], 'none')
                for hook in HOOKS:
                    result = self.hook(hook, harmless)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.log.read_text(), '')
            for metadata in ['issue create --title \"git push\" --body \"$BODY\"',
                             'pr view 1 --json \"$FIELDS\"']:
                command = wrapper + '\"$TOOL\" ' + metadata
                self.assertEqual(self.classify(command)['kind'], 'none', command)
                for hook in HOOKS:
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.log.read_text(), '')
        for command in ["bash -c 'exec \"$PUBLISHER\" push'",
                        "timeout 20 bash -c 'command \"$PUBLISHER\" push'",
                        "printf '%s' 'time \"$PUBLISHER\" push'", 'echo "exec $WORD push"']:
            expected = 'none' if command.startswith(('printf', 'echo')) else 'unknown'
            self.assertEqual(self.classify(command)['kind'], expected, command)

    def test_unquoted_executable_globs_keep_flags_through_wrappers(self):
        wrappers = ['', 'command ', 'env ', 'env -i ', 'env -u HOME ', 'command env ',
                    'time ', 'time -p ', 'exec ', 'timeout 20 ', 'time exec ', 'timeout 20 command ']
        for wrapper in wrappers:
            for verb in ('push', 'pu*', '"$VERB"'):
                command = wrapper + 'gi* ' + verb
                with self.subTest(command=command):
                    self.assertEqual(self.classify(command)['kind'], 'unknown')
                    for hook in HOOKS:
                        result = self.hook(hook, command)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            for program in ('gi* --version', "'gi*' push"):
                command = wrapper + program
                with self.subTest(nonpublication=command):
                    self.assertEqual(self.classify(command)['kind'], 'none')
                    for hook in HOOKS:
                        result = self.hook(hook, command)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                        self.assertEqual(self.log.read_text(), '')
        for command in ['gi? push', '[g]it push', 'PATTERN=gi* command gi* push',
                        "bash -c 'command gi* push'", "timeout 20 bash -c 'exec gi* push'"]:
            self.assertEqual(self.classify(command)['kind'], 'unknown', command)
        for command in ["PATTERN=gi* printf '%s' x", "printf '%s' 'command gi* push'",
                        "gh issue create --title 'gi* push'", 'gh issue create --title gi*',
                        "PATTERN=gi* command 'gi*' push"]:
            self.assertEqual(self.classify(command)['kind'], 'none', command)

    def test_option_values_do_not_hide_known_executable_expansions(self):
        wrappers = ['exec -a label ', 'exec -alabel ', 'exec -c ', 'exec -l ', 'exec -cl ',
                    'timeout -s TERM 20 ', 'timeout --signal=TERM --kill-after=5 20 ',
                    'timeout --foreground --preserve-status --verbose 20 ',
                    'command -p ', 'env --unset=HOME ']
        for wrapper in wrappers:
            for program in ('"$PUBLISHER"', 'gi*'):
                command = wrapper + program + ' push'
                with self.subTest(command=command):
                    self.assertEqual(self.classify(command)['kind'], 'unknown')
                    for hook in HOOKS:
                        result = self.hook(hook, command)
                        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            harmless = wrapper + '"$TOOL" --version'
            self.assertEqual(self.classify(harmless)['kind'], 'none', harmless)
        for arguments in ('--no-replace-objects push', '--no-lazy-fetch -P push', '-p push'):
            command = 'command \"$PUBLISHER\" ' + arguments
            self.assertEqual(self.classify(command)['kind'], 'unknown', command)
            for hook in HOOKS:
                result = self.hook(hook, command)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(self.classify('\"$TOOL\" --version \"$DATA\" \"$MORE\"')['kind'], 'none')

    def test_substitution_publication_uses_its_effective_repository(self):
        other = self.root / 'other repo'
        subprocess.run([self.git, 'clone', '-q', str(self.repo), str(other)], env=self.env,
                       check=True, capture_output=True, timeout=20)
        subprocess.run([self.git, '-C', str(other), 'remote', 'set-url', 'origin',
                        'https://github.com/siege-analytics/fixture.git'], env=self.env,
                       check=True, capture_output=True, timeout=20)
        (other / 'sample.py').write_text('import subprocess\nsubprocess.run(["echo", "owned"])\n')
        subprocess.run([self.git, '-C', str(other), 'add', 'sample.py'], env=self.env,
                       check=True, capture_output=True, timeout=20)
        subprocess.run([self.git, '-C', str(other), 'commit', '-qm',
                        'fix: unpublished #1377\n\nBody has an em\u2014dash.'], env=self.env,
                       check=True, capture_output=True, timeout=20)
        command = 'cd ' + shlex.quote(str(other)) + ' && printf "%s" "$(git push)"'
        verdict = self.classify(command)
        self.assertEqual(verdict['kind'], 'publication', verdict)
        self.assertEqual(Path(verdict['cwd']), other.resolve())
        timed_directory = self.classify('time cd ' + shlex.quote(str(other)) + ' && git push')
        self.assertEqual(timed_directory['kind'], 'publication', timed_directory)
        self.assertEqual(Path(timed_directory['cwd']), other.resolve())
        redirected = self.classify('cd ' + shlex.quote(str(other)) + ' && printf x >"$(git push)"')
        self.assertEqual(redirected['kind'], 'publication', redirected)
        self.assertEqual(Path(redirected['cwd']), other.resolve())
        for hook in HOOKS:
            result = self.hook(hook, command)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        harmless = 'cd ' + shlex.quote(str(other)) + ' && printf "%s" "$(git status --short)"'
        self.assertEqual(self.classify(harmless)['kind'], 'none')

    def test_literal_metadata_does_not_inspect_unrelated_head(self):
        commands = [
            "gh issue create --repo siege-analytics/fixture --title 'git push is incorrectly required to file an issue' --body 'ordinary issue'",
            'gh issue create --title "gh pr create and gh pr merge are literal examples" --body "git push"',
            "gh issue edit 1368 --title='git push' --body='glab mr create and merge'",
            "gh issue comment 1368 --body 'git push; gh pr create; cd /tmp; gh pr merge'",
            "bash -c \"gh issue create --title 'git push' --body 'ordinary issue'\"",
            "gh issue create --title git\\ push --body 'ordinary issue'",
            "gh -R siege-analytics/fixture issue create --title 'git push' --body x",
            "gh issue -R siege-analytics/fixture create --title 'gh pr create' --body x",
            "python3 -c 'print(\"git push\")'", "node -e 'console.log(\"gh pr create\")'",
            "printf '%s\\n' 'git push' \"$(date)\"",
            "printf '$(git push)' \"$WORD\"",
            "printf '%s\\n' 'git push'", "rg 'git push' *.py", "./script.sh 'gh pr merge'",
            "python3 -c \"print('$WORD')\"", "echo \"$WORD\"",
            "kubectl get pods -o json", "ls *.py", "python3 script.py --title 'git push'",

        ]
        for hook in HOOKS:
            for command in commands:
                with self.subTest(hook=hook, command=command):
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.log.read_text(), '', 'literal metadata must not inspect cwd Git state')

    def test_real_publication_remains_reviewed_and_scanned(self):
        commands = [
            'git push', 'gh pr create', 'gh pr merge 1368',
            'gh -R siege-analytics/fixture pr create --title fix',
            'gh pr -R siege-analytics/fixture create --title fix',
            'gh pr create --repo=github.com/siege-analytics/fixture --title fix',
            'gh --repo=github.com/siege-analytics/fixture pr merge 1368',

            "gh issue create --title 'git push is metadata' --body x && git push",
            "gh issue create --title 'cd /tmp; gh pr merge' --body x && git push",
            "git push && gh issue create --title 'ordinary issue' --body x",
            "gh issue create --repo outside-owner/metadata --title 'git push' --body x && git push",
            "gh pr create --body '--repo outside-owner/metadata'",
            "bash -c 'git \"push\"'", "eval 'git push'", "env git push", 'command git push', 'timeout 20 git push', 'exec git push',
            'g"it" "push"', r'g\it pu\sh', '/usr/bin/git push',
            'git -C ' + shlex.quote(str(self.repo)) + ' push',
            'cd ' + shlex.quote(str(self.repo)) + ' && git push',
            'git --no-pager push',
        ]
        for hook in HOOKS:
            for command in commands:
                with self.subTest(hook=hook, command=command):
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertTrue(self.log.read_text(), 'real publication must retain review/scan')

    def test_literal_wrapper_depth_and_unsupported_startup_flags_keep_publication(self):
        for hook in HOOKS:
            for depth in (1, 4, 5):
                command = 'git push'
                for _ in range(depth):
                    command = 'bash -c ' + shlex.quote(command)
                result = self.hook(hook, command)
                self.assertEqual(result.returncode, 2, command + result.stderr)
            result = self.hook(hook, "bash -lc 'git push'")
            self.assertEqual(result.returncode, 2, result.stderr)
            for command in ("bash -lc \"printf '%s' 'git push'\"", "bash -c \"printf '%s' 'git push'\""):
                result = self.hook(hook, command)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.log.read_text(), '')

    def test_actual_publication_selector_keeps_existing_owner_scope(self):
        result = self.hook('self-review.sh', 'gh pr create --repo outside-owner/fixture --title ordinary')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.log.read_text(), '')
        for command in (
            "gh pr create --title '--repo outside-owner/metadata' --repo siege-analytics/fixture",
            "gh pr create --body '--repo' --title 'outside-owner/metadata'",
        ):
            result = self.hook('self-review.sh', command)
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertTrue(self.log.read_text())

    def test_documentation_help_does_not_inspect_head_but_help_values_do(self):
        for hook in HOOKS:
            for command in ('gh pr create --help', 'gh pr merge --help', 'git push --help'):
                with self.subTest(hook=hook, command=command):
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(self.log.read_text(), '')
            for command in ("gh pr create --title '--help' --body x", "gh pr merge 1368 --body '--help'", "git push --push-option '--help'"):
                with self.subTest(hook=hook, command=command):
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                    self.assertTrue(self.log.read_text())

    def test_existing_gitlab_adapter_boundary_is_preserved(self):
        # Keep the existing owner-prefix policy, including nested GitLab paths;
        # do not normalize host-qualified GitLab selectors as GitHub repos.
        for repository in ('outside-owner/subgroup/project', 'gitlab.com/outside-owner/subgroup/project'):
            for title in ('ordinary', 'git push is metadata'):
                command = 'glab mr create --repo ' + repository + ' --title ' + shlex.quote(title)
                for hook in HOOKS:
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 0, command + result.stderr)
                    self.assertEqual(self.log.read_text(), '')
        for command in (
            "glab mr create --title 'git push is metadata'",
            "glab mr create --repo siege-analytics/subgroup/project --description '--help' --title ordinary",
            "glab mr create --description '--repo' --title outside-owner/subgroup/project",
            "glab mr create -d '--repo outside-owner/subgroup/project' --title ordinary",
        ):
            result = self.hook('self-review.sh', command)
            self.assertEqual(result.returncode, 2, command + result.stderr)
            self.assertTrue(self.log.read_text())
            result = self.hook('detect-ai-fingerprints.sh', command)
            self.assertEqual(result.returncode, 0, command + result.stderr)
            self.assertEqual(self.log.read_text(), '')

    def test_multiple_publication_repositories_require_separate_calls(self):
        other = self.root / 'other'; other.mkdir()
        command = 'git -C ' + shlex.quote(str(self.repo)) + ' push && git -C ' + shlex.quote(str(other)) + ' push'
        for hook in HOOKS:
            with self.subTest(hook=hook):
                result = self.hook(hook, command)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertEqual(self.log.read_text(), '', 'do not review only the first repository HEAD')
                self.assertIn('separate calls', result.stderr)

    def test_unresolved_executable_shapes_cannot_skip_publication_checks(self):
        for hook in HOOKS:
            for command in ("$GIT push", "g* push", "gh issue create --title \"$(git push)\"", "sh -c 'git push'; (", "bash <<'CMD'\ngit push\nCMD",
                            "env -S 'gh -R siege-analytics/fixture pr create'",
                            "timeout -k 1 10 gh -R siege-analytics/fixture pr create",
                            "command -p gh -R siege-analytics/fixture pr create",
                            "command -p gh pr -R siege-analytics/fixture create"):
                with self.subTest(hook=hook, command=command):
                    result = self.hook(hook, command)
                    self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

if __name__ == '__main__':
    unittest.main()
