#!/usr/bin/env python3
"""Real-YAML frontmatter validation and its packaging gates (#1046).

Unit cases run against bin/frontmatter_validation.py with real PyYAML. Gate
cases copy the working tree, plant a verbatim v3.5.66 header, and require the
inventory, build, generated-authority, and composition gates to fail, then to
pass again on the fixed header. Fail-closed cases block the yaml import in a
subprocess; nothing here mocks the parser.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "frontmatter_validation.py"
SPEC = importlib.util.spec_from_file_location("frontmatter_validation_under_test", SCRIPT)
assert SPEC and SPEC.loader
FV = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FV
SPEC.loader.exec_module(FV)

# Verbatim headers shipped in v3.5.66 (056b5337), each unparseable as YAML.
ORIGINAL_SKILL_HEADERS = {
    "skills/pipeline-jobs/SKILL.md": '---\nname: pipeline-jobs\ndescription: Pipeline job pattern. TRIGGER: writing data pipeline scripts, Rundeck jobs, Airflow DAGs, or scheduled data processing. Python first, scheduler second.\nrouted-by: coding-standards\n---\n',
    "skills/skillbuilder/SKILL.md": "---\nname: skillbuilder\ndescription: Create, audit, and fix Claude Code skills. Enforces Anthropic's spec: frontmatter, limits, and classification.\nallowed-tools: Read Grep Glob Write Edit\n---\n",
}
ORIGINAL_RULE_HEADERS = {
    "skills/_prospective-memory-rules.md": '---\ndescription: Always-on. Standing conditional instructions ("do X when Y") decay over the trajectory; compliance drops 2--21% under load (Mittal 2026). This rule names the mitigations: repeat the conditional in each verification block; re-quote standing constraints at decision points; treat self-checks as cognitive-load-dependent and prefer mechanical hooks where available. Sibling to `[rule:standing-approval]` which defines how to PARSE the conditional; this rule defines how to RETAIN it.\n---\n',
    "skills/_ticket-lifecycle-rules.md": '---\ndescription: Always-on ticket lifecycle status discipline. Ticket state must move at the point of action: work start, PR open, test/UAT handoff, blocker, unblock/resume, merge/verified close. Platform-agnostic; requires a comment when a platform lacks a mutable Status field.\n---\n',
    "skills/_enforcement-contradiction-rules.md": "---\ndescription: Always-on. When the enforcement system itself produces contradictions -- gates blocking their own prerequisites, false positives forcing workarounds, inter-rule conflicts, integrity failures, or context mismatches -- the agent must capture evidence, classify the failure, file a ticket with a structured contradiction packet, and triage by blast radius. Workarounds normalize evasion; evidence-based escalation preserves the enforcement system's credibility. Provenance: #590 (self-blocking promotion merge), #591 (stderr redirect false positive), #592 (missing terminal status exit path), #595 (original rule), #597--#603 (cross-review hardening).\n---\n",
}
# Quoted control: same `TRIGGER: ` shape, double-quoted, accepted by the host.
ANALYSIS_HEADER = '---\nname: analysis-methods\ndescription: "Analysis methodology. TRIGGER: geographic data, spatial joins, statistical modeling, graph analysis, entity matching, or text processing. Routes to the method."\nuser-invocable: false\n---\n'


def doc(header: str, body: str = "\n# Body\n") -> str:
    return header + body


def skill_header(**fields: str) -> str:
    lines = ["---"] + [f"{key}: {value}" for key, value in fields.items()] + ["---", ""]
    return "\n".join(lines)


def rejects(text: str, kind: str, needle: str) -> None:
    try:
        FV.validate_text(text, kind=kind, source="fixture.md")
    except FV.FrontmatterDependencyError:
        raise
    except FV.FrontmatterError as exc:
        message = str(exc)
        assert message.startswith(f"{kind} frontmatter invalid in fixture.md: "), message
        assert needle in message, (needle, message)
        return
    raise AssertionError(f"{kind} frontmatter accepted but must fail ({needle}): {text!r}")


def accepts(text: str, kind: str = "skill") -> dict | None:
    return FV.validate_text(text, kind=kind, source="fixture.md")


def unit_cases() -> None:
    # Verbatim v3.5.66 headers: all five reject as YAML syntax errors.
    for header in ORIGINAL_SKILL_HEADERS.values():
        rejects(doc(header), "skill", "invalid YAML: mapping values are not allowed here")
    for header in ORIGINAL_RULE_HEADERS.values():
        rejects(doc(header), "rule", "invalid YAML: mapping values are not allowed here")

    # Quoting is a syntax-only change: parsed value == original raw text.
    for header in (*ORIGINAL_SKILL_HEADERS.values(), *ORIGINAL_RULE_HEADERS.values()):
        line = next(item for item in header.splitlines() if item.startswith("description: "))
        raw = line[len("description: "):]
        quote = "'" if '"' in raw else '"'
        fixed = header.replace(line, f"description: {quote}{raw}{quote}")
        kind = "skill" if "\nname: " in header else "rule"
        assert accepts(doc(fixed), kind)["description"] == raw

    # Synthetic type/shape violations that the presence-only check accepted.
    synthetic = [
        ("description: false", "description must be a non-empty string, got bool False"),
        ("description: [release]", "description must be a non-empty string, got list ['release']"),
        ("description: {a: b}", "description must be a non-empty string, got dict"),
        ('description: "unterminated', "invalid YAML"),
        ("description: 42", "description must be a non-empty string, got int 42"),
        ("description: 2026-10-18", "under YAML 1.1 but str under YAML 1.2"),
        ("description: yes", "unquoted 'yes' resolves as bool under YAML 1.1 but str under YAML 1.2"),
        ("description: Off", "unquoted 'Off' resolves as bool under YAML 1.1"),
    ]
    for line, needle in synthetic:
        rejects(f"---\nname: synthetic\n{line}\n---\n", "skill", needle)
    rejects("---\nname: true\ndescription: ok\n---\n", "skill", "name must be a non-empty string, got bool True")
    rejects("---\nname: 123\ndescription: ok\n---\n", "skill", "name must be a non-empty string, got int 123")
    rejects("---\nname: on\ndescription: ok\n---\n", "skill", "unquoted 'on' resolves as bool")
    # The lint covers every key, not only the required ones.
    rejects("---\nname: x\ndescription: ok\nuser-invocable: no\n---\n", "skill", "unquoted 'no'")
    rejects("---\nname: x\ndescription: ok\nversion: 012\n---\n", "skill", "octal under YAML 1.1 but decimal")
    rejects("---\nname: x\ndescription: ok\nlimit: 1_000\n---\n", "skill", "unquoted '1_000' resolves as int")
    rejects("---\nname: x\ndescription: ok\nduration: 1:20\n---\n", "skill", "unquoted '1:20' resolves as int")
    rejects("---\nname: x\ndescription: ok\nmetadata:\n  enabled: yes\n---\n", "skill", "unquoted 'yes'")
    rejects("---\nname: x\nname: y\ndescription: ok\n---\n", "skill", "found duplicate key 'name'")
    rejects("---\nname: x\ndescription: ok\nmetadata:\n  a: 1\n  a: 2\n---\n", "skill", "found duplicate key 'a'")
    rejects("---\nname: x\n\tdescription: ok\n---\n", "skill", "invalid YAML")

    # Existing #1042 negatives keep failing with a real parser.
    rejects('---\nname: "   "\ndescription: whitespace name\n---\n', "skill", "name must be a non-empty string, got blank")
    rejects("---\nname: # pending\ndescription: comment name\n---\n", "skill", "name must be a non-empty string, got NoneType None")
    rejects("---\nname: comment\ndescription: # pending\n---\n", "skill", "description must be a non-empty string, got NoneType None")
    rejects("---\nname: null\ndescription: null name\n---\n", "skill", "name must be a non-empty string, got NoneType None")
    rejects("---\nname: tilde\ndescription: ~\n---\n", "skill", "description must be a non-empty string, got NoneType None")
    rejects("---\nname: missing\n---\n", "skill", "missing required description")
    rejects("# no frontmatter\n", "skill", "missing frontmatter block")
    rejects("---\nname: x\ndescription: ok\n", "skill", "has no closing '---' line")
    rejects("---\n---\n# empty\n", "skill", "must be a YAML mapping, got NoneType")
    rejects("---\n- name\n- description\n---\n", "skill", "must be a YAML mapping, got list")
    rejects("﻿---\nname: x\ndescription: ok\n---\n", "skill", "without a byte-order mark")
    rejects("---\r\nname: x\r\ndescription: ok\r\n---\r\n", "skill", "LF line endings")

    # Near-miss delimiters must not read as "no frontmatter" (rules would pass).
    for kind in ("skill", "rule"):
        rejects("--- \ndescription: a: b\n---\n# Rule\n", kind, "delimiter must be exactly '---' on the first line")
        rejects("\n---\ndescription: a: b\n---\n# Rule\n", kind, "delimiter must be exactly '---' on the first line")
    # YAML 1.1-only or alias-based constructs are rejected outright.
    rejects("---\nname: x\ndescription: &d hello\n---\n", "skill", "anchor not allowed")
    rejects("---\nname: x\nbase: &b {description: ok}\n<<: *b\n---\n", "skill", "merge key '<<' is YAML 1.1 only")
    rejects("---\nname: x\ndescription: ok\ntags: !!set {a, b}\n---\n", "skill", "explicit tag not allowed")
    rejects("---\nname: x\ndescription: ok\nsteps: !!omap [a: 1, a: 2]\n---\n", "skill", "explicit tag not allowed")
    try:
        FV.validate_file("/nonexistent/frontmatter/SKILL.md", kind="rule")
    except FV.FrontmatterError as exc:
        assert "rule frontmatter unreadable in /nonexistent/frontmatter/SKILL.md" in str(exc), exc
    else:
        raise AssertionError("unreadable rule file validated")
    with tempfile.TemporaryDirectory() as raw:
        undecodable = Path(raw) / "_bad-rules.md"
        undecodable.write_bytes(b"---\ndescription: \xff\n---\n")
        try:
            FV.validate_file(undecodable, kind="rule", source="skills/_bad-rules.md")
        except FV.FrontmatterError as exc:
            assert "rule frontmatter unreadable in skills/_bad-rules.md" in str(exc), exc
        else:
            raise AssertionError("undecodable rule file validated")

    # Rule headers: optional block, but a present block must be valid.
    assert accepts("# Rule without frontmatter\n", "rule") is None
    assert accepts('---\ndescription: "Always-on. Rule: quoted."\n---\n', "rule") == {"description": "Always-on. Rule: quoted."}
    rejects("---\ndescription: false\n---\n", "rule", "description must be a non-empty string, got bool")
    rejects("---\ndescription: ''\n---\n", "rule", "description must be a non-empty string, got blank")
    rejects("---\nname: 5\ndescription: ok\n---\n", "rule", "name must be a non-empty string, got int")

    # Positive controls.
    assert accepts(doc(ANALYSIS_HEADER))["user-invocable"] is False
    folded = accepts("---\nname: folded\ndescription: >-\n  Folded text. TRIGGER: spans\n  two lines.\n---\n")
    assert folded["description"] == "Folded text. TRIGGER: spans two lines."
    single = accepts("---\nname: single\ndescription: 'It''s quoted: with a colon'\n---\n")
    assert single["description"] == "It's quoted: with a colon"
    typed = accepts("---\nname: typed\ndescription: ok\nuser-invocable: true\nglobs:\n  - '*.py'\nmetadata:\n  version: \"1.0\"\n---\n")
    assert typed["user-invocable"] is True and typed["globs"] == ["*.py"]

    try:
        FV.validate_text("---\nname: x\ndescription: ok\n---\n", kind="unknown")
    except ValueError as exc:
        assert "unknown frontmatter kind" in str(exc)
    else:
        raise AssertionError("unknown kind accepted")


def committed_content_cases() -> None:
    """The committed fixes parse, and their values equal the v3.5.66 raw text byte for byte."""
    for rel, header in {**ORIGINAL_SKILL_HEADERS, **ORIGINAL_RULE_HEADERS}.items():
        kind = "skill" if rel.endswith("SKILL.md") else "rule"
        current = (ROOT / rel).read_text(encoding="utf-8")
        parsed = FV.validate_file(ROOT / rel, kind=kind, source=rel)
        original_lines = header.splitlines()
        current_lines = current[:len(header) + 2].splitlines()[:len(original_lines)]
        changed = [(old, new) for old, new in zip(original_lines, current_lines) if old != new]
        assert len(changed) == 1 and changed[0][0].startswith("description: "), (rel, changed)
        raw = changed[0][0][len("description: "):]
        assert parsed["description"] == raw, rel
        assert changed[0][1] in (f'description: "{raw}"', f"description: '{raw}'"), rel
        # The whole header grew by exactly the two quote characters.
        end = current.find("\n---\n", 3)
        assert len(current[:end + len("\n---\n")]) == len(header) + 2, rel


BLOCK_YAML = "import sys; sys.modules['yaml'] = None\n"


def run(argv: list[str], cwd: Path, *, block_yaml: bool = False, timeout: int = 300) -> subprocess.CompletedProcess:
    if block_yaml:
        script, rest = argv[0], argv[1:]
        code = BLOCK_YAML + (
            "import runpy\n"
            f"sys.argv = [{script!r}, *{rest!r}]\n"
            f"runpy.run_path({script!r}, run_name='__main__')\n"
        )
        command = [sys.executable, "-B", "-c", code]
    else:
        command = [sys.executable, "-B", *argv]
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def fail_closed_cases() -> None:
    probe = run(
        [str(SCRIPT), str(ROOT / "skills" / "analysis" / "SKILL.md")], ROOT, block_yaml=True,
    )
    assert probe.returncode == 2, probe
    assert "PyYAML is required for frontmatter validation" in probe.stderr, probe.stderr
    assert "PyYAML==6.0.3" in probe.stderr, probe.stderr

    api = subprocess.run(
        [sys.executable, "-B", "-c", BLOCK_YAML + (
            "import importlib.util\n"
            f"spec = importlib.util.spec_from_file_location('fv', {str(SCRIPT)!r})\n"
            "fv = importlib.util.module_from_spec(spec); spec.loader.exec_module(fv)\n"
            "for kind, text in (('skill', '---\\nname: x\\ndescription: ok\\n---\\n'), ('rule', '# no block\\n')):\n"
            "    try:\n"
            "        fv.validate_text(text, kind=kind)\n"
            "    except fv.FrontmatterDependencyError:\n"
            "        continue\n"
            "    raise SystemExit('validated without PyYAML: ' + kind)\n"
            "print('fail-closed')\n"
        )],
        capture_output=True, text=True, timeout=60,
    )
    assert api.returncode == 0 and api.stdout.strip() == "fail-closed", api


def preflight_cases() -> None:
    """install.sh and sync-workspace-hooks.sh stop before any build/deploy
    unless python3 imports the pinned PyYAML.

    Copies of the scripts and the validator run from an otherwise empty root,
    so a regression reaches a missing bin/build.py instead of a real install.
    """
    pin = next(line for line in (ROOT / "requirements-validation.txt").read_text().splitlines()
               if line.startswith("PyYAML=="))
    assert pin.split()[0] == FV.PYYAML_REQUIREMENT, (pin, FV.PYYAML_REQUIREMENT)
    expected_install = (
        '    python3 -m pip install --require-hashes -r "{root}/requirements-validation.txt"'
    )
    with tempfile.TemporaryDirectory(prefix="install-preflight-") as raw:
        scratch = Path(raw).resolve()
        (scratch / "bin").mkdir()
        for name in ("install.sh", "sync-workspace-hooks.sh", "frontmatter_validation.py"):
            shutil.copy2(ROOT / "bin" / name, scratch / "bin" / name)
        shim = scratch / "python-bin"
        shim.mkdir()
        # A wrapper, not a symlink, so a virtualenv interpreter keeps its site-packages.
        (shim / "python3").write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
        (shim / "python3").chmod(0o755)
        absent = scratch / "absent-yaml"
        absent.mkdir()
        (absent / "yaml.py").write_text("raise ImportError('PyYAML blocked by test')\n")
        stale = scratch / "stale-yaml"
        stale.mkdir()
        (stale / "yaml.py").write_text("__version__ = '5.4.1'\n")
        base_env = {"PATH": f"{shim}:/usr/bin:/bin", "HOME": str(scratch / "home")}
        commands = {
            "install.sh": (["bash", str(scratch / "bin/install.sh"), "--no-craft-agent"], "bin/build.py not found"),
            "sync-workspace-hooks.sh": (
                ["bash", str(scratch / "bin/sync-workspace-hooks.sh"), "--yes", "--workspace", str(scratch / "ws")],
                "=== Sync workspace hooks ===",
            ),
        }
        for script, (command, proceeded) in commands.items():
            for label, pythonpath, reason in (
                ("absent", absent, "PyYAML is required for frontmatter validation and is not importable"),
                ("stale", stale, "PyYAML 5.4.1 is importable by"),
            ):
                result = subprocess.run(command, capture_output=True, text=True, timeout=60,
                                        env={**base_env, "PYTHONPATH": str(pythonpath)})
                output = result.stdout + result.stderr
                assert result.returncode == 1, (script, label, result)
                assert "ERROR: PyYAML is required for frontmatter validation: frontmatter validation unavailable: " in result.stderr, (script, label, result.stderr)
                assert reason in result.stderr, (script, label, result.stderr)
                assert "Supported interpreter: CPython 3.12 (the CI-validated version; 3.9+ is compatible) as python3 on PATH," in result.stderr
                assert expected_install.format(root=scratch) in result.stderr.splitlines(), (script, result.stderr)
                assert proceeded not in output, f"{script} continued past the preflight ({label})"
                assert not (scratch / "ws").exists() and not (scratch / "dist").exists(), f"{script} mutated before preflight"
            present = subprocess.run(command, capture_output=True, text=True, timeout=60, env=base_env)
            assert "PyYAML is required" not in present.stderr, (script, present.stderr)
            assert proceeded in present.stdout + present.stderr, (script, present)
            assert present.returncode != 0, "scratch root has no build.py, so the script must stop there"


def copy_tree(destination: Path) -> None:
    # Build policy checks require real ancestry, so start from a shared clone of
    # HEAD and overlay the current working tree (including uncommitted edits).
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], check=True,
                          capture_output=True, text=True, timeout=30).stdout.strip()
    subprocess.run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(ROOT), str(destination)],
                   check=True, capture_output=True, timeout=120)
    subprocess.run(["git", "-C", str(destination), "-c", "core.hooksPath=/dev/null", "checkout", "--quiet",
                    "--detach", head], check=True, capture_output=True, timeout=120)
    listed = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True, capture_output=True, timeout=60,
    ).stdout.split(b"\0")
    for raw in listed:
        if not raw:
            continue
        rel = raw.decode()
        source = ROOT / rel
        if not source.is_file() or source.is_symlink():
            continue
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    subprocess.run(["git", "-C", str(destination), "add", "-A"], check=True, timeout=60)


def replace_header(path: Path, header: str) -> str:
    original = path.read_text(encoding="utf-8")
    end = original.find("\n---\n", 3)
    assert original.startswith("---\n") and end > 0, path
    path.write_text(header + original[end + len("\n---\n"):], encoding="utf-8")
    return original


def gate_cases() -> None:
    with tempfile.TemporaryDirectory(prefix="frontmatter-gates-") as raw:
        tree = Path(raw) / "tree"
        copy_tree(tree)
        identity = "github.example.invalid/synthetic-org/strict-release"
        gates = {
            "inventory --check": ["bin/skill-inventory.py", "--check"],
            "build --check": ["bin/build.py", "--check"],
            "build": ["bin/build.py", "--dist", str(Path(raw) / "dist")],
            "generated authority --check": ["bin/generated-source-authority.py", "--check"],
        }
        compose = ["bin/compose-project.py", "--identity", identity]

        def compose_run(name: str) -> subprocess.CompletedProcess:
            return run([*compose, "--output", str(Path(raw) / name)], tree)

        # Baseline: the fixed tree passes every gate.
        for name, argv in gates.items():
            result = run(argv, tree)
            assert result.returncode == 0, (name, result.stdout[-1500:], result.stderr[-1500:])
        shutil.rmtree(Path(raw) / "dist")
        assert compose_run("compose-ok").returncode == 0

        # One verbatim bad skill header and one verbatim bad rule header.
        for rel, header in (
            ("skills/pipeline-jobs/SKILL.md", ORIGINAL_SKILL_HEADERS["skills/pipeline-jobs/SKILL.md"]),
            ("skills/_ticket-lifecycle-rules.md", ORIGINAL_RULE_HEADERS["skills/_ticket-lifecycle-rules.md"]),
        ):
            path = tree / rel
            original = replace_header(path, header)
            try:
                for name, argv in gates.items():
                    result = run(argv, tree)
                    assert result.returncode != 0, f"{name} accepted bad header {rel}"
                    assert rel in result.stdout + result.stderr, (name, result.stderr[-1500:])
                    assert "mapping values are not allowed here" in result.stdout + result.stderr, name
                    # Phase 3b runs before any layout is written.
                    assert not (Path(raw) / "dist").exists(), f"{name} wrote output before rejecting {rel}"
            finally:
                path.write_text(original, encoding="utf-8")

        # Composed/selected packaging validates its own publisher roots.
        composed = tree / "examples/composition/skills/self-review/SKILL.md"
        original = replace_header(composed, "---\nname: self-review\ndescription: false\n---\n")
        try:
            result = compose_run("compose-bad")
            assert result.returncode != 0, "composition packaged a non-string description"
            # compose-project reports failures as a JSON diagnostic on stdout.
            assert "description must be a non-empty string, got bool False" in result.stdout, result.stdout[-1500:]
            assert "skill frontmatter invalid in skills/self-review/SKILL.md" in result.stdout, result.stdout[-1500:]
        finally:
            composed.write_text(original, encoding="utf-8")
        assert compose_run("compose-fixed").returncode == 0

        # Without PyYAML every gate fails closed with the explicit dependency message.
        for name, argv in {
            "inventory --check": gates["inventory --check"],
            "build --check": gates["build --check"],
            "compose": [*compose, "--output", str(Path(raw) / "compose-noyaml")],
        }.items():
            result = run(argv, tree, block_yaml=True)
            assert result.returncode != 0, f"{name} passed without PyYAML"
            assert "PyYAML is required for frontmatter validation" in result.stdout + result.stderr, (name, result.stderr[-1500:])


def main() -> None:
    unit_cases()
    committed_content_cases()
    fail_closed_cases()
    preflight_cases()
    gate_cases()
    print("frontmatter_validation_test: PASS")


if __name__ == "__main__":
    main()
