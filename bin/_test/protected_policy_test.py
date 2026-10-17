#!/usr/bin/env python3
"""Disposable Git-operation tests for the #1002 protected policy pilot."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = Path("scripts/ci/protected-policy-range.py")


def run(*command: str, cwd: Path, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env, timeout=40)
    if check and result.returncode:
        raise AssertionError(f"{command} failed ({result.returncode})\nstdout={result.stdout}\nstderr={result.stderr}")
    return result


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run("git", *args, cwd=repo, check=check)


class ProtectedPolicyPilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = tempfile.TemporaryDirectory(prefix="protected-policy-pilot-")
        cls.temp = Path(cls.raw.name)
        cls.trusted = cls.temp / "trusted"
        run("git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(cls.trusted), cwd=cls.temp)
        git(cls.trusted, "config", "user.email", "fixture@example.invalid")
        git(cls.trusted, "config", "user.name", "Synthetic Fixture")
        # Hosted PR checkouts may have no local branches. Publish the synthetic
        # parent through an explicit branch so a later shallow clone can recover
        # its complete history from advertised refs. Its default workflow ref is
        # also fixture-owned, not inherited from the runner's local branch set.
        git(cls.trusted, "checkout", "-q", "-B", "fixture/trusted-parent")
        git(cls.trusted, "update-ref", "refs/remotes/origin/main", "HEAD")
        # Synthetic transport retains an explicit canonical parent identity.
        git(cls.trusted, "remote", "set-url", "origin", "https://github.com/siege-analytics/claude-configs-public.git")
        git(cls.trusted, "config", "url." + ROOT.as_uri() + ".insteadOf", "https://github.com/siege-analytics/claude-configs-public.git")
        # Commit the current candidate adapter into the disposable trusted base;
        # immutable-byte checks then exercise a real Git blob rather than a test escape.
        working_authority = (
            SCRIPT, Path("bin/_test/protected_policy_test.py"),
            Path("scripts/ci/check-branch-topology.sh"),
            Path(".github/workflows/pr-base-guard.yml"),
            Path("bin/effective_policy.py"), Path("bin/gate_contract.py"),
            Path("bundles/siege/policy-inputs.json"), Path("bundles/siege/protected-adapter.json"),
            Path("catalog/effective-policy-selection.json"),
            Path("catalog/gate-contract-schema.json"), Path("catalog/gate-contracts.json"),
        )
        for relative in working_authority:
            target = cls.trusted / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        git(cls.trusted, "add", *(path.as_posix() for path in working_authority))
        # Before publication the copied files create this commit; after they are
        # already tracked, an empty commit still gives every disposable run a
        # fresh immutable trusted revision without a test-only byte bypass.
        git(cls.trusted, "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-q", "-m", "pilot adapter #1002")
        cls.trusted_revision = git(cls.trusted, "rev-parse", "HEAD").stdout.strip()
        cls.packages: dict[str, Path] = {}
        for project in ("strict-release", "synthetic-trunk"):
            output = cls.temp / f"package-{project}"
            identity = f"github.example.invalid/synthetic-org/{project}"
            run(sys.executable, "bin/compose-project.py", "--identity", identity, "--output", str(output), cwd=cls.trusted)
            cls.packages[project] = output / "flat"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.raw.cleanup()

    def make_repo(self, project: str = "strict-release", *, configure_hook: bool = True) -> tuple[Path, str]:
        repo = Path(tempfile.mkdtemp(prefix=f"candidate-{project}-", dir=self.temp))
        run("git", "clone", "--quiet", "--no-hardlinks", str(self.trusted), str(repo), cwd=self.temp)
        git(repo, "config", "user.email", "fixture@example.invalid")
        git(repo, "config", "user.name", "Synthetic Fixture")
        git(repo, "remote", "set-url", "origin", f"https://github.example.invalid/synthetic-org/{project}.git")
        shutil.copytree(self.packages[project], repo / ".pilot")
        git(repo, "add", ".pilot")
        git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "install unchanged parent #1002")
        if configure_hook:
            git(repo, "config", "core.hooksPath", ".githooks")
        return repo, git(repo, "rev-parse", "HEAD").stdout.strip()

    def message(self, subject: str, *, ticket: bool = True) -> str:
        suffix = " #1002" if ticket else ""
        return f"{subject}{suffix}\n\nReview-Tier: A\nSelf-Review: synthetic disposable operation\n"

    def change(self, repo: Path, name: str, message: str, *, mode: str = "message", no_verify: bool = False) -> str:
        path = repo / f"{name}.md"
        path.write_text(f"# {name}\n", encoding="utf-8")
        git(repo, "add", path.name)
        verify = ["--no-verify"] if no_verify else []
        if mode == "file":
            message_file = repo / ".message"
            message_file.write_text(message, encoding="utf-8")
            git(repo, "commit", *verify, "-F", str(message_file))
        elif mode == "alias":
            git(repo, "config", "alias.record", "commit")
            git(repo, "record", *verify, "-m", message)
        elif mode == "chain":
            command = ["git", "commit", *verify, "-m", message]
            run("sh", "-c", "git status --short >/dev/null && " + " ".join(subprocess.list2cmdline([x]) for x in command), cwd=repo)
        else:
            git(repo, "commit", *verify, "-m", message)
        return git(repo, "rev-parse", "HEAD").stdout.strip()

    def evaluate(self, repo: Path, base: str, target: str, *, head: str | None = None,
                 head_branch: str = "feature/pilot",
                 trusted: Path | None = None, trusted_revision: str | None = None,
                 canonical_identity: str | None = None,
                 workflow_ref: str | None = None,
                 workflow_revision: str | None = None) -> tuple[int, dict]:
        exact_head = head or git(repo, "rev-parse", "HEAD").stdout.strip()
        trusted_root = trusted or self.trusted
        project = "synthetic-trunk" if "synthetic-trunk" in repo.name else "strict-release"
        canonical = canonical_identity or f"github.example.invalid/synthetic-org/{project}"
        selected_trusted_revision = trusted_revision or self.trusted_revision
        owner_repository = "/".join(canonical.split("/")[1:])
        command = [
            sys.executable, str(trusted_root / SCRIPT),
            "--trusted-root", str(trusted_root),
            "--trusted-revision", selected_trusted_revision,
            "--candidate-repo", str(repo),
            "--base", base,
            "--head", exact_head,
            "--canonical-identity", canonical,
            "--head-branch", head_branch,
            "--target-branch", target,
            "--executed-workflow-ref", workflow_ref or f"{owner_repository}/.github/workflows/pr-base-guard.yml@refs/heads/main",
            "--executed-workflow-revision", workflow_revision or selected_trusted_revision,
            "--installed-pilot-receipt", ".pilot/composition.json",
        ]
        result = run(*command, cwd=trusted_root, check=False)
        return result.returncode, json.loads(result.stdout)

    def topology(self, repo: Path, base: str, target: str, head_branch: str,
                 *, head_repository: str | None = None) -> subprocess.CompletedProcess[str]:
        project = "synthetic-trunk" if "synthetic-trunk" in repo.name else "strict-release"
        canonical = f"synthetic-org/{project}"
        git(repo, "update-ref", "refs/remotes/upstream/main", base)
        env = {
            **os.environ,
            "BASE_BRANCH": target,
            "HEAD_BRANCH": head_branch,
            "HEAD_REPO": head_repository or canonical,
            "CANONICAL_REPO": canonical,
            "MAIN_REF": "upstream/main",
        }
        return run(
            "bash", str(self.trusted / "scripts/ci/check-branch-topology.sh"),
            cwd=repo, check=False, env=env,
        )

    def test_canonical_promotion_and_full_chain_negatives(self):
        repo, base = self.make_repo("strict-release")
        self.change(repo, "promotion", self.message("canonical promotion"))
        old_guard = self.topology(repo, base, "main", "develop")
        self.assertEqual(old_guard.returncode, 0, old_guard.stdout + old_guard.stderr)
        code, receipt = self.evaluate(repo, base, "main", head_branch="develop")
        self.assertEqual((code, receipt["state"]), (0, "eligible"))
        self.assertEqual(receipt["candidate"]["operation"], "canonical-promotion")
        self.assertEqual(receipt["candidate"]["policy_evaluation_target"], "develop")
        self.assertEqual(receipt["candidate"]["target_branch"], "main")

        for head_branch in ("feature/pilot", "main"):
            with self.subTest(head_branch=head_branch):
                old_guard = self.topology(repo, base, "main", head_branch)
                self.assertNotEqual(old_guard.returncode, 0)
                code, denied = self.evaluate(repo, base, "main", head_branch=head_branch)
                self.assertEqual((code, denied["state"]), (1, "denied"))

        fork, fork_base = self.make_repo("strict-release")
        self.change(fork, "fork-promotion", self.message("fork promotion"))
        git(fork, "remote", "set-url", "origin", "https://github.example.invalid/foreign/strict-release.git")
        old_guard = self.topology(
            fork, fork_base, "main", "develop", head_repository="foreign/strict-release",
        )
        self.assertNotEqual(old_guard.returncode, 0)
        code, denied = self.evaluate(
            fork, fork_base, "main", head_branch="develop",
            canonical_identity="github.example.invalid/synthetic-org/strict-release",
        )
        self.assertEqual((code, denied["state"]), (1, "denied"))

    def test_same_develop_operation_differs_by_approved_profile(self):
        strict, strict_base = self.make_repo("strict-release")
        trunk, trunk_base = self.make_repo("synthetic-trunk")
        self.change(strict, "operation", self.message("same operation"))
        self.change(trunk, "operation", self.message("same operation"))
        code, strict_receipt = self.evaluate(strict, strict_base, "develop")
        self.assertEqual((code, strict_receipt["state"], strict_receipt["project"]), (0, "eligible", "strict-release"))
        self.assertEqual(strict_receipt["authorization"], "protected-host-check-required")
        code, denied = self.evaluate(trunk, trunk_base, "develop")
        self.assertEqual((code, denied["state"]), (1, "denied"))
        code, trunk_receipt = self.evaluate(trunk, trunk_base, "main")
        self.assertEqual((code, trunk_receipt["state"], trunk_receipt["project"]), (0, "eligible", "synthetic-trunk"))
        self.assertEqual(
            strict_receipt["candidate"]["installed_pilot"]["parent_content_sha256"],
            trunk_receipt["candidate"]["installed_pilot"]["parent_content_sha256"],
        )
        self.assertNotEqual(
            strict_receipt["candidate"]["installed_pilot"]["effective_policy_sha256"],
            trunk_receipt["candidate"]["installed_pilot"]["effective_policy_sha256"],
        )

    def test_real_file_alias_and_command_chain_commits_are_range_facts(self):
        repo, base = self.make_repo()
        self.change(repo, "file-message", self.message("file message"), mode="file")
        self.change(repo, "alias-message", self.message("alias message"), mode="alias")
        self.change(repo, "chain-message", self.message("chain message"), mode="chain")
        code, receipt = self.evaluate(repo, base, "develop")
        self.assertEqual(code, 0)
        self.assertEqual(len(receipt["candidate"]["commits"]), 3)

    def test_invalid_interior_commit_survives_valid_head_and_no_verify(self):
        repo, base = self.make_repo()
        self.change(repo, "bad-interior", self.message("bad interior", ticket=False), no_verify=True)
        self.change(repo, "valid-head", self.message("valid head"))
        code, receipt = self.evaluate(repo, base, "develop")
        self.assertEqual((code, receipt["state"]), (1, "denied"))
        self.assertIn("lacks required", receipt["diagnostic"])

    def test_missing_or_inert_local_hook_does_not_become_protected_evidence(self):
        absent, absent_base = self.make_repo(configure_hook=False)
        self.change(absent, "valid", self.message("valid without hook"), no_verify=True)
        code, receipt = self.evaluate(absent, absent_base, "develop")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["candidate"]["local_feedback"]["state"], "not-configured")
        self.assertEqual(receipt["candidate"]["local_feedback"]["authorization_effect"], "none")

        inert, inert_base = self.make_repo()
        hook = inert / ".githooks/commit-msg"
        hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hook.chmod(0o755)
        git(inert, "add", ".githooks/commit-msg")
        git(inert, "commit", "-m", self.message("inert hook replacement"))
        self.change(inert, "invalid", self.message("invalid through inert hook", ticket=False))
        code, receipt = self.evaluate(inert, inert_base, "develop")
        self.assertEqual((code, receipt["state"]), (1, "denied"))

    def test_stale_head_and_wrong_repository_fail_closed(self):
        repo, base = self.make_repo()
        first = self.change(repo, "first", self.message("first"))
        self.change(repo, "second", self.message("second"))
        code, stale = self.evaluate(repo, base, "develop", head=first)
        self.assertEqual((code, stale["state"]), (1, "denied"))
        git(repo, "remote", "set-url", "origin", "https://github.example.invalid:8443/synthetic-org/strict-release.git")
        code, port = self.evaluate(repo, base, "develop")
        self.assertEqual((code, port["state"]), (2, "error"))
        self.assertIn("port", port["diagnostic"])
        git(repo, "remote", "set-url", "origin", "https://github.example.invalid/foreign/repository.git")
        code, wrong = self.evaluate(repo, base, "develop")
        self.assertEqual((code, wrong["state"]), (1, "denied"))
        self.assertIn("source repository", wrong["diagnostic"])

    def test_unapproved_policy_edit_is_only_a_proposal(self):
        repo, base = self.make_repo()
        policy = repo / "catalog/effective-policy.json"
        data = json.loads(policy.read_text())
        data["organization_profiles"][0]["values"] = {"branch-policy": {"integration_branch": "main"}}
        policy.write_text(json.dumps(data, indent=2) + "\n")
        git(repo, "add", policy.relative_to(repo).as_posix())
        git(repo, "commit", "--no-verify", "-m", self.message("unapproved policy proposal"))
        code, denied = self.evaluate(repo, base, "main")
        self.assertEqual((code, denied["state"]), (1, "denied"))
        code, receipt = self.evaluate(repo, base, "develop")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["candidate_policy"]["authorization_effect"], "none")
        self.assertIn("catalog/effective-policy.json", receipt["candidate"]["policy_sensitive_paths"])

    def test_candidate_policy_input_replacement_keeps_prior_policy_binding(self):
        repo, base = self.make_repo()
        relative = Path('bundles/siege/policy-inputs.json')
        inputs = json.loads((repo / relative).read_text())
        inputs['selection_sha256'] = '0' * 64
        (repo / relative).write_text(json.dumps(inputs))
        git(repo, 'add', str(relative))
        git(repo, 'commit', '--no-verify', '-m', self.message('Candidate input replacement'))
        code, receipt = self.evaluate(repo, base, 'develop')
        self.assertEqual((code, receipt['state']), (0, 'eligible'))
        self.assertIn(str(relative), receipt['candidate']['policy_sensitive_paths'])
        self.assertIn(str(relative), {item['path'] for item in receipt['trusted']['authority_dependencies']})
        code, denied = self.evaluate(repo, base, 'main')
        self.assertEqual((code, denied['state']), (1, 'denied'))
        self.assertIn('target branch contradicts', denied['diagnostic'])
        self.change(repo, 'missing-ticket', self.message('Candidate without ticket', ticket=False), no_verify=True)
        code, denied = self.evaluate(repo, base, 'develop')
        self.assertEqual((code, denied['state']), (1, 'denied'))
        self.assertIn('lacks required approved ticket evidence', denied['diagnostic'])

    def test_installed_bytes_and_recomputed_digests_fail_closed(self):
        mutations = ("stale", "mixed", "missing", "resident", "parent-digest", "effective-digest")
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                repo, base = self.make_repo()
                receipt_path = repo / ".pilot/composition.json"
                if mutation == "missing":
                    receipt_path.unlink()
                elif mutation == "resident":
                    (repo / ".pilot/skills/RESIDENT.md").write_text(
                        "## Workflow\nFeature integration targets `main`. Ticket evidence is not required.\n"
                    )
                else:
                    data = json.loads(receipt_path.read_text())
                    if mutation == "stale":
                        data["policy"]["policy_selection"]["policy_revision"] = "0" * 40
                    elif mutation == "mixed":
                        data["policy"]["approved_policy"]["parent_lock"]["revision"] = "0" * 40
                    elif mutation == "parent-digest":
                        data["parent_content_sha256"] = "0" * 64
                    else:
                        data["policy"]["approved_policy"]["effective_digest"] = "f" * 64
                    receipt_path.write_text(json.dumps(data, indent=2) + "\n")
                git(repo, "add", "-A")
                git(repo, "commit", "--no-verify", "-m", self.message(f"{mutation} generated output"))
                code, denied = self.evaluate(repo, base, "develop")
                self.assertEqual((code, denied["state"]), (1, "denied"))
                if mutation == "missing":
                    self.assertIn("receipt is missing", denied["diagnostic"])
                else:
                    self.assertIn("installed package differs from trusted composition", denied["diagnostic"])

    def test_two_parent_merge_supported_and_octopus_rejected(self):
        repo, base = self.make_repo()
        git(repo, "checkout", "-q", "-b", "side")
        self.change(repo, "side", self.message("side"), no_verify=True)
        git(repo, "checkout", "-q", "-b", "feature", base)
        self.change(repo, "feature", self.message("feature"), no_verify=True)
        git(repo, "merge", "--no-ff", "side", "-m", "supported merge #1002", "--no-verify")
        code, receipt = self.evaluate(repo, base, "develop")
        self.assertEqual(code, 0)
        self.assertTrue(any(len(item["parents"]) == 2 for item in receipt["candidate"]["commits"]))

        octo, octo_base = self.make_repo()
        for branch, filename in (("one", "one"), ("two", "two")):
            git(octo, "checkout", "-q", "-b", branch, octo_base)
            self.change(octo, filename, self.message(branch), no_verify=True)
        git(octo, "checkout", "-q", "-b", "octopus", octo_base)
        self.change(octo, "root", self.message("root"), no_verify=True)
        git(octo, "merge", "--no-ff", "one", "two", "-m", "octopus #1002", "--no-verify")
        code, denied = self.evaluate(octo, octo_base, "develop")
        self.assertEqual((code, denied["state"]), (1, "denied"))
        self.assertIn("octopus", denied["diagnostic"])

    def test_denied_history_can_be_diagnosed_and_repaired_with_new_exact_head(self):
        repo, base = self.make_repo()
        self.change(repo, "bad", self.message("bad", ticket=False), no_verify=True)
        code, _ = self.evaluate(repo, base, "develop")
        self.assertEqual(code, 1)
        self.assertEqual(git(repo, "status", "--short").returncode, 0)
        git(repo, "reset", "--hard", base)
        repaired = self.change(repo, "bad", self.message("repaired"), no_verify=True)
        code, receipt = self.evaluate(repo, base, "develop", head=repaired)
        self.assertEqual((code, receipt["state"]), (0, "eligible"))

    def test_mutable_trusted_validator_or_missing_range_errors(self):
        repo, base = self.make_repo()
        self.change(repo, "valid", self.message("valid"))
        for dirty_path in (SCRIPT, Path("scripts/ci/check-branch-topology.sh"), Path("bundles/siege/policy-inputs.json")):
            with self.subTest(dirty_path=dirty_path):
                dirty = Path(tempfile.mkdtemp(prefix="dirty-trusted-", dir=self.temp))
                run("git", "clone", "--quiet", "--no-hardlinks", str(self.trusted), str(dirty), cwd=self.temp)
                with (dirty / dirty_path).open("a", encoding="utf-8") as handle:
                    handle.write("\n" if dirty_path.suffix == '.json' else "# mutable candidate bytes\n")
                code, error = self.evaluate(repo, base, "develop", trusted=dirty)
                self.assertEqual((code, error["state"]), (2, "error"))
                self.assertIn("working bytes differ", error["diagnostic"])
        missing = "0" * 40
        code, error = self.evaluate(repo, missing, "develop")
        self.assertNotEqual(code, 0)
        self.assertNotEqual(error["state"], "eligible")

    def test_registered_topology_entrypoint_uses_exact_event_and_denies_missing_ticket(self):
        candidate = self.temp / "provider-candidate"
        run("git", "clone", "--quiet", "--no-hardlinks", str(self.trusted), str(candidate), cwd=self.temp)
        git(candidate, "config", "user.email", "fixture@example.invalid")
        git(candidate, "config", "user.name", "Synthetic Fixture")
        git(candidate, "remote", "set-url", "origin", "https://github.com/siege-analytics/claude-configs-public.git")
        base = git(candidate, "rev-parse", "HEAD").stdout.strip()
        git(candidate, "update-ref", "refs/remotes/upstream/main", base)
        (candidate / "provider-negative.md").write_text("missing ticket\n", encoding="utf-8")
        git(candidate, "add", "provider-negative.md")
        git(candidate, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "provider negative")
        head = git(candidate, "rev-parse", "HEAD").stdout.strip()
        event = self.temp / "event.json"
        event.write_text(json.dumps({
            "repository": {"full_name": "siege-analytics/claude-configs-public"},
            "pull_request": {
                "base": {"sha": base, "ref": "develop", "repo": {"full_name": "siege-analytics/claude-configs-public"}},
                "head": {"sha": head, "ref": "test/provider-negative", "repo": {"full_name": "siege-analytics/claude-configs-public"}},
            },
        }), encoding="utf-8")
        env = {
            **os.environ,
            "BASE_BRANCH": "develop", "HEAD_BRANCH": "test/provider-negative",
            "HEAD_REPO": "siege-analytics/claude-configs-public",
            "CANONICAL_REPO": "siege-analytics/claude-configs-public",
            "MAIN_REF": "upstream/main", "GITHUB_EVENT_NAME": "pull_request_target",
            "GITHUB_EVENT_PATH": str(event), "GITHUB_REPOSITORY": "siege-analytics/claude-configs-public",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_WORKFLOW_REF": "siege-analytics/claude-configs-public/.github/workflows/pr-base-guard.yml@refs/heads/main",
            "GITHUB_WORKFLOW_SHA": git(self.trusted, "rev-parse", "refs/remotes/origin/main").stdout.strip(),
        }
        result = run(
            "bash", str(self.trusted / "scripts/ci/check-branch-topology.sh"),
            cwd=candidate, check=False, env=env,
        )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('"state":"denied"', result.stdout)
        self.assertIn("lacks required approved ticket evidence", result.stdout)

    def test_executed_default_workflow_identity_is_distinct_and_fail_closed(self):
        repo, base = self.make_repo()
        self.change(repo, "valid", self.message("valid"))
        code, receipt = self.evaluate(repo, base, "develop")
        self.assertEqual(code, 0)
        self.assertEqual(receipt["trusted"]["entrypoint"]["path"], "scripts/ci/check-branch-topology.sh")
        self.assertEqual(receipt["trusted"]["executed_workflow"]["revision"], self.trusted_revision)
        self.assertNotIn(".github/workflows/pr-base-guard.yml", {
            item["path"] for item in receipt["trusted"]["authority_dependencies"]
        })
        code, error = self.evaluate(
            repo, base, "develop",
            workflow_ref="synthetic-org/strict-release/.github/workflows/pr-base-guard.yml@refs/heads/develop",
        )
        self.assertEqual((code, error["state"]), (2, "error"))
        self.assertIn("default-branch registration", error["diagnostic"])
        code, error = self.evaluate(repo, base, "develop", workflow_revision="0" * 40)
        self.assertEqual((code, error["state"]), (2, "error"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
