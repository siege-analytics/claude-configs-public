#!/usr/bin/env python3
"""Regression tests for wire-enforcement automation opt-in behavior."""

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WIRE = ROOT / "bin" / "wire-enforcement.py"


def make_workspace(base: Path) -> Path:
    ws = base / "workspace"
    (ws / ".claude").mkdir(parents=True)
    (ws / ".claude" / "settings.json").write_text(json.dumps({"hooks": {"UserPromptSubmit": []}}) + "\n")
    (ws / "automations.json").write_text(json.dumps({"version": 2, "automations": {}}) + "\n")
    return ws


def make_dist(base: Path) -> Path:
    dist = base / "dist" / "craft-agent"
    dist.mkdir(parents=True)
    (dist / "settings-enforcement.json").write_text(json.dumps({
        "hooks": {
            "UserPromptSubmit": [
                {"hooks": [{"type": "command", "command": "/path/to/hooks/ca-enforcement-gate.sh"}]}
            ]
        }
    }) + "\n")
    return base / "dist"


def automation_names(ws: Path) -> list[str]:
    data = json.loads((ws / "automations.json").read_text())
    names = []
    for entries in data.get("automations", {}).values():
        names.extend(entry.get("name", "") for entry in entries if isinstance(entry, dict))
    return names


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["python3", str(WIRE), *args], text=True, capture_output=True)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        ws = make_workspace(base)
        dist = make_dist(base)

        r = run("--workspace", str(ws), "--dist", str(dist))
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
        assert "Skipped standing-order automations" in r.stdout
        assert "Standing-order watchdog" not in automation_names(ws)
        assert "Standing-order completion audit" not in automation_names(ws)

        r = run(
            "--workspace", str(ws),
            "--dist", str(dist),
            "--include-standing-order-automations",
        )
        assert r.returncode == 0, (r.returncode, r.stdout, r.stderr)
        names = automation_names(ws)
        assert "Standing-order watchdog" in names
        assert "Standing-order completion audit" in names

    print("wire_enforcement_automations_test: PASS")


if __name__ == "__main__":
    main()
