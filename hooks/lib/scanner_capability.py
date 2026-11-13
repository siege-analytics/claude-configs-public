"""Typed scanner selection; no arbitrary shell, source execution or test receipt."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess

# Reviewed source-generation closure: refresh these digests with actual
# scanner/adapter changes in the same reviewed source change, never at runtime.
CLOSURE = {
    'skills/detect-ai-fingerprints/scan.sh':'a69df093ed7a84a0a0864250927857d8294df21cffc6e50c9d8a1de663616fb8',
    'skills/detect-ai-fingerprints/scan_snapshot.py':'567f740d50358551bd4d1ba7a53b92e12c51cf76c4a3f7ae6ceb47c8b1ac4a1c',
    'skills/detect-ai-fingerprints/scan_ast.py':'27e0960e2ee767ff8573d4c02ed0d72e7f92fc37382a63b325fbe11971ae7b44',
}

class ScannerError(ValueError):
    pass

def physical(value, *, file=False):
    path = Path(value)
    try:
        resolved = path.resolve(strict=True)
    except (OSError,RuntimeError) as error:
        raise ScannerError('scanner physical path is unavailable') from error
    if not path.is_absolute() or str(path) != value or resolved != path:
        raise ScannerError('scanner paths must be existing physical absolute paths')
    info = path.lstat()
    if file and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 4*1024*1024):
        raise ScannerError('scanner input/producer must be regular and singly linked')
    if not file and not stat.S_ISDIR(info.st_mode):
        raise ScannerError('scanner directory is not a directory')
    return path

def pinned_bytes(path, digest=None):
    physical(str(path),file=True)
    fd = os.open(path,os.O_RDONLY|os.O_NONBLOCK|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'rb') as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 4*1024*1024:
            raise ScannerError('scanner closure must be bounded regular singly linked files')
        raw = source.read(4*1024*1024+1)
        after = os.fstat(source.fileno())
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns) or (digest is not None and hashlib.sha256(raw).hexdigest() != digest):
        raise ScannerError('installed scanner closure differs: '+str(path))
    return raw

def parse_arguments(args):
    fields = {}; mode = None; scan_args = []
    index = 0
    while index < len(args):
        flag = args[index]
        if flag in {'--staged','--working'}:
            if mode: raise ScannerError('scanner requires exactly one mode')
            mode = flag[2:]; scan_args = [] if mode == 'staged' else [flag]; index += 1
        elif flag in {'--repo','--think-gate','--tmp-root','--index-file','--log-dir','--pr','--message','--message-file','--commit-message-file'}:
            if index+1 >= len(args) or not args[index+1] or flag != '--message' and args[index+1].startswith('-'):
                raise ScannerError('scanner option needs one literal value')
            value = args[index+1]; index += 2
            if flag in {'--repo','--think-gate','--tmp-root','--index-file','--log-dir'}:
                if flag in fields: raise ScannerError('duplicate scanner option')
                fields[flag] = value
            else:
                if mode: raise ScannerError('scanner requires exactly one mode')
                mode = flag[2:]; scan_args = [flag,value]
                if flag == '--message' and len(value.encode('utf-8')) > 65536:
                    raise ScannerError('scanner message exceeds64KiB')
                if flag == '--pr' and not re.fullmatch(r'[1-9][0-9]*',value):
                    raise ScannerError('scanner PR must be a literal positive number')
        else: raise ScannerError('unsupported scanner option')
    if not {'--repo','--think-gate','--tmp-root'} <= set(fields) or not mode:
        raise ScannerError('scanner requires explicit repo, own Task, private temporary root and mode')
    if '--index-file' in fields and mode != 'staged':
        raise ScannerError('an explicit index applies only to staged scans')
    return {'log_dir':fields.get('--log-dir'),'index':fields.get('--index-file'),'repo':fields['--repo'],'gate':fields['--think-gate'],'tmp':fields['--tmp-root'],
            'mode':mode,'scan_args':scan_args,'message':scan_args[1] if mode.endswith('message-file') else None}

def validate_files(plan, producer):
    root = Path(producer).parents[2]
    for relative,digest in CLOSURE.items():
        pinned_bytes(root/relative,digest)
    physical(str(producer),file=True)
    if producer != root/'hooks/lib/scanner-exec.py':
        raise ScannerError('scanner producer must be the exact installed entry')
    source_mode = plan['mode'] in {'staged','working','pr'}
    if source_mode and any(os.environ.get(key) for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_COMMON_DIR','GIT_OBJECT_DIRECTORY','GIT_ALTERNATE_OBJECT_DIRECTORIES','GIT_CONFIG','GIT_CONFIG_COUNT','GIT_CONFIG_PARAMETERS')):
        raise ScannerError('inherited Git targeting/configuration is ambiguous; use an explicit scanner target/index')
    if plan['mode'] == 'pr' and os.environ.get('GH_HOST','github.com') != 'github.com':
        raise ScannerError('scanner PR host must be github.com')
    repo = physical(plan['repo']); physical(plan['gate'],file=True)
    if Path(plan['gate']).parent.parent.name != 'tasks':
        raise ScannerError('scanner requires an adjacent per-Task think gate')
    if plan.get('index'): physical(plan['index'],file=True)
    scratch = physical(plan['tmp'])
    if scratch.stat().st_uid != os.geteuid() or stat.S_IMODE(scratch.stat().st_mode) != 0o700:
        raise ScannerError('scanner temporary root must be own private0700 directory')
    if plan['message']: physical(plan['message'],file=True)
    if plan.get('log_dir'):
        logs=physical(plan['log_dir'])
        if logs.stat().st_uid != os.geteuid() or stat.S_IMODE(logs.stat().st_mode) != 0o700:
            raise ScannerError('scanner log directory must be own private0700 directory')
    if source_mode:
        observed = subprocess.run(['git','rev-parse','--show-toplevel'],cwd=repo,capture_output=True,text=True,timeout=5,check=True)
        if Path(observed.stdout.strip()).resolve() != repo:
            raise ScannerError('scanner repo must be the exact Git toplevel')
    if plan['mode'] == 'pr':
        config = subprocess.run(['git','config','--show-scope','--name-only','--get-regexp',
            r'^(core\.(sshcommand|gitproxy|alternaterefscommand)|remote\..*\.(uploadpack|proxy|vcs)|credential\.|url\.|http\.|protocol\.|ssh\.)'],
            cwd=repo,capture_output=True,text=True,timeout=5)
        if config.returncode not in (0,1):
            raise ScannerError('scanner cannot establish Git transport configuration')
        if any(line.split(None,1)[0] in {'local','worktree'} for line in config.stdout.splitlines()):
            raise ScannerError('scanner PR rejects repository-local transport/helper overrides')
        remote = subprocess.run(['git','remote','get-url','origin'],cwd=repo,capture_output=True,text=True,timeout=5,check=True).stdout.strip()
        if re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',remote) or re.fullmatch(r'git@github\.com:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',remote):
            plan['origin'] = remote
        elif os.path.isabs(remote):
            plan['origin_path'] = str(physical(remote))
        else:
            raise ScannerError('scanner PR origin must be canonical GitHub or a physical scoped local repository')
    plan['scanner_root'] = str(root)
    plan['scanner'] = str(root/'skills/detect-ai-fingerprints/scan.sh')
    return plan

def owned_plan(plan, gate_path, gate_data, session):
    session = physical(session)
    if not isinstance(gate_data,dict) or not isinstance(gate_data.get('scope_paths'),list) or any(not isinstance(value,str) or not Path(value).is_absolute() for value in gate_data['scope_paths']):
        raise ScannerError('scanner requires a valid Task object and literal scope paths')
    if not (gate_data.get('ticket') or gate_data.get('task_id')):
        raise ScannerError('scanner Task identity is missing')
    if not isinstance(gate_data.get('status'),str) or not isinstance(gate_data.get('repo_root'),str) or not Path(gate_data['repo_root']).is_absolute():
        raise ScannerError('scanner Task status and repository must be literal values')
    if plan['gate'] != str(gate_path) or gate_data.get('status') not in {'implementing','reviewing','verifying'}:
        raise ScannerError('scanner requires its selected active own Task')
    if not Path(plan['gate']).is_relative_to(session/'tasks') or not any(gate_data.get(key) for key in ('sessionId','session')) or any(gate_data.get(key) and gate_data[key] != session.name for key in ('sessionId','session')):
        raise ScannerError('scanner Task must belong to the actual host session')
    if not gate_data.get('repo_root') or physical(gate_data['repo_root']) != Path(plan['repo']):
        raise ScannerError('scanner Task repo differs from the selected target')
    if not Path(plan['tmp']).is_relative_to(session/'data'):
        raise ScannerError('scanner temporary root must belong to own session data')
    if plan.get('log_dir') and not Path(plan['log_dir']).is_relative_to(session/'data'):
        raise ScannerError('scanner logs must belong to own session data')
    scopes = [Path(os.path.realpath(value)) for value in gate_data.get('scope_paths',[])]
    for value in [plan['tmp'],*([plan['message']] if plan['message'] else []),*([plan['index']] if plan.get('index') else []),*([plan['origin_path']] if plan.get('origin_path') else []),*([plan['log_dir']] if plan.get('log_dir') else [])]:
        if not any(Path(value).is_relative_to(scope) for scope in scopes):
            raise ScannerError('scanner target is outside the selected Task scope')
    return plan
