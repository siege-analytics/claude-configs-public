#!/usr/bin/env python3
"""Generate/check deterministic progressive-loading size and load-set metrics."""
from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=Path("catalog/progressive-loading-metrics.json")
def run(prompt:str,repo:str="other/repo")->dict:
 p=subprocess.run([sys.executable,str(ROOT/"bin/resolve-load-set.py"),"--prompt",prompt,"--repo",repo],text=True,capture_output=True,timeout=20)
 if p.returncode:raise ValueError(p.stderr or p.stdout)
 return json.loads(p.stdout)
def inject(prompt:str)->int:
 p=subprocess.run(["bash",str(ROOT/"hooks/resolver/inject-resolver.sh")],input=json.dumps({"prompt":prompt,"cwd":"/tmp"}),text=True,capture_output=True,timeout=20,env={**os.environ,"CRAFT_AGENT_PLANS_PATH":"/nonexistent"})
 if p.returncode:raise ValueError(p.stderr)
 # Hooks emit absolute, installation-root-correct paths. Normalize only that
 # variable prefix so the tracked metric is reproducible across local clones,
 # CI workspaces, and installed package roots.
 rendered=p.stdout.replace(f"| path={ROOT.resolve()}/","| path=<installation-root>/")
 return len(rendered)
def build()->dict:
 overflow_prompt=" ".join(f"[skill:{slug}]" for slug in ["branch","commit","create-pr","merge","code-review","skillbuilder","ticket-guard","create-ticket","spatial","coding","python","testing-frameworks","sql"])
 multi_prompt="review Python Spark SQL Databricks Unity Catalog spatial PostGIS code"
 fixtures={
  "generic":run("write a friendly greeting"),
  "python_review":run("review this Python diff"),
  "multi_route":run(multi_prompt),
  "explicit_overflow":run(overflow_prompt),
  "siege_utilities_review":run("review this diff","github.com/siege-analytics/siege_utilities")}
 counts={k:len(v["selected"]) for k,v in fixtures.items()}
 selected_content={k:v.get("selected_content",{}) for k,v in fixtures.items()}
 injected={
  "generic":inject("write a friendly greeting"),
  "python_review":inject("review this Python diff"),
  "multi_route":inject(multi_prompt),
  "explicit_overflow":inject(overflow_prompt)}
 legacy_root=len((ROOT/"RESOLVER.md").read_text()); skill_resolver=len((ROOT/"skills/RESOLVER.md").read_text()); kernel=len((ROOT/"skills/KERNEL.md").read_text())
 rules=len((ROOT/"dist/RULES_BUNDLE.md").read_text()) if (ROOT/"dist/RULES_BUNDLE.md").is_file() else 0
 if max(injected.values())>=10000:raise ValueError(f"progressive injection exceeds the 10k inline limit: {injected}")
 if counts["generic"]!=0:raise ValueError("generic fixture must remain kernel-only")
 if fixtures["explicit_overflow"]["state"]!="over-budget" or counts["explicit_overflow"]!=0:raise ValueError("explicit overflow must reject the entire load set")
 return {"schema_version":1,"characters":{"legacy_root_resolver":legacy_root,"legacy_rules_bundle":rules,"skill_resolver":skill_resolver,"kernel":kernel,"injected":injected},"selection_limits":{"items":12,"characters":80000,"estimated_tokens":20000},"fixture_selected_counts":counts,"fixture_selected_content":selected_content,"fixture_states":{k:v["state"] for k,v in fixtures.items()}}
def serial(x):return json.dumps(x,indent=2,sort_keys=True)+"\n"
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");p.add_argument("--output",type=Path,default=OUT);a=p.parse_args();path=a.output if a.output.is_absolute() else ROOT/a.output
 try:expected=serial(build())
 except (OSError,ValueError,subprocess.SubprocessError,json.JSONDecodeError) as e:print(f"PROGRESSIVE METRICS ERROR: {e}",file=sys.stderr);return 1
 if a.check:
  if not path.is_file() or path.read_text()!=expected:print("STALE progressive loading metrics",file=sys.stderr);return 1
  d=json.loads(expected);print(f"progressive loading: current (max injection {max(d['characters']['injected'].values())} chars)");return 0
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(expected);print(f"wrote {path.relative_to(ROOT)}");return 0
if __name__=="__main__":raise SystemExit(main())
