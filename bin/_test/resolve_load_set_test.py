#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; SCRIPT=ROOT/"bin/resolve-load-set.py"
SPEC=importlib.util.spec_from_file_location("resolver",SCRIPT); assert SPEC and SPEC.loader
M=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=M;SPEC.loader.exec_module(M)
def inv():
 def i(s,k="skill"):return {"slug":s,"kind":k,"characters":100,"estimated_tokens":25}
 slugs=["branch","commit","create-pr","merge","code-review","skillbuilder","ticket-guard","create-ticket","update-ticket","close-ticket","ci-billing-failure-merge","coding","python","testing-frameworks","test-coverage-audit","sql","spatial","spark","databricks","unity-catalog","django","django-rest-framework","react","typescript","vue","rust","stalled-session-recovery","develop-guard","siege-utilities--hostile-review","siege-utilities--notebook-impact","siege-utilities--error-path-tests"]
 return {"items":[i(s,"project-skill" if s.startswith("siege-utilities--") else "skill") for s in slugs]+[i("siege-utilities--rules","project-rule"),i("shelves--security","shelf-item")]}
def main():
 manifest=json.loads((ROOT/"catalog/resolver-manifest.json").read_text()); inventory=inv()
 a=M.select(manifest,inventory,"review this Python pull request", "github.com/siege-analytics/siege_utilities")
 slugs=[x["slug"] for x in a["selected"]]
 assert a["state"]=="matched" and slugs[0]=="siege-utilities--rules"
 assert "siege-utilities--hostile-review" in slugs and "coding" in slugs
 assert a==M.select(manifest,inventory,"review this Python pull request", "github.com/siege-analytics/siege_utilities")
 generic=M.select(manifest,inventory,"write a friendly greeting","other/repo")
 assert generic["state"]=="unknown" and generic["selected"]==[] and generic["project"] is None
 outside=M.select(manifest,inventory,"review this diff","other/repo")
 assert not any(x["slug"].startswith("siege-utilities--") for x in outside["selected"])
 explicit=M.select(manifest,inventory,"create ticket [skill:python]","other/repo")
 explicit_slugs=[x["slug"] for x in explicit["selected"]]
 assert "python" in explicit_slugs and "ticket-guard" in explicit_slugs and "create-ticket" in explicit_slugs
 # Every ticket action loads only its guard + corresponding action, including aliases.
 for action,terms in {
  "create-ticket":["create ticket","create issues","file an issue","open a ticket","[skill:create-ticket]","/create-ticket"],
  "update-ticket":["update ticket","update issues","edit issue","[skill:update-ticket]","/update-ticket"],
  "close-ticket":["close ticket","close issues","mark issue closed","[skill:close-ticket]","/close-ticket"],
 }.items():
  for term in terms:
   result=M.select(manifest,inventory,term,"other/repo")
   got={x["slug"] for x in result["selected"]}
   assert result["state"]=="matched" and got=={"ticket-guard",action},(term,result)
 assert any(x["route"]=="ticketing" for x in M.select(manifest,inventory,"create issue","other/repo")["selected"])
 for prompt in ("list open issues","are there any open issues","what is the new issue about"):
  result=M.select(manifest,inventory,prompt,"other/repo")
  assert result["state"]=="unknown" and result["selected"]==[],(prompt,result)
 coding_only=M.select(manifest,inventory,"resolve issue handling in this python module","other/repo")
 assert {x["slug"] for x in coding_only["selected"]}=={"coding","python"},coding_only
 for term in ("create ticket and close issue","update issue then close ticket","create issue [skill:close-ticket]","[skill:create-ticket] /update-ticket"):
  result=M.select(manifest,inventory,term,"other/repo")
  assert result["state"]=="ambiguous" and result["selected"]==[],(term,result)
 for repo in ("other/repo","git@other-host:electinfo/enterprise.git","github.com/electinfo/enterprise"):
  result=M.select(manifest,inventory,"[skill:ci-billing-failure-merge]",repo)
  assert result["state"]=="matched" and "diagnostic-only (no merge authorization)" in result["diagnostic"]
  assert {x["slug"] for x in result["selected"]}=={"ci-billing-failure-merge"}
 project_explicit=M.select(manifest,inventory,"[skill:siege-utilities--hostile-review]","github.com/siege-analytics/siege_utilities")
 assert "siege-utilities--hostile-review" in [x["slug"] for x in project_explicit["selected"]]
 foreign_project_explicit=M.select(manifest,inventory,"[skill:siege-utilities--hostile-review] /siege-utilities--rules","git@other-host:siege-analytics/siege_utilities.git")
 assert not any(x["slug"].startswith("siege-utilities--") for x in foreign_project_explicit["selected"])
 assert "siege-utilities--hostile-review" in foreign_project_explicit["diagnostic"] and "siege-utilities--rules" in foreign_project_explicit["diagnostic"]
 path_prompt=M.select(manifest,inventory,"inspect /tmp/python then create ticket","other/repo")
 path_slugs=[x["slug"] for x in path_prompt["selected"]]
 assert "ticket-guard" in path_slugs
 assert not any(x["route"]=="explicit" for x in path_prompt["selected"])
 shelf=M.select(manifest,inventory,"Use [skill:shelves--security]","other/repo")
 assert shelf["state"]=="unknown" and shelf["selected"]==[] and "rejected explicit" in shelf["diagnostic"]
 unknown_explicit=M.select(manifest,inventory,"create ticket [skill:not-real]","other/repo")
 assert "ticket-guard" in [x["slug"] for x in unknown_explicit["selected"]]
 assert "not-real" in unknown_explicit["diagnostic"]
 many_slugs=[x["slug"] for x in inventory["items"] if x["kind"]=="skill" and x["slug"] not in {"update-ticket","close-ticket"}][:13]
 over_count=M.select(manifest,inventory," ".join(f"[skill:{slug}]" for slug in many_slugs),"other/repo")
 assert over_count["state"]=="over-budget" and over_count["selected"]==[] and over_count["selected_content"]["items"]>12
 huge=json.loads(json.dumps(inventory))
 next(x for x in huge["items"] if x["slug"]=="python")["characters"]=90000
 next(x for x in huge["items"] if x["slug"]=="python")["estimated_tokens"]=22500
 over_content=M.select(manifest,huge,"[skill:python]","other/repo")
 assert over_content["state"]=="over-budget" and over_content["selected"]==[] and "kernel only" in over_content["diagnostic"]
 bad=json.loads(json.dumps(manifest));bad["routes"][0]["skills"]=["missing"]
 try:M.select(bad,inventory,"create branch","other/repo")
 except ValueError as e:assert "unknown slug" in str(e)
 else:raise AssertionError("unknown manifest slug passed")
 bad=json.loads(json.dumps(manifest));bad["routes"][0]["skills"]=["shelves--security"]
 try:M.select(bad,inventory,"create branch","other/repo")
 except ValueError as e:assert "shelf cannot auto-select" in str(e)
 else:raise AssertionError("shelf route passed")
 bad=json.loads(json.dumps(manifest));bad["projects"][0]["always"]=["shelves--security"]
 try:M.select(bad,inventory,"review this diff","github.com/siege-analytics/siege_utilities")
 except ValueError as e:assert "shelf cannot auto-select" in str(e)
 else:raise AssertionError("project always shelf passed")
 ambiguous=json.loads(json.dumps(manifest));ambiguous["routes"]=[
  {"id":"a","priority":1,"terms":["build"],"skills":["coding"],"exclusive_group":"mode"},
  {"id":"b","priority":1,"terms":["build"],"skills":["python"],"exclusive_group":"mode"}]
 ambiguous["projects"]=[]
 result=M.select(ambiguous,inventory,"build this","other/repo")
 assert result["state"]=="ambiguous" and result["selected"]==[]
 assert M.select(manifest,inventory,"[skill:shelves--security]", "other/repo")["selected"]==[]
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
