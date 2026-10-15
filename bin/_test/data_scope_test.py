#!/usr/bin/env python3
"""Behavioral boundary tests for #976 data/geospatial routes and dispositions."""
from __future__ import annotations
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("data_resolver", ROOT / "bin/resolve-load-set.py")
assert spec and spec.loader
resolver = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = resolver
spec.loader.exec_module(resolver)
scope_spec = importlib.util.spec_from_file_location("data_checker", ROOT / "bin/data-scope.py")
assert scope_spec and scope_spec.loader
checker = importlib.util.module_from_spec(scope_spec)
sys.modules[scope_spec.name] = checker
scope_spec.loader.exec_module(checker)


def main() -> None:
    manifest = json.loads((ROOT / "catalog/resolver-manifest.json").read_text())
    inventory = json.loads((ROOT / "catalog/skills-inventory.json").read_text())
    fixtures = {c["id"]: c for c in json.loads((ROOT / "catalog/data-scope-fixtures.json").read_text())["fixtures"]}
    ledger = json.loads((ROOT / "catalog/data-scope-ledger.json").read_text())
    assert len(ledger["items"]) == 34 and len(fixtures) >= 78
    assert {i["classification"] for i in ledger["items"]} == {"reusable-global", "exact-project", "reference-only", "compatibility"}
    assert all(i["known_consumers"] == "UNKNOWN" for i in ledger["items"] if i["classification"] != "exact-project")
    assert all(i["known_consumers"] == [checker.EXACT] for i in ledger["items"] if i["classification"] == "exact-project")
    expectations = {
        "etl": {"pipeline-jobs"}, "analysis": {"analysis"}, "catalog-raw-write": {"unity-catalog"},
        "catalog-saveastable": {"unity-catalog"}, "scala": {"scala-on-spark", "spark"},
        "postgis": {"postgis", "sql", "spatial", "coding"}, "geopandas": {"geopandas", "spatial"},
        "sedona": {"sedona", "spark", "spatial", "sql", "coding"},
        "duckdb": {"duckdb-spatial", "sql", "spatial", "coding"},
    }
    for id, slugs in expectations.items():
        assert set(fixtures[id]["slugs"]) == slugs, id
    for id in ("unknown", "arcgis", "visualization", "read-only", "negative-sql", "negative-uc", "negative-etl", "negative-stat", "negative-engine", "negative-foreign-project", "unknown-arcgis", "scala-file", "scala-negative", "etl-java", "negative-unrelated-catalog", "negative-negated-write", "negative-read-only-delta", "negative-how-to", "negative-viz-engine", "negative-insert-question", "negative-duckdb-docs", "negative-viz-geodataframe", "negative-viz-geometry", "negative-doc-postgis", "negative-how-do-i", "negative-sqlite-insert", "negative-csv-write", "negative-spark-crd", "negative-write-docs", "negative-unrelated-readme", "negative-unrelated-title", "negative-crd-csv"):
        assert fixtures[id]["state"] == "unknown" and fixtures[id]["slugs"] == [], id
    assert fixtures["ambiguous"]["state"] == "ambiguous" and not fixtures["ambiguous"]["slugs"]
    assert fixtures["over-budget"]["state"] == "over-budget" and not fixtures["over-budget"]["slugs"]
    for id in ("foreign-postgis", "bare-project"):
        assert fixtures[id]["slugs"] == fixtures["postgis"]["slugs"] and not any(s.startswith("siege-utilities") for s in fixtures[id]["slugs"])
    assert fixtures["exact-postgis"]["slugs"] == ["siege-utilities--rules"] + fixtures["postgis"]["slugs"]
    for id in ("catalog-orc", "catalog-bronze", "catalog-register", "catalog-insert"):
        assert fixtures[id]["slugs"] == ["unity-catalog"], id
    assert set(fixtures["spatial-analysis"]["slugs"]) == {"analysis", "spatial"}
    assert fixtures["geospatial-crs"]["slugs"] == ["spatial"]
    assert set(fixtures["duckdb-extension"]["slugs"]) == {"duckdb-spatial", "spatial", "sql"}
    assert {"postgis", "sql", "spatial"} <= set(fixtures["postgis-st"]["slugs"])
    assert {"geopandas", "spatial"} == set(fixtures["geopandas-overlay"]["slugs"])
    for id in ("catalog-insert-into", "catalog-insert-bare", "concrete-edit-catalog", "concrete-patch-catalog"):
        assert "unity-catalog" in fixtures[id]["slugs"], id
    for id in ("catalog-crd-delta", "catalog-crd-parquet", "catalog-crd-implement"):
        assert fixtures[id]["slugs"] == ["unity-catalog"], id
    assert fixtures["negative-inherited-doc-leak"]["slugs"] == ["unity-catalog"]
    assert "unity-catalog" not in fixtures["negative-postgres-insert"]["slugs"]
    assert {"postgis", "spatial", "sql"} <= set(fixtures["concrete-edit-postgis"]["slugs"])
    assert {"postgis", "spatial", "sql"} <= set(fixtures["multiline-postgis"]["slugs"])
    assert {"sedona", "spark", "spatial"} <= set(fixtures["multiline-sedona"]["slugs"])
    assert "pipeline-jobs" in fixtures["etl-python-and-scala"]["slugs"]
    assert {"geopandas", "spatial"} == set(fixtures["viz-with-transform"]["slugs"])
    for id, engine in (("analyze-geopandas", "geopandas"), ("analyze-postgis", "postgis"), ("analyze-sedona", "sedona")):
        assert engine in fixtures[id]["slugs"] and "spatial" in fixtures[id]["slugs"], id
    for form in checker.CONSUMERS:
        for fixture in fixtures.values():
            result = checker.resolved(form, fixture)
            assert (result["state"], [s["slug"] for s in result["selected"]], [s["source_path"] for s in result["selected"]]) == (fixture["state"], fixture["slugs"], fixture["source_paths"]), (form, fixture["id"])
            assert result.get("selected_content", {}) == fixture["measurements"][form], (form, fixture["id"])
            package = ROOT if form == "source" else ROOT / "dist" / form
            meta = {} if form == "source" else json.loads((package / "catalog/resolver-manifest.json").read_text())["known_by_source"]
            selected_bytes = sum(len((package / (x["source_path"] if form == "source" else meta[x["source_path"]]["package_path"])).read_bytes()) for x in result["selected"])
            assert selected_bytes == fixture["selected_bytes"][form], (form, fixture["id"])
            if result["state"] in ("unknown", "ambiguous", "over-budget"):
                assert not result["selected"]
    for slug in ("shelves--geospatial", "shelves--data-and-pipelines", "shelves--storytelling", "shelves--data-intensive", "shelves--think-stats"):
        for token in (f"[skill:{slug}]", f"/{slug}"):
            assert resolver.select(manifest, inventory, token, "other/repo")["state"] == "unknown"
    # A path under a foreign host, even with matching owner/repo, never authorizes SU.
    for repo in ("siege-analytics/siege_utilities", "git@foreign-host:siege-analytics/siege_utilities.git", "github.com/elsewhere/siege_utilities"):
        result = resolver.select(manifest, inventory, "write PostGIS spatial join SQL", repo)
        assert result["project"] is None and not any(x["slug"].startswith("siege-utilities") for x in result["selected"])
    # Action gates cannot be bypassed with an unrecognized technology or a broad noun.
    for prompt in ("Which SQL query is fastest?", "Explain Unity Catalog", "Is Scala a language?", "ArcGIS PostGIS overview", "What is geospatial analysis?", "Read Delta table", "What is an Airflow DAG?"):
        assert resolver.select(manifest, inventory, prompt, "other/repo")["state"] == "unknown", prompt
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "SKILL.md"
        probe.write_text("## Setup\nUse `siege_utilities` as the default source for all projects.\n")
        try:
            checker.language.check_global_su_scope(probe)
        except ValueError as exc:
            assert "ungated SU" in str(exc)
        else:
            raise AssertionError("unconditional global SU prescription accepted")
    checker.compute(False)
    print("data_scope_test: PASS")


if __name__ == "__main__":
    main()
