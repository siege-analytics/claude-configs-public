#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "bin" / "skill-lifecycle.py"
SPEC = importlib.util.spec_from_file_location("skill_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(root: Path, rel: str, content: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def skill(name: str, metadata: str = "") -> str:
    return f"---\nname: {name}\ndescription: fixture\n{metadata}---\n\n# {name}\n"


def item(slug: str, path: str, kind: str = "skill", tier: str = "unclassified", owner=None, project=None):
    return {
        "slug": slug,
        "source_path": path,
        "kind": kind,
        "tier": tier,
        "owner": owner or ["unknown"],
        "project": project,
    }


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def git(root: Path, *args: str, input_text: str | None = None) -> str:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()


def commit(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


def expect_value_error(message: str, callback) -> None:
    try:
        callback()
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError(f"expected ValueError containing: {message}")


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td).resolve()
        (root / "bin").mkdir()
        shutil.copy2(ROOT / "bin" / "skill-inventory.py", root / "bin" / "skill-inventory.py")
        schema_path = root / "catalog" / "skill-lifecycle-schema.json"
        schema_path.parent.mkdir()
        shutil.copy2(ROOT / "catalog" / "skill-lifecycle-schema.json", schema_path)

        complete_meta = (
            "tier: on-demand\nowner: owner@example.test\nstatus: active\n"
            "last-reviewed: 2026-10-12\nverification: tests/complete.test.sh\n"
        )
        lifecycle_meta = "status: active\nlast-reviewed: 2026-10-12\nverification: tests/project.test.sh\n"
        deprecated_meta = (
            "tier: on-demand\nowner: owner@example.test\nstatus: deprecated\n"
            "last-reviewed: 2026-10-12\nverification: tests/deprecated.test.sh\n"
        )
        uppercase_meta = complete_meta.replace("status: active", "status: ACTIVE")
        project_conflict_meta = lifecycle_meta + "tier: kernel\n"

        sources = {
            "skills/complete/SKILL.md": skill("complete", complete_meta),
            "skills/legacy/SKILL.md": skill("legacy"),
            "skills/deprecated/SKILL.md": skill("deprecated", deprecated_meta),
            "skills/reference/SKILL.md": skill("reference", lifecycle_meta),
            "skills/uppercase/SKILL.md": skill("uppercase", uppercase_meta),
            "projects/demo/skills/reviewer/SKILL.md": skill("demo--reviewer", lifecycle_meta),
            "projects/demo/skills/conflict/SKILL.md": skill("demo--conflict", project_conflict_meta),
        }
        for path, content in sources.items():
            write(root, path, content)

        inventory = {
            "items": [
                item("complete", "skills/complete/SKILL.md"),
                item("legacy", "skills/legacy/SKILL.md"),
                item("deprecated", "skills/deprecated/SKILL.md"),
                item("reference", "skills/reference/SKILL.md", tier="reference", owner=["inferred@example.test"]),
                item("uppercase", "skills/uppercase/SKILL.md"),
                item(
                    "demo--reviewer", "projects/demo/skills/reviewer/SKILL.md",
                    kind="project-skill", tier="project", owner=["project-owner@example.test"], project="demo",
                ),
                item(
                    "demo--conflict", "projects/demo/skills/conflict/SKILL.md",
                    kind="project-skill", tier="project", owner=["project-owner@example.test"], project="demo",
                ),
            ]
        }
        inventory_path = root / "catalog" / "skills-inventory.json"
        dump(inventory_path, inventory)
        bootstrap_path = root / "catalog" / "skill-lifecycle-bootstrap.json"
        bootstrap_paths = sorted([
            "skills/legacy/SKILL.md",
            "skills/deprecated/SKILL.md",
            "skills/reference/SKILL.md",
            "skills/uppercase/SKILL.md",
            "projects/demo/skills/conflict/SKILL.md",
        ])
        dump(bootstrap_path, {"baseline_reference": "fixture", "source_paths": bootstrap_paths})
        fixture_bootstrap_digest = hashlib.sha256(bootstrap_path.read_bytes()).hexdigest()
        with mock.patch.object(MODULE, "BOOTSTRAP_SHA256", fixture_bootstrap_digest):
            bootstrap_path.write_text(bootstrap_path.read_text() + "\n")
            expect_value_error(
                "lifecycle bootstrap digest changed",
                lambda: MODULE.build_allowlist(
                    root, inventory_path, schema_path, bootstrap_path,
                    root / "catalog" / "not-created-approvals.json",
                    root / "catalog" / "not-created-completed.json",
                    verify_inventory=False,
                    enforce_bootstrap_digest=True,
                    allow_initial_bootstrap=True,
                ),
            )
        dump(bootstrap_path, {"baseline_reference": "fixture", "source_paths": bootstrap_paths})
        approvals_path = root / "catalog" / "skill-lifecycle-approved-exceptions.json"
        dump(approvals_path, {"entries": []})
        completed_path = root / "catalog" / "skill-lifecycle-completed.json"
        dump(completed_path, {"entries": []})

        generated = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        by_path = {entry["source_path"]: entry for entry in generated["entries"]}
        assert "skills/complete/SKILL.md" not in by_path
        assert "projects/demo/skills/reviewer/SKILL.md" not in by_path
        assert {"tier", "owner"}.issubset(by_path["skills/reference/SKILL.md"]["missing_fields"])
        assert "superseded-by" in by_path["skills/deprecated/SKILL.md"]["missing_fields"]
        assert "status:ACTIVE" in by_path["skills/uppercase/SKILL.md"]["invalid_fields"]
        assert "tier-conflict:kernel" in by_path["projects/demo/skills/conflict/SKILL.md"]["invalid_fields"]

        prior_gaps = {
            entry["source_path"]: {
                *(f"missing:{field}" for field in entry["missing_fields"]),
                *(f"invalid:{field}" for field in entry["invalid_fields"]),
            }
            for entry in generated["entries"]
        }
        write(root, "skills/reference/SKILL.md", skill("reference", lifecycle_meta.replace("status: active", "status: ACTIVE")))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False,
                previous_gap_state=prior_gaps,
            )
        except ValueError as exc:
            assert "gap sets expanded" in str(exc)
        else:
            raise AssertionError("an existing exception gained an unapproved invalid field")
        write(root, "skills/reference/SKILL.md", skill("reference", lifecycle_meta))

        old = MODULE.serialize(generated)
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "must be recorded" in str(exc)
        else:
            raise AssertionError("bootstrap completion was removed without a monotonic record")
        dump(completed_path, {"entries": [{
            "source_path": "skills/legacy/SKILL.md",
            "completed_on": "2026-10-12",
            "completion_reference": "PR #122",
        }]})
        refreshed = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        assert old != MODULE.serialize(refreshed)
        assert "skills/legacy/SKILL.md" not in {entry["source_path"] for entry in refreshed["entries"]}
        write(root, "skills/legacy/SKILL.md", skill("legacy"))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
                previous_completed_paths={"skills/legacy/SKILL.md"},
            )
        except ValueError as exc:
            assert "metadata regressed" in str(exc)
        else:
            raise AssertionError("completed metadata regression re-entered bootstrap exceptions")
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))
        dump(completed_path, {"entries": []})
        write(root, "skills/legacy/SKILL.md", skill("legacy"))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
                previous_completed_paths={"skills/legacy/SKILL.md"},
            )
        except ValueError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("completion record deletion reopened a bootstrap exception")
        dump(completed_path, {"entries": [{
            "source_path": "skills/legacy/SKILL.md",
            "completed_on": "2026-10-12",
            "completion_reference": "PR #122",
        }]})
        write(root, "skills/legacy/SKILL.md", skill("legacy", complete_meta))

        write(root, "skills/new/SKILL.md", skill("new"))
        inventory["items"].append(item("new", "skills/new/SKILL.md"))
        dump(inventory_path, inventory)
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "explicit approval records" in str(exc)
        else:
            raise AssertionError("new lifecycle gap could be admitted by regeneration")

        dump(approvals_path, {"entries": [{
            "source_path": "skills/new/SKILL.md",
            "reason": "fixture exception",
            "approval_reference": "PR #123",
            "approved_on": "2026-10-12",
            "approved_gaps": [
                "missing:tier", "missing:owner", "missing:status",
                "missing:last-reviewed", "missing:verification",
            ],
        }]})
        approved = MODULE.build_allowlist(
            root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
            verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
        )
        assert any(entry["source_path"] == "skills/new/SKILL.md" for entry in approved["entries"])

        # A prior approval for one exact gap set cannot be replayed after the
        # source gains a different gap set.
        write(root, "skills/new/SKILL.md", skill("new", "status: active\n"))
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "exact current gap set" in str(exc)
        else:
            raise AssertionError("historical approval authorized a different later gap set")
        write(root, "skills/new/SKILL.md", skill("new"))

        traversal_inventory = {"items": [item("escape", "../escape/SKILL.md")]}
        dump(inventory_path, traversal_inventory)
        try:
            MODULE.build_allowlist(
                root, inventory_path, schema_path, bootstrap_path, approvals_path, completed_path,
                verify_inventory=False, enforce_bootstrap_digest=False, allow_initial_bootstrap=True,
            )
        except ValueError as exc:
            assert "unsafe inventory source_path" in str(exc)
        else:
            raise AssertionError("path traversal was accepted")

    # Model both GitHub event paths around the same canonical promotion merge.
    # The event baseline has no report; ratchet state is recovered from the
    # promoted develop commit's first parent instead of being skipped.
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td).resolve()
        git(repo.parent, "init", "-q", "-b", "main", str(repo))
        git(repo, "config", "user.email", "test@example.test")
        git(repo, "config", "user.name", "Lifecycle Test")
        write(repo, "README.md", "pre-lifecycle main\n")
        first_main = commit(repo, "pre-lifecycle main")
        git(repo, "tag", "first-main-baseline", first_main)

        git(repo, "switch", "-q", "-c", "develop")
        dump(repo / "catalog" / "skill-lifecycle-legacy.json", {"entries": []})
        dump(repo / "catalog" / "skill-lifecycle-completed.json", {"entries": []})
        policy_history = commit(repo, "introduce lifecycle report")
        write(repo, "candidate.txt", "canonical develop candidate\n")
        promotion = commit(repo, "develop candidate")

        git(repo, "switch", "-q", "main")
        git(repo, "merge", "--no-ff", "develop", "-m", "canonical promotion")
        candidate = git(repo, "rev-parse", "HEAD")
        normalized_previous = MODULE.resolve_commit(repo, "first-main-baseline")
        assert normalized_previous == first_main

        common = {
            "root": repo,
            "previous_commit": normalized_previous,
            "current_ref": candidate,
            "repository": "test/repo",
            "head_repository": "test/repo",
            "accepted_base": first_main,
            "policy_base": policy_history,
        }
        pr_history = MODULE.canonical_first_promotion_history_ref(
            **common,
            event_name="pull_request",
            base_ref="main",
            head_ref="develop",
            event_ref="refs/pull/1/merge",
            promotion_ref="refs/heads/develop",
        )
        assert pr_history == policy_history
        push_history = MODULE.canonical_first_promotion_history_ref(
            **common,
            event_name="push",
            base_ref="",
            head_ref="",
            event_ref="refs/heads/main",
            promotion_ref=promotion,
        )
        assert push_history == policy_history

        # The push uses the immutable associated-PR head SHA, so a later
        # develop advance neither changes provenance nor falsely blocks it.
        advanced_develop = git(
            repo, "commit-tree", git(repo, "rev-parse", f"{promotion}^{{tree}}"),
            "-p", promotion, input_text="later develop advance\n",
        )
        git(repo, "branch", "-f", "develop", advanced_develop)
        assert MODULE.canonical_first_promotion_history_ref(
            **common,
            event_name="push",
            base_ref="",
            head_ref="",
            event_ref="refs/heads/main",
            promotion_ref=promotion,
        ) == policy_history

        expect_value_error(
            "missing outside the initial bootstrap",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "previous_commit": policy_history},
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "canonical develop -> main",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **common,
                event_name="pull_request", base_ref="develop", head_ref="feature/f1",
                event_ref="refs/pull/1/merge", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "canonical-repository develop",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "head_repository": "fork/repo"},
                event_name="pull_request", base_ref="main", head_ref="develop",
                event_ref="refs/pull/1/merge", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "canonical-repository develop",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "head_repository": ""},
                event_name="pull_request", base_ref="main", head_ref="develop",
                event_ref="refs/pull/1/merge", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "two-parent merge",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "current_ref": promotion},
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "refs/heads/main",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **common,
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/develop", promotion_ref=promotion,
            ),
        )

        # A conflict-resolution or payload change in the promotion merge is
        # not the already-reviewed develop tree and must not consume the pin.
        write(repo, "merge-only.txt", "not on develop\n")
        git(repo, "add", "merge-only.txt")
        changed_tree = git(repo, "write-tree")
        changed_merge = git(
            repo, "commit-tree", changed_tree, "-p", first_main, "-p", promotion,
            input_text="changed promotion tree\n",
        )
        expect_value_error(
            "merge tree differs",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "current_ref": changed_merge},
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref=promotion,
            ),
        )

        # A feature-derived second parent cannot impersonate develop on the
        # push path even if it contains all policy history and keeps its tree.
        feature_commit = git(
            repo, "commit-tree", changed_tree, "-p", promotion,
            input_text="feature candidate\n",
        )
        feature_merge = git(
            repo, "commit-tree", changed_tree, "-p", first_main, "-p", feature_commit,
            input_text="feature to main\n",
        )
        expect_value_error(
            "not canonical develop",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **{**common, "current_ref": feature_merge},
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref=promotion,
            ),
        )
        expect_value_error(
            "immutable canonical develop SHA",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **common,
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref="",
            ),
        )
        expect_value_error(
            "immutable canonical develop SHA",
            lambda: MODULE.canonical_first_promotion_history_ref(
                **common,
                event_name="push", base_ref="", head_ref="",
                event_ref="refs/heads/main", promotion_ref="refs/heads/develop",
            ),
        )

        # Even a structurally valid merge fails if the promoted branch has no
        # lifecycle history to anchor gap expansion and append-only checks.
        git(repo, "switch", "-q", "--orphan", "no-report-develop")
        git(repo, "rm", "-q", "-rf", ".")
        write(repo, "orphan.txt", "no report\n")
        orphan_base = commit(repo, "orphan base")
        write(repo, "orphan-candidate.txt", "no lifecycle history\n")
        orphan_promotion = commit(repo, "orphan candidate")
        orphan_tree = git(repo, "rev-parse", f"{orphan_promotion}^{{tree}}")
        orphan_merge = git(
            repo, "commit-tree", orphan_tree, "-p", orphan_base, "-p", orphan_promotion,
            input_text="orphan promotion\n",
        )
        expect_value_error(
            "prior lifecycle gap report",
            lambda: MODULE.canonical_first_promotion_history_ref(
                repo,
                orphan_base,
                current_ref=orphan_merge,
                event_name="push",
                base_ref="",
                head_ref="",
                event_ref="refs/heads/main",
                repository="test/repo",
                head_repository="test/repo",
                promotion_ref=orphan_promotion,
                accepted_base=orphan_base,
                policy_base=orphan_base,
            ),
        )

    print("skill_lifecycle_test: PASS")


if __name__ == "__main__":
    main()
