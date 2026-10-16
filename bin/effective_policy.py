#!/usr/bin/env python3
"""Resolve and explain the bounded effective policy approved by issue #848.

Only the checked-in approved catalog participates in precedence. Target identity,
operation facts, host capability states, installation metadata, task evidence,
and an optional candidate catalog are explicit inputs; none can grant policy
authority or replace the approved catalog.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = Path("catalog/effective-policy.json")
SELECTION = Path("catalog/effective-policy-selection.json")
CONTRACT = Path("catalog/gate-contracts.json")
SELECTION_SHA256 = "1d14ef00a67767a2f135946cb6496f3e77e2792ac436c362eb4fcbed56a1d77f"
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\Z")
REPO_PART = re.compile(r"[a-z0-9](?:[a-z0-9_.-]*[a-z0-9])?\Z")
POLICY_FIELDS = {
    "schema_version", "resolver_version", "contract_source", "contract_sha256",
    "parent_contract_revision", "parent_lock", "organization_profiles", "projects",
}
PARENT_LOCK_FIELDS = {
    "host", "owner", "repository", "revision", "import_mechanism", "digest", "tool_version",
}
SELECTION_FIELDS = {
    "schema_version", "policy_revision", "policy_path", "git_blob", "raw_sha256",
    "canonical_sha256", "review_evidence",
}
PROFILE_FIELDS = {"id", "values"}
PROJECT_FIELDS = {"id", "repository_identity", "organization_profile", "values"}
IDENTITY_FIELDS = {"host", "owner", "repository"}
CONTEXT_FIELDS = {"identities", "capabilities", "install_configuration", "task_evidence"}
IDENTITY_INPUT_FIELDS = {"source", "host", "owner", "repository"}
OPERATION_FIELDS = {
    "feature-merge": {"type", "target_branch"},
    "ticket-commit": {"type", "message"},
    "review-procedure": {"type"},
}
CAPABILITY_STATES = {"verified", "unsupported", "unverified"}


def fail(message: str) -> None:
    raise ValueError(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(raw: bytes | str, context: str) -> dict[str, Any]:
    try:
        value = json.loads(raw, object_pairs_hook=unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"cannot read JSON {context}: {exc}")
    if not isinstance(value, dict):
        fail(f"{context}: expected an object")
    return value


def read_json(path: Path) -> dict[str, Any]:
    try:
        return parse_json(path.read_bytes(), path.as_posix())
    except OSError as exc:
        fail(f"cannot read JSON {path}: {exc}")


def exact_fields(value: Any, expected: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{context}: expected object")
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown or missing:
        fail(f"{context}: fields differ; unknown={sorted(unknown)} missing={sorted(missing)}")
    return value


def text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        fail(f"{context}: expected nonempty text without surrounding whitespace")
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _gate_contract_module():
    spec = importlib.util.spec_from_file_location("gate_contract", ROOT / "bin/gate_contract.py")
    if spec is None or spec.loader is None:
        fail("cannot load bin/gate_contract.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_identity(value: dict[str, Any], context: str, *, with_source: bool) -> dict[str, str]:
    expected = IDENTITY_INPUT_FIELDS if with_source else IDENTITY_FIELDS
    exact_fields(value, expected, context)
    result: dict[str, str] = {}
    if with_source:
        source = text(value["source"], f"{context}.source")
        if not ID.fullmatch(source):
            fail(f"{context}.source: expected lowercase hyphenated identifier")
        result["source"] = source
    host = text(value["host"], f"{context}.host").lower().rstrip(".")
    owner = text(value["owner"], f"{context}.owner").lower()
    repository = text(value["repository"], f"{context}.repository").lower()
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not HOST.fullmatch(host) or not REPO_PART.fullmatch(owner) or not REPO_PART.fullmatch(repository):
        fail(f"{context}: invalid canonical host/owner/repository")
    result.update(host=host, owner=owner, repository=repository)
    return result


def identity_tuple(value: dict[str, str]) -> tuple[str, str, str]:
    return value["host"], value["owner"], value["repository"]


def validate_partial_values(
    values: Any,
    policies: dict[str, dict[str, Any]],
    layer: str,
    context: str,
    gc: Any,
) -> dict[str, dict[str, Any]]:
    if not isinstance(values, dict):
        fail(f"{context}: expected object")
    unknown_fields = set(values) - set(policies)
    if unknown_fields:
        fail(f"{context}: unknown policy fields {sorted(unknown_fields)}")
    allowed_name = {
        "organization-profile": "organization_profile_paths",
        "project": "project_paths",
    }[layer]
    result: dict[str, dict[str, Any]] = {}
    for field_id, patch in values.items():
        if not isinstance(patch, dict) or not patch:
            fail(f"{context}.{field_id}: expected nonempty object")
        policy = policies[field_id]
        properties = policy["value_schema"]["properties"]
        unknown_paths = set(patch) - set(properties)
        if unknown_paths:
            fail(f"{context}.{field_id}: unknown paths {sorted(unknown_paths)}")
        allowed = set(policy["override_policy"][allowed_name])
        forbidden = set(patch) - allowed
        if forbidden:
            fail(f"{context}: unauthorized {layer} override of {field_id}.{sorted(forbidden)}")
        merged = dict(policy["default"])
        merged.update(patch)
        gc.validate_typed_value(merged, policy["value_schema"], f"{context}.{field_id}")
        result[field_id] = dict(patch)
    return result


def validate_policy(data: Any, contract: dict[str, Any], context: str = "effective policy") -> dict[str, Any]:
    exact_fields(data, POLICY_FIELDS, context)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail(f"{context}.schema_version: expected integer 1")
    if not SEMVER.fullmatch(text(data["resolver_version"], f"{context}.resolver_version")):
        fail(f"{context}.resolver_version: expected major.minor.patch")
    if data["contract_source"] != CONTRACT.as_posix():
        fail(f"{context}: contract source differs from authoritative source")
    if not HEX64.fullmatch(text(data["contract_sha256"], f"{context}.contract_sha256")):
        fail(f"{context}: invalid contract digest")
    if data["contract_sha256"] != digest(contract):
        fail(f"{context}: contract digest disagrees with authoritative contract")
    if not HEX40.fullmatch(text(data["parent_contract_revision"], f"{context}.parent_contract_revision")):
        fail(f"{context}: parent contract revision must be exact 40-character SHA")
    lock = exact_fields(data["parent_lock"], PARENT_LOCK_FIELDS, f"{context}.parent_lock")
    lock_identity = normalize_identity(
        {key: lock[key] for key in ("host", "owner", "repository")},
        f"{context}.parent_lock", with_source=False,
    )
    if any(lock[key] != lock_identity[key] for key in ("host", "owner", "repository")):
        fail(f"{context}.parent_lock: identity must already be canonical")
    if lock["revision"] != data["parent_contract_revision"]:
        fail(f"{context}.parent_lock: revision disagrees with parent contract revision")
    if lock["digest"] != data["contract_sha256"]:
        fail(f"{context}.parent_lock: digest disagrees with contract digest")
    if lock["import_mechanism"] != "git" or lock["tool_version"] != "effective-policy/1":
        fail(f"{context}.parent_lock: unsupported import mechanism or tool version")

    gc = _gate_contract_module()
    policies = {item["id"]: item for item in contract["policy_fields"]}
    profiles: dict[str, dict[str, Any]] = {}
    if not isinstance(data["organization_profiles"], list) or not data["organization_profiles"]:
        fail(f"{context}.organization_profiles: expected nonempty list")
    for index, raw in enumerate(data["organization_profiles"]):
        item = exact_fields(raw, PROFILE_FIELDS, f"{context}.organization_profiles[{index}]")
        ident = text(item["id"], f"{context}.organization_profiles[{index}].id")
        if not ID.fullmatch(ident) or ident in profiles:
            fail(f"{context}: invalid or duplicate organization profile {ident}")
        profiles[ident] = validate_partial_values(
            item["values"], policies, "organization-profile", f"profile {ident}", gc
        )

    projects: dict[str, dict[str, Any]] = {}
    identities: dict[tuple[str, str, str], str] = {}
    if not isinstance(data["projects"], list) or not data["projects"]:
        fail(f"{context}.projects: expected nonempty list")
    for index, raw in enumerate(data["projects"]):
        item = exact_fields(raw, PROJECT_FIELDS, f"{context}.projects[{index}]")
        ident = text(item["id"], f"{context}.projects[{index}].id")
        if not ID.fullmatch(ident) or ident in projects:
            fail(f"{context}: invalid or duplicate project {ident}")
        profile = text(item["organization_profile"], f"project {ident}.organization_profile")
        if profile not in profiles:
            fail(f"project {ident}: unknown organization profile {profile}")
        identity = normalize_identity(item["repository_identity"], f"project {ident}.repository_identity", with_source=False)
        key = identity_tuple(identity)
        if key in identities:
            fail(f"{context}: duplicate repository identity for {identities[key]} and {ident}")
        identities[key] = ident
        project = dict(item)
        project["repository_identity"] = identity
        project["values"] = validate_partial_values(item["values"], policies, "project", f"project {ident}", gc)
        projects[ident] = project
    return data


def validate_selection(data: Any) -> dict[str, Any]:
    exact_fields(data, SELECTION_FIELDS, "effective policy selection")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("effective policy selection: schema_version must be integer 1")
    if digest(data) != SELECTION_SHA256:
        fail("effective policy selection: complete receipt digest differs from reviewed selection")
    if not HEX40.fullmatch(text(data["policy_revision"], "selection.policy_revision")):
        fail("selection.policy_revision: expected exact 40-character SHA")
    if data["policy_path"] != POLICY.as_posix():
        fail("selection.policy_path: must name the canonical policy artifact")
    if not HEX40.fullmatch(text(data["git_blob"], "selection.git_blob")):
        fail("selection.git_blob: expected exact Git blob")
    for name in ("raw_sha256", "canonical_sha256"):
        if not HEX64.fullmatch(text(data[name], f"selection.{name}")):
            fail(f"selection.{name}: expected SHA-256")
    reviews = data["review_evidence"]
    if not isinstance(reviews, list) or not reviews or len(reviews) != len(set(reviews)):
        fail("selection.review_evidence: expected unique nonempty list")
    for review in reviews:
        text(review, "selection.review_evidence item")
        if not re.fullmatch(r"https://github\.com/siege-analytics/claude-configs-public/pull/[0-9]+#(?:pullrequestreview|issuecomment)-[0-9]+", review):
            fail("selection.review_evidence: expected exact GitHub PR review or conversation-comment URL")
    return data


def git_snapshot_bytes(root: Path, revision: str, path: Path) -> bytes:
    try:
        ancestor = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", revision, "HEAD"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        )
        if ancestor.returncode != 0:
            fail("selected policy revision is unavailable or is not an ancestor of HEAD")
        return subprocess.check_output(
            ["git", "-C", str(root), "show", f"{revision}:{path.as_posix()}"],
            stderr=subprocess.DEVNULL, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot load selected policy snapshot {revision}:{path}: {exc}")


def load_selected_json(root: Path, selection: dict[str, Any], path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = git_snapshot_bytes(root, selection["policy_revision"], path)
    return raw, parse_json(raw, f"git:{selection['policy_revision']}:{path.as_posix()}")


def validate_fixture_agreement(
    root: Path, contract: dict[str, Any], policy: dict[str, Any], gc: Any,
    fixtures: list[dict[str, Any]],
) -> None:
    validated = [gc.validate_fixture(item, contract, f"selected fixture {item.get('fixture_id', '?')}", root) for item in fixtures]
    by_identity = {
        identity_tuple(normalize_identity(item["repository_identity"], f"fixture {item['fixture_id']} identity", with_source=False)): item
        for item in validated
    }
    projects = {
        identity_tuple(normalize_identity(item["repository_identity"], f"project {item['id']} identity", with_source=False)): item
        for item in policy["projects"]
    }
    # Public examples are intentionally synthetic and need not mirror every
    # reviewed deployment identity. Every selected fixture must still map to an
    # exact approved project and agree completely; the independently reviewed
    # policy snapshot remains authoritative for additional deployment entries.
    if not set(by_identity).issubset(projects):
        fail("selected fixture identity is absent from effective policy projects")
    for identity, fixture in by_identity.items():
        project = projects[identity]
        values, _ = resolve_values(contract, policy, project)
        if fixture["fixture_id"] != project["id"] or fixture["values"] != values:
            fail(f"project {project['id']}: resolved values disagree with selected fixture")
        if fixture["parent_lock"] != policy["parent_lock"]:
            fail(f"project {project['id']}: selected fixture parent lock disagrees with policy")


def load_inputs(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    gc = _gate_contract_module()
    contract = gc.load_contract(root)
    selection = validate_selection(read_json(root / SELECTION))
    raw, selected = load_selected_json(root, selection, POLICY)
    if hashlib.sha256(raw).hexdigest() != selection["raw_sha256"]:
        fail("selected policy raw-byte digest disagrees with review receipt")
    if digest(selected) != selection["canonical_sha256"]:
        fail("selected policy canonical digest disagrees with review receipt")
    try:
        blob = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", f"{selection['policy_revision']}:{POLICY.as_posix()}"],
            text=True, stderr=subprocess.DEVNULL, timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"cannot verify selected policy Git blob: {exc}")
    if blob != selection["git_blob"]:
        fail("selected policy Git blob disagrees with review receipt")
    policy = selected
    validate_policy(policy, contract, f"git:{selection['policy_revision']}:{POLICY.as_posix()}")
    fixtures = [load_selected_json(root, selection, path)[1] for path in gc.FIXTURES]
    validate_fixture_agreement(root, contract, policy, gc, fixtures)
    return contract, policy, selection


def validate_context(data: Any, contract: dict[str, Any]) -> dict[str, Any]:
    exact_fields(data, CONTEXT_FIELDS, "context")
    identities = data["identities"]
    if not isinstance(identities, list):
        fail("context.identities: expected list")
    normalized = [normalize_identity(item, f"context.identities[{index}]", with_source=True) for index, item in enumerate(identities)]
    sources = [item["source"] for item in normalized]
    if len(sources) != len(set(sources)):
        fail("context.identities: duplicate identity source")
    capability_ids = {item["id"] for item in contract["capabilities"]}
    capabilities = data["capabilities"]
    if not isinstance(capabilities, dict):
        fail("context.capabilities: expected object")
    unknown = set(capabilities) - capability_ids
    if unknown:
        fail(f"context.capabilities: unknown capability IDs {sorted(unknown)}")
    for ident, state in capabilities.items():
        if state not in CAPABILITY_STATES:
            fail(f"context.capabilities.{ident}: unsupported state {state!r}")
    install = data["install_configuration"]
    if not isinstance(install, dict) or any(not isinstance(key, str) for key in install):
        fail("context.install_configuration: expected object with string keys")
    evidence = data["task_evidence"]
    if not isinstance(evidence, list) or any(not isinstance(item, str) or not item for item in evidence):
        fail("context.task_evidence: expected list of nonempty strings")
    return {
        "identities": normalized,
        "capabilities": dict(capabilities),
        "install_configuration": copy.deepcopy(install),
        "task_evidence": list(evidence),
    }


def validate_operation(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or "type" not in data:
        fail("operation: expected object with type")
    kind = data["type"]
    if kind not in OPERATION_FIELDS:
        fail(f"operation: unsupported type {kind!r}")
    exact_fields(data, OPERATION_FIELDS[kind], "operation")
    if kind == "feature-merge":
        branch = text(data["target_branch"], "operation.target_branch")
        if not REPO_PART.fullmatch(branch):
            fail("operation.target_branch: invalid branch name for bounded pilot")
    elif kind == "ticket-commit":
        text(data["message"], "operation.message")
    return dict(data)


def _apply_layer(
    resolved: dict[str, dict[str, Any]],
    provenance: dict[str, dict[str, dict[str, Any]]],
    patch: dict[str, dict[str, Any]],
    layer: str,
    source: str,
) -> None:
    for field_id, changes in patch.items():
        for path, value in changes.items():
            previous = resolved[field_id][path]
            provenance[field_id][path]["replaced"].append({
                "value": previous,
                "layer": provenance[field_id][path]["layer"],
                "source": provenance[field_id][path]["source"],
            })
            resolved[field_id][path] = value
            provenance[field_id][path].update(value=value, layer=layer, source=source)


def resolve_values(contract: dict[str, Any], policy: dict[str, Any], project: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    policies = {item["id"]: item for item in contract["policy_fields"]}
    resolved = {ident: copy.deepcopy(item["default"]) for ident, item in policies.items()}
    provenance: dict[str, dict[str, dict[str, Any]]] = {}
    for ident, item in policies.items():
        provenance[ident] = {}
        locked = set(item["override_policy"]["locked_paths"])
        for path, value in item["default"].items():
            provenance[ident][path] = {
                "value": value,
                "layer": "parent-default",
                "source": policy["contract_source"],
                "scope": item["scope"],
                "required_capabilities": list(item["required_capability_ids"]),
                "replaced": [],
                "locked": path in locked,
            }
    profiles = {item["id"]: item for item in policy["organization_profiles"]}
    profile_id = project["organization_profile"]
    _apply_layer(resolved, provenance, profiles[profile_id]["values"], "organization-profile", profile_id)
    _apply_layer(resolved, provenance, project["values"], "project", project["id"])
    return resolved, provenance


def policy_payload(policy: dict[str, Any], identity: dict[str, str], project: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    return {
        "resolver_version": policy["resolver_version"],
        "contract_sha256": policy["contract_sha256"],
        "parent_contract_revision": policy["parent_contract_revision"],
        "parent_lock": policy["parent_lock"],
        "repository_identity": {key: identity[key] for key in ("host", "owner", "repository")},
        "project": project["id"],
        "organization_profile": project["organization_profile"],
        "values": values,
    }


def resident_workflow(values: dict[str, Any]) -> str:
    branch = values["branch-policy"]["integration_branch"]
    procedure = values["review-procedure-binding"]["procedure"]
    ticket = "required" if values["ticket-requirement"]["required"] else "not required"
    return (
        f"Feature and fix work targets `{branch}`. Ticket evidence is {ticket} under "
        f"`{values['ticket-requirement']['match_policy']}`. Run `{procedure}` for the "
        "review procedure; procedure selection has no authorization effect. Protected "
        "acceptance and actual host capabilities remain independently required."
    )


def _operation_field(kind: str) -> str:
    return {
        "feature-merge": "branch-policy",
        "ticket-commit": "ticket-requirement",
        "review-procedure": "review-procedure-binding",
    }[kind]


def decide(operation: dict[str, Any], values: dict[str, Any], contract: dict[str, Any], capabilities: dict[str, str]) -> dict[str, Any]:
    kind = operation["type"]
    field_id = _operation_field(kind)
    reasons: list[str] = []
    if kind == "feature-merge":
        expected = values[field_id]["integration_branch"]
        policy_decision = "allow" if operation["target_branch"] == expected else "deny"
        reasons.append(f"feature target must equal effective integration branch {expected!r}")
    elif kind == "ticket-commit":
        required = values[field_id]["required"]
        matched = re.search(r"(?<![A-Za-z0-9])#[0-9]+(?![A-Za-z0-9])", operation["message"]) is not None
        policy_decision = "allow" if not required or matched else "deny"
        reasons.append("canonical ticket reference present" if matched else "required canonical ticket reference missing")
    else:
        policy_decision = "allow"
        reasons.append(f"resolved review procedure {values[field_id]['procedure']!r}; authorization effect remains none")

    policies = {item["id"]: item for item in contract["policy_fields"]}
    required_ids = policies[field_id]["required_capability_ids"]
    states = {ident: capabilities.get(ident, "unverified") for ident in required_ids}
    if all(state == "verified" for state in states.values()):
        readiness = "verified"
    elif any(state == "unsupported" for state in states.values()):
        readiness = "unsupported"
    else:
        readiness = "unverified"
    if policy_decision == "deny":
        final = "deny"
    else:
        # #848 is a pure configured-policy evaluator. Capability states are
        # explicit observations for explanation, not authenticated host facts.
        # A protected adapter in #1002/#1003 must establish acceptance authority;
        # until then even a caller-supplied `verified` state cannot authorize.
        final = "unknown"
        if readiness != "verified":
            reasons.append(f"required capability readiness is {readiness}")
        else:
            reasons.append("capability states are unauthenticated evaluator inputs; protected adapter proof is required")
    return {
        "policy": policy_decision,
        "capability_readiness": readiness,
        "final": final,
        "required_capabilities": states,
        "reasons": reasons,
    }


def _candidate_result(
    candidate: dict[str, Any] | None,
    contract: dict[str, Any],
    active_identity: tuple[str, str, str],
    active_values: dict[str, Any],
) -> dict[str, Any] | None:
    if candidate is None:
        return None
    try:
        validate_policy(candidate, contract, "candidate policy")
        projects = {identity_tuple(normalize_identity(item["repository_identity"], "candidate project identity", with_source=False)): item for item in candidate["projects"]}
        project = projects.get(active_identity)
        if project is None:
            fail("candidate policy does not contain the active repository identity")
        candidate_values, _ = resolve_values(contract, candidate, project)
        changes = []
        for field_id in sorted(active_values):
            for path in sorted(active_values[field_id]):
                before, after = active_values[field_id][path], candidate_values[field_id][path]
                if before != after:
                    changes.append({"field_id": field_id, "path": path, "active": before, "proposed": after})
        return {
            "state": "schema-valid-proposal",
            "digest": digest(policy_payload(candidate, {"host": active_identity[0], "owner": active_identity[1], "repository": active_identity[2]}, project, candidate_values)),
            "declared_parent_contract_revision": candidate["parent_contract_revision"],
            "fixture_agreement": "not-evaluated-for-unapproved-proposal",
            "changes": changes,
            "authorization_effect": "none",
        }
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"state": "rejected", "diagnostic": str(exc), "authorization_effect": "none"}


def explain(
    contract: dict[str, Any], policy: dict[str, Any], selection: dict[str, Any],
    context: dict[str, Any], operation: dict[str, Any], candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = validate_context(context, contract)
    operation = validate_operation(operation)
    identities = context["identities"]
    base = {
        "schema_version": 1,
        "contract_sha256": policy["contract_sha256"],
        "parent_contract_revision": policy["parent_contract_revision"],
        "policy_selection": {
            "source": SELECTION.as_posix(),
            "policy_revision": selection["policy_revision"],
            "policy_path": selection["policy_path"],
            "git_blob": selection["git_blob"],
            "raw_sha256": selection["raw_sha256"],
            "canonical_sha256": selection["canonical_sha256"],
            "review_evidence": list(selection["review_evidence"]),
        },
        "identity_sources": identities,
        "operation": operation,
        "install_configuration": {"value": context["install_configuration"], "authorization_effect": "none"},
        "task_evidence": {"value": context["task_evidence"], "authorization_effect": "none"},
    }
    if not identities:
        return {**base, "state": "unknown", "diagnostic": "repository identity is missing", "decision": {"final": "unknown"}}
    distinct = {identity_tuple(item) for item in identities}
    if len(distinct) != 1:
        return {**base, "state": "ambiguous", "diagnostic": "repository identity sources disagree", "decision": {"final": "unknown"}}
    target = next(iter(distinct))
    projects: dict[tuple[str, str, str], dict[str, Any]] = {}
    for project in policy["projects"]:
        identity = normalize_identity(project["repository_identity"], f"project {project['id']} identity", with_source=False)
        projects[identity_tuple(identity)] = project
    project = projects.get(target)
    if project is None:
        return {**base, "state": "unknown", "diagnostic": "repository identity is not declared by approved policy", "decision": {"final": "unknown"}}
    identity = {"host": target[0], "owner": target[1], "repository": target[2]}
    values, provenance = resolve_values(contract, policy, project)
    active_payload = policy_payload(policy, identity, project, values)
    active_digest = digest(active_payload)
    result = {
        **base,
        "state": "resolved",
        "repository_identity": identity,
        "project": project["id"],
        "organization_profile": project["organization_profile"],
        "approved_policy": {
            "source": f"git:{selection['policy_revision']}:{selection['policy_path']}",
            "revision": selection["policy_revision"],
            "git_blob": selection["git_blob"],
            "raw_sha256": selection["raw_sha256"],
            "canonical_snapshot_sha256": selection["canonical_sha256"],
            "parent_contract_revision": policy["parent_contract_revision"],
            "effective_digest": active_digest,
            "parent_lock": copy.deepcopy(policy["parent_lock"]),
        },
        "values": values,
        "provenance": provenance,
        "capabilities": {
            item["id"]: context["capabilities"].get(item["id"], "unverified")
            for item in contract["capabilities"]
        },
        "resident_workflow": resident_workflow(values),
        "decision": decide(operation, values, contract, context["capabilities"]),
    }
    proposed = _candidate_result(candidate, contract, target, values)
    if proposed is not None:
        result["proposed_policy"] = proposed
    return result


def validate_generated(manifest: dict[str, Any], policy: dict[str, Any], selection: dict[str, Any]) -> None:
    expected_source = f"git:{selection['policy_revision']}:{selection['policy_path']}"
    if manifest.get("effective_policy_source") != expected_source:
        fail("generated manifest has wrong effective policy source")
    if manifest.get("effective_policy_sha256") != digest(policy):
        fail("generated manifest has wrong effective policy digest")
    if manifest.get("effective_policy") != policy:
        fail("generated manifest disagrees with effective policy source")
    if manifest.get("effective_policy_selection") != selection:
        fail("generated manifest disagrees with reviewed policy selection")
    if manifest.get("effective_policy_evidence_state") != "configured":
        fail("generated manifest must label effective policy as configured evidence only")


def default_context(identity: str, capability_pairs: list[str]) -> dict[str, Any]:
    parts = identity.strip("/").split("/") if identity else []
    identities = []
    if parts:
        if len(parts) != 3:
            fail("--identity must be canonical host/owner/repository")
        identities.append({"source": "explicit-target", "host": parts[0], "owner": parts[1], "repository": parts[2]})
    capabilities: dict[str, str] = {}
    for item in capability_pairs:
        ident, separator, state = item.partition("=")
        if not separator or ident in capabilities:
            fail("--capability requires unique ID=state pairs")
        capabilities[ident] = state
    return {"identities": identities, "capabilities": capabilities, "install_configuration": {}, "task_evidence": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "explain", "check"))
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--context", type=Path)
    parser.add_argument("--operation", type=Path)
    parser.add_argument("--identity", default="")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--generated-root", type=Path)
    args = parser.parse_args()
    try:
        contract, policy, selection = load_inputs(ROOT)
        if args.generated_root:
            manifest = read_json(args.generated_root / "craft-agent/enforcement-manifest.json")
            validate_generated(manifest, policy, selection)
        if args.command == "validate":
            print(json.dumps({"state": "valid", "policy_sha256": digest(policy)}, sort_keys=True))
            return 0
        if args.operation is None:
            fail("explain/check requires --operation")
        context = read_json(args.context) if args.context else default_context(args.identity, args.capability)
        operation = read_json(args.operation)
        candidate = read_json(args.candidate) if args.candidate else read_json(ROOT / POLICY)
        result = explain(contract, policy, selection, context, operation, candidate)
        print(json.dumps(result, sort_keys=True))
        if args.command == "explain":
            return 0
        return 0 if result.get("decision", {}).get("final") == "allow" else 1
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        print(json.dumps({"schema_version": 1, "state": "error", "diagnostic": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
