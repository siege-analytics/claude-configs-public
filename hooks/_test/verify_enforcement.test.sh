#!/usr/bin/env bash
# Tests for bin/verify-enforcement.sh
#
# The probe is the acceptance test for "enforcement is live, not just present."
# These tests assert it:
#   1. PASSES a fully-wired fixture (all artifacts + a working blocking gate)
#   2. runs a real live block test (continue:false) against the deployed gate
#   3. FAILS a skills-only fixture (the advisory-only failure mode of #96)
#   4. FAILS when the blocking wrapper is absent from settings.json
#   5. FAILS when a deployed gate guard is missing (F1) or the registered
#      wrapper path does not resolve (F2)
#
# No jq dependency; uses python3 for JSON, matching verify-enforcement.sh.
#
# Refs: #96.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROBE="$REPO_ROOT/bin/verify-enforcement.sh"
REAL_GATE="$REPO_ROOT/hooks/resolver/ca-enforcement-gate.sh"

pass=0
fail=0
ok()   { echo "  PASS: $1"; pass=$((pass + 1)); }
bad()  { echo "  FAIL: $1" >&2; fail=$((fail + 1)); }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- Build a fully-wired PASS fixture ----------------------------------------

WIRED="$TMP/wired"
mkdir -p "$WIRED/hooks/resolver" "$WIRED/.claude"
cp "$REAL_GATE" "$WIRED/hooks/resolver/ca-enforcement-gate.sh"
chmod +x "$WIRED/hooks/resolver/ca-enforcement-gate.sh"
# The wrapper silently skips guards it cannot execute, so the probe requires
# the deployed guards to be present and executable. Provide clean stubs.
for guard in think-gate-guard.sh investigate-gate-guard.sh skill-enforcement-gate.sh; do
    printf '#!/usr/bin/env bash\n' > "$WIRED/hooks/resolver/$guard"
    chmod +x "$WIRED/hooks/resolver/$guard"
done
if [[ ! -f "$REPO_ROOT/dist/flat/skills/KERNEL.md" ]]; then
    echo "verify_enforcement: full build required before kernel digest fixtures" >&2
    exit 1
fi
cp "$REPO_ROOT/dist/flat/skills/KERNEL.md" "$WIRED/KERNEL.md"
printf '# Compatibility bundle\nBroad compatibility rules\n' > "$WIRED/RULES_BUNDLE.md"
: > "$WIRED/RESOLVER.md"
(cd "$WIRED" && ln -s KERNEL.md CLAUDE.md)
cat > "$WIRED/enforcement-manifest.json" <<'JSON'
{"gates":[{"id":"think-gate"},{"id":"investigate-gate"}]}
JSON
cat > "$WIRED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$WIRED/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
cat > "$WIRED/automations.json" <<'JSON'
{"version":2,"automations":{"SchedulerTick":[{"name":"Standing-order watchdog","cron":"*/10 * * * *","actions":[{"type":"prompt","prompt":"x"}]}]}}
JSON

# Native acceptance uses the actual packaged range path, never a stub.
mkdir -p "$WIRED/.githooks" "$WIRED/bin" "$WIRED/catalog"
cp "$REPO_ROOT/.githooks/pre-push" "$WIRED/.githooks/pre-push"
cp -R "$REPO_ROOT/hooks/git" "$REPO_ROOT/hooks/lib" "$WIRED/hooks/"
cp "$REPO_ROOT/bin/review-risk.py" "$WIRED/bin/"
cp "$REPO_ROOT/catalog/review-risk-policy.json" "$WIRED/catalog/"

if bash "$PROBE" --target "$WIRED" --mode craft-agent >/dev/null 2>&1; then
    ok "fully-wired fixture passes"
else
    bad "fully-wired fixture should pass but did not"
fi

# An interactive install hands the probe a stdin that never closes (a TTY).
# The probe must not read it: give it an open, silent pipe and a deadline.
# Bash 3.2 and stock macOS have neither `exec {fd}<` nor `timeout`, so this
# uses a FIFO held open by a background writer and a polling deadline. The
# writer's only open descriptor is the FIFO, so it cannot keep this test's own
# output open; killing it closes the FIFO and releases any reader.
mkfifo "$TMP/never_closes"
sleep 600 > "$TMP/never_closes" 2>/dev/null < /dev/null &
writer=$!
bash "$PROBE" --target "$WIRED" --mode craft-agent < "$TMP/never_closes" >/dev/null 2>&1 &
probe=$!
waited=0
while kill -0 "$probe" 2>/dev/null && [ "$waited" -lt 120 ]; do sleep 1; waited=$((waited + 1)); done
if kill -0 "$probe" 2>/dev/null; then
    kill "$probe" 2>/dev/null; rc=124
else
    wait "$probe"; rc=$?
fi
kill "$writer" 2>/dev/null; wait "$writer" 2>/dev/null
if [[ $rc -eq 0 ]]; then
    ok "probe completes when the caller's stdin never closes"
else
    bad "probe with an open stdin exited $rc (124 = hung waiting on stdin)"
fi

# --- PASS fixture: fully wired but NO watchdog automation ---------------------
# The standing-order watchdog is opt-in and not wired by default (README.md);
# its absence is advisory, not an enforcement failure. A fully-wired target
# whose only "gap" is the missing watchdog must PASS. Goes red if Check 7 is
# reverted to `fail`.

NOWATCHDOG="$TMP/nowatchdog"
cp -r "$WIRED" "$NOWATCHDOG"
rm -f "$NOWATCHDOG/CLAUDE.md"
(cd "$NOWATCHDOG" && ln -s KERNEL.md CLAUDE.md)
cat > "$NOWATCHDOG/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NOWATCHDOG/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
cat > "$NOWATCHDOG/automations.json" <<'JSON'
{"version":2,"automations":{"SchedulerTick":[{"name":"Skills sync","cron":"0 * * * *","actions":[{"type":"prompt","prompt":"x"}]}]}}
JSON
if bash "$PROBE" --target "$NOWATCHDOG" --mode craft-agent >/dev/null 2>&1; then
    ok "fully-wired-but-no-watchdog fixture passes (watchdog is advisory)"
else
    bad "no-watchdog fixture should PASS (watchdog opt-in) but failed"
fi

# --- PASS fixture: fully wired but automations.json ABSENT -------------------
# Check 7 has two downgraded branches: watchdog-automation-absent (covered by
# NOWATCHDOG above) and automations.json-file-absent. Cover the second: a target
# with no automations.json at all (watchdog never configured) must also PASS.
# Goes red if the file-absent branch is reverted to `fail`.

NOAUTOMATIONS="$TMP/noautomations"
cp -r "$WIRED" "$NOAUTOMATIONS"
rm -f "$NOAUTOMATIONS/CLAUDE.md"
(cd "$NOAUTOMATIONS" && ln -s KERNEL.md CLAUDE.md)
cat > "$NOAUTOMATIONS/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NOAUTOMATIONS/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
rm -f "$NOAUTOMATIONS/automations.json"
if bash "$PROBE" --target "$NOAUTOMATIONS" --mode craft-agent >/dev/null 2>&1; then
    ok "fully-wired-but-no-automations.json fixture passes (watchdog is advisory)"
else
    bad "no-automations.json fixture should PASS (watchdog opt-in) but failed"
fi

# --- PASS fixture: operator file equals complete kernel content --------------

OPERATOR_EMBED="$TMP/operator-embed"
cp -r "$WIRED" "$OPERATOR_EMBED"
rm -f "$OPERATOR_EMBED/CLAUDE.md"
cp "$OPERATOR_EMBED/KERNEL.md" "$OPERATOR_EMBED/CLAUDE.md"
cat > "$OPERATOR_EMBED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$OPERATOR_EMBED/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$OPERATOR_EMBED" --mode craft-agent >/dev/null 2>&1; then
    ok "operator CLAUDE.md exactly equal to the complete kernel passes"
else
    bad "operator CLAUDE.md exactly equal to kernel content should pass but failed"
fi

# --- FAIL fixture: decoy kernel filename mention without content -------------

DECOY_MOUNT="$TMP/decoy-mount"
cp -r "$WIRED" "$DECOY_MOUNT"
rm -f "$DECOY_MOUNT/CLAUDE.md"
printf 'The KERNEL.md is not included in this operator file.\n' > "$DECOY_MOUNT/CLAUDE.md"
cat > "$DECOY_MOUNT/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$DECOY_MOUNT/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$DECOY_MOUNT" --mode craft-agent >/dev/null 2>&1; then
    bad "operator CLAUDE.md with a decoy kernel mention should FAIL but passed"
else
    ok "operator CLAUDE.md decoy kernel mention fails the probe"
fi

# --- FAIL fixture: operator file mounts kernel and broad bundle --------------

MIXED_MOUNT="$TMP/mixed-mount"
cp -r "$WIRED" "$MIXED_MOUNT"
rm -f "$MIXED_MOUNT/CLAUDE.md"
cat > "$MIXED_MOUNT/CLAUDE.md" <<'EOF'
Read KERNEL.md as the safety constitution.
Also read RULES_BUNDLE.md for all detailed rules.
EOF
cat > "$MIXED_MOUNT/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$MIXED_MOUNT/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$MIXED_MOUNT" --mode craft-agent >/dev/null 2>&1; then
    bad "operator CLAUDE.md with a mixed full-bundle mount should FAIL but passed"
else
    ok "operator CLAUDE.md mixed full-bundle mount fails the probe"
fi

# --- FAIL fixture: KERNEL.md redirects to the broad bundle -------------------

KERNEL_SYMLINK="$TMP/kernel-symlink"
cp -r "$WIRED" "$KERNEL_SYMLINK"
rm -f "$KERNEL_SYMLINK/KERNEL.md"
ln -s RULES_BUNDLE.md "$KERNEL_SYMLINK/KERNEL.md"
cat > "$KERNEL_SYMLINK/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$KERNEL_SYMLINK/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$KERNEL_SYMLINK" --mode craft-agent >/dev/null 2>&1; then
    bad "KERNEL.md symlink to RULES_BUNDLE.md should FAIL but passed"
else
    ok "KERNEL.md symlink to RULES_BUNDLE.md fails pinned kernel verification"
fi

# --- FAIL fixture: noncanonical regular kernel content -----------------------

ALTERED_KERNEL="$TMP/altered-kernel"
cp -r "$WIRED" "$ALTERED_KERNEL"
printf '# Not the canonical kernel\n' > "$ALTERED_KERNEL/KERNEL.md"
cat > "$ALTERED_KERNEL/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$ALTERED_KERNEL/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$ALTERED_KERNEL" --mode craft-agent >/dev/null 2>&1; then
    bad "altered regular KERNEL.md should FAIL but passed"
else
    ok "altered regular KERNEL.md fails pinned kernel verification"
fi

# --- FAIL fixture: AGENTS.md symlinks the broad bundle ------------------------

AGENTS_BUNDLE_LINK="$TMP/agents-bundle-link"
cp -r "$WIRED" "$AGENTS_BUNDLE_LINK"
ln -s RULES_BUNDLE.md "$AGENTS_BUNDLE_LINK/AGENTS.md"
cat > "$AGENTS_BUNDLE_LINK/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$AGENTS_BUNDLE_LINK/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$AGENTS_BUNDLE_LINK" --mode craft-agent >/dev/null 2>&1; then
    bad "AGENTS.md symlink to RULES_BUNDLE.md should FAIL but passed"
else
    ok "AGENTS.md symlink to RULES_BUNDLE.md fails the probe"
fi

# --- FAIL fixture: AGENTS.md regular file requests broad bundle --------------

AGENTS_BUNDLE_FILE="$TMP/agents-bundle-file"
cp -r "$WIRED" "$AGENTS_BUNDLE_FILE"
printf 'Read RULES_BUNDLE.md globally.\n' > "$AGENTS_BUNDLE_FILE/AGENTS.md"
cat > "$AGENTS_BUNDLE_FILE/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$AGENTS_BUNDLE_FILE/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$AGENTS_BUNDLE_FILE" --mode craft-agent >/dev/null 2>&1; then
    bad "AGENTS.md regular broad-bundle mount should FAIL but passed"
else
    ok "AGENTS.md regular broad-bundle mount fails the probe"
fi

# --- PASS fixture: regular AGENTS.md exactly duplicates verified kernel ------

AGENTS_EXACT="$TMP/agents-exact"
cp -r "$WIRED" "$AGENTS_EXACT"
cp "$AGENTS_EXACT/KERNEL.md" "$AGENTS_EXACT/AGENTS.md"
cat > "$AGENTS_EXACT/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$AGENTS_EXACT/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$AGENTS_EXACT" --mode craft-agent >/dev/null 2>&1; then
    ok "regular AGENTS.md exactly equal to verified kernel passes"
else
    bad "regular AGENTS.md exactly equal to verified kernel should pass"
fi

# --- FAIL fixture: pasted broad bundle bytes in AGENTS.md --------------------

AGENTS_PASTED="$TMP/agents-pasted"
cp -r "$WIRED" "$AGENTS_PASTED"
cp "$AGENTS_PASTED/RULES_BUNDLE.md" "$AGENTS_PASTED/AGENTS.md"
cat > "$AGENTS_PASTED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$AGENTS_PASTED/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$AGENTS_PASTED" --mode craft-agent >/dev/null 2>&1; then
    bad "AGENTS.md containing pasted broad-bundle bytes should FAIL but passed"
else
    ok "AGENTS.md pasted broad-bundle bytes fail exact composition"
fi

# --- FAIL fixture: kernel plus pasted bundle bytes in CLAUDE.md --------------

CLAUDE_PASTED="$TMP/claude-pasted"
cp -r "$WIRED" "$CLAUDE_PASTED"
rm -f "$CLAUDE_PASTED/CLAUDE.md"
cat "$CLAUDE_PASTED/KERNEL.md" "$CLAUDE_PASTED/RULES_BUNDLE.md" > "$CLAUDE_PASTED/CLAUDE.md"
cat > "$CLAUDE_PASTED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$CLAUDE_PASTED/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$CLAUDE_PASTED" --mode craft-agent >/dev/null 2>&1; then
    bad "CLAUDE.md with kernel plus pasted broad bundle should FAIL but passed"
else
    ok "CLAUDE.md kernel plus pasted broad bundle fails exact composition"
fi

# --- FAIL fixture: AGENTS.md indirect alias to broad bundle ------------------

AGENTS_ALIAS="$TMP/agents-alias"
cp -r "$WIRED" "$AGENTS_ALIAS"
ln -s RULES_BUNDLE.md "$AGENTS_ALIAS/extra-policy.md"
printf 'Read extra-policy.md globally before every task.\n' > "$AGENTS_ALIAS/AGENTS.md"
cat > "$AGENTS_ALIAS/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$AGENTS_ALIAS/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$AGENTS_ALIAS" --mode craft-agent >/dev/null 2>&1; then
    bad "AGENTS.md indirect alias to broad bundle should FAIL but passed"
else
    ok "AGENTS.md indirect policy alias fails exact composition"
fi

# --- PASS fixture: session evidence data is not an active policy root --------

SESSION_EVIDENCE="$TMP/session-evidence"
cp -r "$WIRED" "$SESSION_EVIDENCE"
mkdir -p "$SESSION_EVIDENCE/sessions/review-session/data/archive"
cp "$SESSION_EVIDENCE/RULES_BUNDLE.md" "$SESSION_EVIDENCE/sessions/review-session/data/archive/AGENTS.md"
EXTERNAL_EVIDENCE="$TMP/external-evidence"
mkdir -p "$EXTERNAL_EVIDENCE"
cp "$SESSION_EVIDENCE/RULES_BUNDLE.md" "$EXTERNAL_EVIDENCE/CLAUDE.md"
ln -s "$EXTERNAL_EVIDENCE" "$SESSION_EVIDENCE/sessions/review-session/data/external"
cat > "$SESSION_EVIDENCE/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$SESSION_EVIDENCE/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$SESSION_EVIDENCE" --mode craft-agent >/dev/null 2>&1; then
    ok "session evidence data does not become an active instruction surface"
else
    bad "session evidence data should be excluded from active instruction verification"
fi

# --- FAIL fixture: the session root itself remains an active policy surface --

SESSION_ROOT_POLICY="$TMP/session-root-policy"
cp -r "$WIRED" "$SESSION_ROOT_POLICY"
mkdir -p "$SESSION_ROOT_POLICY/sessions/review-session"
cp "$SESSION_ROOT_POLICY/RULES_BUNDLE.md" "$SESSION_ROOT_POLICY/sessions/review-session/CLAUDE.md"
cat > "$SESSION_ROOT_POLICY/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$SESSION_ROOT_POLICY/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$SESSION_ROOT_POLICY" --mode craft-agent >/dev/null 2>&1; then
    bad "session-root CLAUDE.md should FAIL but passed"
else
    ok "session-root CLAUDE.md remains fail-closed"
fi

# --- FAIL fixtures: lookalike/deeper data paths are not excluded -------------

for rel in \
    sessions/review-session/database/AGENTS.md \
    sessions/review-session/archive/data/CLAUDE.md; do
    LOOKALIKE="$TMP/lookalike-$(echo "$rel" | tr '/' '-')"
    cp -r "$WIRED" "$LOOKALIKE"
    mkdir -p "$(dirname "$LOOKALIKE/$rel")"
    cp "$LOOKALIKE/RULES_BUNDLE.md" "$LOOKALIKE/$rel"
    cat > "$LOOKALIKE/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$LOOKALIKE/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
    if bash "$PROBE" --target "$LOOKALIKE" --mode craft-agent >/dev/null 2>&1; then
        bad "lookalike instruction path $rel should FAIL but passed"
    else
        ok "lookalike instruction path $rel remains fail-closed"
    fi
done

# --- PASS fixture: nested instructions resolve/duplicate verified kernel -----

NESTED_EXACT="$TMP/nested-exact"
cp -r "$WIRED" "$NESTED_EXACT"
mkdir -p "$NESTED_EXACT/project/deeper"
ln -s ../KERNEL.md "$NESTED_EXACT/project/AGENTS.md"
cp "$NESTED_EXACT/KERNEL.md" "$NESTED_EXACT/project/deeper/CLAUDE.md"
cat > "$NESTED_EXACT/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NESTED_EXACT/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NESTED_EXACT" --mode craft-agent >/dev/null 2>&1; then
    ok "nested exact-kernel instruction files pass"
else
    bad "nested exact-kernel instruction files should pass but failed"
fi

# --- FAIL fixture: nested AGENTS.md redirects through broad-policy alias -----

NESTED_ALIAS="$TMP/nested-alias"
cp -r "$WIRED" "$NESTED_ALIAS"
mkdir -p "$NESTED_ALIAS/project"
ln -s RULES_BUNDLE.md "$NESTED_ALIAS/policy.md"
printf 'Read %s/policy.md globally before every task.\n' "$NESTED_ALIAS" > "$NESTED_ALIAS/project/AGENTS.md"
cat > "$NESTED_ALIAS/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NESTED_ALIAS/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NESTED_ALIAS" --mode craft-agent >/dev/null 2>&1; then
    bad "nested AGENTS.md indirect broad-policy alias should FAIL but passed"
else
    ok "nested AGENTS.md indirect broad-policy alias fails recursive verification"
fi

# --- FAIL fixtures: case variants resolve as injected names on APFS ----------

for variant in Agents.md claude.md; do
    CASE_VARIANT="$TMP/case-${variant%%.*}"
    cp -r "$WIRED" "$CASE_VARIANT"
    mkdir -p "$CASE_VARIANT/project"
    cp "$CASE_VARIANT/RULES_BUNDLE.md" "$CASE_VARIANT/project/$variant"
    cat > "$CASE_VARIANT/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$CASE_VARIANT/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
    if bash "$PROBE" --target "$CASE_VARIANT" --mode craft-agent >/dev/null 2>&1; then
        bad "nested case-variant $variant pasted bundle should FAIL but passed"
    else
        ok "nested case-variant $variant pasted bundle fails verification"
    fi
done
CASE_SYMLINK="$TMP/case-symlink"
cp -r "$WIRED" "$CASE_SYMLINK"
mkdir -p "$CASE_SYMLINK/project"
ln -s ../RULES_BUNDLE.md "$CASE_SYMLINK/project/agents.md"
cat > "$CASE_SYMLINK/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$CASE_SYMLINK/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$CASE_SYMLINK" --mode craft-agent >/dev/null 2>&1; then
    bad "nested case-variant agents.md bundle symlink should FAIL but passed"
else
    ok "nested case-variant agents.md bundle symlink fails verification"
fi

# --- FAIL fixture: directory symlink hides external nested instruction -------

NESTED_DIR_LINK="$TMP/nested-dir-link"
cp -r "$WIRED" "$NESTED_DIR_LINK"
EXTERNAL_PROJECT="$TMP/external-project"
mkdir -p "$EXTERNAL_PROJECT"
cp "$NESTED_DIR_LINK/RULES_BUNDLE.md" "$EXTERNAL_PROJECT/AGENTS.md"
ln -s "$EXTERNAL_PROJECT" "$NESTED_DIR_LINK/project"
cat > "$NESTED_DIR_LINK/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NESTED_DIR_LINK/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NESTED_DIR_LINK" --mode craft-agent >/dev/null 2>&1; then
    bad "descendant directory symlink hiding AGENTS.md should FAIL but passed"
else
    ok "descendant directory symlink hiding AGENTS.md fails closed"
fi

# --- FAIL fixture: --target root symlink skips recursive traversal -----------

ROOT_REAL="$TMP/root-real"
cp -r "$WIRED" "$ROOT_REAL"
mkdir -p "$ROOT_REAL/project"
cp "$ROOT_REAL/RULES_BUNDLE.md" "$ROOT_REAL/project/AGENTS.md"
cat > "$ROOT_REAL/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$ROOT_REAL/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$ROOT_REAL" --mode craft-agent >/dev/null 2>&1; then
    bad "physical target with nested broad AGENTS.md should FAIL but passed"
else
    ok "physical target with nested broad AGENTS.md fails recursive verification"
fi
ROOT_ALIAS="$TMP/root-alias"
ln -s "$ROOT_REAL" "$ROOT_ALIAS"
if bash "$PROBE" --target "$ROOT_ALIAS" --mode craft-agent >/dev/null 2>&1; then
    bad "symlinked target root should FAIL before traversal but passed"
else
    ok "symlinked target root fails closed before traversal"
fi
for suffix in // ///; do
    if bash "$PROBE" --target "$ROOT_ALIAS$suffix" --mode craft-agent >/dev/null 2>&1; then
        bad "dirty symlinked target root with $suffix should FAIL but passed"
    else
        ok "dirty symlinked target root with $suffix fails closed"
    fi
done
ROOT_CLEAN="$TMP/root-clean"
cp -r "$WIRED" "$ROOT_CLEAN"
ROOT_CLEAN_ALIAS="$TMP/root-clean-alias"
ln -s "$ROOT_CLEAN" "$ROOT_CLEAN_ALIAS"
for suffix in // ///; do
    if bash "$PROBE" --target "$ROOT_CLEAN_ALIAS$suffix" --mode craft-agent >/dev/null 2>&1; then
        bad "clean symlinked target root with $suffix should FAIL but passed"
    else
        ok "clean symlinked target root with $suffix fails closed"
    fi
done

# --- FAIL fixture: skills only, nothing wired --------------------------------

DARK="$TMP/dark"
mkdir -p "$DARK/skills"
: > "$DARK/skills/placeholder"
if bash "$PROBE" --target "$DARK" --mode craft-agent >/dev/null 2>&1; then
    bad "skills-only fixture should FAIL the probe but passed"
else
    ok "skills-only fixture fails the probe (advisory-only caught)"
fi

# --- FAIL fixture: everything present but blocking wrapper not registered -----

NOWRAP="$TMP/nowrap"
cp -r "$WIRED" "$NOWRAP"
cat > "$NOWRAP/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NOWRAP/hooks/resolver/inject-resolver.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NOWRAP" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture missing the blocking wrapper should FAIL but passed"
else
    ok "fixture missing ca-enforcement-gate registration fails the probe"
fi

# --- FAIL fixture: registered wrapper command has shell suffix ----
# #843 hostile re-review: a command like `gate; echo junk` points at the right
# path but emits mixed stdout at runtime, so CA will not parse a single JSON
# object and will not block.

SUFFIX_REGISTERED="$TMP/suffix-registered"
cp -r "$WIRED" "$SUFFIX_REGISTERED"
cat > "$SUFFIX_REGISTERED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$SUFFIX_REGISTERED/hooks/resolver/ca-enforcement-gate.sh; echo trailing-junk"}]}]}}
JSON
if bash "$PROBE" --target "$SUFFIX_REGISTERED" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with suffixed registered CA command should FAIL but passed"
else
    ok "fixture with suffixed registered CA command fails the probe"
fi

# --- FAIL fixture: registered wrapper command redirects stdout ----

REDIRECT_REGISTERED="$TMP/redirect-registered"
cp -r "$WIRED" "$REDIRECT_REGISTERED"
cat > "$REDIRECT_REGISTERED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$REDIRECT_REGISTERED/hooks/resolver/ca-enforcement-gate.sh >/tmp/ca-gate.log"}]}]}}
JSON
if bash "$PROBE" --target "$REDIRECT_REGISTERED" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with redirected registered CA command should FAIL but passed"
else
    ok "fixture with redirected registered CA command fails the probe"
fi

# --- FAIL fixture: registered wrapper points outside deployed hooks root ----
# #843 hostile review: settings may point at an executable external wrapper
# whose sibling gates are missing/stale. The verifier must reject this instead
# of proving an unrelated deployed wrapper can block.

EXTERNAL_REGISTERED="$TMP/external-registered"
cp -r "$WIRED" "$EXTERNAL_REGISTERED"
EXTERNAL_ROOT="$TMP/external-hooks/resolver"
mkdir -p "$EXTERNAL_ROOT"
cp "$REAL_GATE" "$EXTERNAL_ROOT/ca-enforcement-gate.sh"
chmod +x "$EXTERNAL_ROOT/ca-enforcement-gate.sh"
cat > "$EXTERNAL_REGISTERED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$EXTERNAL_ROOT/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$EXTERNAL_REGISTERED" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with external registered CA wrapper should FAIL but passed"
else
    ok "fixture with external registered CA wrapper fails the probe"
fi

# --- FAIL fixture: registered wrapper is executable but does not actually block ----
# #843: the verifier must test the exact settings-registered command, not a
# hard-coded deployed wrapper path. The real deployed wrapper exists and would
# pass the old mock STALE DESIGN probe, but settings points at a no-op wrapper.

NOOP_REGISTERED="$TMP/noop-registered"
cp -r "$WIRED" "$NOOP_REGISTERED"
cat > "$NOOP_REGISTERED/hooks/resolver/noop-ca-enforcement-gate.sh" <<'SH'
#!/usr/bin/env bash
cat >/dev/null
exit 0
SH
chmod +x "$NOOP_REGISTERED/hooks/resolver/noop-ca-enforcement-gate.sh"
cat > "$NOOP_REGISTERED/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"$NOOP_REGISTERED/hooks/resolver/noop-ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$NOOP_REGISTERED" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with no-op registered CA wrapper should FAIL but passed"
else
    ok "fixture with no-op registered CA wrapper fails the probe"
fi

# --- FAIL fixture: wrapper present but a deployed gate guard is missing (F1) --

NOGUARD="$TMP/noguard"
cp -r "$WIRED" "$NOGUARD"
rm -f "$NOGUARD/hooks/resolver/think-gate-guard.sh"
if bash "$PROBE" --target "$NOGUARD" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with a missing gate guard should FAIL but passed"
else
    ok "fixture with a missing deployed gate guard fails the probe"
fi

# --- FAIL fixture: registered wrapper path does not resolve (F2) --------------

BADPATH="$TMP/badpath"
cp -r "$WIRED" "$BADPATH"
cat > "$BADPATH/.claude/settings.json" <<JSON
{"hooks":{"UserPromptSubmit":[{"hooks":[{"type":"command","command":"/nonexistent/typo/hooks/resolver/ca-enforcement-gate.sh"}]}]}}
JSON
if bash "$PROBE" --target "$BADPATH" --mode craft-agent >/dev/null 2>&1; then
    bad "fixture with a non-resolving wrapper path should FAIL but passed"
else
    ok "fixture with a non-resolving ca-enforcement-gate path fails the probe"
fi

echo
echo "verify_enforcement: $pass passed, $fail failed"
[[ $fail -eq 0 ]]
