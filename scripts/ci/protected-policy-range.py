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
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

HEX40 = re.compile(r"[0-9a-f]{40}\Z")
TICKET = re.compile(r"(?<![A-Za-z0-9])#[0-9]+(?![A-Za-z0-9])")
VALIDATOR_PATH = Path("scripts/ci/protected-policy-range.py")
WORKFLOW_PATH = Path(".github/workflows/pr-base-guard.yml")
TRUSTED_DEPENDENCIES = (
    VALIDATOR_PATH,
    WORKFLOW_PATH,
    Path("bin/effective_policy.py"),
    Path("bin/gate_contract.py"),
    Path("catalog/effective-policy-selection.json"),
    Path("catalog/gate-contract-schema.json"),
    Path("catalog/gate-contracts.json"),
)
POLICY_SENSITIVE = (
    "bin/effective_policy.py",
    "bin/gate_contract.py",
    "catalog/effective-policy-selection.json",
    "catalog/effective-policy.json",
    "catalog/gate-contract-schema.json",
    "catalog/gate-contracts.json",
    ".githooks/commit-msg",
    VALIDATOR_PATH.as_posix(),
    WORKFLOW_PATH.as_posix(),
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


def tracked_blob(root: Path, revision: str, relative: Path) -> str:
    blob = str(git(root, "rev-parse", f"{revision}:{relative.as_posix()}")).strip()
    if not HEX40.fullmatch(blob):
        raise ValueError(f"trusted {relative}: invalid Git blob identity")
    raw = git(root, "show", f"{revision}:{relative.as_posix()}", text=False)
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


def candidate_json(repo: Path, head: str, relative: Path, parser: Any) -> dict[str, Any] | None:
    try:
        raw = git(repo, "show", f"{head}:{relative.as_posix()}", text=False)
    except subprocess.CalledProcessError:
        return None
    return parser(raw, f"candidate:{head}:{relative.as_posix()}")


def validate_install(repo: Path, head: str, relative: Path, branch: dict[str, Any], parser: Any) -> dict[str, Any]:
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("installed pilot receipt path must be confined and repository-relative")
    receipt = candidate_json(repo, head, relative, parser)
    if receipt is None:
        raise Denied(f"generated pilot receipt is missing: {relative}")
    expected_identity = "/".join(branch["repository_identity"][key] for key in ("host", "owner", "repository"))
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
    canonical_identity = declared_identity(args.canonical_identity)
    if source_identity != canonical_identity:
        raise Denied("unsupported fork or source repository: candidate origin differs from canonical policy target")
    ep = load_module(trusted, Path("bin/effective_policy.py"), "trusted_effective_policy")
    contract, policy, selection = ep.load_inputs(trusted)
    ctx = context(canonical_identity)
    candidate_policy = candidate_json(candidate, head, ep.POLICY, ep.parse_json)

    branch = ep.explain(
        contract, policy, selection, ctx,
        {"type": "feature-merge", "target_branch": args.target_branch},
        candidate_policy,
    )
    if branch.get("state") != "resolved":
        raise Denied(f"repository identity cannot resolve approved policy: {branch.get('diagnostic', branch.get('state'))}")
    if branch["decision"]["policy"] != "allow":
        raise Denied("target branch contradicts the selected project's approved branch policy")
    if args.installed_pilot_receipt:
        installation = validate_install(candidate, head, args.installed_pilot_receipt, branch, ep.parse_json)
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
        "trusted": {
            "revision": trusted_revision,
            "authority_dependencies": [
                {"path": path, "git_blob": blob}
                for path, blob in sorted(dependency_blobs.items())
            ],
            "validator": {"path": VALIDATOR_PATH.as_posix(), "git_blob": dependency_blobs[VALIDATOR_PATH.as_posix()]},
            "workflow": {"path": WORKFLOW_PATH.as_posix(), "git_blob": dependency_blobs[WORKFLOW_PATH.as_posix()]},
            "policy_selection": branch["policy_selection"],
        },
        "candidate": {
            "canonical_repository_identity": canonical_identity,
            "candidate_source_identity": source_identity,
            "source_relationship": "same-repository",
            "base": base,
            "head": head,
            "target_branch": args.target_branch,
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
    parser.add_argument("--trusted-revision", required=True)
    parser.add_argument("--candidate-repo", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--canonical-identity", required=True, help="host-authenticated target as host/owner/repository")
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--installed-pilot-receipt", type=Path, help="required configured consumer receipt for disposable consumer probes")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
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
