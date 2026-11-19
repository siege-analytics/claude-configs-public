#!/usr/bin/env bash
# Tests for hooks/lib/hook-path.sh and its use by every hook (#1162).
#
# Hooks used to put /home/craftagents/bin first in PATH unconditionally. On
# macOS that directory does not exist and /home is an autofs mount, so every
# command lookup paid an automount miss: the push-time commit-message scan of
# a 75-line message went from 5.8 s to 17.7 s and passed its 15 s timeout.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HELPER="$ROOT/hooks/lib/hook-path.sh"
RUNTIME_BIN=/home/craftagents/bin

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

ok()   { _HARNESS_PASS=$((_HARNESS_PASS + 1)); printf '  [PASS] %s\n' "$1"; }
fail() { _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("$1"); printf '  [FAIL] %s: %s\n' "$1" "${2:0:300}"; }

# --- the helper: prepend only an existing directory ---
mkdir -p "$WORK/bin"
GOT=$(PATH="/usr/bin:/bin" bash -c 'source "$1"; ccp_hook_path "$2"; printf "%s" "$PATH"' _ "$HELPER" "$WORK/bin")
EXPECT="/usr/bin:/bin"; [[ -d $RUNTIME_BIN ]] && EXPECT="$RUNTIME_BIN:$EXPECT"
[[ "$GOT" == "$WORK/bin:$EXPECT" ]] && ok "existing directory is prepended" || fail "existing directory is prepended" "$GOT"

GOT=$(PATH="/usr/bin:/bin" bash -c 'source "$1"; ccp_hook_path "$2"; printf "%s" "$PATH"' _ "$HELPER" "$WORK/absent/bin")
[[ "$GOT" == "$EXPECT" ]] && ok "missing directory leaves PATH unchanged" || fail "missing directory leaves PATH unchanged" "$GOT"

GOT=$(PATH="/usr/bin:/bin" bash -c 'source "$1"; ccp_hook_path "$2"; printf "%s" "$PATH"' _ "$HELPER" "$WORK/bin/file-not-dir" 2>&1)
[[ "$GOT" == "$EXPECT" ]] && ok "a non-directory path is not prepended" || fail "a non-directory path is not prepended" "$GOT"

# --- the line hooks use resolves the helper and applies the default ---
# A hooks tree in a temp dir, with a probe written exactly like a real hook.
mkdir -p "$WORK/tree/hooks/lib" "$WORK/tree/hooks/git"
cp "$HELPER" "$WORK/tree/hooks/lib/"
SOURCE_LINE=$(grep -m1 -F 'lib/hook-path.sh' "$ROOT/hooks/git/detect-ai-fingerprints.sh")
printf '#!/bin/bash\nset -uo pipefail\n%s\nprintf "%%s" "$PATH"\n' "$SOURCE_LINE" > "$WORK/tree/hooks/git/probe.sh"
GOT=$(cd "$WORK" && PATH="/usr/bin:/bin" bash tree/hooks/git/probe.sh 2>&1)
if [[ -d $RUNTIME_BIN ]]; then
  [[ "$GOT" == "$RUNTIME_BIN:/usr/bin:/bin" ]] && ok "hook line prepends the runtime bin on its host" || fail "hook line prepends the runtime bin on its host" "$GOT"
else
  [[ "$GOT" == "/usr/bin:/bin" ]] && ok "hook line leaves PATH unchanged without $RUNTIME_BIN" || fail "hook line leaves PATH unchanged without $RUNTIME_BIN" "$GOT"
fi

# --- a missing helper must not change a hook's own decision ---
# A `set -e` hook (catalog-guard.sh is one) would otherwise exit 1 at the
# source line: a non-blocking hook error, so the guard would fail open. bash
# 3.2 exits on a failed `source` under `set -e` even with `|| true`, so the
# line sources /dev/null when the helper file is absent.
mkdir -p "$WORK/bare/hooks/git"
printf '#!/bin/bash\nset -euo pipefail\n%s\necho reached-own-decision >&2\nexit 2\n' "$SOURCE_LINE" > "$WORK/bare/hooks/git/probe.sh"
GOT=$(bash "$WORK/bare/hooks/git/probe.sh" 2>&1); RC=$?
[[ $RC -eq 2 && "$GOT" == *reached-own-decision* ]] && ok "set -e hook without the helper still reaches its own exit 2" \
  || fail "set -e hook without the helper still reaches its own exit 2" "rc=$RC $GOT"
NONFATAL=$(grep -rhF 'lib/hook-path.sh' "$ROOT/hooks" --include='*.sh' | grep '^source ' | grep -vcF '|| printf /dev/null)"' || true)
[[ "$NONFATAL" -eq 0 ]] && ok "every helper source line falls back to /dev/null" || fail "every helper source line falls back to /dev/null" "$NONFATAL lines without the fallback"

# --- every hook: no raw prefix, helper sourced before any other command ---
RAW=$(grep -rlF "$RUNTIME_BIN" "$ROOT/hooks" --include='*.sh' | grep -v -e '/hooks/lib/hook-path.sh$' -e '/hooks/_test/' || true)
[[ -z "$RAW" ]] && ok "no hook names $RUNTIME_BIN outside the helper" || fail "no hook names $RUNTIME_BIN outside the helper" "$RAW"

USERS=0; LATE=""
while IFS= read -r f; do
  USERS=$((USERS + 1))
  # The helper must come before the hook reads stdin or runs anything: only
  # the shebang, comments, blank lines, `set` and other library sources (which
  # only define functions) may precede it.
  first=$(awk '/^[[:space:]]*(#|$)/ || /^set / { next }
               /^source .*\/\.\.\/lib\/[a-z-]+\.sh"$/ && !/hook-path\.sh/ { next }
               { print; exit }' "$f")
  [[ "$first" == *"lib/hook-path.sh"* ]] || LATE+="${f#$ROOT/} "
done < <(grep -rlF 'lib/hook-path.sh' "$ROOT/hooks" --include='*.sh' | grep -v -e '/hooks/_test/' -e '/hooks/lib/')
(( USERS >= 25 )) && ok "helper sourced by $USERS hooks (was 25 raw prefixes)" || fail "helper sourced by at least 25 hooks" "$USERS"
[[ -z "$LATE" ]] && ok "every hook sources the helper as its first command" || fail "every hook sources the helper as its first command" "$LATE"

# --- the incident: a 75-line commit message scan fits the 15 s hook timeout ---
REPO="$WORK/repo"
git init -q "$REPO"
git -C "$REPO" config user.email t@t
git -C "$REPO" config user.name t
printf 'x\n' > "$REPO/f"
git -C "$REPO" add f
{
  printf 'fix(hooks): keep the scan inside its budget\n\n'
  for _ in $(seq 1 72); do printf 'This line explains part of the change in plain words.\n'; done
} > "$WORK/msg"
git -C "$REPO" commit -q -F "$WORK/msg"
LINES=$(git -C "$REPO" log -1 --format=%B | wc -l | tr -d ' ')
PUSH="git pu""sh origin main"
START=$(python3 -c 'import time; print(time.monotonic())')
OUT=$(printf '{"tool_name":"Bash","tool_input":{"command":"%s"},"cwd":"%s"}' "$PUSH" "$REPO" \
  | bash "$ROOT/hooks/git/detect-ai-fingerprints.sh" 2>&1); RC=$?
ELAPSED=$(python3 -c "import time; print(round(time.monotonic() - $START, 2))")
if [[ $RC -eq 0 && $LINES -ge 75 ]] && python3 -c "import sys; sys.exit(0 if $ELAPSED < 15 else 1)"; then
  ok "fingerprint hook scans a ${LINES}-line message in ${ELAPSED}s (< 15s timeout)"
else
  fail "fingerprint hook fits its 15s timeout on a 75-line message" "rc=$RC lines=$LINES ${ELAPSED}s $OUT"
fi

report
