#!/usr/bin/env python3
"""Classify changed paths into non-downgradable proportional review tiers."""
from __future__ import annotations
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ORDER={"A":0,"B":1,"C":2}
# Bootstrap floor is intentionally code-owned, not policy-owned: editing the
# data policy cannot downgrade the mechanisms that define or enforce risk.
BOOTSTRAP_HIGH_RISK=re.compile(r"^(bin/review-risk\.py|catalog/review-risk-policy\.json|\.githooks/commit-msg|hooks/git/(self-review|pre-push-self-review)\.sh)$")

def git(repo:Path,*args:str)->str:
 return subprocess.check_output(["git",*args],cwd=repo,text=True,stderr=subprocess.DEVNULL)

def changed_paths(repo:Path,base:str|None=None,head:str="HEAD",staged:bool=False,commit:str|None=None)->list[str]:
 if staged:out=git(repo,"diff","--cached","--no-renames","--name-only","--diff-filter=ACDMRT")
 elif commit:
  parents=git(repo,"show","-s","--format=%P",commit).split();base_ref=parents[0] if parents else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
  out=git(repo,"diff","--no-renames","--name-only","--diff-filter=ACDMRT",base_ref,commit)
 elif base:out=git(repo,"diff","--no-renames","--name-only","--diff-filter=ACDMRT",base,head)
 else:raise ValueError("one of --staged, --commit, or --base is required")
 return sorted({p.strip() for p in out.splitlines() if p.strip()})

def matches(path:str,patterns:list[str])->str|None:
 return next((pattern for pattern in patterns if re.search(pattern,path,re.IGNORECASE)),None)

def classify(policy:dict,paths:list[str])->dict:
 if not paths:return {"computed_tier":"A","paths":[],"reasons":["empty change set"],"required_evidence":policy["tiers"]["A"]["required_evidence"]}
 reasons=[];tier="A"
 for path in paths:
  if BOOTSTRAP_HIGH_RISK.search(path):tier="C";reasons.append(f"C:{path}:bootstrap review-policy floor")
  elif pattern:=matches(path,policy["high_risk_path_patterns"]):tier="C";reasons.append(f"C:{path}:{pattern}")
  elif matches(path,policy["trivial_generated_paths"]):reasons.append(f"A:{path}:generated evidence")
  elif pattern:=matches(path,policy["standard_path_patterns"]):
   if ORDER[tier]<ORDER["B"]:tier="B"
   reasons.append(f"B:{path}:{pattern}")
  elif pattern:=matches(path,policy["trivial_path_patterns"]):reasons.append(f"A:{path}:{pattern}")
  else:
   if ORDER[tier]<ORDER["B"]:tier="B"
   reasons.append(f"B:{path}:unclassified defaults to standard")
 return {"computed_tier":tier,"paths":paths,"reasons":reasons,"required_evidence":policy["tiers"][tier]["required_evidence"]}

def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--policy",type=Path,default=ROOT/"catalog/review-risk-policy.json");p.add_argument("--repo",type=Path,default=Path.cwd());p.add_argument("--base");p.add_argument("--head",default="HEAD");p.add_argument("--staged",action="store_true");p.add_argument("--commit");p.add_argument("--paths",nargs="*");p.add_argument("--declared",choices=ORDER)
 a=p.parse_args()
 try:
  policy=json.loads(a.policy.read_text());paths=sorted(set(a.paths)) if a.paths is not None else changed_paths(a.repo,a.base,a.head,a.staged,a.commit)
  result=classify(policy,paths);computed=result["computed_tier"];result["declared_tier"]=a.declared
  if a.declared and ORDER[a.declared]<ORDER[computed]:result["valid"]=False;result["diagnostic"]=f"declared Tier {a.declared} cannot downgrade computed Tier {computed}"
  else:result["valid"]=True;result["diagnostic"]=(f"Tier {a.declared} escalation accepted" if a.declared and a.declared!=computed else f"Tier {computed} required")
 except (OSError,subprocess.SubprocessError,ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
  print(json.dumps({"valid":False,"diagnostic":str(e)},sort_keys=True));return 2
 print(json.dumps(result,sort_keys=True));return 0 if result["valid"] else 2
if __name__=="__main__":raise SystemExit(main())
