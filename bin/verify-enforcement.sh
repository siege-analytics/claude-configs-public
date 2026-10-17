#!/usr/bin/env bash
# Verify local wiring and executable behavior in disposable fixtures.
# This does not establish that a live Craft backend invokes the configured hooks.
#
# Prompt-wrapper conversion is exercised with a mock blocking child; native Git
# range behavior is exercised with actual local pushes. Files and these probes
# establish neither host invocation nor protected server-side authorization.
# Local Git hooks can be bypassed with --no-verify.
#
# Usage:
#   bash bin/verify-enforcement.sh --target <root> [--mode craft-agent|direct]
#       [--git-repo <consumer-root>]
#
#   --target <root>   Installed package/workspace root to check.
#   --mode            craft-agent (default) or direct. Selects the settings
#                     filename and whether CLAUDE.md / automations are required.
#   --git-repo        Exact consumer Git root whose core.hooksPath must resolve
#                     to the target's packaged .githooks directory.
#
# Exit codes:
#   0  every enforcement-critical check passed
#   1  at least one enforcement-critical check failed
#   2  bad invocation
#
# Refs: #96 (portable hook packaging), #409 / #416 / #572 (CA continue:false),
#       #380 (empirical CA verification).

set -uo pipefail

for argument in "$@"; do
    if [[ "$argument" == "--selected" ]]; then
        ROOT="$(cd "$(dirname "$0")/.." && pwd)"
        exec python3 -B "$ROOT/bin/selected_registration.py" verify "$@"
    fi
done

TARGET=""
MODE="craft-agent"
NATIVE_GIT_REPO=""
# Code-owned trust anchor for the canonical compact kernel. This verifier is a
# Tier C surface; never derive the expected digest from the mutable target.
EXPECTED_KERNEL_SHA256="063230c4e75ee2ba6cf8c1afd16d3f3261320c60460bfb550fa599d44f4cb13a"
KERNEL_VERIFIED=0

usage() {
    cat <<'USAGE'
Usage: bash bin/verify-enforcement.sh --target <root> [--mode craft-agent|direct] [--git-repo <consumer-root>]
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --target)
            [[ -z "${2:-}" ]] && { echo "ERROR: --target requires a path" >&2; exit 2; }
            TARGET="$2"; shift 2 ;;
        --mode)
            [[ -z "${2:-}" ]] && { echo "ERROR: --mode requires a value" >&2; exit 2; }
            MODE="$2"; shift 2 ;;
        --git-repo)
            [[ -z "${2:-}" ]] && { echo "ERROR: --git-repo requires a path" >&2; exit 2; }
            NATIVE_GIT_REPO="${2%/}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "ERROR: unknown arg: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [[ -z "$TARGET" ]]; then
    echo "ERROR: --target is required" >&2; usage >&2; exit 2
fi
while [[ "$TARGET" != "/" && "$TARGET" == */ ]]; do
    TARGET="${TARGET%/}"
done
if [[ "$MODE" != "craft-agent" && "$MODE" != "direct" ]]; then
    echo "ERROR: --mode must be craft-agent or direct" >&2; exit 2
fi
if [[ -L "$TARGET" ]]; then
    echo "ERROR: target root must not be a symlink: $TARGET" >&2; exit 1
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

# --- Check 1: local wrapper conversion probe -------------------

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
        ok "local block probe: gate emitted continue:false on STALE DESIGN"
    else
        fail "local block probe: gate did NOT emit continue:false (enforcement is advisory-only)"
        echo "         gate stdout was: ${probe_out:-<empty>}" >&2
    fi
fi

# --- Check 2: settings register the blocking wrapper on UserPromptSubmit ------

if [[ ! -f "$SETTINGS" ]]; then
    fail "settings file missing: $SETTINGS (hooks not registered)"
elif ! python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$SETTINGS" 2>/dev/null; then
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
            ok "registered wrapper local block probe: emitted continue:false on STALE DESIGN"
        else
            fail "registered wrapper local block probe: registered gate did NOT emit continue:false"
            echo "         registered gate stdout was: ${registered_probe_out:-<empty>}" >&2
        fi
    fi
fi

# --- Check 3: compact kernel + compatibility bundle present ------------------

if [[ -f "$TARGET/KERNEL.md" && ! -L "$TARGET/KERNEL.md" && -s "$TARGET/KERNEL.md" ]] \
    && python3 - "$TARGET/KERNEL.md" "$EXPECTED_KERNEL_SHA256" <<'PY'
from pathlib import Path
import hashlib, sys
actual = hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
sys.exit(0 if actual == sys.argv[2] else 1)
PY
then
    KERNEL_VERIFIED=1
    ok "KERNEL.md is a non-symlink file matching the pinned canonical digest"
else
    fail "KERNEL.md is missing, empty, symlinked, or differs from the pinned canonical kernel"
fi
if [[ -f "$TARGET/RULES_BUNDLE.md" ]]; then
    ok "RULES_BUNDLE.md present (on-demand compatibility)"
else
    fail "RULES_BUNDLE.md missing (compatibility rollback absent)"
fi

# --- Check 4: RESOLVER present -----------------------------------------------

if [[ -f "$TARGET/RESOLVER.md" ]]; then
    ok "RESOLVER.md present"
else
    fail "RESOLVER.md missing"
fi

# --- Check 5: enforcement manifest present -----------------------------------

if [[ -f "$TARGET/enforcement-manifest.json" ]]; then
    gate_count="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1])).get("gates", [])))' "$TARGET/enforcement-manifest.json" 2>/dev/null || echo 0)"
    if [[ "$gate_count" -gt 0 ]]; then
        ok "enforcement-manifest.json present ($gate_count gates)"
    else
        fail "enforcement-manifest.json present but declares 0 gates"
    fi
else
    fail "enforcement-manifest.json missing (CA enforcement not deployed)"
fi

# --- Check 6: native Git registration and real range push -------------------

NATIVE_HOOKS="$TARGET/.githooks"
NATIVE_PRE_PUSH="$NATIVE_HOOKS/pre-push"
if [[ ! -f "$NATIVE_PRE_PUSH" || ! -x "$NATIVE_PRE_PUSH" ]]; then
    fail "native .githooks/pre-push missing or not executable"
elif [[ ! -f "$TARGET/hooks/git/pre-push-self-review.sh" || ! -x "$TARGET/hooks/git/pre-push-self-review.sh" ]]; then
    fail "range-aware hooks/git/pre-push-self-review.sh missing or not executable"
elif [[ ! -f "$TARGET/bin/review-risk.py" || ! -f "$TARGET/catalog/review-risk-policy.json" ]]; then
    fail "native pre-push trusted risk helper or policy missing"
else
    if [[ -n "$NATIVE_GIT_REPO" ]]; then
        git_top=$(git -C "$NATIVE_GIT_REPO" rev-parse --show-toplevel 2>/dev/null || true)
        requested_real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$NATIVE_GIT_REPO")
        git_top_real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "${git_top:-/nonexistent}")
        configured=$(git -C "$NATIVE_GIT_REPO" config --get core.hooksPath 2>/dev/null || true)
        if [[ -z "$git_top" || "$requested_real" != "$git_top_real" || -z "$configured" ]]; then
            fail "consumer repository or core.hooksPath registration is missing/ambiguous: $NATIVE_GIT_REPO"
        else
            if [[ "$configured" = /* ]]; then
                configured_path="$configured"
            else
                configured_path="$NATIVE_GIT_REPO/$configured"
            fi
            configured_real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$configured_path")
            expected_real=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$NATIVE_HOOKS")
            if [[ "$configured_real" == "$expected_real" ]]; then
                ok "consumer core.hooksPath resolves to installed native hooks"
            else
                fail "consumer core.hooksPath resolves outside installed native hooks: $configured"
            fi
        fi
    else
        warn "no consumer repository supplied; native consumer registration is unverified"
    fi

    native_probe=$(mktemp -d)
    trap 'rm -rf "${probe_dir:-}" "${native_probe:-}"' EXIT
    remote="$native_probe/remote.git"
    consumer="$native_probe/consumer"
    git init -q --bare "$remote"
    git init -q "$consumer"
    git -C "$consumer" config user.email probe@example.invalid
    git -C "$consumer" config user.name "Native Hook Probe"
    git -C "$consumer" remote add origin "$remote"
    printf 'baseline\n' > "$consumer/README.md"
    git -C "$consumer" add README.md
    GIT_AUTHOR_DATE=2026-01-01T00:00:00Z GIT_COMMITTER_DATE=2026-01-01T00:00:00Z \
        git -C "$consumer" commit -q --no-verify -m 'baseline'
    git -C "$consumer" branch -M main
    git -C "$consumer" push -q --no-verify -u origin main
    git -C "$consumer" checkout -q -b feature
    git -C "$consumer" config core.hooksPath "$NATIVE_HOOKS"

    printf 'missing source evidence\n' > "$consumer/probe.py"
    git -C "$consumer" add probe.py
    git -C "$consumer" commit -q --no-verify -m $'test: invalid interior #845\n\nReview-Tier: B\nSelf-Review: intentionally incomplete'
    printf 'valid head after invalid interior\n' > "$consumer/head.md"
    git -C "$consumer" add head.md
    git -C "$consumer" commit -q --no-verify -m $'docs: valid head #845\n\nReview-Tier: A\nSelf-Review: probe'

    invalid_log="$native_probe/invalid-push.log"
    if git -C "$consumer" push origin HEAD:refs/heads/feature >"$invalid_log" 2>&1; then
        fail "real native push accepted an invalid interior commit"
    elif git --git-dir="$remote" show-ref --verify --quiet refs/heads/feature; then
        fail "denied native push still changed the remote feature ref"
    elif grep -qF 'BLOCKED by pre-push-self-review hook' "$invalid_log"; then
        ok "real native push rejected invalid interior evidence with no remote side effect"
    else
        fail "native push failed without observed range-hook denial"
    fi

    git -C "$consumer" reset -q --hard origin/main
    printf 'repaired range\n' > "$consumer/repaired.md"
    git -C "$consumer" add repaired.md
    git -C "$consumer" commit -q --no-verify -m $'docs: repaired range #845\n\nReview-Tier: A\nSelf-Review: probe'
    repaired_head=$(git -C "$consumer" rev-parse HEAD)
    if git -C "$consumer" push -q origin HEAD:refs/heads/feature \
        && [[ "$(git --git-dir="$remote" rev-parse refs/heads/feature 2>/dev/null || true)" == "$repaired_head" ]]; then
        ok "same registered hook permits repaired range and advances only the intended ref"
    else
        fail "registered native hook did not permit the repaired valid range"
    fi
fi

# --- Craft-Agent-only checks -------------------------------------------------

if [[ "$MODE" == "craft-agent" ]]; then
    # Check 6: CLAUDE.md must auto-mount only the compact kernel.
    if [[ -L "$TARGET/CLAUDE.md" ]]; then
        link_target="$(readlink "$TARGET/CLAUDE.md")"
        if [[ "$link_target" == "KERNEL.md" ]]; then
            ok "CLAUDE.md -> KERNEL.md (progressive CA auto-inject wired)"
        else
            fail "CLAUDE.md symlink points at '$link_target', not KERNEL.md"
        fi
    elif [[ -f "$TARGET/CLAUDE.md" ]]; then
        if [[ "$KERNEL_VERIFIED" -eq 1 ]] && cmp -s "$TARGET/KERNEL.md" "$TARGET/CLAUDE.md"; then
            ok "CLAUDE.md operator file is byte-identical to the verified compact kernel"
        else
            fail "CLAUDE.md operator file must equal the verified compact kernel exactly"
        fi
    else
        fail "CLAUDE.md missing (CA has nothing to auto-inject; rules never enter the system prompt)"
    fi

    # Check 6b: AGENTS.md is another Craft auto-injected root instruction
    # surface. It may be absent or contain operator guidance, but it must not
    # mount the compatibility bundle or redirect to an unverified policy file.
    if [[ -L "$TARGET/AGENTS.md" ]]; then
        agents_target="$(readlink "$TARGET/AGENTS.md")"
        if [[ "$agents_target" == "KERNEL.md" && "$KERNEL_VERIFIED" -eq 1 ]]; then
            ok "AGENTS.md duplicates only the verified compact kernel"
        else
            fail "AGENTS.md symlink points at '$agents_target'; only verified KERNEL.md is permitted"
        fi
    elif [[ -f "$TARGET/AGENTS.md" ]]; then
        if [[ ! -s "$TARGET/AGENTS.md" ]]; then
            ok "AGENTS.md is empty (no second root policy surface)"
        elif [[ "$KERNEL_VERIFIED" -eq 1 ]] && cmp -s "$TARGET/KERNEL.md" "$TARGET/AGENTS.md"; then
            ok "AGENTS.md regular file duplicates only the verified compact kernel"
        else
            fail "AGENTS.md regular file must be empty or equal the verified compact kernel exactly"
        fi
    else
        ok "AGENTS.md absent (no second root instruction mount)"
    fi

    # Check 6c: Craft may auto-inject descendant CLAUDE.md/AGENTS.md files as
    # sessions enter subdirectories. `find` does not traverse directory
    # symlinks by default, so reject every descendant directory symlink before
    # scanning; otherwise an external tree can hide an injected instruction.
    symlinked_directories=0
    while IFS= read -r -d '' descendant_link; do
        if [[ -d "$descendant_link" ]]; then
            symlinked_directories=$((symlinked_directories + 1))
            fail "descendant directory symlink is not verifiable: ${descendant_link#"$TARGET"/}"
        fi
    done < <(find "$TARGET" -mindepth 1 -type l -print0 2>/dev/null)
    if [[ "$symlinked_directories" -eq 0 ]]; then
        ok "no descendant directory symlinks can hide instruction files"
    fi

    # Apply the exact-content allowlist to every directly traversable nested
    # instruction surface; file aliases must resolve to root KERNEL.md.
    nested_instructions=0
    while IFS= read -r -d '' instruction_file; do
        nested_instructions=$((nested_instructions + 1))
        rel_instruction="${instruction_file#"$TARGET"/}"
        if [[ -L "$instruction_file" ]]; then
            if [[ "$KERNEL_VERIFIED" -eq 1 ]] && python3 - "$TARGET/KERNEL.md" "$instruction_file" <<'PY'
from pathlib import Path
import sys
sys.exit(0 if Path(sys.argv[1]).resolve() == Path(sys.argv[2]).resolve() else 1)
PY
            then
                ok "$rel_instruction resolves only to verified root KERNEL.md"
            else
                fail "$rel_instruction symlink does not resolve to verified root KERNEL.md"
            fi
        elif [[ ! -s "$instruction_file" ]]; then
            ok "$rel_instruction is empty (no nested policy surface)"
        elif [[ "$KERNEL_VERIFIED" -eq 1 ]] && cmp -s "$TARGET/KERNEL.md" "$instruction_file"; then
            ok "$rel_instruction duplicates only the verified compact kernel"
        else
            fail "$rel_instruction must be empty, equal verified KERNEL.md, or resolve directly to it"
        fi
    done < <(find "$TARGET" -mindepth 2 \( -iname CLAUDE.md -o -iname AGENTS.md \) -print0 2>/dev/null)
    if [[ "$nested_instructions" -eq 0 ]]; then
        ok "no nested CLAUDE.md/AGENTS.md instruction surfaces"
    fi

    # Check 7: the standing-order watchdog automation (advisory).
    #
    # The watchdog is opt-in and NOT wired by default -- README.md: each
    # SchedulerTick tick spawns a watchdog session (~144/day) and floods the
    # session list, so standing-order continuity is delivered by the always-on
    # injected resolver rules instead. Its absence is therefore not an
    # enforcement failure; warn (advisory), do not fail. The load-bearing
    # pass/fail is the blocking gate's local probe (Checks 1-6).
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
    echo "LOCAL ENFORCEMENT PROBES FAILED: $errors check(s) failed." >&2
    echo "Local wiring or executable behavior is incomplete; live host status is unverified." >&2
    echo "Run bin/install.sh (Craft Agent) or bin/install-hooks.sh (direct) to wire them." >&2
    exit 1
fi
echo "LOCAL ENFORCEMENT PROBES PASSED for $TARGET; live host invocation remains unverified."
exit 0
