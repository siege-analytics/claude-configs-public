#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SCRIPT=ROOT/"bin/review-risk.py"
spec=importlib.util.spec_from_file_location("review_risk",SCRIPT);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
policy=json.loads((ROOT/"catalog/review-risk-policy.json").read_text())
def tier(paths):return m.classify(policy,paths)["computed_tier"]
def main():
 assert tier(["README.md","plans/note.md"])=="A"
 assert tier(["catalog/skills-inventory.json"])=="A"
 assert tier(["skills/python/SKILL.md"])=="B"
 assert tier(["src/app.py"])=="B"
 assert tier(["hooks/agent-comms/status.sh"])=="B"
 for path in ["hooks/git/self-review.sh","hooks/resolver/skill-enforcement-gate.sh","hooks/resolver/inject-resolver.sh",".github/workflows/build-and-publish.yml","bin/install.sh","bin/resolve-load-set.py","catalog/review-risk-policy.json","catalog/resolver-manifest.json","auth/token.py","VERSION"]:assert tier([path])=="C",path
 stripped=json.loads(json.dumps(policy));stripped["high_risk_path_patterns"]=[]
 assert m.classify(stripped,["catalog/review-risk-policy.json"])["computed_tier"]=="C"
 assert m.classify(stripped,["bin/review-risk.py"])["computed_tier"]=="C"
 assert tier(["README.md","hooks/git/x.sh"])=="C"
 assert tier(["hooks/git/link","vendor/submodule"])=="C"
 assert tier(["vendor/submodule"])=="B"
 assert tier(["docs/copied-example.md"])=="A"
 low=subprocess.run([sys.executable,str(SCRIPT),"--paths","README.md","hooks/git/x.sh","--declared","B"],text=True,capture_output=True)
 assert low.returncode==2 and not json.loads(low.stdout)["valid"]
 high=subprocess.run([sys.executable,str(SCRIPT),"--paths","README.md","--declared","C"],text=True,capture_output=True)
 assert high.returncode==0 and json.loads(high.stdout)["valid"]
 malformed=policy.copy();malformed["tiers"]={}
 with tempfile.TemporaryDirectory() as raw:
  path=Path(raw)/"bad.json";path.write_text(json.dumps(malformed))
  bad=subprocess.run([sys.executable,str(SCRIPT),"--policy",str(path),"--paths","README.md"],text=True,capture_output=True)
  assert bad.returncode==2 and not json.loads(bad.stdout)["valid"]
  missing=subprocess.run([sys.executable,str(SCRIPT),"--policy",str(Path(raw)/"missing.json"),"--paths","README.md"],text=True,capture_output=True)
  assert missing.returncode==2 and not json.loads(missing.stdout)["valid"]
 with tempfile.TemporaryDirectory() as raw:
  repo=Path(raw);subprocess.run(["git","init","-q"],cwd=repo,check=True);subprocess.run(["git","config","user.email","test@example.com"],cwd=repo,check=True);subprocess.run(["git","config","user.name","Test"],cwd=repo,check=True)
  (repo/"hooks/git").mkdir(parents=True);(repo/"hooks/git/gate.sh").write_text("guard\n");subprocess.run(["git","add","."],cwd=repo,check=True);subprocess.run(["git","commit","-qm","base"],cwd=repo,check=True)
  root_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip();assert tier(m.changed_paths(repo,commit=root_commit))=="C"
  subprocess.run(["git","mv","hooks/git/gate.sh","README.md"],cwd=repo,check=True)
  assert tier(m.changed_paths(repo,staged=True))=="C"
  subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True);(repo/"hooks/git/gate.sh").unlink();subprocess.run(["git","add","-u"],cwd=repo,check=True)
  assert tier(m.changed_paths(repo,staged=True))=="C"
 print("review_risk_test: PASS")
if __name__=="__main__":main()
