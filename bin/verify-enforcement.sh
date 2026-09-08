#!/usr/bin/env bash
# Verify that enforcement is actually LIVE in a target root, not merely that
# the advisory files were copied in.
#
# This is the "corner-cutting agent cannot evade it" acceptance probe. Skills
# and rules can be perfectly authored and perfectly synced and still be
# honor-system if the hook wiring, the RULES_BUNDLE mount, and the automation
# watchdog were never installed. A sync that copies skills/ alone passes every
# file-presence check and still leaves enforcement dark. This probe fails when
# that happens.
#
# It runs a LIVE block test: it drives the installed ca-enforcement-gate.sh
# with a mock resolver whose think-gate reports STALE DESIGN, and asserts the
# gate emits a single {"continue": false} object. A gate that cannot block is
# not enforcement.
#
# Usage:
#   bash bin/verify-enforcement.sh --target <root> [--mode craft-agent|direct]
#
#   --target <root>   Workspace root (CA) or repo root (direct-clone) to check.
#   --mode            craft-agent (default) or direct. Selects the settings
#                     filename and whether CLAUDE.md / automations are required.
#
# Exit codes:
#   0  every enforcement-critical check passed
#   1  at least one enforcement-critical check failed
#   2  bad invocation
#
# Refs: #96 (portable hook packaging), #409 / #416 / #572 (CA continue:false),
#       #380 (empirical CA verification).

set -uo pipefail

TARGET=""
MODE="craft-agent"

usage() {
    cat <<'USAGE'
Usage: bash bin/verify-enforcement.sh --target <root> [--mode craft-agent|direct]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            [[ -z "${2:-}" ]] && { echo "ERROR: --target requires a path" >&2; exit 2; }
            TARGET="${2%/}"; shift 2 ;;
        --mode)
            [[ -z "${2:-}" ]] && { echo "ERROR: --mode requires a value" >&2; exit 2; }
            MODE="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "ERROR: --target is required" >&2; usage >&2; exit 2
fi
if [[ "$MODE" != "craft-agent" && "$MODE" != "direct" ]]; then
    echo "ERROR: --mode must be craft-agent or direct" >&2; exit 2
fi
if [[ ! -d "$TARGET" ]]; then
    echo "ERROR: target not found: $TARGET" >&2; exit 1
fi

errors=0
ok()   { echo "  [ok]   $1"; }
fail() { echo "  [FAIL] $1" >&2; errors=$((errors + 1)); }
warn() { echo "  [warn] $1"; }

echo "=== Enforcement verification ==="
echo "Target: $TARGET"
echo "Mode:   $MODE"
echo

# --- Resolve the hooks root and settings file --------------------------------

HOOKS_ROOT="$TARGET/hooks"
if [[ ! -d "$HOOKS_ROOT" ]]; then
    # Direct-clone repo layout keeps hooks at the repo root already; a workspace
    # that vendored the framework under skills/siege/ keeps them there.
    if [[ -d "$TARGET/skills/siege/hooks" ]]; then
        HOOKS_ROOT="$TARGET/skills/siege/hooks"
    fi
fi

if [[ "$MODE" == "craft-agent" ]]; then
    SETTINGS="$TARGET/.claude/settings.json"
else
    SETTINGS="$TARGET/.claude/settings.local.json"
fi

# --- Check 1: the LIVE block test (the load-bearing check) -------------------

GATE="$HOOKS_ROOT/resolver/ca-enforcement-gate.sh"
if [[ ! -f "$GATE" ]]; then
    fail "ca-enforcement-gate.sh not deployed (looked in $HOOKS_ROOT/resolver/)"
else
    # The wrapper silently skips a gate guard it cannot execute
    # (ca-enforcement-gate.sh: [[ ! -x "$gate_script" ]] && return 0). A
    # wrapper with no guards behind it therefore never blocks. The mock block
    # test below proves the wrapper's conversion logic, but only asserting the
    # DEPLOYED guards are present and executable proves the deployed workspace
    # can actually block. Check both.
    for guard in think-gate-guard.sh investigate-gate-guard.sh skill-enforcement-gate.sh; do
        if [[ ! -x "$HOOKS_ROOT/resolver/$guard" ]]; then
            fail "gate guard missing or not executable: resolver/$guard (the wrapper would skip it and never block)"
        fi
    done

    probe_dir="$(mktemp -d)"
    trap 'rm -rf "$probe_dir"' EXIT
    mock_resolver="$probe_dir/hooks/resolver"
    mkdir -p "$mock_resolver"
    cp "$GATE" "$mock_resolver/ca-enforcement-gate.sh"
    chmod +x "$mock_resolver/ca-enforcement-gate.sh"
    # Mock think-gate: emit a blocking keyword the wrapper scans for.
    cat > "$mock_resolver/think-gate-guard.sh" <<'MOCK'
#!/usr/bin/env bash
echo "STALE DESIGN: probe assertion no longer holds. Re-examine."
MOCK
    # Mock the other gates as clean no-ops so only think-gate drives the block.
    for g in investigate-gate-guard.sh skill-enforcement-gate.sh; do
        printf '#!/usr/bin/env bash\n' > "$mock_resolver/$g"
    done
    chmod +x "$mock_resolver"/*.sh

    probe_out="$(bash "$mock_resolver/ca-enforcement-gate.sh" 2>/dev/null || true)"
    if printf '%s' "$probe_out" \
        | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("continue") is False else 1)' 2>/dev/null; then
        ok "live block test: gate emitted continue:false on STALE DESIGN"
    else
        fail "live block test: gate did NOT emit continue:false (enforcement is advisory-only)"
        echo "         gate stdout was: ${probe_out:-<empty>}" >&2
    fi
fi

# --- Check 2: settings register the blocking wrapper on UserPromptSubmit ------

if [[ ! -f "$SETTINGS" ]]; then
    fail "settings file missing: $SETTINGS (hooks not registered)"
elif ! python3 -c "import json; json.load(open('$SETTINGS'))" 2>/dev/null; then
    fail "settings file is not valid JSON: $SETTINGS"
else
    # Extract the registered wrapper command. #843: accepting a substring like
    # `ca-enforcement-gate.sh; echo junk` is false liveness because CA requires
    # the hook stdout to be one clean JSON object. Accept exactly one shell token
    # resolving to ca-enforcement-gate.sh; no suffixes, redirections, pipes, or
    # control operators. Quoted paths with spaces are valid single tokens.
    gate_cmd="$(python3 - "$SETTINGS" <<'PY'
import json, shlex, sys
s = json.load(open(sys.argv[1]))
ups = s.get("hooks", {}).get("UserPromptSubmit", [])
marker = "ca-enforcement-gate.sh"
for grp in ups:
    for h in grp.get("hooks", []):
        c = h.get("command", "")
        if marker not in c:
            continue
        try:
            parts = shlex.split(c)
        except ValueError:
            print("__INVALID_COMMAND__")
            sys.exit(0)
        if len(parts) != 1 or not parts[0].endswith(marker):
            print("__INVALID_COMMAND__")
            sys.exit(0)
        print(parts[0])
        sys.exit(0)
sys.exit(0)
PY
)"
    if [[ -z "$gate_cmd" ]]; then
        fail "settings do NOT register ca-enforcement-gate.sh (blocking wrapper not wired)"
    elif [[ "$gate_cmd" == "__INVALID_COMMAND__" ]]; then
        fail "settings register ca-enforcement-gate.sh with unsupported command shape; expected one shell token and no suffix/redirection"
        gate_cmd=""
    elif [[ ! -x "$gate_cmd" ]]; then
        fail "registered ca-enforcement-gate.sh path is not an executable file: $gate_cmd"
        gate_cmd=""
    else
        expected_gate="$HOOKS_ROOT/resolver/ca-enforcement-gate.sh"
        gate_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$gate_cmd")"
        expected_real="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$expected_gate")"
        if [[ "$gate_real" != "$expected_real" ]]; then
            fail "registered ca-enforcement-gate.sh path is outside deployed hooks root: $gate_cmd (expected $expected_gate)"
            # Do not claim liveness for an external wrapper with unrelated
            # sibling gates. Project-level external hook roots need an explicit
            # contract/override model (#848/#851), not silent acceptance here.
            gate_cmd=""
        else
            ok "settings register deployed ca-enforcement-gate.sh (resolves to executable)"
        fi
    fi

    if [[ -n "${gate_cmd:-}" ]]; then
        # #843: prove the SETTINGS-REGISTERED wrapper, not a hard-coded
        # deployed sibling, can emit continue:false. Copy that exact wrapper
        # into a mock resolver beside blocking/clean child gates so wrapper
        # behavior is tested without relying on target-local gate state.
        probe_dir="$(mktemp -d)"
        trap 'rm -rf "$probe_dir"' EXIT
        mock_resolver="$probe_dir/hooks/resolver"
        mkdir -p "$mock_resolver"
        cp "$gate_cmd" "$mock_resolver/ca-enforcement-gate.sh"
        chmod +x "$mock_resolver/ca-enforcement-gate.sh"
        cat > "$mock_resolver/think-gate-guard.sh" <<'MOCK'
#!/usr/bin/env bash
echo "STALE DESIGN: registered-wrapper probe assertion no longer holds. Re-examine."
MOCK
        for g in investigate-gate-guard.sh skill-enforcement-gate.sh; do
            printf '#!/usr/bin/env bash\n' > "$mock_resolver/$g"
        done
        chmod +x "$mock_resolver"/*.sh
        registered_probe_out="$(printf '%s' '{"prompt":"registered-wrapper-probe"}' | bash "$mock_resolver/ca-enforcement-gate.sh" 2>/dev/null || true)"
        if printf '%s' "$registered_probe_out" \
            | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("continue") is False else 1)' 2>/dev/null; then
            ok "registered wrapper live block test: emitted continue:false on STALE DESIGN"
        else
            fail "registered wrapper live block test: registered gate did NOT emit continue:false"
            echo "         registered gate stdout was: ${registered_probe_out:-<empty>}" >&2
        fi
    fi
fi

# --- Check 3: RULES_BUNDLE present -------------------------------------------

if [[ -f "$TARGET/RULES_BUNDLE.md" ]]; then
    ok "RULES_BUNDLE.md present"
else
    fail "RULES_BUNDLE.md missing (non-hook injection fallback absent)"
fi

# --- Check 4: RESOLVER present -----------------------------------------------

if [[ -f "$TARGET/RESOLVER.md" ]]; then
    ok "RESOLVER.md present"
else
    fail "RESOLVER.md missing"
fi

# --- Check 5: enforcement manifest present -----------------------------------

if [[ -f "$TARGET/enforcement-manifest.json" ]]; then
    gate_count="$(python3 -c "import json; print(len(json.load(open('$TARGET/enforcement-manifest.json')).get('gates', [])))" 2>/dev/null || echo 0)"
    if [[ "$gate_count" -gt 0 ]]; then
        ok "enforcement-manifest.json present ($gate_count gates)"
    else
        fail "enforcement-manifest.json present but declares 0 gates"
    fi
else
    fail "enforcement-manifest.json missing (CA enforcement not deployed)"
fi

# --- Craft-Agent-only checks -------------------------------------------------

if [[ "$MODE" == "craft-agent" ]]; then
    # Check 6: CLAUDE.md must auto-mount the bundle into the CA system prompt.
    if [[ -L "$TARGET/CLAUDE.md" ]]; then
        link_target="$(readlink "$TARGET/CLAUDE.md")"
        if [[ "$link_target" == "RULES_BUNDLE.md" ]]; then
            ok "CLAUDE.md -> RULES_BUNDLE.md (CA auto-inject wired)"
        else
            fail "CLAUDE.md symlink points at '$link_target', not RULES_BUNDLE.md"
        fi
    elif [[ -f "$TARGET/CLAUDE.md" ]]; then
        if grep -q "RULES_BUNDLE\|Always-on\|RESOLVER" "$TARGET/CLAUDE.md" 2>/dev/null; then
            ok "CLAUDE.md is an operator file that references the bundle"
        else
            fail "CLAUDE.md exists but does not mount the bundle (CA will not auto-inject rules)"
        fi
    else
        fail "CLAUDE.md missing (CA has nothing to auto-inject; rules never enter the system prompt)"
    fi

    # Check 7: the standing-order watchdog automation (advisory).
    #
    # The watchdog is opt-in and NOT wired by default -- README.md: each
    # SchedulerTick tick spawns a watchdog session (~144/day) and floods the
    # session list, so standing-order continuity is delivered by the always-on
    # injected resolver rules instead. Its absence is therefore not an
    # enforcement failure; warn (advisory), do not fail. The load-bearing
    # pass/fail is the blocking gate's live block test (Checks 1-6).
    AUTO="$TARGET/automations.json"
    if [[ ! -f "$AUTO" ]]; then
        warn "automations.json has no standing-order watchdog (opt-in; continuity via injected rules)"
    elif python3 - "$AUTO" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(1)
autos = d.get("automations", {})
names = []
for _event, entries in autos.items():
    if isinstance(entries, list):
        names += [e.get("name", "") for e in entries if isinstance(e, dict)]
sys.exit(0 if any("watchdog" in n.lower() for n in names) else 1)
PY
    then
        ok "standing-order watchdog automation registered"
    else
        warn "standing-order watchdog automation not registered (opt-in; continuity via injected rules)"
    fi
fi

echo
if [[ $errors -gt 0 ]]; then
    echo "ENFORCEMENT NOT LIVE: $errors check(s) failed." >&2
    echo "Skills may be present and current, but they are advisory-only." >&2
    echo "Run bin/install.sh (Craft Agent) or bin/install-hooks.sh (direct) to wire them." >&2
    exit 1
fi
echo "ENFORCEMENT LIVE: all checks passed for $TARGET"
exit 0
