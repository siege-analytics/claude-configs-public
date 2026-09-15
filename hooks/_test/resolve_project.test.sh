#!/usr/bin/env bash
# Test: resolve_project() in hooks/lib/resolve-think-gate.py (#873 P3, defect D2)
#
# Maps the current repo (by git origin org/repo) to a project slug declared in
# projects/<slug>/PROJECT.md, or 'umbrella' when none matches. This is the same
# key the build uses for PROJECT.md repo uniqueness, so the gate layer and the
# skills/rules layer agree on what "project" a session is in.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RESOLVER="$ROOT/hooks/lib/resolve-think-gate.py"

_PASS=0; _FAIL=0; _FAILED=()
check() {
    local name="$1" want="$2" got="$3"
    if [[ "$got" == "$want" ]]; then
        _PASS=$((_PASS+1)); printf '  [PASS] %s\n' "$name"
    else
        _FAIL=$((_FAIL+1)); _FAILED+=("$name")
        printf '  [FAIL] %s (want "%s", got "%s")\n' "$name" "$want" "$got"
    fi
}

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

# A workspace with a projects/ dir declaring two projects.
mkdir -p "$TMP/ws/projects/siege-utilities" "$TMP/ws/projects/electinfo"
cat > "$TMP/ws/projects/siege-utilities/PROJECT.md" <<'MD'
---
name: siege-utilities
repo: siege-analytics/siege_utilities
scope:
  - "siege_utilities/**"
owners:
  - x@y.test
---
MD
cat > "$TMP/ws/projects/electinfo/PROJECT.md" <<'MD'
---
name: electinfo
repo: electinfo/platform
owners:
  - x@y.test
---
MD

# Fixture repo whose origin matches siege-utilities.
mkdir -p "$TMP/su"
git -C "$TMP/su" init -q -b main
git -C "$TMP/su" remote add origin git@github.com:siege-analytics/siege_utilities.git

# Fixture repo whose origin matches electinfo (https form).
mkdir -p "$TMP/ei"
git -C "$TMP/ei" init -q -b main
git -C "$TMP/ei" remote add origin https://github.com/electinfo/platform.git

# Fixture repo with an origin that matches no project.
mkdir -p "$TMP/other"
git -C "$TMP/other" init -q -b main
git -C "$TMP/other" remote add origin git@github.com:someone/unrelated.git

# Fixture repo with no origin at all.
mkdir -p "$TMP/noremote"
git -C "$TMP/noremote" init -q -b main

proj() { python3 "$RESOLVER" --workspace "$TMP/ws" --repo-root "$1" --project 2>/dev/null; }

check "ssh origin matches siege-utilities"     siege-utilities "$(proj "$TMP/su")"
check "https origin matches electinfo"         electinfo       "$(proj "$TMP/ei")"
check "unmatched origin -> umbrella"           umbrella        "$(proj "$TMP/other")"
check "no remote -> umbrella"                  umbrella        "$(proj "$TMP/noremote")"
check "no projects dir -> umbrella"            umbrella        "$(python3 "$RESOLVER" --workspace "$TMP/nope" --repo-root "$TMP/su" --project 2>/dev/null)"

echo
if [[ $_FAIL -eq 0 ]]; then
    echo "Results: $_PASS passed, 0 failed"; exit 0
else
    echo "Results: $_PASS passed, $_FAIL failed"
    printf '  FAILED: %s\n' "${_FAILED[@]}"; exit 1
fi
