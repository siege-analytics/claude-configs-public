#!/usr/bin/env python3
"""Invoke the shipped prompt hook over real, project-composed package content.

These are local adapter observations. They do not establish host registration,
backend delivery, package authenticity or authorization.
"""
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("resident_composer",ROOT/"bin/compose-project.py")
composer=importlib.util.module_from_spec(spec);spec.loader.exec_module(composer)


class ResidentDeliveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix="resident-delivery-")
        cls.root=Path(cls.temp.name)
        cls.dist=cls.root/"dist"
        # The shell hook must use the same supported Python as this test.
        python_bin=cls.root/"python-bin";python_bin.mkdir()
        (python_bin/"python3").symlink_to(sys.executable)
        cls.env={**os.environ,"PATH":str(python_bin)+os.pathsep+os.environ.get("PATH",""),
                 "PYTHONDONTWRITEBYTECODE":"1","CRAFT_AGENT_PLANS_PATH":"/nonexistent",
                 "CLAUDE_PROGRESSIVE_LOADING":"on"}
        cls.env.pop("CLAUDE_KERNEL_PATH",None)
        built=subprocess.run([sys.executable,"-B","bin/build.py","--dist",str(cls.dist)],cwd=ROOT,
                             env=cls.env,text=True,capture_output=True)
        if built.returncode:raise RuntimeError(built.stdout+built.stderr)
        for project in ("strict-release","synthetic-trunk"):
            composer.package(ROOT/"examples/composition",cls.root/project,"github.example.invalid/synthetic-org/"+project)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def payload(self,project="strict-release",layout="flat"):
        temp=tempfile.TemporaryDirectory(prefix="resident-case-");self.addCleanup(temp.cleanup)
        root=Path(temp.name);payload=root/"payload"
        # Exactly the generic runtime dependencies plus the complete composition
        # last. Selected files and hook are genuine generated package artifacts.
        for name in ("bin","catalog","hooks"):
            shutil.copytree(self.dist/layout/name,payload/name)
        (payload/"skills").mkdir()
        shutil.copy2(self.dist/layout/"skills/KERNEL.md",payload/"skills/KERNEL.md")
        shutil.copytree(self.root/project/layout,payload,dirs_exist_ok=True)
        repo=root/"consumer";repo.mkdir()
        subprocess.run(["git","init","-q",str(repo)],check=True)
        subprocess.run(["git","-C",str(repo),"remote","add","origin","https://github.example.invalid/synthetic-org/"+project+".git"],check=True)
        return payload,repo

    def hook(self,payload,repo,prompt="review candidate",**env):
        p=subprocess.run(["bash",str(payload/"hooks/resolver/inject-resolver.sh")],
                         input=json.dumps({"prompt":prompt,"cwd":str(repo)}),cwd=repo,
                         env={**self.env,**env},text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
        return p.stdout

    def kernel_only(self,output):
        self.assertEqual(output.count("<skill-kernel "),1,output)
        self.assertNotIn("<project-resident>",output)
        self.assertNotIn("STRICT_OVERLAY",output)
        self.assertNotIn("TRUNK_OVERLAY",output)
        self.assertNotRegex(output,r"(?m)^(load|candidate):")

    @staticmethod
    def change_json(path,change):
        value=json.loads(path.read_text());change(value);path.write_text(json.dumps(value))

    def test_both_projects_and_layouts_deliver_exact_resident_once(self):
        for project,marker,foreign,branch,slugs in (
            ("strict-release","STRICT_OVERLAY","TRUNK_OVERLAY","develop",["strict-release--review","strict-release--checks"]),
            ("synthetic-trunk","TRUNK_OVERLAY","STRICT_OVERLAY","main",["hostile-review"]),
        ):
            for layout in ("nested","flat"):
                with self.subTest(project=project,layout=layout):
                    payload,repo=self.payload(project,layout);out=self.hook(payload,repo)
                    self.assertEqual(out.count("<skill-kernel "),1)
                    self.assertEqual(out.count("<project-resident>"),1)
                    self.assertEqual(out.count(marker),1)
                    self.assertNotIn(foreign,out)
                    self.assertNotIn("STRICT_PROJECT_RULE",out)
                    self.assertNotIn("TRUNK_PROJECT_RULE",out)
                    self.assertIn("Feature and fix work targets `"+branch+"`",out)
                    self.assertIn("For the Siege scaffold repository",out)
                    self.assertIn("(`github.com/siege-analytics/claude-configs-public`)",out)
                    self.assertIn("Other consumers follow their exact, independently approved project topology",out)
                    self.assertIn((payload/"skills/KERNEL.md").read_text(),out)
                    resident=out.split("<project-resident>\n",1)[1].split("\n</project-resident>",1)[0]
                    self.assertEqual(resident,(payload/"skills/RESIDENT.md").read_text())
                    self.assertEqual(re.findall(r"(?m)^load: ([^ ]+)",out),slugs)
                    for path in re.findall(r"\| path=([^\n]+?) \| source=",out):
                        self.assertTrue(Path(path).is_file())
                    self.assertTrue(Path(path).is_relative_to(payload.resolve()))

    def test_unknown_task_retains_only_exact_matched_project_context(self):
        payload,repo=self.payload();out=self.hook(payload,repo,"hello")
        self.assertIn("state: unknown",out)
        self.assertEqual(out.count("STRICT_OVERLAY"),1)
        self.assertNotRegex(out,r"(?m)^load:")

    def test_identity_normalization_and_foreign_port_alias_rejection(self):
        payload,repo=self.payload()
        for identity,allowed in (("https://GITHUB.EXAMPLE.INVALID/SYNTHETIC-ORG/STRICT-RELEASE.git",True),
                                 ("https://github.example.invalid:443/synthetic-org/strict-release",False),
                                 ("https://github.example.invalid/foreign/strict-release",False),
                                 ("https://github.example.invalid/synthetic-org/synthetic-trunk",False),
                                 ("strict-release",False)):
            with self.subTest(identity=identity):
                subprocess.run(["git","-C",str(repo),"remote","set-url","origin",identity],check=True)
                out=self.hook(payload,repo)
                if allowed:self.assertIn("STRICT_OVERLAY",out)
                else:self.kernel_only(out);self.assertIn("state: error",out)
        subprocess.run(["git","-C",str(repo),"remote","remove","origin"],check=True)
        self.kernel_only(self.hook(payload,repo))

    def test_receipt_tampering_never_emits_partial_project_content(self):
        changes={
            "identity":lambda d:d.update(identity="github.example.invalid/foreign/strict-release"),
            "project":lambda d:d.update(project="synthetic-trunk"),
            "rendered":lambda d:d["resident"].update(rendered="FORGED_RESIDENT"),
            "characters":lambda d:d["resident"].update(characters=True),
            "tokens":lambda d:d["resident"].update(estimated_tokens=1),
            "state":lambda d:d.update(evidence_state="verified"),
            "authorization":lambda d:d.update(authorization_effect="allow"),
            "resident_authorization":lambda d:d["resident"].update(authorization_effect="allow"),
            "resident_project":lambda d:d["resident"].update(project="synthetic-trunk"),
        }
        for name,change in changes.items():
            with self.subTest(name=name):
                payload,repo=self.payload();self.change_json(payload/"composition.json",change)
                out=self.hook(payload,repo);self.kernel_only(out);self.assertIn("state: error",out)

    def test_missing_changed_and_symlinked_files_reject(self):
        for relative in ("composition.json","skills/RESIDENT.md","catalog/resolver-manifest.json",
                         "catalog/skills-inventory.json","skills/strict-release--checks/SKILL.md"):
            for variant in ("missing","symlink","changed"):
                with self.subTest(relative=relative,variant=variant):
                    payload,repo=self.payload();path=payload/relative
                    if variant=="changed" and relative.endswith("SKILL.md"):
                        continue # Skills are selected readable content, not authenticated by the resident receipt.
                    if variant=="changed":path.write_text("not the expected content")
                    else:
                        outside=payload.parent/"saved-input";shutil.copy2(path,outside);path.unlink()
                        if variant=="symlink":path.symlink_to(outside)
                    out=self.hook(payload,repo)
                    self.kernel_only(out);self.assertIn("state: error",out)

    def test_symlinked_parent_and_escaped_selected_path_reject(self):
        for variant in ("symlink-directory","escape","absolute","resident-path"):
            with self.subTest(variant=variant):
                payload,repo=self.payload()
                if variant=="symlink-directory":
                    path=payload/"skills/strict-release--checks";outside=payload.parent/"external-skill"
                    path.rename(outside);path.symlink_to(outside,target_is_directory=True)
                elif variant=="resident-path":
                    self.change_json(payload/"catalog/resolver-manifest.json",lambda d:d.update(kernel="skills/RULES_BUNDLE.md"))
                else:
                    def change(d):
                        item=next(i for i in d["items"] if i["slug"]=="strict-release--checks")
                        item["package_path"]="../outside.md" if variant=="escape" else "/etc/hosts"
                    self.change_json(payload/"catalog/skills-inventory.json",change)
                out=self.hook(payload,repo);self.kernel_only(out);self.assertIn("state: error",out)

    def test_budget_and_ambiguous_selection_emit_no_resident(self):
        for variant in ("resident-budget","selection-budget","ambiguous"):
            with self.subTest(variant=variant):
                payload,repo=self.payload()
                if variant=="resident-budget":
                    text="X"*80001;(payload/"skills/RESIDENT.md").write_text(text)
                    self.change_json(payload/"composition.json",lambda d:d["resident"].update(rendered=text,characters=len(text),estimated_tokens=(len(text)+3)//4))
                elif variant=="selection-budget":
                    def change(d):
                        for item in d["items"]:item["characters"]=80001
                    self.change_json(payload/"catalog/skills-inventory.json",change)
                else:
                    def change(d):
                        route=d["routes"][0];route["exclusive_group"]="probe"
                        d["routes"].append({**route,"id":"ambiguous-review"})
                    self.change_json(payload/"catalog/resolver-manifest.json",change)
                out=self.hook(payload,repo);self.kernel_only(out)
                self.assertIn("state: "+{"resident-budget":"error","selection-budget":"over-budget","ambiguous":"ambiguous"}[variant],out)

    def test_candidate_disabled_and_noop_controls_do_not_deliver_resident(self):
        payload,repo=self.payload()
        for mode in ("off","kernel-only","canary"):
            with self.subTest(mode=mode):
                out=self.hook(payload,repo,CLAUDE_PROGRESSIVE_LOADING=mode)
                self.assertNotIn("STRICT_OVERLAY",out);self.assertNotIn("<project-resident>",out)
                self.assertNotRegex(out,r"(?m)^load:")
                if mode=="canary":
                    self.assertIn("resident-candidate: skills/RESIDENT.md",out)
                    self.assertIn("candidate: strict-release--review",out)
                else:self.assertIn("state: disabled",out)
        hook=payload/"hooks/resolver/inject-resolver.sh";hook.write_text("#!/bin/bash\nexit 0\n")
        self.assertEqual(self.hook(payload,repo),"")

    def test_canonical_kernel_override_integrity_is_unchanged(self):
        payload,repo=self.payload();alternate=payload.parent/"alternate.md"
        alternate.write_text((payload/"skills/KERNEL.md").read_text()+"\nFORGED_KERNEL\n")
        out=self.hook(payload,repo,CLAUDE_KERNEL_PATH=str(alternate))
        self.assertIs(json.loads(out)["continue"],False)
        self.assertNotIn("FORGED_KERNEL",out);self.assertNotIn("STRICT_OVERLAY",out)
        shutil.copy2(payload/"skills/KERNEL.md",alternate)
        self.assertEqual(self.hook(payload,repo),self.hook(payload,repo,CLAUDE_KERNEL_PATH=str(alternate)))

    def test_selector_is_invoked_once_and_invalid_result_is_atomic(self):
        for invalid in (False,True):
            with self.subTest(invalid=invalid):
                payload,repo=self.payload();selector=payload/"bin/resolve-load-set.py"
                original=selector.with_name("original-selector.py");selector.rename(original)
                counter=payload/"selector-count"
                wrapper=("import importlib.util\nfrom pathlib import Path\n"
                         f"counter=Path({str(counter)!r})\n"
                         "with counter.open('a') as f:f.write('called\\n')\n"
                         f"spec=importlib.util.spec_from_file_location('original_selector',{str(original)!r})\n"
                         "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\n")
                if invalid:
                    wrapper+=("original_select=m.select\n"
                              "def invalid_select(*args):\n"
                              "    result=original_select(*args);result['state']='invalid';return result\n"
                              "m.select=invalid_select\n")
                selector.write_text(wrapper+"raise SystemExit(m.main())\n")
                out=self.hook(payload,repo)
                self.assertEqual(counter.read_text(),"called\n")
                if invalid:self.kernel_only(out);self.assertIn("state: error",out)
                else:self.assertEqual(out.count("STRICT_OVERLAY"),1)

    def test_unavailable_selector_and_missing_kernel_do_not_load_project(self):
        payload,repo=self.payload();(payload/"bin/resolve-load-set.py").unlink()
        out=self.hook(payload,repo);self.kernel_only(out)
        self.assertIn("Selector unavailable",out)
        (payload/"skills/KERNEL.md").unlink()
        self.assertIs(json.loads(self.hook(payload,repo))["continue"],False)


if __name__=="__main__":unittest.main()
