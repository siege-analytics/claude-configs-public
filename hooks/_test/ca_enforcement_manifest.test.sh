#!/usr/bin/env bash
# Regression tests for CA enforcement manifest contract text.
# Ref: #843

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

pass=0
fail=0
ok() { echo "  PASS: $1"; pass=$((pass + 1)); }
bad() { echo "  FAIL: $1" >&2; fail=$((fail + 1)); }

manifest_json="$(python3 - <<'PY' "$REPO_ROOT"
import importlib.util, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("build", root / "bin" / "build.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
print(json.dumps(mod.CA_ENFORCEMENT_GATES))
PY
)"

think_condition="$(printf '%s' "$manifest_json" | python3 -c 'import json, sys
gates = json.load(sys.stdin)
for gate in gates:
    if gate.get("id") == "think-gate":
        print(gate.get("condition", ""))
        break')"

if printf '%s' "$think_condition" | grep -qi 'No design note registered before non-trivial work'; then
    bad "think-gate manifest must not claim missing design note is CA-blocking"
else
    ok "think-gate manifest avoids false missing-design blocking claim"
fi

if printf '%s' "$think_condition" | grep -qi 'missing design note is advisory'; then
    ok "think-gate manifest documents missing design as advisory until mutation gates"
else
    bad "think-gate manifest should document missing design advisory semantics"
fi

# DRIFT CHECK (#892 FU1 review r3 finding #1). The runtime reads the manifest
# built from CA_ENFORCEMENT_GATES. It can drift if someone edits build.py's gate
# list, or hand-edits a built/deployed manifest, without a matching rebuild.
#
# Compare the ON-DISK built manifest AS IT IS NOW against the live source
# CA_ENFORCEMENT_GATES. Do NOT rebuild first -- rebuilding would regenerate the
# file from the same source in the same process (tautological, the round-2 bug)
# AND clobber the developer's dist/. Reading the on-disk file directly means a
# manifest that has drifted from source (stale build, or a hand-edited/deployed
# artifact) is detected. (#892 FU1 review r4 cleanup: no destructive rebuild,
# no dead temp dir.)
built="$REPO_ROOT/dist/craft-agent/enforcement-manifest.json"
if python3 - "$built" "$manifest_json" <<'PY'
import json, sys
try:
    prev = json.load(open(sys.argv[1]))
except Exception:
    # No on-disk manifest -> treat as drift (must be built before deploy)
    sys.exit(1)
source_gates = json.loads(sys.argv[2])
sys.exit(0 if prev.get("gates") == source_gates else 1)
PY
then
    ok "on-disk dist manifest was already in sync with CA_ENFORCEMENT_GATES (no drift)"
else
    bad "on-disk dist manifest DRIFTED from build.py CA_ENFORCEMENT_GATES -- rebuild + redeploy (run bin/build.py)"
fi

# The manifest must be colocated into each consumer package's hooks/ dir, or the
# deployed hook cannot resolve it and runtime-aware enforcement silently reverts
# to plain hard-block (loses the Craft anti-deadlock). (#892 FU1 review #1/#2.)
for pkg in claude-code craft-agent; do
    if [ -f "$REPO_ROOT/dist/$pkg/hooks/enforcement-manifest.json" ]; then
        ok "manifest colocated in dist/$pkg/hooks/"
    else
        bad "manifest NOT colocated in dist/$pkg/hooks/ -- deployed $pkg loses runtime policy"
    fi
done

echo
echo "ca_enforcement_manifest: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
