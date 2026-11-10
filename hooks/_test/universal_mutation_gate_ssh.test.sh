#!/usr/bin/env bash
# #1160: ssh is outbound contact, not a local cwd mutation. The mutation gate
# admits ssh only to hosts on the operator-owned hooks/lib/ssh-host-allowlist.json,
# only with options whose effects stay remote, and never through forms that
# could hide a local write. scp/rsync/sftp keep resolving their local operands.
#
# Every case runs from a copied hook tree under `env -i`, so allowlist variants
# and the live session's metadata cannot leak in or out.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
REAL_PY="$(command -v python3)"
PYDIR="$(dirname "$REAL_PY")"
SID="261104-ssh-fixture"
TASK="TEST-1160-ssh-host-scope-fixture"   # unique: never appears in real plans/
WS="$T/ws"; REPO="$T/repo"; PLAIN="$T/plain"
mkdir -p "$WS/sessions/$SID/plans" "$REPO" "$PLAIN" "$T/home"
cp -R "$ROOT/hooks" "$WS/hooks"
cp -R "$ROOT/bin" "$WS/bin"; cp -R "$ROOT/catalog" "$WS/catalog"
( cd "$REPO" && git init -q && git -c user.name=t -c user.email=t@t commit -q --allow-empty -m init )

PASS=0; FAIL=0; FAILED=()
payload() {  # payload <command> [cwd]
    "$REAL_PY" -c 'import json,sys;print(json.dumps({"tool_name":"Bash","hook_event_name":"PreToolUse","session_id":sys.argv[3],"tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2]}))' "$1" "${2:-$REPO}" "$SID"
}
run() {  # run <hook> <command> [cwd] [tree] -> exit code; output in $T/out
    local tree="${4:-$WS/hooks}"
    payload "$2" "${3:-$REPO}" | (cd "${3:-$REPO}" && env -i PATH="$PYDIR:/usr/bin:/bin" HOME="$T/home" \
        CRAFT_AGENT_WORKSPACE="$WS" CRAFT_SESSION_ID="$SID" bash "$tree/$1" >"$T/out" 2>&1)
}
record() {  # record <ok> <name>
    if [[ "$1" == 1 ]]; then PASS=$((PASS + 1)); printf '  [PASS] %s\n' "$2"
    else FAIL=$((FAIL + 1)); FAILED+=("$2"); printf '  [FAIL] %s\n         output: %s\n' "$2" "$(head -c 300 "$T/out")"; fi
}
allow() {  # allow <name> <command> [cwd] [tree]
    run bash/universal-mutation-gate.sh "$2" "${3:-}" "${4:-}"; [[ $? == 0 ]] && record 1 "$1" || record 0 "$1"
}
deny() {  # deny <name> <command> <pattern> [cwd] [tree]: blocked, and for the named reason
    run bash/universal-mutation-gate.sh "$2" "${4:-}" "${5:-}"; local rc=$?
    [[ $rc == 2 ]] && grep -qE "$3" "$T/out" && record 1 "$1" || record 0 "$1 (exit $rc, wanted 2 /$3/)"
}
UNSCOPED='Unscoped mutation'
NOT_LISTED='not on the ssh host allowlist .*ssh-host-allowlist\.json'
OPTION='ssh option -. is not allowed|ssh -o .* is not allowed|is not a plain (port|login)|missing its value'
HIDDEN='run ssh directly'

echo "--- AC1: allowlisted ssh passes with no task gate, from any cwd ---"
allow "AC1 ticket command: ssh -o BatchMode=yes -o ConnectTimeout=6 cyberpower 'screen -ls'" \
    "ssh -o BatchMode=yes -o ConnectTimeout=6 cyberpower 'screen -ls'"
allow "AC1 ssh -o BatchMode=yes cyberpower 'screen -ls' (ticket falsifier)" "ssh -o BatchMode=yes cyberpower 'screen -ls'"
allow "AC1 from a non-git cwd" "ssh -o BatchMode=yes cyberpower 'screen -ls'" "$PLAIN"
allow "AC1 from the filesystem root" "ssh cyberpower uptime" "/"
allow "bare interactive destination" "ssh cyberpower"
allow "user@host destination" "ssh me@cyberpower uptime"
allow "host match is case-insensitive" "ssh CyberPower uptime"
allow "ssh:// URI with user and port" "ssh ssh://me@cyberpower:22 uptime"
allow "/usr/bin/ssh by absolute system path" "/usr/bin/ssh cyberpower uptime"
allow "allowed flags and values" "ssh -4 -C -n -q -T -x -a -v -p 22 -l me cyberpower true"
allow "clustered flags and attached values" "ssh -tt -qp22 -lme -oBatchMode=yes cyberpower true"
allow "-o in 'Key Value' form, case-insensitive" "ssh -o 'connecttimeout 6' -o LogLevel=ERROR -o RequestTTY=no cyberpower true"
allow "allowed option after the destination" "ssh cyberpower -v -o BatchMode=yes true"
allow "remote text with slashes is not a local target" "ssh cyberpower 'cat /etc/hosts'"
allow "quoted remote glob/tilde is not a local expansion" "ssh cyberpower 'ls ~/logs/*.txt'"
allow "remote command after -- may look like options" "ssh cyberpower -- ls -la /tmp"
allow "-- before the destination ends option parsing" "ssh -- cyberpower -o ProxyCommand=remote-arg"
allow "remote words after the command are not options" "ssh cyberpower ls -o ProxyCommand=x"
allow "stderr duplication and /dev/null sink" "ssh cyberpower uptime 2>&1 >/dev/null"
allow "reading local stdin is not a write" "ssh cyberpower 'cat > /tmp/remote' < README.md"
allow "chained with a proven reader" "ssh cyberpower uptime; ls"
allow "explicit task binding prefix" "CCP_TASK_ID=$TASK ssh cyberpower uptime"
allow "existing artifact text edit plus ssh" "gh issue edit 123 --title changed && ssh cyberpower uptime"

echo "--- AC2: other hosts are denied, naming the allowlist ---"
deny "AC2 ssh unknown-host true (ticket falsifier)" "ssh unknown-host true" "$NOT_LISTED"
deny "unknown host with user@" "ssh cyberpower@unknown-host true" "$NOT_LISTED"
deny "allowlisted name as a subdomain" "ssh cyberpower.evil.example true" "$NOT_LISTED"
deny "host given as an -l value is not the destination" "ssh -l cyberpower evil true" "$NOT_LISTED"
deny "host given as a -p value is not a port" "ssh -p cyberpower evil" "$OPTION"
deny "ssh:// URI to another host" "ssh ssh://cyberpower@evil true" "$NOT_LISTED"
deny "IP literal is not an allowlisted alias" "ssh 10.0.0.1 true" "$NOT_LISTED"
deny "malformed destination" "ssh 'cyber power' true" "not a plain \\[user@\\]host"
deny "trailing-dot hostname" "ssh cyberpower. true" "not a plain"
deny "no destination at all" "ssh -v" "requires a literal destination"

echo "--- local-effect and unmodeled ssh options are denied ---"
deny "-o ProxyCommand" "ssh -o ProxyCommand=nc cyberpower true" "$OPTION"
deny "-oProxyCommand attached" "ssh -oProxyCommand=nc cyberpower true" "$OPTION"
deny "-o 'ProxyCommand x' space form" "ssh -o 'ProxyCommand nc %h %p' cyberpower true" "$OPTION"
deny "-o LocalCommand" "ssh -o LocalCommand=touch cyberpower true" "$OPTION"
deny "-o PermitLocalCommand" "ssh -o PermitLocalCommand=yes cyberpower true" "$OPTION"
deny "-o HostName redirects the alias" "ssh -o HostName=evil cyberpower true" "$OPTION"
deny "-o ProxyJump" "ssh -o ProxyJump=evil cyberpower true" "$OPTION"
deny "-o ControlMaster" "ssh -o ControlMaster=yes cyberpower true" "$OPTION"
deny "-o ControlPath" "ssh -o ControlPath=/tmp/sock cyberpower true" "$OPTION"
deny "-o UserKnownHostsFile" "ssh -o UserKnownHostsFile=/tmp/kh cyberpower true" "$OPTION"
deny "-o KnownHostsCommand" "ssh -o KnownHostsCommand=touch cyberpower true" "$OPTION"
deny "-o StrictHostKeyChecking" "ssh -o StrictHostKeyChecking=no cyberpower true" "$OPTION"
deny "-o allowed key with a bad value" "ssh -o BatchMode=maybe cyberpower true" "$OPTION"
deny "-o allowed key with a quoted value" "ssh -o 'User=\"me\"' cyberpower true" "$OPTION"
deny "-o with no value" "ssh cyberpower -o" "$OPTION"
deny "-o with trailing extra words" "ssh -o 'BatchMode yes ProxyCommand' cyberpower true" "$OPTION"
deny "-l empty login" "ssh -l '' cyberpower true" "$OPTION"
deny "dash-led destination after --" "ssh -- -oProxyCommand=nc true" "not a plain"
deny "-F config file" "ssh -F ./cfg cyberpower true" "$OPTION"
deny "-F attached" "ssh -F/dev/null cyberpower true" "$OPTION"
deny "-E log file" "ssh -E ./ssh.log cyberpower true" "$OPTION"
deny "-S control socket" "ssh -S ./sock cyberpower true" "$OPTION"
deny "-M master mode" "ssh -M cyberpower true" "$OPTION"
deny "-L local forward" "ssh -L 8080:localhost:80 cyberpower" "$OPTION"
deny "-R remote forward" "ssh -R 9000:localhost:22 cyberpower" "$OPTION"
deny "-D dynamic forward" "ssh -D 1080 cyberpower" "$OPTION"
deny "-f background" "ssh -f cyberpower sleep 9" "$OPTION"
deny "-f inside a flag cluster" "ssh -qf cyberpower true" "$OPTION"
deny "-W stdio forward" "ssh -W evil:22 cyberpower" "$OPTION"
deny "-J jump host" "ssh -J evil cyberpower true" "$OPTION"
deny "-A agent forwarding" "ssh -A cyberpower true" "$OPTION"
deny "-X X11 forwarding" "ssh -X cyberpower true" "$OPTION"
deny "-Y trusted X11 forwarding" "ssh -Y cyberpower true" "$OPTION"
deny "-i identity file" "ssh -i ./key cyberpower true" "$OPTION"
deny "-G print config" "ssh -G cyberpower" "$OPTION"
deny "-N no command" "ssh -N cyberpower" "$OPTION"
deny "-w tunnel" "ssh -w 0:0 cyberpower" "$OPTION"
deny "-O control command" "ssh -O exit cyberpower" "$OPTION"
deny "-V version" "ssh -V" "$OPTION"
deny "long option form" "ssh --help cyberpower" "$OPTION"
deny "ProxyCommand after the destination (ssh re-parses options)" "ssh cyberpower -o ProxyCommand=nc true" "$OPTION"
deny "-L after the destination" "ssh cyberpower -L 8080:localhost:80" "$OPTION"
deny "-F after the destination" "ssh cyberpower -F ./cfg true" "$OPTION"
deny "denied option between destination and --" "ssh cyberpower -f -- true" "$OPTION"

echo "--- ssh hidden behind another argv0 is denied ---"
deny "relative ./ssh" "./ssh cyberpower true" "$HIDDEN"
deny "other absolute ssh path" "/tmp/ssh cyberpower true" "$HIDDEN"
deny "environment assignment prefix" "SSH_ASKPASS=./x ssh cyberpower true" "$HIDDEN"
deny "timeout wrapper" "timeout 5 ssh cyberpower true" "$HIDDEN"
deny "nohup wrapper" "nohup ssh cyberpower true" "$HIDDEN"
deny "xargs wrapper" "xargs ssh cyberpower < hosts.txt" "$HIDDEN"
deny "sudo wrapper" "sudo ssh evil true" "$HIDDEN"
deny "env wrapper" "env ssh evil true" "$HIDDEN"
deny "command wrapper" "command ssh evil true" "$HIDDEN"
deny "wrapper with ssh in a command string" "watch 'ssh evil true'" "$HIDDEN"

echo "--- AC3: scp/rsync/sftp keep their local operands ---"
deny "AC3 scp cyberpower:/x ./out (ticket falsifier)" "scp cyberpower:/x ./out" "$UNSCOPED"
deny "scp upload still targets the cwd" "scp ./in cyberpower:/x" "$UNSCOPED"
deny "scp to an absolute local path" "scp cyberpower:/x /tmp/out" "$UNSCOPED"
deny "rsync to a local destination" "rsync -a cyberpower:/x ./out" "$UNSCOPED"
deny "rsync -e ssh still targets the cwd" "rsync -e ssh cyberpower:/x out" "$UNSCOPED"
deny "sftp still targets the cwd" "sftp cyberpower" "$UNSCOPED"

echo "--- AC4: wrappers cannot smuggle a local write through ssh ---"
deny "AC4 redirect to an absolute local file" "ssh cyberpower cat /etc/hosts > /tmp/out.txt" "$UNSCOPED"
deny "AC4 tee to a local file" "ssh cyberpower cat x | tee ./f" "$UNSCOPED"
deny "append redirect" "ssh cyberpower cat x >> out.txt" "$UNSCOPED"
deny "stderr redirect to a file" "ssh cyberpower cat x 2> err.log" "$UNSCOPED"
deny "&> redirect" "ssh cyberpower cat x &> both.log" "$UNSCOPED"
deny ">| clobber redirect" "ssh cyberpower cat x >| out.txt" "$UNSCOPED"
deny "newline-separated local mutation" $'ssh cyberpower uptime\ntouch x' "$UNSCOPED"
deny "chained local mutation" "ssh cyberpower uptime && touch x" "$UNSCOPED"
deny "sequenced local deletion" "ssh cyberpower uptime; rm x" "$UNSCOPED"
deny "local write before ssh" "touch x; ssh cyberpower uptime" "$UNSCOPED"
deny "remote output piped into a local interpreter" "ssh cyberpower cat x | python3 -" "$UNSCOPED"
deny "remote output piped into a local shell" "ssh cyberpower cat x | sh" "opaque inline execution"
deny "local command substitution" "ssh cyberpower \"\$(touch x)\"" "shell expansion"
deny "local backtick substitution" "ssh cyberpower \`touch x\`" "shell expansion"
deny "local variable expansion" "ssh cyberpower \"echo \$HOME\"" "shell expansion"
deny "unquoted local glob" "ssh cyberpower ls *" "expanded mutation targets"
deny "backgrounded ssh" "ssh cyberpower sleep 9 &" "unsupported shell operator"
deny "heredoc" "ssh cyberpower cat <<EOF" "unsupported shell operator"
deny "subshell" "(ssh cyberpower uptime)" "shell group"
deny "unknown host chained after an allowed one" "ssh cyberpower uptime; ssh evil uptime" "$NOT_LISTED"
deny "unproven local reader companion keeps its cwd target" "ssh cyberpower uptime; printenv" "$UNSCOPED"
# A GitHub project action beside ssh keeps its task-owned project
# authorization (#1161/#1193): remote_contact_only never short-circuits it.
PROJECT_ADD='gh project item-add 1 --owner electinfo --url https://github.com/electinfo/enterprise/issues/3300'
run bash/universal-mutation-gate.sh "$PROJECT_ADD && ssh cyberpower uptime"
[[ $? == 2 ]] && record 1 "project action beside ssh still needs its project task" \
    || record 0 "project action beside ssh still needs its project task"
shape="$(cd "$REPO" && "$REAL_PY" -c 'import sys,json; sys.path.insert(0, sys.argv[1]); import task_actions as t
s = t.action(sys.argv[3], sys.argv[2]); print(json.dumps([bool(s.get("remote_actions")), s.get("remote_contact_only"), s.get("metadata_only")]))' \
    "$WS/hooks/lib" "$REPO" "$PROJECT_ADD && ssh cyberpower uptime")"
printf '%s' "$shape" > "$T/out"
[[ "$shape" == '[true, false, false]' ]] && record 1 "action(): project+ssh is never remote_contact_only or metadata_only" \
    || record 0 "action(): project+ssh is never remote_contact_only or metadata_only"
# A review-thread resolution beside ssh keeps its task-owned review
# authorization the same way: remote_contact_only never short-circuits it.
REVIEW_RESOLVE="gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: \"PRRT_kwDOabc\"}) { thread { id } } }'"
run bash/universal-mutation-gate.sh "$REVIEW_RESOLVE && ssh cyberpower uptime"
[[ $? == 2 ]] && record 1 "review action beside ssh still needs its review task" \
    || record 0 "review action beside ssh still needs its review task"
shape="$(cd "$REPO" && "$REAL_PY" -c 'import sys,json; sys.path.insert(0, sys.argv[1]); import task_actions as t
s = t.action(sys.argv[3], sys.argv[2]); print(json.dumps([bool(s.get("review_actions")), s.get("remote_contact_only"), s.get("metadata_only")]))' \
    "$WS/hooks/lib" "$REPO" "$REVIEW_RESOLVE && ssh cyberpower uptime")"
printf '%s' "$shape" > "$T/out"
[[ "$shape" == '[true, false, false]' ]] && record 1 "action(): review+ssh is never remote_contact_only or metadata_only" \
    || record 0 "action(): review+ssh is never remote_contact_only or metadata_only"

echo "--- the operator-owned allowlist is the only source, and defects deny ---"
variant() {  # variant <name> <allowlist contents | __absent__>
    cp -R "$WS/hooks" "$T/$1"
    if [[ "$2" == __absent__ ]]; then rm "$T/$1/lib/ssh-host-allowlist.json"
    else printf '%s' "$2" > "$T/$1/lib/ssh-host-allowlist.json"; fi
}
variant widened '{"hosts": ["cyberpower", "build-box"]}'
allow "a host the operator added passes" "ssh build-box uptime" "" "$T/widened"
variant absent __absent__
deny "allowlist absent: cyberpower denied" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/absent"
variant zerobyte ''
deny "allowlist empty (0-byte) file: denied" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/zerobyte"
variant malformed '{"hosts": ["cyberpower",'
deny "allowlist malformed JSON: denied" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/malformed"
variant wrongtype '{"hosts": "cyberpower"}'
deny "allowlist hosts not a list: denied" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/wrongtype"
variant badentry '{"hosts": ["cyberpower", "evil host"]}'
deny "allowlist with an invalid entry: whole file rejected" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/badentry"
variant nonstring '{"hosts": ["cyberpower", 7]}'
deny "allowlist with a non-string entry: denied" "ssh cyberpower uptime" "$NOT_LISTED.*unusable" "" "$T/nonstring"
variant empty '{"hosts": []}'
deny "empty allowlist: denied" "ssh cyberpower uptime" "allowed: none" "" "$T/empty"

echo "--- the grant comes only from the physical policy file ---"
# Physical-file cases: the grant must come from the fixed policy file itself.
# Every case is bounded, so a policy that could stall the hook fails the case
# instead of the suite.
bounded() {  # bounded <name> <tree> <command> <pattern>: exit 2 within 10 s, for the named reason
    payload "$3" > "$T/payload.json"
    "$REAL_PY" - "$2" "$T/payload.json" "$REPO" "$PYDIR" "$T/home" "$WS" "$SID" > "$T/out" 2>&1 <<'PY'
import subprocess, sys
tree, payload, repo, pydir, home, ws, sid = sys.argv[1:]
env = {"PATH": pydir + ":/usr/bin:/bin", "HOME": home, "CRAFT_AGENT_WORKSPACE": ws, "CRAFT_SESSION_ID": sid}
try:
    with open(payload) as stdin:
        done = subprocess.run(["bash", tree + "/bash/universal-mutation-gate.sh"], stdin=stdin,
                              capture_output=True, text=True, cwd=repo, env=env, timeout=10)
    sys.stdout.write(done.stdout + done.stderr)
    sys.exit(done.returncode)
except subprocess.TimeoutExpired:
    print("TIMEOUT: the gate did not return within 10 s")
    sys.exit(124)
PY
    local rc=$?
    [[ $rc == 2 ]] && grep -qE "$4" "$T/out" && record 1 "$1" || record 0 "$1 (exit $rc, wanted 2 within 10 s /$4/)"
}
fresh() {  # fresh <name>: a copied tree with the policy removed
    cp -R "$WS/hooks" "$T/$1"
    rm "$T/$1/lib/ssh-host-allowlist.json"
}
printf '%s' '{"hosts":["outsider"]}' > "$T/outside-policy.json"
fresh linksym
ln -s "$T/outside-policy.json" "$T/linksym/lib/ssh-host-allowlist.json"
bounded "symlinked policy to another file: outsider denied" "$T/linksym" "ssh outsider true" "$NOT_LISTED.*symbolic link"
bounded "symlinked policy: allowlisted host also denied" "$T/linksym" "ssh cyberpower true" "$NOT_LISTED.*symbolic link"
printf '%s' '{"hosts":["outsider"]}' > "$T/linked-policy.json"
fresh linkhard
ln "$T/linked-policy.json" "$T/linkhard/lib/ssh-host-allowlist.json"
bounded "hard-linked policy: outsider denied" "$T/linkhard" "ssh outsider true" "$NOT_LISTED.*hard links"
printf '%s' '{"hosts":["outsider","cyberpower"]}' > "$T/linked-policy.json"
bounded "hard-linked policy after a secondary-path update: still denied" "$T/linkhard" "ssh cyberpower true" "$NOT_LISTED.*hard links"
variant dupkey '{"hosts":[],"hosts":["outsider"]}'
bounded "duplicate hosts key: outsider denied" "$T/dupkey" "ssh outsider true" "$NOT_LISTED.*duplicate key"
fresh oversized
"$REAL_PY" -c 'import sys; open(sys.argv[1], "w").write(" " * 1100000 + "{\"hosts\":[\"cyberpower\"]}")' "$T/oversized/lib/ssh-host-allowlist.json"
bounded "policy over the size cap (1.1 MB): denied" "$T/oversized" "ssh cyberpower true" "$NOT_LISTED.*larger than"
fresh fifo
mkfifo "$T/fifo/lib/ssh-host-allowlist.json"
bounded "FIFO policy: denied without stalling" "$T/fifo" "ssh cyberpower true" "$NOT_LISTED.*not a regular file"
fresh dirpolicy
mkdir "$T/dirpolicy/lib/ssh-host-allowlist.json"
bounded "directory in place of the policy: denied" "$T/dirpolicy" "ssh cyberpower true" "$NOT_LISTED.*not a regular file"
variant extrakey '{"hosts":["cyberpower"],"extra":1}'
bounded "unknown key beside hosts: denied" "$T/extrakey" "ssh cyberpower true" "$NOT_LISTED.*exactly"
variant emptyhost '{"hosts":["cyberpower",""]}'
bounded "empty-string host entry: whole file rejected" "$T/emptyhost" "ssh cyberpower true" "$NOT_LISTED.*list of hostnames"
variant notobject '["cyberpower"]'
bounded "policy that is not an object: denied" "$T/notobject" "ssh cyberpower true" "$NOT_LISTED.*exactly"

echo "--- a covering task gate never widens the host allowlist ---"
TASK_DIR="$WS/sessions/$SID/tasks/ssh-fixture"
mkdir -p "$TASK_DIR"
gate_json() { "$REAL_PY" -c 'import json,sys;open(sys.argv[1],"w").write(json.dumps(json.loads(sys.argv[2])))' "$@"; }
gate_json "$TASK_DIR/think-gate.json" "{\"task_id\": \"$TASK\", \"sessionId\": \"$SID\", \"status\": \"implementing\", \"repo_root\": \"$REPO\", \"scope_paths\": [\"$REPO\"], \"tier\": \"C\"}"
gate_json "$TASK_DIR/investigate-gate.json" "{\"task_id\": \"$TASK\", \"sessionId\": \"$SID\", \"findings\": [\"fixture\"]}"
gate_json "$TASK_DIR/junior-senior-gate.json" "{\"task_id\": \"$TASK\", \"sessionId\": \"$SID\", \"junior_found\": true, \"senior_found\": true}"
gate_json "$TASK_DIR/artifacts-posted-gate.json" "{\"task_id\": \"$TASK\", \"sessionId\": \"$SID\", \"investigate_posted\": true, \"premortem_posted\": true}"
printf -- '---\nticket_refs:\n  - %s: fixture\n---\n# Pre-mortem %s\n\n### Tiger 1\nSeverity: LOW\nMitigation: fixture.\n' "$TASK" "$TASK" \
    > "$WS/sessions/$SID/plans/pre-mortem-ssh-fixture.md"
allow "control: a covered local mutation passes" "touch x"
allow "AC3 positive: scp into the covered cwd passes" "scp cyberpower:/x ./out"
allow "AC4 positive: covered redirect plus allowlisted ssh passes" "ssh cyberpower cat x > out.txt"
deny "unknown host denied even under a covering gate" "ssh unknown-host true" "$NOT_LISTED"
deny "local-effect option denied even under a covering gate" "ssh -o ProxyCommand=nc cyberpower true" "$OPTION"
deny "wrapper denied even under a covering gate" "timeout 5 ssh unknown-host true" "$HIDDEN"
allow "allowlisted ssh still passes alongside a covering gate" "ssh cyberpower uptime"

# An allowlisted contact is outbound contact only. Even
# with a covering task gate, the resolution must not select, bind or report
# that task for the ssh, so it can never be read as task-authorized remote
# mutation. A local write in the same command still binds the gate normally.
resolution() {  # resolution <command> -> resolver JSON for the copied tree, in $T/out
    payload "$1" | (cd "$REPO" && env -i PATH="$PYDIR:/usr/bin:/bin" HOME="$T/home" CRAFT_AGENT_WORKSPACE="$WS" \
        CRAFT_SESSION_ID="$SID" CCP_HOOK_INPUT_JSON="$(cat)" "$REAL_PY" "$WS/hooks/lib/resolve-think-gate.py" \
        --workspace "$WS" --action-json > "$T/out" 2>&1)
}
contact_only() {  # contact_only <name> <command>: flag set, no task authority attached
    resolution "$2"
    "$REAL_PY" -c 'import json,sys; d=json.load(open(sys.argv[1]))
sys.exit(0 if d.get("remote_contact_only") is True and not d.get("gate") and not d.get("task")
         and not d.get("remote_only_authorized") and not d.get("tier") and d.get("paths") == [] else 1)' "$T/out" \
        && record 1 "$1" || record 0 "$1"
}
contact_only "covering gate: allowlisted contact carries no task authority" "ssh cyberpower 'screen -ls'"
contact_only "covering gate: remote-side write text is still only contact" "ssh cyberpower 'touch /srv/remote-file'"
resolution "ssh cyberpower cat x > out.txt"
"$REAL_PY" -c 'import json,sys; d=json.load(open(sys.argv[1])); g=d.get("gate") or {}
sys.exit(0 if not d.get("remote_contact_only") and str(g.get("path","")).endswith("tasks/ssh-fixture/think-gate.json") else 1)' "$T/out" \
    && record 1 "covering gate: a local write beside ssh binds the task gate normally" \
    || record 0 "covering gate: a local write beside ssh binds the task gate normally"

echo "--- other guards still see ssh commands (metadata_only is not reused) ---"
run bash/destructive-guard.sh "ssh cyberpower kubectl delete pod web"
[[ $? == 2 ]] && grep -q 'kubectl mutation' "$T/out" && record 1 "destructive-guard still scans a remote kubectl delete" \
    || record 0 "destructive-guard still scans a remote kubectl delete"
shape="$(cd "$REPO" && "$REAL_PY" -c 'import sys,json; sys.path.insert(0, sys.argv[1]); import task_actions as t
s = t.action("ssh cyberpower uptime", sys.argv[2]); print(json.dumps([s.get("metadata_only"), s.get("remote_contact_only"), s.get("paths")]))' "$WS/hooks/lib" "$REPO")"
printf '%s' "$shape" > "$T/out"
[[ "$shape" == '[false, true, []]' ]] && record 1 "action(): ssh is remote_contact_only, never metadata_only" \
    || record 0 "action(): ssh is remote_contact_only, never metadata_only"

# Each guard's own short-circuit predicate, evaluated on ssh commands. A guard
# "skips" only when its predicate is true; for every ssh form it must be false,
# so destructive-guard, fix-shape-guard and coordinator-status-guard run their
# normal checks, and the Craft router never permits ssh without a verified
# session binding (the unbound-identity path).
cd "$REPO" && "$REAL_PY" - "$WS/hooks/lib" "$REPO" > "$T/out" 2>&1 <<'PY'
import importlib.util, json, os, sys
lib, cwd = sys.argv[1:3]
sys.path.insert(0, lib)
import task_actions as t
spec = importlib.util.spec_from_file_location("roc", os.path.join(lib, "read-only-command.py"))
roc = importlib.util.module_from_spec(spec); spec.loader.exec_module(roc)
commands = ["ssh cyberpower 'rm -rf /'", "ssh cyberpower uptime", "ssh -o BatchMode=yes cyberpower 'screen -ls'",
            "gh issue edit 1 --title t && ssh cyberpower 'rm -rf /'", "ssh unknown-host 'rm -rf /'"]
bad = []
for c in commands:
    s = t.action(c, cwd)
    predicates = {
        "destructive-guard/fix-shape-guard skip": t.released_read_verdict(c) == 0 or bool(s.get("metadata_only")),
        "coordinator-status-guard skip": bool(s.get("read_only") or s.get("metadata_only")),
        "craft router permitted_without_identity": roc.main(c) == 0 or bool(s.get("metadata_only")),
    }
    bad += [f"{name} is true for {c!r}" for name, value in predicates.items() if value]
# (a) the flag exists only after the host check passed.
for c in ["ssh unknown-host true", "ssh 'cyber power' true", "ssh -o ProxyCommand=nc cyberpower true", "./ssh cyberpower"]:
    s = t.action(c, cwd)
    if s.get("remote_contact_only") or not s.get("error"):
        bad.append(f"denied form {c!r} produced {s.get('remote_contact_only')!r} / error {s.get('error')!r}")
print("\n".join(bad) or "ok")
sys.exit(1 if bad else 0)
PY
[[ $? == 0 ]] && record 1 "no guard short-circuits on ssh; flag only after the host check" \
    || record 0 "no guard short-circuits on ssh; flag only after the host check"
# Only the mutation gate path may read the new flag.
readers="$(grep -l 'remote_contact_only' "$WS/hooks/bash/destructive-guard.sh" "$WS/hooks/git/fix-shape-guard.sh" \
    "$WS/hooks/bash/coordinator-status-guard.sh" "$WS/hooks/lib/craft-settings-router.py" "$WS/hooks/lib/git_command.py" 2>/dev/null)"
printf '%s' "$readers" > "$T/out"
[[ -z "$readers" ]] && record 1 "other guards and the Craft router do not read remote_contact_only" \
    || record 0 "other guards and the Craft router do not read remote_contact_only"

echo
echo "Summary: $PASS passed, $FAIL failed"
if (( FAIL > 0 )); then
    printf '  - %s\n' "${FAILED[@]}"
    exit 1
fi
exit 0
