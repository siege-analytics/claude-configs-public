#!/usr/bin/env python3
"""Check whether deployed workspace hooks match this repo's hooks."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hook_files(root: Path) -> dict[str, str]:
    hooks = root / "hooks"
    result: dict[str, str] = {}
    if not hooks.is_dir():
        return result
    for p in sorted(hooks.rglob("*")):
        if p.is_file():
            result[str(p.relative_to(hooks))] = sha256(p)
    return result


def git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-root", type=Path, required=True)
    ap.add_argument("--workspace", type=Path, required=True)
    ap.add_argument("--scope", choices=("hooks",), default="hooks")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    repo = args.repo_root.expanduser().resolve()
    ws = args.workspace.expanduser().resolve()
    errors: list[dict[str, str]] = []

    if not (repo / "hooks").is_dir():
        print(f"ERROR: repo hooks/ not found at {repo / 'hooks'}", file=sys.stderr)
        return 2
    if not ws.is_dir():
        print(f"ERROR: workspace not found: {ws}", file=sys.stderr)
        return 2

    repo_hooks = hook_files(repo)
    ws_hooks = hook_files(ws)
    if not ws_hooks:
        errors.append({"type": "missing-hooks", "path": "hooks/", "detail": "workspace hooks directory missing or empty"})

    for rel, digest in repo_hooks.items():
        if rel not in ws_hooks:
            errors.append({"type": "missing", "path": f"hooks/{rel}", "detail": "missing from workspace"})
        elif ws_hooks[rel] != digest:
            errors.append({"type": "hash-different", "path": f"hooks/{rel}", "detail": "workspace content differs from repo"})
    for rel in sorted(set(ws_hooks) - set(repo_hooks)):
        errors.append({"type": "extra", "path": f"hooks/{rel}", "detail": "extra deployed hook not present in repo"})

    stamp_path = ws / "deploy-stamp.json"
    head = git_head(repo)
    stamp = None
    if not stamp_path.is_file():
        errors.append({"type": "missing-stamp", "path": "deploy-stamp.json", "detail": "deploy stamp missing"})
    else:
        try:
            stamp = json.loads(stamp_path.read_text())
        except Exception as exc:
            errors.append({"type": "bad-stamp", "path": "deploy-stamp.json", "detail": f"invalid JSON: {exc}"})
        else:
            for field in ("commit", "timestamp", "repo_root"):
                if not str(stamp.get(field, "")).strip():
                    errors.append({"type": "stamp-incomplete", "path": "deploy-stamp.json", "detail": f"missing required field: {field}"})
            commit = str(stamp.get("commit", ""))
            if commit and commit != head:
                errors.append({"type": "stamp-mismatch", "path": "deploy-stamp.json", "detail": f"stamp commit {commit or '<empty>'} != repo HEAD {head}"})

    payload = {
        "ok": not errors,
        "repo_root": str(repo),
        "workspace": str(ws),
        "repo_head": head,
        "deployed_commit": (stamp or {}).get("commit") if isinstance(stamp, dict) else None,
        "repo_hook_count": len(repo_hooks),
        "workspace_hook_count": len(ws_hooks),
        "errors": errors,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if errors:
            print("DEPLOY DRIFT detected")
            print(f"repo:      {repo}")
            print(f"workspace: {ws}")
            print(f"repo HEAD: {head}")
            if args.verbose:
                for e in errors:
                    print(f"  - {e['type']}: {e['path']} ({e['detail']})")
            else:
                print(f"errors: {len(errors)} (rerun with --verbose for per-file detail)")
        else:
            print("deploy drift: clean")
            print(f"repo HEAD: {head}")
            print(f"hooks compared: {len(repo_hooks)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
