#!/usr/bin/env python3
"""Deterministically select task/project skills from the compact resolver manifest."""
from __future__ import annotations
import argparse, functools, importlib.util, json, os, re, subprocess, sys
from pathlib import Path, PurePosixPath
from typing import Any
ROOT=Path(__file__).resolve().parents[1]
SHELF_PREFIX="shelves"
TICKET_ACTIONS={"create-ticket","update-ticket","close-ticket"}
# This legacy slug is diagnostic-only until an exact project policy exists.
DIAGNOSTIC_ONLY={"ci-billing-failure-merge"}
MAX_SELECTED_ITEMS=12
MAX_SELECTED_CHARACTERS=80000
MAX_SELECTED_ESTIMATED_TOKENS=20000
MAX_RESIDENT_BYTES=80000

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

def payload_fields(raw:bytes)->tuple[str,str]:
    # Same values the hook used to extract with two separate python3 calls: each
    # field falls back to "" on its own failure (including invalid UTF-8 or a
    # BOM), rendered the way print() and shell command substitution rendered it
    # (str(), trailing newlines removed).
    def field(get)->str:
        try:value=get(json.loads(raw.decode("utf-8")))
        except Exception:return ""
        return str(value).rstrip("\n")
    prompt=field(lambda d:d.get("prompt") or d.get("tool_input",{}).get("prompt") or "")
    cwd=field(lambda d:d.get("cwd") or "")
    if not (cwd and Path(cwd).is_dir()):
        pwd=os.environ.get("PWD","")
        cwd=pwd if pwd and Path(pwd).is_dir() else os.getcwd()
    return prompt,cwd

def detect_repo(cwd:Path)->str:
    try:return norm_repo(subprocess.check_output(["git","-C",str(cwd),"remote","get-url","origin"],text=True,stderr=subprocess.DEVNULL,timeout=5))
    except (OSError,subprocess.SubprocessError):return ""

def token_match(text:str,term:str)->bool:
    # Bare JSX/TSX terminology is a signal; an extension inside a
    # sourcemap/domain is not. File extensions use route_matches instead.
    before = r"[a-z0-9.]" if term.lower() in {"jsx","tsx","vue"} else r"[a-z0-9]"
    return re.search(r"(?<!"+before+r")"+re.escape(term.lower())+r"(?![a-z0-9])",text) is not None

# Apostrophe-like and quotation-like code points, mapped to their ASCII forms.
QUOTE_VARIANTS=str.maketrans({
    **{chr(c):"'" for c in (0x2018,0x2019,0x201A,0x201B,0x2032,0x02BC,0x00B4,0xFF07)},
    **{chr(c):'"' for c in (0x201C,0x201D,0x201E,0x201F,0x2033,0xFF02,0x00AB,0x00BB)},
})
# A period after one of these tokens, or after dotted initials, does not end a sentence.
ABBREVIATIONS={"e.g","i.e","etc","vs","cf","approx","al","mr","mrs","ms","dr","jr","sr","prof",
               "no","nos","fig","figs","st","ver","vol","pp","ch","sec","eq","ref","inc","ltd","dept"}
TOKEN_CHARS=frozenset("abcdefghijklmnopqrstuvwxyz0123456789.")
NEGATION_LEAD=re.compile(r"(?:do not|don't)\b")
READ_ONLY_REQUEST=re.compile(r"\bread.only\b|\b(?:do not|don't|never)\s+(?:write|save|load|insert|register)\b|\b(?:without modifying code|documentation about|readme mentions|docs discuss|docs say)\b|\b(?:write|edit|review|update)\s+(?:docs|documentation|readme|guide)\b")

def normalize_quotes(text:str)->str:
    # Curly apostrophes and quotes behave exactly like their ASCII forms in every route.
    return text.translate(QUOTE_VARIANTS)

def strip_quoted(text:str)->str:
    # Used only by prose-request routes. A quotation opens at the start of the text,
    # after whitespace or after an opening bracket. A single quote opens only before a
    # letter that does not start a common elision and closes only at a word boundary,
    # so contractions, elisions, decades and lone possessives ("don't", "'em", "'cos",
    # "'90s", "users'") are not quote marks.
    text=re.sub(r'(?:^|(?<=[\s(\[{]))"[^"]*"(?![a-z0-9])'," ",text)
    return re.sub(r"(?:^|(?<=[\s(\[{]))'(?=[a-z])(?!(?:em|til|cause|cos|coz|cuz|tis|twas|n|bout|round|kay)\b)(?:[^']|(?<=[a-z0-9])'(?=[a-z0-9]))+'(?![a-z0-9])"," ",text)

def split_sentences(clause:str)->list[str]:
    return list(_sentences(clause))

@functools.lru_cache(maxsize=4096)
def _sentences(clause:str)->tuple[str,...]:
    # One linear pass over whitespace-separated words: a word ending in "." or "!"
    # ends a sentence unless it is a known abbreviation or dotted initials. Decimals,
    # paths and URLs have no whitespace after the period. Each piece keeps its own
    # text verbatim, so joining all pieces reproduces the clause. Cached because every
    # verb route reads the same clauses.
    sentences=[];start=0
    for match in re.finditer(r"\S+",clause):
        word=match.group(0)
        if word[-1] not in ".!":continue
        body=word[:-1];cut=len(body)
        while cut and body[cut-1] in TOKEN_CHARS:cut-=1
        token=body[cut:]
        if token in ABBREVIATIONS or re.fullmatch(r"(?:[a-z]\.)*[a-z]",token):continue
        sentences.append(clause[start:match.end()]);start=match.end()
    sentences.append(clause[start:])
    return tuple(sentences)

IMPERATIVE_ASK=re.compile(r"(?:(?:instead|rather|please|so),? )*(?:ask|interview)\b")

def manner_prohibition(sentence:str,qualifiers:list[str])->bool:
    # The whole sentence forbids only a manner of asking: "don't ask [me] [all your]
    # questions|them <qualifier>". Anything more ("or at all", ", at once start
    # coding", "together with the code", a request after a comma) is not a match.
    manner="|".join(re.escape(q.lower()) for q in qualifiers)
    return re.fullmatch(r"(?:do not|don't) (?:ask|send)(?: (?:me|us))?(?: (?:all|your|the|these|those|my))*"
                        r"(?: (?:questions?|them))?(?: all)? (?:"+manner+r")[.!]?",sentence.strip()) is not None

def without_prohibitions(clause:str,qualifiers:list[str]|None=None)->str:
    # Drop sentences that open with "don't" or "do not", keeping the rest verbatim.
    # Without qualifiers only the leading run of such sentences is dropped. With a
    # route's qualifiers a sentence is dropped only when it forbids nothing but a
    # manner of asking and the next sentence asks for it another way ("Don't ask
    # questions as a group. Ask them one at a time."); every other prohibition stays.
    sentences=split_sentences(clause);kept=[];leading=True
    for index,sentence in enumerate(sentences):
        prohibition=NEGATION_LEAD.match(sentence.strip()) is not None
        if qualifiers is None:
            if leading and prohibition:continue
            leading=leading and (prohibition or not sentence.strip())
        elif prohibition and manner_prohibition(sentence,qualifiers):
            following=next((s.strip() for s in sentences[index+1:] if s.strip()),"")
            if IMPERATIVE_ASK.match(following):continue
        kept.append(sentence)
    return "".join(kept)

def route_matches(route:dict[str,Any],text:str)->list[str]:
    # A prose-request route names a conversational protocol rather than a technology:
    # quoted prose is data for it. Technology routes keep every quotation as context.
    prose=route.get("prose_request")
    if prose:text=strip_quoted(text)
    # A map's input geometry is not proof of a geometry transformation.
    if route.get("exclude_pure_visualization") and re.search(r"\b(?:choropleth|visualization|arcgis map|map rendering)\b",text) and not re.search(r"\b(?:spatial join|sjoin|overlay|reproject|geoparquet|crs|geometry transform|geometry repair|st_[a-z]+)\b",text):
        return []
    # Pair action and technology within the same clause. An unrelated action
    # before a semicolon must not authorize a README mention after it.
    clauses=text.split(";") if route.get("verbs") else [text]
    reasons=[]
    if route.get("all_terms") and all(token_match(text, term) for term in route["all_terms"]):
        lead=clauses[0].strip()
        continuation=any(re.match(r"^"+re.escape(term)+r"\b",part.strip()) for term in route["all_terms"][1:] for part in clauses[1:])
        if continuation and token_match(lead, route["all_terms"][0]) and any(token_match(lead, verb) for verb in route.get("verbs",[])) and not re.match(r"^(?:what|why|which|explain|tell me|how does|how do i|how to|is it|do not|don't)\b",lead):
            reasons.append("compound:"+"+".join(route["all_terms"]))
    for clause in clauses:
        clause=whole=clause.strip()
        if route.get("verbs"):
            # A prohibition binds only its own sentence, which then contributes nothing
            # (neither verbs nor terms); the rest of the clause is judged as before. A
            # read-only signal still scopes the whole clause.
            clause=without_prohibitions(whole,route.get("prohibition_qualifiers")).strip()
        if any(token_match(clause,term) for term in route.get("exclude_terms",[])):
            continue
        if route.get("verbs"):
            if re.match(r"^(?:what|why|which|explain|tell me|how does|how do i|how to|is it|do not|don't)\b",clause) or READ_ONLY_REQUEST.search(whole):
                continue
            if not any(token_match(clause, verb) for verb in route["verbs"]):
                continue
        if route.get("context_terms") and not any(token_match(clause, term) for term in route["context_terms"]):
            continue
        if any(not any(token_match(clause,term) for term in group) for group in route.get("required_groups",[])):
            continue
        reasons.extend(f"term:{t}" for t in route.get("terms",[]) if token_match(clause,t))
        # Match filenames, but not a hostname or sourcemap continuation.
        for suffix in route.get("suffixes",[]):
            pattern=r"(?<![a-z0-9_.-])(?:[a-z0-9_-]+\.)*[a-z0-9_-]+"+re.escape(suffix.lower())+r"(?![a-z0-9_-])(?!\.[a-z0-9])"
            if any(m.group(0) not in {"docs.rs","crates.rs"} for m in re.finditer(pattern,clause)):
                reasons.append(f"suffix:{suffix}")
    return reasons

def typed_kind(kind:str)->str:
    return "rule" if kind in ("rule","project-rule") else "skill"

def inventory_maps(inventory:dict[str,Any])->tuple[dict[str,Any],dict[tuple[str,str],Any]]:
    # Untyped manifest routes keep their historical deterministic winner; explicit
    # tokens resolve in separate namespaces and retain their concrete source.
    known={i["slug"]:i for i in inventory["items"]}
    typed={}
    for item in inventory["items"]:
        key=(typed_kind(item["kind"]),item["slug"])
        if key in typed:raise ValueError(f"duplicate typed slug: {key}")
        typed[key]=item
    return known,typed

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
        if "prose_request" in route and not isinstance(route["prose_request"],bool):
            raise ValueError(f"invalid prose_request flag: {route['id']}")
        if "prohibition_qualifiers" in route and not route.get("verbs"):
            raise ValueError(f"prohibition qualifiers need a verb route: {route['id']}")
        for key in ("verbs","context_terms","all_terms","exclude_terms","prohibition_qualifiers"):
            if key in route and (not isinstance(route[key],list) or not route[key] or not all(isinstance(v,str) and v for v in route[key])):
                raise ValueError(f"invalid {key} gate: {route['id']}")
        if "exclude_pure_visualization" in route and not isinstance(route["exclude_pure_visualization"],bool):
            raise ValueError(f"invalid visualization gate: {route['id']}")
        if "required_groups" in route and (not isinstance(route["required_groups"],list) or not route["required_groups"] or any(not isinstance(g,list) or not g or not all(isinstance(v,str) and v for v in g) for g in route["required_groups"])):
            raise ValueError(f"invalid required groups: {route['id']}")
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
    known,typed=inventory_maps(inventory);validate_manifest(manifest,known)
    composition=None
    if "procedure_composition" in manifest:
        spec=importlib.util.spec_from_file_location("procedure_composition",Path(__file__).with_name("procedure_composition.py"))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        composition=module.graph_from_manifest(manifest,inventory,norm_repo(repo))
    prompt=normalize_quotes(prompt)
    # An explicit task/code heading owns its next line; unrelated lines remain
    # separate clauses so README notes cannot borrow an earlier action verb.
    prompt=re.sub(r"(?im)^\s*(implement(?: the following)?|review this code|write the following|analyze the following)\s*:\s*\n",r"\1: ",prompt)
    # A how-to question is read-only unless the immediately following clause
    # requests a concrete code/SQL patch to the same task. Never carry its
    # technology into a later independent docs/README clause.
    question=re.match(r"(?is)^\s*((?:how do i|how to|what is the best way to)\b[^?]*\?)\s*(.*)$",prompt)
    if question:
        follow,separator,rest=question.group(2).partition(";")
        if (re.match(r"(?i)^\s*(?:please\s+)?(?:implement|edit|fix|patch)\b",follow)
            and re.search(r"(?i)\b(?:code|patch|sql|script|query|table|saveastable)\b",follow)
            and not re.search(r"(?i)\b(?:unrelated|readme|docs|documentation|title)\b",follow)):
            prompt=f"{follow.strip()} {question.group(1).rstrip('?')}"+(f"; {rest}" if separator else "")
    text=" ".join(prompt.lower().replace("?","; ").replace("\n","; ").split()); matches=[];matched_routes=[]
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
    # Slash commands are untyped: keep the deterministic route/default winner.
    explicit_refs.update(("untyped",slug) for slug in re.findall(r"(?<!\S)/([a-z0-9-]+)(?!\S)",text))
    rejected_explicit=[]
    explicit_actions=set()
    for kind,slug in sorted(explicit_refs):
        item=known.get(slug) if kind=="untyped" else typed.get((kind,slug))
        if composition and kind in ("untyped","skill") and slug in composition.aliases:
            effective=composition.resolve([slug])["selected"][0]["slug"]
            item={**known[effective],"slug":slug}
        is_shelf=item is not None and (slug.startswith(SHELF_PREFIX) or item["kind"].startswith("shelf"))
        is_wrong_project=item is not None and item["kind"].startswith("project") and slug not in permitted_project_slugs
        if composition and item is not None and item.get("project")==composition.project:
            is_wrong_project=False
        if item is not None and not is_shelf and not is_wrong_project:
            matches.append((1000,"explicit",item,["explicit-slug"]))
            if slug in TICKET_ACTIONS:explicit_actions.add(slug)
            # Stacks are assigned to the concrete kind: a rule token with the
            # same slug as a skill must not inherit the skill's prerequisites.
            if known.get(slug) is item and not (composition and typed_kind(item["kind"])=="skill"):
                for dependency in manifest.get("explicit_stacks",{}).get(slug,[]):
                    matches.append((999,"explicit-prerequisite",known[dependency],[f"prerequisite:{slug}"]))
            if slug in TICKET_ACTIONS:matches.append((999,"explicit-ticket-guard",known["ticket-guard"],["ticket-action-prerequisite"]))
        else:
            rejected_explicit.append(slug)
    for route in manifest["routes"]:
        why=route_matches(route,route_text)
        if why:
            matched_routes.append(route)
            for slug in route["skills"]: matches.append((route["priority"],route["id"],known[slug],why))
    project_id=None
    if matching_project:
        project_id=matching_project["id"]
        for slug in matching_project.get("always",[]): matches.append((2000,f"project:{project_id}",known[slug],[f"repo:{normalized_repo}"]))
        for route in matching_project.get("routes",[]):
            why=route_matches(route,route_text)
            if why:
                matched_routes.append(route)
                for slug in route["skills"]: matches.append((route["priority"],f"project:{project_id}:{route['id']}",known[slug],why))
    groups={}
    for route in matched_routes:
        if route.get("exclusive_group"):groups.setdefault(route["exclusive_group"],[]).append(route["id"])
    conflicts={group:sorted(ids) for group,ids in groups.items() if len(ids)>1}
    routed_actions={slug for route in matched_routes if route.get("exclusive_group")=="ticket-action" for slug in route["skills"] if slug in TICKET_ACTIONS}
    if len(routed_actions|explicit_actions)>1:conflicts["ticket-action"]=sorted(routed_actions|explicit_actions)
    if conflicts:
        return {"schema_version":1,"state":"ambiguous","kernel":manifest["kernel"],"project":project_id,"selected":[],"diagnostic":f"ambiguous routes: {conflicts}"}
    selected={}
    for priority,route,item,why in sorted(matches,key=lambda x:(-x[0],x[1],x[2]["slug"],x[2].get("source_path",""))):
        slug=item["slug"]
        if item["kind"].startswith("shelf") or slug.startswith(SHELF_PREFIX): raise ValueError(f"shelf cannot auto-select: {slug}")
        source=item.get("source_path",f"{typed_kind(item['kind'])}:{slug}")
        if composition and typed_kind(item['kind'])=="skill":
            source=f"composition:{slug}"
        selected.setdefault(source,{
            "slug":slug,
            "source_path":item.get("source_path","unknown"),
            "load_path":item.get("package_path",item.get("source_path","unknown")),
            "route":route,
            "priority":priority,
            "reasons":why,
            "_item":item,
        })
    selected_items=list(selected.values())
    if composition:
        skill_rows=[row for row in selected_items if typed_kind(row["_item"]["kind"])=="skill"]
        # Resolve before the final content budget, and use the same graph as
        # package links. All routes, aliases and prerequisite edges converge.
        requests=[row["slug"] for row in skill_rows]
        by_request={row["slug"]:row for row in skill_rows}
        composed=[]
        for entry in composition.resolve(requests)["selected"]:
            first=by_request[entry["requested_by"][0]]
            composed.append({**first,**entry,"_item":typed[("skill",entry["slug"])]})
        selected_items=composed+[row for row in selected_items if typed_kind(row["_item"]["kind"])=="rule"]
    # Explicit selection is discovery, never permission to bypass protected CI.
    # The legacy billing skill is retained only as a non-authorizing diagnostic.
    diagnostic_only=sorted({item["slug"] for item in selected_items}&DIAGNOSTIC_ONLY)
    selected_characters=sum(int(item["_item"].get("characters",0)) for item in selected_items)
    selected_tokens=sum(int(item["_item"].get("estimated_tokens",0)) for item in selected_items)
    for item in selected_items:del item["_item"]
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
    diagnostic=("no task route matched; matched project context only" if composition else "no route matched; kernel only") if state=="unknown" else f"{len(selected_items)} capability item(s) selected"
    if diagnostic_only:diagnostic+=f"; diagnostic-only (no merge authorization): {','.join(diagnostic_only)}"
    if rejected_explicit:diagnostic+=f"; rejected explicit slugs: {','.join(rejected_explicit)}"
    return {
        "schema_version":1,"state":state,"kernel":manifest["kernel"],"project":project_id,"selected":selected_items,
        "selected_content":{"items":len(selected_items),"characters":selected_characters,"estimated_tokens":selected_tokens},
        "authorization_effect":"none",
        "diagnostic":diagnostic,
    }

def runtime_file(root:Path,relative:str)->Path:
    """Resolve a regular package file without following links or escaping root."""
    if not isinstance(relative,str) or not relative or "\\" in relative or "\x00" in relative:
        raise ValueError("invalid runtime path")
    path=PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path)!=relative:
        raise ValueError("runtime path must be canonical and package-relative")
    current=root.resolve()
    for part in path.parts:
        current=current/part
        if current.is_symlink():raise ValueError("symlink runtime path is unsupported: "+relative)
    if not current.is_file():raise ValueError("unreadable runtime path: "+relative)
    return current

def composed_resident(root:Path,manifest:dict[str,Any],result:dict[str,Any],repo:str)->str:
    """Check installed composition consistency, never package authenticity.

    Content comes from the already selected package. A receipt or matching
    digest cannot authorize an operation or establish a live host capability.
    The mandatory canonical kernel is emitted separately by the prompt hook.
    """
    if manifest.get("kernel")!="skills/RESIDENT.md" or "procedure_composition" not in manifest:
        raise ValueError("unsupported composed resident path or missing composition")
    config=manifest["procedure_composition"]
    receipt=json.loads(runtime_file(root,"composition.json").read_bytes())
    project=result.get("project")
    if not project or project!=config["project"] or project!=receipt["project"]:
        raise ValueError("resident project differs from selected composition")
    if norm_repo(repo)!=config["identity"] or config["identity"]!=receipt["identity"]:
        raise ValueError("resident repository identity differs from target")
    resident=receipt["resident"]
    if (receipt.get("authorization_effect")!="none" or receipt.get("evidence_state")!="configured"
        or resident.get("authorization_effect")!="none" or resident.get("project")!=project):
        raise ValueError("resident receipt is not non-authorizing configured content")
    content=runtime_file(root,"skills/RESIDENT.md").read_bytes()
    if len(content)>MAX_RESIDENT_BYTES:raise ValueError("composed resident exceeds runtime byte budget")
    rendered=resident["rendered"]
    if not isinstance(rendered,str) or not rendered or content!=rendered.encode("utf-8"):
        raise ValueError("resident bytes differ from composition receipt")
    if (type(resident["characters"]) is not int or resident["characters"]!=len(rendered)
        or type(resident["estimated_tokens"]) is not int or resident["estimated_tokens"]!=(len(rendered)+3)//4):
        raise ValueError("resident size differs from composition receipt")
    return rendered

def render_hook_result(root:Path,manifest:dict[str,Any],result:dict[str,Any],repo:str,mode:str)->str:
    """Render one fully checked load set; failures cannot emit partial content."""
    state=result["state"]
    if state not in {"matched","unknown","ambiguous","over-budget"}:
        raise ValueError("invalid selector state")
    selected=result.get("selected",[])
    resolved=[(item,runtime_file(root,item.get("load_path",item.get("source_path","unknown")))) for item in selected]
    kernel=manifest.get("kernel")
    if kernel not in {"skills/KERNEL.md","skills/RESIDENT.md"}:
        raise ValueError("unsupported resident path")
    if "procedure_composition" in manifest and kernel!="skills/RESIDENT.md":
        raise ValueError("composed package is missing its resident binding")
    resident=None
    if kernel=="skills/RESIDENT.md" and state in {"matched","unknown"}:
        resident=composed_resident(root,manifest,result,repo)
    label="candidate" if mode=="canary" else "load"
    action="Canary mode: report candidates but do not load them automatically." if mode=="canary" else "Read each selected skill before acting."
    lines=[]
    if resident is not None and mode!="canary":
        lines.extend(["<project-resident>",resident,"</project-resident>"])
    lines.extend(["<progressive-load-set>","state: "+state,"project: "+str(result.get("project") or "none")])
    if resident is not None:
        lines.append("resident-"+label+": skills/RESIDENT.md")
    for item,path in resolved:
        lines.append("%s: %s | path=%s | source=%s | route=%s | reasons=%s"%(label,item["slug"],path,item.get("source_path","unknown"),item["route"],",".join(item["reasons"])))
    lines.extend(["diagnostic: "+result["diagnostic"],action,
                  "Unknown task routing loads no task skills; only an independently matched composed project may supply resident context. Ambiguous or invalid selection means kernel only; do not load the full library.",
                  "Reference shelves never self-select and may load only through an active skill's declared reference.","</progressive-load-set>"])
    return "\n".join(lines)

def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--prompt",default="");p.add_argument("--cwd",type=Path,default=Path.cwd());p.add_argument("--repo",default="");p.add_argument("--manifest",type=Path,default=ROOT/"catalog/resolver-manifest.json");p.add_argument("--inventory",type=Path,default=ROOT/"catalog/skills-inventory.json")
    p.add_argument("--render-hook",action="store_true",help="render checked package content for the registered prompt hook")
    p.add_argument("--mode",choices=("on","canary"),default="on")
    p.add_argument("--payload-stdin",action="store_true",help="read prompt and cwd from the hook's JSON payload on stdin; overrides --prompt and --cwd")
    a=p.parse_args()
    if a.payload_stdin:
        prompt,cwd=payload_fields(sys.stdin.buffer.read())
        a.prompt,a.cwd=prompt,Path(cwd)
    try:
        if a.render_hook:
            runtime_file(ROOT,a.manifest.relative_to(ROOT).as_posix())
            if a.inventory.exists() or a.inventory.is_symlink():
                runtime_file(ROOT,a.inventory.relative_to(ROOT).as_posix())
        manifest=json.loads(a.manifest.read_text())
        if a.render_hook and "procedure_composition" in manifest:
            runtime_file(ROOT,a.inventory.relative_to(ROOT).as_posix())
        if a.inventory.is_file():
            inventory=json.loads(a.inventory.read_text())
        else:
            entries=manifest.get("known_by_source")
            inventory={"items":list(entries.values()) if entries is not None else
                       [{"slug":slug,**meta} for slug,meta in manifest.get("known",{}).items()]}
        repo=a.repo or detect_repo(a.cwd)
        result=select(manifest,inventory,a.prompt,repo)
        if a.render_hook:
            print(render_hook_result(ROOT,manifest,result,repo,a.mode));return 0
    except (OSError,ValueError,KeyError,TypeError,AttributeError,IndexError,json.JSONDecodeError) as e:
        if a.render_hook:
            print("<progressive-load-set>\nstate: error\ndiagnostic: selector or runtime content invalid; kernel only\n</progressive-load-set>")
            print(str(e),file=sys.stderr);return 1
        print(json.dumps({"schema_version":1,"state":"error","kernel":"skills/KERNEL.md","selected":[],"diagnostic":str(e)},sort_keys=True));return 1
    print(json.dumps(result,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
