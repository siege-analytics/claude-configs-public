#!/usr/bin/env python3
"""Behavior and regression tests for the #975 language scope ledger."""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("scope_resolver", ROOT / "bin/resolve-load-set.py")
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = resolver
spec.loader.exec_module(resolver)


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
    assert not any(r["id"] in ("qml", "scala-on-spark") for r in manifest["routes"])
    assert resolver.select(manifest, inv, "design a REST framework in FastAPI", "other/repo")["state"] == "unknown"
    for prompt in ("docs.rs", "crates.rs", "x.tailnet.ts.net", "example.tsx.map", "mail.vue.example"):
        assert resolver.select(manifest, inv, prompt, "other/repo")["state"] == "unknown", prompt
    for prompt in ("[skill:django-rest-framework]", "/django-rest-framework"):
        assert {x["slug"] for x in resolver.select(manifest, inv, prompt, "other/repo")["selected"]} == {"coding", "django", "django-rest-framework", "python"}, prompt
    for prompt in ("[skill:rust]", "/rust", "[rule:rust]"):
        assert {x["slug"] for x in resolver.select(manifest, inv, prompt, "other/repo")["selected"]} == {"coding", "rust"}, prompt
    assert {x["slug"] for x in resolver.select(manifest, inv, "[rule:typescript]", "other/repo")["selected"]} == {"coding", "typescript"}
    assert resolver.select(manifest, inv, "[rule:react]", "other/repo")["state"] == "unknown"  # same slug resolves to skill, not rule
    assert resolver.select(manifest, inv, "review this Python diff", "siege-analytics/siege_utilities")["project"] is None
    assert resolver.select(manifest, inv, "review Python Spark SQL Databricks Unity Catalog spatial PostGIS code", "other/repo")["state"] == "matched"
    assert resolver.select(manifest, inv, "create ticket and close issue", "other/repo")["state"] == "ambiguous"
    assert resolver.select(manifest, inv, "[skill:react] [skill:typescript] [skill:vue] [skill:rust] " + " ".join(f"[skill:{s}]" for s in ("branch", "commit", "create-pr", "merge", "code-review", "skillbuilder", "python", "sql", "spark")), "other/repo")["state"] == "over-budget"
    subprocess.run([sys.executable, str(ROOT / "bin/language-scope.py"), "--check"], check=True)
    print("language_scope_test: PASS")


if __name__ == "__main__":
    main()
