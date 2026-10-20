#!/usr/bin/env bash
# Fast skip for trigger-specific Bash hooks (#1083).
#
# Oracle: a copy of hooks/ with every fast-skip block deleted is exactly the
# pre-#1083 behaviour. Every case must give the same exit code from the real
# hook and from that copy, run from a git repo on main so the hooks do real
# work. On top of that, a python3 shim counts starts: "skip" cases must start
# none, "full" cases must start at least one (the full path was taken).
# Cases include every gap from the #1083 review: \f and \u escapes, empty,
# nested and non-first commands, and shell-quoted gh for the shlex-based guard.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
REAL_PY="$(command -v python3)"
mkdir -p "$T/bin" "$T/home"
cat > "$T/bin/python3" <<EOF
#!/bin/bash
echo x >> "$T/count"
exec "$REAL_PY" "\$@"
EOF
chmod +x "$T/bin/python3"
cp -R "$ROOT/hooks" "$T/orig"
for f in "$T"/orig/git/*.sh "$T/orig/bash/coordinator-status-guard.sh"; do
    sed '/# Fast skip (#1083)/,/then exit 0; fi$/d' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
if grep -q '_FAST_' "$T"/orig/git/*.sh "$T/orig/bash/coordinator-status-guard.sh"; then echo "oracle still contains fast-skip code"; exit 1; fi
REPO="$T/git/repo"; mkdir -p "$REPO"
( cd "$REPO" && { git init -q -b main 2>/dev/null || { git init -q && git checkout -q -b main; }; } &&
  git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init )
PASS=0; FAIL=0
run() {  # run <tree> <hook> <stdin> -> "rc python3_starts"
    : > "$T/count"
    printf '%s' "$3" | (cd "$REPO" && env -i PATH="$T/bin:/usr/bin:/bin" HOME="$T/home" bash "$1/$2.sh" >/dev/null 2>&1)
    echo "$? $(wc -l < "$T/count" | tr -d ' ')"
}
payload() {  # payload <command> -> JSON tool payload, cwd = the repo (path contains "git")
    "$REAL_PY" -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2],"session_id":"s1"}))' "$1" "$REPO"
}
expect() {  # expect skip|full <hook> <label> <stdin>
    local new old rc n orc ok=1
    new="$(run "$ROOT/hooks" "$2" "$4")"; old="$(run "$T/orig" "$2" "$4")"
    rc="${new% *}"; n="${new#* }"; orc="${old% *}"
    [[ "$rc" == "$orc" ]] || ok=0
    if [[ "$1" == skip ]]; then [[ "$n" == 0 ]] || ok=0; else [[ "$n" -gt 0 ]] || ok=0; fi
    if (( ok )); then PASS=$((PASS + 1))
    else FAIL=$((FAIL + 1)); printf '  FAIL  %s %s: want %s, rc=%s (before #1083: %s), python3 starts=%s\n' "$2" "$3" "$1" "$rc" "$orc" "$n"; fi
}
# hook|trigger pairs (bash 3.2 compatible: no associative arrays)
CASES='git/no-attribution|git commit -m x
git/ticket-required|git commit -m x
git/no-broad-staging|git add -A
git/no-sensitive-files|git add .env
git/detect-ai-fingerprints|git push origin x
git/fix-shape-guard|git push origin x
git/pr-base-guard|gh pr create --base main
git/self-review|gh pr create --base develop
git/survey-context|git push origin x
git/test-tracking-guard|glab mr create
git/post-error-revision-required|git revert HEAD
git/branch-guard|git commit -m x
git/branch-guard|bash deploy.sh
bash/coordinator-status-guard|gh issue close 5 --comment done'
while IFS='|' read -r h trig; do
    expect skip "$h" "plain read" "$(payload 'ls -la | head')"
    expect skip "$h" "read mentioning neither word" "$(payload 'grep -rn TODO src | wc -l')"
    expect skip "$h" "git reads that trigger nothing" "$(payload 'git status && git log --oneline -3 && cat f | wc -l')"
    expect skip "$h" "read with quotes and an escaped backslash" "$(payload 'grep -n "a\\b" f')"
    expect full "$h" "trigger" "$(payload "$trig")"
    expect full "$h" "trigger after a newline" "$(payload $'ls\n'"$trig")"
    expect full "$h" "trigger after a tab" "$(payload $'ls\t'"$trig")"
    expect full "$h" "trigger inside a compound" "$(payload "cd /tmp && $trig")"
    expect full "$h" "trigger quoted inside bash -c" "$(payload "bash -c \"$trig\"")"
    expect full "$h" "form-feed escape" "$(payload "${trig// /$'\f'}")"
    expect full "$h" "unicode-escaped payload" '{"tool_name":"Bash","tool_input":{"command":"\u0067h pr create \u0067it commit -m x \u0067it add -A \u0067it push \u0067it revert HEAD"},"cwd":"/tmp"}'
    expect full "$h" "empty command (git-push fallback)" "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"\"},\"cwd\":\"$REPO\"}"
    expect full "$h" "nested command key" "{\"tool_name\":\"Bash\",\"tool_input\":{\"args\":{\"command\":\"ls\"}},\"cwd\":\"$REPO\"}"
    expect full "$h" "command not the first key" "{\"tool_name\":\"Bash\",\"tool_input\":{\"description\":\"x\",\"command\":\"ls\"},\"cwd\":\"$REPO\"}"
    expect full "$h" "git-hook invocation (refs on stdin)" 'refs/heads/x 0123 refs/heads/x 4567'
done <<< "$CASES"
# shlex-based guard: shell quoting rebuilds the gh token.
for c in 'g\h issue close 5 --comment done' '"g"h issue close 5 --comment done' "g''h issue close 5 --comment done"; do
    expect full bash/coordinator-status-guard "quoted gh: $c" "$(payload "$c")"
done
printf 'git_hook_fast_skip: %d passed, %d failed\n' "$PASS" "$FAIL"
(( FAIL == 0 ))
