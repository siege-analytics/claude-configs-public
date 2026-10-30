#!/usr/bin/env python3
"""Wire the blocking enforcement layer into an already-deployed CA workspace.

Run after install-hooks.sh to merge the prompt wrapper into the selected
settings file. Normal Craft installation selects .claude/craft-settings.json;
the legacy default remains .claude/settings.json for existing direct callers.
This verifies neither SDK discovery nor actual backend callback delivery.

Standing-order watchdog automations remain opt-in via
--include-standing-order-automations. SchedulerTick prompt automations create
sessions and SessionStatusChange audits can self-trigger if enabled.

The settings merge is idempotent. Optional automation registration is also
idempotent (replace-by-identity, never append duplicates) and preserves every
entry the workspace already has, including a consumer's own skills-sync
automation. The automations write is backed up and restored on a parse failure
so a bad merge cannot corrupt the file that drives harmonisation.

Usage:
    python3 bin/wire-enforcement.py --workspace <path>
    python3 bin/wire-enforcement.py --workspace <path> --settings-file <policy-path>
    python3 bin/wire-enforcement.py --workspace <path> --dist <dist-dir>
    python3 bin/wire-enforcement.py --workspace <path> --include-standing-order-automations

Exit codes: 0 wired, 1 error, 2 bad invocation.

Refs: #96, #409, #416, #572.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def merge_ca_enforcement_settings(src: Path, dst: Path, *, workspace_root: Path | None = None) -> None:
    """Merge the CA enforcement wrapper into the selected settings file.

    Adds the ca-enforcement-gate.sh UserPromptSubmit entry. Preserves all
    operator-owned settings. Idempotent: an existing ca-enforcement-gate entry
    is removed before the fresh one is appended, so re-runs do not stack it.
    """
    if not dst.exists():
        raise SystemExit(
            f"ERROR: {dst} not found -- run install-hooks.sh (or bin/install.sh) first"
        )
    try:
        existing = json.loads(dst.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: {dst} is not valid JSON: {e}")
    if not isinstance(existing, dict):
        raise SystemExit(f"ERROR: {dst} top-level is not a JSON object; refusing to merge")
    if not isinstance(existing.get("hooks", {}), dict):
        raise SystemExit(f"ERROR: {dst} 'hooks' is not a JSON object; refusing to merge")

    generated = json.loads(src.read_text())
    if not isinstance(existing.get("env", {}), dict):
        raise SystemExit(f"ERROR: {dst} 'env' is not a JSON object; refusing to merge")
    generated_environment = generated.get("env", {})
    if not isinstance(generated_environment, dict):
        raise SystemExit(f"ERROR: {src} 'env' is not a JSON object; refusing to merge")
    if generated_environment.get("CLAUDE_CA_ENFORCE") == "1":
        existing.setdefault("env", {})["CLAUDE_CA_ENFORCE"] = "1"
    existing.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    if not isinstance(existing["hooks"].get("UserPromptSubmit"), list):
        raise SystemExit(f"ERROR: {dst} hooks.UserPromptSubmit is not a list; refusing to merge")

    # Resolve the path placeholder to the workspace hooks root.
    ws_root = workspace_root if workspace_root is not None else dst.parent.parent
    gen_hooks = generated.get("hooks", {}).get("UserPromptSubmit", [])
    for entry in gen_hooks:
        for hook in entry.get("hooks", []):
            if "command" in hook:
                resolved = hook["command"].replace("/path/to", str(ws_root))
                hook["command"] = shlex.quote(resolved) if resolved.endswith("ca-enforcement-gate.sh") else resolved

    # Retirement requires the exact generated command identity, not a basename
    # substring that could belong to an unrelated operator hook.
    managed_commands = {
        tuple(shlex.split(hook["command"]))
        for group in gen_hooks for hook in group.get("hooks", [])
        if hook.get("type") == "command" and isinstance(hook.get("command"), str)
    }

    def owned_wrapper(hook: object) -> bool:
        if not isinstance(hook, dict) or hook.get("type") != "command" or not isinstance(hook.get("command"), str):
            return False
        try:
            tokens = tuple(shlex.split(hook["command"]))
        except ValueError:
            tokens = ()  # An unparseable operator command establishes no ownership.
        return tokens in managed_commands

    retained = []
    for group in existing["hooks"]["UserPromptSubmit"]:
        if isinstance(group, dict) and isinstance(group.get("hooks"), list):
            original = group["hooks"]
            group["hooks"] = [hook for hook in original if not owned_wrapper(hook)]
            if original and not group["hooks"]:
                continue
        retained.append(group)
    existing["hooks"]["UserPromptSubmit"] = retained + gen_hooks

    dst.write_text(json.dumps(existing, indent=2) + "\n")
    print(f"  Merged CA enforcement wrapper into {dst}")


def register_ca_automations(snippet: Path, dst: Path) -> None:
    """Merge the CA enforcement automations into a workspace automations.json.

    Idempotent by (event, name): a re-run replaces the matching entry rather
    than appending a duplicate. Every other entry (operator automations, a
    consumer's own skills-sync job) is preserved. A single rolling backup
    (automations.json.bak) is written and restored if the merged result does
    not parse.
    """
    if not snippet.exists():
        print(f"  [warn] {snippet} not found; skipping automation registration")
        return

    try:
        existing = (
            json.loads(dst.read_text())
            if dst.exists()
            else {"version": 2, "automations": {}}
        )
    except json.JSONDecodeError:
        raise SystemExit(f"ERROR: {dst} is not valid JSON; refusing to merge")

    # Validate the shape up front, before writing anything, so an odd-but-valid
    # JSON file produces a clear refusal instead of a half-merged workspace and
    # a raw traceback. A consumer's automations.json is load-bearing.
    if not isinstance(existing, dict):
        raise SystemExit(f"ERROR: {dst} top-level is not a JSON object; refusing to merge")
    existing.setdefault("version", 2)
    existing.setdefault("automations", {})
    if not isinstance(existing["automations"], dict):
        raise SystemExit(f"ERROR: {dst} 'automations' is not a JSON object; refusing to merge")
    for event, bucket in existing["automations"].items():
        if not isinstance(bucket, list):
            raise SystemExit(f"ERROR: {dst} automations['{event}'] is not a list; refusing to merge")

    # Single rolling backup (bounded): the recurring harmonise job runs often,
    # so a per-run timestamped backup would grow without limit.
    backup = None
    if dst.exists():
        backup = dst.with_name("automations.json.bak")
        backup.write_text(dst.read_text())

    generated = json.loads(snippet.read_text())

    added = 0
    for event, entries in generated.get("automations", {}).items():
        bucket = existing["automations"].setdefault(event, [])
        for entry in entries:
            name = entry.get("name")
            # Drop only matching-name dict entries; preserve every other entry,
            # including non-dict entries we do not understand.
            bucket = [
                e for e in bucket
                if not (isinstance(e, dict) and e.get("name") == name)
            ]
            bucket.append(entry)
            existing["automations"][event] = bucket
            added += 1

    merged = json.dumps(existing, indent=2) + "\n"
    try:
        json.loads(merged)
    except json.JSONDecodeError:
        if backup is not None:
            dst.write_text(backup.read_text())
        raise SystemExit("ERROR: merged automations.json did not parse; restored backup")

    dst.write_text(merged)
    print(f"  Registered {added} CA automation(s) into {dst}")


def main() -> int:
    if "--selected" in sys.argv[1:]:
        import selected_registration
        return selected_registration.main(["wire", *sys.argv[1:]])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True, help="Craft Agent workspace path")
    parser.add_argument("--settings-file", type=Path, help="Explicit managed settings destination (default: workspace/.claude/settings.json)")
    parser.add_argument("--dist", type=Path, default=REPO_ROOT / "dist", help="Build dist directory (default: %(default)s)")
    parser.add_argument(
        "--include-standing-order-automations",
        action="store_true",
        help="Opt in to registering standing-order SchedulerTick/SessionStatusChange prompt automations",
    )
    args = parser.parse_args()

    ws = args.workspace.expanduser()
    if not ws.is_dir():
        print(f"ERROR: workspace not found: {ws}", file=sys.stderr)
        return 2

    settings_src = args.dist / "craft-agent" / "settings-enforcement.json"
    if not settings_src.exists():
        print(
            f"ERROR: {settings_src} not found -- run the build (bin/build.py) before wiring",
            file=sys.stderr,
        )
        return 1

    merge_ca_enforcement_settings(settings_src, args.settings_file.expanduser() if args.settings_file else ws / ".claude" / "settings.json", workspace_root=ws)
    if args.include_standing_order_automations:
        register_ca_automations(REPO_ROOT / "craft-agent" / "automations-snippet.json", ws / "automations.json")
    else:
        print("  Skipped standing-order automations (opt-in; pass --include-standing-order-automations to register)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
