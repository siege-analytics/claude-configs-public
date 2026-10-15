#!/usr/bin/env python3
from __future__ import annotations
import importlib.util,json,re,shlex,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];SCRIPT=ROOT/"bin/review-risk.py"
spec=importlib.util.spec_from_file_location("review_risk",SCRIPT);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
policy=json.loads((ROOT/"catalog/review-risk-policy.json").read_text())
AUDITED_ENFORCEMENT_DEPENDENCIES = [
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
 "hooks/_test/review_risk_policy.test.sh",
]
ADVISORY_DEPENDENCY_EXCLUSIONS = {"hooks/lib/log-block.sh"}
CI_INVOCATION_SITES = [
 ("bin/generated-source-authority.py","bin/skill-inventory.py",'[sys.executable, str(root / "bin" / "skill-inventory.py"), "--check"],',1),
 ("bin/generated-source-authority.py","bin/build.py",'[sys.executable, str(root / "bin" / "build.py"), "--dist", str(fresh_dist)],',1),
 ("bin/kernel-budget.py","bin/generated-source-authority.py",'[sys.executable, str(root / "bin" / "generated-source-authority.py"), "--check"],',1),
 (".github/workflows/build-and-publish.yml","bin/build.py","run: python3 bin/build.py --check",1),
 (".github/workflows/build-and-publish.yml","bin/build.py","run: python3 bin/build.py",2),
 (".github/workflows/build-and-publish.yml","bin/generated-source-authority.py","python3 bin/generated-source-authority.py --check",1),
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
def tier(paths):return m.classify(policy,paths)["computed_tier"]

def settings_entrypoints(settings:dict,marker:str)->set[str]:
 paths=set()
 for groups in settings.get("hooks",{}).values():
  for group in groups:
   for hook in group.get("hooks",[]):
    command=shlex.split(hook["command"])[0];assert command.startswith(marker),command
    paths.add(command[len(marker):])
 return paths

def configured_entrypoints()->set[str]:
 # Parse the actual canonical registry, then run an isolated build and parse its
 # emitted blocking manifest/settings. This catches generated entrypoints even
 # when build.py stops spelling them as one of the old literal string shapes.
 source=json.loads((ROOT/"hooks/settings-snippet.json").read_text())
 paths=settings_entrypoints(source,"/path/to/claude-configs-public/")
 with tempfile.TemporaryDirectory(prefix="review-risk-entrypoints-") as raw:
  dist=Path(raw);built=subprocess.run([sys.executable,str(ROOT/"bin/build.py"),"--dist",str(dist)],cwd=ROOT,text=True,capture_output=True)
  assert built.returncode==0,(built.stdout,built.stderr)
  manifest=json.loads((dist/"craft-agent/enforcement-manifest.json").read_text())
  paths.update(gate["hook"] for gate in manifest["gates"] if gate.get("blocking"))
  generated=json.loads((dist/"craft-agent/settings-enforcement.json").read_text())
  paths.update(settings_entrypoints(generated,"/path/to/"))
 return paths

def helper_invocation_sites(entrypoints:set[str],overrides:dict[str,str]|None=None)->set[tuple[str,str,str]]:
 helper_names={path.name for path in (ROOT/"hooks/lib").iterdir() if path.is_file()};sites=set();overrides=overrides or {}
 for entrypoint in entrypoints:
  text=overrides.get(entrypoint,(ROOT/entrypoint).read_text())
  for line in text.splitlines():
   stripped=line.strip()
   if not stripped or stripped.startswith("#"):continue
   for helper in helper_names:
    if helper not in stripped:continue
    assignment=bool(re.match(r"^(?:local )?[A-Za-z_][A-Za-z0-9_]*=.*"+re.escape(helper)+r'[^A-Za-z0-9_.-]*$',stripped))
    sourced=bool(re.match(r"^(?:source|\.)\s+.*"+re.escape(helper),stripped))
    executed=helper!="probe-runner.py" and "python3" in stripped and helper in stripped
    evidence_validation=helper=="probe-runner.py" and 'doc.get("generator") != "probe-runner.py"' in stripped
    if assignment or sourced or executed or evidence_validation:
     sites.add((entrypoint,f"hooks/lib/{helper}",stripped))
 return sites

def replace_nth_line(text:str,site:str,replacement:str,index:int)->str:
 lines=text.splitlines(keepends=True);matches=[i for i,line in enumerate(lines) if line.strip()==site]
 assert index<len(matches),(site,index,matches)
 i=matches[index];newline="\n" if lines[i].endswith("\n") else "";indent=lines[i][:len(lines[i])-len(lines[i].lstrip())]
 lines[i]=indent+replacement+newline
 return "".join(lines)

def ci_site_problems(overrides:dict[str,str]|None=None)->list[tuple]:
 overrides=overrides or {};problems=[]
 for source,target,site,count in CI_INVOCATION_SITES:
  text=overrides.get(source,(ROOT/source).read_text());actual=sum(1 for line in text.splitlines() if line.strip()==site)
  if actual!=count:problems.append((source,target,site,count,actual))
 return problems

def verify_dependency_graph()->None:
 entrypoints=configured_entrypoints();assert entrypoints
 for path in entrypoints:assert tier([path])=="C",("entrypoint",path)
 helper_sites=helper_invocation_sites(entrypoints);helper_edges={(source,target) for source,target,_ in helper_sites}
 assert helper_edges==REQUIRED_HELPER_EDGES,("helper edge drift",sorted(helper_edges^REQUIRED_HELPER_EDGES))
 for edge in REQUIRED_HELPER_EDGES:
  sites=[site for source,target,site in helper_sites if (source,target)==edge]
  assert len(sites)==1,("helper invocation site drift",edge,sites)
  source,target=edge;expected="B" if target in ADVISORY_DEPENDENCY_EXCLUSIONS else "C"
  assert tier([target])==expected,(target,expected)
  original=(ROOT/source).read_text();mutated=original.replace(sites[0],"removed-helper-site",1)
  observed={(a,b) for a,b,_ in helper_invocation_sites({source},{source:mutated})}
  assert edge not in observed,("helper site removal undetected",edge,sites[0])
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
