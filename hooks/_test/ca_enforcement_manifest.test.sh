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

echo
echo "ca_enforcement_manifest: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
