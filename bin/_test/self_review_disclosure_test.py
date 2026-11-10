#!/usr/bin/env python3
"""Preserved review contracts, real flat assets and native parser outcomes."""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/self-review"
spec = importlib.util.spec_from_file_location("compose_review_fixture", ROOT / "bin/compose-project.py")
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)
# Template/fields retain baseline7e1 bytes. The checks pin includes the
# reviewed project-tooling correction after extraction (PR1203 findings).
EXPECTED = {
    "template": "75604494106ee6254c54ef657a739081c240ecd13ca6335cde3d396a8cb9a5f5",
    "fields": "5b844bcc2a023e7a1a18dc6f8a7fe72d5138d39aad67583a5bac26cd80e5171a",
    "checks": "fe89f4c4c025589717e91736e88ba5b6181a72ba0ddc5039c3b3116fa152400b",
}


class ReviewDisclosure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review-disclosure-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "consumer"
        self.repo.mkdir()
        self.env = {**os.environ, "HOME": str(self.base / "home"),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "CLAUDE_CONFIG_ROOT": str(ROOT),
                    "PYTHONDONTWRITEBYTECODE": "1"}
        for key in list(self.env):
            if key.startswith("GIT_") and key not in {"GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM"}:
                self.env.pop(key)
        binary = self.base / "bin"
        binary.mkdir()
        (binary / "python3").symlink_to(sys.executable)
        self.env["PATH"] = str(binary) + os.pathsep + self.env["PATH"]
        self.run_cmd(["git", "init", "-q", str(self.repo)])
        (self.repo / "README.md").write_text("fixture\n")
        self.run_cmd(["git", "add", "README.md"])

    def run_cmd(self, argv, expected=0):
        result = subprocess.run(argv, cwd=self.repo, env=self.env, text=True,
                                capture_output=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_template_and_detailed_contracts_are_verbatim(self):
        contract = (SKILL / "artifact-contract.md").read_bytes()
        split = contract.index(b"## Pre-author-inventory field\n")
        regions = {
            "template": contract[contract.index(b"## Artifact format\n"):split],
            "fields": contract[split:],
        }
        checks = (SKILL / "review-checklists.md").read_bytes()
        regions["checks"] = checks[checks.index(b"## Domains and roles\n"):]
        for name, content in regions.items():
            self.assertEqual(hashlib.sha256(content).hexdigest(), EXPECTED[name], name)

    def test_project_verification_contract_is_not_python_specific(self):
        entry = (SKILL / "SKILL.md").read_text()
        checks = (SKILL / "review-checklists.md").read_text()
        lead = checks.split("5. **Did the Junior run the mechanical verification gates?**", 1)[1]
        self.assertIn("Use the actual project test runner", entry)
        self.assertIn("selected project's actual test", lead)
        self.assertIn("Always\n     required for projects with a test suite", lead)
        self.assertIn("plain Markdown without a builder", lead)
        self.assertIn("Record the actual command and result", lead)
        self.assertNotIn("evidence line for `pytest`. Always required", lead)
        self.assertNotIn("evidence line for `sphinx-build`. Required", lead)

    def test_dispatch_example_creates_a_named_task_branch_from_remote_ref(self):
        rules = (ROOT / "skills/_session-coordination-rules.md").read_text()
        commands = re.findall(r'`(python3 /absolute/installed/claude-configs-public/bin/prepare-task-branch\.py [^`]+)`', rules)
        self.assertEqual(len(commands), 1)
        command = commands[0]
        self.assertNotIn("\n", command)
        self.assertNotIn("$", command)
        self.run_cmd(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                      "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture"])
        remote = self.base / "origin.git"
        self.run_cmd(["git", "init", "-q", "--bare", str(remote)])
        self.run_cmd(["git", "remote", "add", "origin", str(remote)])
        self.run_cmd(["git", "push", "-q", "origin", "HEAD:refs/heads/develop"])
        worktree = self.base / "isolated worker"
        values = {"/absolute/installed/claude-configs-public/bin/prepare-task-branch.py": str(ROOT / "bin/prepare-task-branch.py"),
                  "/absolute/project": str(self.repo), "feature/1234_task": "task/fixture-review",
                  "/absolute/unique-task-worktree": str(worktree)}
        argv = [values.get(word, word) for word in shlex.split(command)]
        parent_branch = self.run_cmd(["git", "symbolic-ref", "--short", "HEAD"]).stdout.strip()
        self.run_cmd(argv)
        self.assertEqual(self.run_cmd(["git", "symbolic-ref", "--short", "HEAD"]).stdout.strip(), parent_branch)
        child = self.run_cmd(["git", "-C", str(worktree), "symbolic-ref", "--short", "HEAD"])
        self.assertEqual(child.stdout.strip(), "task/fixture-review")
        self.assertEqual(self.run_cmd(["git", "-C", str(worktree), "rev-parse", "HEAD"]).stdout.strip(),
                         self.run_cmd(["git", "rev-parse", "origin/develop"]).stdout.strip())
        self.assertIn("Keep the parent in its own workspace", rules)
        self.assertIn("set the child's `workingDirectory` to the actual absolute worktree path", rules)
        # Discovery must include canonical and project-specific names, local
        # branches, remote-only refs and recorded heads with no ticket number.
        branches = ["bugfix/repair_692", "feature/completion_692", "task/cleanup_692",
                    "chore/tooling_692", "hotfix/urgent_692", "project-approved/recorded_head"]
        for name in branches:
            self.run_cmd(["git", "branch", name])
        self.run_cmd(["git", "update-ref", "refs/remotes/origin/project-approved/remote_head", "HEAD"])
        discover = "git for-each-ref --format='%(refname:short)' refs/heads refs/remotes"
        self.assertIn('`' + discover + '`', rules)
        found = self.run_cmd(["bash", "-c", discover]).stdout.splitlines()
        self.assertTrue(set(branches + ["origin/project-approved/remote_head", "task/fixture-review"]).issubset(found))
        self.assertIn('`git worktree list --porcelain`', rules)
        worktrees = self.run_cmd(["git", "worktree", "list", "--porcelain"]).stdout
        self.assertIn("branch refs/heads/task/fixture-review", worktrees)
        self.assertIn("ticket or PR's recorded head branch", rules)
        self.assertIn("Missing an ID match is not proof that work is absent", rules)

    def support_fragments(self, entry, directory):
        for link in compose.raw_link_targets(entry):
            parsed = urlsplit(link)
            if parsed.path not in {"artifact-contract.md", "review-checklists.md"}:
                continue
            target = directory / parsed.path
            if not target.is_file():
                raise ValueError("missing required review support: " + parsed.path)
            anchors, fenced = set(), False
            for line in target.read_text().splitlines():
                if line.lstrip().startswith("```"):
                    fenced = not fenced
                    continue
                heading = re.match(r"^#{1,6} +(.+?) *#*$", line)
                if heading and not fenced:
                    # The targeted sibling headings use ordinary GitHub-style
                    # words, spaces and punctuation; fenced examples are not anchors.
                    anchors.add(re.sub(r"[^\w -]", "", heading[1].lower()).replace(" ", "-"))
            if parsed.fragment and unquote(parsed.fragment) not in anchors:
                raise ValueError("missing required review fragment: " + parsed.fragment)

    def test_real_packages_keep_one_entry_and_flat_sibling_closure(self):
        for form in ("nested", "flat", "claude-code", "craft-agent"):
            package = ROOT / "dist" / form
            source = package / "skills/self-review"
            self.assertTrue(source.is_dir(), "build both layouts before this test: " + form)
            target = self.base / (form + "-only")
            shutil.copytree(source, target)
            self.assertEqual(len(list(target.rglob("SKILL.md"))), 1)
            entry = (target / "SKILL.md").read_text()
            for name in ("artifact-contract.md", "review-checklists.md"):
                sibling = target / name
                self.assertTrue(sibling.is_file(), form + ":" + name)
                self.assertFalse(sibling.read_text().startswith("---"))
                self.assertIn("](" + name + "#", entry)
            # Validate real outgoing links from the changed entry/support files.
            # Other package paths remain available targets without revalidating
            # every unrelated legacy skill's Markdown in this focused test.
            files = {p.relative_to(package).as_posix(): b"" for p in package.rglob("*") if p.is_file()}
            for path in source.glob("*.md"):
                files[path.relative_to(package).as_posix()] = path.read_bytes()
            compose.validate_packaged_links(files)
            self.support_fragments(entry, target)
            self.assertIn("review-checklists.md#lead-review-the-leads-adversarial-pass", entry)
            self.assertNotIn(str(ROOT), entry)

    def test_missing_required_support_and_invalid_fragments_fail(self):
        target = self.base / "damaged"
        shutil.copytree(SKILL, target)
        entry = (target / "SKILL.md").read_text()
        self.support_fragments(entry, target)
        with self.assertRaisesRegex(ValueError, "missing required review fragment"):
            self.support_fragments(entry.replace("#lead-review-the-leads-adversarial-pass", "#missing-lead-section"), target)
        (target / "artifact-contract.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing required review support"):
            self.support_fragments(entry, target)
        with self.assertRaises(ValueError):
            compose.validate_packaged_links({"skills/self-review/SKILL.md": b"[Required](artifact-contract.md)"})

    def message(self, tier, extra=""):
        return ("docs: fixture #1191\n\nReview-Tier: " + tier +
                "\nSelf-Review: fixture contract checked\nSelf-Review-Source: review.md\n" + extra)

    def native_check(self, message, expected=0):
        path = self.repo / "message"
        path.write_text(message)
        return self.run_cmd(["bash", str(ROOT / ".githooks/commit-msg"), str(path)], expected)

    def test_tier_b_native_parser_keeps_positive_and_missing_section_negative(self):
        path = self.repo / "review.md"
        path.write_text("## Assumptions\nFixture target.\n## Test plan\nFixture check.\n")
        self.native_check(self.message("B"))
        path.write_text("## Assumptions\nFixture target.\n")
        denied = self.native_check(self.message("B"), 1)
        self.assertIn("## Test plan", denied.stdout + denied.stderr)

    def test_tier_c_extracted_template_keeps_required_sections_and_trailers(self):
        contract = (SKILL / "artifact-contract.md").read_text()
        template = contract.split("```\n", 1)[1].split("```", 1)[0]
        path = self.repo / "review.md"
        # Placeholder values model structural input only; not a completed real review.
        path.write_text(template)
        trailers = ("Hostile-Review: review.md\nNegative-Tests: fixture denial\n"
                    "Full-Suite: fixture only\nCanary-Rollback: disposable fixture\n")
        self.native_check(self.message("C", trailers))
        path.write_text(template.replace("## Lead review", "Lead section removed"))
        denied = self.native_check(self.message("C", trailers), 1)
        self.assertIn("## Lead review", denied.stdout + denied.stderr)
        path.write_text(template)
        # Baseline set-e behavior can deny a missing trailer before printing a
        # diagnostic. This extraction preserves rejection, not new diagnostics.
        self.native_check(self.message("C", trailers.replace("Hostile-Review: review.md\n", "")), 1)


if __name__ == "__main__":
    unittest.main()
