#!/usr/bin/env python3
"""Generate/check deterministic progressive-loading size and load-set metrics."""
from __future__ import annotations
import argparse,hashlib,json,os,stat,subprocess,sys,tempfile
from contextlib import contextmanager
from pathlib import PurePosixPath
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=Path("catalog/progressive-loading-metrics.json")
def run(prompt:str,repo:str="other/repo")->dict:
 p=subprocess.run([sys.executable,"-I","-B",str(ROOT/"bin/resolve-load-set.py"),"--prompt",prompt,"--repo",repo],text=True,capture_output=True,timeout=20)
 if p.returncode:raise ValueError(p.stderr or p.stdout)
 return json.loads(p.stdout)
def reference_bytes(source:Path)->bytes:
 fd=os.open(source,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
 with os.fdopen(fd,"rb") as stream:
  if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):raise ValueError("reference source is not a regular file")
  raw=stream.read(16*1024*1024+1)
 if len(raw)>16*1024*1024:raise ValueError("reference source exceeds copy byte budget")
 return raw
@contextmanager
def reference_package(fixtures:dict):
 # A fixed-length physical root makes the real byte cap deterministic before
 # any display normalization. Never copy arbitrary bin/ shadow modules.
 with tempfile.TemporaryDirectory(prefix="plm-",dir="/tmp") as temporary:
  parent=Path(temporary).resolve()
  padding=32-len(str(parent).encode("utf-8"))-1
  if padding<1:raise ValueError("private metrics reference parent is too long")
  reference=parent/("r"*padding);reference.mkdir()
  fixed={"bin/resolve-load-set.py","hooks/resolver/inject-resolver.sh","skills/KERNEL.md","catalog/resolver-manifest.json","catalog/skills-inventory.json"}
  inventory=json.loads(reference_bytes(ROOT/"catalog/skills-inventory.json"))
  sources={item["canonical_source"]:item for item in inventory["items"]}
  for fixture in fixtures.values():
   for item in fixture["selected"]:
    relative=item.get("load_path",item.get("source_path"))
    if relative!=item.get("source_path") or relative not in sources:raise ValueError("metric fixture is not canonical source data")
    fixed.add(relative)
  for relative in sorted(fixed):
   path=PurePosixPath(relative)
   if path.is_absolute() or ".." in path.parts or str(path)!=relative:raise ValueError("invalid reference path")
   source=ROOT
   for part in path.parts:
    source=source/part
    if source.is_symlink():raise ValueError("reference source contains symlink")
   raw=reference_bytes(source)
   if relative in sources and hashlib.sha256(raw).hexdigest()!=sources[relative]["content_sha256"]:raise ValueError("stale canonical source digest")
   destination=reference/relative;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
  (reference/"empty-cwd").mkdir();(reference/"empty-plans").mkdir()
  yield reference

def inject(prompt:str,reference:Path)->int:
 environment={key:value for key,value in os.environ.items() if not key.startswith("GIT_") and key not in {"CLAUDE_KERNEL_PATH","CLAUDE_PROGRESSIVE_LOADING","PYTHONPATH","PYTHONHOME"}}
 environment.update(CRAFT_AGENT_PLANS_PATH=str(reference/"empty-plans"),CLAUDE_PROGRESSIVE_LOADING="on",PYTHONDONTWRITEBYTECODE="1")
 p=subprocess.run(["bash",str(reference/"hooks/resolver/inject-resolver.sh")],input=json.dumps({"prompt":prompt,"cwd":str(reference/"empty-cwd")}),text=True,capture_output=True,timeout=20,cwd=reference/"empty-cwd",env=environment)
 if p.returncode:raise ValueError(p.stderr)
 rendered=p.stdout.replace(f"| path={reference}/","| path=<installation-root>/")
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
 with reference_package(fixtures) as reference:
  injected={
   "generic":inject("write a friendly greeting",reference),
   "python_review":inject("review this Python diff",reference),
   "multi_route":inject(multi_prompt,reference),
   "explicit_overflow":inject(overflow_prompt,reference)}
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
