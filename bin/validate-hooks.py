#!/usr/bin/env python3
"""Validate hook installation for a settings-snippet.json.

Usage:
    # Validate the repo's own hooks (default)
    python3 bin/validate-hooks.py

    # Validate a consumer package directory (dist/claude-code/, dist/craft-agent/)
    python3 bin/validate-hooks.py dist/claude-code/

Checks:
    1. Every hook path in settings JSON resolves to an existing, executable file
    2. Every .sh hook passes bash -n (syntax check)
    3. Lib helpers referenced by hooks exist
    4. Hook scripts on disk but not in settings JSON are reported as warnings
    5. Minimum hook count assertion (catches silent truncation)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PATH_TOKEN = "/path/to/claude-configs-public"
MIN_HOOK_COUNT = 20


def load_settings(package_dir: Path | None) -> tuple[dict, Path]:
    if package_dir:
        candidates = [
            package_dir / "hooks" / "settings-snippet.json",
            package_dir / "settings-snippet.json",
        ]
        for c in candidates:
            if c.exists():
                return json.loads(c.read_text()), package_dir
        print(f"FAIL: No settings-snippet.json found in {package_dir}")
        sys.exit(1)
    else:
        snippet = REPO_ROOT / "hooks" / "settings-snippet.json"
        return json.loads(snippet.read_text()), REPO_ROOT


def resolve_path(hook_path: str, base: Path) -> Path:
    if PATH_TOKEN in hook_path:
        return base / hook_path.replace(PATH_TOKEN + "/", "")
    return Path(hook_path)


def extract_hook_paths(settings: dict) -> list[str]:
    paths = []
    hooks_section = settings.get("hooks", {})
    for event_hooks in hooks_section.values():
        if not isinstance(event_hooks, list):
            continue
        for group in event_hooks:
            for hook in group.get("hooks", []):
                cmd = hook.get("command", "")
                if cmd:
                    paths.append(cmd)
    return paths


def find_hook_scripts(base: Path) -> set[Path]:
    hooks_dir = base / "hooks"
    if not hooks_dir.exists():
        return set()
    scripts = set()
    for f in hooks_dir.rglob("*.sh"):
        rel = f.relative_to(base)
        if "_test" in str(rel) or " " in f.name:
            continue
        scripts.add(f)
    return scripts


def main():
    package_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    settings, base = load_settings(package_dir)

    hook_paths = extract_hook_paths(settings)
    errors = []
    warnings = []
    referenced_files: set[Path] = set()

    if len(hook_paths) < MIN_HOOK_COUNT:
        errors.append(
            f"Only {len(hook_paths)} hooks in settings (minimum {MIN_HOOK_COUNT}). "
            f"Possible silent truncation."
        )

    for raw_path in hook_paths:
        resolved = resolve_path(raw_path, base)
        referenced_files.add(resolved.resolve())

        if not resolved.exists():
            errors.append(f"Missing: {raw_path} -> {resolved}")
            continue

        if not os.access(resolved, os.X_OK):
            errors.append(f"Not executable: {resolved}")

        if resolved.suffix == ".sh":
            result = subprocess.run(
                ["bash", "-n", str(resolved)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"Syntax error: {resolved}\n  {result.stderr.strip()}")

    lib_dir = base / "hooks" / "lib"
    if lib_dir.exists():
        for lib_file in lib_dir.iterdir():
            if lib_file.is_file() and not lib_file.name.startswith("."):
                if not os.access(lib_file, os.R_OK):
                    errors.append(f"Lib helper not readable: {lib_file}")

    on_disk = find_hook_scripts(base)
    for script in sorted(on_disk):
        if script.resolve() not in referenced_files:
            warnings.append(f"Unreferenced hook: {script.relative_to(base)}")

    print(f"Validated {len(hook_paths)} hook paths in {base}")
    if warnings:
        print(f"\nWarnings ({len(warnings)}):")
        for w in warnings:
            print(f"  WARN: {w}")
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  FAIL: {e}")
        sys.exit(1)
    else:
        print("All hooks valid.")


if __name__ == "__main__":
    main()
