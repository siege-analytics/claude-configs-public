#!/usr/bin/env python3
"""Resolve gate signal files — shared by all hooks.

Supports both legacy singleton (<gate-name>.json) and repo-scoped
(<gate-name>-<slug>.json) signal files. Gate name defaults to
"think-gate" for backward compatibility; use --gate-name to resolve
other gate types (investigate-gate, junior-senior-gate, etc.).

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


def find_gate_for_repo(
    workspace: str,
    repo_root: str,
    gate_name: str = "think-gate",
    env_override: str = "",
) -> Optional[dict]:
    """Find a gate signal file for a specific repo.

    Search order:
    1. env_override path (if set and file exists)
    2. <gate-name>-<slug>.json in workspace (repo-scoped)
    3. <gate-name>.json in workspace (legacy singleton, only if
       repo_root matches or is absent in the file)
    4. .<gate-name>.json in repo_root (Claude Code convention)
    """
    if env_override and os.path.isfile(env_override):
        return _load(env_override)

    slug = repo_slug(repo_root)
    scoped = os.path.join(workspace, f"{gate_name}-{slug}.json")
    if os.path.isfile(scoped):
        return _load(scoped)

    legacy = os.path.join(workspace, f"{gate_name}.json")
    if os.path.isfile(legacy):
        loaded = _load(legacy)
        if loaded:
            gate_repo = loaded["data"].get("repo_root", "")
            if not gate_repo or os.path.basename(gate_repo.rstrip("/")) == os.path.basename(repo_root.rstrip("/")):
                return loaded
        return None

    local = os.path.join(repo_root, f".{gate_name}.json")
    if os.path.isfile(local):
        return _load(local)

    return None


def find_think_gate_for_repo(workspace: str, repo_root: str, env_override: str = "") -> Optional[dict]:
    return find_gate_for_repo(workspace, repo_root, "think-gate", env_override)


def find_all_gates(workspace: str, gate_name: str = "think-gate") -> "list[dict]":
    """Find all gate signal files of a given type in the workspace."""
    results = []
    for path in sorted(glob.glob(os.path.join(workspace, f"{gate_name}*.json"))):
        loaded = _load(path)
        if loaded:
            results.append(loaded)
    return results


def find_all_think_gates(workspace: str) -> "list[dict]":
    return find_all_gates(workspace, "think-gate")


def resolve_many(
    workspace: str, repo_root: str, gate_names: "list[str]"
) -> "dict[str, Optional[str]]":
    """Resolve multiple gate types at once, returning a name-to-path map."""
    result: dict[str, Optional[str]] = {}
    for name in gate_names:
        found = find_gate_for_repo(workspace, repo_root, name)
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
        result = resolve_many(args.workspace, args.repo_root, names)
        print(json.dumps(result))
    elif args.all:
        results = find_all_gates(args.workspace, args.gate_name)
        print(json.dumps(results))
    elif args.repo_root:
        result = find_gate_for_repo(
            args.workspace, args.repo_root, args.gate_name, args.env_override,
        )
        print(json.dumps(result))
    else:
        print(json.dumps(None))


if __name__ == "__main__":
    main()
