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
import subprocess
from task_actions import action, canonical
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
    # An unexpanded host template is not a session identity or scratch root.
    # Never sanitize it into a shared id, even if another identity is present.
    for name in ('CRAFT_SESSION_DIR', 'CRAFT_AGENT_SESSION_DIR', 'CLAUDE_SESSION_DIR'):
        directory = os.environ.get(name, '').strip()
        if directory and (not os.path.isabs(directory) or
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
    for name in ("CLAUDE_SESSION_ID", "SESSION_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return _safe_session_id(value)
    value = _find_session_value(payload)
    return _safe_session_id(value) if value else ""


SESSION_UNRESOLVED = ("Session id unresolved; gates under sessions/<id>/ are not visible. "
                      "Have the hook host supply CRAFT_SESSION_DIR "
                      "(CLAUDE_SESSION_ID for a native runtime); an SDK UUID or ordinary Claude transcript path alone is not a Craft directory id.")


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


def _git_origin(path: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", path, "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=3,
        ).strip()
    except Exception:
        return ""


def _target_repo(path: str) -> str:
    directory = canonical(path)
    while not os.path.isdir(directory):
        parent = os.path.dirname(directory)
        if parent == directory:
            return ""
        directory = parent
    try:
        return canonical(subprocess.check_output(
            ["git", "-C", directory, "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL, timeout=3).strip())
    except Exception:
        return ""


def _scope_diagnostic(gate: dict, expected_repo: str) -> str:
    declared = str(gate["data"].get("repo_root", ""))
    return (f"Task gate scope rejected: {gate['path']} declares repo_root={declared} "
            f"(origin={_git_origin(declared) or '<none>'}); expected target repo={expected_repo} "
            f"(origin={_git_origin(expected_repo) or '<none>'}). "
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


def _same_repo(gate_repo: str, repo_root: str) -> bool:
    if not gate_repo:
        return True
    if not repo_root:
        return False
    try:
        if os.path.realpath(gate_repo) == os.path.realpath(repo_root):
            return True
    except Exception:
        pass
    gate_origin = _git_origin(gate_repo)
    repo_origin = _git_origin(repo_root)
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
        print(SESSION_UNRESOLVED, file=sys.stderr)
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
            "Keep companion evidence beside this task's gate; never overwrite root signals or another task. "
            "Then satisfy only this task's effective review tier; see [skill:think].")


def select_task(workspace: str, paths: list[str], binding: str = "", session_id: str = "") -> dict:
    """Resolve all targets to one owner. Explicit binding disambiguates, not expands scope."""
    if not (session_id or session_id_from_env()):
        return {"gate": None, "error": SESSION_UNRESOLVED}
    candidates = _session_thinks(workspace, session_id)
    binding = binding or task_binding()
    if binding:
        candidates = [g for g in candidates if task_identity(g["data"]) == binding]
    selected = []
    for path in paths:
        scores = []
        rejected = []
        expected_repo = _target_repo(path)
        for gate in candidates:
            declared = str(gate["data"].get("repo_root", ""))
            if declared and expected_repo and not _same_repo(declared, expected_repo):
                rejected.append(_scope_diagnostic(gate, expected_repo))
                continue
            matching = [len(p.split(os.sep)) for p in _scopes(gate) if _within(path, p)]
            if matching:
                scores.append((max(matching), gate))
        if not scores:
            return {"gate": None, "error": "Unscoped mutation: open a task gate with scope_paths for this action.\n" + task_bootstrap_help(workspace, session_id) + ("\n" + "\n".join(rejected) if rejected else "")}
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
        if payload.get("cwd"):
            ti = payload.get("tool_input") or {}
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
    if gate_name == "think-gate" and not (session_id or session_id_from_env() or session_dirs(workspace)):
        legacy = _load(os.path.join(workspace, gate_name + ".json"))
        if legacy and legacy["data"].get("repo_root") and canonical(legacy["data"]["repo_root"]) == canonical(repo_root):
            return legacy
    # Native pre-push (no session identity): the pre-#1051 workspace or repository
    # test-gate.json is the evidence a terminal push supplies (#1092 review).
    if gate_name == "test-gate" and not (session_id or session_id_from_env()):
        for root in dict.fromkeys(p for p in (workspace, repo_root) if p):
            legacy = _load(os.path.join(root, "test-gate.json"))
            if legacy:
                return legacy
    if selection.get("error") and ("scope rejected" in selection["error"] or not selection["error"].startswith("Unscoped mutation:")):
        print(selection["error"], file=sys.stderr)
    return None


def find_session_gate(workspace: str, gate_name: str = "think-gate", session_id: str = "") -> Optional[dict]:
    if not (session_id or session_id_from_env()):
        print(SESSION_UNRESOLVED, file=sys.stderr)
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
            if not os.path.isdir(target) and st.st_nlink > 1:
                return False
        except OSError:
            pass
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
    shape = action(command, cwd) if command else {"read_only": False, "paths": [canonical(ti.get("file_path") or ti.get("notebook_path") or ti.get("path") or cwd, cwd)]}
    if shape["read_only"] or shape.get('investigation'):
        return shape  # No gate lookup for recognized reads/approved diagnostics.
    if shape.get("error"):
        return {**shape, "gate": None, "error": "Cannot resolve mutation targets: " + shape["error"]}
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
    selected = select_task(workspace, shape["paths"], binding)
    result = {**shape, **selected}
    if result["gate"]:
        tg = result["gate"]
        result["session_dir"] = own_session_directory(workspace)
        result["artifacts"] = {name: g["path"] if (g := _artifact_for(tg, name, workspace)) else None for name in ("investigate-gate", "junior-senior-gate", "artifacts-posted-gate", "review-gate", "test-gate")}
        result["task"] = task_identity(tg["data"])
        result["tier"] = task_tier(tg["data"], shape["paths"], command)
    return result


TIER_ORDER = {"A": 0, "B": 1, "C": 2}


def _git_lines(repo: str, *args: str) -> Optional[list]:
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


def task_tier(gate: dict, paths: list, command: str = "") -> dict:
    """Effective review tier for this mutation (#1086): the higher of the gate's
    declared `tier` and the floor bin/review-risk.py computes for the targets.

    A target the shape analysis records as a directory or the repository
    toplevel (tree-wide commands: rm -r, cp -r, git apply/merge/pull/reset,
    scripts) is classified by the tracked files under it plus a probe path
    inside it, so `rm -rf hooks/bash` is C wherever hooks/bash holds Tier C
    files. A lone `git commit` is classified by the staged and modified files
    it can record. A declared lower tier never wins; a missing classifier,
    policy, repo_root or git listing fails closed to C."""
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
        # A lone commit records only staged/modified files: its other operands
        # (message words such as "docs: a/b") are not targets. Only when the
        # repository itself is a target, so the staged set is what gets classified.
        lone_commit = _lone_git_commit(command) and any(os.path.realpath(p) == repo_root for p in paths)
        for p in paths:
            rp = os.path.realpath(p)
            if lone_commit and rp != repo_root:
                continue
            if not (rp == repo_root or rp.startswith(repo_root + os.sep)):
                raise ValueError("target outside the gate's repo_root")
            r = "" if rp == repo_root else os.path.relpath(rp, repo_root).replace(os.sep, "/")
            if r == "" and lone_commit:
                files = (_git_lines(repo_root, "diff", "--cached", "--name-only", "-z") or []) + \
                        (_git_lines(repo_root, "diff", "--name-only", "-z") or [])
                rel.extend(files or ["(empty commit)"])
            elif r == "" or os.path.isdir(rp):
                files = _git_lines(repo_root, "ls-files", "-z", "--", r or ".")
                if files is None:
                    raise ValueError("cannot list files under " + (r or "the repository"))
                rel.extend(files + [(r + "/" if r else "") + "__any__"])
            else:
                rel.append(r)
        verdict = module.classify(policy, sorted(set(rel)))
        floor, reasons = verdict["computed_tier"], [x for x in verdict["reasons"] if x.startswith(verdict["computed_tier"])]
    except Exception as exc:
        floor, reasons = "C", [f"C:{exc}; failing closed" if isinstance(exc, ValueError)
                               else f"C:review-risk classifier unavailable ({type(exc).__name__}); failing closed"]
    effective = declared if declared and TIER_ORDER[declared] > TIER_ORDER[floor] else floor
    return {"effective": effective, "declared": declared, "floor": floor, "reasons": reasons[:6]}


def _load(path: str) -> Optional[dict]:
    try:
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            data = json.load(f)
        return {"path": path, "data": data} if isinstance(data, dict) else None
    except Exception:
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
