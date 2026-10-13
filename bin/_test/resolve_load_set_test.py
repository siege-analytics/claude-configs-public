#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; SCRIPT=ROOT/"bin/resolve-load-set.py"
SPEC=importlib.util.spec_from_file_location("resolver",SCRIPT); assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=M;SPEC.loader.exec_module(M)
def inv():
 def i(s,k="skill"):return {"slug":s,"kind":k}
 return {"items":[i(s) for s in ["branch","commit","create-pr","merge","code-review","skillbuilder","ticket-guard","create-ticket","update-ticket","coding","python","testing-frameworks","test-coverage-audit","sql","spatial","spark","databricks","unity-catalog","django","react","stalled-session-recovery","develop-guard","siege-utilities--hostile-review","siege-utilities--notebook-impact","siege-utilities--error-path-tests"]]+[i("siege-utilities--rules","project-rule"),i("shelves--security","shelf-item")]}
def main():
 manifest=json.loads((ROOT/"catalog/resolver-manifest.json").read_text()); inventory=inv()
 a=M.select(manifest,inventory,"review this Python pull request", "siege-analytics/siege_utilities")
 slugs=[x["slug"] for x in a["selected"]]
 assert a["state"]=="matched" and slugs[0]=="siege-utilities--rules"
 assert "siege-utilities--hostile-review" in slugs and "coding" in slugs
 assert a==M.select(manifest,inventory,"review this Python pull request", "siege-analytics/siege_utilities")
 generic=M.select(manifest,inventory,"write a friendly greeting","other/repo")
 assert generic["state"]=="unknown" and generic["selected"]==[] and generic["project"] is None
 outside=M.select(manifest,inventory,"review this diff","other/repo")
 assert not any(x["slug"].startswith("siege-utilities--") for x in outside["selected"])
 explicit=M.select(manifest,inventory,"create ticket [skill:python]","other/repo")
 explicit_slugs=[x["slug"] for x in explicit["selected"]]
 assert "python" in explicit_slugs and "ticket-guard" in explicit_slugs and "create-ticket" in explicit_slugs
 path_prompt=M.select(manifest,inventory,"inspect /tmp/python then create ticket","other/repo")
 path_slugs=[x["slug"] for x in path_prompt["selected"]]
 assert "ticket-guard" in path_slugs
 assert not any(x["route"]=="explicit" for x in path_prompt["selected"])
 shelf=M.select(manifest,inventory,"Use [skill:shelves--security]","other/repo")
 assert shelf["state"]=="unknown" and shelf["selected"]==[] and "rejected explicit" in shelf["diagnostic"]
 unknown_explicit=M.select(manifest,inventory,"create ticket [skill:not-real]","other/repo")
 assert "ticket-guard" in [x["slug"] for x in unknown_explicit["selected"]]
 assert "not-real" in unknown_explicit["diagnostic"]
 bad=json.loads(json.dumps(manifest));bad["routes"][0]["skills"]=["missing"]
 try:M.select(bad,inventory,"create branch","other/repo")
 except ValueError as e:assert "unknown slug" in str(e)
 else:raise AssertionError("unknown manifest slug passed")
 bad=json.loads(json.dumps(manifest));bad["routes"][0]["skills"]=["shelves--security"]
 try:M.select(bad,inventory,"create branch","other/repo")
 except ValueError as e:assert "shelf cannot auto-select" in str(e)
 else:raise AssertionError("shelf route passed")
 ambiguous=json.loads(json.dumps(manifest));ambiguous["routes"]=[
  {"id":"a","priority":1,"terms":["build"],"skills":["coding"],"exclusive_group":"mode"},
  {"id":"b","priority":1,"terms":["build"],"skills":["python"],"exclusive_group":"mode"}]
 ambiguous["projects"]=[]
 result=M.select(ambiguous,inventory,"build this","other/repo")
 assert result["state"]=="ambiguous" and result["selected"]==[]
 assert M.norm_repo("git@github.com:Siege-Analytics/siege_utilities.git")=="github.com/siege-analytics/siege_utilities"
 assert M.norm_repo("https://github.com/siege-analytics/siege_utilities.git")=="github.com/siege-analytics/siege_utilities"
 assert M.norm_repo("ssh://git@github.com/siege-analytics/siege_utilities.git")=="github.com/siege-analytics/siege_utilities"
 spoofed=M.select(manifest,inventory,"review this diff","git@other-host:siege-analytics/siege_utilities.git")
 assert spoofed["project"] is None and not any(x["slug"].startswith("siege-utilities--") for x in spoofed["selected"])
 with tempfile.TemporaryDirectory() as raw:
  malformed=Path(raw)/"manifest.json";malformed.write_text('{"routes":null}')
  proc=subprocess.run([sys.executable,str(SCRIPT),"--manifest",str(malformed)],text=True,capture_output=True)
  assert proc.returncode==1 and json.loads(proc.stdout)["state"]=="error" and not proc.stderr
 print("resolve_load_set_test: PASS")
if __name__=="__main__":main()
