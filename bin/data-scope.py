#!/usr/bin/env python3
"""Verify #976 source dispositions, exact-base costs, and source/consumer routes.

Build dist, inventory and generated authority first. --write refreshes current
measurements only; it never rewrites identities, classifications, or expected
routes. Packaged baseline is attested from an isolated build of BASE.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "f115158b58db3690d2ea63999699284dc79db1bb"
EXACT = "github.com/siege-analytics/siege_utilities"
LEDGER = ROOT / "catalog/data-scope-ledger.json"
FIXTURES = ROOT / "catalog/data-scope-fixtures.json"
FORMS = ("nested", "flat", "claude-code", "craft-agent")
# Existing ledgers attest source plus the two dedicated archives. Current parity
# also covers both release-branch layouts without rewriting historical evidence.
CONSUMERS = ("source", "claude-code", "craft-agent")
ALL_CONSUMERS = ("source", *FORMS)
GLOBAL = {"analysis", "pipeline-jobs", "unity-catalog", "scala-on-spark", "sql", "spark", "databricks", "spatial", "postgis", "geopandas", "sedona", "duckdb-spatial", "coding"}
SHELVES = ("data-and-pipelines", "geospatial", "statistical-inference", "storytelling")
VALID = {"reusable-global", "exact-project", "reference-only", "compatibility"}
spec = importlib.util.spec_from_file_location("language_scope_for_data", ROOT / "bin/language-scope.py")
assert spec and spec.loader
language = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = language
spec.loader.exec_module(language)


def cost(characters: int) -> dict:
    return {"characters": characters, "estimated_tokens": math.ceil(characters / 4)}


def text_cost(text: str) -> dict:
    return cost(len(text)) | {"bytes": len(text.encode("utf-8"))}


def measure(path: Path) -> dict:
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"missing generated output: {path}")
    text = "".join(p.read_text() for p in files)
    return text_cost(text)


def baseline(path: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{path}"], text=True, timeout=15)


def required_sources(inv: dict) -> set[str]:
    return {p for p in inv if p in {f"skills/{s}/SKILL.md" for s in GLOBAL} | {"skills/_data-trust-rules.md", "skills/_siege-utilities-rules.md"}
            or p.startswith("projects/siege-utilities/") and (p.endswith("SKILL.md") or p.endswith("_rules.md"))
            or any(p.startswith(f"skills/shelves/{s}/") and p.endswith("SKILL.md") for s in SHELVES)
            or p == "skills/shelves/systems-architecture/data-intensive/SKILL.md"}


def resolved(form: str, fixture: dict) -> dict:
    script = ROOT / ("bin/resolve-load-set.py" if form == "source" else f"dist/{form}/bin/resolve-load-set.py")
    proc = subprocess.run([sys.executable, str(script), "--prompt", fixture["prompt"], "--repo", fixture["repo"]], capture_output=True, text=True, timeout=20)
    if proc.returncode:
        raise ValueError(f"resolver failed: {form}/{fixture['id']}: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def compute(write: bool) -> None:
    ledger = json.loads(LEDGER.read_text())
    fixture_data = json.loads(FIXTURES.read_text())
    inv = {i["source_path"]: i for i in json.loads((ROOT / "catalog/skills-inventory.json").read_text())["items"]}
    manifest = json.loads((ROOT / "catalog/resolver-manifest.json").read_text())
    if manifest["projects"] != json.loads(baseline("catalog/resolver-manifest.json"))["projects"] or manifest["projects"][0]["repos"] != [EXACT]:
        raise ValueError("exact-host project scope changed")
    required = required_sources(inv)
    recorded = {i["source"] for i in ledger["items"]}
    if ledger["base_sha"] != BASE or len(recorded) != len(ledger["items"]) or recorded != required:
        raise ValueError(f"incomplete data ledger: missing={sorted(required-recorded)}, extra={sorted(recorded-required)}")
    routes = {s for r in manifest["routes"] for s in r["skills"]}
    routed_paths = {next(i for i in inv.values() if i["slug"] == slug)["source_path"] for slug in routes}
    if manifest["policy"]["shelves_auto_select"] is not False or any(p.startswith("skills/shelves/") for p in routed_paths):
        raise ValueError("reference shelf promoted to auto-selection")
    packages = {form: json.loads((ROOT / f"dist/{form}/catalog/resolver-manifest.json").read_text()) for form in FORMS}
    for form, pkg in packages.items():
        for source, meta in pkg["known_by_source"].items():
            if {k: meta[k] for k in ("characters", "estimated_tokens")} != cost(len((ROOT / f"dist/{form}" / meta["package_path"]).read_text())):
                raise ValueError(f"package character mismatch: {form}/{source}")
    for entry in ledger["items"]:
        path = entry["source"]
        item = inv[path]
        if entry["slug"] != item["slug"] or entry["kind"] != item["kind"] or entry["classification"] not in VALID:
            raise ValueError(f"wrong identity/disposition: {path}")
        if entry["baseline"]["authored"] != text_cost(baseline(path)) or set(entry["baseline"]["packaged"]) != set(FORMS):
            raise ValueError(f"invalid exact-base cost: {path}")
        if entry["classification"] == "exact-project":
            if not path.startswith("projects/siege-utilities/") or entry["known_consumers"] != [EXACT] or entry["auto_select"] != "exact-project":
                raise ValueError(f"invalid exact project: {path}")
        elif entry["known_consumers"] != "UNKNOWN" or not entry["consumer_evidence"].startswith("UNKNOWN:"):
            raise ValueError(f"unproven consumer: {path}")
        if entry["classification"] == "reference-only":
            if not path.startswith("skills/shelves/") or path in routed_paths or entry["auto_select"] != "never":
                raise ValueError(f"shelf route leak: {path}")
        if entry["classification"] == "compatibility":
            if path != "skills/_siege-utilities-rules.md" or path in routed_paths or entry["auto_select"] != "explicit-only":
                raise ValueError(f"compatibility pointer became global route: {path}")
        if entry["classification"] == "reusable-global":
            if path.startswith("projects/") or entry["auto_select"] == "exact-project":
                raise ValueError(f"global scope leak: {path}")
            # #975's section-aware gate applies to every active global data
            # source, not just the spatial engines; package text must match.
            language.check_global_su_scope(ROOT / path)
            for form in FORMS:
                language.check_global_su_scope(ROOT / f"dist/{form}" / packages[form]["known_by_source"][path]["package_path"])
        if path == "skills/analysis/SKILL.md" and "\npaths:" in (ROOT / path).read_text().split("---", 2)[1]:
            raise ValueError("native data extension auto-selection bypass")
        actual = {"authored": text_cost((ROOT / path).read_text()), "packaged": {form: measure(language.generated(item, form)) for form in FORMS}}
        if write:
            entry["current"] = actual
        elif entry["current"] != actual:
            raise ValueError(f"stale source cost: {path}")
    ids = set()
    with tempfile.TemporaryDirectory() as tmp:
        base_dir = Path(tmp)
        archive = base_dir / "base.tar"
        with archive.open("wb") as output:
            subprocess.run(["git", "-C", str(ROOT), "archive", BASE], stdout=output, check=True, timeout=30)
        subprocess.run(["tar", "-xf", str(archive), "-C", str(base_dir)], check=True, timeout=30)
        archive.unlink()
        subprocess.run([sys.executable, str(base_dir / "bin/build.py")], cwd=base_dir,
                       capture_output=True, text=True, check=True, timeout=90)
        old_inv = {i["source_path"]: i for i in json.loads((base_dir / "catalog/skills-inventory.json").read_text())["items"]}
        for entry in ledger["items"]:
            old = old_inv[entry["source"]]
            for form in FORMS:
                current_path = language.generated(old, form).relative_to(ROOT)
                if entry["baseline"]["packaged"][form] != measure(base_dir / current_path):
                    raise ValueError(f"wrong isolated exact-base package cost: {form}/{entry['source']}")
        for fixture in fixture_data["fixtures"]:
            if fixture["id"] in ids:
                raise ValueError("duplicate data fixture")
            ids.add(fixture["id"])
            for base_form in CONSUMERS:
                old_script = base_dir / ("bin/resolve-load-set.py" if base_form == "source" else f"dist/{base_form}/bin/resolve-load-set.py")
                old_args = [sys.executable, str(old_script), "--prompt", fixture["prompt"], "--repo", fixture["repo"]]
                original = json.loads(subprocess.check_output(old_args, text=True, timeout=20))
                expected = {"state": original["state"], "slugs": [s["slug"] for s in original["selected"]], "selected_content": original.get("selected_content", {})}
                if fixture["baseline_load_effect"][base_form] != expected:
                    raise ValueError(f"wrong isolated exact-base fixture evidence: {base_form}/{fixture['id']}")
            measurements = {}
            selected_bytes = {}
            for form in ALL_CONSUMERS:
                result = resolved(form, fixture)
                slugs = [s["slug"] for s in result["selected"]]
                paths = [s["source_path"] for s in result["selected"]]
                if (result["state"], slugs, paths) != (fixture["state"], fixture["slugs"], fixture["source_paths"]):
                    raise ValueError(f"wrong route: {form}/{fixture['id']}: {result['state']} {slugs} {paths}")
                content = result.get("selected_content", {})
                if result["state"] == "matched" and (content["items"] > 12 or content["characters"] > 80000 or content["estimated_tokens"] > 20000):
                    raise ValueError(f"budget bypass: {form}/{fixture['id']}")
                if result["state"] in ("unknown", "ambiguous", "over-budget") and result["selected"]:
                    raise ValueError(f"non-kernel fallback: {form}/{fixture['id']}")
                selected_byte_count = 0
                for selected in result["selected"]:
                    source = selected["source_path"]
                    target = ROOT / source if form == "source" else ROOT / f"dist/{form}" / packages[form]["known_by_source"][source]["package_path"]
                    selected_byte_count += len(target.read_bytes())
                    if source.startswith("projects/") and result["project"] != "siege-utilities":
                        raise ValueError(f"foreign project leak: {form}/{fixture['id']}")
                    if form != "source":
                        meta = packages[form]["known_by_source"][source]
                        actual = cost(len((ROOT / f"dist/{form}" / meta["package_path"]).read_text()))
                        if actual != {key: meta[key] for key in ("characters", "estimated_tokens")}:
                            raise ValueError(f"selected byte mismatch: {form}/{source}")
                if form in CONSUMERS:
                    selected_bytes[form] = selected_byte_count
                    measurements[form] = content
            if write:
                fixture["measurements"] = measurements
                fixture["selected_bytes"] = selected_bytes
            elif fixture["measurements"] != measurements or fixture["selected_bytes"] != selected_bytes:
                raise ValueError(f"stale selected-content/byte cost: {fixture['id']}")
    required_ids = {"etl", "analysis", "catalog-raw-write", "catalog-insert-into", "catalog-insert-bare", "negative-postgres-insert", "negative-csv-write", "catalog-crd-delta", "catalog-crd-parquet", "negative-crd-csv", "negative-unrelated-readme", "negative-inherited-doc-leak", "concrete-edit-catalog", "concrete-edit-postgis", "scala", "scala-negative", "postgis", "geopandas", "sedona", "duckdb", "duckdb-extension", "foreign-postgis", "exact-postgis", "multi", "over-budget", "ambiguous", "unknown", "arcgis", "visualization", "read-only", "multiline-postgis", "multiline-sedona", "negative-duckdb-docs", "negative-viz-geometry", "negative-how-do-i", "analyze-postgis"}
    if not required_ids <= ids:
        raise ValueError(f"missing boundary fixtures: {sorted(required_ids - ids)}")
    if write:
        LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
        FIXTURES.write_text(json.dumps(fixture_data, indent=2) + "\n")
    print(f"data scope: {len(ledger['items'])} dispositions, {len(ids)} source/Claude/Craft fixtures current")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    try:
        compute(args.write)
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"DATA SCOPE ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
