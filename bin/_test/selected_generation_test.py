#!/usr/bin/env python3
"""Real selected build/registration and coherent generation transitions."""
from __future__ import annotations
import importlib.util
import copy
import fcntl
import shlex
import shutil
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'bin'))
spec = importlib.util.spec_from_file_location('registration_fixture', ROOT / 'bin/_test/selected_registration_test.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class SelectedGenerationTest(unittest.TestCase):
    def setUp(self):
        self.case = fixture.SelectedRegistrationTest()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.case.prepare()
        self.store = self.case.output.parent / 'generations-store'
        self.operations = self.case.output.parent / 'operations.json'
        self.operations.write_text(json.dumps([
            {'type': 'feature-merge', 'target_branch': 'trunk'},
            {'type': 'feature-merge', 'target_branch': 'release'},
            {'type': 'ticket-commit', 'message': 'Independent custom commit'},
            {'type': 'review-procedure'}]))

    def cli(self, command, *arguments, ok=True):
        return self.case.run_cmd([sys.executable, '-B', str(self.case.source / 'bin/package-generation.py'),
            '--store', str(self.store), command, *map(str, arguments)], ok=ok)

    def pins(self):
        return ['--policy-root', self.case.source, '--policy-inputs', self.case.policy_source,
                '--policy-inputs-sha256', self.case.policy_pin,
                '--registration-inputs', self.case.registration_source,
                '--registration-inputs-sha256', self.case.registration_pin]

    def stage(self):
        return json.loads(self.cli('stage-selected', '--source', self.case.source,
            '--selection', self.case.source / 'selected-build.json', *self.pins()).stdout)['generation']

    def activate(self, candidate, epoch=0, rollback=False):
        extra = []
        if epoch:
            observed = json.loads(self.cli('observe', '--generation', candidate,
                '--operations', self.operations, *(['--rollback'] if rollback else [])).stdout)
            extra = ['--operations', self.operations, '--accepted-observation', observed['sha256']]
        return json.loads(self.cli('rollback' if rollback else 'select', '--generation', candidate,
            '--expected-epoch', epoch, *extra, *self.pins()).stdout)

    def registered_entry(self, action):
        resolved = json.loads(self.cli('resolve').stdout)
        package = Path(resolved['package'])
        args = self.case.arguments()
        args[args.index('--hooks-root') + 1] = str(package)
        args[args.index('--selection') + 1] = str(Path(resolved['payload']) / 'provenance/selected-build.json')
        entry = {'install': ['bash', str(self.case.source / 'bin/install-hooks.sh')],
                 'wire': [sys.executable, '-B', str(self.case.source / 'bin/wire-enforcement.py')],
                 'verify': ['bash', str(self.case.source / 'bin/verify-enforcement.sh')]}[action]
        return self.case.run_cmd([*entry, *args, '--generation-store', str(self.store)])

    def native_corpus(self):
        case = self.case
        case.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'No ticket or review required'], cwd=case.consumer)
        before_denials = None
        for alias in ('origin', '--help', '--selected', '--binding', '--command', '-h', '--', '名前'):
            if alias != 'origin' and case.run_cmd(['git', 'remote', 'get-url', '--', alias], cwd=case.consumer, ok=False).returncode:
                case.run_cmd(['git', 'remote', 'add', '--', alias, str(case.remote)], cwd=case.consumer)
            case.run_cmd(['git', 'push', '--', alias, 'HEAD:trunk'], cwd=case.consumer)
            case.run_cmd(['git', 'push', '--', alias, 'HEAD:trunk'], cwd=case.consumer)
            before_denials = case.refs()
            result = case.run_cmd(['git', 'push', '--', alias, 'HEAD:release'], cwd=case.consumer, ok=False)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertEqual(case.refs(), before_denials)
        settings = json.loads(case.settings.read_text())
        self.assertEqual(settings['model'], 'operator-choice')
        command = settings['hooks']['UserPromptSubmit'][0]['hooks'][-1]['command']
        result = case.run_cmd(shlex.split(command), cwd=case.consumer, input=json.dumps({'prompt': 'review this change'}))
        self.assertTrue(result.stdout)
        return settings

    def reseal(self, role, path, text):
        case = self.case
        target = case.source / path
        target.write_text(target.read_text() + text)
        case.run_cmd(['git', 'add', path])
        case.run_cmd(['git', 'commit', '-qm', 'Synthetic component upgrade'])
        revision = case.run_cmd(['git', 'rev-parse', 'HEAD']).stdout.strip()
        selection = case.fixture.selection
        component = selection[role] if role != 'bundle' else selection['bundles'][0]['component']
        replacement = fixture.selected.describe_component(case.source, component['id'], revision, component['paths'])
        component.update(replacement)
        case.definition['selection_sha256'] = fixture.selected.effective.digest(selection)
        case.registration_source = Path('project/registration-' + case.definition['selection_sha256'] + '.json')
        case.write_definition()
        (case.source / 'selected-build.json').write_text(json.dumps(selection))

    def test_real_single_component_transitions_and_rollback(self):
        case = self.case
        # Include an independently versioned non-Siege content bundle at baseline.
        case.fixture.bundle('independent-content')
        case.fixture.selection['backend'] = 'claude-code-local'
        case.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        case.definition['selection_sha256'] = fixture.selected.effective.digest(case.fixture.selection)
        case.write_definition()
        (case.source / 'selected-build.json').write_text(json.dumps(case.fixture.selection))
        self.assertFalse((case.source / 'bundles/siege').exists())
        for path in ('skills', 'hooks', '.githooks', 'examples', 'craft-agent'):
            self.assertFalse((case.source / path).exists(), path)
        first = self.stage()
        first_pins = self.pins()
        first_state = self.activate(first)
        for action in ('install', 'wire', 'verify'):
            self.registered_entry(action)
        settings = self.native_corpus()
        root = self.store / 'generations' / first / 'payload'
        original = fixture.selected.file_inventory({str(p.relative_to(root)): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
            for p in root.rglob('*') if p.is_file()})
        customization = (root / 'source/projects/independent/skills/review/SKILL.md').read_bytes()
        self.reseal('bundle', 'bundles/independent-content/skills/format/SKILL.md', '\nBundle upgrade.\n')
        second = self.stage()
        second_state = self.activate(second, 1)
        for role in ('scaffold', 'project', 'workflow_policy'):
            self.assertEqual(first_state['generation_receipt']['identities'][role], second_state['generation_receipt']['identities'][role])
        self.registered_entry('verify')
        self.assertEqual(self.native_corpus(), settings)
        self.assertEqual((self.store / 'generations' / second / 'payload/source/projects/independent/skills/review/SKILL.md').read_bytes(), customization)
        stale = self.cli('resolve', '--expected-token', first_state['activation_token'], ok=False)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn('stale activation token', stale.stderr)
        stale_receipt = self.cli('rollback', '--generation', first, '--expected-epoch', 2,
            '--operations', self.operations, '--accepted-observation', second_state['observation']['sha256'],
            *first_pins, ok=False)
        self.assertNotEqual(stale_receipt.returncode, 0)
        self.assertIn('review and accept the exact observation', stale_receipt.stderr)
        self.assertEqual(json.loads(self.cli('resolve').stdout)['epoch'], 2)
        observed = json.loads(self.cli('observe', '--generation', first, '--operations', self.operations, '--rollback').stdout)
        restored = json.loads(self.cli('rollback', '--generation', first, '--expected-epoch', 2,
            '--operations', self.operations, '--accepted-observation', observed['sha256'], *first_pins).stdout)
        self.assertEqual(restored['epoch'], 3)
        self.assertNotEqual(restored['generation_receipt'], first_state['generation_receipt'])
        self.assertNotEqual(restored['activation_token'], first_state['activation_token'])
        self.assertEqual(self.native_corpus(), settings)
        actual = fixture.selected.file_inventory({str(p.relative_to(root)): (p.read_bytes(), bool(p.stat().st_mode & 0o111))
            for p in root.rglob('*') if p.is_file()})
        self.assertEqual(actual, original)
        self.assertEqual(restored['generation_receipt']['identities'], first_state['generation_receipt']['identities'])
        # Upgrade only the scaffold from the bundle-upgraded selection, preserving project bytes.
        self.activate(second, 3)
        self.reseal('scaffold', 'bin/build.py', '\n# Synthetic independently versioned scaffold.\n')
        third = self.stage()
        third_state = self.activate(third, 4)
        for role in ('bundles', 'project', 'workflow_policy'):
            self.assertEqual(second_state['generation_receipt']['identities'][role], third_state['generation_receipt']['identities'][role])
        self.registered_entry('verify')
        self.assertEqual(self.native_corpus(), settings)
        self.reseal('project', 'projects/independent/skills/review/SKILL.md', '\nProject customization revision.\n')
        fourth = self.stage()
        fourth_state = self.activate(fourth, 5)
        for role in ('bundles', 'scaffold', 'workflow_policy'):
            self.assertEqual(third_state['generation_receipt']['identities'][role], fourth_state['generation_receipt']['identities'][role])
        self.registered_entry('verify')
        self.assertEqual(self.native_corpus(), settings)
        self.assertEqual(second_state['authorization_effect'], 'none')

    def test_real_old_scaffold_new_bundle_and_new_scaffold_old_project_rejected(self):
        case = self.case
        case.fixture.bundle('independent-content')
        case.fixture.selection['backend'] = 'claude-code-local'
        case.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        case.definition['selection_sha256'] = fixture.selected.effective.digest(case.fixture.selection)
        case.write_definition()
        (case.source / 'selected-build.json').write_text(json.dumps(case.fixture.selection))
        first = self.stage()
        self.activate(first)
        before = (self.store / 'current.json').read_bytes()
        old = copy.deepcopy(case.fixture.selection)
        self.reseal('scaffold', 'bin/build.py', '\n# Next scaffold.\n')
        self.reseal('bundle', 'bundles/independent-content/skills/format/SKILL.md', '\nNext bundle.\n')
        self.reseal('project', 'projects/independent/skills/review/SKILL.md', '\nNext project.\n')
        coherent = copy.deepcopy(case.fixture.selection)
        for role in ('scaffold', 'project'):
            mixed = copy.deepcopy(coherent)
            mixed[role] = old[role]
            (case.source / 'selected-build.json').write_text(json.dumps(mixed))
            rejected = self.cli('stage-selected', '--source', case.source,
                '--selection', case.source / 'selected-build.json', *self.pins(), ok=False)
            self.assertNotEqual(rejected.returncode, 0, role)
            self.assertEqual((self.store / 'current.json').read_bytes(), before)
        (case.source / 'selected-build.json').write_text(json.dumps(coherent))
        second = self.stage()
        self.assertEqual(self.activate(second, 1)['epoch'], 2)

    def second_project(self):
        self.reseal('project', 'projects/independent/skills/review/SKILL.md', '\nChanged project content.\n')
        return self.stage()

    def test_mixed_components_wrong_pins_and_stale_receipts_preserve_active(self):
        first = self.stage()
        self.activate(first)
        original = (self.store / 'current.json').read_bytes()
        old_selection = copy.deepcopy(self.case.fixture.selection)
        second = self.second_project()
        valid_selection = copy.deepcopy(self.case.fixture.selection)
        # A reviewed registration seals the complete pairing; a generated receipt cannot change it.
        for role in ('scaffold', 'project'):
            mixed = copy.deepcopy(valid_selection)
            mixed[role] = old_selection[role]
            if mixed == valid_selection:
                mixed[role]['revision'] = '0' * 40
            (self.case.source / 'selected-build.json').write_text(json.dumps(mixed))
            failed = self.cli('stage-selected', '--source', self.case.source,
                '--selection', self.case.source / 'selected-build.json', *self.pins(), ok=False)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual((self.store / 'current.json').read_bytes(), original)
        (self.case.source / 'selected-build.json').write_text(json.dumps(valid_selection))
        for flag in ('--policy-inputs-sha256', '--registration-inputs-sha256'):
            pins = self.pins()
            pins[pins.index(flag) + 1] = '0' * 64
            failed = self.cli('select', '--generation', second, '--expected-epoch', 1, *pins, ok=False)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual((self.store / 'current.json').read_bytes(), original)
        root = self.store / 'generations' / second
        for name in ('package/flat/selected-build.json', 'package/flat/selected-registration.json',
                     'package/flat/hooks/settings-snippet.json', 'package/flat/.githooks/pre-push',
                     'source/projects/independent/skills/review/SKILL.md'):
            path = root / 'payload' / name
            before = path.read_bytes()
            path.write_bytes(before + b'\nCHANGED\n')
            failed = self.cli('select', '--generation', second, '--expected-epoch', 1, *self.pins(), ok=False)
            self.assertNotEqual(failed.returncode, 0, name)
            self.assertEqual((self.store / 'current.json').read_bytes(), original)
            path.write_bytes(before)
        for field, changed_value, diagnostic in (
            ('identity', 'github.example.invalid/other/project', 'mixed selected project identity'),
            ('composition_tools', {}, 'changed selected composition tool identities')):
            bad = json.loads((root / 'generation.json').read_text())
            bad[field] = changed_value
            bad_id = fixture.selected.effective.digest(bad)
            shutil.copytree(root, root.parent / bad_id)
            (root.parent / bad_id / 'generation.json').write_text(json.dumps(bad))
            rejected = self.cli('select', '--generation', bad_id, '--expected-epoch', 1, *self.pins(), ok=False)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn(diagnostic, rejected.stderr)
            self.assertEqual((self.store / 'current.json').read_bytes(), original)
        # Rehash the entire inventory after forging a build receipt. The normal
        # rebuild, with independent pins, still rejects this self-consistent lie.
        forged_root = root.parent / 'forged-staging'
        shutil.copytree(root, forged_root)
        receipt_path = forged_root / 'payload/package/flat/selected-build.json'
        receipt = json.loads(receipt_path.read_text())
        receipt['selection_sha256'] = '0' * 64
        receipt_path.write_text(json.dumps(receipt))
        forged_manifest = json.loads((forged_root / 'generation.json').read_text())
        forged_manifest['files'] = fixture.selected.file_inventory({p.relative_to(forged_root / 'payload').as_posix():
            (p.read_bytes(), bool(p.stat().st_mode & 0o111)) for p in (forged_root / 'payload').rglob('*') if p.is_file()})
        forged_id = fixture.selected.effective.digest(forged_manifest)
        (forged_root / 'generation.json').write_text(json.dumps(forged_manifest))
        forged_root.rename(root.parent / forged_id)
        rejected = self.cli('select', '--generation', forged_id, '--expected-epoch', 1, *self.pins(), ok=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn('mixed or stale selected package/receipt', rejected.stderr)
        self.assertEqual((self.store / 'current.json').read_bytes(), original)
        # Rehashing a candidate's false identity still cannot establish a pin.
        manifest = json.loads((root / 'generation.json').read_text())
        manifest['identities']['project']['id'] = 'other'
        changed = fixture.selected.effective.digest(manifest)
        shutil.copytree(root, root.parent / changed)
        (root.parent / changed / 'generation.json').write_text(json.dumps(manifest))
        failed = self.cli('select', '--generation', changed, '--expected-epoch', 1, *self.pins(), ok=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('mixed selected component identities', failed.stderr)
        self.assertEqual((self.store / 'current.json').read_bytes(), original)
        self.activate(second, 1)

    def test_unapproved_candidate_scaffold_never_executes_before_registration_seal(self):
        first = self.stage()
        self.activate(first)
        before = (self.store / 'current.json').read_bytes()
        marker = self.case.output.parent / 'unapproved-builder-executed'
        injected = 'from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("unapproved")\nraise SystemExit(43)\n'
        path = self.case.source / 'bin/build.py'
        path.write_text(injected)
        self.case.run_cmd(['git', 'add', 'bin/build.py'])
        self.case.run_cmd(['git', 'commit', '-qm', 'Unapproved synthetic scaffold'])
        revision = self.case.run_cmd(['git', 'rev-parse', 'HEAD']).stdout.strip()
        declaration = copy.deepcopy(self.case.fixture.selection)
        scaffold = declaration['scaffold']
        declaration['scaffold'] = fixture.selected.describe_component(self.case.source, scaffold['id'], revision, scaffold['paths'])
        original = self.store / 'generations' / first
        forged = original.parent / 'forged-scaffold'
        shutil.copytree(original, forged)
        (forged / 'payload/source/bin/build.py').write_text(injected)
        (forged / 'payload/provenance/selected-build.json').write_text(json.dumps(declaration))
        manifest = json.loads((forged / 'generation.json').read_text())
        manifest['identities']['scaffold'] = declaration['scaffold']
        manifest['selection_sha256'] = fixture.selected.effective.digest(declaration)
        def inventory(root):
            return fixture.selected.file_inventory({p.relative_to(root).as_posix():
                (p.read_bytes(), bool(p.stat().st_mode & 0o111)) for p in root.rglob('*') if p.is_file()})
        manifest['source_files'] = inventory(forged / 'payload/source')
        manifest['composition_tools']['bin/build.py'] = manifest['source_files']['bin/build.py']['sha256']
        manifest['files'] = inventory(forged / 'payload')
        ident = fixture.selected.effective.digest(manifest)
        (forged / 'generation.json').write_text(json.dumps(manifest))
        forged.rename(original.parent / ident)
        # Invoke trusted tools, with the unchanged independently pinned definition.
        result = self.case.run_cmd([sys.executable, '-B', str(ROOT / 'bin/package-generation.py'),
            '--store', str(self.store), 'select', '--generation', ident, '--expected-epoch', '1',
            *map(str, self.pins())], ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists(), result.stderr)
        self.assertIn('stale or mixed selected registration', result.stderr)
        self.assertEqual((self.store / 'current.json').read_bytes(), before)

    def test_lock_symlink_existing_target_and_cleanup_preserve_retained_sets(self):
        first = self.stage()
        self.activate(first)
        second = self.second_project()
        before = (self.store / 'current.json').read_bytes()
        repeated = self.cli('stage-selected', '--source', self.case.source,
            '--selection', self.case.source / 'selected-build.json', *self.pins(), ok=False)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertIn('already exists', repeated.stderr)
        with (self.store / '.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)
            blocked = self.cli('select', '--generation', second, '--expected-epoch', 1, *self.pins(), ok=False)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertEqual((self.store / 'current.json').read_bytes(), before)
        for target in (self.store / 'generations' / first, self.store / 'generations' / second, self.store.parent):
            failed = self.cli('cleanup-candidate', '--candidate', target, ok=False)
            self.assertNotEqual(failed.returncode, 0)
            self.assertTrue(target.exists())
        link = self.store / '.stage-escape'
        link.symlink_to(self.store / 'generations' / first, target_is_directory=True)
        failed = self.cli('cleanup-candidate', '--candidate', link, ok=False)
        self.assertNotEqual(failed.returncode, 0)
        link.unlink()
        candidate = self.store / '.stage-interrupted'
        candidate.mkdir()
        (candidate / 'partial').write_text('incomplete')
        self.cli('cleanup-candidate', '--candidate', candidate)
        self.assertFalse(candidate.exists())
        self.assertEqual((self.store / 'current.json').read_bytes(), before)
        self.cli('verify', '--generation', first)
        self.cli('verify', '--generation', second)

    def test_process_death_and_failed_replace_have_one_commit_point(self):
        first = self.stage()
        self.activate(first)
        second = self.second_project()
        observation = json.loads(self.cli('observe', '--generation', second, '--operations', self.operations).stdout)
        before = (self.store / 'current.json').read_bytes()
        argv = [str(self.case.source / 'bin/package-generation.py'), '--store', str(self.store), 'select',
                '--generation', second, '--expected-epoch', '1', '--operations', str(self.operations),
                '--accepted-observation', observation['sha256'], *map(str, self.pins())]
        for fail in ('error-before', 'kill-before', 'kill-after'):
            code = '''import os, runpy, signal, sys
mode = sys.argv.pop(1)
original = os.replace
def replace(source, target):
    if str(target).endswith('/current.json'):
        if mode == 'error-before': raise OSError('injected publication error')
        if mode == 'kill-before': os.kill(os.getpid(), signal.SIGKILL)
        original(source, target)
        os.kill(os.getpid(), signal.SIGKILL)
    original(source, target)
os.replace = replace
sys.path.insert(0, os.path.dirname(sys.argv[1]))
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            result = self.case.run_cmd([sys.executable, '-B', '-c', code, fail, *argv], ok=False)
            self.assertNotEqual(result.returncode, 0)
            current = json.loads(self.cli('resolve').stdout)
            if fail == 'kill-after':
                self.assertEqual(current['generation'], second)
                self.assertEqual(current['epoch'], 2)
            else:
                self.assertEqual((self.store / 'current.json').read_bytes(), before)
                self.assertEqual(current['generation'], first)
        self.cli('verify', '--generation', first)
        self.cli('verify', '--generation', second)

    def test_wrong_profile_changed_component_and_unapproved_registration_reject(self):
        first = self.stage()
        self.activate(first)
        before = (self.store / 'current.json').read_bytes()
        declaration = self.case.fixture.selection
        for field, value in (('workflow_profile', 'strict-release'), ('backend', 'resolver-only')):
            changed = {**declaration, field: value}
            (self.case.source / 'selected-build.json').write_text(json.dumps(changed))
            result = self.cli('stage-selected', '--source', self.case.source,
                '--selection', self.case.source / 'selected-build.json', *self.pins(), ok=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual((self.store / 'current.json').read_bytes(), before)
        old = copy.deepcopy(declaration)
        self.reseal('project', 'projects/independent/skills/review/SKILL.md', '\nChanged bytes.\n')
        declaration['project']['sha256'] = old['project']['sha256']
        self.case.definition['selection_sha256'] = fixture.selected.effective.digest(declaration)
        self.case.write_definition()
        (self.case.source / 'selected-build.json').write_text(json.dumps(declaration))
        result = self.cli('stage-selected', '--source', self.case.source,
            '--selection', self.case.source / 'selected-build.json', *self.pins(), ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('component digest differs', result.stderr)
        self.assertEqual((self.store / 'current.json').read_bytes(), before)

    def test_policy_and_registration_only_transitions_preserve_content_and_rollback(self):
        import hashlib
        first = self.stage()
        original_pins = self.pins()
        first_state = self.activate(first)
        self.registered_entry('install')
        fixture_policy = self.case.fixture.fixture.fixture
        policy = copy.deepcopy(fixture_policy.approved)
        policy['organization_profiles'][0]['values'] = {'branch-policy': {'integration_branch': 'release'}}
        fixture_policy.write_json('project/upgraded-policy.json', policy)
        revision = fixture_policy.commit()
        policy_selection = {**fixture_policy.selection, 'policy_revision': revision,
            'policy_path': 'project/upgraded-policy.json',
            'git_blob': fixture_policy.git('rev-parse', revision + ':project/upgraded-policy.json'),
            'raw_sha256': hashlib.sha256((self.case.source / 'project/upgraded-policy.json').read_bytes()).hexdigest(),
            'canonical_sha256': fixture.selected.effective.digest(policy)}
        fixture_policy.write_json('project/upgraded-policy-selection.json', policy_selection)
        inputs = {**fixture_policy.inputs, 'selection_source': 'project/upgraded-policy-selection.json',
                  'selection_sha256': fixture.selected.effective.digest(policy_selection)}
        self.case.policy_source = Path('project/upgraded-policy-inputs.json')
        fixture_policy.write_json(self.case.policy_source, inputs)
        self.case.policy_pin = fixture.selected.effective.digest(inputs)
        self.case.definition['policy_inputs'] = {'source': str(self.case.policy_source), 'sha256': self.case.policy_pin}
        self.case.registration_source = Path('project/upgraded-registration.json')
        self.case.write_definition()
        second = self.stage()
        second_state = self.activate(second, 1)
        second_pins = self.pins()
        a, b = first_state['generation_receipt']['identities'], second_state['generation_receipt']['identities']
        for role in ('scaffold', 'project', 'bundles'):
            self.assertEqual(a[role], b[role])
        self.assertNotEqual(a['workflow_policy'], b['workflow_policy'])
        case = self.case
        case.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'Project without mandatory ceremony'], cwd=case.consumer)
        case.run_cmd(['git', 'push', 'origin', 'HEAD:release'], cwd=case.consumer)
        before = case.refs()
        denied = case.run_cmd(['git', 'push', 'origin', 'HEAD:trunk'], cwd=case.consumer, ok=False)
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(case.refs(), before)
        # Registration-only change removes protection from trunk, retaining the exact policy.
        case.definition['protected_targets'] = ['release']
        case.registration_source = Path('project/adapter-upgrade.json')
        case.write_definition()
        third = self.stage()
        third_state = self.activate(third, 2)
        c = third_state['generation_receipt']['identities']
        for role in ('scaffold', 'project', 'bundles', 'workflow_policy'):
            self.assertEqual(b[role], c[role])
        self.assertNotEqual(b['registration'], c['registration'])
        case.run_cmd(['git', 'push', 'origin', 'HEAD:trunk'], cwd=case.consumer)
        self.assertEqual(third_state['authorization_effect'], 'none')
        observed = json.loads(self.cli('observe', '--generation', second, '--operations', self.operations, '--rollback').stdout)
        restored = json.loads(self.cli('rollback', '--generation', second, '--expected-epoch', 3,
            '--operations', self.operations, '--accepted-observation', observed['sha256'], *second_pins).stdout)
        self.assertEqual(restored['epoch'], 4)
        self.assertEqual(restored['generation_receipt']['identities'], b)
        self.assertNotEqual(restored['generation_receipt'], second_state['generation_receipt'])
        case.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'New change after rollback'], cwd=case.consumer)
        before = case.refs()
        self.assertNotEqual(case.run_cmd(['git', 'push', 'origin', 'HEAD:trunk'], cwd=case.consumer, ok=False).returncode, 0)
        self.assertEqual(case.refs(), before)
        # Old source/profile receipts remain retained; no source identity is rewritten.
        self.cli('verify', '--generation', first)
        self.assertEqual(original_pins[original_pins.index('--policy-inputs-sha256') + 1], fixture_policy.pin)

    def test_concurrent_writers_stale_observation_and_damaged_active_rollback(self):
        first = self.stage()
        first_pins = self.pins()
        first_state = self.activate(first)
        second = self.second_project()
        observed = json.loads(self.cli('observe', '--generation', second, '--operations', self.operations).stdout)
        argv = [sys.executable, '-B', str(self.case.source / 'bin/package-generation.py'), '--store', str(self.store),
                'select', '--generation', second, '--expected-epoch', '1', '--operations', str(self.operations),
                '--accepted-observation', observed['sha256'], *map(str, self.pins())]
        processes = [subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        results = [(p, p.communicate(timeout=120)) for p in processes]
        self.assertEqual(sum(p.returncode == 0 for p, _ in results), 1, results)
        self.assertEqual(json.loads(self.cli('resolve').stdout)['epoch'], 2)
        stale = self.case.run_cmd(argv, ok=False)
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn('stale selection epoch', stale.stderr)
        path = self.store / 'generations' / second / 'payload/package/flat/.githooks/pre-push'
        path.write_bytes(path.read_bytes() + b'\nchanged active bytes\n')
        self.assertNotEqual(self.cli('resolve', ok=False).returncode, 0)
        observed = json.loads(self.cli('observe', '--generation', first, '--operations', self.operations, '--rollback').stdout)
        self.assertEqual(observed['previous_verification']['state'], 'unknown')
        restored = json.loads(self.cli('rollback', '--generation', first, '--expected-epoch', 2,
            '--operations', self.operations, '--accepted-observation', observed['sha256'], *first_pins).stdout)
        self.assertEqual(restored['epoch'], 3)
        self.assertEqual(restored['generation'], first)
        self.assertNotEqual(restored['activation_token'], first_state['activation_token'])
        self.assertNotEqual(self.cli('resolve', '--expected-token', first_state['activation_token'], ok=False).returncode, 0)

    def test_interrupted_stage_and_partial_publication_cannot_activate(self):
        first = self.stage()
        self.activate(first)
        before = (self.store / 'current.json').read_bytes()
        self.reseal('project', 'projects/independent/skills/review/SKILL.md', '\nInterrupted candidate.\n')
        argv = [str(self.case.source / 'bin/package-generation.py'), '--store', str(self.store), 'stage-selected',
                '--source', str(self.case.source), '--selection', str(self.case.source / 'selected-build.json'),
                *map(str, self.pins())]
        code = '''import os, runpy, signal, sys
original = os.rename
def rename(source, target):
    original(source, target)
    if '/generations/' in str(target) and str(target).endswith('/payload'):
        os.kill(os.getpid(), signal.SIGKILL)
os.rename = rename
sys.path.insert(0, os.path.dirname(sys.argv[1]))
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
        result = self.case.run_cmd([sys.executable, '-B', '-c', code, *argv], ok=False)
        self.assertEqual(result.returncode, -9)
        self.assertEqual((self.store / 'current.json').read_bytes(), before)
        partial = [p for p in (self.store / 'generations').iterdir() if p.name != first]
        self.assertEqual(len(partial), 1)
        self.assertNotEqual(self.cli('select', '--generation', partial[0].name, '--expected-epoch', 1, *self.pins(), ok=False).returncode, 0)
        for staged in self.store.glob('.stage-*'):
            self.cli('cleanup-candidate', '--candidate', staged)
        self.cli('verify', '--generation', first)
        self.assertEqual((self.store / 'current.json').read_bytes(), before)

    def test_siege_content_without_profile_adoption_does_not_activate_policy(self):
        case = self.case
        case.fixture.bundle('siege')
        case.fixture.selection['backend'] = 'claude-code-local'
        case.fixture.selection['required_capabilities'] = ['native-git', 'settings']
        case.definition['selection_sha256'] = fixture.selected.effective.digest(case.fixture.selection)
        case.write_definition()
        (case.source / 'selected-build.json').write_text(json.dumps(case.fixture.selection))
        first = self.stage()
        active = self.activate(first)
        self.assertEqual(active['generation_receipt']['identities']['workflow_policy']['profile'], 'independent')
        self.registered_entry('install')
        case.run_cmd(['git', 'commit', '--allow-empty', '-qm', 'No mandatory ticket or review'], cwd=case.consumer)
        case.run_cmd(['git', 'push', 'origin', 'HEAD:trunk'], cwd=case.consumer)
        case.run_cmd(['git', 'push', 'origin', 'HEAD:develop'], cwd=case.consumer)
        before = case.refs()
        self.assertNotEqual(case.run_cmd(['git', 'push', 'origin', 'HEAD:release'], cwd=case.consumer, ok=False).returncode, 0)
        self.assertEqual(case.refs(), before)

    def test_generation_settings_indexes_ignore_json_event_key_order(self):
        registration = fixture.selected.module('generation_settings_test', ROOT, 'selected_registration.py')
        package = self.case.output.parent / 'settings-order'
        (package / 'hooks').mkdir(parents=True)
        hooks = {event: [{'hooks': [{'type': 'command', 'command': 'python3 ' + event, 'timeout': 15}]}]
                 for event in ('UserPromptSubmit', 'Stop')}
        bound = {'hooks_root': str(package), 'generation_store': str(self.store)}
        def render(value):
            (package / 'hooks/settings-snippet.json').write_text(json.dumps({'hooks': value}))
            return registration.render_settings(bound)
        self.assertEqual(render(hooks), render(dict(reversed(list(hooks.items())))))

    def test_selected_stage_activation_and_fresh_rollback_scope(self):
        first = self.stage()
        self.assertFalse((self.store / 'current.json').exists())
        active = self.activate(first)
        self.assertEqual(active['epoch'], 1)
        resolved = json.loads(self.cli('resolve').stdout)
        self.assertEqual(resolved['generation'], first)
        manifest = json.loads(self.cli('verify', '--generation', first).stdout)
        self.assertEqual(manifest['kind'], 'selected-package')
        spec = importlib.util.spec_from_file_location('generation_ontology', ROOT / 'bin/ontology.py')
        ontology = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ontology)
        self.assertEqual(ontology.validate_bindings(ontology.read_json(ROOT / 'catalog/selected-generation-bindings.json'),
            ontology.read_json(ROOT / 'catalog/ontology.json'), self.store / 'generations' / first), 8)
        self.assertEqual(set(manifest['identities']), {'scaffold', 'bundles', 'workflow_policy', 'project', 'registration'})
        self.assertEqual(active['authorization_effect'], 'none')
        self.assertNotEqual(active['generation_receipt']['sha256'], first)
        self.assertEqual(resolved['activation_token'], active['activation_token'])


if __name__ == '__main__':
    unittest.main()
