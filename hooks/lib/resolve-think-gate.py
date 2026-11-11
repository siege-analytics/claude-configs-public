#!/usr/bin/env python3
"""Resolve gate signal files — shared by all hooks.

Authoritative mutation signals live under sessions/<id>/tasks/<slug>/.
Legacy session-level signals remain readable as one task; workspace-root
singletons never authorize mutations. One diagnostic-only unknown-session
think read requires an exact canonical repo match. Artifact identities match
full ticket/task ids, never issue-number substrings.

Usage:
    # Find think-gate for a specific repo (default, backward compat)
    python3 resolve-think-gate.py --workspace /path/to/workspace --repo-root /path/to/repo

    # Find investigate-gate for a specific repo
    python3 resolve-think-gate.py --workspace /path --repo-root /path --gate-name investigate-gate

    # Resolve multiple gate types at once (returns name-to-path map)
    python3 resolve-think-gate.py --workspace /path --repo-root /path \
        --resolve-many investigate-gate,junior-senior-gate,artifacts-posted-gate,review-gate

    # List all active think-gates (resolver hooks)
    python3 resolve-think-gate.py --workspace /path/to/workspace --all

Output (JSON):
    Single gate:  {"path": "/path/to/<gate-name>-<slug>.json", "data": {...}}
    --all:        [{"path": "...", "data": {...}}, ...]
    --resolve-many: {"investigate-gate": "/path/or/null", ...}
    Not found:    null / []

Ref: #494 (repo-scoped think-gate), #578 (all gate types)
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
import glob
import stat
import subprocess
from task_actions import action, canonical, github_ticket_reference
from session_anchor import correct_environ as _correct_session_environ

# A mis-tagged CRAFT_SESSION_DIR must not decide whose gates apply (#1099). Fix
# it in this process's environment before anything reads it; children inherit.
for _note in _correct_session_environ():
    print(f"[resolve-think-gate] {_note}", file=sys.stderr)
from typing import Optional


def repo_slug(repo_root: str) -> str:
    """Derive a filesystem-safe slug from a repo root path."""
    base = os.path.basename(repo_root.rstrip("/"))
    return re.sub(r"[^a-zA-Z0-9_-]", "_", base)


def _safe_session_id(value: str) -> str:
    # Identity must be preserved, never collapsed into a shared sanitized name.
    value = value.strip()
    if value.strip('_').upper() in {'SESSION_ID', 'SESSION_PATH', 'CRAFT_SESSION_ID', 'CRAFT_SESSION_DIR',
            'CRAFT_AGENT_SESSION_ID', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_ID',
            'CLAUDE_SESSION_DIR', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_SIGNAL_DIR',
            'CRAFT_SIGNAL_DIR', 'CRAFT_AGENT_SIGNAL_DIR'}:
        return ''
    return value if value not in {'.', '..'} and re.fullmatch(r'[a-zA-Z0-9_.-]+', value) else ''


def _craft_session_value(obj) -> str:
    """Craft transcript identity precedes SDK/native session UUID fields."""
    if not isinstance(obj, dict):
        return ""
    transcript = obj.get("transcript_path") or obj.get("transcriptPath")
    if isinstance(transcript, str):
        match = re.search(r"/sessions/([^/]+)/", transcript)
        if match:
            return match.group(1)
    for key in ("craftSessionId", "craft_session_id"):
        value = obj.get(key)
        if isinstance(value, str) and value.strip():
            return value
    for key in ("session", "conversation", "metadata"):
        value = _craft_session_value(obj.get(key))
        if value:
            return value
    return ""


def _find_session_value(obj) -> str:
    """Do not mistake a generic SDK UUID for a Craft directory identity."""
    craft = _craft_session_value(obj)
    if craft:
        return craft
    if isinstance(obj, dict):
        for key in ("sessionId", "session_id", "sessionID", "id"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip() and not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
                return value
        for key in ("session", "conversation", "metadata"):
            value = _find_session_value(obj.get(key))
            if value:
                return value
    return ""


def host_binding_present() -> bool:
    # Invalid host identity is not an unbound native terminal invocation.
    if any(os.environ.get(name, '').strip() for name in (
        'CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_DIR',
        'CRAFT_SESSION_ID', 'CRAFT_AGENT_SESSION_ID', 'CLAUDE_SESSION_ID',
        'SESSION_ID', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_SIGNAL_DIR',
        'CRAFT_SIGNAL_DIR', 'CRAFT_AGENT_SIGNAL_DIR')):
        return True
    raw_payload = os.environ.get('CCP_HOOK_INPUT_JSON', '').strip()
    try:
        payload = json.loads(raw_payload or '{}')
    except (ValueError, TypeError):
        return True
    if raw_payload and not isinstance(payload, dict):
        return True
    def bound(obj):
        if not isinstance(obj, dict):
            return False
        if 'tool_input' in obj or obj.get('tool_name'):
            return True
        if any(obj.get(key) for key in ('craftSessionId', 'craft_session_id',
               'sessionId', 'session_id', 'sessionID', 'id', 'transcript_path', 'transcriptPath')):
            return True
        return any(bound(obj.get(key)) for key in ('session', 'conversation', 'metadata'))
    return bound(payload)


def _session_directory_id(names) -> str:
    for name in names:
        directory = os.environ.get(name, "").strip()
        if directory:
            value = os.path.basename(os.path.normpath(directory))
            if value not in {".", ".."}:
                return _safe_session_id(value)
    return ""


def session_id_from_env() -> str:
    """Craft directory > Craft id > Craft transcript > native explicit id."""
    if os.environ.get("CCP_CRAFT_ROUTER_SESSION_UNRESOLVED") == "1":
        return ""
    # An unexpanded host template is not a session identity or scratch root.
    # Never sanitize it into a shared id, even if another identity is present.
    for name in ('CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_DIR'):
        directory = os.environ.get(name, '').strip()
        if directory and (not os.path.isabs(directory) or not _safe_session_id(os.path.basename(os.path.normpath(directory))) or
                          re.search(r'\{\{|\}\}|\$\{|\$[A-Za-z_]|%[A-Za-z_][^%]*%', directory)):
            return ''
    directory_id = _session_directory_id(("CRAFT_SESSION_DIR", "CRAFT_AGENT_SESSION_DIR"))
    if directory_id:
        return directory_id
    for name in ("CRAFT_SESSION_ID", "CRAFT_AGENT_SESSION_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return _safe_session_id(value)
    try:
        payload = json.loads(os.environ.get("CCP_HOOK_INPUT_JSON", "{}"))
    except Exception:
        payload = {}
    craft = _craft_session_value(payload)
    if craft:
        return _safe_session_id(craft)
    directory_id = _session_directory_id(("CLAUDE_SESSION_DIR",))
    if directory_id:
        return directory_id
    for name in ("CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "SESSION_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return _safe_session_id(value)
    value = _find_session_value(payload)
    return _safe_session_id(value) if value else ""


SESSION_UNRESOLVED = ("Session id unresolved; gates under sessions/<id>/ are not visible. "
                      "Repair the hook host's CRAFT_SESSION_DIR to the absolute actual session directory "
                      "(native: CLAUDE_SESSION_ID or CLAUDE_CODE_SESSION_ID). "
                      "Then Write <actual-session-directory>/tasks/<task-slug>/think-gate.json; never use a shared root. "
                      "An SDK UUID or ordinary Claude transcript path alone is not a Craft directory id.")


def session_unresolved_message() -> str:
    names = ('CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_DIR',
             'CRAFT_SESSION_ID', 'CRAFT_AGENT_SESSION_ID', 'CLAUDE_SESSION_ID',
             'CLAUDE_CODE_SESSION_ID', 'SESSION_ID')
    present = [name for name in names if os.environ.get(name, '').strip()]
    return SESSION_UNRESOLVED + (' Present bindings to check: ' + ', '.join(present) + '.' if present else ' No supported environment session binding was supplied.')


def session_dirs(workspace: str, session_id: str = "") -> "list[str]":
    """Candidate session-scoped signal directories, highest priority first."""
    dirs: list[str] = []
    # CRAFT_SESSION_DIR is the var Craft actually sets (#697). The
    # CRAFT_AGENT_ prefixed names never resolve at runtime; kept for
    # backward compat with any explicit exporter.
    for name in ("CLAUDE_SIGNAL_DIR", "CRAFT_SIGNAL_DIR", "CRAFT_AGENT_SIGNAL_DIR", "CRAFT_SESSION_DIR", "CRAFT_AGENT_SESSION_DIR", "CLAUDE_SESSION_DIR"):
        value = os.environ.get(name, "").strip()
        if value:
            dirs.append(value)
    sid = session_id or session_id_from_env()
    if sid:
        dirs.append(os.path.join(workspace, "sessions", sid))
        dirs.append(os.path.join(workspace, "session-signals", sid))
    # Deduplicate while preserving order.
    out: list[str] = []
    seen = set()
    for d in dirs:
        if d not in seen:
            out.append(d)
            seen.add(d)
    return out


_METADATA_GIT_REDIRECT_ENV = frozenset({
    "GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
    "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
})


def _metadata_git_redirect(name: str) -> bool:
    return name in _METADATA_GIT_REDIRECT_ENV or name.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))


def _metadata_git_environment() -> dict[str, str]:
    """Observe the granted physical repository, not a caller's Git target.

    Same location/config isolation as the canary's private-repository reads;
    ordinary Git action classification deliberately retains its ambient env.
    """
    environment = {key: value for key, value in os.environ.items() if not _metadata_git_redirect(key)}
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    return environment


def _git_origin(path: str, *, git_environment: Optional[dict] = None) -> str:
    try:
        if git_environment is not None:
            # Keep global trust/auth settings, but only repository-owned origin
            # values supply authority. Explicit includes inherit local/worktree
            # ownership. Local values precede worktree values in Git's order.
            for scope in ("--local", "--worktree"):
                result = subprocess.run(
                    ["git", "-C", path, "config", scope, "--includes", "--null",
                     "--get-all", "remote.origin.url"],
                    text=True, capture_output=True, timeout=3, env=git_environment)
                if result.returncode == 1:  # No key: try worktree-only config.
                    continue
                if result.returncode != 0:
                    return ""
                # Git fetch/gh use the first URL, not --get's last value.
                first = result.stdout.split("\0", 1)[0]
                if not first or first != first.strip() or any(ord(c) < 32 or ord(c) == 127 for c in first):
                    return ""
                return first
            return ""
        return subprocess.check_output(
            ["git", "-C", path, "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3, env=git_environment,
        ).strip()
    except Exception:
        return ""


def _nearest_directory(path: str) -> str:
    """The canonical nearest existing directory at or above path, or ''."""
    directory = canonical(path)
    while not os.path.isdir(directory):
        parent = os.path.dirname(directory)
        if parent == directory:
            return ""
        directory = parent
    return directory


def _toplevel(directory: str, *, git_environment: Optional[dict] = None) -> str:
    """The git toplevel for directory, or '' when the lookup fails. No failed
    lookup (any exit status, timeout, launch failure or signal) proves that a
    repository is absent, so only a non-empty result may be reused."""
    try:
        return canonical(subprocess.check_output(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL, timeout=3, env=git_environment).strip())
    except Exception:
        return ""


def _target_repo(path: str, *, git_environment: Optional[dict] = None) -> str:
    directory = _nearest_directory(path)
    return _toplevel(directory, git_environment=git_environment) if directory else ""
def _entry_present(directory: str, name: str) -> bool:
    try:
        os.lstat(os.path.join(directory, name))
        return True
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return True


def _git_entry_above(path: str) -> bool:
    """Whether a Git layout exists at or above path (filesystem only, #1281).

    A `.git` entry, or a Git directory itself (bare repository or `.git`
    internals: HEAD, objects and refs), makes an empty toplevel a failed
    lookup, not a non-Git target. A stat error other than absence counts as
    present so it cannot reopen the skip.
    """
    directory = canonical(path)
    while True:
        if _entry_present(directory, ".git") or all(
                _entry_present(directory, name) for name in ("HEAD", "objects", "refs")):
            return True
        parent = os.path.dirname(directory)
        if parent == directory:
            return False
        directory = parent


def _scope_diagnostic(gate: dict, expected_repo: str, *, git_environment: Optional[dict] = None) -> str:
    declared = str(gate["data"].get("repo_root", ""))
    return (f"Task gate scope rejected: {gate['path']} declares repo_root={declared} "
            f"(origin={_git_origin(declared, git_environment=git_environment) or '<none>'}); expected target repo={expected_repo} "
            f"(origin={_git_origin(expected_repo, git_environment=git_environment) or '<none>'}). "
            "Set repo_root to the task's TARGET repository, not the session CWD/workspace repository.")


def _origin_to_slug(url: str) -> str:
    """Normalize a git remote URL to an 'org/repo' slug, or '' if not parseable.

    Handles the common forms:
      git@github.com:org/repo.git       -> org/repo
      https://github.com/org/repo.git   -> org/repo
      ssh://git@github.com/org/repo      -> org/repo
    """
    if not url:
        return ""
    u = url.strip()
    if u.endswith(".git"):
        u = u[:-4]
    # scp-like: git@host:org/repo
    m = re.search(r"[:/]([^/:]+/[^/:]+)$", u)
    return m.group(1) if m else ""


def resolve_project(repo_root: str, workspace: str = "") -> str:
    """Map the current repo to a project slug, or 'umbrella' if none matches.

    #873 P3 (defect D2). The skills/rules layer already scopes by project via
    projects/<slug>/PROJECT.md (repo: field, build-validated unique). This gives
    the GATE layer the same notion: a gate file can be scoped per project, and
    umbrella (Siege general) gates apply only when no project matches.

    Matching is by git origin slug (org/repo) of repo_root against each
    PROJECT.md's `repo:` field -- the same key the build uses for uniqueness.
    Falls back to 'umbrella' on no/ambiguous match, never raising.
    """
    origin = _origin_to_slug(_git_origin(repo_root))
    if not origin:
        return "umbrella"
    search_roots = []
    if workspace:
        search_roots.append(os.path.join(workspace, "projects"))
    # the repo's own projects/ dir (source checkouts), deduped
    repo_projects = os.path.join(repo_root, "projects")
    if repo_projects not in search_roots:
        search_roots.append(repo_projects)
    for proot in search_roots:
        if not os.path.isdir(proot):
            continue
        for manifest in sorted(glob.glob(os.path.join(proot, "*", "PROJECT.md"))):
            repo_field = _project_repo_field(manifest)
            if repo_field and repo_field == origin:
                return os.path.basename(os.path.dirname(manifest))
    return "umbrella"


def _project_repo_field(manifest_path: str) -> str:
    """Read the `repo:` value from a PROJECT.md YAML frontmatter, or '' on miss.

    A deliberately tiny frontmatter reader: PROJECT.md frontmatter is flat
    key: value, so a line scan between the --- fences avoids a yaml dependency
    in a hook-path library.
    """
    try:
        with open(manifest_path, encoding="utf-8") as f:
            text = f.read(4096)
    except Exception:
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    front = text[3:end] if end != -1 else text[3:]
    for line in front.splitlines():
        m = re.match(r"\s*repo:\s*(\S+)\s*$", line)
        if m:
            return m.group(1).strip().strip("'\"")
    return ""


def _same_repo(gate_repo: str, repo_root: str, *, git_environment: Optional[dict] = None) -> bool:
    if not gate_repo:
        return True
    if not repo_root:
        return False
    try:
        if os.path.realpath(gate_repo) == os.path.realpath(repo_root):
            return True
    except (OSError, TypeError, ValueError) as exc:
        print(f"[resolve-think-gate] Cannot compare repository identity: {exc}", file=sys.stderr)
        return False
    gate_origin = _git_origin(gate_repo, git_environment=git_environment)
    repo_origin = _git_origin(repo_root, git_environment=git_environment)
    return bool(gate_origin and repo_origin and gate_origin == repo_origin)


def _gate_matches_scope(loaded: dict, repo_root: str, session_id: str) -> bool:
    data = loaded.get("data", {})
    gate_session = str(data.get("session", "")).strip()
    gate_session_id = str(data.get("sessionId", "")).strip()
    if session_id:
        if gate_session and gate_session != session_id:
            return False
        if gate_session_id and gate_session_id != session_id:
            return False
    gate_repo = str(data.get("repo_root", "")).strip()
    if gate_repo and not _same_repo(gate_repo, repo_root):
        print(_scope_diagnostic(loaded, repo_root), file=sys.stderr)
        return False
    return True


def _artifact_matches_strict_scope(loaded: dict, repo_root: str, session_id: str) -> bool:
    """Artifact gates must be explicitly scoped; generic artifacts do not authorize mutation."""
    data = loaded.get("data", {})
    if not str(data.get("repo_root", "")).strip():
        return False
    if session_id and not (str(data.get("session", "")).strip() or str(data.get("sessionId", "")).strip()):
        return False
    return _gate_matches_scope(loaded, repo_root, session_id)


def task_identity(data: dict) -> str:
    """Full ticket refs or explicit task ids; never compare #N substrings."""
    return str(data.get("ticket") or data.get("task_id") or data.get("task") or "").strip()


def task_slug(identity: str) -> str:
    # Hash suffix makes sanitization collision-safe, including explicit ids.
    import hashlib
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "-", identity).strip(".-")[:80] or "task"
    return stem + "-" + hashlib.sha256(identity.encode()).hexdigest()[:12]


def task_binding() -> str:
    return os.environ.get("CCP_TASK_ID", "").strip()


def _gate_matches_ticket(loaded: dict, current_ticket: str, *, require_explicit: bool = False) -> bool:
    identity = task_identity(loaded.get("data", {}))
    return identity == current_ticket if current_ticket else not require_explicit


def _within(path: str, scope: str) -> bool:
    try:
        return os.path.commonpath([canonical(path), canonical(scope)]) == canonical(scope)
    except (ValueError, TypeError):
        return False


def _scopes(loaded: dict) -> list[str]:
    d = loaded["data"]
    paths = d.get("scope_paths")
    if paths is None:
        paths = [d.get("repo_root")] if d.get("repo_root") else []
    if not isinstance(paths, list) or any(not isinstance(p, str) or not os.path.isabs(p) for p in paths):
        return []
    return [canonical(p) for p in paths]


def _canonical_claim(sd: str, sid: str, identity: str) -> str:
    import hashlib
    key = hashlib.sha256((sid + '\0' + identity).encode()).hexdigest()
    return os.path.join(canonical(sd), 'tasks', '.canonical', key + '.json')


def _canonical_seen(sd: str, sid: str, identity: str, workspace: str) -> bool:
    if not identity or canonical(sd) == canonical(workspace):
        return False
    path = _canonical_claim(sd, sid, identity)
    if not _within(canonical(os.path.dirname(path)), canonical(sd)):
        return True  # An invalid migration namespace cannot lend legacy authority.
    return os.path.lexists(path)


def _remember_canonical(sd: str, sid: str, identity: str, workspace: str) -> None:
    """Atomic, per-(session,task) denial-only migration claim; never a gate."""
    import tempfile
    path = _canonical_claim(sd, sid, identity)
    parent = canonical(os.path.dirname(path))
    if canonical(sd) == canonical(workspace) or not _within(parent, canonical(sd)):
        raise ValueError('canonical claim path escapes current session')
    expected = {'task_id': identity, 'sessionId': sid}
    if os.path.lexists(path):
        if os.path.islink(path):
            raise ValueError('reserved canonical claim is a symlink: ' + path)
        existing = _load(path)
        if not existing or existing['data'] != expected:
            raise ValueError('repair invalid reserved canonical claim: ' + path)
        return
    os.makedirs(parent, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=parent, prefix='.claim-')
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(expected, stream)
        try:
            os.link(temp, path)  # exclusive atomic publish; never replace user data
        except FileExistsError:
            if os.path.islink(path):
                raise ValueError('reserved canonical claim is a symlink: ' + path)
            existing = _load(path)
            if not existing or existing['data'] != expected:
                raise ValueError('repair invalid reserved canonical claim: ' + path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _remember_managed_paths(workspace: str, paths: list[str]) -> None:
    sid = session_id_from_env()
    for sd in session_dirs(workspace, sid):
        for path in paths:
            think = canonical(os.path.join(os.path.dirname(path), 'think-gate.json'))
            if os.path.dirname(os.path.dirname(think)) != canonical(os.path.join(sd, 'tasks')):
                continue
            loaded = _load(think)
            if loaded and _gate_matches_session(loaded, sid) and task_identity(loaded['data']):
                _remember_canonical(sd, sid, task_identity(loaded['data']), workspace)


def _session_thinks(workspace: str, session_id: str = "") -> list[dict]:
    sid = session_id or session_id_from_env()
    if not sid:
        print(session_unresolved_message(), file=sys.stderr)
        return []
    result, seen, canonical_ids = [], set(), set()
    for sd in session_dirs(workspace, sid):
        if canonical(sd) == canonical(workspace):
            continue
        for path in sorted(glob.glob(os.path.join(sd, "tasks", "*", "think-gate.json"))):
            if not _within(canonical(path), canonical(sd)):
                continue
            loaded = _load(path)
            if loaded and _gate_matches_session(loaded, sid) and task_identity(loaded["data"]):
                identity = task_identity(loaded["data"])
                key = canonical(path)
                if key not in seen:
                    canonical_ids.add(identity)
                    try:
                        _remember_canonical(sd, sid, identity, workspace)
                    except (OSError, ValueError) as exc:
                        print(f'Canonical retirement record unavailable for {identity}: {exc}', file=sys.stderr)
                    result.append(loaded)
                    seen.add(key)
    for sd in session_dirs(workspace, sid):
        if canonical(sd) == canonical(workspace):
            continue
        for path in sorted(glob.glob(os.path.join(sd, "think-gate*.json"))):
            if not _within(canonical(path), canonical(sd)):
                continue
            loaded = _load(path)
            if (loaded and _gate_matches_session(loaded, sid)
                    and task_identity(loaded["data"]) not in canonical_ids
                    and not any(_canonical_seen(d, sid, task_identity(loaded['data']), workspace)
                                for d in session_dirs(workspace, sid))
                    and canonical(path) not in seen):
                result.append(loaded)
                seen.add(canonical(path))
    # Per-task canonical claims survive individual gate cleanup. Other legacy
    # tasks remain independent; no session-wide namespace switch is used.
    return [g for g in result if str(g['data'].get('status', '')).lower() not in
            {'disposed', 'complete', 'completed', 'done', 'done-awaiting-pr'}]


def _gate_matches_session(loaded: dict, session_id: str) -> bool:
    return all(not loaded["data"].get(k) or str(loaded["data"][k]) == session_id
               for k in ("session", "sessionId")) if session_id else True


def task_bootstrap_help(workspace: str, session_id: str = "") -> str:
    """Explain an own-task bootstrap without requiring a ticket or hash tool."""
    sid = session_id or session_id_from_env()
    if not sid:
        return "Restore the host session binding first; never create shared workspace-root gates."
    directory = own_session_directory(workspace, sid)
    if not os.path.isabs(directory) or os.path.basename(os.path.normpath(directory)) != sid:
        directory = os.path.join(workspace, 'sessions', sid)
    return (f"Use the Write tool to create {directory}/tasks/<task-slug>/think-gate.json. "
            "Choose a stable unique non-hidden slug; no hash computation or GitHub ticket is required. "
            "Set task_id (or the full ticket), sessionId, target repo_root, scope_paths and status for this task. "
            "Own-session task gate JSON and plans can be bootstrapped without another gate. "
            "Keep JSON companions beside this task's gate; write its pre-mortem under this session's plans/ naming the task_id. Never overwrite root signals or another task. "
            "Then satisfy only this task's effective review tier; see [skill:think].")


def select_task(workspace: str, paths: list[str], binding: str = "", session_id: str = "",
                *, git_environment: Optional[dict] = None) -> dict:
    """Resolve all targets to one owner. Explicit binding disambiguates, not expands scope."""
    if not (session_id or session_id_from_env()):
        return {"gate": None, "error": session_unresolved_message()}
    candidates = _session_thinks(workspace, session_id)
    binding = binding or task_binding()
    if binding:
        candidates = [g for g in candidates if task_identity(g["data"]) == binding]
    # Long literal operand lists must not cost git subprocesses per target.
    # Within this one resolution, a toplevel depends only on the canonical
    # nearest existing directory and an identity verdict only on its exact
    # repository pair, so each is asked once. Only a successful toplevel is
    # reused; a failed lookup is never cached as an identity.
    toplevels: dict[str, str] = {}
    identities: dict[tuple[str, str], bool] = {}

    def expected_repo_of(path: str) -> str:
        directory = _nearest_directory(path)
        if not directory:
            return ""
        if directory not in toplevels:
            toplevel = _toplevel(directory, git_environment=git_environment)
            if not toplevel:
                return toplevel
            toplevels[directory] = toplevel
        return toplevels[directory]

    def same_repo(declared: str, expected: str) -> bool:
        if (declared, expected) not in identities:
            identities[(declared, expected)] = _same_repo(declared, expected, git_environment=git_environment)
        return identities[(declared, expected)]

    selected = []
    for path in paths:
        scores = []
        rejected = []
        expected_repo = expected_repo_of(path)
        # Failed observations inside Git layouts must deny immediately; only
        # successful toplevels are cached, so failure never spreads to siblings.
        unresolved = not expected_repo and _git_entry_above(path)
        for gate in candidates:
            declared = str(gate["data"].get("repo_root", ""))
            if declared and (expected_repo or unresolved) and not same_repo(declared, expected_repo):
                rejected.append(gate)  # Diagnosed only if this target ends unowned.
                continue
            matching = [len(p.split(os.sep)) for p in _scopes(gate) if _within(path, p)]
            if matching:
                scores.append((max(matching), gate))
        if not scores:
            diagnostics = [
                _scope_diagnostic(gate, expected_repo, git_environment=git_environment) if expected_repo else
                f"Task gate scope rejected: {gate['path']} declares repo_root={gate['data'].get('repo_root', '')}; "
                f"target repository is unresolved for {path} (git rev-parse failed while a .git entry or Git directory exists at or above it)."
                for gate in rejected]
            return {"gate": None, "error": "Unscoped mutation: open a task gate with scope_paths for this action.\n" + task_bootstrap_help(workspace, session_id) + ("\n" + "\n".join(diagnostics) if diagnostics else "")}
        best = max(s for s, _ in scores)
        winners = [g for score, g in scores if score == best]
        if len(winners) != 1:
            return {"gate": None, "error": "Ambiguous task ownership: " + ", ".join(sorted(task_identity(g["data"]) for g in winners))}
        selected.append(winners[0])
    if not selected or len({canonical(g["path"]) for g in selected}) != 1:
        return {"gate": None, "error": "Mutation spans multiple tasks; split the action into task-scoped calls."}
    return {"gate": selected[0], "error": ""}


def _artifact_for(think: dict, name: str, workspace: str, session_id: str = "") -> Optional[dict]:
    identity = task_identity(think["data"])
    if not identity:
        return None
    directory = os.path.dirname(think["path"])
    # Canonical task files are the sole authority. A legacy session think file
    # can consume newly written task artifacts, then its own legacy siblings.
    dirs = [directory]
    if os.path.basename(os.path.dirname(directory)) != "tasks":
        dirs.insert(0, os.path.join(directory, "tasks", task_slug(identity)))
    for d in dirs:
        paths = [os.path.join(d, name + ".json")]
        if d == directory and os.path.basename(think["path"]) != "think-gate.json":
            suffix = os.path.basename(think["path"])[len("think-gate"):-5]
            paths.insert(0, os.path.join(d, name + suffix + ".json"))
        for path in paths:
            if canonical(os.path.dirname(path)) != canonical(d):
                continue
            if os.path.dirname(canonical(path)) != canonical(d):
                continue
            loaded = _load(path)
            if loaded and _gate_matches_session(loaded, session_id or session_id_from_env()) and _gate_matches_ticket(loaded, identity, require_explicit=True):
                # Explicit foreign repo metadata cannot satisfy this task either.
                repo = loaded["data"].get("repo_root")
                expected_repo = think["data"].get("repo_root")
                if repo and expected_repo and not _same_repo(repo, expected_repo):
                    print(_scope_diagnostic(loaded, expected_repo), file=sys.stderr)
                    continue
                if repo and not expected_repo and not any(_same_repo(repo, _target_repo(p) or p) for p in _scopes(think)):
                    print(_scope_diagnostic(loaded, ", ".join(_scopes(think))), file=sys.stderr)
                    continue
                return loaded
    return None


def write_directory(think: dict, workspace: str, session_id: str = "") -> str:
    """Only session/task dirs may receive writes; root legacy is read-only."""
    identity = task_identity(think["data"])
    if not identity:
        return ""
    path = canonical(think["path"])
    for sd in session_dirs(workspace, session_id):
        sd = canonical(sd)
        if not _within(path, sd) or sd == canonical(workspace):
            continue
        directory = os.path.dirname(path)
        if os.path.basename(os.path.dirname(directory)) == "tasks":
            return directory
        if directory == sd:
            return os.path.join(sd, "tasks", task_slug(identity))
    return ""


def find_gate_for_repo(workspace: str, repo_root: str, gate_name: str = "think-gate", env_override: str = "", session_id: str = "") -> Optional[dict]:
    paths = [repo_root]
    try:
        payload = json.loads(os.environ.get("CCP_HOOK_INPUT_JSON", "{}"))
        if not isinstance(payload, dict):
            return None
        if payload.get("cwd"):
            ti = payload.get("tool_input") or {}
            if not isinstance(ti, dict):
                return None
            shape = action(ti.get("command", ""), payload["cwd"]) if ti.get("command") else {"paths": [repo_root or payload["cwd"]]}
            # A proven read has no mutation targets; select the task by the repo
            # instead of sending an empty target list through mutation selection.
            paths = shape.get("paths") or [repo_root or payload["cwd"]]
    except (ValueError, TypeError):
        return None
    selection = select_task(workspace, paths, session_id=session_id)
    found = selection["gate"]
    if found:
        if env_override and canonical(env_override) != canonical(found["path"]):
            return None
        return found if gate_name == "think-gate" else _artifact_for(found, gate_name, workspace, session_id)
    # Sole root legacy read: UNKNOWN session, exact canonical repo match.
    # Diagnostic consumers only: resolve_action never uses this path.
    if gate_name == "think-gate" and not (session_id or session_id_from_env() or session_dirs(workspace) or host_binding_present()):
        legacy = _load(os.path.join(workspace, gate_name + ".json"))
        if legacy and legacy["data"].get("repo_root") and canonical(legacy["data"]["repo_root"]) == canonical(repo_root):
            return legacy
    # Native pre-push (no session identity): the pre-#1051 workspace or repository
    # test-gate.json is the evidence a terminal push supplies (#1092 review).
    if gate_name == "test-gate" and not (session_id or session_id_from_env() or host_binding_present()):
        for root in dict.fromkeys(p for p in (workspace, repo_root) if p):
            legacy = _load(os.path.join(root, "test-gate.json"))
            if legacy:
                return legacy
    if selection.get("error") and ("scope rejected" in selection["error"] or not selection["error"].startswith("Unscoped mutation:")):
        print(selection["error"], file=sys.stderr)
    return None


def find_session_gate(workspace: str, gate_name: str = "think-gate", session_id: str = "") -> Optional[dict]:
    if not (session_id or session_id_from_env()):
        print(session_unresolved_message(), file=sys.stderr)
        return None
    gates = _session_thinks(workspace, session_id)
    binding = task_binding()
    if binding:
        gates = [g for g in gates if task_identity(g["data"]) == binding]
    if len(gates) != 1:
        return None
    return gates[0] if gate_name == "think-gate" else _artifact_for(gates[0], gate_name, workspace, session_id)


def resolve_many_session(workspace: str, gate_names: list[str], session_id: str = "") -> dict:
    think = find_session_gate(workspace, session_id=session_id)
    return {n: (g["path"] if (g := _artifact_for(think, n, workspace, session_id)) else None) if think else None for n in gate_names}


def find_think_gate_for_repo(workspace: str, repo_root: str, env_override: str = "") -> Optional[dict]:
    return find_gate_for_repo(workspace, repo_root, "think-gate", env_override)


def find_all_gates(workspace: str, gate_name: str = "think-gate", session_id: str = "") -> list[dict]:
    gates = _session_thinks(workspace, session_id)
    if gate_name == "think-gate":
        return gates
    return [g for tg in gates if (g := _artifact_for(tg, gate_name, workspace, session_id))]


def find_all_think_gates(workspace: str) -> list[dict]:
    return find_all_gates(workspace)


def resolve_many(workspace: str, repo_root: str, gate_names: list[str], session_id: str = "") -> dict:
    selection = select_task(workspace, [repo_root], session_id=session_id)
    think = selection["gate"]
    if selection.get("error") and ("scope rejected" in selection["error"] or not selection["error"].startswith("Unscoped mutation:")):
        print(selection["error"], file=sys.stderr)
    return {n: (g["path"] if (g := _artifact_for(think, n, workspace, session_id)) else None) if think else None for n in gate_names}


def _candidate_paths(workspace: str, repo_root: str, gate_name: str, session_id: str = "") -> list[str]:
    return [g["path"]] if (g := find_gate_for_repo(workspace, repo_root, gate_name, session_id=session_id)) else []


def own_session_directory(workspace: str, session_id: str = '') -> str:
    sid = session_id or session_id_from_env()
    if not sid:
        return ''
    return next((os.environ.get(k) for k in ('CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_DIR')
                 if os.environ.get(k)), os.path.join(workspace, 'sessions', sid))


def own_session_path(workspace: str, path: str, directory: bool = False, removal: bool = False) -> bool:
    """Narrow lifecycle exception, not task/repository implementation authority.

    Only the host-resolved current session owns these paths. Canonicalization
    rejects descendant symlinks into another session/repository.
    """
    sid = session_id_from_env()
    if not sid:
        return False
    sd = own_session_directory(workspace, sid)
    root = canonical(sd)
    target = canonical(path)
    if root == canonical(workspace) or not _within(target, root) or target == root:
        return False
    if _within(target, canonical(os.path.join(root, 'tasks', '.canonical'))):
        return False  # Reserved per-task migration claims are not lifecycle files.
    if not removal:
        # A file with another name elsewhere is not scratch (#1100): canonical
        # paths see symlinks, not hardlinks, and a write here changes both.
        try:
            st = os.stat(target)
        except FileNotFoundError:
            st = None  # Creating a new lifecycle file has no existing hardlink alias.
        except OSError as exc:
            print(f"[resolve-think-gate] Cannot inspect lifecycle target: {exc}", file=sys.stderr)
            return False
        if st is not None and not os.path.isdir(target) and st.st_nlink > 1:
            return False
    parts = os.path.relpath(target, root).split(os.sep)
    if parts[0] in {'plans', 'data'}:
        return len(parts) > 1 or directory
    if parts[0] != 'tasks':
        return False
    if directory:
        return len(parts) <= 2 and not (removal and len(parts) == 1)
    return len(parts) >= 3 and not os.path.isdir(target) and bool(re.fullmatch(r'[A-Za-z0-9_.-]+-gate\.json', parts[-1]))


def resolve_action(workspace: str, payload: dict) -> dict:
    ti = payload.get("tool_input") or {}
    command = ti.get("command", "")
    cwd = payload.get("cwd") or os.getcwd()
    if isinstance(command, str) and re.match(r'^\s*gh\s+(?:pr\s+merge|api\s+graphql)(?:\s|$)', command):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('merge_queue', os.path.join(os.path.dirname(__file__), 'github-merge-queue.py'))
            queue = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(queue)
            target = queue.parse(command)
            if target is not None:
                verified = queue.verify(target, cwd)
                if verified is not None:
                    queue.audit(verified, session_id_from_env(), own_session_directory(workspace))
                    return {'read_only': False, 'paths': [], 'remote_only_authorized': True,
                            'queue_enqueue': verified, 'error': ''}
        except (OSError, ValueError, TypeError, KeyError, ImportError, SyntaxError) as exc:
            label = 'Queue enqueue denied: ' if re.match(r'^\s*gh\s+api\s', command) else 'Pinned merge denied: '
            return {'read_only': False, 'paths': [], 'gate': None, 'error': label + str(exc)}
    shape = action(command, cwd) if command else {"read_only": False, "paths": [canonical(ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or cwd, cwd)]}
    if not shape.get("metadata_posts") and (shape["read_only"] or shape.get('investigation') or shape.get("metadata_only") or shape.get("remote_contact_only")):
        return shape  # No gate lookup for recognized reads/approved diagnostics/allowlisted ssh (#1160).
    if shape.get("error"):
        return {**shape, "gate": None, "error": "Cannot resolve mutation targets: " + shape["error"]}
    post_selected = None
    if shape.get('metadata_posts'):
        if shape.get('remote_actions') or shape.get('review_actions'):
            return {**shape, 'gate': None, 'error': 'Split metadata posts from separately granted remote operations.'}
        post_selected = select_metadata_post_task(workspace, shape)
        if not post_selected.get('gate'):
            return {**shape, **post_selected}
        if not shape['paths']:
            # Reporting evidence is not implementation. This existing remote
            # authorization flag is set only after own-Task/target proof above.
            return {**shape, **post_selected, 'remote_only_authorized': True}
        if shape['paths']:
            local = select_task(workspace, shape['paths'], shape.get('binding') or task_binding())
            if not local.get('gate') or canonical(local['gate']['path']) != canonical(post_selected['gate']['path']):
                return {**shape, 'gate': None, 'error': 'Metadata posts and local mutations require the same own Task.'}
    if shape.get('review_actions'):
        if shape.get('remote_actions'):
            return {**shape, 'gate': None, 'error': 'Split review and project remote operations; each has its own grant.'}
        remote = select_review_task(workspace, shape, cwd)
        if not remote.get('gate') or not shape['paths']:
            return {**shape, **remote, 'remote_only_authorized': bool(remote.get('gate')) and not shape['paths']}
        local = select_task(workspace, shape['paths'], shape.get('binding') or task_binding())
        if not local.get('gate') or canonical(local['gate']['path']) != canonical(remote['gate']['path']):
            return {**shape, 'gate': None, 'error': 'Review and local mutations must belong to the same own task; split this action.'}
    if shape.get('remote_actions'):
        remote = select_project_task(workspace, shape)
        if not remote.get('gate') or not shape['paths']:
            return {**shape, **remote, 'remote_only_authorized': bool(remote.get('gate')) and not shape['paths']}
        # Remote permission never replaces local ownership or implementation gates.
        local = select_task(workspace, shape['paths'], shape.get('binding') or task_binding())
        if not local.get('gate') or canonical(local['gate']['path']) != canonical(remote['gate']['path']):
            return {**shape, 'gate': None, 'error': local.get('error') or 'Local and remote mutations belong to different tasks; split the action.'}
    managed_shape = shape.get('self_managed_shape', not command)
    if managed_shape:
        directories = shape.get('directory_paths', [])
        remaining = [p for p in shape['paths'] if not own_session_path(workspace, p, p in directories, p in shape.get('directory_removals', []) or p in shape.get('file_removals', []))]
        if not remaining:
            try:
                _remember_managed_paths(workspace, shape['paths'])
            except (OSError, ValueError) as exc:
                return {**shape, 'gate': None, 'error': 'Cannot preserve per-task canonical retirement: ' + str(exc)}
            return {**shape, 'self_management': True}
        shape['paths'] = remaining
    binding = shape.get("binding") or task_binding()
    if shape.get("binding") and task_binding() and shape["binding"] != task_binding():
        return {**shape, "gate": None, "error": "Conflicting explicit task bindings."}
    selected = post_selected or select_task(workspace, shape["paths"], binding)
    result = {**shape, **selected}
    if result["gate"]:
        tg = result["gate"]
        if shape.get("test_receipt_output"):
            expected_gate = canonical(tg["path"])
            requested_gate = shape["test_receipt_gate"]
            output = shape["test_receipt_output"]
            expected_output = os.path.join(os.path.dirname(expected_gate), "test-gate.json")
            valid = (tg["data"].get("status") == "implementing"
                     and os.path.basename(expected_gate) == "think-gate.json"
                     and requested_gate == expected_gate == os.path.abspath(tg["path"])
                     and canonical(requested_gate) == requested_gate
                     and output == expected_output and canonical(output) == output
                     and own_session_path(workspace, requested_gate)
                     and own_session_path(workspace, output)
                     and bool(tg["data"].get("repo_root"))
                     and canonical(tg["data"]["repo_root"]) == shape["test_receipt_repo"])
            if not valid:
                return {**result, "gate": None, "error": "Test execution requires the selected own-task implementing think gate and its exact adjacent test-gate.json receipt; repair task/output ownership before rerunning."}
        result["session_dir"] = own_session_directory(workspace)
        result["artifacts"] = {name: g["path"] if (g := _artifact_for(tg, name, workspace)) else None for name in ("investigate-gate", "junior-senior-gate", "artifacts-posted-gate", "review-gate", "test-gate")}
        result["task"] = task_identity(tg["data"])
        result["tier"] = task_tier(tg["data"], shape["paths"], command, cwd)
    return result


def select_metadata_post_task(workspace: str, shape: dict) -> dict:
    """Bind descriptive remote posts to existing own-Task repository authority.

    Repository paths below prove already declared scope; they are not invented
    filesystem mutation targets. Pure reports do not acquire code-mutation rights.
    """
    def deny(message):
        return {'gate': None, 'error': 'GitHub metadata target scope: ' + message}
    if not session_id_from_env():
        return deny('verified current-session identity required')
    binding = shape.get('binding') or task_binding()
    if shape.get('binding') and task_binding() and binding != task_binding():
        return deny('conflicting explicit Task bindings')
    if (os.environ.get('GH_HOST') or 'github.com').casefold() != 'github.com':
        return deny('ambient GitHub host override is unproven')
    if os.environ.get('GH_REPO') and any(not target['repository'] for target in shape['metadata_posts']):
        return deny('implicit repository under GH_REPO is unproven; use a literal --repo or canonical URL')
    command_environment = dict(os.environ)
    inspection_environment = _metadata_git_environment()
    cache = {}
    def repository(root):
        if root not in cache:
            from urllib.parse import urlsplit
            raw = _git_origin(root, git_environment=inspection_environment)
            scp = re.fullmatch(r'git@github\.com:([^?#]+)', raw, re.I)
            if scp:
                path = scp[1]
            else:
                try:
                    url = urlsplit(raw)
                    if url.scheme not in {'https', 'ssh'} or (url.hostname or '').casefold() != 'github.com' or url.query or url.fragment:
                        cache[root] = ''; return ''
                    path = url.path.lstrip('/')
                except ValueError:
                    cache[root] = ''; return ''
            path = re.sub(r'\.git$', '', path)
            cache[root] = path.casefold() if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path) and not any(x in {'.', '..'} for x in path.split('/')) else ''
        return cache[root]
    def implicit_repository(cwd):
        # Observe gh's actual command cwd/environment, not a sanitized
        # authority root or a configured core.worktree's apparent toplevel.
        root = canonical(cwd)
        try:
            remotes = subprocess.check_output(['git', '-C', root, 'remote'],
                text=True, stderr=subprocess.DEVNULL, timeout=3, env=command_environment).splitlines()
            resolved = subprocess.run(['git', '-C', root, 'config', '--get-regexp',
                r'^remote\..*\.gh-resolved$'], capture_output=True, timeout=3, env=command_environment)
            # gh can prefer upstream/github or an explicitly resolved default.
            # Resolve such targets explicitly instead of borrowing origin.
            if remotes != ['origin'] or resolved.returncode != 1:
                return ''
            effective = subprocess.check_output(['git', '-C', root, 'remote',
                'get-url', 'origin'], text=True,
                stderr=subprocess.DEVNULL, timeout=3, env=command_environment).splitlines()
            if len(effective) != 1:
                return ''
            from urllib.parse import urlsplit
            raw = effective[0]
            if not raw or raw != raw.strip() or any(ord(c) < 32 or ord(c) == 127 for c in raw):
                return ''
            scp = re.fullmatch(r'git@github\.com:([^?#]+)', raw, re.I)
            if scp:
                path = scp[1]
            else:
                url = urlsplit(raw)
                if url.scheme not in {'https', 'ssh'} or (url.hostname or '').casefold() != 'github.com' or url.query or url.fragment:
                    return ''
                path = url.path.lstrip('/')
            path = re.sub(r'\.git$', '', path)
            slug = path.casefold() if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path) and not any(x in {'.', '..'} for x in path.split('/')) else ''
            return slug
        except (OSError, subprocess.SubprocessError, ValueError):
            return ''

    owners = []
    for gate in _session_thinks(workspace):
        data = gate['data']; identity = task_identity(data)
        if binding and identity != binding:
            continue
        allowed = set()
        verified_scope = False
        for scope in _scopes(gate):
            root = _target_repo(scope, git_environment=inspection_environment)
            if not root:
                continue
            proof = select_task(workspace, [scope], identity, git_environment=inspection_environment)
            if proof.get('gate') and canonical(proof['gate']['path']) == canonical(gate['path']):
                verified_scope = True
                slug = repository(root)
                if slug: allowed.add(slug)
        if not verified_scope:
            continue
        ticket = re.fullmatch(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([1-9][0-9]*)', identity)
        matched = True
        for target in shape['metadata_posts']:
            actual = target['repository'] or implicit_repository(target['cwd'])
            own_ticket = bool(ticket and target['resource'] == 'issue' and target['operation'] == 'comment'
                              and actual == ticket[1].casefold() and target['selector'] == ticket[2])
            if not actual or actual not in allowed and not own_ticket:
                matched = False; break
        if matched:
            owners.append(gate)
    if len(owners) != 1:
        return deny('one unambiguous own Task with actual repository scope or its canonical ticket is required; use a literal --repo/canonical URL when gh defaults or URL rewrites are ambiguous, and do not borrow cwd for another remote repository')
    return {'gate': owners[0], 'error': ''}


def select_review_task(workspace: str, shape: dict, cwd: str) -> dict:
    """A review write uses the existing own-task grant, never cwd authority."""
    def deny(message):
        return {'gate': None, 'error': 'GitHub review scope: ' + message}
    if not session_id_from_env(): return deny('verified current-session identity required')
    binding = shape.get('binding') or task_binding()
    if shape.get('binding') and task_binding() and binding != task_binding():
        return deny('conflicting explicit task bindings')
    if (os.environ.get('GH_HOST') or 'github.com') != 'github.com' or os.environ.get('GH_REPO'):
        return deny('ambient GitHub host/repository override unsupported')
    if len(shape['review_actions']) != 1:
        return deny('one bounded review operation per invocation required')
    target = shape['review_actions'][0]
    query = ('query($id:ID!){node(id:$id){... on PullRequestReviewThread{'
             'id __typename viewerCanResolve isResolved pullRequest{number body headRefOid '
             'repository{nameWithOwner} closingIssuesReferences(first:100){nodes{number repository{nameWithOwner}}}}}}}')
    try:
        import importlib.util
        import time
        spec = importlib.util.spec_from_file_location('review_reader', os.path.join(os.path.dirname(__file__), 'craft-settings-router.py'))
        runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
        deadline = time.monotonic() + 3.0

        def read(arguments):
            remaining = deadline - time.monotonic()
            if remaining <= 0: raise ValueError('review identity read deadline exhausted')
            code, output, _ = runner.execute_hook(shlex.join(['gh'] + arguments), b'', dict(os.environ), remaining)
            if code or len(output.encode()) > 65536: raise ValueError('bounded review identity lookup failed')
            return json.loads(output)

        if target['kind'] == 'resolve-review-thread':
            node = read(['api', 'graphql', '-f', 'query=' + query, '-f', 'id=' + target['thread_id']])['data']['node']
            if (not isinstance(node, dict) or node.get('__typename') != 'PullRequestReviewThread'
                    or node.get('id') != target['thread_id'] or node.get('viewerCanResolve') is not True):
                return deny('thread identity or current resolution permission does not match')
            pr = node['pullRequest']
        else:
            repository, number = target['repository'], target['number']
            comment = read(['api', 'repos/' + repository + '/pulls/comments/' + str(target['comment_id'])])
            if not isinstance(comment, dict) or type(comment.get('id')) is not int or comment['id'] != target['comment_id']:
                return deny('actual review comment identity differs')
            url = comment.get('pull_request_url')
            link = re.fullmatch(r'https://api\.github\.com/repos/([^/]+/[^/]+)/pulls/([1-9][0-9]*)', url) if isinstance(url, str) else None
            if not link or link[1].casefold() != repository.casefold() or int(link[2]) != number:
                return deny('actual review comment does not belong to the declared repository/PR')
            owner, name = repository.split('/')
            query = ('query($owner:String!,$name:String!,$pr:Int!){repository(owner:$owner,name:$name){pullRequest(number:$pr){'
                     'number body headRefOid repository{nameWithOwner} closingIssuesReferences(first:100){nodes{number repository{nameWithOwner}}}}}}')
            pr = read(['api', 'graphql', '-f', 'query=' + query, '-f', 'owner=' + owner,
                       '-f', 'name=' + name, '-F', 'pr=' + str(number)])['data']['repository']['pullRequest']
        if not isinstance(pr, dict): return deny('missing PR identity')
        repository = pr['repository']['nameWithOwner']
        if (not isinstance(repository, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', repository)
                or type(pr['number']) is not int or pr['number'] < 1):
            return deny('invalid thread repository/PR identity')
        if target['kind'] == 'reply-review-comment' and (repository.casefold() != target['repository'].casefold() or pr['number'] != target['number']):
            return deny('actual PR identity differs from the reply target')
        tickets = {repository.lower() + '#' + str(pr['number'])}
        links = pr.get('closingIssuesReferences', {})
        if not isinstance(links, dict) or not isinstance(links.get('nodes'), list) or len(links['nodes']) > 100:
            return deny('invalid bounded linked-ticket evidence')
        for issue in links['nodes']:
            if not isinstance(issue, dict) or not isinstance(issue.get('repository'), dict):
                return deny('malformed linked-ticket identity')
            owner = issue['repository'].get('nameWithOwner')
            if (not isinstance(owner, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+', owner)
                    or type(issue.get('number')) is not int or issue['number'] < 1):
                return deny('malformed linked-ticket identity')
            tickets.add(owner.lower() + '#' + str(issue['number']))
        body = pr.get('body')
        if body is None: body = ''
        if not isinstance(body, str): return deny('uninspectable actual PR body')
        owners = []
        for gate in _session_thinks(workspace):
            data = gate['data']; value = data.get('ticket') or data.get('task_id', '')
            match = re.fullmatch(r'([A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+)#([1-9][0-9]*)', value) if isinstance(value, str) else None
            if not match: continue
            if value.lower() not in tickets and not github_ticket_reference(body, int(match[2]), match[1],
                                                                            kind='reference', source_repo=repository):
                continue
            alias = data.get('task_id', '')
            if isinstance(alias, str) and re.fullmatch(r'[^/\s]+/[^#\s]+#[1-9][0-9]*', alias) and alias.lower() != value.lower():
                return deny('conflicting canonical ticket/task_id')
            if not binding or task_identity(data) == binding: owners.append(gate)
        if len(owners) != 1: return deny('one unambiguous own task bound to this PR or its linked ticket required')
        gate = owners[0]; data = gate['data']; role = str(data.get('role', '')).lower()
        if re.search(r'read.only|review.only', role) or role == 'reviewer':
            return deny('read-only/review-only assignment cannot post or resolve without its existing comment-only grant')
        status = data.get('status')
        if status != 'implementing' and not (status in {'reviewing', 'verifying'} and role == 'comment-only'
                                               and isinstance(data.get('authorized_by'), str) and data['authorized_by'].strip()):
            return deny('existing author or explicit comment-only review grant required; planned/read-only work is insufficient')
        return {'gate': gate, 'review_target': {'repository': repository, 'number': pr['number'],
                                               'operation': target['kind']}, 'error': ''}
    except (OSError, ValueError, TypeError, KeyError, ImportError) as error:
        return deny('cannot verify actual thread/PR/task binding: ' + str(error))


def project_policy() -> list:
    """Fixed installed policy, owned and delivered with the hook source."""
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'github-project-policy.json'))
    if canonical(path) != path:
        raise ValueError('standing policy must be a regular installed file, not a symlink')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate standing policy key: ' + key)
            result[key] = value
        return result
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    with os.fdopen(fd, encoding='utf-8') as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 65536:
            raise ValueError('standing policy must be a bounded regular installed file')
        data = json.loads(source.read(65537), object_pairs_hook=unique)
    if not isinstance(data, dict) or set(data) != {'schema_version', 'grants'} or type(data['schema_version']) is not int or data['schema_version'] != 1 or not isinstance(data['grants'], list):
        raise ValueError('invalid GitHub project standing policy schema')
    fields = {'host', 'owner', 'project', 'operation', 'issue_owner', 'issue_binding', 'authority_source'}
    seen = set()
    for grant in data['grants']:
        extra = {'field_name', 'field_type', 'values'} if isinstance(grant, dict) and grant.get('operation') == 'item-edit' else set()
        if not isinstance(grant, dict) or set(grant) != fields | extra:
            raise ValueError('invalid GitHub project standing grant fields')
        if (grant['host'] != 'github.com' or grant['operation'] not in {'item-add', 'item-edit'}
                or grant['issue_binding'] != 'current-task-ticket'
                or type(grant['project']) is not int or grant['project'] < 1
                or any(not isinstance(grant[k], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*', grant[k]) for k in ('owner', 'issue_owner'))
                or not isinstance(grant['authority_source'], str) or not grant['authority_source'].strip()):
            raise ValueError('invalid GitHub project standing grant values')
        if extra and (grant['field_name'] != 'Status' or grant['field_type'] != 'SINGLE_SELECT'
                      or not isinstance(grant['values'], list) or not grant['values']
                      or any(v not in ('In Progress', 'In Review') for v in grant['values'])
                      or len(set(grant['values'])) != len(grant['values'])):
            raise ValueError('item-edit grant is limited to Status In Progress/In Review')
        key = (grant['host'], grant['owner'].lower(), grant['project'], grant['issue_owner'].lower(), grant['operation'])
        if key in seen:
            raise ValueError('ambiguous duplicate GitHub project standing grants')
        seen.add(key)
    return data['grants']


def select_project_task(workspace: str, shape: dict) -> dict:
    """Standing permission narrows to one current task's exact canonical ticket."""
    def deny(message):
        return {'gate': None, 'error': 'GitHub project remote scope: ' + message}
    if not session_id_from_env():
        return deny('restore the current-session task identity; filesystem scope cannot supply remote authority.')
    binding = shape.get('binding') or task_binding()
    if shape.get('binding') and task_binding() and shape['binding'] != task_binding():
        return deny('conflicting explicit task bindings.')
    if (os.environ.get('GH_HOST') or 'github.com').lower() != 'github.com' or os.environ.get('GH_REPO'):
        return deny('ambient GH_HOST/GH_REPO overrides do not match the literal scoped operation.')
    try:
        grants = project_policy()
    except (OSError, ValueError, TypeError) as exc:
        return deny('cannot validate installed standing policy: ' + str(exc))
    if any(t['operation'] == 'item-edit' for t in shape['remote_actions']) and len(shape['remote_actions']) != 1:
        return deny('split Status edits from other remote mutations; one bounded live lookup per invocation.')
    selected = []
    for target in shape['remote_actions']:
        if target['operation'] == 'item-edit':
            if not any(g['operation'] == 'item-edit' for g in grants):
                return deny('installed standing policy has no Status item-edit grant.')
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location('github_status', os.path.join(os.path.dirname(__file__), 'github-project-status.py'))
                module = importlib.util.module_from_spec(spec)
                sys.dont_write_bytecode = True
                spec.loader.exec_module(module)
                target = module.verify(target, grants)
            except (OSError, ValueError, TypeError) as error:
                return deny('cannot verify live Status membership: ' + str(error))
        permitted = any(g['host'] == target['host'] and g['operation'] == target['operation']
                        and g['project'] == target['project'] and g['owner'].lower() == target['owner'].lower()
                        and g['issue_owner'].lower() == target['issue_owner'].lower() for g in grants)
        if not permitted:
            return deny('installed standing policy does not grant this owner/project/issue-owner operation; task fields cannot grant it.')
        ticket = f"{target['issue_owner']}/{target['repository']}#{target['issue']}".lower()
        owners = []
        for gate in _session_thinks(workspace):
            value = gate['data'].get('ticket') or gate['data'].get('task_id', '')
            if (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+#[1-9][0-9]*', value)
                    and value.lower() == ticket and (not binding or task_identity(gate['data']) == binding)):
                alias = gate['data'].get('task_id', '')
                if (isinstance(alias, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+#[1-9][0-9]*', alias)
                        and alias.lower() != ticket):
                    return deny('conflicting canonical issue in ticket and task_id; repair the owning task identity.')
                owners.append(gate)
        if len(owners) != 1:
            return deny('requires one unambiguous current-session task with canonical ticket or task_id=' + ticket + '; a parent, slug or local scope is insufficient.')
        gate = owners[0]
        if gate['data'].get('status') != 'implementing':
            return deny('the owning task must be implementing; no remote authority from another lifecycle status.')
        selected.append(gate)
    if len({canonical(g['path']) for g in selected}) != 1:
        return deny('remote mutations span different tasks; split the action.')
    return {'gate': selected[0], 'error': '', 'task': task_identity(selected[0]['data'])}


TIER_ORDER = {"A": 0, "B": 1, "C": 2}


def _git_lines(repo: str, *args: str) -> Optional[list]:
    """Return Git lines, or None when Git cannot establish the requested listing."""
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return [l for l in out.stdout.split("\0" if "-z" in args else "\n") if l] if out.returncode == 0 else None


def _lone_git_commit(command: str) -> bool:
    """A single `git [-C dir] commit ...` with no other shell command. Quoted
    text (a `fix(hooks): a -> b` message) is not an operator (#1092 review)."""
    if not command:
        return False
    from task_actions import shell_tokens, UnknownShape
    try:
        tokens = shell_tokens(command)
    except UnknownShape:
        return False
    if any(is_op for _, is_op, _ in tokens):
        return False
    words = [t for t, _, _ in tokens]
    i = 1
    while i + 1 < len(words) and words[i] in {"-C", "-c"}:
        i += 2
    return bool(words) and words[0] == "git" and i < len(words) and words[i] == "commit"


def _named_git_add_targets(command: str, cwd: str, repo_root: str) -> Optional[list]:
    """Risk targets for a lone, explicit named-file staging operation.

    This never selects task ownership. Unproved shapes retain the ordinary
    repository-wide risk calculation, including directories and missing files.
    """
    from task_actions import shell_tokens, UnknownShape
    from git_command import prefix
    try:
        tokens = shell_tokens(command)
        if any(operator or globs for _, operator, globs in tokens):
            return None
        words = [word for word, _, _ in tokens]
        if words and words[0].startswith('CCP_TASK_ID='):
            words = words[1:]
        if not words or words[0] != 'git':
            return None
        # Restrict dispatch before reusing the shared normalizer: aliases and
        # configuration overrides are not part of this named-file exception.
        rest = words[1:]
        while rest and rest[0].startswith('-'):
            if rest[0] == '-C' and len(rest) > 1:
                rest = rest[2:]
            elif rest[0].startswith('-C') and len(rest[0]) > 2:
                rest = rest[1:]
            elif rest[0] in {'--no-pager', '--no-optional-locks'}:
                rest = rest[1:]
            else:
                return None
        if not rest or rest[0] != 'add':
            return None
        operation = prefix(words, cwd)
        if not operation or operation['config'] or operation['args'][0] != 'add':
            return None
        targets, terminated = [], False
        allowed = {'-f', '--force', '-v', '--verbose', '-u', '--update', '-A', '--all'}
        for word in operation['args'][1:]:
            if not terminated and word == '--':
                terminated = True
                continue
            if not terminated and word.startswith('-'):
                if word not in allowed:
                    return None
                continue
            if not word or word.startswith(':') or any(c in word for c in '*?[\n\r\0'):
                return None
            lexical = os.path.abspath(os.path.join(operation['cwd'], word))
            target = canonical(word, operation['cwd'])
            if (target != lexical or not _within(target, repo_root)
                    or not stat.S_ISREG(os.lstat(target).st_mode)):
                return None
            targets.append(os.path.relpath(target, repo_root).replace(os.sep, '/'))
        return sorted(set(targets)) if targets else None
    except (UnknownShape, OSError, subprocess.SubprocessError):
        return None


def _pytest_execution_targets(command: str, cwd: str, repo_root: str) -> Optional[list]:
    """Risk view for bounded task-owned test execution, not a reader certificate.

    Local remote-tracking refs are a checkout risk heuristic, not a server
    freshness proof or an authority grant. Existing Git metadata trust applies.
    """
    from task_actions import shell_tokens, UnknownShape, _options
    try:
        tokens = shell_tokens(command)
    except UnknownShape:
        return None
    while tokens and tokens[0][0].startswith('CCP_TASK_ID=') and not tokens[0][1] and not tokens[0][2]:
        tokens.pop(0)
    effective = canonical(cwd)
    if (len(tokens) >= 3 and tokens[0][0] == 'cd' and tokens[2][0] == '&&'
            and tokens[2][1] and not tokens[1][1] and not tokens[1][2]
            and not tokens[1][0].startswith('-')):
        effective = canonical(tokens[1][0], effective)
        tokens = tokens[3:]
    if not tokens or any(operator or glob for _, operator, glob in tokens):
        return None
    args = [word for word, _, _ in tokens]
    if args[0] == 'pytest':
        arguments = args[1:]
    elif args[:3] == ['python3', '-m', 'pytest'] or args[:3] == ['python', '-m', 'pytest']:
        arguments = args[3:]
    else:
        return None
    if effective != repo_root or os.environ.get('PYTEST_ADDOPTS') or os.environ.get('PYTEST_PLUGINS'):
        return None
    flags = set('-q -qq -v -vv -x -s --collect-only --disable-warnings --strict-markers --strict-config --no-header --no-summary'.split())
    values = set('-k -m --maxfail --tb --color'.split())
    if not _options(arguments, flags=flags, values=values):
        return None
    selectors, literal, index = [], False, 0
    while index < len(arguments):
        word = arguments[index]
        if not literal and word == '--':
            literal = True
        elif not literal and word.startswith('-'):
            if word.partition('=')[0] in values and '=' not in word:
                index += 1
        else:
            selector = word.split('::', 1)[0]
            path = canonical(selector, effective)
            if not _within(path, repo_root) or not os.path.exists(path) or os.path.islink(os.path.join(effective, selector)):
                return None
            relative = os.path.relpath(path, repo_root).replace(os.sep, '/')
            if os.path.isdir(path):
                listed = _git_lines(repo_root, 'ls-files', '--cached', '--others', '-z', '--', relative)
                if listed is None:
                    raise ValueError('cannot list explicit test selector')
                selectors.extend(listed)
            else:
                selectors.append(relative)
        index += 1
    bases = []
    for ref in ('refs/remotes/origin/main', 'refs/remotes/origin/develop'):
        existing = _git_lines(repo_root, 'rev-parse', '--verify', ref)
        if existing is None:
            continue
        common = _git_lines(repo_root, 'merge-base', ref, 'HEAD')
        if common is None or len(common) != 1:
            raise ValueError('cannot resolve protected test-execution baseline')
        bases.append(common[0])
    if not bases:
        raise ValueError('test execution has no canonical remote main/develop baseline')
    base = bases[0]
    for candidate in bases[1:]:
        if _git_lines(repo_root, 'merge-base', '--is-ancestor', base, candidate) is not None:
            base = candidate
        elif _git_lines(repo_root, 'merge-base', '--is-ancestor', candidate, base) is None:
            raise ValueError('test execution has incomparable protected baselines')
    changed = []
    for arguments in (
            ('diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', '--no-renames', base, 'HEAD'),
            ('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z', '--no-renames'),
            ('diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', '--no-renames'),
            ('ls-files', '--others', '--exclude-standard', '-z')):
        paths = _git_lines(repo_root, *arguments)
        if paths is None:
            raise ValueError('cannot enumerate changed test-execution paths')
        changed.extend(paths)
    return sorted(set(changed + selectors))


def _worktree_materialization_targets(command: str, cwd: str, repo_root: str) -> Optional[list]:
    """Risk of a bounded new checkout, not authority to create it or its branch.

    Task selection still owns every source/destination path, and the operation
    guard still owns develop provenance. Unchanged source-tree files are not
    authored changes merely because Git materializes them in an assigned path.
    """
    from task_actions import shell_tokens, UnknownShape
    from git_command import prefix
    try:
        tokens = shell_tokens(command)
        if tokens and tokens[0][0].startswith('CCP_TASK_ID=') and not tokens[0][1] and not tokens[0][2]:
            tokens = tokens[1:]
        if not tokens or any(operator or glob for _, operator, glob in tokens):
            return None
        words = [word for word, _, _ in tokens]
        if words[0] != 'git':
            return None
        rest = words[1:]
        while rest and rest[0].startswith('-'):
            if rest[0] == '-C' and len(rest) > 1:
                rest = rest[2:]
            elif rest[0].startswith('-C') and len(rest[0]) > 2:
                rest = rest[1:]
            elif rest[0] in {'--no-pager', '--no-optional-locks'}:
                rest = rest[1:]
            else:
                return None
        if rest[:2] != ['worktree', 'add']:
            return None
        operation = prefix(words, cwd)
        if not operation or operation['config'] or operation['args'][:2] != ['worktree', 'add']:
            return None
        operands, branch, detached, literal = [], None, False, False
        options = iter(operation['args'][2:])
        for word in options:
            if not literal and word == '--':
                literal = True
            elif not literal and word == '-b':
                if branch is not None:
                    return None
                branch = next(options, '')
                if not branch or branch.startswith('-'):
                    return None
            elif not literal and word in {'--detach', '-d'}:
                detached = True
            elif not literal and word in {'-q', '--quiet', '--no-checkout'}:
                continue
            elif not literal and word.startswith('-'):
                return None  # No force/reset, configuration or unknown options.
            else:
                operands.append(word)
        if len(operands) != 2 or branch and detached:
            return None
        source_root = _git_lines(operation['cwd'], 'rev-parse', '--show-toplevel')
        if source_root is None:
            raise ValueError('cannot resolve worktree materialization repository')
        if source_root != [repo_root]:
            return None
        destination = canonical(operands[0], operation['cwd'])
        if os.path.lexists(destination):
            return None  # Existing destinations retain conservative assessment.
        source = operands[1]
        if source.startswith('-'):
            return None
        head = _git_lines(repo_root, 'rev-parse', '--verify', source + '^{commit}')
        if head is None or len(head) != 1:
            raise ValueError('cannot resolve worktree materialization source')
        # Offline known develop is sufficient; no network or new permission is
        # introduced by this risk view. Missing Git evidence is never empty risk.
        baseline_ref = None
        for ref in ('refs/remotes/origin/develop', 'refs/heads/develop'):
            if _git_lines(repo_root, 'rev-parse', '--verify', ref + '^{commit}'):
                baseline_ref = ref
                break
        if baseline_ref is None:
            raise ValueError('worktree materialization has no proven develop baseline')
        changed = []
        current = _git_lines(repo_root, 'rev-parse', '--verify', 'HEAD^{commit}')
        if current is None or len(current) != 1:
            raise ValueError('cannot resolve current worktree revision')
        for revision in set(head + current):
            baseline = _git_lines(repo_root, 'merge-base', baseline_ref, revision)
            if baseline is None or len(baseline) != 1:
                raise ValueError('worktree materialization has no comparable develop baseline')
            listed = _git_lines(repo_root, 'diff', '--no-ext-diff', '--no-textconv',
                                '--name-only', '-z', '--no-renames', baseline[0], revision)
            if listed is None:
                raise ValueError('cannot enumerate committed worktree materialization changes')
            changed.extend(listed)
        for arguments in (
                ('diff', '--no-ext-diff', '--no-textconv', '--cached', '--name-only', '-z', '--no-renames'),
                ('diff', '--no-ext-diff', '--no-textconv', '--name-only', '-z', '--no-renames'),
                ('ls-files', '--others', '--exclude-standard', '-z')):
            listed = _git_lines(repo_root, *arguments)
            if listed is None:
                raise ValueError('cannot enumerate worktree materialization changes')
            changed.extend(listed)
        if _within(destination, repo_root):
            # A newly created checkout *inside* a critical directory is still a
            # critical target, independent of the checked-out files' contents.
            changed.append(os.path.relpath(destination, repo_root).replace(os.sep, '/') + '/__any__')
        return sorted(set(changed))
    except (UnknownShape, OSError, subprocess.SubprocessError):
        return None


def task_tier(gate: dict, paths: list, command: str = "", cwd: str = "") -> dict:
    """Effective review tier for this mutation (#1086): the higher of the gate's
    declared `tier` and the floor bin/review-risk.py computes for the targets.

    A target the shape analysis records as a directory or the repository
    toplevel (tree-wide commands: rm -r, cp -r, git apply/merge/pull/reset,
    scripts) is classified by the tracked files under it plus a probe path
    inside it, so `rm -rf hooks/bash` is C wherever hooks/bash holds Tier C
    files. A lone `git commit` is classified by the staged and modified files
    it can record. A lone explicit named-file git add uses those files for
    risk while retaining repository ownership. A declared lower tier never
    wins; a missing classifier,
    policy, repo_root or git listing fails closed to C. Bounded root pytest
    uses its branch/working delta and selectors, with at least B; normal task
    ownership and preparation requirements still apply."""
    declared = str(gate.get("tier") or gate.get("review_tier") or "").strip().upper()
    declared = declared if declared in TIER_ORDER else ""
    root = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    floor, reasons = "C", []
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("review_risk", os.path.join(root, "bin", "review-risk.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with open(os.path.join(root, "catalog", "review-risk-policy.json")) as fh:
            policy = json.load(fh)
        repo_root = os.path.realpath(gate["repo_root"]) if gate.get("repo_root") else ""
        if not repo_root:
            raise ValueError("gate has no repo_root")
        rel = []
        worktree_targets = _worktree_materialization_targets(command, cwd or repo_root, repo_root)
        pytest_targets = (_pytest_execution_targets(command, cwd or repo_root, repo_root)
                          if any(os.path.realpath(p) == repo_root for p in paths) else None)
        # A lone commit records only staged/modified files: its other operands
        # (message words such as "docs: a/b") are not targets. Only when the
        # repository itself is a target, so the staged set is what gets classified.
        lone_commit = _lone_git_commit(command) and any(os.path.realpath(p) == repo_root for p in paths)
        named_add = _named_git_add_targets(command, cwd or repo_root, repo_root)
        for p in paths:
            if worktree_targets is not None:
                continue  # All paths already passed own-Task scope selection.
            rp = os.path.realpath(p)
            if lone_commit and rp != repo_root:
                continue
            if not (rp == repo_root or rp.startswith(repo_root + os.sep)):
                raise ValueError("target outside the gate's repo_root")
            r = "" if rp == repo_root else os.path.relpath(rp, repo_root).replace(os.sep, "/")
            if r == "" and named_add is not None:
                rel.extend(named_add)
            elif r == "" and pytest_targets is not None:
                rel.extend(pytest_targets)
            elif r == "" and lone_commit:
                staged = _git_lines(repo_root, "diff", "--cached", "--name-only", "-z")
                modified = _git_lines(repo_root, "diff", "--name-only", "-z")
                if staged is None or modified is None:
                    raise ValueError("cannot enumerate commit targets")
                rel.extend((staged + modified) or ["(empty commit)"])
            elif r == "" or os.path.isdir(rp):
                files = _git_lines(repo_root, "ls-files", "-z", "--", r or ".")
                if files is None:
                    raise ValueError("cannot list files under " + (r or "the repository"))
                rel.extend(files + [(r + "/" if r else "") + "__any__"])
            else:
                rel.append(r)
        if worktree_targets is not None:
            rel.extend(worktree_targets)
        verdict = module.classify(policy, sorted(set(rel)))
        floor, reasons = verdict["computed_tier"], [x for x in verdict["reasons"] if x.startswith(verdict["computed_tier"])]
        if pytest_targets is not None and TIER_ORDER[floor] < TIER_ORDER['B']:
            floor, reasons = 'B', ['B:task-owned test execution']
        if worktree_targets is not None and TIER_ORDER[floor] < TIER_ORDER['B']:
            floor, reasons = 'B', ['B:task-owned worktree materialization']
    except Exception as exc:
        floor, reasons = "C", [f"C:{exc}; failing closed" if isinstance(exc, ValueError)
                               else f"C:review-risk classifier unavailable ({type(exc).__name__}); failing closed"]
    effective = declared if declared and TIER_ORDER[declared] > TIER_ORDER[floor] else floor
    return {"effective": effective, "declared": declared, "floor": floor, "reasons": reasons[:6]}


def _load(path: str) -> Optional[dict]:
    """Return a gate object, or None for missing, unreadable or malformed input."""
    try:
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return {"path": path, "data": data} if isinstance(data, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--action-json", action="store_true", help="Classify hook input and resolve task mutation authority")
    parser.add_argument("--write-dir", action="store_true", help="Resolve canonical task write directory")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--env-override", default="")
    parser.add_argument("--gate-name", default="think-gate")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--session-value", action="store_true", help="Print resolved runtime session identity without gate lookup")
    parser.add_argument("--session-known", action="store_true", help="Return 1 if a current session id is resolvable, else 0")
    parser.add_argument("--session-gate", action="store_true", help="Resolve <gate-name>.json from the current session's own signal dir only, no repo binding (#926)")
    parser.add_argument("--session-scoped", action="store_true", help="With --resolve-many: resolve from the session dir only; no --repo-root required (#926)")
    parser.add_argument("--project", action="store_true", help="Print the project slug for --repo-root (or 'umbrella')")
    parser.add_argument(
        "--resolve-many", default="",
        help="Comma-separated gate names; returns name-to-path map",
    )
    args = parser.parse_args()

    if args.session_value:
        print(args.session_id or session_id_from_env())
        return
    if args.action_json:
        try:
            payload = json.loads(os.environ.get("CCP_HOOK_INPUT_JSON", "{}"))
            print(json.dumps(resolve_action(args.workspace, payload)))
        except Exception:
            print(json.dumps({"read_only": False, "gate": None, "error": "Task/action resolution failed closed."}))
        return
    if args.write_dir:
        think = find_gate_for_repo(args.workspace, args.repo_root, session_id=args.session_id) if args.repo_root else find_session_gate(args.workspace, session_id=args.session_id)
        print(write_directory(think, args.workspace, args.session_id) if think else "")
        return
    if args.session_known:
        print("1" if (args.session_id or session_id_from_env()) else "0")
        return

    if args.project:
        print(resolve_project(args.repo_root, args.workspace))
        return

    if args.session_gate:
        result = find_session_gate(args.workspace, args.gate_name, args.session_id)
        print(json.dumps(result))
        return

    if args.resolve_many:
        names = [n.strip() for n in args.resolve_many.split(",") if n.strip()]
        if args.session_scoped:
            result = resolve_many_session(args.workspace, names, args.session_id)
            print(json.dumps(result))
            return
        if not args.repo_root:
            print(json.dumps({}))
            return
        result = resolve_many(args.workspace, args.repo_root, names, args.session_id)
        print(json.dumps(result))
    elif args.all:
        results = find_all_gates(args.workspace, args.gate_name, args.session_id)
        print(json.dumps(results))
    elif args.repo_root:
        result = find_gate_for_repo(
            args.workspace, args.repo_root, args.gate_name, args.env_override, args.session_id,
        )
        print(json.dumps(result))
    else:
        print(json.dumps(None))


if __name__ == "__main__":
    main()
