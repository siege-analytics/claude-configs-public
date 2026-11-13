#!/usr/bin/env python3
"""Run the installed scanner through its typed, Task-scoped diagnostic contract."""
import os
import json
import signal
import time
from pathlib import Path
import subprocess
import sys
import tempfile
import contextlib
import hashlib
import stat
import types
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Verified before execution, rather than importing mutable sibling code.
CAPABILITY_SHA256 = '489888db51876971fbfc3d4308e51fc06bf643cdaab1ba3c6e2a5b1ee510acf0'
def capability():
    path = Path(__file__).with_name('scanner_capability.py')
    if os.path.realpath(path) != str(path):
        raise ValueError('scanner capability cannot use symlink aliases')
    fd = os.open(path,os.O_RDONLY|os.O_NONBLOCK|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as source:
        info=os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1024*1024:
            raise ValueError('scanner capability must be bounded and singly linked')
        raw=source.read(1024*1024+1)
    if hashlib.sha256(raw).hexdigest() != CAPABILITY_SHA256:
        raise ValueError('installed scanner capability differs')
    module=types.ModuleType('verified_scanner_capability');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

class ScannerError(ValueError):
    pass

def stop_scanner(process):
    if process.poll() is None:
        os.killpg(process.pid,signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait(timeout=5)
        # The shell may exit before a descendant that ignored SIGTERM.
        try:
            os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:
            pass  # The owned process group is already gone.

def wait_scanner(process, budget=1800, interval=30):
    started = time.monotonic()
    try:
        while True:
            try:
                return process.wait(timeout=interval)
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic()-started
                print(f'scanner running: {int(elapsed)} seconds; no completion verdict yet',file=sys.stderr,flush=True)
                if elapsed >= budget:
                    raise ScannerError(f'scanner exceeded{budget:g}s; incomplete, no clean verdict')
    finally:
        stop_scanner(process)

def main():
    try:
        policy = capability()
        parse_arguments,validate_files,owned_plan,pinned_bytes,CLOSURE = (policy.parse_arguments,policy.validate_files,policy.owned_plan,policy.pinned_bytes,policy.CLOSURE)
        plan = parse_arguments(sys.argv[1:])
        validate_files(plan, Path(__file__))
        gate = Path(plan['gate'])
        owned_plan(plan,str(gate),json.loads(gate.read_text()),str(gate.parents[2]))
        # Keep existing authenticated gh/git configuration, but do not inherit
        # shell/Python startup injection or Git target overrides. This is a
        # trusted-tool environment, not a sandbox for arbitrary project code.
        permitted = {'PATH','HOME','LANG','LC_ALL','LC_CTYPE','GH_TOKEN','GITHUB_TOKEN','GH_HOST','GH_CONFIG_DIR','XDG_CONFIG_HOME','SSH_AUTH_SOCK'}
        env = {key:value for key,value in os.environ.items() if key in permitted}
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        env['PYTHONSAFEPATH'] = '1'
        if plan.get('index'):
            env['GIT_INDEX_FILE'] = plan['index']
        env['GIT_TERMINAL_PROMPT'] = '0'
        if plan['mode'] == 'pr' and env.get('GH_HOST','github.com') != 'github.com':
            raise ScannerError('scanner PR host must be github.com')
        with tempfile.TemporaryDirectory(prefix='scan-',dir=plan['tmp']) as tmp:
            env['TMPDIR'] = tmp
            hooks = Path(tmp)/'empty-hooks'; hooks.mkdir(mode=0o700)
            # Reading an index can otherwise execute repository fsmonitor code.
            # Neither index selection nor exact PR fetch needs repository hooks.
            env.update(GIT_CONFIG_COUNT='2',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false',
                       GIT_CONFIG_KEY_1='core.hooksPath',GIT_CONFIG_VALUE_1=str(hooks))
            # Execute only freshly verified bytes in the private child, so a
            # later installed-file edit cannot change the selected scanner.
            code_root = Path(tmp)/'tool';code_root.mkdir(mode=0o700)
            installed = Path(__file__).parents[2]
            for relative,digest in CLOSURE.items():
                if relative.startswith('skills/detect-ai-fingerprints/'):
                    target = code_root/Path(relative).name
                    with target.open('xb') as output:
                        output.write(pinned_bytes(installed/relative,digest))
                    target.chmod(0o600)
            scan_args = list(plan['scan_args'])
            identity = {'mode': plan['mode'], 'repo': plan['repo']}
            if plan['message']:
                message = pinned_bytes(Path(plan['message']))
                selected_message = Path(tmp)/'message-input'
                selected_message.write_bytes(message); selected_message.chmod(0o600)
                scan_args[1] = str(selected_message)
                identity.update(input_path=plan['message'], input_sha256=hashlib.sha256(message).hexdigest())
            elif plan['mode'] == 'message':
                identity['input_sha256'] = hashlib.sha256(scan_args[1].encode()).hexdigest()
            selection = Path(tmp)/'selection.json'
            env['SCANNER_SELECTION_OUTPUT'] = str(selection)
            command = ['/bin/bash',str(code_root/'scan.sh'),*scan_args]
            with contextlib.ExitStack() as outputs:
                stdout,stderr=None,None
                if plan.get('log_dir'):
                    logs=Path(tempfile.mkdtemp(prefix='scanner-result-',dir=plan['log_dir']))
                    stdout=outputs.enter_context((logs/'stdout.log').open('xb'))
                    stderr=outputs.enter_context((logs/'stderr.log').open('xb'))
                    (logs/'stdout.log').chmod(0o600);(logs/'stderr.log').chmod(0o600)
                    print(f'scanner raw logs: {logs}',file=sys.stderr,flush=True)
                process = None
                try:
                    process = subprocess.Popen(command,cwd=plan['repo'],env=env,start_new_session=True,stdout=stdout,stderr=stderr)
                    print(f'scanner owned process group: {process.pid}',file=sys.stderr,flush=True)
                    code = wait_scanner(process)
                finally:
                    if process is not None:
                        stop_scanner(process)
                result = code
                if plan['mode'] in ('staged','working','pr'):
                    if selection.is_file():
                        identity['selection'] = json.loads(selection.read_text())
                    else:
                        identity['selection_incomplete'] = True
                        result = 2
                identity['child_exit'] = code
                encoded = json.dumps(identity,sort_keys=True) + '\n'
                print('scanner input identity: '+encoded.strip(),file=sys.stderr,flush=True)
                if plan.get('log_dir'):
                    record = logs/'selection.json'
                    record.write_text(encoded); record.chmod(0o600)
            if plan.get('log_dir'):
                print(f'scanner child exit: {code}',file=sys.stderr,flush=True)
        return result if result in (0,1,2) else 2
    except (KeyboardInterrupt,ValueError,OSError,subprocess.SubprocessError) as error:
        print('scanner execution incomplete: '+str(error),file=sys.stderr)
        return 2

def interrupted(_signal, _frame):
    raise KeyboardInterrupt('scanner interrupted; incomplete')

if __name__ == '__main__':
    signal.signal(signal.SIGTERM,interrupted)
    raise SystemExit(main())
