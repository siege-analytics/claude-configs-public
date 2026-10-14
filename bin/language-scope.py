#!/usr/bin/env python3
"""Check curated #975 dispositions and measured source/consumer load fixtures.

Build dist and regenerate inventory/authority before checking. --write refreshes
costs, never classifications, consumers, prompts or expected routes. No args
checks without writing. Exact-base authored costs and source load fixtures are
verified from git; packaged baseline costs are attested isolated-build evidence.
Unknown consumers stay UNKNOWN: inbound text references are not runtime identity.
"""
from __future__ import annotations
import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "catalog/language-scope-ledger.json"
FIXTURES = ROOT / "catalog/language-scope-fixtures.json"
FORMS = ("nested", "flat", "claude-code", "craft-agent")
VALID = {"reusable-global", "exact-project", "reference-only", "compatibility"}
EXACT = "github.com/siege-analytics/siege_utilities"
BASE = "b9b631988091fcabdc1c531087da57c5ca1a0419"
LANGUAGE = {"coding", "django", "django-rest-framework", "python", "python-exceptions", "python-patterns", "qml-component-review", "react", "scala-on-spark", "spark", "vue", "spatial", "geopandas", "postgis", "sedona", "duckdb-spatial", "sql"}
RULES = {"django-rest-framework", "jvm", "python", "react", "rust", "siege-utilities", "typescript"}


def base_file(path: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "show", f"{BASE}:{path}"], text=True, timeout=15)



def cost(characters: int) -> dict:
    return {"characters": characters, "estimated_tokens": math.ceil(characters / 4)}


def measure(path: Path) -> dict:
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"missing generated output: {path}")
    return cost(sum(len(p.read_text()) for p in files))


def generated(item: dict, form: str) -> Path:
    prefix = "nested" if form == "nested" else "flat"
    candidate = next((s for s in item["generated_outputs"] if s.startswith(f"dist/{prefix}/skills/")), None)
    if candidate is None:
        raise ValueError(f"missing {form} destination for {item['slug']}")
    if form not in ("nested", "flat"):
        candidate = candidate.replace("dist/flat/", f"dist/{form}/", 1)
    return ROOT / candidate


def resolved(form: str, fixture: dict) -> dict:
    script = ROOT / ("bin/resolve-load-set.py" if form == "source" else f"dist/{form}/bin/resolve-load-set.py")
    proc = subprocess.run([sys.executable, str(script), "--prompt", fixture["prompt"], "--repo", fixture["repo"]], capture_output=True, text=True, timeout=20)
    if proc.returncode:
        raise ValueError(f"resolver failed for {form}/{fixture['id']}: {proc.stderr or proc.stdout}")
    return json.loads(proc.stdout)


def compute(write: bool) -> None:
    ledger = json.loads(LEDGER.read_text())
    fixtures = json.loads(FIXTURES.read_text())
    inv = {i["source_path"]: i for i in json.loads((ROOT / "catalog/skills-inventory.json").read_text())["items"]}
    manifest = json.loads((ROOT / "catalog/resolver-manifest.json").read_text())
    routes = {s for route in manifest["routes"] for s in route["skills"]}
    required = {path for path in inv if path.startswith("skills/shelves/languages/") or
                path.startswith("projects/siege-utilities/") and (path.endswith("SKILL.md") or path.endswith("_rules.md")) or
                path in {f"skills/{name}/SKILL.md" for name in LANGUAGE} or
                path in {f"skills/_{name}-rules.md" for name in RULES}}
    recorded = {i["source"] for i in ledger["items"]}
    if recorded != required:
        raise ValueError(f"incomplete ledger: missing={sorted(required - recorded)}, extra={sorted(recorded - required)}")
    source_known = {i["slug"]: i for i in json.loads((ROOT / "catalog/skills-inventory.json").read_text())["items"]}
    consumer_known = {form: json.loads((ROOT / f"dist/{form}/catalog/resolver-manifest.json").read_text())["known"] for form in ("claude-code", "craft-agent")}
    for slug in routes:
        origins = {source_known[slug]["source_path"]} | {consumer_known[form][slug]["source_path"] for form in consumer_known}
        if len(origins) != 1:
            raise ValueError(f"source/consumer route identity mismatch: {slug}: {origins}")
    packaged_known = consumer_known["claude-code"]
    # Skill and rule namespaces can share slugs; only the manifest's resolved
    # source is routed (e.g. python skill, not the namesake python rule).
    routed_sources = {packaged_known[slug]["source_path"] for slug in routes}
    project = manifest["projects"]
    if len(project) != 1 or project[0]["repos"] != [EXACT]:
        raise ValueError("only verified exact GitHub project identity may activate overlay")
    if (ledger["base_sha"] != BASE
            or len(ledger["items"]) != len({i["source"] for i in ledger["items"]})):
        raise ValueError("invalid base or duplicate ledger source")
    for entry in ledger["items"]:
        if set(entry.get("baseline", {}).get("packaged", {})) != set(FORMS):
            raise ValueError(f"missing exact-base packaged evidence: {entry['source']}")
        path = entry["source"]
        if entry["baseline"]["authored"] != cost(len(base_file(path))):
            raise ValueError(f"invalid exact-base authored cost: {path}")
        item = inv[path]
        text = (ROOT / path).read_text()
        frontmatter = text.split("---", 2)[1] if text.startswith("---\n") else ""
        if "\npaths:" in frontmatter:
            raise ValueError(f"native path auto-activation bypasses resolver scope/budgets: {path}")
        classification = entry["classification"]
        if classification not in VALID or entry["slug"] != item["slug"] or entry["kind"] != item["kind"]:
            raise ValueError(f"invalid disposition: {path}")
        if classification == "exact-project":
            if not path.startswith("projects/siege-utilities/") or entry["known_consumers"] != [EXACT] or entry["auto_select"] != "exact-project":
                raise ValueError(f"invalid project scope: {path}")
        elif entry["known_consumers"] != "UNKNOWN" or not entry["consumer_evidence"].startswith("UNKNOWN:"):
            raise ValueError(f"unproven consumer identity: {path}")
        if classification == "reference-only" and (not item["kind"].startswith(("shelf", "reference-shelf")) or path in routed_sources):
            raise ValueError(f"reference shelf must remain isolated: {path}")
        if classification == "compatibility" and (path != "skills/_siege-utilities-rules.md" or path in routed_sources):
            raise ValueError(f"compatibility rule routed globally: {path}")
        if path == "skills/qml-component-review/SKILL.md" and path in routed_sources:
            raise ValueError("unknown QML project auto-routed")
        if entry["auto_select"] == "explicit-signal-only" and path not in routed_sources:
            raise ValueError(f"documented signal route absent: {path}")
        if entry["auto_select"] in ("never", "not-routed") and path in routed_sources:
            raise ValueError(f"unapproved global route: {path}")
        actual = {"authored": cost(len((ROOT / path).read_text())),
                  "packaged": {form: measure(generated(item, form)) for form in FORMS}}
        if write:
            entry["current"] = actual
        elif entry["current"] != actual:
            raise ValueError(f"stale authored/packaged measurement: {path}")
        for form in ("claude-code", "craft-agent"):
            packaged_manifest = json.loads((ROOT / f"dist/{form}/catalog/resolver-manifest.json").read_text())
            meta = packaged_manifest["known"][entry["slug"]]
            if meta["source_path"] != path:
                if entry["auto_select"] == "explicit-signal-only":
                    raise ValueError(f"route resolves to another source: {form}/{path}")
                continue
            file_cost = cost(len((ROOT / f"dist/{form}" / meta["package_path"]).read_text()))
            if file_cost != {key: meta[key] for key in ("characters", "estimated_tokens")}:
                raise ValueError(f"stale packaged resolver cost: {form}/{path}")
    ids = set()
    with tempfile.TemporaryDirectory() as raw:
        base_dir = Path(raw)
        for name, source in (("resolver.py", "bin/resolve-load-set.py"), ("manifest.json", "catalog/resolver-manifest.json"), ("inventory.json", "catalog/skills-inventory.json")):
            (base_dir / name).write_text(base_file(source))
        for fixture in fixtures["fixtures"]:
            expected = fixture.get("baseline_load_effect", {}).get("source")
            args = [sys.executable, str(base_dir / "resolver.py"), "--manifest", str(base_dir / "manifest.json"), "--inventory", str(base_dir / "inventory.json"), "--prompt", fixture["prompt"], "--repo", fixture["repo"]]
            result = json.loads(subprocess.check_output(args, text=True, timeout=20))
            baseline = {"state": result["state"], "slugs": [s["slug"] for s in result["selected"]], "selected_content": result.get("selected_content", {})}
            if baseline != expected:
                raise ValueError(f"invalid exact-base source load evidence: {fixture['id']}")
    for fixture in fixtures["fixtures"]:
        if fixture["id"] in ids:
            raise ValueError("duplicate fixture")
        ids.add(fixture["id"])
        measurements = {}
        if set(fixture.get("baseline_load_effect", {})) != {"source", "claude-code", "craft-agent"}:
            raise ValueError(f"missing exact-base source/consumer load evidence: {fixture['id']}")
        for form in ("source", "claude-code", "craft-agent"):
            result = resolved(form, fixture)
            slugs = [s["slug"] for s in result["selected"]]
            if result["state"] != fixture["state"] or slugs != fixture["slugs"]:
                raise ValueError(f"unexpected {form}/{fixture['id']}: {result['state']} {slugs}")
            content = result.get("selected_content", cost(0) | {"items": 0})
            if content.get("items", 0) > 12 and result["state"] != "over-budget":
                raise ValueError(f"item budget exceeded: {form}/{fixture['id']}")
            if result["state"] == "matched" and (content["characters"] > 80000 or content["estimated_tokens"] > 20000):
                raise ValueError(f"content budget exceeded: {form}/{fixture['id']}")
            measurements[form] = content
        if write:
            fixture["measurements"] = measurements
        elif fixture.get("measurements") != measurements:
            raise ValueError(f"stale fixture load effect: {fixture['id']}")
    if write:
        LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
        FIXTURES.write_text(json.dumps(fixtures, indent=2) + "\n")
    print(f"language scope: {len(ledger['items'])} dispositions, {len(ids)} source/consumer fixtures current")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify (default)")
    mode.add_argument("--write", action="store_true", help="refresh current measurements")
    args = parser.parse_args()
    try:
        compute(write=args.write)
    except (OSError, KeyError, TypeError, ValueError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(f"LANGUAGE SCOPE ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
