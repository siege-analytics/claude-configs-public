#!/usr/bin/env bash
# Read-only safelist scenarios for universal-mutation-gate (#704).
#
# The gate blocked read-only jq, diff, comm and sed line-range paging while
# allowing head, so it blocked the commands needed to diagnose it. Class 4
# blocked observability per skills/_enforcement-contradiction-rules.md:72-73.
#
# Every scenario runs with no think-gate resolvable. Without that the gate
# short-circuits to exit 0 and every assertion below passes for the wrong
# reason. TG_ISOLATION_PROOF at the bottom asserts the isolation actually
# holds, so a broken harness fails loudly instead of silently greening.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/bash/universal-mutation-gate.sh"

# --- Isolation: no think-gate may resolve for any scenario ---------------
TMPROOT=$(mktemp -d)
export CRAFT_AGENT_WORKSPACE="$TMPROOT/empty-workspace"
export CLAUDE_THINK_GATE=""
mkdir -p "$CRAFT_AGENT_WORKSPACE"
# CWD is deliberately outside any git repo: the gate derives REPO_ROOT via
# `git rev-parse --show-toplevel` and skips the resolver when it comes back
# empty, so this is what makes the fail-closed path reachable.
NONREPO="$TMPROOT/not-a-repo"
mkdir -p "$NONREPO"
trap 'rm -rf "$TMPROOT"' EXIT

payload() {
  python3 - "$1" "$NONREPO" <<'PY'
import json, sys
print(json.dumps({
    "tool_name": "Bash",
    "cwd": sys.argv[2],
    "tool_input": {"command": sys.argv[1]},
}))
PY
}

# --- Positive control ----------------------------------------------------
# head was always safelisted. If this blocks, the isolation is wrong or the
# gate is broken in a way unrelated to this ticket.
expect_pass \
  "control: head is safelisted and passes" \
  "$HOOK" \
  "$(payload "head -3 README.md")"

# Negative control: something with no path through must still block, proving
# the scenarios are not all passing because the gate is inert.
expect_block \
  "control: unsafelisted command still blocks" \
  "$HOOK" \
  "$(payload "curl -X POST https://example.com")"

# --- Regression: the four measured blocks (#704) -------------------------
expect_pass \
  "sed line-range print passes" \
  "$HOOK" \
  "$(payload "sed -n '1,140p' hooks/bash/universal-mutation-gate.sh")"

expect_pass \
  "sed single-line print passes" \
  "$HOOK" \
  "$(payload "sed -n '42p' README.md")"

expect_pass \
  "jq passes" \
  "$HOOK" \
  "$(payload "jq . hooks/settings-snippet.json")"

expect_pass \
  "jq with flags and filter passes" \
  "$HOOK" \
  "$(payload "jq -r '.hooks | keys[]' hooks/settings-snippet.json")"

expect_pass \
  "diff passes" \
  "$HOOK" \
  "$(payload "diff /tmp/a /tmp/b")"

expect_pass \
  "comm passes" \
  "$HOOK" \
  "$(payload "comm -23 /tmp/a /tmp/b")"

# --- Preservation: forms that reach the safelist loop and must be refused -
# These carry no MUTATION_INDICATORS match, so they fall through to the
# safelist. That is what makes them a real test of the new sed pattern
# rather than a test of an untouched earlier branch.
expect_block \
  "sed -n with w command must block: it writes a file" \
  "$HOOK" \
  "$(payload "sed -n '1w /tmp/e704_probe_w' README.md")"

expect_block \
  "sed -n with e command must block: GNU sed executes shell" \
  "$HOOK" \
  "$(payload "sed -n '1e id' README.md")"

expect_block \
  "sed -n with s///w must block" \
  "$HOOK" \
  "$(payload "sed -n 's/a/b/w /tmp/e704_probe_sw' README.md")"

expect_block \
  "sed -n with r command must block" \
  "$HOOK" \
  "$(payload "sed -n '1r /etc/passwd' README.md")"

expect_block \
  "awk stays blocked: system() executes shell" \
  "$HOOK" \
  "$(payload "awk 'BEGIN{system(\"id\")}'")"

expect_block \
  "awk stays blocked: command pipe into getline executes shell" \
  "$HOOK" \
  "$(payload "awk 'BEGIN{ \"id\" | getline r; print r}'")"

expect_block \
  "awk stays blocked even in its innocent form: out of scope for #704" \
  "$HOOK" \
  "$(payload "awk 'NR<10' README.md")"

# --- Preservation: the sed pattern must not be escapable ------------------
expect_block \
  "sed range followed by a chained mutation must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' README.md; rm -rf /tmp/x")"

expect_block \
  "sed range piped into another command must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' README.md | tee /tmp/x")"

expect_block \
  "sed range with output redirect must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' README.md > /tmp/x")"

expect_block \
  "sed range with command substitution in the file argument must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' \$(id)")"

expect_block \
  "sed in-place still blocks" \
  "$HOOK" \
  "$(payload "sed -i 's/a/b/' README.md")"

expect_block \
  "sed --in-place still blocks" \
  "$HOOK" \
  "$(payload "sed --in-place 's/a/b/' README.md")"

expect_block \
  "awk -i inplace still blocks" \
  "$HOOK" \
  "$(payload "awk -i inplace '{print}' README.md")"

# The two forms that a looser pattern admitted during development. Both
# reach the safelist loop, so they are tests of the new patterns.
#
# MUTATION_INDICATORS matches the literal string "sed -i". GNU getopt
# permutes, so `sed -n '1,2p' -i file` edits in place while containing no
# such substring. Only the single-bare-token file argument stops it.
expect_block \
  "sed with -i permuted after the script must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' -i README.md")"

expect_block \
  "sed with a trailing -i must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' README.md -i")"

expect_block \
  "sed with two file arguments must block" \
  "$HOOK" \
  "$(payload "sed -n '1,2p' a b")"

# Process substitution runs arbitrary commands and contains no character
# that MUTATION_INDICATORS looks for. A bare `^diff ` pattern would admit it.
expect_block \
  "diff with process substitution must block" \
  "$HOOK" \
  "$(payload "diff <(id) <(id)")"

expect_block \
  "comm with process substitution must block" \
  "$HOOK" \
  "$(payload "comm -23 <(sort a) <(sort b)")"

expect_block \
  "jq with command substitution must block" \
  "$HOOK" \
  "$(payload "jq . \$(id)")"

# --- Preservation: arbitrary code execution stays out of scope -----------
expect_block \
  "python3 -c still blocks" \
  "$HOOK" \
  "$(payload "python3 -c \"import json; print(1)\"")"

expect_block \
  "running a python script still blocks" \
  "$HOOK" \
  "$(payload "python3 bin/validate-hooks.py")"

expect_block \
  "running a bash script still blocks" \
  "$HOOK" \
  "$(payload "bash scripts/discipline/evaluate-ticket.sh 704")"

# --- Filesystem proof ----------------------------------------------------
# Asserting exit 2 tests the gate's opinion. This tests the filesystem: the
# write probes above must not have left anything behind, and the write they
# describe must actually be a write, so the scenario is not vacuous.
for probe in /tmp/e704_probe_w /tmp/e704_probe_sw; do
    if [[ -e "$probe" ]]; then
        echo "  [FAIL] filesystem: $probe exists after the run" >&2
        exit 1
    fi
done

WRITE_PROOF="$TMPROOT/sed_w_is_really_a_write"
printf 'x\n' | sed -n "1w $WRITE_PROOF" 2>/dev/null || true
if [[ ! -e "$WRITE_PROOF" ]]; then
    echo "  [FAIL] premise: sed -n '1w <path>' did not create a file on this" >&2
    echo "         platform, so the sed preservation scenarios prove nothing" >&2
    exit 1
fi
echo "  [PASS] premise: sed -n '1w <path>' does create a file, so blocking it matters"

# --- Isolation proof -----------------------------------------------------
# If a think-gate resolved during this run, the negative controls above
# would have exited 0 and been reported as failures. Assert the resolver
# returns null for the harness environment so the reason for any failure is
# unambiguous.
TG_ISOLATION_PROOF=$(cd "$NONREPO" && git rev-parse --show-toplevel 2>/dev/null || true)
if [[ -n "$TG_ISOLATION_PROOF" ]]; then
    echo "  [FAIL] isolation: harness CWD is inside a git repo ($TG_ISOLATION_PROOF);" >&2
    echo "         a repo-scoped think-gate could resolve and green these scenarios" >&2
    exit 1
fi

report
