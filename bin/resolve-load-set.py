#!/usr/bin/env python3
"""Deterministically select task/project skills from the compact resolver manifest."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
SHELF_PREFIX="shelves"
TICKET_ACTIONS={"create-ticket","update-ticket","close-ticket"}
# This legacy slug is diagnostic-only until an exact project policy exists.
DIAGNOSTIC_ONLY={"ci-billing-failure-merge"}
MAX_SELECTED_ITEMS=12
MAX_SELECTED_CHARACTERS=80000
MAX_SELECTED_ESTIMATED_TOKENS=20000

def norm_repo(value:str)->str:
    value=value.strip().removesuffix(".git").replace("\\","/")
    match=re.match(r"^[a-z]+://([^/]+)/(.+)$",value,re.IGNORECASE)
    if match:value=f"{match.group(1).rsplit('@',1)[-1]}/{match.group(2)}"
    else:
        match=re.match(r"^[^@]+@([^:]+):(.+)$",value)
        if match:value=f"{match.group(1)}/{match.group(2)}"
    value=value.strip("/").lower()
    # A bare owner/repo string is not proof of a GitHub origin.
    return value

def detect_repo(cwd:Path)->str:
    try:return norm_repo(subprocess.check_output(["git","-C",str(cwd),"remote","get-url","origin"],text=True,stderr=subprocess.DEVNULL,timeout=5))
    except (OSError,subprocess.SubprocessError):return ""

def token_match(text:str,term:str)->bool:
    # Bare JSX/TSX terminology is a signal; an extension inside a
    # sourcemap/domain is not. File extensions use route_matches instead.
    before = r"[a-z0-9.]" if term.lower() in {"jsx","tsx","vue"} else r"[a-z0-9]"
    return re.search(r"(?<!"+before+r")"+re.escape(term.lower())+r"(?![a-z0-9])",text) is not None

def route_matches(route:dict[str,Any],text:str)->list[str]:
    reasons=[f"term:{t}" for t in route.get("terms",[]) if token_match(text,t)]
    # Match filenames, including dotted basenames and sentence-final periods,
    # but not a hostname or sourcemap continuing after the extension.
    for suffix in route.get("suffixes",[]):
        pattern=r"(?<![a-z0-9_.-])(?:[a-z0-9_-]+\.)*[a-z0-9_-]+"+re.escape(suffix.lower())+r"(?![a-z0-9_-])(?!\.[a-z0-9])"
        if any(m.group(0) not in {"docs.rs","crates.rs"} for m in re.finditer(pattern,text)):
            reasons.append(f"suffix:{suffix}")
    return reasons

def validate_manifest(manifest:dict[str,Any],known:dict[str,Any])->None:
    ids=[]; repos=[]
    all_routes=list(manifest.get("routes",[]))
    for project in manifest.get("projects",[]):
        repos.extend(norm_repo(r) for r in project.get("repos",[]));all_routes.extend(project.get("routes",[]))
        for slug in project.get("always",[]):
            if slug not in known:raise ValueError(f"manifest references unknown slug: {slug}")
            if known[slug]["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX):raise ValueError(f"shelf cannot auto-select: {slug}")
    for route in all_routes:
        ids.append(route["id"])
        if not route.get("terms") and not route.get("suffixes"):raise ValueError(f"route has no signals: {route['id']}")
        for slug in route["skills"]:
            if slug not in known:raise ValueError(f"manifest references unknown slug: {slug}")
            if known[slug]["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX):raise ValueError(f"shelf cannot auto-select: {slug}")
    if len(ids)!=len(set(ids)):raise ValueError("resolver route IDs must be unique")
    if len(repos)!=len(set(repos)):raise ValueError("project repository identities must be unique")
    for slug, dependencies in manifest.get("explicit_stacks",{}).items():
        if slug not in known:raise ValueError(f"unknown explicit stack: {slug}")
        for dependency in dependencies:
            if dependency not in known:raise ValueError(f"unknown prerequisite: {dependency}")
            if known[dependency]["kind"].startswith("shelf") or dependency.startswith(SHELF_PREFIX) or known[dependency]["kind"].startswith("project"):
                raise ValueError(f"invalid explicit prerequisite: {dependency}")

def select(manifest:dict[str,Any],inventory:dict[str,Any],prompt:str,repo:str="")->dict[str,Any]:
    known={i["slug"]:i for i in inventory["items"]};validate_manifest(manifest,known)
    text=" ".join(prompt.lower().split()); matches=[];matched_routes=[]
    # Explicit tokens pass through scope/shelf checks, never through prose routes.
    route_text=re.sub(r"\[(?:skill|rule):[a-z0-9-]+\]", " ", text)
    route_text=re.sub(r"(?<!\S)/[a-z0-9-]+(?!\S)", " ", route_text)
    normalized_repo=norm_repo(repo); matching_project=None
    for project in manifest.get("projects",[]):
        if normalized_repo in {norm_repo(r) for r in project["repos"]}:
            matching_project=project;break
    permitted_project_slugs=set()
    if matching_project:
        permitted_project_slugs.update(matching_project.get("always",[]))
        for route in matching_project.get("routes",[]):permitted_project_slugs.update(route["skills"])
    explicit_refs=set(re.findall(r"\[(skill|rule):([a-z0-9-]+)\]",text))
    explicit_refs.update(("skill",slug) for slug in re.findall(r"(?<!\S)/([a-z0-9-]+)(?!\S)",text))
    rejected_explicit=[]
    explicit_actions=set()
    for kind,slug in sorted(explicit_refs):
        is_known=slug in known and (kind!="rule" or known[slug]["kind"] in ("rule","project-rule"))
        is_shelf=is_known and (slug.startswith(SHELF_PREFIX) or known[slug]["kind"].startswith("shelf"))
        is_wrong_project=is_known and known[slug]["kind"].startswith("project") and slug not in permitted_project_slugs
        if is_known and not is_shelf and not is_wrong_project:
            matches.append((1000,"explicit",slug,["explicit-slug"]))
            if slug in TICKET_ACTIONS:explicit_actions.add(slug)
            for dependency in manifest.get("explicit_stacks",{}).get(slug,[]):
                matches.append((999,"explicit-prerequisite",dependency,[f"prerequisite:{slug}"]))
            if slug in TICKET_ACTIONS:matches.append((999,"explicit-ticket-guard","ticket-guard",["ticket-action-prerequisite"]))
        else:
            rejected_explicit.append(slug)
    for route in manifest["routes"]:
        why=route_matches(route,route_text)
        if why:
            matched_routes.append(route)
            for slug in route["skills"]: matches.append((route["priority"],route["id"],slug,why))
    project_id=None
    if matching_project:
        project_id=matching_project["id"]
        for slug in matching_project.get("always",[]): matches.append((2000,f"project:{project_id}",slug,[f"repo:{normalized_repo}"]))
        for route in matching_project.get("routes",[]):
            why=route_matches(route,route_text)
            if why:
                matched_routes.append(route)
                for slug in route["skills"]: matches.append((route["priority"],f"project:{project_id}:{route['id']}",slug,why))
    groups={}
    for route in matched_routes:
        if route.get("exclusive_group"):groups.setdefault(route["exclusive_group"],[]).append(route["id"])
    conflicts={group:sorted(ids) for group,ids in groups.items() if len(ids)>1}
    routed_actions={slug for route in matched_routes if route.get("exclusive_group")=="ticket-action" for slug in route["skills"] if slug in TICKET_ACTIONS}
    if len(routed_actions|explicit_actions)>1:conflicts["ticket-action"]=sorted(routed_actions|explicit_actions)
    if conflicts:
        return {"schema_version":1,"state":"ambiguous","kernel":manifest["kernel"],"project":project_id,"selected":[],"diagnostic":f"ambiguous routes: {conflicts}"}
    selected={}
    for priority,route,slug,why in sorted(matches,key=lambda x:(-x[0],x[1],x[2])):
        if slug not in known: raise ValueError(f"manifest references unknown slug: {slug}")
        if known[slug]["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX): raise ValueError(f"shelf cannot auto-select: {slug}")
        selected.setdefault(slug,{"slug":slug,"source_path":known[slug].get("source_path","unknown"),"route":route,"priority":priority,"reasons":why})
    selected_items=list(selected.values())
    # Explicit selection is discovery, never permission to bypass protected CI.
    # The legacy billing skill is retained only as a non-authorizing diagnostic.
    diagnostic_only=sorted(set(selected)&DIAGNOSTIC_ONLY)
    selected_characters=sum(int(known[item["slug"]].get("characters",0)) for item in selected_items)
    selected_tokens=sum(int(known[item["slug"]].get("estimated_tokens",0)) for item in selected_items)
    over_budget=(
        len(selected_items)>MAX_SELECTED_ITEMS
        or selected_characters>MAX_SELECTED_CHARACTERS
        or selected_tokens>MAX_SELECTED_ESTIMATED_TOKENS
    )
    if over_budget:
        return {
            "schema_version":1,"state":"over-budget","kernel":manifest["kernel"],"project":project_id,"selected":[],
            "selected_content":{"items":len(selected_items),"characters":selected_characters,"estimated_tokens":selected_tokens},
            "diagnostic":(
                f"selection exceeds budget (items={len(selected_items)}/{MAX_SELECTED_ITEMS}, "
                f"characters={selected_characters}/{MAX_SELECTED_CHARACTERS}, "
                f"estimated_tokens={selected_tokens}/{MAX_SELECTED_ESTIMATED_TOKENS}); kernel only"
            ),
        }
    state="matched" if selected_items else "unknown"
    diagnostic="no route matched; kernel only" if state=="unknown" else f"{len(selected_items)} capability item(s) selected"
    if diagnostic_only:diagnostic+=f"; diagnostic-only (no merge authorization): {','.join(diagnostic_only)}"
    if rejected_explicit:diagnostic+=f"; rejected explicit slugs: {','.join(rejected_explicit)}"
    return {
        "schema_version":1,"state":state,"kernel":manifest["kernel"],"project":project_id,"selected":selected_items,
        "selected_content":{"items":len(selected_items),"characters":selected_characters,"estimated_tokens":selected_tokens},
        "diagnostic":diagnostic,
    }

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
