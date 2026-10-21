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
