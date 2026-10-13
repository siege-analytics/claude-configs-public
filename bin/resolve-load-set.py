#!/usr/bin/env python3
"""Deterministically select task/project skills from the compact resolver manifest."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
SHELF_PREFIX="shelves"

def norm_repo(value:str)->str:
    value=value.strip().removesuffix(".git").replace("\\","/")
    match=re.match(r"^[a-z]+://([^/]+)/(.+)$",value,re.IGNORECASE)
    if match:value=f"{match.group(1).rsplit('@',1)[-1]}/{match.group(2)}"
    else:
        match=re.match(r"^[^@]+@([^:]+):(.+)$",value)
        if match:value=f"{match.group(1)}/{match.group(2)}"
    value=value.strip("/").lower()
    if value.count("/")==1:value=f"github.com/{value}"
    return value

def detect_repo(cwd:Path)->str:
    try:return norm_repo(subprocess.check_output(["git","-C",str(cwd),"remote","get-url","origin"],text=True,stderr=subprocess.DEVNULL,timeout=5))
    except (OSError,subprocess.SubprocessError):return ""

def token_match(text:str,term:str)->bool:
    return re.search(r"(?<![a-z0-9])"+re.escape(term.lower())+r"(?![a-z0-9])",text) is not None

def route_matches(route:dict[str,Any],text:str)->list[str]:
    reasons=[f"term:{t}" for t in route.get("terms",[]) if token_match(text,t)]
    reasons += [f"suffix:{s}" for s in route.get("suffixes",[]) if re.search(re.escape(s.lower())+r"(?:\b|$)",text)]
    return reasons

def validate_manifest(manifest:dict[str,Any],known:dict[str,Any])->None:
    ids=[]; repos=[]
    all_routes=list(manifest.get("routes",[]))
    for project in manifest.get("projects",[]):
        repos.extend(norm_repo(r) for r in project.get("repos",[]));all_routes.extend(project.get("routes",[]))
        for slug in project.get("always",[]):
            if slug not in known:raise ValueError(f"manifest references unknown slug: {slug}")
    for route in all_routes:
        ids.append(route["id"])
        if not route.get("terms") and not route.get("suffixes"):raise ValueError(f"route has no signals: {route['id']}")
        for slug in route["skills"]:
            if slug not in known:raise ValueError(f"manifest references unknown slug: {slug}")
            if known[slug]["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX):raise ValueError(f"shelf cannot auto-select: {slug}")
    if len(ids)!=len(set(ids)):raise ValueError("resolver route IDs must be unique")
    if len(repos)!=len(set(repos)):raise ValueError("project repository identities must be unique")

def select(manifest:dict[str,Any],inventory:dict[str,Any],prompt:str,repo:str="")->dict[str,Any]:
    known={i["slug"]:i for i in inventory["items"]};validate_manifest(manifest,known)
    text=" ".join(prompt.lower().split()); matches=[];matched_routes=[]
    explicit_slugs=sorted(set(re.findall(r"\[skill:([a-z0-9-]+)\]",text)+re.findall(r"(?<!\S)/([a-z0-9-]+)(?!\S)",text)))
    rejected_explicit=[]
    for slug in explicit_slugs:
        if slug in known and not slug.startswith(SHELF_PREFIX) and not known[slug]["kind"].startswith("shelf"):
            matches.append((1000,"explicit",slug,["explicit-slug"]))
        else:
            rejected_explicit.append(slug)
    for route in manifest["routes"]:
        why=route_matches(route,text)
        if why:
            matched_routes.append(route)
            for slug in route["skills"]: matches.append((route["priority"],route["id"],slug,why))
    project_id=None
    for project in manifest.get("projects",[]):
        if norm_repo(repo) in {norm_repo(r) for r in project["repos"]}:
            project_id=project["id"]
            for slug in project.get("always",[]): matches.append((2000,f"project:{project_id}",slug,[f"repo:{norm_repo(repo)}"]))
            for route in project.get("routes",[]):
                why=route_matches(route,text)
                if why:
                    matched_routes.append(route)
                    for slug in route["skills"]: matches.append((route["priority"],f"project:{project_id}:{route['id']}",slug,why))
    groups={}
    for route in matched_routes:
        if route.get("exclusive_group"):groups.setdefault(route["exclusive_group"],[]).append(route["id"])
    conflicts={group:sorted(ids) for group,ids in groups.items() if len(ids)>1}
    if conflicts:
        return {"schema_version":1,"state":"ambiguous","kernel":manifest["kernel"],"project":project_id,"selected":[],"diagnostic":f"ambiguous routes: {conflicts}"}
    selected={}
    for priority,route,slug,why in sorted(matches,key=lambda x:(-x[0],x[1],x[2])):
        if slug not in known: raise ValueError(f"manifest references unknown slug: {slug}")
        if known[slug]["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX): raise ValueError(f"shelf cannot auto-select: {slug}")
        selected.setdefault(slug,{"slug":slug,"route":route,"priority":priority,"reasons":why})
    state="matched" if selected else "unknown"
    diagnostic="no route matched; kernel only" if state=="unknown" else f"{len(selected)} capability item(s) selected"
    if rejected_explicit:diagnostic+=f"; rejected explicit slugs: {','.join(rejected_explicit)}"
    return {"schema_version":1,"state":state,"kernel":manifest["kernel"],"project":project_id,"selected":list(selected.values()),"diagnostic":diagnostic}

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--prompt",default="");p.add_argument("--cwd",type=Path,default=Path.cwd());p.add_argument("--repo",default="");p.add_argument("--manifest",type=Path,default=ROOT/"catalog/resolver-manifest.json");p.add_argument("--inventory",type=Path,default=ROOT/"catalog/skills-inventory.json");a=p.parse_args()
    try:
        manifest=json.loads(a.manifest.read_text())
        if a.inventory.is_file():
            inventory=json.loads(a.inventory.read_text())
        else:
            inventory={"items":[{"slug":slug,**meta} for slug,meta in manifest.get("known",{}).items()]}
        result=select(manifest,inventory,a.prompt,a.repo or detect_repo(a.cwd))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError,json.JSONDecodeError) as e:
        print(json.dumps({"schema_version":1,"state":"error","kernel":"skills/KERNEL.md","selected":[],"diagnostic":str(e)},sort_keys=True));return 1
    print(json.dumps(result,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
