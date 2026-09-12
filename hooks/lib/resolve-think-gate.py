#!/usr/bin/env python3
"""Resolve gate signal files — shared by all hooks.

Supports session-scoped (<workspace>/sessions/<session-id>/<gate-name>.json),
repo-scoped (<gate-name>-<slug>.json), and legacy singleton
(<gate-name>.json) signal files. Gate name defaults to "think-gate" for
backward compatibility; use --gate-name to resolve other gate types
(investigate-gate, junior-senior-gate, etc.).

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
import sys
import glob
import subprocess
from typing import Optional


def repo_slug(repo_root: str) -> str:
    """Derive a filesystem-safe slug from a repo root path."""
    base = os.path.basename(repo_root.rstrip("/"))
    return re.sub(r"[^a-zA-Z0-9_-]", "_", base)


def _safe_session_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", value.strip())


def _find_session_value(obj) -> str:
    """Best-effort recursive extraction from hook input JSON."""
    if isinstance(obj, dict):
        for key in ("sessionId", "session_id", "sessionID", "id"):
            value = obj.get(key)
            if isinstance(value, str) and value.strip():
                return value
        for key in ("session", "conversation", "metadata"):
            value = _find_session_value(obj.get(key))
            if value:
                return value
        transcript = obj.get("transcript_path") or obj.get("transcriptPath")
        if isinstance(transcript, str):
            match = re.search(r"/sessions/([^/]+)/", transcript)
            if match:
                return match.group(1)
    return ""


def session_id_from_env() -> str:
    """Return the current session id from known runtime env vars or hook JSON."""
    # Craft Agents sets CRAFT_SESSION_ID (verified via ps -eE on the running
    # server). The CRAFT_AGENT_ prefix was aspirational and is NEVER set at
    # runtime (#697). Kept for backward compat if a caller ever exports it,
    # but the CRAFT_ prefix is checked first because that is what Craft
    # actually sets.
    for name in ("CRAFT_SESSION_ID", "CRAFT_AGENT_SESSION_ID", "CLAUDE_SESSION_ID", "SESSION_ID"):
        value = os.environ.get(name, "").strip()
        if value:
            return _safe_session_id(value)
    hook_input = os.environ.get("CCP_HOOK_INPUT_JSON", "").strip()
    if hook_input:
        try:
            value = _find_session_value(json.loads(hook_input))
            if value:
                return _safe_session_id(value)
        except Exception:
            return ""
    return ""


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


def _ticket_slug(ref: str) -> str:
    if not ref or "#" not in ref:
        return ref or ""
    return "#" + ref.split("#")[-1]


def _gate_matches_ticket(loaded: dict, current_ticket: str, *, require_explicit: bool = False) -> bool:
    """Return True when a gate is usable for the current task/ticket."""
    if not current_ticket:
        return not require_explicit
    data = loaded.get("data", {})
    values = [str(data.get(k, "")).strip() for k in ("ticket", "task")]
    values = [v for v in values if v]
    if not values:
        return False if require_explicit else True
    slug = _ticket_slug(current_ticket)
    for value in values:
        if value == current_ticket or (slug and slug in value):
            return True
    return False


def find_gate_for_repo(
    workspace: str,
    repo_root: str,
    gate_name: str = "think-gate",
    env_override: str = "",
    session_id: str = "",
) -> Optional[dict]:
    """Find a gate signal file for a specific repo.

    Search order:
    1. env_override path (if set, file exists, and matches repo/session)
    2. session-scoped <gate-name>-<slug>.json
    3. session-scoped <gate-name>.json
    4. <gate-name>-<slug>.json in workspace
    5. .<gate-name>.json in repo_root, only if repo/session metadata matches
    6. <gate-name>.json in workspace, only if repo/session metadata matches
    """
    sid = session_id or session_id_from_env()
    if env_override and os.path.isfile(env_override):
        loaded = _load(env_override)
        if loaded and _gate_matches_scope(loaded, repo_root, sid):
            return loaded
        return None

    slug = repo_slug(repo_root)
    for session_dir in session_dirs(workspace, sid):
        session_repo_scoped = os.path.join(session_dir, f"{gate_name}-{slug}.json")
        if os.path.isfile(session_repo_scoped):
            loaded = _load(session_repo_scoped)
            if loaded and _gate_matches_scope(loaded, repo_root, sid):
                return loaded
        session_scoped = os.path.join(session_dir, f"{gate_name}.json")
        if os.path.isfile(session_scoped):
            loaded = _load(session_scoped)
            if loaded and _gate_matches_scope(loaded, repo_root, sid):
                return loaded

    scoped = os.path.join(workspace, f"{gate_name}-{slug}.json")
    if os.path.isfile(scoped):
        loaded = _load(scoped)
        if loaded and _gate_matches_scope(loaded, repo_root, sid):
            return loaded
        return None

    local = os.path.join(repo_root, f".{gate_name}.json")
    if os.path.isfile(local):
        loaded = _load(local)
        if loaded and _gate_matches_scope(loaded, repo_root, sid):
            return loaded
        return None

    legacy = os.path.join(workspace, f"{gate_name}.json")
    if os.path.isfile(legacy):
        loaded = _load(legacy)
        # #873 P2 (defect D3): the workspace-root singleton is shared by every
        # session, task, and repo. _gate_matches_scope only REJECTS on a
        # positive mismatch, so a generic singleton with no repo_root applied to
        # any repo whenever the session id was unknown -- the cross-project bleed
        # that governed an unrelated action in the 2026-09-12 incident. Fail
        # safe: when we cannot identify the session, the singleton must carry an
        # explicit repo_root that matches this repo; a no-repo generic gate does
        # not bind. With a known session the prior scope check is sufficient.
        if loaded and _gate_matches_scope(loaded, repo_root, sid):
            if not sid:
                gate_repo = str(loaded.get("data", {}).get("repo_root", "")).strip()
                if not (gate_repo and _same_repo(gate_repo, repo_root)):
                    return None
            return loaded
        return None

    return None


def find_think_gate_for_repo(workspace: str, repo_root: str, env_override: str = "") -> Optional[dict]:
    return find_gate_for_repo(workspace, repo_root, "think-gate", env_override)


def find_all_gates(workspace: str, gate_name: str = "think-gate", session_id: str = "") -> "list[dict]":
    """Find all gate signal files, with current-session files first.

    Workspace-root (non-session-scoped) files are included only when they
    plausibly belong to the calling session: the calling session id is
    unknown (can't disambiguate; preserves legacy single-tenant behavior),
    the file's own recorded "session" field matches, or the file records
    no session at all (fully generic legacy singleton). A workspace-root
    file stamped with a DIFFERENT session's id is excluded -- otherwise a
    brand-new session with no gate of its own inherits whichever foreign
    session's stale, non-terminal think-gate happens to sort first
    alphabetically, and gets gated on a ticket it has never touched.
    """
    sid = session_id or session_id_from_env()
    results = []
    seen = set()
    for session_dir in session_dirs(workspace, sid):
        for path in sorted(glob.glob(os.path.join(session_dir, f"{gate_name}*.json"))):
            loaded = _load(path)
            if loaded and path not in seen:
                results.append(loaded)
                seen.add(path)
    for path in sorted(glob.glob(os.path.join(workspace, f"{gate_name}*.json"))):
        if path in seen:
            continue
        loaded = _load(path)
        if not loaded:
            continue
        file_session = loaded["data"].get("session", "")
        if sid and file_session and file_session != sid:
            continue
        results.append(loaded)
        seen.add(path)
    return results


def find_all_think_gates(workspace: str) -> "list[dict]":
    return find_all_gates(workspace, "think-gate")


def resolve_many(
    workspace: str, repo_root: str, gate_names: "list[str]", session_id: str = ""
) -> "dict[str, Optional[str]]":
    """Resolve multiple gate types at once, returning a name-to-path map.

    Artifact gates are resolved relative to the current think-gate ticket/task
    when one exists. This prevents stale session-scoped artifacts from an older
    task in the same long-lived coordinator session from shadowing current
    repo/workspace-scoped artifacts.
    """
    result: dict[str, Optional[str]] = {}
    think_gate = find_gate_for_repo(workspace, repo_root, "think-gate", session_id=session_id)
    current_ticket = ""
    if think_gate:
        td = think_gate.get("data", {})
        current_ticket = str(td.get("ticket") or td.get("task") or "").strip()
    for name in gate_names:
        found = find_gate_for_repo(workspace, repo_root, name, session_id=session_id)
        sid = session_id or session_id_from_env()
        if found and (not _artifact_matches_strict_scope(found, repo_root, sid) or not _gate_matches_ticket(found, current_ticket, require_explicit=True)):
            found = None
        if not found and current_ticket:
            # Re-scan lower-priority candidates for the first scope-valid gate
            # matching the current task. find_gate_for_repo may have skipped
            # them because a stale same-session artifact appeared first.
            for candidate in _candidate_paths(workspace, repo_root, name, sid):
                loaded = _load(candidate)
                if loaded and _artifact_matches_strict_scope(loaded, repo_root, sid) and _gate_matches_ticket(loaded, current_ticket, require_explicit=True):
                    found = loaded
                    break
        result[name] = found["path"] if found else None
    return result


def _candidate_paths(workspace: str, repo_root: str, gate_name: str, session_id: str = "") -> "list[str]":
    """Return gate candidate paths in resolver priority order."""
    slug = repo_slug(repo_root)
    paths: list[str] = []
    for session_dir in session_dirs(workspace, session_id):
        paths.append(os.path.join(session_dir, f"{gate_name}-{slug}.json"))
        paths.append(os.path.join(session_dir, f"{gate_name}.json"))
    paths.append(os.path.join(workspace, f"{gate_name}-{slug}.json"))
    paths.append(os.path.join(repo_root, f".{gate_name}.json"))
    paths.append(os.path.join(workspace, f"{gate_name}.json"))
    out: list[str] = []
    seen = set()
    for path in paths:
        if path not in seen and os.path.isfile(path):
            out.append(path)
            seen.add(path)
    return out


def _load(path: str) -> Optional[dict]:
    try:
        with open(path) as f:
            data = json.load(f)
        return {"path": path, "data": data}
    except Exception:
        return None


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--env-override", default="")
    parser.add_argument("--gate-name", default="think-gate")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--session-known", action="store_true", help="Return 1 if a current session id is resolvable, else 0")
    parser.add_argument("--project", action="store_true", help="Print the project slug for --repo-root (or 'umbrella')")
    parser.add_argument(
        "--resolve-many", default="",
        help="Comma-separated gate names; returns name-to-path map",
    )
    args = parser.parse_args()

    if args.session_known:
        print("1" if (args.session_id or session_id_from_env()) else "0")
        return

    if args.project:
        print(resolve_project(args.repo_root, args.workspace))
        return

    if args.resolve_many:
        if not args.repo_root:
            print(json.dumps({}))
            return
        names = [n.strip() for n in args.resolve_many.split(",") if n.strip()]
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
