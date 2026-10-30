"""Verify a Craft session directory against the payload's session (#1099).

Craft hands each hook a CRAFT_SESSION_DIR, and it has been seen naming a
sibling session (electinfo/enterprise#2960): the variable is process-global
and set at agent creation, so a concurrent session can inherit another's.
Every session-scoped decision keyed on that directory then belongs to the
wrong session, including which task gate authorizes a mutation.

The payload's session_id is the SDK session id for the turn. Craft appends a
record for each final assistant message to <session dir>/meta/
claude-turn-anchors.json ({"anchors": {msg-id: {"sdkSessionId": ...}}}) and
never prunes it, so the file lists every SDK id the session has had. Rules,
in order:

1. the payload's id is among the env dir's anchors: the env dir stands;
2. a sibling's anchors contain it: that sibling is the session, whether or
   not the env dir has anchors of its own (a new session, or a provider that
   writes none, is the usual mis-tag target);
3. neither the env dir nor any sibling has anchors (Claude Code CLI, older
   Craft, non-Claude providers): the env dir stands, as before;
4. the env dir's anchors exist and none matches: <sessions>/<payload id>, a
   session that exists in name only, so no gate is visible and mutations fail
   closed. Right after Craft rotates a session's SDK id this costs at most the
   turn before the new id is recorded.
"""
import json
import os
import re
import stat

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
ENV_NAMES = ("CRAFT_SESSION_DIR", "CRAFT_AGENT_SESSION_DIR")
MAX_ANCHOR_BYTES = 4 * 1024 * 1024
MAX_HEADER_BYTES = 1024 * 1024
MAX_REGISTERED_SESSIONS = 2048


def _read_regular(path: str) -> str:
    """Contents of a regular file, never blocking on a FIFO or device."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return ""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_ANCHOR_BYTES:
            return ""
        chunks, left = [], MAX_ANCHOR_BYTES
        while left > 0:
            chunk = os.read(fd, min(65536, left))
            if not chunk:
                break
            chunks.append(chunk)
            left -= len(chunk)
        return b"".join(chunks).decode("utf-8", "replace")
    except OSError:
        return ""
    finally:
        os.close(fd)


def anchor_ids(session_dir: str, text: str = None) -> set:
    """Every SDK session id recorded in the session's turn anchors."""
    if text is None:
        text = _read_regular(os.path.join(session_dir, "meta", "claude-turn-anchors.json"))
    if not text:
        return set()
    try:
        data = json.loads(text)
    except ValueError:
        data = None
    found = set()
    if isinstance(data, dict) and isinstance(data.get("anchors"), dict):
        for record in data["anchors"].values():
            value = record.get("sdkSessionId") if isinstance(record, dict) else None
            if isinstance(value, str) and UUID_RE.fullmatch(value):
                found.add(value)
    if not found:
        found = set(UUID_RE.findall(text))  # older or unexpected layouts
    return found


def payload_uuid(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("session_id", "sessionId"):
        value = payload.get(key)
        if isinstance(value, str) and UUID_RE.fullmatch(value.strip()):
            return value.strip()
    return ""


def _siblings(parent: str):
    try:
        names = sorted(os.listdir(parent))
    except OSError:
        return []
    return [os.path.join(parent, n) for n in names if os.path.isdir(os.path.join(parent, n))]


def verified_session_dir(env_dir: str, payload) -> str:
    """env_dir if it belongs to the payload's session, else the session that does."""
    uuid = payload_uuid(payload)
    # Registered SDK children must retain strict provenance through every legacy
    # consumer; a tolerant raw-text anchor must never undo the router binding.
    if os.environ.get("CCP_CRAFT_ROUTER_BOUND_SDK_ID") == uuid and uuid:
        workspace = os.environ.get("CRAFT_AGENT_WORKSPACE", "")
        fixed = registered_session_dir(workspace, env_dir, payload)
        if not fixed:
            os.environ['CCP_CRAFT_ROUTER_SESSION_UNRESOLVED'] = '1'
        return fixed
    if not env_dir or not uuid:
        return env_dir
    own = anchor_ids(env_dir)
    if uuid in own:
        return env_dir
    parent = os.path.dirname(os.path.normpath(env_dir))
    for candidate in _siblings(parent):
        if os.path.normpath(candidate) == os.path.normpath(env_dir):
            continue
        # Parse a sibling only when its raw text mentions the id: a scan of
        # hundreds of sessions otherwise costs a JSON parse each.
        text = _read_regular(os.path.join(candidate, "meta", "claude-turn-anchors.json"))
        if uuid in text and uuid in anchor_ids(candidate, text):
            return candidate
    if not own:
        return env_dir  # no anchor names this dir's session either way
    return os.path.join(parent, uuid)


def _registered_header(directory: str, sessions: str):
    """Strict first-line identity inside an already verified workspace only."""
    if (os.path.dirname(directory) != sessions or os.path.realpath(directory) != directory
            or not os.path.isdir(directory)):
        return None
    path = os.path.join(directory, "session.jsonl")
    if os.path.realpath(path) != path:
        return None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                return None
            raw = stream.readline(MAX_HEADER_BYTES + 1)
        if len(raw) > MAX_HEADER_BYTES:
            return None
        def unique(items):
            value = {}
            for key, field in items:
                if key in value:
                    raise ValueError('duplicate session header field')
                value[key] = field
            return value
        header = json.loads(raw, object_pairs_hook=unique)
        if not isinstance(header, dict) or header.get('id') != os.path.basename(directory):
            return None
        sdk_id = header.get('sdkSessionId')
        if sdk_id is not None and (not isinstance(sdk_id, str) or not UUID_RE.fullmatch(sdk_id)):
            return None
        return header
    except (OSError, ValueError):
        return None


def _registered_anchor_ids(directory):
    path = os.path.join(directory, 'meta', 'claude-turn-anchors.json')
    if os.path.realpath(path) != path:
        return set()
    try:
        info = os.lstat(path)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return set()
        def unique(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError('duplicate anchor field')
                result[key] = value
            return result
        data = json.loads(_read_regular(path), object_pairs_hook=unique)
        anchors = data.get('anchors') if isinstance(data, dict) else None
        if not isinstance(anchors, dict):
            return set()
        return {item['sdkSessionId'] for item in anchors.values() if isinstance(item, dict)
                and isinstance(item.get('sdkSessionId'), str) and UUID_RE.fullmatch(item['sdkSessionId'])}
    except (OSError, ValueError):
        return set()


def registered_session_dir(workspace: str, env_dir: str, payload) -> str:
    """Exact identity binding for an already registered, verified Craft host.

    Structured anchors and exact headers must uniquely identify one session.
    A fresh SDK can persist its ID in
    the header before any final-turn anchor exists, so a bounded UNIQUE exact
    header SDK ID is a second witness. Never guess a path or borrow another
    task when metadata has not arrived; callers receive an unresolved binding.
    """
    if not os.path.isabs(workspace) or os.path.realpath(workspace) != workspace:
        return ''
    sessions = os.path.join(workspace, 'sessions')
    sdk_id = payload_uuid(payload)
    if not sdk_id or os.path.dirname(env_dir) != sessions:
        return ''
    try:
        names = os.listdir(sessions)
    except OSError:
        return ''
    if len(names) > MAX_REGISTERED_SESSIONS:
        return ''
    matches = []
    for name in names:
        directory = os.path.join(sessions, name)
        header = _registered_header(directory, sessions)
        if header and (header.get('sdkSessionId') == sdk_id or sdk_id in _registered_anchor_ids(directory)):
            matches.append(directory)
    return matches[0] if len(matches) == 1 else ''


def payload_from_env() -> dict:
    try:
        data = json.loads(os.environ.get("CCP_HOOK_INPUT_JSON", "") or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def correct_environ(payload=None) -> list:
    """Rewrite mis-tagged session dirs in os.environ; return the notes made."""
    payload = payload_from_env() if payload is None else payload
    notes = []
    for name in ENV_NAMES:
        value = os.environ.get(name, "").strip()
        if not value:
            continue
        fixed = verified_session_dir(value, payload)
        if fixed != value:
            os.environ[name] = fixed
            notes.append(f"{name} named another session ({os.path.basename(os.path.normpath(value))}); "
                         f"using {os.path.basename(os.path.normpath(fixed))} (#1099)")
    return notes
