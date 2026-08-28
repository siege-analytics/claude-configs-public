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
    for name in ("CRAFT_AGENT_SESSION_ID", "CLAUDE_SESSION_ID", "SESSION_ID"):
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
    for name in ("CLAUDE_SIGNAL_DIR", "CRAFT_AGENT_SIGNAL_DIR", "CRAFT_AGENT_SESSION_DIR", "CLAUDE_SESSION_DIR"):
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


def find_gate_for_repo(
    workspace: str,
    repo_root: str,
    gate_name: str = "think-gate",
    env_override: str = "",
    session_id: str = "",
) -> Optional[dict]:
    """Find a gate signal file for a specific repo.

    Search order:
    1. env_override path (if set and file exists)
    2. session-scoped <gate-name>-<slug>.json
    3. session-scoped <gate-name>.json
    4. <gate-name>-<slug>.json in workspace (repo-scoped)
    5. .<gate-name>.json in repo_root (Claude Code convention)
    6. <gate-name>.json in workspace (legacy singleton, only if
       repo_root matches or is absent in the file)
    """
    if env_override and os.path.isfile(env_override):
        return _load(env_override)

    slug = repo_slug(repo_root)
    for session_dir in session_dirs(workspace, session_id):
        session_repo_scoped = os.path.join(session_dir, f"{gate_name}-{slug}.json")
        if os.path.isfile(session_repo_scoped):
            return _load(session_repo_scoped)
        session_scoped = os.path.join(session_dir, f"{gate_name}.json")
        if os.path.isfile(session_scoped):
            return _load(session_scoped)

    scoped = os.path.join(workspace, f"{gate_name}-{slug}.json")
    if os.path.isfile(scoped):
        return _load(scoped)

    local = os.path.join(repo_root, f".{gate_name}.json")
    if os.path.isfile(local):
        return _load(local)

    legacy = os.path.join(workspace, f"{gate_name}.json")
    if os.path.isfile(legacy):
        loaded = _load(legacy)
        if loaded:
            gate_repo = loaded["data"].get("repo_root", "")
            if not gate_repo or os.path.basename(gate_repo.rstrip("/")) == os.path.basename(repo_root.rstrip("/")):
                return loaded
        return None

    return None


def find_think_gate_for_repo(workspace: str, repo_root: str, env_override: str = "") -> Optional[dict]:
    return find_gate_for_repo(workspace, repo_root, "think-gate", env_override)


def find_all_gates(workspace: str, gate_name: str = "think-gate", session_id: str = "") -> "list[dict]":
    """Find all gate signal files, with current-session files first."""
    results = []
    seen = set()
    for session_dir in session_dirs(workspace, session_id):
        for path in sorted(glob.glob(os.path.join(session_dir, f"{gate_name}*.json"))):
            loaded = _load(path)
            if loaded and path not in seen:
                results.append(loaded)
                seen.add(path)
    for path in sorted(glob.glob(os.path.join(workspace, f"{gate_name}*.json"))):
        loaded = _load(path)
        if loaded and path not in seen:
            results.append(loaded)
            seen.add(path)
    return results


def find_all_think_gates(workspace: str) -> "list[dict]":
    return find_all_gates(workspace, "think-gate")


def resolve_many(
    workspace: str, repo_root: str, gate_names: "list[str]", session_id: str = ""
) -> "dict[str, Optional[str]]":
    """Resolve multiple gate types at once, returning a name-to-path map."""
    result: dict[str, Optional[str]] = {}
    for name in gate_names:
        found = find_gate_for_repo(workspace, repo_root, name, session_id=session_id)
        result[name] = found["path"] if found else None
    return result


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
    parser.add_argument(
        "--resolve-many", default="",
        help="Comma-separated gate names; returns name-to-path map",
    )
    args = parser.parse_args()

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
