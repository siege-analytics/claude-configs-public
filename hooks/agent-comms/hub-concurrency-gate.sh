#!/usr/bin/env bash
# Hook: hub-concurrency-gate (#1051).
# Messaging is NEVER blocked: per-task open_threads are advisory audit only.
# Administrative load is enforced on spawn_session PreToolUse, and reconciled
# on PostToolUse. Only metadata-labelled hubs are capped; stewards and unknown
# roles communicate/spawn freely. Steward labels: role::traffic-cop,
# role::workspace-config, role::deep-think, role::steward (declared in the policy
# JSON). See hooks/README.md for state/role contracts.

set -uo pipefail
export PATH="/home/craftagents/bin:$PATH:/usr/local/bin:/opt/homebrew/bin"

# Fail open if python3 is unavailable -- never block on a missing interpreter.
command -v python3 >/dev/null 2>&1 || exit 0

INPUT=$(cat 2>/dev/null || true)
export CCP_HOOK_INPUT_JSON="$INPUT"

RESOLVE_TG="$(cd "$(dirname "$0")/../lib" && pwd)/resolve-think-gate.py"
export CCP_HOOK_LIB="$(cd "$(dirname "$0")/../lib" && pwd)"
SENDER=$(python3 "$RESOLVE_TG" --workspace "${CRAFT_AGENT_WORKSPACE:-.}" --session-value 2>/dev/null || true)
POLICY="$(cd "$(dirname "$0")/../lib" && pwd)/hub-concurrency-policy.json"
HUB_GATE_SENDER="$SENDER" HUB_GATE_POLICY="$POLICY" HUB_GATE_INPUT="$INPUT" python3 - <<'PYCODE'
import os, sys, json, datetime, tempfile, fcntl, hashlib, re, subprocess
from pathlib import Path


def load(path):
    try:
        with open(path) as f:
            obj = json.loads(f.readline()) if str(path).endswith('.jsonl') else json.load(f)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def audit(path, reason, sender='', target='', task=''):
    try:
        with open(str(path) + '.audit.jsonl', 'a') as f:
            f.write(json.dumps({'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                'gate_id': 'hub-concurrency-gate', 'reason': reason,
                                'sender': sender, 'target': target, 'task': task}) + '\n')
    except Exception:
        pass


def safe_id(s):
    return isinstance(s, str) and bool(s) and s not in {'.', '..'} and not any(c in s for c in '/\\')


def metadata(root, sid, own_dir=''):
    if not safe_id(sid):
        return {}
    directory = Path(own_dir) if own_dir else Path(root) / sid
    return load(directory / 'session.jsonl') or load(directory / 'session.json')


def labels(meta):
    result = meta.get('labels', [])
    return set(x for x in result if isinstance(x, str)) if isinstance(result, list) else set()


def parent(meta):
    return meta.get('parentSessionId') or meta.get('parent_session_id') or ''


def fresh(entry, now, window):
    try:
        t = datetime.datetime.fromisoformat(entry['last_activity'].replace('Z', '+00:00'))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return (now - t).total_seconds() < window
    except Exception:
        return False


def persist(path, state):
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.hub-threads-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def spawned_session(response):
    if isinstance(response, str):
        try: response = json.loads(response)
        except Exception: return ''
    if isinstance(response, list):
        for item in response:
            child = spawned_session(item)
            if child: return child
        return ''
    if not isinstance(response, dict): return ''
    if response.get('isError') or response.get('error'): return ''
    if response.get('type') == 'text':
        return spawned_session(response.get('text'))
    for key in ('sessionId', 'session_id'):
        if safe_id(response.get(key)): return response[key]
    for key in ('structuredContent', 'toolResults', 'tool_result', 'tool_response'):
        nested = spawned_session(response.get(key))
        if nested: return nested
    content = response.get('content')
    if isinstance(content, list):
        for item in content:
            nested = spawned_session(item.get('text')) if isinstance(item, dict) else ''
            if nested: return nested
    return ''


def main():
    try:
        payload = json.loads(os.environ.get('HUB_GATE_INPUT', ''))
    except Exception:
        return 0
    if not isinstance(payload, dict) or not isinstance(payload.get('tool_input'), dict):
        return 0
    ti = payload['tool_input']
    tool = payload.get('tool_name') or 'mcp__session__send_agent_message'
    is_spawn = tool.endswith('spawn_session')
    if is_spawn and ti.get('help'):
        return 0
    target = ti.get('sessionId', '') if not is_spawn else '(spawn)'
    phase = payload.get('hook_event_name') or 'PreToolUse'
    # Validate the same protocol before taking a lease: sibling PreToolUse
    # hooks may run concurrently and a denial need not produce a completion.
    if is_spawn and phase == 'PreToolUse':
        protocol = Path(os.environ.get('CCP_HOOK_LIB', '')).parent / 'agent-comms' / 'spawn-guard.sh'
        checked = subprocess.run(['bash', str(protocol)], input=json.dumps(payload),
                                 text=True, capture_output=True, timeout=10)
        if checked.returncode:
            sys.stderr.write(checked.stderr)
            return checked.returncode
    sender = os.environ.get('HUB_GATE_SENDER', '')
    if not safe_id(sender):
        audit(os.environ.get('HUB_THREADS_FILE') or os.path.join(os.environ.get('CRAFT_AGENT_WORKSPACE', '.'), 'hub-unresolved'), 'unresolved sender session/role; not capped', sender, target)
        return 0
    if not is_spawn and not safe_id(target):
        return 0
    # A mis-tagged session dir must not count this hub's load against a sibling (#1099).
    sys.path.insert(0, os.environ.get('CCP_HOOK_LIB', ''))
    from session_anchor import verified_session_dir
    own_dir = verified_session_dir(os.environ.get('CRAFT_SESSION_DIR', ''), payload)
    workspace = os.environ.get('CRAFT_AGENT_WORKSPACE', '')
    root = os.path.join(workspace, 'sessions') if workspace else os.path.dirname(own_dir)
    path = os.environ.get('HUB_THREADS_FILE') or (os.path.join(own_dir, 'hub-threads.json') if own_dir else os.path.join(root, sender, 'hub-threads.json') if root else '')
    if not path:
        return 0
    path = Path(path)
    policy = load(os.environ.get('HUB_GATE_POLICY', ''))
    me = metadata(root, sender, own_dir)
    mine = labels(me)
    stewards = set(policy.get('steward_roles', []))
    if not any(label.startswith('role::') for label in mine):
        audit(path, 'unresolved sender role; not capped', sender, target)
        return 0
    if not policy or not isinstance(policy.get('hub_role'), str):
        audit(path, 'unresolved role policy; not capped', sender, target)
        return 0
    if mine & stewards or policy['hub_role'] not in mine:
        return 0
    peer = metadata(root, target)
    if not is_spawn and (labels(peer) & stewards or parent(me) == target or parent(peer) == sender):
        return 0
    # Shell exports do not reach a Craft hook. Bind from the actual tool
    # payload, or the sender's sole active task gate (not invented header keys).
    def session_task(sid, directory=''):
        directory = Path(directory) if directory else Path(root) / sid
        tasks = set()
        for gate in (directory / 'tasks').glob('*/think-gate.json'):
            if not gate.resolve().is_relative_to(directory.resolve()):
                continue
            data = load(gate)
            if any(data.get(k) and data[k] != sid for k in ('session', 'sessionId')):
                continue
            if str(data.get('status', '')).lower() in {'disposed', 'complete', 'completed', 'done', 'done-awaiting-pr'}:
                continue
            identity = data.get('ticket') or data.get('task_id') or data.get('task')
            if isinstance(identity, str) and identity.strip():
                tasks.add(identity.strip())
        return next(iter(tasks)) if len(tasks) == 1 else ''
    text = str(ti.get('prompt') if is_spawn else ti.get('message', ''))
    markers = re.findall(r'^CCP_TASK_ID=([^\s]+)[ \t]*$', text, re.MULTILINE)
    task = markers[0] if len(markers) == 1 else ''
    if not markers:
        task = session_task(sender, own_dir)
    # Serialize read/modify/write; atomic replacement alone loses concurrent opens.
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load(path)
        entries = state.get('open_threads', [])
        entries = [t for t in entries if isinstance(t, dict) and t.get('peer_session')] if isinstance(entries, list) else []
        cap = int(os.environ.get('HUB_THREAD_CAP') or state.get('cap', 3))
        window = int(os.environ.get('HUB_THREAD_STALE_SECONDS') or state.get('stale_seconds', 3600))
        now = datetime.datetime.now(datetime.timezone.utc)
        if is_spawn:
            # A reservation covers concurrent pre-tool admissions until the
            # corresponding result becomes a child record, or times out.
            pending = state.get('pending_spawns', {})
            if not isinstance(pending, dict): pending = {}
            pending = {k: v for k, v in pending.items() if isinstance(v, dict) and fresh(v, now, 600)}
            tokens = re.findall(r'^CCP_SPAWN_REQUEST_ID=([A-Za-z0-9_.-]+)[ \t]*$', text, re.MULTILINE)
            request_key = payload.get('tool_use_id') or (tokens[0] if len(tokens) == 1 else '')
            if not isinstance(request_key, str) or not request_key:
                sys.stderr.write('BLOCKED: hub spawn needs a stable tool_use_id or an explicit unique CCP_SPAWN_REQUEST_ID=<request-token> prompt line; reuse that token only when retrying the same request. Messaging remains unrestricted.\n')
                return 2
            fingerprint = hashlib.sha256(json.dumps(ti, sort_keys=True).encode()).hexdigest()
            reservation = pending.get(request_key, {})
            if reservation and reservation.get('fingerprint') not in {None, fingerprint}:
                sys.stderr.write('BLOCKED: spawn request token was reused for different arguments; use a new unique request token.\n')
                return 2
            task = task or (pending.get(request_key, {}).get('task', '') if phase in {'PostToolUse', 'PostToolUseFailure'} else '')
            if not task:
                audit(path, 'unresolved spawn task; not capped; add CCP_TASK_ID=<full-task-id> line to tool prompt', sender, target)
                return 0
            spokes = state.get('administered_spokes', [])
            spokes = [x for x in spokes if isinstance(x, dict) and safe_id(x.get('sessionId'))] if isinstance(spokes, list) else []
            terminal = set(policy['concluded_session_statuses'])
            def active(meta):
                status = str(meta.get('sessionStatus') or meta.get('status') or meta.get('todoState') or '').lower().replace('_', '-')
                return not (meta.get('isArchived') or meta.get('archived')) and status not in terminal
            spokes = [x for x in spokes if active(metadata(root, x['sessionId']))]
            # Reconcile witnessed children; discover older parent/adoption
            # records only with an actual unique task gate. Real headers do
            # not carry taskId/ticket, so unknown history cannot form one bucket.
            ids = {x['sessionId'] for x in spokes}
            adopted = me.get('adoptedSessionIds', [])
            adopted = set(x for x in adopted if safe_id(x)) if isinstance(adopted, list) else set()
            if root and os.path.isdir(root):
                for child_id in os.listdir(root):
                    child = metadata(root, child_id)
                    if child_id not in ids and (parent(child) == sender or child_id in adopted) and active(child):
                        child_task = session_task(child_id)
                        if child_task:
                            spokes.append({'sessionId': child_id, 'task': child_task})
                            ids.add(child_id)
            if phase in {'PostToolUse', 'PostToolUseFailure'}:
                reservation = pending.get(request_key, {})
                response = payload.get('tool_response') or payload.get('tool_result') or {}
                if isinstance(response, str):
                    try: response = json.loads(response)
                    except Exception: response = {}
                child_id = spawned_session(response)
                def result_failed(value):
                    if isinstance(value, str):
                        try: value = json.loads(value)
                        except (ValueError, TypeError): return False
                    if isinstance(value, list): return any(result_failed(x) for x in value)
                    return isinstance(value, dict) and (bool(value.get('error') or value.get('isError'))
                        or any(result_failed(value.get(k)) for k in ('toolResults', 'content', 'text', 'structuredContent', 'tool_result', 'tool_response')))
                failed = phase == 'PostToolUseFailure' or result_failed(response) or bool(payload.get('tool_error') or payload.get('error') or payload.get('is_error'))
                if failed:
                    child_id = ''
                if child_id or failed:
                    pending.pop(request_key, None)
                else:
                    audit(path, 'unresolved spawn result; reservation retained until reconciliation/expiry', sender, target, task)
                if safe_id(child_id) and child_id not in ids:
                    spokes.append({'sessionId': child_id, 'task': reservation.get('task') or task, 'request_id': request_key, 'fingerprint': fingerprint})
                state.update(administered_spokes=spokes, pending_spawns=pending)
                persist(path, state)
                return 0
            completed = next((x for x in spokes if x.get('request_id') == request_key), None)
            if completed:
                sys.stderr.write('BLOCKED: this spawn request already created session %s; inspect or message that child instead of spawning again.\n' % completed['sessionId'])
                return 2
            if reservation and not payload.get('tool_use_id'):
                sys.stderr.write('BLOCKED: this request token already has a pending spawn; inspect its result or wait for its bounded lease before retrying.\n')
                return 2
            count = sum(x.get('task') == task for x in spokes)
            count += sum(x.get('task') == task for k, x in pending.items() if k != request_key)
            if count >= cap:
                audit(path, 'administrative cap reached at spawn', sender, target, task)
                sys.stderr.write('BLOCKED: hub administrative cap reached -- %d/%d administered spokes for task %s. Drain/retire a concluded spoke or delegate administration before spawning another. Messaging remains unrestricted. Stewards (Traffic Cop, Workspace Config, Deep Think, steward) are never limited.\n' % (count, cap, task))
                return 2
            # A witnessed completion is idempotent too: duplicated post events
            # cannot create multiple children or release another request.
            pending[request_key] = {'task': task, 'last_activity': now.isoformat(), 'fingerprint': fingerprint}
            state.update(administered_spokes=spokes, pending_spawns=pending)
            persist(path, state)
            return 0
        # Message bookkeeping is advisory only. No path below can return 2.
        task = task or 'unresolved-task'
        same = lambda t: (t.get('task') or 'unresolved-task') == task
        continuing = next((t for t in entries if same(t) and t['peer_session'] == target), None)
        kept = [t for t in entries if t is continuing or fresh(t, now, window)]
        kept = [t for t in kept if not (labels(metadata(root, t['peer_session'])) & stewards
                 or t['peer_session'] == parent(me) or parent(metadata(root, t['peer_session'])) == sender)]
        counted = [t for t in kept if same(t)]
        if continuing is None and len(counted) >= cap:
            audit(path, 'advisory message thread threshold exceeded; communication allowed', sender, target, task)
        if continuing is not None:
            continuing['last_activity'] = now.isoformat()
        else:
            kept.append({'peer_session': target, 'task': task, 'topic': str(ti.get('message', ''))[:60],
                         'opened_at': now.isoformat(), 'last_activity': now.isoformat()})
        state.update(open_threads=kept, hub_session=sender, lastUpdated=now.isoformat())
        state.setdefault('cap', cap)
        persist(path, state)
    return 0


try:
    sys.exit(main())
except Exception:
    # This is a communication load-shedder, not a safety authorization gate.
    path = os.environ.get('HUB_THREADS_FILE') or os.path.join(os.environ.get('CRAFT_SESSION_DIR', '.'), 'hub-threads.json')
    audit(path, 'bookkeeping failure; not capped')
    sys.exit(0)
PYCODE
exit $?
