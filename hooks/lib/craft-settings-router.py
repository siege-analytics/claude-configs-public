#!/usr/bin/env python3
# Managed bootstrap: siege-craft-settings-router/v1
"""Host-scoped SDK bootstrap; workspace craft-settings.json is the sole policy.

This file is copied unchanged outside project discovery. It uses only stdlib,
never logs prompt payloads, and does nothing for a native CLI without Craft's
session binding. Real callback delivery remains a separately measured property.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time

EVENTS = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure")
RUNNING_ROUTER_PATH = Path(__file__).resolve()
LIMIT = 1024 * 1024
TOTAL_SECONDS = 90
APP_EXECUTABLE = "/Applications/Craft Agents.app/Contents/MacOS/Craft Agents"


class RoutingError(ValueError):
    pass


def regular_bytes(path: Path, *, header=False) -> bytes:
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise RoutingError("registration/session paths must be physical, without aliases")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(fd, "rb") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not header and info.st_size > LIMIT:
            raise RoutingError("registration/session metadata must be bounded regular singly linked files")
        data = source.readline(LIMIT + 1) if header else source.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise RoutingError("registration/session metadata exceeds its size limit")
    return data


def object_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise RoutingError("duplicate JSON fields are ambiguous")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(RoutingError("non-finite JSON")))
    if not isinstance(value, dict):
        raise RoutingError("expected one JSON object")
    return value


def craft_ancestry() -> bool:
    """Same bounded OS observation boundary as ca-enforcement-gate.sh."""
    observed = subprocess.run(["/bin/ps", "-ax", "-o", "pid=,ppid=,comm="],
                              text=True, capture_output=True, check=True, timeout=2)
    parents = {}
    for line in observed.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            parents[int(parts[0])] = (int(parts[1]), parts[2])
    pid, visited = os.getppid(), set()
    for _ in range(24):
        if pid <= 1:
            return False
        if pid in visited or pid not in parents:
            raise RoutingError("Craft ancestry could not be established")
        visited.add(pid)
        parent, executable = parents[pid]
        if executable == APP_EXECUTABLE:
            return True
        pid = parent
    raise RoutingError("Craft ancestry inspection exceeded its bound")


def router_path(home: Path, workspace: Path) -> Path:
    return home / ".claude/hooks/siege-craft-router" / (hashlib.sha256(str(workspace).encode()).hexdigest() + ".py")


BOOTSTRAP_TAG = "siege-craft-router-bootstrap/v1"
BOOTSTRAP_SHELL = ('if [ -z "${CRAFT_SESSION_DIR-}${CRAFT_AGENT_WORKSPACE-}" ]; then exit 0; fi; '
                   'if [ ! -f "$1" ]; then printf "%s\\n" "Craft hook router missing; repair exact-main registration." >&2; exit 2; fi; '
                   'python3 -I -B "$1" --workspace "$2" --event "$3"; '
                   'status=$?; if [ "$status" -ne 0 ]; then exit 2; fi; exit 0')


def command_for(router: Path, workspace: Path, event: str) -> str:
    import shlex
    return shlex.join(["/bin/sh", "-c", BOOTSTRAP_SHELL, BOOTSTRAP_TAG, str(router), str(workspace), event])


def own_registration(command, router: Path, workspace: Path):
    # Exact canonical text protects the shell program and argument quoting too.
    # Token equality alone cannot distinguish shell expansion before /bin/sh -c.
    return next((event for event in EVENTS if command == command_for(router, workspace, event)), None)


def legacy_own_registration(command, router: Path, workspace: Path):
    """Recognize only our previous canonical direct entry for safe migration."""
    import shlex
    return next((event for event in EVENTS if command == shlex.join(
        ["python3", "-I", "-B", str(router), "--workspace", str(workspace), "--event", event])), None)


def workspace_policy_commands(policy: dict, workspace: Path) -> set[str]:
    """Exact policy commands owned by this physical workspace hooks tree."""
    import shlex
    found = set()
    for groups in policy.get("hooks", {}).values():
        if not isinstance(groups, list):
            raise RoutingError("policy hook events are malformed")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise RoutingError("policy hook groups are malformed")
            for hook in group["hooks"]:
                if not isinstance(hook, dict) or hook.get("type") != "command":
                    raise RoutingError("the scoped router supports synchronous command policy only")
                command = hook.get("command")
                if not isinstance(command, str):
                    raise RoutingError("policy command must be a string")
                tokens = shlex.split(command)
                candidate = tokens[1] if len(tokens) >= 2 and tokens[0] in {"bash", "/bin/bash", "sh", "/bin/sh", "python3"} else tokens[0] if tokens else ""
                path = Path(candidate)
                try:
                    path.relative_to(workspace / "hooks")
                except ValueError:
                    continue  # An operator hook is not ours to retire elsewhere.
                if path.is_absolute() and path.resolve() == path:
                    found.add(command)
    return found


def verify_global(settings: dict, router: Path, workspace: Path, *, policy: dict | None = None):
    environment = settings.get("env", {})
    if isinstance(environment, dict) and environment.get("CLAUDE_CA_ENFORCE") == "1":
        raise RoutingError("global CLAUDE_CA_ENFORCE=1 leaks Craft policy into native CLI; remove that exact legacy flag from native CLI settings before registration")
    if settings.get("disableAllHooks") is True:
        raise RoutingError("global disableAllHooks prevents registered callback delivery; operator must resolve it")
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        raise RoutingError("global bootstrap registrations are missing")
    policy_commands = workspace_policy_commands(policy, workspace) if policy is not None else set()
    counts = {event: 0 for event in EVENTS}
    for event, groups in hooks.items():
        if not isinstance(groups, list):
            raise RoutingError("global hook event must be an array")
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
                raise RoutingError("global hook registration is malformed")
            for hook in group["hooks"]:
                if not isinstance(hook, dict):
                    raise RoutingError("global hook registration is malformed")
                if hook.get("command") in policy_commands:
                    raise RoutingError("workspace policy command is registered directly in global hooks; operator must remove the duplicate")
                if legacy_own_registration(hook.get("command"), router, workspace):
                    raise RoutingError("legacy direct router registration must be migrated before use")
                owned = own_registration(hook.get("command"), router, workspace)
                if owned:
                    if (owned != event or hook.get("type") != "command" or hook.get("async", False) is not False
                            or hook.get("timeout") != 120 or event == "UserPromptSubmit" and "matcher" in group
                            or event != "UserPromptSubmit" and group.get("matcher") != ".*"):
                        raise RoutingError("global bootstrap event/matcher is incorrect")
                    counts[event] += 1
    if any(count != 1 for count in counts.values()):
        raise RoutingError("global bootstrap requires exactly one owned registration per event")


def registration(workspace: Path, *, router_path_override=None) -> tuple[dict, dict]:
    receipt = object_json(regular_bytes(workspace / ".claude/craft-hook-registration.json"))
    policy = workspace / ".claude/craft-settings.json"
    router = router_path_override or RUNNING_ROUTER_PATH
    global_settings = router.parents[2] / "settings.json"
    if router.parent.name != "siege-craft-router" or router.name != hashlib.sha256(str(workspace).encode()).hexdigest() + ".py":
        raise RoutingError("router copy does not match the enrolled workspace")
    anchor = workspace / "hooks/lib/session_anchor.py"
    if (receipt.get("schema_version") != 1 or receipt.get("state") != "active" or receipt.get("workspace") != str(workspace)
            or receipt.get("policy_path") != str(policy) or receipt.get("router_path") != str(router)
            or receipt.get("global_settings_path") != str(global_settings)
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", str(receipt.get("source_revision", "")))):
        raise RoutingError("Craft hook registration receipt is missing, corrupt or bound elsewhere")
    for key, path in (("router_sha256", router), ("policy_sha256", policy), ("session_anchor_sha256", anchor), ("read_classifier_sha256", workspace / "hooks/lib/read-only-command.py"), ("task_resolver_sha256", workspace / "hooks/lib/resolve-think-gate.py"), ("hook_payload_sha256", workspace / "hooks/lib/hook_payload.py"), ("task_actions_sha256", workspace / "hooks/lib/task_actions.py")):
        if receipt.get(key) != hashlib.sha256(regular_bytes(path)).hexdigest():
            raise RoutingError("Craft hook generation changed; rerun exact-main registration")
    parsed_policy = object_json(regular_bytes(policy))
    verify_global(object_json(regular_bytes(global_settings)), router, workspace, policy=parsed_policy)
    return receipt, parsed_policy


def metadata_environment(payload: dict, helper_path=None) -> str:
    """Use the one serializer; global copies import only a verified workspace helper."""
    helper = helper_path or Path(__file__).with_name('hook_payload.py')
    spec = importlib.util.spec_from_file_location('siege_hook_payload', helper)
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    try:
        return module.metadata_environment(payload)
    except (ValueError, TypeError) as error:
        raise RoutingError(str(error)) from error


def session_context(raw: bytes, event: str, environment: dict):
    payload = object_json(raw)
    if payload.get("hook_event_name") != event:
        raise RoutingError("SDK event does not match the registered bootstrap event")
    original = Path(environment["CRAFT_SESSION_DIR"])
    if not original.is_absolute() or original.resolve(strict=True) != original or original.parent.name != "sessions":
        raise RoutingError("Craft requires an absolute physical session directory")
    workspace = original.parent.parent
    receipt, policy = registration(workspace)
    helper = workspace / "hooks/lib/session_anchor.py"
    spec = importlib.util.spec_from_file_location("siege_verified_session_anchor", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sdk_id = module.payload_uuid(payload)
    if not sdk_id:
        raise RoutingError("SDK session identity is missing")
    corrected = module.registered_session_dir(str(workspace), str(original), payload)
    child_environment = dict(environment)
    policy_environment = policy.get("env", {})
    if not isinstance(policy_environment, dict) or any(not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key)
            or not isinstance(value, str) or "\0" in value for key, value in policy_environment.items()):
        raise RoutingError("workspace hook environment must contain literal string values")
    child_environment.update(policy_environment)
    # Identity is sealed AFTER policy env: configuration cannot borrow another
    # session/task or redirect discovery away from this enrolled workspace.
    for name in ("CRAFT_SESSION_DIR", "CRAFT_AGENT_SESSION_DIR", "CRAFT_SESSION_ID", "CRAFT_AGENT_SESSION_ID",
                 "CLAUDE_SESSION_DIR", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID", "SESSION_ID",
                 "CLAUDE_SIGNAL_DIR", "CRAFT_SIGNAL_DIR", "CRAFT_AGENT_SIGNAL_DIR", "CCP_TASK_ID"):
        child_environment.pop(name, None)
    child_environment.update(CRAFT_AGENT_WORKSPACE=str(workspace), CCP_HOOK_INPUT_JSON=metadata_environment(payload, workspace / "hooks/lib/hook_payload.py"),
                             CCP_CRAFT_ROUTER_SOURCE_REVISION=receipt["source_revision"],
                             CCP_CRAFT_ROUTER_POLICY_SHA256=receipt["policy_sha256"],
                             CCP_CRAFT_ROUTER_SHA256=receipt["router_sha256"])
    child_environment.pop("CCP_CRAFT_ROUTER_SESSION_UNRESOLVED", None)
    child_environment.pop("CCP_CRAFT_ROUTER_BOUND_SDK_ID", None)
    if corrected:
        child_environment["CCP_CRAFT_ROUTER_BOUND_SDK_ID"] = sdk_id
        child_environment["CRAFT_SESSION_DIR"] = corrected
        if environment.get("CCP_TASK_ID"):
            child_environment["CCP_TASK_ID"] = environment["CCP_TASK_ID"]
    return policy, child_environment, bool(corrected)


def matching_hooks(policy: dict, event: str, payload: dict) -> list[tuple[str, float]]:
    events = policy.get("hooks")
    if not isinstance(events, dict):
        raise RoutingError("workspace policy has no hook events")
    groups = events.get(event, [])
    if not isinstance(groups, list):
        raise RoutingError("workspace event must be an array")
    tool = payload.get("tool_name")
    if event != "UserPromptSubmit" and (not isinstance(tool, str) or not tool):
        raise RoutingError("SDK tool name is missing")
    found = {}
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("hooks"), list):
            raise RoutingError("workspace hook group is malformed")
        matcher = group.get("matcher", ".*")
        if not isinstance(matcher, str):
            raise RoutingError("workspace matcher must be a regex")
        if event != "UserPromptSubmit" and re.fullmatch(matcher, tool) is None:
            continue
        for hook in group["hooks"]:
            if not isinstance(hook, dict) or hook.get("type") != "command":
                raise RoutingError("only synchronous command hooks are supported by this router")
            command, timeout = hook.get("command"), hook.get("timeout", 10)
            if not isinstance(command, str) or not command.strip() or type(timeout) not in (int, float) or not 0 < timeout <= 120:
                raise RoutingError("workspace hook command/timeout is invalid")
            if command in found and found[command] != timeout:
                raise RoutingError("duplicate hook commands have conflicting timeouts")
            found[command] = timeout
    return list(found.items())


def execute_hook(command: str, raw: bytes, environment: dict, budget: float):
    process = subprocess.Popen(command, shell=True, executable="/bin/bash", stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
                               cwd=os.getcwd(), start_new_session=True)
    selector = selectors.DefaultSelector()
    chunks = {"stdout": bytearray(), "stderr": bytearray()}
    deadline = time.monotonic() + budget
    completed = False
    try:
        os.set_blocking(process.stdin.fileno(), False)
        selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
        offset = 0
        for pipe, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
            selector.register(pipe, selectors.EVENT_READ, name)
        while selector.get_map():
            if time.monotonic() >= deadline:
                raise RoutingError("workspace hook timed out")
            for key, _ in selector.select(min(0.1, max(0, deadline - time.monotonic()))):
                if key.data == "stdin":
                    try:
                        offset += os.write(key.fileobj.fileno(), raw[offset:offset + 8192])
                    except BrokenPipeError:
                        offset = len(raw)
                    if offset == len(raw):
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                    continue
                data = os.read(key.fileobj.fileno(), 8192)
                if not data:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                chunks[key.data].extend(data)
                if len(chunks[key.data]) > LIMIT:
                    raise RoutingError("workspace hook output exceeded its bound")
        result = process.wait(timeout=max(0.01, deadline - time.monotonic()))
        completed = True
        return result, chunks["stdout"].decode("utf-8", "replace"), chunks["stderr"].decode("utf-8", "replace")
    finally:
        selector.close()
        if not completed or process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        for pipe in (process.stdin, process.stdout, process.stderr):
            if pipe and not pipe.closed:
                pipe.close()


def add_text(target: dict, key: str, value):
    if not isinstance(value, str):
        raise RoutingError("SDK context/reason fields must be strings")
    if value and value not in target.setdefault(key, []):
        target[key].append(value)


def aggregate(event: str, outputs: list[tuple[int, str, str]]) -> tuple[int, dict, str]:
    result, specific, texts, specific_texts, errors = {}, {"hookEventName": event}, {}, {}, []
    blocked = False
    allowed_top = {"continue", "suppressOutput", "stopReason", "decision", "systemMessage", "reason", "hookSpecificOutput"}
    specific_keys = {"hookEventName", "additionalContext"}
    if event == "PreToolUse":
        specific_keys |= {"permissionDecision", "permissionDecisionReason", "updatedInput"}
    if event == "PostToolUse":
        specific_keys |= {"updatedToolOutput", "updatedMCPToolOutput", "classifierContext"}
    if event == "UserPromptSubmit":
        specific_keys |= {"sessionTitle", "suppressOriginalPrompt"}
    for code, stdout, stderr in outputs:
        if stderr.strip() and stderr.strip() not in errors:
            errors.append(stderr.strip())
        if code:
            blocked = True
            if code != 2:
                errors.append("Workspace hook execution failed; repair the registered policy before retrying.")
        stripped = stdout.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            # Native command hooks also return plain context containing code
            # examples. Only a whole JSON object is an SDK control response;
            # text quoting JSON must never become permission/control authority.
            add_text(specific_texts, "additionalContext", stripped)
            continue
        value = object_json(stripped.encode())
        if set(value) - allowed_top:
            raise RoutingError("workspace hook returned unsupported SDK fields")
        for key, item in value.items():
            if key == "hookSpecificOutput":
                if not isinstance(item, dict) or set(item) - specific_keys or item.get("hookEventName") != event:
                    raise RoutingError("workspace hook returned conflicting/unsupported event output")
                for name, field in item.items():
                    if name == "hookEventName":
                        continue
                    if name in {"additionalContext", "permissionDecisionReason"}:
                        add_text(specific_texts, name, field)
                    else:
                        if name == "permissionDecision" and (not isinstance(field, str) or field not in {"allow", "ask", "deny"}):
                            raise RoutingError("unsupported SDK permission decision")
                        if name in {"sessionTitle", "classifierContext"} and not isinstance(field, str):
                            raise RoutingError("SDK text field must be a string")
                        if name == "suppressOriginalPrompt" and type(field) is not bool:
                            raise RoutingError("SDK suppressOriginalPrompt must be boolean")
                        if name == "updatedInput" and not isinstance(field, dict):
                            raise RoutingError("SDK input update must be an object")
                        if name in specific and specific[name] != field:
                            raise RoutingError("workspace hooks returned conflicting SDK decisions/input updates")
                        specific[name] = field
            elif key in {"stopReason", "systemMessage", "reason"}:
                add_text(texts, key, item)
            elif key == "continue":
                if type(item) is not bool:
                    raise RoutingError("SDK continue field must be boolean")
                result[key] = result.get(key, True) and item
            else:
                if key == "decision" and (not isinstance(item, str) or item not in {"approve", "block"}):
                    raise RoutingError("unsupported SDK decision")
                if key == "suppressOutput" and type(item) is not bool:
                    raise RoutingError("SDK suppressOutput field must be boolean")
                if key in result and result[key] != item:
                    raise RoutingError("workspace hooks returned conflicting SDK decisions")
                result[key] = item
    for key, values in texts.items():
        result[key] = "\n\n".join(values)
    for key, values in specific_texts.items():
        specific[key] = "\n\n".join(values)
    if event == "PreToolUse" and (result.get("decision") == "block" or result.get("continue") is False):
        if specific.get("permissionDecision") in {"allow", "ask"}:
            raise RoutingError("workspace hooks returned an explicit denial alongside allow/ask")
        specific["permissionDecision"] = "deny"
        # Use one unambiguous tool permission channel for explicit JSON denials.
        result.pop("decision", None)
    if blocked:
        if event == "PreToolUse":
            specific.update(permissionDecision="deny", permissionDecisionReason="\n\n".join(errors) or "Workspace policy denied this action.")
        else:
            result.update(decision="block", reason="\n\n".join(errors) or "Workspace policy denied this event.")
    if event == "PreToolUse" and specific.get("permissionDecision") == "deny":
        result.pop("decision", None)
        if result.get("continue") is True:
            result.pop("continue")
    if len(specific) > 1:
        result["hookSpecificOutput"] = specific
    return (2 if blocked else 0), result, "\n\n".join(errors)


def local_audit(environment, payload, event, commands, outputs, value):
    """Non-authorizing local observation; never raw prompt/input/result logging."""
    if not environment.get("CRAFT_SESSION_DIR"):
        return
    directory = Path(environment["CRAFT_SESSION_DIR"]) / "data"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.resolve() != directory:
        return
    import shlex
    from datetime import datetime, timezone
    selected = []
    root = Path(environment["CRAFT_AGENT_WORKSPACE"])
    for (command, _), (code, _, _) in zip(commands, outputs):
        words = shlex.split(command)
        path = words[1] if len(words) > 1 and words[0] in {"bash", "/bin/bash", "python3"} else words[0] if words else ""
        try:
            name = str(Path(path).relative_to(root / "hooks"))
        except ValueError:
            name = "operator-command"
        selected.append({"hook": name, "exit": code})
    tool = payload.get("tool_name", "")
    tool_id = payload.get("tool_use_id", "")
    specific = value.get("hookSpecificOutput", {})
    denied = value.get("continue") is False or value.get("decision") == "block" or specific.get("permissionDecision") == "deny" or any(code for code, _, _ in outputs)
    entry = {"evidence_kind": "local-router-observation", "timestamp": datetime.now(timezone.utc).isoformat(),
             "event": event, "tool": tool if isinstance(tool, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{0,200}", tool) else "unrecognized",
             "tool_use_id": tool_id if isinstance(tool_id, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{0,200}", tool_id) else "",
             "craft_session": Path(environment["CRAFT_SESSION_DIR"]).name,
             "source_revision": environment["CCP_CRAFT_ROUTER_SOURCE_REVISION"],
             "policy_sha256": environment["CCP_CRAFT_ROUTER_POLICY_SHA256"],
             "router_sha256": environment["CCP_CRAFT_ROUTER_SHA256"],
             "selected_hooks": selected, "verdict": "deny" if denied else "allow"}
    fd = os.open(directory / "craft-hook-router-events.jsonl", os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w") as target:
        info = os.fstat(target.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            return
        target.write(json.dumps(entry, ensure_ascii=True) + "\n")


def claimed_workspace(environment):
    value = environment.get("CRAFT_SESSION_DIR", "")
    path = Path(value)
    return path.parent.parent.resolve() if value and path.is_absolute() and path.parent.name == "sessions" else None


def maybe_enrolled(environment, workspace):
    claimed = claimed_workspace(environment)
    if claimed is not None:
        return claimed == workspace
    marker = environment.get("CRAFT_AGENT_WORKSPACE", "")
    return bool(marker and Path(marker).is_absolute() and Path(marker).resolve() == workspace)


def route(raw: bytes, event: str, workspace: Path, environment=None):
    environment = dict(os.environ if environment is None else environment)
    if not maybe_enrolled(environment, workspace):
        return 0, None, ""  # Native CLI/unenrolled workspace: no policy/receipt read.
    if not craft_ancestry():
        return 0, None, ""  # Marker-only standalone processes are out of scope.
    if claimed_workspace(environment) != workspace:
        raise RoutingError("enrolled Craft workspace has no usable absolute session binding")
    if len(raw) > LIMIT:
        raise RoutingError("SDK payload exceeds its size limit")
    policy, child_environment, bound = session_context(raw, event, environment)
    payload = object_json(raw)
    if not bound:
        note = "Craft session identity metadata is pending or ambiguous. No task authority was borrowed; reads and existing-artifact text edits remain available. Task mutations require a verified own-session binding; retry after host metadata is persisted."
        if event != "PreToolUse":
            return 0, {"hookSpecificOutput": {"hookEventName": event, "additionalContext": note}}, ""
        permitted_without_identity = payload.get("tool_name") in {"Read", "Glob", "Grep", "LS"}
        if payload.get("tool_name") == "Bash":
            spec = importlib.util.spec_from_file_location("siege_verified_read_classifier", workspace / "hooks/lib/read-only-command.py")
            classifier = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(classifier)
            command = payload.get("tool_input", {}).get("command")
            permitted_without_identity = isinstance(command, str) and classifier.main(command) == 0
            if isinstance(command, str) and not permitted_without_identity:
                spec = importlib.util.spec_from_file_location("siege_verified_task_actions", workspace / "hooks/lib/task_actions.py")
                actions = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(actions)
                permitted_without_identity = actions.action(command, payload.get("cwd") or str(workspace)).get("metadata_only", False)
        if not permitted_without_identity:
            return aggregate(event, [(2, "", note)])
    outputs, deadline, output_bytes = [], time.monotonic() + TOTAL_SECONDS, 0
    commands = matching_hooks(policy, event, payload)
    for command, seconds in commands:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RoutingError("workspace hook event exceeded its total budget")
        output = execute_hook(command, raw, child_environment, min(seconds, remaining))
        output_bytes += len(output[1].encode()) + len(output[2].encode())
        if output_bytes > LIMIT:
            raise RoutingError("combined hook output exceeds the invocation bound")
        outputs.append(output)
    result = aggregate(event, outputs)
    if len(json.dumps(result[1], ensure_ascii=True).encode()) > LIMIT:
        raise RoutingError("combined SDK hook response exceeds its bound")
    try:
        local_audit(child_environment, payload, event, commands, outputs, result[1])
    except (OSError, ValueError):
        pass  # Audit availability is not permission and never selects a fallback directory.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event", choices=EVENTS, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    # Native callbacks with no Craft marker do not resolve paths or read policy.
    if not (os.environ.get("CRAFT_SESSION_DIR") or os.environ.get("CRAFT_AGENT_WORKSPACE")):
        return 0
    def expired(_signal, _frame):
        raise RoutingError("whole SDK hook invocation exceeded its time budget")
    previous_handler = signal.signal(signal.SIGALRM, expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, TOTAL_SECONDS)
    try:
        if not maybe_enrolled(os.environ, args.workspace):
            return 0
        raw = sys.stdin.buffer.read(LIMIT + 1)
        try:
            code, value, diagnostics = route(raw, args.event, args.workspace)
        except Exception as error:  # SDK exit-1 failures must not bypass enforcement.
            detail = str(error) if isinstance(error, RoutingError) else type(error).__name__
            diagnostics = "Craft hook routing failed closed: " + detail + ". Repair registration from native CLI with the exact-main installer."
            code, value, _ = aggregate(args.event, [(2, "", diagnostics)])
    except Exception as error:
        detail = str(error) if isinstance(error, RoutingError) else type(error).__name__
        diagnostics = "Craft hook routing failed closed: " + detail
        code, value, _ = aggregate(args.event, [(2, "", diagnostics)])
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)
    if value is not None:
        print(json.dumps(value, ensure_ascii=True))
    if diagnostics:
        print(diagnostics, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
