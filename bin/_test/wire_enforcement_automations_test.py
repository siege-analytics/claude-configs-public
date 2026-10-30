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
        "env": {"CLAUDE_CA_ENFORCE": "1", "SOURCE_ONLY": "must-not-copy"},
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
    return subprocess.run(["python3", str(WIRE), *args], text=True, capture_output=True, timeout=30)


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

        legacy_before = (ws / ".claude/settings.json").read_bytes()
        scoped = ws / ".claude/craft-settings.json"
        foreign = {"matcher": "operator", "timeout": 77, "hooks": [
            {"type": "command", "command": "/operator/ca-enforcement-gate.sh", "operator": True},
            {"type": "command", "command": "echo ca-enforcement-gate; true"},
            {"type": "command", "command": "unterminated'"},
        ]}
        scoped.write_text(json.dumps({"env": {"OPERATOR_FLAG": "preserve"}, "hooks": {"UserPromptSubmit": [foreign]}}))
        for _ in range(2):
            r = run("--workspace", str(ws), "--dist", str(dist), "--settings-file", str(scoped))
            assert r.returncode == 0, r.stdout + r.stderr
        assert (ws / ".claude/settings.json").read_bytes() == legacy_before
        assert json.loads(scoped.read_text())["env"] == {"OPERATOR_FLAG": "preserve", "CLAUDE_CA_ENFORCE": "1"}
        entries = json.loads(scoped.read_text())["hooks"]["UserPromptSubmit"]
        assert len(entries) == 2 and entries[0] == foreign, entries
        assert automation_names(ws) == []
        alternate = base / "alternate-policy.json"
        alternate.write_text("{}\n")
        r = run("--workspace", str(ws), "--dist", str(dist), "--settings-file", str(alternate))
        assert r.returncode == 0, r.stdout + r.stderr
        assert str(ws / "hooks/ca-enforcement-gate.sh") in alternate.read_text()
        r = run("--workspace", str(ws), "--settings-file")
        assert r.returncode == 2 and "expected one argument" in r.stderr

        snippet = dist / "craft-agent/settings-enforcement.json"
        generated = json.loads(snippet.read_text())
        canonical = snippet.read_bytes()
        for target_environment, source_environment in (([], {}), ({}, [])):
            alternate.write_text(json.dumps({"env": target_environment}))
            before = alternate.read_bytes()
            bad = dict(generated, env=source_environment)
            snippet.write_text(json.dumps(bad))
            r = run("--workspace", str(ws), "--dist", str(dist), "--settings-file", str(alternate))
            assert r.returncode != 0 and "env" in r.stderr
            assert alternate.read_bytes() == before
        for source_environment in ({"SOURCE_ONLY": "ignore"}, {"CLAUDE_CA_ENFORCE": "0"}):
            alternate.write_text(json.dumps({"env": {"OPERATOR_FLAG": "preserve", "CLAUDE_CA_ENFORCE": "operator-value"}}))
            snippet.write_text(json.dumps(dict(generated, env=source_environment)))
            r = run("--workspace", str(ws), "--dist", str(dist), "--settings-file", str(alternate))
            assert r.returncode == 0, r.stdout + r.stderr
            assert json.loads(alternate.read_text())["env"] == {"OPERATOR_FLAG": "preserve", "CLAUDE_CA_ENFORCE": "operator-value"}
        snippet.write_bytes(canonical)

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
