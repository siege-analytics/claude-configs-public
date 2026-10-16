#!/usr/bin/env python3
"""Validate the bounded gate/capability contract and its generated agreement.

This module deliberately is not a policy resolver. It validates the typed source
contract, two synthetic instances, configured artifact agreement, and the one
native ticket pilot probe. Live host and protected-acceptance evidence belong to
later acceptance stages (#1002/#1003).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path("catalog/gate-contracts.json")
SCHEMA = Path("catalog/gate-contract-schema.json")
FIXTURES = (
    Path("examples/scaffolding/strict-release-policy.json"),
    Path("examples/scaffolding/synthetic-trunk-policy.json"),
)
ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
PROCEDURE = re.compile(r"[a-z][a-z0-9-]*(?:--[a-z][a-z0-9-]*)?\Z")
SEMVER = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
DECISIONS = ["allow", "deny", "not-applicable", "unknown", "error"]
CAPABILITY_STATES = ["verified", "unsupported", "unverified"]
SCHEMA_SHA256 = "3cd65d6ffee11f39baca5c066d550fb89e5e2ccab4ee73e51f8a87bf00974d72"
PROTECTED_ADAPTER_WORKFLOW_SHA256 = "13b83c61b8326f9c2deaab9beb8611968a7c00562dcb1b155dba9c37f0748d50"
# The bounded pilot supports one reviewed registration/package shape per
# capability. Reject alternate declarations until a migrated behavior needs
# them; otherwise metadata can drift from the concrete builder/verifier path.
SUPPORTED_CAPABILITY_TARGETS = {
    "native-ticket-commit-msg": {
        "kind": "executable",
        "registered_path": ".githooks/commit-msg",
        "package_paths": ("dist/craft-agent/.githooks/commit-msg",),
    },
    "native-branch-pre-push": {
        "kind": "generated-executable",
        "registered_path": "dist/craft-agent/.githooks/pre-push",
        "package_paths": ("dist/craft-agent/.githooks/pre-push",),
    },
    "protected-range-validation": {
        "kind": "external",
        "registered_path": ".github/workflows/pr-base-guard.yml",
        "package_paths": (),
    },
    "procedure-binding-resolution": {
        "kind": "declarative",
        "registered_path": "skills/self-review/SKILL.md",
        "package_paths": ("dist/craft-agent/skills/self-review/SKILL.md",),
    },
}
CONTRACT_FIELDS = {
    "schema_version", "contract_version", "ontology_version", "decision_values",
    "capability_states", "policy_fields", "capabilities",
}
POLICY_FIELDS = {
    "id", "ontology_term", "owner", "scope", "value_schema", "default",
    "override_policy", "required_capability_ids",
}
CAPABILITY_FIELDS = {
    "id", "ontology_term", "boundary", "kind", "registered_path",
    "input_contract", "result_contract", "failure_semantics", "package_paths",
    "acceptance_probe_ids", "configured_evidence_only",
}
VALUE_SCHEMA_FIELDS = {"type", "properties", "required", "additional_properties"}
PROPERTY_BASE_FIELDS = {"type"}
OVERRIDE_FIELDS = {"organization_profile_paths", "project_paths", "locked_paths"}
RESULT_FIELDS = {"type", "allow", "deny", "error"}
FIXTURE_FIELDS = {
    "schema_version", "fixture_id", "repository_identity", "parent_lock",
    "values", "declared_overrides",
}
IDENTITY_FIELDS = {"host", "owner", "repository"}
LOCK_FIELDS = {
    "host", "owner", "repository", "revision", "import_mechanism", "digest",
    "tool_version",
}
DECLARATION_FIELDS = {"field_id", "path", "layer"}


def fail(message: str) -> None:
    raise ValueError(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read JSON {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path}: expected an object")
    return value


def exact_fields(value: Any, expected: set[str], context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        fail(f"{context}: expected an object")
    unknown = set(value) - expected
    missing = expected - set(value)
    if unknown or missing:
        fail(f"{context}: fields differ; unknown={sorted(unknown)} missing={sorted(missing)}")
    return value


def text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        fail(f"{context}: expected nonempty text without surrounding whitespace")
    return value


def identifier(value: Any, context: str) -> str:
    value = text(value, context)
    if not ID.fullmatch(value):
        fail(f"{context}: expected lowercase hyphenated identifier")
    return value


def string_list(value: Any, context: str, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        fail(f"{context}: expected {'a' if empty else 'a nonempty'} list")
    result = [text(item, context) for item in value]
    if len(result) != len(set(result)):
        fail(f"{context}: duplicate values")
    return result


def repository_path(root: Path, value: str, context: str, *, must_exist: bool = True) -> Path:
    text(value, context)
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or "\\" in value:
        fail(f"{context}: path must stay within repository: {value}")
    resolved_root = root.resolve()
    current = resolved_root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            fail(f"{context}: path contains symlink: {value}")
    resolved = (resolved_root / relative).resolve()
    if not resolved.is_relative_to(resolved_root):
        fail(f"{context}: path escapes repository: {value}")
    if must_exist and not resolved.exists():
        fail(f"{context}: path is missing: {value}")
    return resolved


def validate_property_schema(schema: Any, context: str) -> None:
    if not isinstance(schema, dict):
        fail(f"{context}: expected object")
    allowed = PROPERTY_BASE_FIELDS | ({"enum"} if "enum" in schema else set()) | ({"pattern"} if "pattern" in schema else set())
    if set(schema) != allowed:
        fail(f"{context}: unsupported schema fields {sorted(set(schema) - allowed)}")
    kind = text(schema["type"], f"{context}.type")
    if kind not in {"string", "boolean"}:
        fail(f"{context}.type: only string and boolean are supported in the pilot")
    if "enum" in schema:
        if kind != "string":
            fail(f"{context}.enum: enum requires string type")
        string_list(schema["enum"], f"{context}.enum")
    if "pattern" in schema:
        if kind != "string" or "enum" in schema:
            fail(f"{context}.pattern: pattern requires a non-enum string")
        try:
            re.compile(text(schema["pattern"], f"{context}.pattern") + r"\Z")
        except re.error as exc:
            fail(f"{context}.pattern: invalid regular expression: {exc}")


def validate_typed_value(value: Any, schema: dict[str, Any], context: str) -> None:
    if schema["type"] != "object" or not isinstance(value, dict):
        fail(f"{context}: expected object")
    properties = schema["properties"]
    if not isinstance(properties, dict) or not properties:
        fail(f"{context}: schema properties must be nonempty")
    required = string_list(schema["required"], f"{context}.required")
    if set(required) != set(properties):
        fail(f"{context}: all pilot properties must be required")
    if schema["additional_properties"] is not False:
        fail(f"{context}: additional_properties must be false")
    if set(value) != set(properties):
        fail(f"{context}: value fields differ; expected {sorted(properties)} got {sorted(value)}")
    for name, prop in properties.items():
        identifier(name.replace("_", "-"), f"{context}.{name} name")
        validate_property_schema(prop, f"{context}.{name} schema")
        actual = value[name]
        if prop["type"] == "string":
            text(actual, f"{context}.{name}")
            if "enum" in prop and actual not in prop["enum"]:
                fail(f"{context}.{name}: value is outside enum")
            if "pattern" in prop and not re.fullmatch(prop["pattern"], actual):
                fail(f"{context}.{name}: value does not match pattern")
        elif type(actual) is not bool:
            fail(f"{context}.{name}: expected boolean")


def validate_json_schema_instance(instance: Any, schema: Any, root_schema: dict[str, Any], context: str = "contract") -> None:
    """Evaluate the bounded JSON Schema vocabulary used by this catalog."""
    if not isinstance(schema, dict):
        fail(f"{context}: advertised schema node is not an object")
    if "$ref" in schema:
        ref = schema["$ref"]
        prefix = "#/$defs/"
        if not isinstance(ref, str) or not ref.startswith(prefix) or "/" in ref[len(prefix):]:
            fail(f"{context}: unsupported advertised schema reference {ref!r}")
        name = ref[len(prefix):]
        target = root_schema.get("$defs", {}).get(name)
        if target is None:
            fail(f"{context}: missing advertised schema definition {name}")
        validate_json_schema_instance(instance, target, root_schema, context)
        return
    if "const" in schema and instance != schema["const"]:
        fail(f"{context}: canonical source violates advertised const")
    if "enum" in schema and instance not in schema["enum"]:
        fail(f"{context}: canonical source violates advertised enum")
    kind = schema.get("type")
    expected_types = {
        "object": dict, "array": list, "string": str, "integer": int, "boolean": bool,
    }
    if kind in expected_types and type(instance) is not expected_types[kind]:
        fail(f"{context}: canonical source violates advertised type {kind}")
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            fail(f"{context}: canonical source violates advertised minLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            fail(f"{context}: canonical source violates advertised pattern")
    if isinstance(instance, int) and not isinstance(instance, bool) and instance < schema.get("minimum", instance):
        fail(f"{context}: canonical source violates advertised minimum")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0) or len(instance) > schema.get("maxItems", len(instance)):
            fail(f"{context}: canonical source violates advertised item count")
        if schema.get("uniqueItems"):
            values = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in instance]
            if len(values) != len(set(values)):
                fail(f"{context}: canonical source violates advertised uniqueness")
        if "items" in schema:
            for index, value in enumerate(instance):
                validate_json_schema_instance(value, schema["items"], root_schema, f"{context}[{index}]")
    if isinstance(instance, dict):
        if len(instance) < schema.get("minProperties", 0):
            fail(f"{context}: canonical source violates advertised minProperties")
        required = schema.get("required", [])
        missing = set(required) - set(instance)
        if missing:
            fail(f"{context}: canonical source misses advertised fields {sorted(missing)}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(instance) - set(properties)
            if unknown:
                fail(f"{context}: canonical source has fields forbidden by advertised schema {sorted(unknown)}")
        for key, subschema in properties.items():
            if key in instance:
                validate_json_schema_instance(instance[key], subschema, root_schema, f"{context}.{key}")


def validate_schema_document(data: Any) -> dict[str, Any]:
    """Guard the checked-in JSON Schema from drifting behind the strict checker."""
    required = {"$schema", "$id", "title", "type", "additionalProperties", "required", "properties", "$defs"}
    exact_fields(data, required, "gate contract schema")
    if data["$schema"] != "https://json-schema.org/draft/2020-12/schema":
        fail("gate contract schema: unsupported JSON Schema dialect")
    if data["type"] != "object" or data["additionalProperties"] is not False:
        fail("gate contract schema: root must be a closed object")
    if set(data["required"]) != CONTRACT_FIELDS or set(data["properties"]) != CONTRACT_FIELDS:
        fail("gate contract schema: root fields disagree with strict checker")
    if data["properties"].get("decision_values", {}).get("const") != DECISIONS:
        fail("gate contract schema: decision values disagree with strict checker")
    if data["properties"].get("capability_states", {}).get("const") != CAPABILITY_STATES:
        fail("gate contract schema: capability states disagree with strict checker")
    expected_defs = {"identifier", "string_list", "value_schema", "override_policy", "policy_field", "result_contract", "capability"}
    if set(data["$defs"]) != expected_defs:
        fail("gate contract schema: definitions disagree with strict checker")
    capability = data["$defs"]["capability"]
    if capability.get("additionalProperties") is not False or set(capability.get("required", [])) != CAPABILITY_FIELDS:
        fail("gate contract schema: capability fields disagree with strict checker")
    configured = capability.get("properties", {}).get("configured_evidence_only", {})
    if configured.get("const") is not True:
        fail("gate contract schema: configured evidence constraint disagrees with strict checker")
    policy = data["$defs"]["policy_field"]
    if policy.get("additionalProperties") is not False or set(policy.get("required", [])) != POLICY_FIELDS:
        fail("gate contract schema: policy fields disagree with strict checker")
    override = data["$defs"]["override_policy"]
    if override.get("additionalProperties") is not False or set(override.get("required", [])) != OVERRIDE_FIELDS:
        fail("gate contract schema: override fields disagree with strict checker")
    if set(override.get("properties", {})) != OVERRIDE_FIELDS or any(
        value != {"$ref": "#/$defs/string_list"}
        for value in override["properties"].values()
    ):
        fail("gate contract schema: override path types disagree with strict checker")
    policy_properties = policy.get("properties", {})
    if set(policy_properties) != POLICY_FIELDS:
        fail("gate contract schema: policy property definitions disagree with strict checker")
    capability_properties = capability.get("properties", {})
    if set(capability_properties) != CAPABILITY_FIELDS:
        fail("gate contract schema: capability property definitions disagree with strict checker")
    result = data["$defs"]["result_contract"]
    if result.get("additionalProperties") is not False or set(result.get("required", [])) != RESULT_FIELDS:
        fail("gate contract schema: result fields disagree with strict checker")
    digest = hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    if digest != SCHEMA_SHA256:
        fail("gate contract schema: complete schema digest differs from the reviewed bounded schema")
    return data


def validate_contract(data: Any, root: Path = ROOT, *, check_paths: bool = True) -> dict[str, Any]:
    exact_fields(data, CONTRACT_FIELDS, "gate contract")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("gate contract: schema_version must be integer 1")
    for field in ("contract_version", "ontology_version"):
        if not SEMVER.fullmatch(text(data[field], field)):
            fail(f"{field}: expected major.minor.patch")
    if data["decision_values"] != DECISIONS:
        fail(f"decision_values must equal {DECISIONS}")
    if data["capability_states"] != CAPABILITY_STATES:
        fail(f"capability_states must equal {CAPABILITY_STATES}")

    capabilities: dict[str, dict[str, Any]] = {}
    probe_ids: set[str] = set()
    if not isinstance(data["capabilities"], list) or not data["capabilities"]:
        fail("capabilities: expected nonempty list")
    for raw in data["capabilities"]:
        capability = exact_fields(raw, CAPABILITY_FIELDS, "capability")
        ident = identifier(capability["id"], "capability.id")
        if ident in capabilities:
            fail(f"duplicate capability id: {ident}")
        if capability["ontology_term"] != "host-capability":
            fail(f"{ident}: ontology_term must be host-capability")
        identifier(capability["boundary"], f"{ident}.boundary")
        kind = text(capability["kind"], f"{ident}.kind")
        if kind not in {"executable", "generated-executable", "external", "declarative"}:
            fail(f"{ident}.kind: unsupported kind {kind}")
        path = repository_path(root, capability["registered_path"], f"{ident}.registered_path", must_exist=check_paths and kind != "generated-executable")
        if check_paths and kind == "executable" and (not path.is_file() or not path.stat().st_mode & 0o111):
            fail(f"{ident}: registered executable is not executable")
        inputs = string_list(capability["input_contract"], f"{ident}.input_contract")
        for item in inputs:
            identifier(item, f"{ident}.input_contract item")
        result = exact_fields(capability["result_contract"], RESULT_FIELDS, f"{ident}.result_contract")
        if result["type"] not in {"process-exit", "protected-check", "decision"}:
            fail(f"{ident}: unsupported result type")
        codes: list[int] = []
        for outcome in ("allow", "deny", "error"):
            values = result[outcome]
            if not isinstance(values, list) or not values or any(type(code) is not int or code < 0 for code in values):
                fail(f"{ident}.{outcome}: expected nonempty list of nonnegative integer codes")
            codes.extend(values)
        if len(codes) != len(set(codes)):
            fail(f"{ident}: contradictory result codes overlap")
        if capability["failure_semantics"] not in {"error-never-allow", "unknown-never-allow"}:
            fail(f"{ident}: unsupported failure semantics")
        packages = string_list(capability["package_paths"], f"{ident}.package_paths", empty=True)
        for package in packages:
            repository_path(root, package, f"{ident}.package_paths", must_exist=False)
        target = SUPPORTED_CAPABILITY_TARGETS.get(ident)
        if target is None:
            fail(f"unsupported pilot capability id: {ident}")
        if (
            kind != target["kind"]
            or capability["registered_path"] != target["registered_path"]
            or tuple(packages) != target["package_paths"]
        ):
            fail(f"{ident}: registration/package declaration differs from the supported bounded target")
        probes = string_list(capability["acceptance_probe_ids"], f"{ident}.acceptance_probe_ids")
        for probe in probes:
            identifier(probe, f"{ident}.probe")
            if probe in probe_ids:
                fail(f"duplicate acceptance probe id: {probe}")
            probe_ids.add(probe)
        if capability["configured_evidence_only"] is not True:
            fail(f"{ident}: generated registration must be configured evidence only")
        capabilities[ident] = capability

    if set(capabilities) != set(SUPPORTED_CAPABILITY_TARGETS):
        fail(f"pilot capabilities differ from supported IDs: {sorted(set(capabilities) ^ set(SUPPORTED_CAPABILITY_TARGETS))}")

    fields: dict[str, dict[str, Any]] = {}
    if not isinstance(data["policy_fields"], list) or not data["policy_fields"]:
        fail("policy_fields: expected nonempty list")
    for raw in data["policy_fields"]:
        policy = exact_fields(raw, POLICY_FIELDS, "policy field")
        ident = identifier(policy["id"], "policy field.id")
        if ident in fields:
            fail(f"duplicate policy field id: {ident}")
        if policy["ontology_term"] not in {"policy", "procedure-binding"}:
            fail(f"{ident}: unsupported ontology term")
        identifier(policy["owner"], f"{ident}.owner")
        identifier(policy["scope"], f"{ident}.scope")
        schema = exact_fields(policy["value_schema"], VALUE_SCHEMA_FIELDS, f"{ident}.value_schema")
        validate_typed_value(policy["default"], schema, f"{ident}.default")
        override = exact_fields(policy["override_policy"], OVERRIDE_FIELDS, f"{ident}.override_policy")
        property_names = set(schema["properties"])
        seen: set[str] = set()
        for name in ("organization_profile_paths", "project_paths", "locked_paths"):
            paths = string_list(override[name], f"{ident}.{name}", empty=True)
            unknown = set(paths) - property_names
            if unknown:
                fail(f"{ident}.{name}: unknown paths {sorted(unknown)}")
            overlap = seen.intersection(paths)
            if overlap:
                fail(f"{ident}: contradictory override/lock declarations {sorted(overlap)}")
            seen.update(paths)
        if seen != property_names:
            fail(f"{ident}: every value path must be overrideable or locked; missing {sorted(property_names - seen)}")
        required = string_list(policy["required_capability_ids"], f"{ident}.required_capability_ids")
        unknown_capabilities = set(required) - capabilities.keys()
        if unknown_capabilities:
            fail(f"{ident}: unknown required capabilities {sorted(unknown_capabilities)}")
        fields[ident] = policy
    if set(fields) != {"branch-policy", "ticket-requirement", "review-procedure-binding"}:
        fail("pilot must contain exactly branch-policy, ticket-requirement, review-procedure-binding")
    return data


def contract_digest(data: dict[str, Any]) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(canonical).hexdigest()


def load_contract(root: Path = ROOT, *, check_paths: bool = True) -> dict[str, Any]:
    schema = validate_schema_document(read_json(root / SCHEMA))
    data = read_json(root / CONTRACT)
    validate_json_schema_instance(data, schema, schema)
    return validate_contract(data, root, check_paths=check_paths)


def validate_fixture(data: Any, contract: dict[str, Any], context: str, root: Path = ROOT) -> dict[str, Any]:
    exact_fields(data, FIXTURE_FIELDS, context)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail(f"{context}: schema_version must be integer 1")
    identifier(data["fixture_id"], f"{context}.fixture_id")
    identity = exact_fields(data["repository_identity"], IDENTITY_FIELDS, f"{context}.repository_identity")
    for field, value in identity.items():
        text(value, f"{context}.repository_identity.{field}")
    lock = exact_fields(data["parent_lock"], LOCK_FIELDS, f"{context}.parent_lock")
    for field in ("host", "owner", "repository", "import_mechanism", "tool_version"):
        text(lock[field], f"{context}.parent_lock.{field}")
    if not HEX40.fullmatch(text(lock["revision"], f"{context}.parent_lock.revision")):
        fail(f"{context}: parent revision must be an exact 40-character SHA")
    if not HEX64.fullmatch(text(lock["digest"], f"{context}.parent_lock.digest")):
        fail(f"{context}: parent digest must be a SHA-256")
    policies = {item["id"]: item for item in contract["policy_fields"]}
    values = data["values"]
    if not isinstance(values, dict) or set(values) != set(policies):
        fail(f"{context}.values: expected exactly {sorted(policies)}")
    changed: set[tuple[str, str]] = set()
    for ident, policy in policies.items():
        validate_typed_value(values[ident], policy["value_schema"], f"{context}.{ident}")
        for path, value in values[ident].items():
            if value != policy["default"][path]:
                changed.add((ident, path))
    declarations = data["declared_overrides"]
    if not isinstance(declarations, list):
        fail(f"{context}.declared_overrides: expected list")
    declared: set[tuple[str, str]] = set()
    for raw in declarations:
        item = exact_fields(raw, DECLARATION_FIELDS, f"{context}.override")
        ident = identifier(item["field_id"], f"{context}.override.field_id")
        path = text(item["path"], f"{context}.override.path")
        layer = text(item["layer"], f"{context}.override.layer")
        if ident not in policies:
            fail(f"{context}: override references unknown field {ident}")
        key = (ident, path)
        if key in declared:
            fail(f"{context}: duplicate/conflicting override declaration {ident}.{path}")
        declared.add(key)
        allowed_name = {"organization-profile": "organization_profile_paths", "project": "project_paths"}.get(layer)
        if not allowed_name or path not in policies[ident]["override_policy"][allowed_name]:
            fail(f"{context}: unauthorized {layer} override of {ident}.{path}")
    if declared != changed:
        fail(f"{context}: declared overrides do not match changed values; declared={sorted(declared)} changed={sorted(changed)}")
    procedure = values["review-procedure-binding"]["procedure"]
    if "--" in procedure:
        project, skill = procedure.split("--", 1)
        procedure_path = Path("projects") / project / "skills" / skill / "SKILL.md"
    else:
        procedure_path = Path("skills") / procedure / "SKILL.md"
    repository_path(root, procedure_path.as_posix(), f"{context}.review procedure")
    return data


def load_fixtures(root: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures = [validate_fixture(read_json(root / path), contract, path.as_posix(), root) for path in FIXTURES]
    ids = [item["fixture_id"] for item in fixtures]
    if len(ids) != len(set(ids)):
        fail("duplicate fixture id")
    locks = {json.dumps(item["parent_lock"], sort_keys=True) for item in fixtures}
    if len(locks) != 1:
        fail("synthetic fixtures use mixed parent locks")
    identities = {
        tuple(item["repository_identity"][key] for key in ("host", "owner", "repository"))
        for item in fixtures
    }
    if len(identities) != len(fixtures):
        fail("synthetic fixture repository identities are ambiguous")
    return fixtures


def validate_protected_workflow(content: str) -> None:
    """Require an unconditional, exact gate-contract validation step."""
    lines = content.splitlines()
    marker = "- name: Gate contract and generated agreement"
    starts = [index for index, line in enumerate(lines) if line.strip() == marker]
    if len(starts) != 1:
        fail("protected validation workflow lost or duplicated gate contract step")
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip().startswith("- name:"):
            end = index
            break
    actual = [line.strip() for line in lines[start:end] if line.strip()]
    expected = [
        marker,
        "run: |",
        "python3 bin/_test/gate_contract_test.py",
        "python3 bin/gate_contract.py --check --probe --generated-root dist",
        "python3 bin/_test/effective_policy_test.py",
        "python3 bin/effective_policy.py validate --generated-root dist",
    ]
    if actual != expected:
        fail("protected validation workflow gate contract step is conditional, altered, or non-exact")


def validate_protected_adapter_workflow(content: str) -> None:
    """Require the reviewed future default-branch registration shape.

    GitHub executes pull_request_target YAML from the repository default branch.
    The sealed workflow therefore preserves the already-registered topology
    step, checks out the exact PR base as trusted policy with complete history,
    and delegates provider evaluation to that base's topology entrypoint. The
    checked-out YAML is never represented as the workflow GitHub executed.
    """
    actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if actual != PROTECTED_ADAPTER_WORKFLOW_SHA256:
        fail(
            "base-controlled protected adapter workflow bytes differ from the "
            "reviewed complete registration"
        )


def validate_generated(root: Path, generated_root: Path, contract: dict[str, Any]) -> None:
    manifest = read_json(generated_root / "craft-agent/enforcement-manifest.json")
    settings = read_json(generated_root / "craft-agent/settings-enforcement.json")
    digest = contract_digest(contract)
    if manifest.get("gate_contract_source") != CONTRACT.as_posix():
        fail("generated enforcement manifest has wrong gate contract source")
    if manifest.get("gate_contract_sha256") != digest or manifest.get("gate_contract") != contract:
        fail("generated enforcement manifest disagrees with source gate contract")
    expected = {
        "schema_version": contract["schema_version"],
        "contract_version": contract["contract_version"],
        "source": CONTRACT.as_posix(),
        "sha256": digest,
        "evidence_state": "configured",
    }
    if settings.get("_gate_contract") != expected:
        fail("generated enforcement settings metadata disagrees with source gate contract")
    expected_wrapper = [{"hooks": [{
        "type": "command",
        "command": "/path/to/hooks/resolver/ca-enforcement-gate.sh",
        "timeout": 15,
    }]}]
    if settings.get("hooks", {}).get("UserPromptSubmit") != expected_wrapper:
        fail("generated enforcement settings lost or changed the registered wrapper")
    if settings.get("env", {}).get("CLAUDE_CA_ENFORCE") != "1":
        fail("generated enforcement settings lost CLAUDE_CA_ENFORCE")
    gates = manifest.get("gates")
    if not isinstance(gates, list) or not gates:
        fail("generated enforcement manifest lost gate registrations")
    gate_ids = [gate.get("id") for gate in gates if isinstance(gate, dict)]
    if len(gate_ids) != len(set(gate_ids)):
        fail("generated enforcement manifest has duplicate gate registrations")
    branch = [gate for gate in gates if gate.get("id") == "branch-guard"]
    if len(branch) != 1 or any(branch[0].get(key) != value for key, value in {
        "hook": "hooks/git/branch-guard.sh",
        "surface": "native-git-pre-push",
        "blocking": True,
    }.items()):
        fail("generated enforcement manifest disagrees with native-branch-pre-push")

    by_id = {capability["id"]: capability for capability in contract["capabilities"]}
    packaged: dict[str, list[Path]] = {}
    for capability in contract["capabilities"]:
        for package in capability["package_paths"]:
            relative = Path(package)
            if relative.parts[:1] != ("dist",):
                fail(f"{capability['id']}: package path must begin with dist/")
            candidate = repository_path(
                generated_root, Path(*relative.parts[1:]).as_posix(),
                f"{capability['id']}.package path",
            )
            if not candidate.is_file():
                fail(f"{capability['id']}: generated package path is not a regular file: {package}")
            packaged.setdefault(capability["id"], []).append(candidate)

    ticket_capability = by_id["native-ticket-commit-msg"]
    ticket_targets = packaged.get("native-ticket-commit-msg", [])
    if len(ticket_targets) != 1:
        fail("native-ticket-commit-msg must have exactly one generated package target")
    ticket = ticket_targets[0]
    source_ticket = repository_path(root, ticket_capability["registered_path"], "native ticket declared registration")
    if ticket.read_bytes() != source_ticket.read_bytes():
        fail("packaged native-ticket-commit-msg bytes disagree with registered source")
    if not ticket.stat().st_mode & 0o111:
        fail("packaged native-ticket-commit-msg is not executable")
    run_ticket_probe(root, contract, executable_override=ticket)

    branch_capability = by_id["native-branch-pre-push"]
    branch_targets = packaged.get("native-branch-pre-push", [])
    if len(branch_targets) != 1:
        fail("native-branch-pre-push must have exactly one generated package target")
    pre_push = branch_targets[0]
    registered_branch = Path(branch_capability["registered_path"])
    if registered_branch.parts[:1] != ("dist",):
        fail("native-branch-pre-push declared registration must be generated under dist/")
    declared_pre_push = repository_path(
        generated_root, Path(*registered_branch.parts[1:]).as_posix(),
        "native branch declared registration",
    )
    if declared_pre_push != pre_push:
        fail("native-branch-pre-push declared registration disagrees with package target")
    if not pre_push.stat().st_mode & 0o111:
        fail("packaged native-branch-pre-push is not executable")
    pre_push_text = pre_push.read_text(encoding="utf-8")
    required_branch_sites = (
        "# Gate: branch-guard — Commit to protected branch",
        'GATE_SCRIPT="$HOOKS_ROOT/git/branch-guard.sh"',
        'echo "pre-push: branch-guard gate BLOCKED push" >&2',
    )
    if any(pre_push_text.count(site) != 1 for site in required_branch_sites):
        fail("packaged native-branch-pre-push lost or duplicated branch-guard registration")
    run_pre_push_probe(pre_push, contract)

    protected_capability = by_id["protected-range-validation"]
    workflow = repository_path(
        root, protected_capability["registered_path"], "protected validation declared registration"
    )
    validate_protected_adapter_workflow(workflow.read_text(encoding="utf-8"))
    # Candidate CI continues to verify source/generated agreement, but it is
    # not the protected adapter and cannot authorize its own head.
    validate_protected_workflow(
        repository_path(root, ".github/workflows/build-and-publish.yml", "contract CI workflow").read_text(encoding="utf-8")
    )


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=20)


def run_pre_push_probe(executable: Path, contract: dict[str, Any]) -> None:
    capability = next(item for item in contract["capabilities"] if item["id"] == "native-branch-pre-push")
    if not executable.is_file() or not executable.stat().st_mode & 0o111:
        fail("pre-push probe executable is missing or not executable")
    with tempfile.TemporaryDirectory(prefix="gate-contract-pre-push-") as raw:
        package = Path(raw)
        target = package / ".githooks/pre-push"
        target.parent.mkdir(parents=True)
        shutil.copy2(executable, target)
        hooks = package / "hooks/git"; hooks.mkdir(parents=True)
        for name, code in (("self-review.sh", 0), ("branch-guard.sh", 1), ("test-guard.sh", 0)):
            gate = hooks / name
            gate.write_text(f"#!/usr/bin/env bash\nexit {code}\n", encoding="utf-8")
            gate.chmod(0o755)
        denied = _run([str(target), "origin", "synthetic"], package)
        if denied.returncode not in capability["result_contract"]["deny"]:
            fail("branch-protected-update-denies failed: packaged pre-push accepted the blocking branch gate")
        (hooks / "branch-guard.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        (hooks / "branch-guard.sh").chmod(0o755)
        allowed = _run([str(target), "origin", "synthetic"], package)
        if allowed.returncode not in capability["result_contract"]["allow"]:
            fail("branch-clean-update-allows failed: packaged pre-push rejected clean gate results")


def run_ticket_probe(root: Path, contract: dict[str, Any], *, executable_override: Path | None = None) -> None:
    capability = next(item for item in contract["capabilities"] if item["id"] == "native-ticket-commit-msg")
    executable = executable_override or repository_path(root, capability["registered_path"], "ticket probe executable")
    if not executable.is_file() or not executable.stat().st_mode & 0o111:
        fail("ticket probe executable is missing or not executable")
    with tempfile.TemporaryDirectory(prefix="gate-contract-ticket-") as raw:
        repo = Path(raw)
        (repo / ".githooks").mkdir()
        (repo / "bin").mkdir()
        (repo / "catalog").mkdir()
        if executable_override is None:
            shutil.copy2(executable, repo / ".githooks/commit-msg")
            shutil.copy2(root / "bin/review-risk.py", repo / "bin/review-risk.py")
            shutil.copy2(root / "catalog/review-risk-policy.json", repo / "catalog/review-risk-policy.json")
            target = repo / ".githooks/commit-msg"
        else:
            target = executable
        for command in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "fixture@example.invalid"],
            ["git", "config", "user.name", "Synthetic Fixture"],
        ):
            result = _run(command, repo)
            if result.returncode:
                fail(f"ticket probe setup failed: {result.stderr.strip()}")
        (repo / "README.md").write_text("synthetic\n", encoding="utf-8")
        result = _run(["git", "add", "README.md"], repo)
        if result.returncode:
            fail(f"ticket probe staging failed: {result.stderr.strip()}")
        valid = repo / "valid.msg"
        invalid = repo / "invalid.msg"
        valid.write_text("Synthetic change #851\n\nReview-Tier: A\nSelf-Review: synthetic\n", encoding="utf-8")
        invalid.write_text("Synthetic change\n\nReview-Tier: A\nSelf-Review: synthetic\n", encoding="utf-8")
        valid_result = _run([str(target), str(valid)], repo)
        invalid_result = _run([str(target), str(invalid)], repo)
        allow_codes = capability["result_contract"]["allow"]
        deny_codes = capability["result_contract"]["deny"]
        if valid_result.returncode not in allow_codes:
            fail(f"ticket-valid-reference-allows failed with {valid_result.returncode}: {valid_result.stderr.strip()}")
        if invalid_result.returncode not in deny_codes:
            fail("ticket-missing-reference-denies failed: registered executable accepted or misclassified the invalid candidate")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true", help="Validate source contract and both synthetic fixtures")
    parser.add_argument("--probe", action="store_true", help="Run the native ticket allow/deny acceptance probes")
    parser.add_argument("--generated-root", type=Path, help="Validate generated manifest/settings/package agreement under this dist root")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        contract = load_contract(root)
        fixtures = load_fixtures(root, contract)
        if args.probe:
            run_ticket_probe(root, contract)
        if args.generated_root:
            validate_generated(root, args.generated_root.resolve(), contract)
        if not (args.check or args.probe or args.generated_root):
            parser.error("one of --check, --probe, or --generated-root is required")
        print(
            f"Gate contract OK: {len(contract['policy_fields'])} policy fields, "
            f"{len(contract['capabilities'])} capabilities, {len(fixtures)} fixtures, "
            f"sha256={contract_digest(contract)}"
        )
        return 0
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print(f"GATE CONTRACT ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
