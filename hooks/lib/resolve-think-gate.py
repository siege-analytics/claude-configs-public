#!/usr/bin/env python3
"""Resolve think-gate signal files — shared by all hooks.

Supports both legacy singleton (think-gate.json) and repo-scoped
(think-gate-<slug>.json) signal files.

Usage:
    # Find think-gate for a specific repo (mutation gate)
    python3 resolve-think-gate.py --workspace /path/to/workspace --repo-root /path/to/repo

    # List all active think-gates (resolver hooks)
    python3 resolve-think-gate.py --workspace /path/to/workspace --all

Output (JSON):
    {"path": "/path/to/think-gate-<slug>.json", "data": {...}}
    or for --all:
    [{"path": "...", "data": {...}}, ...]
    or null / [] if none found.
"""

import json
import os
import re
import sys
import glob


def repo_slug(repo_root: str) -> str:
    """Derive a filesystem-safe slug from a repo root path."""
    base = os.path.basename(repo_root.rstrip("/"))
    return re.sub(r"[^a-zA-Z0-9_-]", "_", base)


def find_think_gate_for_repo(workspace: str, repo_root: str, env_override: str = "") -> dict | None:
    """Find the think-gate signal file for a specific repo.

    Search order:
    1. CLAUDE_THINK_GATE env override (if set)
    2. think-gate-<slug>.json in workspace
    3. think-gate.json in workspace (legacy fallback, only if repo_root matches or is absent)
    4. .think-gate.json in repo_root (Claude Code convention)
    """
    if env_override and os.path.isfile(env_override):
        return _load(env_override)

    slug = repo_slug(repo_root)
    scoped = os.path.join(workspace, f"think-gate-{slug}.json")
    if os.path.isfile(scoped):
        return _load(scoped)

    legacy = os.path.join(workspace, "think-gate.json")
    if os.path.isfile(legacy):
        loaded = _load(legacy)
        if loaded:
            gate_repo = loaded["data"].get("repo_root", "")
            if not gate_repo or os.path.basename(gate_repo.rstrip("/")) == os.path.basename(repo_root.rstrip("/")):
                return loaded
        return None

    local = os.path.join(repo_root, ".think-gate.json")
    if os.path.isfile(local):
        return _load(local)

    return None


def find_all_think_gates(workspace: str) -> list[dict]:
    """Find all think-gate signal files in the workspace."""
    results = []

    for path in sorted(glob.glob(os.path.join(workspace, "think-gate*.json"))):
        loaded = _load(path)
        if loaded:
            results.append(loaded)

    return results


def _load(path: str) -> dict | None:
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
    args = parser.parse_args()

    if args.all:
        results = find_all_think_gates(args.workspace)
        print(json.dumps(results))
    elif args.repo_root:
        result = find_think_gate_for_repo(args.workspace, args.repo_root, args.env_override)
        print(json.dumps(result))
    else:
        print(json.dumps(None))


if __name__ == "__main__":
    main()
