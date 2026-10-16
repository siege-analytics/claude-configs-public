#!/usr/bin/env python3
"""Prepare and validate a bounded Craft/backend canary without launching it.

This tool intentionally has no session-launch, credential-read, install, publish,
or provider-mutation operation. It materializes synthetic local fixtures, validates
an approval packet, validates exported host evidence, and verifies cleanup receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
RUN_ID_RE = re.compile(r"^cc-1003-[a-z0-9-]+$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EVENTS = {
    "startup_resolver",
    "prompt_hook",
    "write_guard_allow",
    "write_guard_deny",
    "git_push_allow",
    "git_push_deny",
    "resume_context",
    "compaction_context",
    "no_op_detection",
}


class PacketError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(sys.stdin.read() if str(path) == "-" else path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise PacketError(f"expected JSON object: {path}")
    return value


def load_module(root: Path, relative: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, root / relative)
    require(spec is not None and spec.loader is not None, f"cannot load pinned module: {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(name, None)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PacketError(message)


def exact_path(value: Any, expected: Path, label: str) -> Path:
    require(isinstance(value, str), f"{label} must be a string")
    actual = Path(value)
    require(actual.is_absolute(), f"{label} must be absolute")
    require(actual == expected, f"{label} must be exactly {expected}")
    require(".." not in actual.parts, f"{label} may not contain '..'")
    return actual


def approval_subject_sha256(manifest: dict[str, Any]) -> str:
    subject = json.loads(json.dumps(manifest))
    subject.pop("operator_approval", None)
    return sha256_bytes(canonical_bytes(subject))


def validate_manifest(manifest: dict[str, Any], *, require_approval_record: bool = False) -> dict[str, Any]:
    require(manifest.get("schema_version") == SCHEMA_VERSION, "unsupported schema_version")
    run = manifest.get("run")
    require(isinstance(run, dict), "run must be an object")
    run_id = run.get("id")
    require(isinstance(run_id, str) and RUN_ID_RE.fullmatch(run_id) is not None, "invalid run.id")
    require(run.get("mode") == "sequential", "only sequential mode is supported")

    paths = manifest.get("paths")
    require(isinstance(paths, dict), "paths must be an object")
    temp_root = exact_path(paths.get("temp_root"), Path("/private/tmp") / run_id, "paths.temp_root")
    workspace_root = exact_path(
        paths.get("workspace_root"),
        Path.home() / ".craft-agent" / "workspaces" / run_id,
        "paths.workspace_root",
    )
    evidence_root = exact_path(paths.get("evidence_root"), temp_root / "evidence", "paths.evidence_root")
    source_root = exact_path(paths.get("source_root"), temp_root / "source", "paths.source_root")

    approval_recorded = manifest.get("status") == "approval-recorded"
    if require_approval_record:
        require(approval_recorded, "external operator approval has not been recorded")
    require_final_pins = require_approval_record or approval_recorded

    pins = manifest.get("pins")
    require(isinstance(pins, dict), "pins must be an object")
    for name in (
        "develop_revision",
        "source_revision",
        "provider_accepted_head",
        "provider_integration_revision",
        "native_hooks_accepted_head",
        "native_hooks_revision",
    ):
        value = pins.get(name)
        if require_final_pins or name in {"develop_revision", "source_revision"}:
            require(isinstance(value, str) and HEX40.fullmatch(value) is not None, f"pins.{name} must be a full Git SHA")
        elif value is not None:
            require(isinstance(value, str) and HEX40.fullmatch(value) is not None, f"pins.{name} must be null or a full Git SHA")
    for name in (
        "source_tree_sha256", "craft_package_canonical_sha256",
        "approval_driver_sha256", "workspace_setup_driver_sha256",
    ):
        value = pins.get(name)
        require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"pins.{name} must be SHA-256")
    for name in ("craft_package_tree_sha256", "composition_tree_sha256", "workspace_payload_tree_sha256"):
        value = pins.get(name)
        if require_final_pins:
            require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"pins.{name} must pin materialized bytes")
        elif value is not None:
            require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"pins.{name} must be null or SHA-256")
    require(pins.get("develop_revision") == pins.get("source_revision"), "source_revision must equal accepted develop_revision")
    require(
        pins.get("approval_driver_sha256") == sha256_bytes(Path(__file__).read_bytes()),
        "approval driver bytes differ from the pinned digest",
    )
    setup_driver = Path(__file__).with_name("setup-disposable-workspace.py")
    require(
        pins.get("workspace_setup_driver_sha256") == sha256_bytes(setup_driver.read_bytes()),
        "workspace setup driver bytes differ from the pinned digest",
    )

    fixture = manifest.get("fixture")
    require(isinstance(fixture, dict), "fixture must be an object")
    require(fixture.get("canonical_identity") == "github.example.invalid/synthetic-org/strict-release", "fixture canonical identity mismatch")
    require(fixture.get("project") == "strict-release", "fixture project mismatch")
    require(fixture.get("composition_layout") == "flat", "fixture composition layout must be flat")
    require(
        fixture.get("resident_marker") == "STRICT_OVERLAY: run the project regression command.",
        "fixture resident marker mismatch",
    )

    backends = manifest.get("backends")
    require(isinstance(backends, list) and len(backends) == 2, "exactly two backend runs are required")
    expected = [(1, "anthropic"), (2, "pi")]
    seen: set[tuple[str, str]] = set()
    for entry, (sequence, provider) in zip(backends, expected):
        require(isinstance(entry, dict), "backend entries must be objects")
        require(entry.get("sequence") == sequence, "backend sequence must be 1 then 2")
        require(entry.get("provider_type") == provider, f"backend {sequence} provider_type must be {provider}")
        connection = entry.get("connection")
        model = entry.get("model")
        require(isinstance(connection, str) and connection, f"backend {sequence} connection is required")
        require(isinstance(model, str) and model, f"backend {sequence} model is required")
        require((connection, model) not in seen, "backend connection/model pairs must be distinct")
        seen.add((connection, model))

    timeouts = manifest.get("timeouts_seconds")
    require(isinstance(timeouts, dict), "timeouts_seconds must be an object")
    for name in ("per_backend", "transition", "cleanup", "overall"):
        require(isinstance(timeouts.get(name), int) and 1 <= timeouts[name] <= 3600, f"invalid timeout {name}")
    require(
        timeouts["overall"] >= max(timeouts["per_backend"], timeouts["transition"], timeouts["cleanup"]),
        "overall timeout is shorter than an individual phase budget",
    )

    effects = manifest.get("allowed_side_effects")
    required_effects = {
        "create_exact_workspace",
        "write_exact_temp_root",
        "create_local_bare_remote",
        "create_disposable_git_refs",
        "deploy_pinned_source_to_exact_workspace",
        "register_hooks_in_exact_workspace_and_fixture",
        "record_host_event_metadata",
        "remove_exact_workspace",
        "remove_exact_temp_root",
    }
    require(isinstance(effects, list) and set(effects) == required_effects, "allowed_side_effects must equal the closed set")

    limits = manifest.get("limits")
    require(isinstance(limits, dict), "limits must be an object")
    for name in (
        "no_credentials_read",
        "no_main_mutation",
        "no_branch_protection_mutation",
        "no_release_or_shared_install",
        "no_external_messages",
        "no_parallel_sessions",
        "no_provider_authority_claim",
        "no_model_self_report_as_evidence",
    ):
        require(limits.get(name) is True, f"limits.{name} must be true")

    cleanup = manifest.get("cleanup")
    require(isinstance(cleanup, dict), "cleanup must be an object")
    require(isinstance(cleanup.get("owner"), str) and cleanup["owner"], "cleanup.owner is required")
    require(cleanup.get("verify_absent") == [str(workspace_root), str(temp_root)], "cleanup.verify_absent must list exact workspace then temp root")

    approval = manifest.get("operator_approval")
    require(isinstance(approval, dict), "operator_approval must be an object")
    status = manifest.get("status")
    require(status in {"proposal", "approval-recorded"}, "status must be proposal or approval-recorded")
    if status == "proposal":
        require(approval.get("state") == "not-supplied", "proposal must not claim operator approval")
        for name in ("source_kind", "source_reference", "approved_by", "approved_at", "subject_sha256"):
            require(approval.get(name) is None, f"proposal operator_approval.{name} must be null")
    else:
        require(approval.get("state") == "externally-supplied", "approval record must be externally supplied")
        require(approval.get("source_kind") in {"direct-user-instruction", "reviewed-issue-comment"}, "unsupported operator approval source")
        for name in ("source_reference", "approved_by", "approved_at"):
            require(isinstance(approval.get(name), str) and approval[name], f"operator_approval.{name} is required")
        require(approval.get("subject_sha256") == approval_subject_sha256(manifest), "operator approval subject digest mismatch")
    if require_approval_record:
        require(status == "approval-recorded", "external operator approval has not been recorded")

    return {
        "run_id": run_id,
        "temp_root": temp_root,
        "workspace_root": workspace_root,
        "evidence_root": evidence_root,
        "source_root": source_root,
        "manifest_sha256": sha256_bytes(canonical_bytes(manifest)),
        "approval_subject_sha256": approval_subject_sha256(manifest),
        "approval_evidence_state": "recorded-unverified" if status == "approval-recorded" else "not-supplied",
        "authorization_effect": "none",
    }


def run_git(args: list[str], *, cwd: Path) -> str:
    proc = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False, timeout=30)
    if proc.returncode:
        raise PacketError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def tree_digest(root: Path, *, canonical_package: bool = False) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative_text = path.relative_to(root).as_posix()
        relative = relative_text.encode()
        if path.is_symlink():
            kind, content = b"L", os.readlink(path).encode()
        elif path.is_file():
            kind, content = b"F", path.read_bytes()
            if canonical_package and relative_text in {
                "enforcement-manifest.json",
                "hooks/enforcement-manifest.json",
                "package.json",
            }:
                value = json.loads(content)
                require(isinstance(value, dict) and isinstance(value.get("built_at"), str), f"missing built_at in {relative_text}")
                value["built_at"] = "<normalized-built-at>"
                content = canonical_bytes(value)
        else:
            continue
        digest.update(kind + b"\0" + relative + b"\0" + hashlib.sha256(content).digest() + b"\0")
    return digest.hexdigest()


def materialize_source(manifest: dict[str, Any], destination: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    revision = manifest["pins"]["source_revision"]
    listing = subprocess.check_output(["git", "ls-tree", "-r", "--full-tree", revision], cwd=repo)
    require(sha256_bytes(listing) == manifest["pins"]["source_tree_sha256"], "source tree digest mismatch")
    clone = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--no-checkout", str(repo), str(destination)],
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    require(clone.returncode == 0, f"source clone failed: {clone.stderr.strip()}")
    run_git(["checkout", "--detach", revision], cwd=destination)
    require(run_git(["rev-parse", "HEAD"], cwd=destination) == revision, "materialized source revision mismatch")
    build = subprocess.run(
        [sys.executable, "bin/build.py"],
        cwd=destination,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    require(build.returncode == 0, f"pinned source build failed: {build.stderr.strip()}")
    package = destination / "dist" / "craft-agent"
    require(package.is_dir(), "pinned build lacks dist/craft-agent")
    require(tree_digest(package, canonical_package=True) == manifest["pins"]["craft_package_canonical_sha256"], "canonical Craft package digest mismatch")
    exact_digest = tree_digest(package)
    pinned_exact = manifest["pins"].get("craft_package_tree_sha256")
    if pinned_exact is not None:
        require(exact_digest == pinned_exact, "exact Craft package tree digest mismatch")
    require(run_git(["status", "--porcelain", "--untracked-files=no"], cwd=destination) == "", "pinned build changed tracked source")


def copy_workspace_tree(source: Path, destination: Path, strip_markdown: Any | None = None) -> None:
    require(source.is_dir(), f"workspace payload source is absent: {source}")
    for item in sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix()):
        relative = item.relative_to(source)
        target = destination / relative
        require(not item.is_symlink(), f"workspace payload source may not contain symlinks: {item}")
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            if strip_markdown is not None and item.suffix.lower() == ".md":
                target.write_text(strip_markdown(item.read_text()))
            else:
                shutil.copy2(item, target)


def prepare_composition_and_payload(manifest: dict[str, Any], source: Path, root: Path) -> dict[str, Any]:
    fixture = manifest["fixture"]
    composition = root / "composition"
    proc = subprocess.run(
        [sys.executable, "bin/compose-project.py", "--identity", fixture["canonical_identity"], "--output", str(composition)],
        cwd=source,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    require(proc.returncode == 0, f"strict-release composition failed: {proc.stderr.strip()}")
    flat = composition / fixture["composition_layout"]
    required = {
        "composition.json", "skills/RESIDENT.md", "skills/RULES_BUNDLE.md",
        "skills/_strict-release--rules.md", "skills/strict-release--review/SKILL.md",
        "skills/strict-release--review/references/steps.md", "skills/strict-release--checks/SKILL.md",
        "bin/procedure_composition.py", "bin/resolve-load-set.py",
        "catalog/resolver-manifest.json", "catalog/skills-inventory.json",
    }
    require(all((flat / relative).is_file() for relative in required), "strict-release composition is incomplete")
    receipt = json.loads((flat / "composition.json").read_text())
    require(receipt.get("identity") == fixture["canonical_identity"], "composition identity mismatch")
    require(receipt.get("project") == fixture["project"], "composition project mismatch")
    require(fixture["resident_marker"] in (flat / "skills/RESIDENT.md").read_text(), "strict-release resident marker is absent")

    payload = root / "workspace-payload"
    payload.mkdir()
    build_module = load_module(source, Path("bin/build.py"), "canary_pinned_build")
    strip_markdown = build_module.strip_craft_incompatible_keys
    copy_workspace_tree(source / "dist/flat/skills", payload / "skills", strip_markdown)
    copy_workspace_tree(source / "dist/flat/hooks", payload / "hooks")
    copy_workspace_tree(flat, payload, strip_markdown)
    for source_path, target_path in (
        (source / "RESOLVER.md", payload / "RESOLVER.md"),
        (source / "dist/RULES_BUNDLE.md", payload / "RULES_BUNDLE.md"),
        (source / "dist/flat/skills/KERNEL.md", payload / "KERNEL.md"),
        (source / "dist/craft-agent/enforcement-manifest.json", payload / "enforcement-manifest.json"),
    ):
        require(source_path.is_file() and not source_path.is_symlink(), f"workspace payload input is absent: {source_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.suffix.lower() == ".md":
            target_path.write_text(strip_markdown(source_path.read_text()))
        else:
            shutil.copy2(source_path, target_path)
    for relative in (
        ".githooks", "bin", "catalog",
    ):
        package_path = source / "dist/craft-agent" / relative
        if package_path.is_dir():
            copy_workspace_tree(package_path, payload / relative)
    (payload / "CLAUDE.md").symlink_to("KERNEL.md")
    require(not (payload / "deploy-stamp.json").exists(), "disposable payload must not contain a production deploy stamp")
    return {
        "composition_root": str(flat),
        "composition_tree_sha256": tree_digest(flat),
        "workspace_payload_root": str(payload),
        "workspace_payload_tree_sha256": tree_digest(payload),
    }


def fixture_commit_message(subject: str) -> str:
    return (
        f"{subject} (#1003)\n\n"
        "Review-Tier: A\n"
        "Self-Review: disposable canary fixture only"
    )


def materialize(manifest: dict[str, Any]) -> dict[str, Any]:
    facts = validate_manifest(manifest)
    root: Path = facts["temp_root"]
    require(not root.exists(), f"refusing existing temp root: {root}")
    require(not facts["workspace_root"].exists(), "refusing because exact disposable workspace already exists")
    fixture = root / "fixture"
    evidence = facts["evidence_root"]
    repo = fixture / "repo"
    remote = fixture / "remote.git"
    for path in (fixture, evidence, facts["source_root"], repo):
        path.mkdir(parents=True, exist_ok=True)
    materialize_source(manifest, facts["source_root"])
    payload_observation = prepare_composition_and_payload(manifest, facts["source_root"], root)
    control = root / "control"
    control.mkdir()
    (control / "FOREIGN_PROJECT_MARKER.txt").write_text("FOREIGN_PROJECT_CONTROL_MUST_NOT_BE_INJECTED\n")
    (control / "GLOBAL_BUNDLE_MARKER.txt").write_text("GLOBAL_BUNDLE_CONTROL_MUST_NOT_BE_INJECTED\n")
    run_git(["init", "--bare", str(remote)], cwd=fixture)
    run_git(["init", "-b", "main"], cwd=repo)
    run_git(["config", "user.name", "Canary Fixture"], cwd=repo)
    run_git(["config", "user.email", "canary@example.invalid"], cwd=repo)
    (repo / "CONTROL.md").write_text("baseline\n")
    run_git(["add", "CONTROL.md"], cwd=repo)
    run_git(["commit", "-m", fixture_commit_message("test: seed canary fixture")], cwd=repo)
    canonical_remote = "https://" + manifest["fixture"]["canonical_identity"] + ".git"
    run_git(["config", f"url.{remote.as_uri()}.insteadOf", canonical_remote], cwd=repo)
    run_git(["remote", "add", "origin", canonical_remote], cwd=repo)
    run_git(["push", "-u", "origin", "main"], cwd=repo)
    run_git(["checkout", "-b", "canary/1003-observation"], cwd=repo)
    (repo / "PROMPT_MARKER.txt").write_text("prompt-marker-not-observed\n")
    (repo / "WRITE_MARKER.txt").write_text("write-marker-not-observed\n")
    (repo / "COMPACTION_MARKER.txt").write_text("compaction-marker-not-observed\n")
    run_git(["add", "."], cwd=repo)
    run_git(["commit", "-m", fixture_commit_message("test: add synthetic canary markers")], cwd=repo)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": facts["run_id"],
        "manifest_sha256": facts["manifest_sha256"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "paths": {
            "fixture_repo": str(repo),
            "bare_remote": str(remote),
            "evidence_root": str(evidence),
            "source_root": str(facts["source_root"]),
            "composition_root": payload_observation["composition_root"],
            "workspace_payload_root": payload_observation["workspace_payload_root"],
            "control_root": str(control),
        },
        "pins": manifest["pins"],
        "package_observation": {
            "canonical_sha256": tree_digest(facts["source_root"] / "dist" / "craft-agent", canonical_package=True),
            "exact_tree_sha256": tree_digest(facts["source_root"] / "dist" / "craft-agent"),
            "composition_tree_sha256": payload_observation["composition_tree_sha256"],
            "workspace_payload_tree_sha256": payload_observation["workspace_payload_tree_sha256"],
        },
        "fixture": {
            **manifest["fixture"],
            "origin": canonical_remote,
            "transport": "strictly-local-insteadOf",
            "foreign_control_sha256": sha256_bytes((control / "FOREIGN_PROJECT_MARKER.txt").read_bytes()),
            "global_bundle_control_sha256": sha256_bytes((control / "GLOBAL_BUNDLE_MARKER.txt").read_bytes()),
        },
        "git": {
            "main": run_git(["rev-parse", "main"], cwd=repo),
            "candidate": run_git(["rev-parse", "HEAD"], cwd=repo),
            "remote_main": run_git(["--git-dir", str(remote), "rev-parse", "refs/heads/main"], cwd=fixture),
        },
        "workspace_preexisting": False,
        "live_session_created": False,
        "credentials_read": False,
    }
    out = root / "materialization.json"
    out.write_bytes(canonical_bytes(receipt))
    return {"receipt": str(out), "receipt_sha256": sha256_bytes(out.read_bytes())}


def attest_materialized(manifest: dict[str, Any]) -> dict[str, Any]:
    facts = validate_manifest(manifest, require_approval_record=True)
    source: Path = facts["source_root"]
    package = source / "dist" / "craft-agent"
    require(source.is_dir() and package.is_dir(), "materialized source/package is absent")
    require(run_git(["rev-parse", "HEAD"], cwd=source) == manifest["pins"]["source_revision"], "materialized source revision mismatch")
    require(run_git(["status", "--porcelain", "--untracked-files=no"], cwd=source) == "", "materialized source has tracked drift")
    require(tree_digest(package, canonical_package=True) == manifest["pins"]["craft_package_canonical_sha256"], "materialized canonical package mismatch")
    require(tree_digest(package) == manifest["pins"]["craft_package_tree_sha256"], "materialized exact package mismatch")
    composition = facts["temp_root"] / "composition" / manifest["fixture"]["composition_layout"]
    payload = facts["temp_root"] / "workspace-payload"
    require(tree_digest(composition) == manifest["pins"]["composition_tree_sha256"], "materialized composition tree mismatch")
    require(tree_digest(payload) == manifest["pins"]["workspace_payload_tree_sha256"], "materialized workspace payload mismatch")
    require(not (payload / "deploy-stamp.json").exists(), "disposable payload contains a production deploy stamp")
    composition_receipt = json.loads((composition / "composition.json").read_text())
    require(composition_receipt.get("identity") == manifest["fixture"]["canonical_identity"], "materialized composition identity mismatch")
    require(composition_receipt.get("project") == manifest["fixture"]["project"], "materialized composition project mismatch")
    require(manifest["fixture"]["resident_marker"] in (composition / "skills/RESIDENT.md").read_text(), "materialized resident marker mismatch")
    fixture_repo = facts["temp_root"] / "fixture" / "repo"
    require((facts["temp_root"] / "fixture" / "remote.git").is_dir(), "synthetic bare remote is absent")
    expected_origin = "https://" + manifest["fixture"]["canonical_identity"] + ".git"
    require(run_git(["config", "--get", "remote.origin.url"], cwd=fixture_repo) == expected_origin, "fixture origin identity mismatch")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "run_id": facts["run_id"],
        "manifest_sha256": facts["manifest_sha256"],
        "source_revision": manifest["pins"]["source_revision"],
        "package_tree_sha256": manifest["pins"]["craft_package_tree_sha256"],
        "composition_tree_sha256": manifest["pins"]["composition_tree_sha256"],
        "workspace_payload_tree_sha256": manifest["pins"]["workspace_payload_tree_sha256"],
        "fixture_identity": manifest["fixture"]["canonical_identity"],
        "live_session_created": False,
    }
    output = facts["evidence_root"] / "authorization-attestation.json"
    output.write_bytes(canonical_bytes(receipt))
    return {
        "status": "materialization-consistent-unverified",
        "authorization_effect": "none",
        "receipt": str(output),
        "receipt_sha256": sha256_bytes(output.read_bytes()),
    }


def evidence_timestamp(value: Any, label: str) -> datetime:
    require(isinstance(value, str) and value, f"{label} must be an ISO-8601 timestamp")
    try:
        observed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PacketError(f"{label} must be an ISO-8601 timestamp") from exc
    require(observed.tzinfo is not None and observed.utcoffset() is not None, f"{label} must include a UTC offset")
    return observed


def validate_evidence(manifest: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    facts = validate_manifest(manifest, require_approval_record=True)
    require(evidence.get("schema_version") == SCHEMA_VERSION, "unsupported evidence schema")
    require(evidence.get("run_id") == facts["run_id"], "evidence run_id mismatch")
    require(evidence.get("manifest_sha256") == facts["manifest_sha256"], "evidence manifest digest mismatch")
    runs = evidence.get("backend_runs")
    require(isinstance(runs, list) and len(runs) == 2, "exactly two backend evidence records required")
    timeouts = manifest["timeouts_seconds"]
    first_start: datetime | None = None
    prior_end: datetime | None = None
    backend_durations: list[float] = []
    transition_durations: list[float] = []
    validated_events = 0
    artifact_references: set[str] = set()
    evidence_root: Path = facts["evidence_root"]
    require(evidence_root.is_dir() and not evidence_root.is_symlink(), "evidence root is absent or symlinked")
    require(evidence_root.resolve() == evidence_root, "evidence root must resolve to its exact approved path")
    for expected, observed in zip(manifest["backends"], runs):
        require(isinstance(observed, dict), "backend evidence must be objects")
        sequence = expected["sequence"]
        for name in ("sequence", "connection", "model"):
            require(observed.get(name) == expected[name], f"backend evidence {name} mismatch")
        outcome = observed.get("outcome")
        if outcome == "unsupported-unverified":
            raise PacketError(f"backend {sequence} capability evidence is unsupported/unverified")
        require(outcome == "observed", "backend outcome must be observed or explicitly unsupported-unverified")
        require(observed.get("model_self_report_used") is False, "model self-report cannot be evidence")
        start = evidence_timestamp(observed.get("started_at"), f"backend {sequence} started_at")
        end = evidence_timestamp(observed.get("ended_at"), f"backend {sequence} ended_at")
        require(start < end, f"backend {sequence} interval must have positive duration")
        duration = (end - start).total_seconds()
        require(duration <= timeouts["per_backend"], f"backend {sequence} exceeds per_backend time budget")
        backend_durations.append(duration)
        if first_start is None:
            first_start = start
        if prior_end is not None:
            require(start >= prior_end, "backend runs overlap; sequential evidence required")
            transition = (start - prior_end).total_seconds()
            require(transition <= timeouts["transition"], "backend transition exceeds transition time budget")
            transition_durations.append(transition)
        prior_end = end
        events = observed.get("host_events")
        require(isinstance(events, list), "host_events must be a list")
        require(len(events) == len(EVENTS), f"backend {sequence} must contain exactly {len(EVENTS)} host events")
        require(all(isinstance(event, dict) for event in events), "every host event must be an object")
        event_names = [event.get("name") for event in events]
        require(all(isinstance(name, str) and name for name in event_names), "every host event name must be a non-empty string")
        require(len(set(event_names)) == len(event_names), f"backend {sequence} contains duplicate host event names")
        names = set(event_names)
        require(names == EVENTS, f"host event set mismatch: missing={sorted(EVENTS - names)} unexpected={sorted(names - EVENTS)}")
        for event in events:
            require(event.get("source") == "host-observed", "every event must be host-observed")
            reference = event.get("artifact_reference")
            require(isinstance(reference, str) and reference, "event artifact reference required")
            relative = Path(reference)
            require(not relative.is_absolute() and ".." not in relative.parts, "event artifact reference must be confined and relative")
            require(reference not in artifact_references, "event artifact references must be unique")
            artifact_references.add(reference)
            artifact = evidence_root / relative
            require(artifact.is_file() and not artifact.is_symlink(), f"event artifact is absent or symlinked: {reference}")
            require(artifact.resolve() == artifact, f"event artifact traverses a symlink: {reference}")
            digest = event.get("artifact_sha256")
            require(isinstance(digest, str) and HEX64.fullmatch(digest), "event artifact digest required")
            require(sha256_bytes(artifact.read_bytes()) == digest, f"event artifact digest mismatch: {reference}")
        validated_events += len(events)
    require(first_start is not None and prior_end is not None, "backend timing evidence is absent")
    overall_duration = (prior_end - first_start).total_seconds()
    require(overall_duration <= timeouts["overall"], "backend evidence exceeds overall time budget")
    observations = evidence.get("side_effect_observations")
    require(isinstance(observations, dict), "side_effect_observations must be an object")
    for name in ("outside_allowlist_unchanged", "credentials_unread", "main_unchanged", "protections_unchanged", "release_state_unchanged"):
        require(observations.get(name) is True, f"side effect observation {name} must be true")
    provenance = evidence.get("provenance")
    require(isinstance(provenance, dict), "evidence provenance is required")
    require(provenance.get("kind") == "external-host-export", "synthetic/import relabeling cannot establish host evidence")
    require(isinstance(provenance.get("reference"), str) and provenance["reference"], "host export reference is required")
    return {
        "status": "evidence-consistent-unverified",
        "authorization_effect": "none",
        "run_id": facts["run_id"],
        "backend_runs": len(runs),
        "events": validated_events,
        "timing_seconds": {
            "backend_runs": backend_durations,
            "transitions": transition_durations,
            "overall": overall_duration,
        },
    }


def verify_cleanup(manifest: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    facts = validate_manifest(manifest, require_approval_record=True)
    require(receipt.get("schema_version") == SCHEMA_VERSION, "unsupported cleanup schema")
    require(receipt.get("run_id") == facts["run_id"], "cleanup run_id mismatch")
    require(receipt.get("manifest_sha256") == facts["manifest_sha256"], "cleanup manifest digest mismatch")
    require(receipt.get("workspace_absent") is True, "workspace residue remains")
    require(receipt.get("temp_root_absent") is True, "temp-root residue remains")
    require(receipt.get("disposable_refs_absent") is True, "disposable Git refs remain")
    require(receipt.get("outside_allowlist_unchanged") is True, "outside-allowlist state changed")
    require(not facts["workspace_root"].exists(), "workspace still exists on disk")
    require(not facts["temp_root"].exists(), "temp root still exists on disk")
    return {
        "status": "local-cleanup-absence-observed",
        "imported_receipt_state": "consistent-unverified",
        "authorization_effect": "none",
        "run_id": facts["run_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="validate a proposal or non-authorizing external approval record")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--require-approval-record", action="store_true")
    prepare = sub.add_parser("materialize", help="create synthetic local fixtures only")
    prepare.add_argument("--manifest", type=Path, required=True)
    attest = sub.add_parser("attest-materialized", help="bind an external approval record to existing exact fixture bytes without granting authority")
    attest.add_argument("--manifest", type=Path, required=True)
    evidence = sub.add_parser("validate-evidence", help="validate exported host evidence")
    evidence.add_argument("--manifest", type=Path, required=True)
    evidence.add_argument("--evidence", type=Path, required=True)
    cleanup = sub.add_parser("verify-cleanup", help="verify a cleanup receipt and exact path absence")
    cleanup.add_argument("--manifest", type=Path, required=True)
    cleanup.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = load_json(args.manifest)
        if args.command == "validate":
            facts = validate_manifest(manifest, require_approval_record=args.require_approval_record)
            result = {"status": "manifest-valid", **{k: str(v) for k, v in facts.items()}}
        elif args.command == "materialize":
            result = materialize(manifest)
        elif args.command == "attest-materialized":
            result = attest_materialized(manifest)
        elif args.command == "validate-evidence":
            result = validate_evidence(manifest, load_json(args.evidence))
        else:
            result = verify_cleanup(manifest, load_json(args.receipt))
    except (PacketError, ValueError, TypeError) as exc:
        print(f"CANARY PACKET ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
