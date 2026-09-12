#!/bin/bash
# Shared library: gate-registry.sh (#873 P0, defect D6)
# Reads the generated enforcement manifest so gate identity is DATA, not
# hardcoded strings scattered across hooks. Later stages consume it:
#   - P1 (D5): gate_runtime_policy() decides advisory vs block per runtime.
#   - P4 (D1): gate_action_class() drives the task-relevance predicate.
#
# BASH ONLY (arrays, like detect-host.sh). Source it, do not run under sh/dash.
#
# The manifest lives at dist/craft-agent/enforcement-manifest.json in the repo
# and is deployed alongside the hooks. Resolution order:
#   1. $CCP_ENFORCEMENT_MANIFEST (explicit override, for tests)
#   2. <hook-dir>/../../dist/craft-agent/enforcement-manifest.json (repo layout)
#   3. <hook-dir>/../enforcement-manifest.json (deployed-flat layout)
#
# Every accessor FAILS SOFT: a missing manifest or unknown gate returns empty /
# the documented default, never an error exit. A gate library that hard-errors
# would turn a missing file into a blocked tool call -- the exact failure mode
# detect-host.sh documents and avoids. Callers treat empty as "no manifest
# opinion" and fall back to their prior behavior.

_gate_registry_manifest_path() {
    if [ -n "${CCP_ENFORCEMENT_MANIFEST:-}" ] && [ -r "${CCP_ENFORCEMENT_MANIFEST}" ]; then
        echo "${CCP_ENFORCEMENT_MANIFEST}"
        return 0
    fi
    local here
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local candidates=(
        "$here/../../dist/craft-agent/enforcement-manifest.json"
        "$here/../enforcement-manifest.json"
    )
    local c
    for c in "${candidates[@]}"; do
        [ -r "$c" ] && { echo "$c"; return 0; }
    done
    return 1
}

# gate_field <gate-id> <field>
# Echo a top-level scalar field for a gate (e.g. action_class, surface, hook).
# Empty if manifest/gate/field is absent.
gate_field() {
    local gate_id="$1" field="$2" manifest
    manifest="$(_gate_registry_manifest_path)" || return 0
    python3 - "$manifest" "$gate_id" "$field" <<'PY' 2>/dev/null || true
import json, sys
try:
    m = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
gid, field = sys.argv[2], sys.argv[3]
for g in m.get("gates", []):
    if g.get("id") == gid:
        v = g.get(field, "")
        if isinstance(v, (dict, list)):
            print(json.dumps(v))
        else:
            print(v if v is not None else "")
        break
PY
}

# gate_action_class <gate-id>  -> the gate's action_class (P4 input).
gate_action_class() { gate_field "$1" "action_class"; }

# gate_runtime_policy <gate-id> [runtime]
# Echo "advisory" | "block" for the given runtime (default: detect_host).
# Fail-soft default is "advisory": if the manifest has no opinion we prefer the
# non-fatal behavior, because the #873 root cause was a gate being fatal where
# it should have narrated. A gate that genuinely must block declares "block"
# explicitly in the manifest.
gate_runtime_policy() {
    local gate_id="$1" runtime="${2:-}"
    if [ -z "$runtime" ]; then
        local here dh
        here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        dh="$here/detect-host.sh"
        if [ -r "$dh" ]; then
            # shellcheck disable=SC1090
            . "$dh" && command -v detect_host >/dev/null 2>&1 && runtime="$(detect_host)"
        fi
        [ -z "$runtime" ] && runtime="unknown"
    fi
    local policy_json
    policy_json="$(gate_field "$gate_id" "runtime_policy")"
    if [ -z "$policy_json" ]; then
        echo "advisory"
        return 0
    fi
    python3 - "$policy_json" "$runtime" <<'PY' 2>/dev/null || echo "advisory"
import json, sys
try:
    p = json.loads(sys.argv[1])
except Exception:
    print("advisory"); sys.exit(0)
print(p.get(sys.argv[2], p.get("unknown", "advisory")))
PY
}

# gate_applies <gate-id> <current-action-class> [runtime]
# The task-relevance predicate (#873 P4, defect D1). Echoes the enforcement
# decision for a gate against the action currently being attempted:
#   "block"    -- the gate governs this action class AND its runtime policy is
#                 block in this runtime. The caller may hard-stop.
#   "advisory" -- either the action is outside this gate's class (the gate is
#                 irrelevant to what is happening -- a design gate does not
#                 govern "list *.pdf"), or the gate's runtime policy is advisory.
#                 The caller narrates but does not hard-stop.
#
# Unknown action class is treated as "in class" (conservative: do not silently
# stop governing because the classifier did not recognize the action). An empty
# current_action_class means "caller could not classify" -> also in-class.
# A gate with no declared action_class governs everything (legacy behavior).
gate_applies() {
    local gate_id="$1" current_action="$2" runtime="${3:-}"
    local gate_action policy
    gate_action="$(gate_action_class "$gate_id")"
    # Relevance: if the gate declares a class and the action declares a class and
    # they differ, the gate is irrelevant -> advisory regardless of policy.
    if [ -n "$gate_action" ] && [ -n "$current_action" ] && [ "$gate_action" != "$current_action" ]; then
        echo "advisory"
        return 0
    fi
    policy="$(gate_runtime_policy "$gate_id" "$runtime")"
    echo "$policy"
}

# Executed directly: dump resolved policy for every gate under the current
# runtime. Handy for `bash hooks/lib/gate-registry.sh` debugging.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    _m="$(_gate_registry_manifest_path)" || { echo "no manifest found" >&2; exit 0; }
    python3 - "$_m" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
for g in m.get("gates", []):
    print(g.get("id"), "action_class=" + str(g.get("action_class", "")),
          "runtime_policy=" + json.dumps(g.get("runtime_policy", {})))
PY
fi
