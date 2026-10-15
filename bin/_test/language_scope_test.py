#!/usr/bin/env python3
"""Behavior and regression tests for the #975 language scope ledger."""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("scope_resolver", ROOT / "bin/resolve-load-set.py")
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = resolver
spec.loader.exec_module(resolver)
scope_spec = importlib.util.spec_from_file_location("scope_check", ROOT / "bin/language-scope.py")
assert scope_spec and scope_spec.loader
scope_check = importlib.util.module_from_spec(scope_spec)
sys.modules[scope_spec.name] = scope_check
scope_spec.loader.exec_module(scope_check)


def main() -> None:
    manifest = json.loads((ROOT / "catalog/resolver-manifest.json").read_text())
    inv = json.loads((ROOT / "catalog/skills-inventory.json").read_text())
    cases = json.loads((ROOT / "catalog/language-scope-fixtures.json").read_text())["fixtures"]
    for case in cases:
        for form in ("source", "claude-code", "craft-agent"):
            script = ROOT / ("bin/resolve-load-set.py" if form == "source" else f"dist/{form}/bin/resolve-load-set.py")
            result = json.loads(subprocess.check_output([sys.executable, str(script), "--prompt", case["prompt"], "--repo", case["repo"]], text=True))
            assert (result["state"], [x["slug"] for x in result["selected"]]) == (case["state"], case["slugs"]), (form, case["id"])
            assert result.get("selected_content", {}) == case["measurements"][form], (form, case["id"])
            if "source_paths" in case:
                assert [x["source_path"] for x in result["selected"]] == case["source_paths"], (form, case["id"])
            if case["id"] == "foreign-spatial-content":
                # Read the exact files selected in source/consumer packages;
                # the check enforces section boundaries, not string absence.
                package = ROOT if form == "source" else ROOT / "dist" / form
                meta = None if form == "source" else json.loads((package / "catalog/resolver-manifest.json").read_text())["known_by_source"]
                for selected in result["selected"]:
                    path = package / (selected["source_path"] if meta is None else meta[selected["source_path"]]["package_path"])
                    scope_check.check_global_su_scope(path)
    # A rejected explicit slug may not select by name through a prose route.
    for prompt in ("[skill:shelves--effective-python]", "/shelves--effective-python", "[skill:siege-utilities--hostile-review]", "/siege-utilities--hostile-review"):
        result = resolver.select(manifest, inv, prompt, "git@foreign-host:siege-analytics/siege_utilities.git")
        assert result["state"] == "unknown" and result["selected"] == []
    # Distinct lifecycle concerns stay intact, including deferred Scala work.
    ledger = json.loads((ROOT / "catalog/language-scope-ledger.json").read_text())
    assert len(ledger["items"]) == 39
    assert {i["classification"] for i in ledger["items"]} == {"reusable-global", "exact-project", "reference-only", "compatibility"}
    assert all(i["known_consumers"] == "UNKNOWN" for i in ledger["items"] if i["classification"] != "exact-project")
    assert all(i["known_consumers"] == ["github.com/siege-analytics/siege_utilities"] for i in ledger["items"] if i["classification"] == "exact-project")
    assert not any(r["id"] == "qml" for r in manifest["routes"])
    assert {x["slug"] for x in resolver.select(manifest, inv, "write a Scala Spark Dataset[T] transform", "other/repo")["selected"]} == {"scala-on-spark", "spark"}
    assert resolver.select(manifest, inv, "design a REST framework in FastAPI", "other/repo")["state"] == "unknown"
    for prompt in ("docs.rs", "crates.rs", "x.tailnet.ts.net", "example.tsx.map", "mail.vue.example"):
        assert resolver.select(manifest, inv, prompt, "other/repo")["state"] == "unknown", prompt
    for prompt in ("[skill:django-rest-framework]", "/django-rest-framework"):
        assert {x["slug"] for x in resolver.select(manifest, inv, prompt, "other/repo")["selected"]} == {"coding", "django", "django-rest-framework", "python"}, prompt
    for prompt in ("[rule:rust]", "/rust"):
        assert {x["slug"] for x in resolver.select(manifest, inv, prompt, "other/repo")["selected"]} == {"coding", "rust"}, prompt
    assert {x["slug"] for x in resolver.select(manifest, inv, "[rule:typescript]", "other/repo")["selected"]} == {"coding", "typescript"}
    for slug,rule_path,skill_path in (
        ("python", "skills/_python-rules.md", "skills/python/SKILL.md"),
        ("react", "skills/_react-rules.md", "skills/react/SKILL.md"),
        ("django-rest-framework", "skills/_django-rest-framework-rules.md", "skills/django-rest-framework/SKILL.md"),
    ):
        pair = resolver.select(manifest, inv, f"[rule:{slug}] [skill:{slug}]", "other/repo")
        assert [x["source_path"] for x in pair["selected"] if x["slug"] == slug] == [rule_path, skill_path], pair
        assert pair["selected_content"]["items"] == len(pair["selected"])
        for kind,path in (("rule",rule_path),("skill",skill_path)):
            selected = resolver.select(manifest, inv, f"[{kind}:{slug}]", "other/repo")["selected"]
            assert any(x["source_path"] == path for x in selected), (kind, slug, selected)
    for slug in ("typescript", "rust", "siege-utilities"):
        result = resolver.select(manifest, inv, f"[skill:{slug}]", "other/repo")
        assert result["state"] == "unknown" and result["selected"] == [], slug
    for slug in ("vue", "geopandas", "sedona"):
        result = resolver.select(manifest, inv, f"[rule:{slug}]", "other/repo")
        assert result["state"] == "unknown" and result["selected"] == [], slug
    assert resolver.select(manifest, inv, "/react", "other/repo")["selected"][0]["source_path"] == "skills/react/SKILL.md"
    inflated = json.loads(json.dumps(inv))
    next(i for i in inflated["items"] if i["source_path"] == "skills/_react-rules.md")["characters"] = 79000
    pair = resolver.select(manifest, inflated, "[rule:react] [skill:react]", "other/repo")
    assert pair["state"] == "over-budget" and pair["selected"] == [] and pair["selected_content"]["items"] == 2
    assert resolver.select(manifest, inv, "review this Python diff", "siege-analytics/siege_utilities")["project"] is None
    assert resolver.select(manifest, inv, "review Python Spark SQL Databricks Unity Catalog spatial PostGIS code", "other/repo")["state"] == "matched"
    assert resolver.select(manifest, inv, "create ticket and close issue", "other/repo")["state"] == "ambiguous"
    assert resolver.select(manifest, inv, "[skill:react] [rule:typescript] [skill:vue] [rule:rust] " + " ".join(f"[skill:{s}]" for s in ("branch", "commit", "create-pr", "merge", "code-review", "skillbuilder", "python", "sql", "spark")), "other/repo")["state"] == "over-budget"
    # The preceding exact-host gate must not leak into a later global section.
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "SKILL.md"
        probe.write_text("## Exact host only\nOnly for exact `github.com/siege-analytics/siege_utilities`:\n"
                         "from siege_utilities.geo import capabilities\n")
        scope_check.check_global_su_scope(probe)
        probe.write_text(probe.read_text() + "## Quick start\nfrom siege_utilities.geo import spatial_data\n")
        try:
            scope_check.check_global_su_scope(probe)
        except ValueError as exc:
            assert "ungated SU" in str(exc)
        else:
            raise AssertionError("global SU import escaped scope check")
        probe.write_text("## Runtime detection\nSU detects and recommends the runtime.\n")
        try:
            scope_check.check_global_su_scope(probe)
        except ValueError as exc:
            assert "ungated SU" in str(exc)
        else:
            raise AssertionError("global SU recommendation escaped scope check")
    subprocess.run([sys.executable, str(ROOT / "bin/language-scope.py"), "--check"], check=True)
    print("language_scope_test: PASS")


if __name__ == "__main__":
    main()
