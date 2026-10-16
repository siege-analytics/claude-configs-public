#!/usr/bin/env python3
"""Evaluate an exact Git range with previously approved project policy.

This program is a bounded evaluator for a trusted CI adapter.  A successful
local invocation means only that the exact range is eligible for a protected
host check.  It never turns caller input or its own exit status into host
authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
TICKET = re.compile(r"(?<![A-Za-z0-9])#[0-9]+(?![A-Za-z0-9])")
VALIDATOR_PATH = Path("scripts/ci/protected-policy-range.py")
ENTRYPOINT_PATH = Path("scripts/ci/check-branch-topology.sh")
WORKFLOW_PATH = Path(".github/workflows/pr-base-guard.yml")
TRUSTED_DEPENDENCIES = (
    VALIDATOR_PATH,
    ENTRYPOINT_PATH,
    Path("bin/effective_policy.py"),
    Path("bin/gate_contract.py"),
    Path("bundles/siege/policy-inputs.json"),
    Path("catalog/effective-policy-selection.json"),
    Path("catalog/gate-contract-schema.json"),
    Path("catalog/gate-contracts.json"),
)
POLICY_SENSITIVE = (
    "bin/effective_policy.py",
    "bin/gate_contract.py",
    "bundles/siege/policy-inputs.json",
    "catalog/effective-policy-selection.json",
    "catalog/effective-policy.json",
    "catalog/gate-contract-schema.json",
    "catalog/gate-contracts.json",
    ".githooks/commit-msg",
    VALIDATOR_PATH.as_posix(),
    ENTRYPOINT_PATH.as_posix(),
    WORKFLOW_PATH.as_posix(),
    "examples/provider/shared-parent-workflow.yml",
)


class Denied(ValueError):
    """The observed operation contradicts approved policy."""


def git(repo: Path, *args: str, text: bool = True) -> str | bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=text,
        stderr=subprocess.DEVNULL, timeout=20,
    )


def exact_sha(value: str, field: str) -> str:
    if not HEX40.fullmatch(value):
        raise ValueError(f"{field}: expected exact lowercase 40-character Git SHA")
    return value


def load_module(root: Path, relative: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, root / relative)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load trusted {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def revision_blob(root: Path, revision: str, relative: Path) -> tuple[str, bytes]:
    blob = str(git(root, "rev-parse", f"{revision}:{relative.as_posix()}")).strip()
    if not HEX40.fullmatch(blob):
        raise ValueError(f"trusted {relative}: invalid Git blob identity")
    return blob, git(root, "show", f"{revision}:{relative.as_posix()}", text=False)


def tracked_blob(root: Path, revision: str, relative: Path) -> str:
    blob, raw = revision_blob(root, revision, relative)
    if (root / relative).read_bytes() != raw:
        raise ValueError(f"trusted {relative}: working bytes differ from trusted revision")
    return blob


def remote_identity(repo: Path) -> dict[str, str]:
    raw = str(git(repo, "config", "--get", "remote.origin.url")).strip()
    if not raw:
        raise ValueError("candidate repository has no origin identity")
    if re.match(r"^[^/@:]+@[^/:]+:", raw):
        user_host, path = raw.split(":", 1)
        host = user_host.rsplit("@", 1)[-1]
    else:
        parsed = urlsplit(raw)
        if parsed.scheme not in {"https", "ssh"} or not parsed.hostname:
            raise ValueError("candidate origin must be an exact HTTPS or SSH repository URL")
        if parsed.port is not None:
            raise ValueError("candidate origin with an explicit port is unsupported")
        host, path = parsed.hostname, parsed.path
    parts = path.strip("/").split("/")
    if len(parts) != 2:
        raise ValueError("candidate origin must identify exactly owner/repository")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    return {"host": host.lower().rstrip("."), "owner": owner.lower(), "repository": repository.lower()}


def declared_identity(raw: str) -> dict[str, str]:
    parts = raw.strip("/").split("/")
    if len(parts) != 3 or any(not part for part in parts):
        raise ValueError("canonical identity must be exact host/owner/repository")
    host, owner, repository = parts
    if ":" in host:
        raise ValueError("canonical identity with a port is unsupported")
    return {"host": host.lower().rstrip("."), "owner": owner.lower(), "repository": repository.removesuffix(".git").lower()}


def validate_workflow_ref(ref: str, identity: dict[str, str]) -> None:
    # Repository identity is normalized; Git paths and refs remain case-sensitive.
    # Preserve the original host-observed ref in the receipt.
    parts = ref.split("/", 2)
    suffix = f"{WORKFLOW_PATH.as_posix()}@refs/heads/main"
    if (len(parts) != 3 or parts[0].lower() != identity["owner"]
            or parts[1].lower() != identity["repository"] or parts[2] != suffix):
        expected = f"{identity['owner']}/{identity['repository']}/{suffix}"
        raise ValueError(
            "executed workflow ref is not the canonical default-branch registration: "
            f"expected {expected}"
        )


def candidate_json(repo: Path, head: str, relative: Path, parser: Any) -> dict[str, Any] | None:
    try:
        raw = git(repo, "show", f"{head}:{relative.as_posix()}", text=False)
    except subprocess.CalledProcessError:
        return None
    return parser(raw, f"candidate:{head}:{relative.as_posix()}")


def commit_tree_files(repo: Path, revision: str, directory: Path) -> dict[str, bytes]:
    raw = git(repo, "ls-tree", "-r", "-z", revision, "--", directory.as_posix(), text=False)
    result: dict[str, bytes] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, kind, _ = metadata.decode().split()
        if kind != "blob" or mode == "120000":
            raise Denied(f"installed pilot contains unsupported non-file entry: {encoded_path!r}")
        path = encoded_path.decode("utf-8", "surrogateescape")
        relative_path = Path(path).relative_to(directory).as_posix()
        result[relative_path] = git(repo, "show", f"{revision}:{path}", text=False)
    return result


def trusted_composition_files(trusted: Path, trusted_revision: str, identity: str, layout: str) -> dict[str, bytes]:
    if layout not in {"flat", "nested"}:
        raise Denied("generated pilot receipt has unsupported layout")
    with tempfile.TemporaryDirectory(prefix="protected-policy-composition-") as raw:
        temporary = Path(raw)
        exact = temporary / "trusted"
        output = temporary / "output"
        subprocess.run(
            ["git", "clone", "--quiet", "--shared", "--no-checkout", str(trusted), str(exact)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30,
        )
        subprocess.run(
            ["git", "-C", str(exact), "checkout", "--quiet", "--detach", trusted_revision],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20,
        )
        subprocess.run(
            [sys.executable, str(exact / "bin/compose-project.py"), "--identity", identity, "--output", str(output)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=90,
        )
        root = output / layout
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()
        }


def validate_install(
    repo: Path, head: str, relative: Path, branch: dict[str, Any], parser: Any,
    trusted: Path, trusted_revision: str,
) -> dict[str, Any]:
    if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2:
        raise ValueError("installed pilot receipt path must be confined under a repository-relative package directory")
    receipt = candidate_json(repo, head, relative, parser)
    if receipt is None:
        raise Denied(f"generated pilot receipt is missing: {relative}")
    expected_identity = "/".join(branch["repository_identity"][key] for key in ("host", "owner", "repository"))
    layout = receipt.get("layout")
    expected_files = trusted_composition_files(trusted, trusted_revision, expected_identity, layout)
    installed_files = commit_tree_files(repo, head, relative.parent)
    if installed_files != expected_files:
        missing = sorted(set(expected_files) - set(installed_files))
        extra = sorted(set(installed_files) - set(expected_files))
        changed = sorted(path for path in set(expected_files) & set(installed_files) if expected_files[path] != installed_files[path])
        raise Denied(f"installed package differs from trusted composition: missing={missing} extra={extra} changed={changed}")
    expected_receipt = parser(expected_files[relative.name], f"trusted composition:{layout}/{relative.name}")
    if receipt != expected_receipt:
        raise Denied("installed composition receipt differs from trusted recomputation")
    expected = {
        "project": branch["project"],
        "identity": expected_identity,
        "evidence_state": "configured",
        "authorization_effect": "none",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise Denied(f"generated pilot receipt {key} disagrees with approved project")
    packaged = receipt.get("policy")
    if not isinstance(packaged, dict):
        raise Denied("generated pilot receipt lost effective policy explanation")
    if packaged.get("policy_selection") != branch["policy_selection"]:
        raise Denied("generated pilot receipt has stale policy selection")
    if packaged.get("values") != branch["values"]:
        raise Denied("generated pilot guidance values disagree with approved policy")
    approved = packaged.get("approved_policy", {})
    if approved.get("parent_lock") != branch["approved_policy"]["parent_lock"]:
        raise Denied("generated pilot receipt has mixed or stale parent lock")
    if packaged.get("decision", {}).get("final") != "unknown":
        raise Denied("generated configured pilot improperly claims final authorization")
    raw = git(repo, "show", f"{head}:{relative.as_posix()}", text=False)
    parent_content = receipt.get("parent_content_sha256")
    effective_digest = approved.get("effective_digest")
    if not isinstance(parent_content, str) or not re.fullmatch(r"[0-9a-f]{64}", parent_content):
        raise Denied("generated pilot receipt has invalid parent content identity")
    if not isinstance(effective_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", effective_digest):
        raise Denied("generated pilot receipt has invalid effective policy identity")
    return {
        "path": relative.as_posix(),
        "git_blob": str(git(repo, "rev-parse", f"{head}:{relative.as_posix()}")).strip(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "parent_content_sha256": parent_content,
        "effective_policy_sha256": effective_digest,
        "evidence_state": "configured",
        "authorization_effect": "none",
    }


def changed_paths(repo: Path, commit: str) -> list[str]:
    parents = str(git(repo, "show", "-s", "--format=%P", commit)).split()
    if len(parents) > 2:
        raise Denied(f"unsupported merge strategy: octopus commit {commit}")
    base = parents[0] if parents else "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    raw = git(repo, "diff", "--no-renames", "--name-only", "-z", "--diff-filter=ACDMRT", base, commit, text=False)
    return sorted({item.decode("utf-8", "surrogateescape") for item in raw.split(b"\0") if item})


def context(identity: dict[str, str]) -> dict[str, Any]:
    return {
        "identities": [{"source": "git-remote-origin", **identity}],
        "capabilities": {},
        "install_configuration": {},
        "task_evidence": [],
    }


def local_feedback(repo: Path, head: str) -> dict[str, Any]:
    """Describe local-hook configuration without treating it as acceptance."""
    try:
        hooks_path = str(git(repo, "config", "--get", "core.hooksPath")).strip()
    except subprocess.CalledProcessError:
        hooks_path = ""
    result: dict[str, Any] = {
        "core_hooks_path": hooks_path or None,
        "state": "unobserved",
        "authorization_effect": "none",
    }
    if not hooks_path:
        result["state"] = "not-configured"
        return result
    hook_path = Path(hooks_path) / "commit-msg"
    if hook_path.is_absolute() or ".." in hook_path.parts:
        result["state"] = "unsupported-path"
        return result
    try:
        raw = git(repo, "show", f"{head}:{hook_path.as_posix()}", text=False)
    except subprocess.CalledProcessError:
        result["state"] = "missing-at-head"
        return result
    result.update(
        path=hook_path.as_posix(),
        git_blob=str(git(repo, "rev-parse", f"{head}:{hook_path.as_posix()}")).strip(),
        sha256=hashlib.sha256(raw).hexdigest(),
    )
    return result


def normalize_host_event(args: argparse.Namespace) -> None:
    """Read registered host facts; never select parent authority from candidate data.

    A local process can simulate these variables. Its result remains eligibility,
    not authorization; actual execution/required-check evidence is external.
    """
    required = (
        "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REPOSITORY",
        "GITHUB_SERVER_URL", "GITHUB_WORKFLOW_REF", "GITHUB_WORKFLOW_SHA",
    )
    facts = {key: os.environ.get(key, "") for key in required}
    if any(not value for value in facts.values()):
        raise ValueError("registered host event inputs are incomplete")
    if facts["GITHUB_EVENT_NAME"] != "pull_request_target":
        raise ValueError("unsupported registered provider event")
    event = json.loads(Path(facts["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    pr = event["pull_request"]
    base, head = pr["base"], pr["head"]
    repository = facts["GITHUB_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("host repository identity is malformed")
    if event["repository"]["full_name"] != repository or base["repo"]["full_name"] != repository:
        raise ValueError("host event base/repository identities disagree")
    if head["repo"]["full_name"] != repository:
        raise Denied("unsupported fork: host event head repository differs from canonical repository")
    server = urlsplit(facts["GITHUB_SERVER_URL"])
    if (server.scheme != "https" or not server.hostname or server.port is not None
            or server.username or server.password or server.path or server.query or server.fragment):
        raise ValueError("provider server URL must be one exact HTTPS host")
    values = {
        "base": exact_sha(base["sha"], "event base"),
        "head": exact_sha(head["sha"], "event head"),
        "head_branch": head["ref"], "target_branch": base["ref"],
        "canonical_identity": f"{server.hostname}/{repository}",
        "executed_workflow_ref": facts["GITHUB_WORKFLOW_REF"],
        "executed_workflow_revision": exact_sha(facts["GITHUB_WORKFLOW_SHA"], "host workflow revision"),
    }
    for name, value in values.items():
        if not isinstance(value, str) or not value or any(c in value for c in "\t\n\r"):
            raise ValueError(f"malformed host event field: {name}")
        supplied = getattr(args, name)
        if supplied is not None and supplied != value:
            raise ValueError(f"explicit {name} disagrees with host event")
        setattr(args, name, value)
    for key, value in {
        "BASE_BRANCH": args.target_branch, "HEAD_BRANCH": args.head_branch,
        "HEAD_REPO": repository, "CANONICAL_REPO": repository,
    }.items():
        if key in os.environ and os.environ[key] != value:
            raise ValueError(f"workflow {key} disagrees with exact host event")
    validate_workflow_ref(args.executed_workflow_ref, declared_identity(args.canonical_identity))
    candidate = args.candidate_repo.resolve()
    trusted = args.trusted_root.resolve()
    if str(git(candidate, "rev-parse", "HEAD")).strip() != args.head:
        raise ValueError("candidate checkout differs from exact host event head")
    if remote_identity(candidate) != declared_identity(args.canonical_identity):
        raise ValueError("candidate origin disagrees with canonical host repository")
    # The existing self-hosted registration uses the PR base. External consumers
    # must supply their independently pinned parent revision in trusted host code.
    binding = "shared-parent" if args.trusted_revision is not None else "self-hosted-base"
    if binding == "shared-parent" and not args.trusted_repository:
        raise ValueError("shared parent requires an independently configured repository identity")
    args.trusted_repository = args.trusted_repository or args.canonical_identity
    parent_identity = declared_identity(args.trusted_repository)
    if remote_identity(trusted) != parent_identity:
        raise ValueError("trusted parent repository differs from host-configured parent identity")
    args.trusted_revision = exact_sha(args.trusted_revision or args.base, "trusted parent revision")
    if str(git(trusted, "rev-parse", "HEAD")).strip() != args.trusted_revision:
        raise ValueError("trusted parent checkout differs from host-configured parent revision")
    if str(git(trusted, "rev-parse", "--is-shallow-repository")).strip() == "true":
        git(trusted, "fetch", "--quiet", "--no-tags", "--unshallow", "origin",
            "+refs/heads/*:refs/remotes/origin/*")
    # Workflow bytes belong to a separately validated canonical consumer
    # checkout, never a candidate/fork checkout. The self-hosted exact base is
    # already that canonical checkout; shared-parent hosts supply another one.
    if binding == "shared-parent" and args.executed_workflow_root is None:
        raise ValueError("shared parent requires a separate canonical workflow checkout")
    workflow_root = (args.executed_workflow_root or trusted).resolve()
    if workflow_root == candidate:
        raise ValueError("candidate checkout cannot serve as canonical workflow authority")
    if remote_identity(workflow_root) != declared_identity(args.canonical_identity):
        raise ValueError("workflow checkout is not the canonical consumer repository")
    if binding == "shared-parent" and str(git(workflow_root, "rev-parse", "HEAD")).strip() != args.executed_workflow_revision:
        raise ValueError("canonical workflow checkout HEAD differs from host workflow revision")
    # fetch-depth:0 preserves origin/main even with persist-credentials:false.
    # A private consumer must not require a later anonymous network fetch.
    current_main = str(git(workflow_root, "rev-parse", "refs/remotes/origin/main")).strip()
    if current_main != args.executed_workflow_revision:
        raise ValueError("host workflow SHA differs from fetched canonical default branch")
    if subprocess.run(["git", "-C", str(candidate), "merge-base", "--is-ancestor", current_main, args.head],
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
        raise Denied("candidate HEAD does not contain current canonical main")
    args.executed_workflow_root = workflow_root
    args.host_event_binding = {"event": facts["GITHUB_EVENT_NAME"], "mode": binding,
                               "parent_repository": parent_identity, "parent_revision": args.trusted_revision,
                               "consumer_repository": declared_identity(args.canonical_identity),
                               "candidate_repository": remote_identity(candidate),
                               "consumer_base": args.base, "consumer_head": args.head}


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    trusted = args.trusted_root.resolve()
    candidate = args.candidate_repo.resolve()
    base = exact_sha(args.base, "base")
    head = exact_sha(args.head, "head")
    trusted_revision = exact_sha(args.trusted_revision, "trusted_revision")

    if str(git(trusted, "rev-parse", "HEAD")).strip() != trusted_revision:
        raise ValueError("trusted checkout HEAD differs from declared trusted revision")
    dependency_blobs = {
        path.as_posix(): tracked_blob(trusted, trusted_revision, path)
        for path in TRUSTED_DEPENDENCIES
    }
    workflow_revision = exact_sha(args.executed_workflow_revision, "executed_workflow_revision")
    workflow_root = (args.executed_workflow_root or trusted).resolve()
    workflow_blob, workflow_raw = revision_blob(workflow_root, workflow_revision, WORKFLOW_PATH)
    canonical_identity = declared_identity(args.canonical_identity)
    validate_workflow_ref(args.executed_workflow_ref, canonical_identity)
    if str(git(candidate, "rev-parse", "HEAD")).strip() != head:
        raise Denied("stale reviewed head: candidate HEAD differs from exact requested head")
    if subprocess.run(
        ["git", "-C", str(candidate), "merge-base", "--is-ancestor", base, head],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode:
        raise Denied("base is unavailable or is not an ancestor of exact head")

    commits = str(git(candidate, "rev-list", "--reverse", "--topo-order", f"{base}..{head}")).split()
    if not commits:
        raise Denied("exact candidate range is empty")
    source_identity = remote_identity(candidate)
    if source_identity != canonical_identity:
        raise Denied("unsupported fork or source repository: candidate origin differs from canonical policy target")
    ep = load_module(trusted, Path("bin/effective_policy.py"), "trusted_effective_policy")
    contract, policy, selection = ep.load_inputs(trusted)
    ctx = context(canonical_identity)
    candidate_policy = candidate_json(candidate, head, ep.POLICY, ep.parse_json)

    if subprocess.run(
        ["git", "-C", str(candidate), "check-ref-format", "--branch", args.head_branch],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    ).returncode:
        raise Denied("authenticated head branch is invalid")
    requested_branch = ep.explain(
        contract, policy, selection, ctx,
        {"type": "feature-merge", "target_branch": args.target_branch},
        candidate_policy,
    )
    if requested_branch.get("state") != "resolved":
        raise Denied(
            "repository identity cannot resolve approved policy: "
            f"{requested_branch.get('diagnostic', requested_branch.get('state'))}"
        )
    expected_integration = requested_branch["values"]["branch-policy"]["integration_branch"]
    operation = "feature-integration"
    branch = requested_branch
    if requested_branch["decision"]["policy"] != "allow":
        # Promotion is a distinct, topology-bounded operation. It does not
        # weaken the strict profile's feature target: only that profile's
        # exact integration branch may be promoted to main in the canonical
        # same-repository range already established above.
        if (
            args.target_branch == "main"
            and expected_integration != "main"
            and args.head_branch == expected_integration
        ):
            operation = "canonical-promotion"
            branch = ep.explain(
                contract, policy, selection, ctx,
                {"type": "feature-merge", "target_branch": expected_integration},
                candidate_policy,
            )
        else:
            raise Denied("target branch contradicts the selected project's approved branch policy")
    if branch["decision"]["policy"] != "allow":
        raise Denied("effective integration branch is not approved")
    if args.installed_pilot_receipt:
        installation = validate_install(
            candidate, head, args.installed_pilot_receipt, branch, ep.parse_json,
            trusted, trusted_revision,
        )
    else:
        # The parent repository has policy but no installed consumer package.
        # This absence grants nothing and is explicit in the receipt; disposable
        # consumer probes pass --installed-pilot-receipt and fail closed on it.
        installation = {
            "state": "not-observed-parent-repository",
            "authorization_effect": "none",
        }

    observations = []
    sensitive: set[str] = set()
    for commit in commits:
        message = str(git(candidate, "show", "-s", "--format=%B", commit))
        paths = changed_paths(candidate, commit)
        sensitive.update(path for path in paths if path in POLICY_SENSITIVE)
        ticket = ep.explain(
            contract, policy, selection, ctx,
            # Git's %B emits the stored terminal newline. The bounded policy
            # operation accepts semantic message text without surrounding
            # whitespace; preserve raw bytes in the digest but normalize the
            # operation value exactly once here.
            {"type": "ticket-commit", "message": message.strip()},
            candidate_policy,
        )
        if ticket.get("state") != "resolved" or ticket["decision"]["policy"] != "allow":
            raise Denied(f"commit {commit} lacks required approved ticket evidence")
        parents = str(git(candidate, "show", "-s", "--format=%P", commit)).split()
        observations.append({
            "commit": commit,
            "parents": parents,
            "message_sha256": hashlib.sha256(message.encode()).hexdigest(),
            "paths": paths,
            "ticket_policy": "allow",
        })

    values = branch["values"]
    expected_branch = values["branch-policy"]["integration_branch"]
    ticket_word = "required" if values["ticket-requirement"]["required"] else "not required"
    guidance = branch["resident_workflow"]
    if f"targets `{expected_branch}`" not in guidance or f"Ticket evidence is {ticket_word}" not in guidance:
        raise ValueError("generated guidance disagrees with executable effective policy")

    return {
        "schema_version": 1,
        "state": "eligible",
        "authorization": "protected-host-check-required",
        "authorization_effect": "none-outside-trusted-host-receipt",
        "host_event_binding": getattr(args, "host_event_binding", None),
        "trusted": {
            "revision": trusted_revision,
            "repository_identity": declared_identity(args.trusted_repository) if args.trusted_repository else None,
            "authority_dependencies": [
                {"path": path, "git_blob": blob}
                for path, blob in sorted(dependency_blobs.items())
            ],
            "validator": {"path": VALIDATOR_PATH.as_posix(), "git_blob": dependency_blobs[VALIDATOR_PATH.as_posix()]},
            "entrypoint": {"path": ENTRYPOINT_PATH.as_posix(), "git_blob": dependency_blobs[ENTRYPOINT_PATH.as_posix()]},
            "executed_workflow": {
                "path": WORKFLOW_PATH.as_posix(),
                "source_ref": args.executed_workflow_ref,
                "repository_identity": canonical_identity if getattr(args, "host_event_binding", None) else None,
                "revision": workflow_revision,
                "git_blob": workflow_blob,
                "sha256": hashlib.sha256(workflow_raw).hexdigest(),
            },
            "policy_selection": branch["policy_selection"],
        },
        "candidate": {
            "canonical_repository_identity": canonical_identity,
            "candidate_source_identity": source_identity,
            "source_relationship": "same-repository",
            "base": base,
            "head": head,
            "head_branch": args.head_branch,
            "target_branch": args.target_branch,
            "operation": operation,
            "policy_evaluation_target": expected_integration if operation == "canonical-promotion" else args.target_branch,
            "supported_strategy": "linear-or-two-parent-merge",
            "commits": observations,
            "policy_sensitive_paths": sorted(sensitive),
            "local_feedback": local_feedback(candidate, head),
            "installed_pilot": installation,
        },
        "project": branch["project"],
        "organization_profile": branch["organization_profile"],
        "resident_workflow": guidance,
        "branch_policy": branch["decision"]["policy"],
        "candidate_policy": branch.get("proposed_policy"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trusted-root", type=Path, required=True)
    parser.add_argument("--trusted-revision")
    parser.add_argument("--trusted-repository", help="independently configured parent host/owner/repository")
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--canonical-identity", help="host-authenticated target as host/owner/repository")
    parser.add_argument("--head-branch", help="host-authenticated candidate branch name")
    parser.add_argument("--target-branch")
    parser.add_argument("--executed-workflow-ref", help="host-observed workflow source ref")
    parser.add_argument("--executed-workflow-revision", help="host-observed default-branch workflow commit")
    parser.add_argument("--host-event", action="store_true", help="normalize fixed GitHub host-event facts")
    parser.add_argument("--executed-workflow-root", type=Path, help="Git object store containing actual workflow revision")
    parser.add_argument("--installed-pilot-receipt", type=Path, help="required configured consumer receipt for disposable consumer probes")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.host_event:
            normalize_host_event(args)
        elif any(getattr(args, name) is None for name in (
            "trusted_revision", "base", "head", "canonical_identity", "head_branch",
            "target_branch", "executed_workflow_ref", "executed_workflow_revision",
        )):
            raise ValueError("direct evaluator requires complete explicit operation/provenance inputs")
        result = evaluate(args)
        code = 0
    except Denied as exc:
        result = {"schema_version": 1, "state": "denied", "authorization": "none", "diagnostic": str(exc)}
        code = 1
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {"schema_version": 1, "state": "error", "authorization": "none", "diagnostic": str(exc)}
        code = 2
    raw = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.receipt:
        args.receipt.write_text(raw, encoding="utf-8")
    print(raw, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
