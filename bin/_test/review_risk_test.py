#!/usr/bin/env python3
from __future__ import annotations
import hashlib,importlib.util,json,re,shlex,subprocess,sys,tempfile
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SCRIPT=ROOT/"bin/review-risk.py"
spec=importlib.util.spec_from_file_location("review_risk",SCRIPT);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
policy=json.loads((ROOT/"catalog/review-risk-policy.json").read_text())
AUTHORITY_DEPENDENCY_FLOOR = [
 "bundles/siege/policy-inputs.json",
 "bin/effective_policy.py",
 "bin/gate_contract.py",
 "bin/_test/effective_policy_test.py",
 "bin/_test/gate_contract_test.py",
 "bin/_test/protected_policy_test.py",
 "bin/_test/provider_event_test.py",
 "bin/_test/resident_delivery_test.py",
 "examples/provider/shared-parent-workflow.yml",
 "scripts/ci/protected-policy-range.py",
 "scripts/ci/check-branch-topology.sh",
 "catalog/effective-policy-selection.json",
 "catalog/gate-contract-schema.json",
 "catalog/gate-contracts.json",
]
AUDITED_ENFORCEMENT_DEPENDENCIES = AUTHORITY_DEPENDENCY_FLOOR + [
 "bin/package-generation.py",
 "bin/_test/package_generation_test.py",
 "hooks/agent-comms/hub-concurrency-gate.sh",
 "hooks/agent-comms/no-slug-form-outbound.sh",
 "hooks/agent-comms/spawn-guard.sh",
 "hooks/infrastructure/catalog-guard.sh",
 "hooks/lib/after-image.py",
 "hooks/lib/artifact-casefold-candidate.py",
 "hooks/lib/canonical-path.py",
 "hooks/lib/detect-host.sh",
 "hooks/lib/extract-json.py",
 "hooks/lib/gate-registry.sh",
 "hooks/lib/probe-runner.py",
 "hooks/lib/resolve-think-gate.py",
 "hooks/lib/scope-check.sh",
 "hooks/lib/split-frontmatter.py",
 "bin/build.py",
 "bin/generated-source-authority.py",
 "bin/kernel-budget.py",
 "bin/skill-inventory.py",
 "bin/validate-hooks.py",
 "bin/_test/review_risk_test.py",
 "bin/_test/native_push_test.py",
 "bin/install-hooks.sh",
 "bin/verify-enforcement.sh",
 ".githooks/pre-push",
 "hooks/_test/review_risk_policy.test.sh",
]
ADVISORY_DEPENDENCY_EXCLUSIONS = {"hooks/lib/log-block.sh"}
REQUIRED_SOURCE_ENTRYPOINTS = set("""
hooks/agent-comms/hub-concurrency-gate.sh
hooks/agent-comms/no-slug-form-outbound.sh
hooks/agent-comms/spawn-guard.sh
hooks/bash/coordinator-status-guard.sh
hooks/bash/destructive-guard.sh
hooks/bash/universal-mutation-gate.sh
hooks/git/branch-guard.sh
hooks/git/detect-ai-fingerprints.sh
hooks/git/fix-shape-guard.sh
hooks/git/no-attribution.sh
hooks/git/no-broad-staging.sh
hooks/git/no-sensitive-files.sh
hooks/git/post-error-revision-required.sh
hooks/git/pr-base-guard.sh
hooks/git/self-review.sh
hooks/git/survey-context.sh
hooks/git/test-tracking-guard.sh
hooks/git/ticket-required.sh
hooks/git/vergil-quote.sh
hooks/infrastructure/catalog-guard.sh
hooks/resolver/branch-state-guard.sh
hooks/resolver/inject-resolver.sh
hooks/resolver/investigate-gate-guard.sh
hooks/resolver/pipeline-state-guard.sh
hooks/resolver/pre-action-guard.sh
hooks/resolver/standing-order-guard.sh
hooks/resolver/think-gate-guard.sh
hooks/write/branch-guard.sh
hooks/write/ticket-propagation-guard.sh
hooks/write/write-guard.sh
""".strip().splitlines())
REQUIRED_SOURCE_ENTRYPOINT_COUNTS = {path:(4 if path.startswith("hooks/write/") else 1) for path in REQUIRED_SOURCE_ENTRYPOINTS}
REQUIRED_MANIFEST_ENTRYPOINTS = set("""
hooks/git/branch-guard.sh
hooks/git/pre-push-self-review.sh
hooks/git/test-guard.sh
hooks/resolver/investigate-gate-guard.sh
hooks/resolver/skill-enforcement-gate.sh
hooks/resolver/think-gate-guard.sh
""".strip().splitlines())
REQUIRED_MANIFEST_ENTRYPOINT_COUNTS = {path:1 for path in REQUIRED_MANIFEST_ENTRYPOINTS}
REQUIRED_GENERATED_SETTINGS_ENTRYPOINTS = {"hooks/resolver/ca-enforcement-gate.sh"}
REQUIRED_GENERATED_SETTINGS_ENTRYPOINT_COUNTS = {path:1 for path in REQUIRED_GENERATED_SETTINGS_ENTRYPOINTS}
REQUIRED_SOURCE_REGISTRATIONS_SHA256 = "67e52755ef66fb4ba9ad1bf32df1e51653924b41ccad535aa7126050e009549c"
REQUIRED_MANIFEST_REGISTRATIONS_SHA256 = "868ca27fe41ca9d2e6f9335e2ddaf05d7cb992617b42f24cbc3ff2794099414b"
REQUIRED_GENERATED_SETTINGS_REGISTRATIONS_SHA256 = "19a972d9471da0d66c46568c0efb8a16c356ed66f620702b7f06b8251bc809f0"
CI_INVOCATION_SITES = [
 (".github/workflows/build-and-publish.yml","bin/_test/resident_delivery_test.py","python3 bin/_test/resident_delivery_test.py",1),
 (".github/workflows/build-and-publish.yml","bin/_test/provider_event_test.py","run: python3 bin/_test/provider_event_test.py",1),
 (".github/workflows/build-and-publish.yml","bin/_test/native_push_test.py","run: python3 bin/_test/native_push_test.py",1),
 ("bin/generated-source-authority.py","bin/skill-inventory.py",'[sys.executable, str(root / "bin" / "skill-inventory.py"), "--check"],',1),
 ("bin/generated-source-authority.py","bin/build.py",'[sys.executable, str(root / "bin" / "build.py"), "--dist", str(fresh_dist)],',1),
 ("bin/kernel-budget.py","bin/generated-source-authority.py",'[sys.executable, str(root / "bin" / "generated-source-authority.py"), "--check"],',1),
 (".github/workflows/build-and-publish.yml","bin/build.py","run: python3 bin/build.py --check",1),
 (".github/workflows/build-and-publish.yml","bin/build.py","run: python3 bin/build.py",2),
 (".github/workflows/build-and-publish.yml","bin/generated-source-authority.py","python3 bin/generated-source-authority.py --check",2),
 (".github/workflows/build-and-publish.yml","bin/kernel-budget.py","python3 bin/kernel-budget.py --check",1),
 (".github/workflows/build-and-publish.yml","bin/skill-inventory.py","python3 bin/skill-inventory.py --check",1),
 (".github/workflows/build-and-publish.yml","bin/validate-hooks.py","run: python3 bin/validate-hooks.py dist/claude-code/",1),
 (".github/workflows/build-and-publish.yml","bin/validate-hooks.py","run: python3 bin/validate-hooks.py dist/craft-agent/",1),
 (".github/workflows/build-and-publish.yml","bin/validate-hooks.py","run: python3 bin/validate-hooks.py",1),
 (".github/workflows/build-and-publish.yml","bin/_test/review_risk_test.py","python3 bin/_test/review_risk_test.py",1),
 (".github/workflows/build-and-publish.yml","hooks/_test/review_risk_policy.test.sh","bash hooks/_test/review_risk_policy.test.sh",1),
]
REQUIRED_HELPER_EDGES = {
 tuple(row.split("|")) for row in """
hooks/agent-comms/no-slug-form-outbound.sh|hooks/lib/extract-json.py
hooks/bash/coordinator-status-guard.sh|hooks/lib/extract-json.py
hooks/bash/destructive-guard.sh|hooks/lib/extract-json.py
hooks/bash/destructive-guard.sh|hooks/lib/log-block.sh
hooks/bash/universal-mutation-gate.sh|hooks/lib/extract-json.py
hooks/bash/universal-mutation-gate.sh|hooks/lib/log-block.sh
hooks/bash/universal-mutation-gate.sh|hooks/lib/resolve-think-gate.py
hooks/git/branch-guard.sh|hooks/lib/extract-json.py
hooks/git/branch-guard.sh|hooks/lib/scope-check.sh
hooks/git/detect-ai-fingerprints.sh|hooks/lib/extract-json.py
hooks/git/fix-shape-guard.sh|hooks/lib/extract-json.py
hooks/git/no-attribution.sh|hooks/lib/extract-json.py
hooks/git/no-attribution.sh|hooks/lib/scope-check.sh
hooks/git/no-broad-staging.sh|hooks/lib/extract-json.py
hooks/git/no-broad-staging.sh|hooks/lib/scope-check.sh
hooks/git/no-sensitive-files.sh|hooks/lib/extract-json.py
hooks/git/no-sensitive-files.sh|hooks/lib/scope-check.sh
hooks/git/post-error-revision-required.sh|hooks/lib/extract-json.py
hooks/git/pr-base-guard.sh|hooks/lib/extract-json.py
hooks/git/self-review.sh|hooks/lib/extract-json.py
hooks/git/self-review.sh|hooks/lib/probe-runner.py
hooks/git/self-review.sh|hooks/lib/resolve-think-gate.py
hooks/git/self-review.sh|hooks/lib/scope-check.sh
hooks/git/survey-context.sh|hooks/lib/extract-json.py
hooks/git/survey-context.sh|hooks/lib/scope-check.sh
hooks/git/test-guard.sh|hooks/lib/extract-json.py
hooks/git/test-tracking-guard.sh|hooks/lib/extract-json.py
hooks/git/ticket-required.sh|hooks/lib/extract-json.py
hooks/git/ticket-required.sh|hooks/lib/scope-check.sh
hooks/git/vergil-quote.sh|hooks/lib/extract-json.py
hooks/infrastructure/catalog-guard.sh|hooks/lib/extract-json.py
hooks/resolver/branch-state-guard.sh|hooks/lib/log-block.sh
hooks/resolver/ca-enforcement-gate.sh|hooks/lib/detect-host.sh
hooks/resolver/ca-enforcement-gate.sh|hooks/lib/gate-registry.sh
hooks/resolver/investigate-gate-guard.sh|hooks/lib/resolve-think-gate.py
hooks/resolver/pipeline-state-guard.sh|hooks/lib/resolve-think-gate.py
hooks/resolver/pre-action-guard.sh|hooks/lib/log-block.sh
hooks/resolver/skill-enforcement-gate.sh|hooks/lib/resolve-think-gate.py
hooks/resolver/think-gate-guard.sh|hooks/lib/resolve-think-gate.py
hooks/write/branch-guard.sh|hooks/lib/extract-json.py
hooks/write/ticket-propagation-guard.sh|hooks/lib/after-image.py
hooks/write/ticket-propagation-guard.sh|hooks/lib/artifact-casefold-candidate.py
hooks/write/ticket-propagation-guard.sh|hooks/lib/canonical-path.py
hooks/write/ticket-propagation-guard.sh|hooks/lib/split-frontmatter.py
hooks/write/write-guard.sh|hooks/lib/extract-json.py
""".strip().splitlines()
}
REQUIRED_HELPER_INVOCATION_SITES_SHA256 = "be3eb70e43afc0c3eb747204a06ee2eb2d4ff6057ec9c1b63f119bdd795c9f60"
REQUIRED_HELPER_ASSIGNMENT_USE_SITES_SHA256 = "961b75dda8e289f0997bd17cdfefd6b8fd1b4be78473da3577bf747ed6a88bfc"
REQUIRED_HELPER_USE_COUNTS = {
 (source,target):int(count) for source,target,count in (
  row.split("|") for row in """
hooks/agent-comms/no-slug-form-outbound.sh|hooks/lib/extract-json.py|2
hooks/bash/coordinator-status-guard.sh|hooks/lib/extract-json.py|1
hooks/bash/destructive-guard.sh|hooks/lib/extract-json.py|2
hooks/bash/universal-mutation-gate.sh|hooks/lib/extract-json.py|2
hooks/bash/universal-mutation-gate.sh|hooks/lib/resolve-think-gate.py|6
hooks/git/branch-guard.sh|hooks/lib/extract-json.py|2
hooks/git/detect-ai-fingerprints.sh|hooks/lib/extract-json.py|2
hooks/git/fix-shape-guard.sh|hooks/lib/extract-json.py|2
hooks/git/no-attribution.sh|hooks/lib/extract-json.py|2
hooks/git/no-broad-staging.sh|hooks/lib/extract-json.py|2
hooks/git/no-sensitive-files.sh|hooks/lib/extract-json.py|2
hooks/git/post-error-revision-required.sh|hooks/lib/extract-json.py|1
hooks/git/pr-base-guard.sh|hooks/lib/extract-json.py|3
hooks/git/self-review.sh|hooks/lib/extract-json.py|2
hooks/git/self-review.sh|hooks/lib/resolve-think-gate.py|1
hooks/git/survey-context.sh|hooks/lib/extract-json.py|2
hooks/git/test-guard.sh|hooks/lib/extract-json.py|2
hooks/git/test-tracking-guard.sh|hooks/lib/extract-json.py|2
hooks/git/ticket-required.sh|hooks/lib/extract-json.py|2
hooks/git/vergil-quote.sh|hooks/lib/extract-json.py|1
hooks/resolver/branch-state-guard.sh|hooks/lib/log-block.sh|1
hooks/resolver/ca-enforcement-gate.sh|hooks/lib/gate-registry.sh|1
hooks/resolver/investigate-gate-guard.sh|hooks/lib/resolve-think-gate.py|2
hooks/resolver/pipeline-state-guard.sh|hooks/lib/resolve-think-gate.py|1
hooks/resolver/pre-action-guard.sh|hooks/lib/log-block.sh|1
hooks/resolver/skill-enforcement-gate.sh|hooks/lib/resolve-think-gate.py|1
hooks/resolver/think-gate-guard.sh|hooks/lib/resolve-think-gate.py|1
hooks/write/branch-guard.sh|hooks/lib/extract-json.py|2
hooks/write/ticket-propagation-guard.sh|hooks/lib/after-image.py|2
hooks/write/ticket-propagation-guard.sh|hooks/lib/artifact-casefold-candidate.py|1
hooks/write/ticket-propagation-guard.sh|hooks/lib/canonical-path.py|1
hooks/write/ticket-propagation-guard.sh|hooks/lib/split-frontmatter.py|2
""".strip().splitlines()
 )
}
def tier(paths):return m.classify(policy,paths)["computed_tier"]

def records_digest(records:list)->str:
 return hashlib.sha256(json.dumps(sorted(records),separators=(",",":"),ensure_ascii=True).encode()).hexdigest()

def settings_registration_records(settings:dict)->list[tuple[str,str,str]]:
 records=[]
 for event,groups in settings.get("hooks",{}).items():
  for group in groups:
   matcher=group.get("matcher","")
   for hook in group.get("hooks",[]):records.append((event,matcher,json.dumps(hook,sort_keys=True,separators=(",",":"))))
 return records

def manifest_registration_records(manifest:dict)->list[str]:
 return [json.dumps(gate,sort_keys=True,separators=(",",":")) for gate in manifest.get("gates",[])]

def settings_entrypoint_counts(settings:dict,marker:str)->Counter:
 paths=Counter()
 for groups in settings.get("hooks",{}).values():
  for group in groups:
   for hook in group.get("hooks",[]):
    command=shlex.split(hook["command"])[0];assert command.startswith(marker),command
    paths[command[len(marker):]]+=1
 return paths

def settings_entrypoints(settings:dict,marker:str)->set[str]:return set(settings_entrypoint_counts(settings,marker))

def entrypoint_surfaces()->tuple[dict,dict,dict]:
 # Parse the actual canonical registry, then run an isolated build and return
 # its emitted blocking manifest/settings for independent per-surface checks.
 source=json.loads((ROOT/"hooks/settings-snippet.json").read_text())
 with tempfile.TemporaryDirectory(prefix="review-risk-entrypoints-") as raw:
  dist=Path(raw);built=subprocess.run([sys.executable,str(ROOT/"bin/build.py"),"--dist",str(dist)],cwd=ROOT,text=True,capture_output=True)
  assert built.returncode==0,(built.stdout,built.stderr)
  manifest=json.loads((dist/"craft-agent/enforcement-manifest.json").read_text())
  generated=json.loads((dist/"craft-agent/settings-enforcement.json").read_text())
 return source,manifest,generated

def manifest_entrypoint_counts(manifest:dict)->Counter:
 return Counter(gate["hook"] for gate in manifest.get("gates",[]) if gate.get("blocking"))

def manifest_entrypoints(manifest:dict)->set[str]:return set(manifest_entrypoint_counts(manifest))

def entrypoint_surface_problems(source:dict,manifest:dict,generated:dict)->list[tuple]:
 observed=[
  ("source",settings_entrypoint_counts(source,"/path/to/claude-configs-public/"),Counter(REQUIRED_SOURCE_ENTRYPOINT_COUNTS)),
  ("manifest",manifest_entrypoint_counts(manifest),Counter(REQUIRED_MANIFEST_ENTRYPOINT_COUNTS)),
  ("generated-settings",settings_entrypoint_counts(generated,"/path/to/"),Counter(REQUIRED_GENERATED_SETTINGS_ENTRYPOINT_COUNTS)),
 ]
 problems=[(label,dict(actual),dict(required)) for label,actual,required in observed if actual!=required]
 digests=[
  ("source registration digest",records_digest(settings_registration_records(source)),REQUIRED_SOURCE_REGISTRATIONS_SHA256),
  ("manifest registration digest",records_digest(manifest_registration_records(manifest)),REQUIRED_MANIFEST_REGISTRATIONS_SHA256),
  ("generated settings registration digest",records_digest(settings_registration_records(generated)),REQUIRED_GENERATED_SETTINGS_REGISTRATIONS_SHA256),
 ]
 problems.extend((label,actual) for label,actual,required in digests if actual!=required)
 return problems

def mutate_nth_settings_entrypoint(settings:dict,marker:str,path:str,index:int,action:str)->dict:
 mutated=json.loads(json.dumps(settings));seen=0
 for groups in mutated.get("hooks",{}).values():
  for group in groups:
   changed=[]
   for hook in group.get("hooks",[]):
    if shlex.split(hook["command"])[0]==marker+path:
     if seen==index:
      if action=="duplicate":changed.extend([hook,json.loads(json.dumps(hook))])
      elif action=="neutralize":
       hook=json.loads(json.dumps(hook));hook["command"]+=" >/dev/null 2>&1; true"
      elif action!="remove":raise AssertionError(action)
      seen+=1
      if action=="remove":continue
     else:seen+=1
    changed.append(hook)
   group["hooks"]=changed
 assert seen>index,(path,index,seen)
 return mutated

def mutate_nth_manifest_entrypoint(manifest:dict,path:str,index:int,action:str)->dict:
 mutated=json.loads(json.dumps(manifest));seen=0;changed=[]
 for gate in mutated.get("gates",[]):
  if gate.get("blocking") and gate.get("hook")==path:
   if seen==index:
    if action=="duplicate":changed.extend([gate,json.loads(json.dumps(gate))])
    elif action!="remove":raise AssertionError(action)
    seen+=1
    if action=="remove":continue
   else:seen+=1
  changed.append(gate)
 mutated["gates"]=changed;assert seen>index,(path,index,seen)
 return mutated

def configured_entrypoints()->set[str]:
 source,manifest,generated=entrypoint_surfaces()
 assert not entrypoint_surface_problems(source,manifest,generated),entrypoint_surface_problems(source,manifest,generated)
 return REQUIRED_SOURCE_ENTRYPOINTS|REQUIRED_MANIFEST_ENTRYPOINTS|REQUIRED_GENERATED_SETTINGS_ENTRYPOINTS

def helper_assignment_use_sites(entrypoints:set[str],overrides:dict[str,str]|None=None)->list[tuple[str,str,int,str,str,int,str]]:
 helper_names={path.name for path in (ROOT/"hooks/lib").iterdir() if path.is_file()};uses=[];overrides=overrides or {}
 for entrypoint in sorted(entrypoints):
  lines=overrides.get(entrypoint,(ROOT/entrypoint).read_text()).splitlines()
  for assignment_index,line in enumerate(lines):
   assignment=line.strip()
   if not assignment or assignment.startswith("#"):continue
   for helper in helper_names:
    match=re.match(r'^(?:local )?([A-Za-z_][A-Za-z0-9_]*)=".*'+re.escape(helper)+r'"$',assignment)
    if not match:continue
    variable=match.group(1);operand=r'"\$(?:\{'+re.escape(variable)+r'\}|'+re.escape(variable)+r')"'
    terminator=r"(?=$|[\s;)|&])"
    command_prefix=r"(?:^|[|;]|&&|\|\||\$\()\s*"
    python_call=re.compile(command_prefix+r"python3\s+"+operand+terminator)
    source_call=re.compile(r"^(?:source|\.)\s+"+operand+terminator)
    for use_index,later in enumerate(lines[assignment_index+1:],assignment_index+1):
     use=later.strip()
     if python_call.search(use) or source_call.search(use):
      uses.append((entrypoint,f"hooks/lib/{helper}",assignment_index,assignment,variable,use_index,use))
 return uses

def helper_invocation_sites(entrypoints:set[str],overrides:dict[str,str]|None=None)->list[tuple[str,str,str]]:
 helper_names={path.name for path in (ROOT/"hooks/lib").iterdir() if path.is_file()};sites=[];overrides=overrides or {}
 assignment_uses=helper_assignment_use_sites(entrypoints,overrides)
 assignments={(source,target,assignment_index,assignment) for source,target,assignment_index,assignment,_,_,_ in assignment_uses}
 sites.extend((source,target,assignment) for source,target,_,assignment in sorted(assignments))
 for entrypoint in entrypoints:
  text=overrides.get(entrypoint,(ROOT/entrypoint).read_text())
  for line in text.splitlines():
   stripped=line.strip()
   if not stripped or stripped.startswith("#"):continue
   for helper in helper_names:
    if helper not in stripped:continue
    sourced=bool(re.match(r"^(?:source|\.)\s+.*"+re.escape(helper),stripped))
    literal_operand=r'"[^"]*'+re.escape(helper)+r'"'
    executed=helper!="probe-runner.py" and bool(re.search(r"(?:^|[|;]|&&|\|\||\$\()\s*python3\s+"+literal_operand+r"(?=$|[\s;)|&])",stripped))
    evidence_validation=helper=="probe-runner.py" and 'doc.get("generator") != "probe-runner.py"' in stripped
    if sourced or executed or evidence_validation:sites.append((entrypoint,f"hooks/lib/{helper}",stripped))
 return sites

def helper_site_problems(entrypoints:set[str],overrides:dict[str,str]|None=None)->list[tuple]:
 sites=helper_invocation_sites(entrypoints,overrides);problems=[]
 if records_digest(sites)!=REQUIRED_HELPER_INVOCATION_SITES_SHA256:problems.append(("invocation site digest",records_digest(sites)))
 return problems

def helper_use_problems(entrypoints:set[str],overrides:dict[str,str]|None=None)->list[tuple]:
 uses=helper_assignment_use_sites(entrypoints,overrides);problems=[]
 digest_records=[(source,target,assignment,use) for source,target,_,assignment,_,_,use in uses]
 if records_digest(digest_records)!=REQUIRED_HELPER_ASSIGNMENT_USE_SITES_SHA256:problems.append(("assignment use digest",records_digest(digest_records)))
 for edge,expected in REQUIRED_HELPER_USE_COUNTS.items():
  actual=sum(1 for source,target,*_ in uses if (source,target)==edge)
  if actual!=expected:problems.append((edge,expected,actual))
 observed={(source,target) for source,target,*_ in uses}
 if observed!=set(REQUIRED_HELPER_USE_COUNTS):problems.append(("assignment edge drift",sorted(observed^set(REQUIRED_HELPER_USE_COUNTS))))
 return problems

def replace_line_index(text:str,index:int,replacement:str)->str:
 lines=text.splitlines(keepends=True);assert index<len(lines),(index,len(lines));newline="\n" if lines[index].endswith("\n") else "";indent=lines[index][:len(lines[index])-len(lines[index].lstrip())]
 lines[index]=indent+replacement+newline
 return "".join(lines)

def insert_line_after_index(text:str,index:int,content:str)->str:
 lines=text.splitlines(keepends=True);assert index<len(lines),(index,len(lines));newline="\n" if lines[index].endswith("\n") else ""
 lines.insert(index+1,content+newline)
 return "".join(lines)

def replace_nth_line(text:str,site:str,replacement:str,index:int)->str:
 lines=text.splitlines(keepends=True);matches=[i for i,line in enumerate(lines) if line.strip()==site]
 assert index<len(matches),(site,index,matches)
 return replace_line_index(text,matches[index],replacement)

def ci_site_problems(overrides:dict[str,str]|None=None)->list[tuple]:
 overrides=overrides or {};problems=[]
 for source,target,site,count in CI_INVOCATION_SITES:
  text=overrides.get(source,(ROOT/source).read_text());actual=sum(1 for line in text.splitlines() if line.strip()==site)
  if actual!=count:problems.append((source,target,site,count,actual))
 return problems

def verify_dependency_graph()->None:
 source_settings,manifest,generated_settings=entrypoint_surfaces()
 assert not entrypoint_surface_problems(source_settings,manifest,generated_settings),entrypoint_surface_problems(source_settings,manifest,generated_settings)
 # Remove every registration from its actual parsed surface and require the
 # independent snapshot comparison to fail, including helper-free blockers.
 for path,count in REQUIRED_SOURCE_ENTRYPOINT_COUNTS.items():
  for occurrence in range(count):
   for action in ("remove","duplicate","neutralize"):
    mutated=mutate_nth_settings_entrypoint(source_settings,"/path/to/claude-configs-public/",path,occurrence,action)
    assert entrypoint_surface_problems(mutated,manifest,generated_settings),(f"source registration {action} undetected",path,occurrence)
 for path,count in REQUIRED_MANIFEST_ENTRYPOINT_COUNTS.items():
  for occurrence in range(count):
   for action in ("remove","duplicate"):
    mutated=mutate_nth_manifest_entrypoint(manifest,path,occurrence,action)
    assert entrypoint_surface_problems(source_settings,mutated,generated_settings),(f"manifest registration {action} undetected",path,occurrence)
 for path,count in REQUIRED_GENERATED_SETTINGS_ENTRYPOINT_COUNTS.items():
  for occurrence in range(count):
   for action in ("remove","duplicate","neutralize"):
    mutated=mutate_nth_settings_entrypoint(generated_settings,"/path/to/",path,occurrence,action)
    assert entrypoint_surface_problems(source_settings,manifest,mutated),(f"generated settings {action} undetected",path,occurrence)
 entrypoints=REQUIRED_SOURCE_ENTRYPOINTS|REQUIRED_MANIFEST_ENTRYPOINTS|REQUIRED_GENERATED_SETTINGS_ENTRYPOINTS
 for path in entrypoints:assert tier([path])=="C",("entrypoint",path)
 helper_sites=helper_invocation_sites(entrypoints);helper_edges={(source,target) for source,target,_ in helper_sites}
 assert helper_edges==REQUIRED_HELPER_EDGES,("helper edge drift",sorted(helper_edges^REQUIRED_HELPER_EDGES))
 assert not helper_site_problems(entrypoints),helper_site_problems(entrypoints)
 assert not helper_use_problems(entrypoints),helper_use_problems(entrypoints)
 for edge in REQUIRED_HELPER_EDGES:
  sites=[site for source,target,site in helper_sites if (source,target)==edge]
  assert len(sites)==1,("helper invocation site drift",edge,sites)
  source,target=edge;expected="B" if target in ADVISORY_DEPENDENCY_EXCLUSIONS else "C"
  assert tier([target])==expected,(target,expected)
  original=(ROOT/source).read_text();mutated=original.replace(sites[0],"removed-helper-site",1)
  observed={(a,b) for a,b,_ in helper_invocation_sites({source},{source:mutated})}
  assert edge not in observed,("helper assignment/source removal undetected",edge,sites[0])
 # Removing each actual variable execution/source must also fail the chain
 # audit; retaining only the helper-path assignment is not sufficient.
 helper_uses=helper_assignment_use_sites(entrypoints)
 assignments={(source,target,assignment_index,assignment,variable) for source,target,assignment_index,assignment,variable,_,_ in helper_uses}
 for source,target,assignment_index,_,variable in assignments:
  original=(ROOT/source).read_text();decoy=f'{variable}="/tmp/not-the-helper" # {Path(target).name}'
  decoy_text=replace_line_index(original,assignment_index,decoy)
  observed={(a,b) for a,b,_ in helper_invocation_sites({source},{source:decoy_text})}
  assert (source,target) not in observed,("helper assignment comment decoy accepted",source,target,assignment_index,decoy)
 for source,target,_,_,variable,use_index,use_site in helper_uses:
  original=(ROOT/source).read_text()
  removed=replace_line_index(original,use_index,"removed-helper-use")
  assert helper_use_problems(entrypoints,{source:removed}),("helper use removal undetected",source,target,use_index,use_site)
  duplicated=insert_line_after_index(original,use_index,use_site)
  assert helper_use_problems(entrypoints,{source:duplicated}),("helper use duplication undetected",source,target,use_index,use_site)
  operand=re.compile(r'"\$(?:\{'+re.escape(variable)+r'\}|'+re.escape(variable)+r')"')
  decoy=operand.sub('"$OTHER_HELPER"',use_site,1)+f" # ${variable}"
  assert decoy!=use_site;decoy_text=replace_line_index(original,use_index,decoy)
  assert helper_use_problems(entrypoints,{source:decoy_text}),("helper decoy execution accepted",source,target,use_index,decoy)
  python_operand=re.compile(r"python3\s+"+operand.pattern)
  nonexecuting=python_operand.sub(lambda match:"echo "+match.group(0),use_site,1) if python_operand.search(use_site) else "echo "+use_site
  assert nonexecuting!=use_site;nonexecuting_text=replace_line_index(original,use_index,nonexecuting)
  assert helper_use_problems(entrypoints,{source:nonexecuting_text}),("non-executing helper text accepted",source,target,use_index,nonexecuting)
 assert not ci_site_problems(),ci_site_problems()
 for source,target,site,count in CI_INVOCATION_SITES:
  assert tier([source])=="C",source;assert tier([target])=="C",target
  original=(ROOT/source).read_text()
  for occurrence in range(count):
   mutated=replace_nth_line(original,site,"removed-ci-site",occurrence)
   assert ci_site_problems({source:mutated}),("CI invocation removal undetected",source,target,site,occurrence)

def verify_generated_output_exclusions()->None:
 # Generated catalogs stay Tier A only because their Tier C checkers recompute
 # expected bytes. Exercise the real CLI for both modified and missing output,
 # then require the checked-in output to pass again.
 for checker,catalog in [
  ("bin/generated-source-authority.py","catalog/generated-source-authority.json"),
  ("bin/kernel-budget.py","catalog/kernel-budget.json"),
 ]:
  with tempfile.TemporaryDirectory() as raw:
   mutated=Path(raw)/Path(catalog).name;mutated.write_text((ROOT/catalog).read_text()+"\n")
   changed=subprocess.run([sys.executable,str(ROOT/checker),"--catalog",str(mutated),"--check"],cwd=ROOT,text=True,capture_output=True)
   assert changed.returncode!=0,(checker,"modified output accepted",changed.stdout,changed.stderr)
   mutated.unlink()
   deleted=subprocess.run([sys.executable,str(ROOT/checker),"--catalog",str(mutated),"--check"],cwd=ROOT,text=True,capture_output=True)
   assert deleted.returncode!=0,(checker,"deleted output accepted",deleted.stdout,deleted.stderr)
  current=subprocess.run([sys.executable,str(ROOT/checker),"--check"],cwd=ROOT,text=True,capture_output=True)
  assert current.returncode==0,(checker,"current output rejected",current.stdout,current.stderr)
def declared_b(repo:Path,*args:str)->dict:
 result=subprocess.run(
  [sys.executable,str(SCRIPT),"--repo",str(repo),*args,"--declared","B"],
  text=True,capture_output=True,
 )
 assert result.returncode==2,(args,result.stdout,result.stderr)
 payload=json.loads(result.stdout)
 assert payload["computed_tier"]=="C" and not payload["valid"],payload
 return payload

def main():
 verify_dependency_graph()
 verify_generated_output_exclusions()
 assert tier(["README.md","plans/note.md"])=="A"
 assert tier(["catalog/skills-inventory.json"])=="A"
 assert tier(["skills/python/SKILL.md"])=="B"
 assert tier(["src/app.py"])=="B"
 assert tier(["hooks/agent-comms/status.sh"])=="B"
 # Enforcement authority code, its immutable selection receipt, the reviewed
 # contract and the tests that advertise those semantics must change together
 # under Tier C. Mutable policy/fixture candidates remain proposals, not proof.
 for path in AUTHORITY_DEPENDENCY_FLOOR:assert tier([path])=="C",("authority dependency",path)
 for path in ["catalog/effective-policy.json","examples/scaffolding/strict-release-policy.json","examples/scaffolding/synthetic-trunk-policy.json"]:assert tier([path])=="B",("proposal content",path)
 for path in ["hooks/git/self-review.sh","hooks/resolver/skill-enforcement-gate.sh","hooks/resolver/inject-resolver.sh","hooks/settings-snippet.json",".github/workflows/build-and-publish.yml","skills/KERNEL.md","bin/install.sh","bin/resolve-load-set.py","bin/skill-lifecycle.py","bin/data-scope.py","bin/_test/data_scope_test.py","catalog/data-scope-ledger.json","catalog/data-scope-fixtures.json","catalog/review-risk-policy.json","catalog/resolver-manifest.json","catalog/skill-lifecycle-approved-exceptions.json","auth/token.py","VERSION",*AUDITED_ENFORCEMENT_DEPENDENCIES]:assert tier([path])=="C",path
 for path in ["hooks/lib/log-block.sh","hooks/create-ticket/scaffold-test-stub.sh","bin/review-risk-metrics.py","hooks/agent-comms/future-advisory.sh"]:assert tier([path])=="B",path
 for path in ["catalog/generated-source-authority.json","catalog/kernel-budget.json"]:assert tier([path])=="A",path
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
  (repo/"hooks/git").mkdir(parents=True);(repo/"hooks/git/gate.sh").write_text("guard\n")
  for dependency in AUDITED_ENFORCEMENT_DEPENDENCIES:
   candidate=repo/dependency;candidate.parent.mkdir(parents=True,exist_ok=True);candidate.write_text("enforcement dependency\n")
  subprocess.run(["git","add","-f","."],cwd=repo,check=True);subprocess.run(["git","commit","-qm","base"],cwd=repo,check=True)
  root_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=repo,text=True).strip();assert tier(m.changed_paths(repo,commit=root_commit))=="C"
  # Every audited dependency retains its Tier C floor for modification,
  # deletion, and rename source paths. Each staged shape must reject a
  # declared Tier B rather than relying only on direct --paths fixtures.
  (repo/"docs").mkdir()
  for index,dependency in enumerate(AUDITED_ENFORCEMENT_DEPENDENCIES):
   candidate=repo/dependency
   candidate.write_text(candidate.read_text()+"modified\n");subprocess.run(["git","add","-f",dependency],cwd=repo,check=True)
   assert tier(m.changed_paths(repo,staged=True))=="C",("modify",dependency)
   declared_b(repo,"--staged")
   subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True)
   candidate.unlink();subprocess.run(["git","add","-u",dependency],cwd=repo,check=True)
   assert tier(m.changed_paths(repo,staged=True))=="C",("delete",dependency)
   declared_b(repo,"--staged")
   subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True)
   (repo/"docs").mkdir(exist_ok=True)
   renamed=f"docs/renamed-{index}.md";subprocess.run(["git","mv",dependency,renamed],cwd=repo,check=True)
   assert tier(m.changed_paths(repo,staged=True))=="C",("rename",dependency)
   declared_b(repo,"--staged")
   subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True)
  subprocess.run(["git","mv","hooks/git/gate.sh","README.md"],cwd=repo,check=True)
  assert tier(m.changed_paths(repo,staged=True))=="C"
  subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True);(repo/"hooks/git/gate.sh").unlink();subprocess.run(["git","add","-u"],cwd=repo,check=True)
  assert tier(m.changed_paths(repo,staged=True))=="C"
  subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True)
  unusual=["hooks/git/gate\t.sh","hooks/git/gate\n.sh","hooks/git/gaté.sh"]
  for name in unusual:(repo/name).write_text("guard\n")
  subprocess.run(["git","add","-A"],cwd=repo,check=True)
  observed=m.changed_paths(repo,staged=True)
  assert set(unusual)<=set(observed),observed
  assert tier(observed)=="C"
  subprocess.run(["git","reset","--hard","-q","HEAD"],cwd=repo,check=True)
  resolver_newline="hooks/resolver/new\nthink-gate-guard.sh"
  (repo/"hooks/resolver").mkdir(parents=True,exist_ok=True);(repo/resolver_newline).write_text("guard\n")
  subprocess.run(["git","add","-A"],cwd=repo,check=True)
  added=m.changed_paths(repo,staged=True)
  assert resolver_newline in added,added
  assert tier(added)=="C",added
  subprocess.run(["git","commit","-qm","add newline resolver gate"],cwd=repo,check=True)
  (repo/resolver_newline).unlink();subprocess.run(["git","add","-u"],cwd=repo,check=True)
  deleted=m.changed_paths(repo,staged=True)
  assert resolver_newline in deleted,deleted
  assert tier(deleted)=="C",deleted
 print("review_risk_test: PASS")
if __name__=="__main__":main()
