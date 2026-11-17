#!/usr/bin/env python3
# Managed bootstrap: siege-project-settings/v1
"""Installed project callbacks; candidate enforcement files are never imported."""
from __future__ import annotations
import argparse
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import sys
import time

sys.dont_write_bytecode = True
EVENTS = ('UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure')
RELATIVE = Path('.claude/hooks/siege-project-bootstrap.py')
RECEIPT = Path('.claude/hooks/siege-project-bootstrap.json')
BOOTSTRAP_ABI = 'siege-project-settings/v1'
PUBLISH_LOCK = Path('.claude/hooks/siege-project-bootstrap.lock')
LIMIT = 1024 * 1024
ADVICE = ('Install reviewed exact-main bin/core-authoring-profile.py install --repo <primary-repo> '
          '--package <external-versioned-package> --home <physical-home>; '
          'add --workspace <verified-headless-workspace> for qualified Linux Craft. '
          'See docs/core-authoring-profile.md.')
SHELL = ('if [ -L "$HOME/.claude" ] || [ -L "$HOME/.claude/hooks" ] || [ -L "$HOME/.claude/hooks/siege-project-bootstrap.py" ]; then exit 2; fi; if [ ! -f "$HOME/.claude/hooks/siege-project-bootstrap.py" ]; then '
         'printf "%s\\n" "Project policy bootstrap missing; install the reviewed stable profile." >&2; exit 2; fi; '
         'python3 -I -B "$HOME/.claude/hooks/siege-project-bootstrap.py" --event "$1"; '
         'status=$?; if [ "$status" -ne 0 ]; then exit 2; fi; exit 0')


def command_for(event):
    if event not in EVENTS:
        raise ValueError('unsupported project bootstrap event')
    return shlex.join(['/bin/sh', '-c', SHELL, 'siege-project-bootstrap/v1', event])


def profile():
    return {'hooks': {event: [{**({} if event == 'UserPromptSubmit' else {'matcher': '.*'}),
                              'hooks': [{'type': 'command', 'command': command_for(event), 'timeout': 120}]}]
                      for event in EVENTS}}


def profile_problems(settings):
    """Validate owned registrations without taking ownership of operator hooks."""
    if not isinstance(settings, dict) or not isinstance(settings.get('hooks'), dict):
        return ['profile hooks must be an object']
    expected = profile()['hooks']
    counts = {event: 0 for event in EVENTS}
    problems = []
    for event, groups in settings['hooks'].items():
        if not isinstance(groups, list):
            problems.append('profile hook groups must be arrays')
            continue
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get('hooks'), list):
                problems.append('profile hook group must contain hooks')
                continue
            for hook in group['hooks']:
                if not isinstance(hook, dict):
                    problems.append('profile hook must be an object')
                    continue
                command = hook.get('command', '')
                if not isinstance(command, str):
                    problems.append('profile hook command must be a string')
                    continue
                if hook.get('type') != 'command' or 'siege-project-bootstrap/v1' not in command:
                    continue
                metadata = {key: value for key, value in group.items() if key != 'hooks'}
                approved = expected.get(event, [])
                if not any(metadata == {key: value for key, value in entry.items() if key != 'hooks'}
                           and hook in entry['hooks'] for entry in approved):
                    problems.append('managed bootstrap has conflicting event, metadata or command vector')
                elif event in counts:
                    counts[event] += 1
    for event, count in counts.items():
        if count != 1:
            problems.append('authoring profile requires one exact stable bootstrap registration for ' + event)
    return problems



def retire_source(settings, legacy):
    """Retire exact canonical relative registrations; preserve operator policy."""
    value = copy.deepcopy(settings)
    expected = {}
    for event, groups in legacy['hooks'].items():
        for group in groups:
            for hook in group['hooks']:
                command = hook['command']
                expected.setdefault(command, []).append((event, {k: v for k, v in group.items() if k != 'hooks'}, hook))
    for event, groups in value.get('hooks', {}).items():
        retained = []
        for group in groups:
            kept = []
            for hook in group['hooks']:
                command = hook.get('command', '')
                tokens = shlex.split(command) if hook.get('type') == 'command' else []
                candidate = tokens[0] if tokens else ''
                if tokens[:2] == ['/bin/sh', '-c'] and len(tokens) >= 4 and tokens[3] == 'siege-project-bootstrap/v1':
                    metadata = {k: v for k, v in group.items() if k != 'hooks'}
                    approved = profile()['hooks'].get(event, [])
                    if not any(metadata == {k: v for k, v in entry.items() if k != 'hooks'} and hook in entry['hooks'] for entry in approved):
                        raise ValueError('managed bootstrap has conflicting event, metadata or command vector')
                if candidate in expected:
                    metadata = {k: v for k, v in group.items() if k != 'hooks'}
                    if (event, metadata, hook) not in expected[candidate]:
                        raise ValueError('managed relative hook has conflicting event, metadata or command vector')
                    continue
                kept.append(hook)
            if kept or set(group) - {'matcher', 'hooks'}:
                retained.append({**group, 'hooks': kept})
        value['hooks'][event] = retained
    return value

def regular(path):
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('stable profile path must be physical and absolute')
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('stable profile input must be a regular file')
    return path.read_bytes()


@contextmanager
def _physical_directory(home, relative, *, create=False):
    """Pin every directory component; never resolve a publication through links."""
    if not home.is_absolute() or relative.is_absolute() or '..' in (*home.parts, *relative.parts):
        raise ValueError('stable publication directory must be physical and home-relative')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors, bindings = [], []
    try:
        current = os.open(home.anchor, flags)
        descriptors.append(current)
        components = [(part, False) for part in home.parts[1:]]
        components.extend((part, create) for part in relative.parts)
        for name, make in components:
            if make:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=current)
                except FileExistsError:
                    pass  # The no-follow directory open below validates an existing entry.
            child = os.open(name, flags, dir_fd=current)
            descriptors.append(child)
            bindings.append((current, name, child))
            current = child
        def verify():
            for parent, name, child in bindings:
                named = os.stat(name, dir_fd=parent, follow_symlinks=False)
                pinned = os.fstat(child)
                if not stat.S_ISDIR(named.st_mode) or (named.st_dev, named.st_ino) != (pinned.st_dev, pinned.st_ino):
                    raise ValueError('stable publication directory changed during activation')
        verify()
        yield current, verify
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _bytes_at(directory, name, *, absent=False):
    descriptor, verify = directory
    verify()
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    except FileNotFoundError:
        verify()
        if absent:
            return None
        raise
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('stable publication input must be a regular file')
        data = stream.read()
    verify()
    return data


def _replace_at(directory, name, contents, mode, previous, *, prefix='.project-bootstrap-'):
    descriptor, verify = directory
    verify()
    if _bytes_at(directory, name, absent=True) != previous:
        raise ValueError('stable publication target changed during activation')
    temporary = prefix + os.urandom(16).hex()
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=descriptor)
    try:
        with os.fdopen(fd, 'wb') as stream:
            verify()
            stream.write(contents)
            stream.flush()
            os.fchmod(stream.fileno(), mode)
            os.fsync(stream.fileno())
        if _bytes_at(directory, name, absent=True) != previous:
            raise ValueError('stable publication target changed during activation')
        os.replace(temporary, name, src_dir_fd=descriptor, dst_dir_fd=descriptor)
        verify()
    finally:
        try:
            os.unlink(temporary, dir_fd=descriptor)
        except FileNotFoundError:
            pass  # A successful descriptor-relative rename consumed this temporary entry.


def load(path, name):
    regular(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def craft_process():
    """The same fixed application ancestry boundary as the installed router."""
    result = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,comm='], capture_output=True, text=True, timeout=5)
    if result.returncode:
        raise ValueError('cannot establish callback process ancestry')
    parents = {}
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            parents[int(parts[0])] = (int(parts[1]), parts[2])
    pid, visited = os.getpid(), set()
    for _ in range(64):
        if pid in {0, 1}:
            return False
        if pid in visited or pid not in parents:
            raise ValueError('callback ancestry is unresolved')
        visited.add(pid)
        pid, executable = parents[pid]
        if executable == '/Applications/Craft Agents.app/Contents/MacOS/Craft Agents':
            return True
    raise ValueError('callback ancestry exceeded its bound')



def headless_process(proc=Path('/proc'), pid=None):
    """Qualified Linux server ancestry, matching the existing project bridge."""
    if sys.platform != 'linux':
        return False
    pid = os.getppid() if pid is None else pid
    seen = set()
    for _ in range(32):
        if pid < 1:
            return False
        if pid in seen:
            raise ValueError('headless parent process cycle')
        seen.add(pid)
        process = proc / str(pid)
        try:
            executable = os.readlink(process / 'exe')
        except PermissionError:
            if pid == 1:
                return False
            raise
        if executable == '/app/vendor/bun/bun':
            with (process / 'cmdline').open('rb') as stream:
                raw = stream.read(65537)
            if len(raw) > 65536:
                raise ValueError('headless process metadata exceeds its bound')
            if raw.rstrip(b'\0').split(b'\0') == [b'/app/vendor/bun/bun', b'run', b'/app/packages/server/src/index.ts', b'--allow-insecure-bind']:
                return True
        with (process / 'status').open('rb') as stream:
            status = stream.read(65537)
        if len(status) > 65536:
            raise ValueError('headless parent metadata exceeds its bound')
        parents = [line.split(b':', 1)[1].strip() for line in status.splitlines() if line.startswith(b'PPid:')]
        if len(parents) != 1 or not parents[0].isdigit():
            raise ValueError('headless parent identity is unresolved')
        pid = int(parents[0])
    raise ValueError('headless ancestry exceeds its bound')

def matching(settings, event, payload):
    selected = []
    for group in settings.get('hooks', {}).get(event, []):
        if event == 'UserPromptSubmit' or re.fullmatch(group.get('matcher', ''), payload.get('tool_name', '')):
            for hook in group['hooks']:
                if hook.get('type') != 'command' or hook.get('async', False):
                    raise ValueError('unsupported installed hook type')
                selected.append(hook)
    return selected



def git(repo, *arguments):
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    environment.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    result = subprocess.run(['/usr/bin/git', '-C', str(repo), *arguments], capture_output=True,
                            timeout=10, env=environment)
    if result.returncode:
        raise ValueError('cannot resolve the registered CLI repository: ' + result.stderr.decode('utf-8', 'replace'))
    return result.stdout


def common_directory(repo):
    return Path(os.fsdecode(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')).strip()).resolve(strict=True)



def state_path(home, common):
    return home / '.claude/hooks/siege-authoring-state' / hashlib.sha256(str(common).encode()).hexdigest()

def anchor_path(home, common, workspace=None):
    # A workspace selects only an independently installed headless anchor.
    # It cannot replace the CLI enrollment or another workspace's policy.
    key = str(common) if workspace is None else str(common) + '\0headless-craft\0' + str(workspace)
    return home / '.claude/hooks/siege-authoring-profiles' / (hashlib.sha256(key.encode()).hexdigest() + '.json')


def package_digest(package):
    # The expected digest comes from the external installed anchor. No package
    # Python, generated receipt or candidate-provided verifier executes here.
    if not package.is_absolute() or package.resolve(strict=True) != package:
        raise ValueError('CLI package must be a physical absolute directory')
    inventory = {}
    for path in sorted(package.rglob('*')):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise ValueError('CLI package contains a symlink or non-regular input')
        if path.is_file():
            data = regular(path)
            inventory[path.relative_to(package).as_posix()] = {
                'sha256': hashlib.sha256(data).hexdigest(), 'executable': bool(path.stat().st_mode & 0o111)}
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()



def primary_repository(repo):
    roots = [Path(os.fsdecode(part[len(b'worktree '):])).resolve(strict=True)
             for part in git(repo, 'worktree', 'list', '--porcelain', '-z').split(b'\0') if part.startswith(b'worktree ')]
    if not roots:
        raise ValueError('Core authoring enrollment requires a primary working repository')
    return roots[0]

def publish_anchor(home, bound, workspace=None):
    common = common_directory(Path(bound['git_repo']))
    workspace = Path(bound['git_repo']) if workspace is None else workspace
    target = anchor_path(home, common, None if workspace == Path(bound['git_repo']) else workspace)
    state = state_path(home, common)
    scope = {'mode': 'native-cli'} if workspace == Path(bound['git_repo']) else {'mode': 'headless-craft', 'workspace': str(workspace)}
    value = {'schema_version': 1, 'purpose': 'core-authoring-profile/v1',
             'git_common_dir': str(common), 'binding': bound, 'scope': scope}
    with _physical_directory(home, target.parent.relative_to(home), create=True) as directory:
        with _physical_directory(home, state.relative_to(home), create=True):
            pass
        previous = _bytes_at(directory, target.name, absent=True)
        if previous is not None:
            old = json.loads(previous)
            if old.get('purpose') != value['purpose'] or old.get('git_common_dir') != str(common):
                raise ValueError('CLI profile anchor is operator-owned or bound elsewhere')
        _replace_at(directory, target.name, (json.dumps(value, sort_keys=True) + '\n').encode(),
                    0o600, previous, prefix='.cli-profile-')
    return target


def cli_binding(repo, workspace=None):
    common = common_directory(repo)
    location = anchor_path(Path.home(), common, workspace)
    if not location.is_file():
        raise ValueError('Core authoring CLI enforcement profile is not registered outside the project')
    installed = json.loads(regular(location))
    if installed.get('schema_version') != 1 or installed.get('purpose') != 'core-authoring-profile/v1' or installed.get('git_common_dir') != str(common):
        raise ValueError('independently installed CLI profile anchor is invalid')
    bound = installed['binding']
    registered = Path(bound['git_repo'])
    roots = {Path(os.fsdecode(part[len(b'worktree '):])).resolve(strict=True)
             for part in git(repo, 'worktree', 'list', '--porcelain', '-z').split(b'\0') if part.startswith(b'worktree ')}
    if repo not in roots or registered not in roots or common_directory(registered) != common:
        raise ValueError('callback is not a registered worktree of the installed CLI project')
    package = Path(bound['hooks_root'])
    if any(package.is_relative_to(root) for root in roots):
        raise ValueError('Core enforcement must be installed outside its authoring worktrees')
    if package_digest(package) != bound['package_sha256']:
        raise ValueError('independently installed CLI package bytes changed')
    return bound, package, installed['scope']


def require_core_profile(definition, settings, event, payload):
    if definition.get('adapter') != 'siege-compatibility' or definition.get('settings_source') != 'hooks/settings-snippet.json':
        raise ValueError('Core authoring requires the verified Siege-compatibility enforcement profile; an independent prompt-only profile does not supply its guards')
    required = ('hooks/bash/universal-mutation-gate.sh' if event == 'PreToolUse' and payload.get('tool_name') in
                {'Bash', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'} else
                'hooks/resolver/inject-resolver.sh' if event == 'UserPromptSubmit' else None)
    if required is not None:
        needle = '${package}/compatibility/' + required
        if not any(shlex.split(hook['command']) == [needle] for hook in matching(settings, event, payload)):
            raise ValueError('installed Core profile lacks required canonical enforcement for this event/tool')

def cli(raw, event, payload, *, mode='native-cli'):
    # Resolve actual Git worktrees; payload paths and local config cannot select code.
    repo = Path(os.fsdecode(git(Path.cwd(), 'rev-parse', '--show-toplevel')).strip()).resolve(strict=True)
    bound, package, scope = cli_binding(repo, os.environ.get('CRAFT_WORKSPACE_PATH', '') if mode == 'headless-craft' else None)
    if scope.get('mode') != mode:
        raise ValueError('authoring profile is not enrolled for this verified host mode')
    interpreter = Path(bound['interpreter'])
    if not interpreter.is_absolute() or not interpreter.is_file() or not os.access(interpreter, os.X_OK):
        raise ValueError('enrolled Core interpreter is unavailable')
    if interpreter.resolve() != Path(sys.executable).resolve():
        # The independent anchor selected this interpreter after package hashing;
        # SDK PATH and project metadata cannot substitute package verifier code.
        result = subprocess.run([str(interpreter), '-I', '-B', str(Path(__file__).resolve()), '--event', event],
                                input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        if len(result.stdout) + len(result.stderr) > LIMIT:
            raise ValueError('installed callback relay output exceeds its bound')
        print(result.stdout.decode('utf-8'), end='')
        print(result.stderr.decode('utf-8'), end='', file=sys.stderr)
        return 0 if result.returncode == 0 else 2
    sys.path.insert(0, str(package / 'bin'))
    try:
        registration = load(package / 'bin/core-authoring-profile.py', 'installed_core_authoring_profile')
        definition = registration.verify_runtime(bound)
        template = json.loads(regular(package / 'hooks/settings-snippet.json'))
        require_core_profile(definition, template, event, payload)
        settings = template
        deadline = time.monotonic() + 90
        outputs = []
        state = state_path(Path.home(), common_directory(repo))
        # OS ancestry selected native CLI. Stale Craft host markers cannot
        # redirect its Task namespace; this is not a fabricated session.
        craft_keys = {'CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CRAFT_SESSION_ID',
                      'CRAFT_AGENT_SESSION_ID', 'CRAFT_AGENT_WORKSPACE', 'CRAFT_IS_PACKAGED'}
        environment = {k: v for k, v in os.environ.items() if k not in craft_keys and not k.startswith('CCP_CRAFT_ROUTER_')}
        environment.update(PYTHONDONTWRITEBYTECODE='1', CCP_HOOK_STATE_DIR=str(state))
        environment['PATH'] = str(interpreter.parent) + os.pathsep + environment.get('PATH', '')
        if mode == 'headless-craft':
            for key in ('CRAFT_SESSION_PATH', 'CRAFT_AGENT_SESSION_PATH', 'CLAUDE_SESSION_DIR', 'CLAUDE_SESSION_ID',
                        'CLAUDE_CODE_SESSION_ID', 'SESSION_ID', 'CLAUDE_SIGNAL_DIR', 'CRAFT_SIGNAL_DIR',
                        'CRAFT_AGENT_SIGNAL_DIR', 'CCP_HOOK_INPUT_JSON'):
                environment.pop(key, None)
            workspace = Path(scope['workspace'])
            if not workspace.is_absolute() or workspace.resolve(strict=True) != workspace or not workspace.is_dir():
                raise ValueError('enrolled headless workspace must be physical')
            if os.environ.get('CRAFT_WORKSPACE_PATH') != str(workspace):
                raise ValueError('headless callback workspace differs from independent enrollment')
            anchor = load(package / 'compatibility/hooks/lib/session_anchor.py', 'project_headless_session_anchor')
            sdk = anchor.payload_uuid(payload)
            if not sdk:
                raise ValueError('headless SDK UUID is unresolved')
            own = anchor.registered_session_dir(str(workspace), os.environ.get('CRAFT_SESSION_DIR', ''), payload)
            if not own:
                if event != 'UserPromptSubmit':
                    raise ValueError('headless SDK UUID/header/physical witness is unresolved')
                # Match existing registered-router startup behavior: prompt
                # context can load before identity persists; Task mutation
                # authority is absent until a later strict witness succeeds.
                environment.update(CRAFT_AGENT_WORKSPACE=str(workspace), CCP_CRAFT_ROUTER_SESSION_UNRESOLVED='1')
            else:
                for key in ('CLAUDE_SESSION_DIR', 'CLAUDE_SESSION_ID', 'CLAUDE_CODE_SESSION_ID', 'SESSION_ID',
                            'CLAUDE_SIGNAL_DIR', 'CRAFT_SIGNAL_DIR', 'CRAFT_AGENT_SIGNAL_DIR'):
                    environment.pop(key, None)
                environment.update(CRAFT_SESSION_DIR=own, CRAFT_AGENT_WORKSPACE=str(workspace), CCP_CRAFT_ROUTER_BOUND_SDK_ID=sdk)

        for hook in matching(settings, event, payload):
            tokens = shlex.split(hook['command'])
            prefix = '${package}/compatibility/'
            if len(tokens) != 1 or not tokens[0].startswith(prefix):
                raise ValueError('installed canonical hook has an unsupported command vector')
            relative = Path(tokens[0][len('${package}/'):])
            if '..' in relative.parts or relative.is_absolute():
                raise ValueError('installed canonical hook escapes its verified package')
            vector = [str(package / relative)]
            # Only canonical vectors from the independently verified profile run.
            seconds = hook.get('timeout', 90)
            remaining = deadline - time.monotonic()
            if type(seconds) not in (int, float) or not 0 < seconds <= 120 or remaining <= 0:
                raise ValueError('installed callback timeout is invalid or exhausted')
            result = subprocess.run(vector, input=raw, capture_output=True, timeout=min(seconds, remaining),
                                    env=environment)
            if len(result.stdout) + len(result.stderr) > LIMIT:
                raise ValueError('installed callback output exceeds its bound')
            outputs.append((result.returncode, result.stdout.decode('utf-8'), result.stderr.decode('utf-8')))
        return emit(event, outputs, definition, package)
    finally:
        sys.path.pop(0)
    return 0



def emit(event, outputs, definition, package):
    if definition['adapter'] == 'siege-compatibility':
        # Reuse this independently pinned runtime's existing SDK combiner.
        # Concatenating JSON decisions would turn a valid deny into bad output.
        adapter = load(package / 'compatibility/hooks/lib/craft-settings-router.py', 'project_cli_sdk_combiner')
        code, value, diagnostics = adapter.aggregate(event, outputs)
        if value:
            print(json.dumps(value))
        if diagnostics:
            print(diagnostics, file=sys.stderr)
        return 0 if code == 0 else 2

def dispatch(raw, event):
    payload = json.loads(raw)
    if not isinstance(payload, dict) or payload.get('hook_event_name') != event:
        raise ValueError('project callback event differs from its fixed registration')
    if event != 'UserPromptSubmit' and (not isinstance(payload.get('tool_name'), str) or not payload['tool_name']):
        raise ValueError('project callback has no tool name')
    if craft_process():
        session = Path(os.environ.get('CRAFT_SESSION_DIR', ''))
        if not session.is_absolute() or session.parent.name != 'sessions':
            raise ValueError('Craft callback has no usable workspace binding')
        workspace = session.parent.parent.resolve(strict=True)
        target = Path.home() / '.claude/hooks/siege-craft-router' / (hashlib.sha256(str(workspace).encode()).hexdigest() + '.py')
        regular(target)
        code = subprocess.run([sys.executable, '-I', '-B', str(target), '--workspace', str(workspace), '--event', event],
                              input=raw, timeout=100).returncode
        return 0 if code == 0 else 2
    if headless_process():
        return cli(raw, event, payload, mode='headless-craft')
    if any(os.environ.get(key) for key in ('CRAFT_WORKSPACE_PATH', 'CRAFT_AGENT_WORKSPACE', 'CRAFT_SESSION_DIR')):
        raise ValueError('Craft context has no qualified host witness; refusing CLI fallback')
    return cli(raw, event, payload)



def registration_bytes(data):
    return (json.dumps({'schema_version': 1, 'purpose': BOOTSTRAP_ABI,
                        'sha256': hashlib.sha256(data).hexdigest()}, sort_keys=True) + '\n').encode()


@contextmanager
def publication_lock(home, *, shared=False):
    with _physical_directory(home, PUBLISH_LOCK.parent) as directory:
        descriptor, verify = directory
        flags = os.O_RDONLY if shared else os.O_RDWR | os.O_CREAT
        fd = os.open(PUBLISH_LOCK.name, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=descriptor)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('shared bootstrap lock must be a regular file')
            deadline = time.monotonic() + 10
            while True:
                try:
                    fcntl.flock(fd, (fcntl.LOCK_SH if shared else fcntl.LOCK_EX) | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ValueError('shared bootstrap publication is busy; retry after the active publisher')
                    time.sleep(0.05)
            verify()
            yield directory
        finally:
            os.close(fd)


def verify_published(home):
    with publication_lock(home, shared=True) as directory:
        expected = json.loads(_bytes_at(directory, RECEIPT.name))
        if not isinstance(expected, dict) or expected.get('schema_version') != 1 or expected.get('purpose') != BOOTSTRAP_ABI:
            raise ValueError('installed shared bootstrap registration is invalid')
        if hashlib.sha256(_bytes_at(directory, RELATIVE.name)).hexdigest() != expected.get('sha256'):
            raise ValueError('installed shared bootstrap bytes changed')
        return expected


def publish(home, data, *, before_publish=None, expected=None):
    """Serialize trusted common-ABI updates; readers never accept a split pair."""
    target = home / RELATIVE
    if not home.is_absolute() or home.resolve(strict=True) != home:
        raise ValueError('bootstrap home must be a physical absolute directory')
    with _physical_directory(home, RELATIVE.parent, create=True):
        pass
    with publication_lock(home) as directory:
        old = _bytes_at(directory, RELATIVE.name, absent=True)
        if old is not None and b'# Managed bootstrap: siege-project-settings/v1\n' not in old.splitlines(keepends=True)[:3]:
            raise ValueError('project bootstrap destination is operator-owned')
        old_receipt = _bytes_at(directory, RECEIPT.name, absent=True)
        if old_receipt is not None:
            value = json.loads(old_receipt)
            if not isinstance(value, dict) or value.get('purpose') != BOOTSTRAP_ABI:
                raise ValueError('shared bootstrap registration is operator-owned')
        desired_receipt = registration_bytes(data)
        if before_publish is not None:
            before_publish()
        if (_bytes_at(directory, RELATIVE.name, absent=True),
                _bytes_at(directory, RECEIPT.name, absent=True)) != (old, old_receipt):
            raise ValueError('shared bootstrap changed during activation; retry with a fresh snapshot')
        if (old, old_receipt) == (data, desired_receipt):
            return target
        if expected is not None and (old, old_receipt) != expected:
            raise ValueError('shared bootstrap changed during activation; retry with a fresh snapshot')
        _replace_at(directory, RELATIVE.name, data, 0o700, old)
        _replace_at(directory, RECEIPT.name, desired_receipt, 0o600, old_receipt)
        if (_bytes_at(directory, RELATIVE.name), _bytes_at(directory, RECEIPT.name)) != (data, desired_receipt):
            raise ValueError('shared bootstrap changed during publication')
    return target



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--event', choices=EVENTS, required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('callback payload exceeds its bound')
        return dispatch(raw, args.event)
    except (OSError, ValueError, KeyError, TypeError, ImportError, subprocess.SubprocessError) as error:
        print('Project policy bootstrap failed closed: ' + str(error) + '. ' + ADVICE, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
