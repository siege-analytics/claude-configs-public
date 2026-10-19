#!/usr/bin/env bash
# universal-mutation-gate: proven reads pass without a task gate; anything the
# positive allowlist (hooks/lib/read-only-command.py) does not prove falls
# through to the gate. Every reproducer from the hostile reviews of the
# electinfo port (electinfo/electinfo_claude_skills#349) is a must-block case
# with no gate. Ref: #1057, #1051.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/ws" "$T/home"; ln -s "$ROOT/hooks" "$T/ws/hooks"
SD="$T/ws/sessions/s1"; D="$SD/data"; mkdir -p "$D"; printf '{"id":"s1"}\n' > "$SD/session.jsonl"
PASS=0; FAIL=0
gate() {  # gate <cwd> <command> -> allow|block
    local pl
    pl=$(python3 -c 'import json,sys;print(json.dumps({"tool_name":"Bash","tool_input":{"command":sys.argv[1]},"cwd":sys.argv[2],"session_id":"s1"}))' "$2" "$1")
    printf '%s' "$pl" | env -i PATH=/usr/bin:/bin HOME="$T/home" CRAFT_AGENT_WORKSPACE="$T/ws" CRAFT_SESSION_DIR="$SD" \
        bash "$T/ws/hooks/bash/universal-mutation-gate.sh" >/dev/null 2>&1
    [[ $? -eq 2 ]] && echo block || echo allow
}
expect() {  # expect <allow|block> <cwd> <command>
    local got; got="$(gate "$2" "$3")"
    if [[ "$got" == "$1" ]]; then PASS=$((PASS + 1)); else FAIL=$((FAIL + 1)); printf '  FAIL  want %s got %s: %s (cwd %s)\n' "$1" "$got" "$3" "$2"; fi
}
O="$T/home"
echo "== proven reads pass with no gate =="
for c in 'which lilypond' 'sed -n 1,20p /etc/hostname' 'git -C /tmp log --oneline -3' \
         'for f in a b; do echo $f; done' 'git fetch origin --quiet' \
         'ls -la /tmp | head -5' 'grep -rn foo . 2>/dev/null | wc -l' 'gh pr view 12 --json state' \
         'gh api repos/o/r/pulls/1' 'find . -maxdepth 2 -name "*.md" | sort' \
         'cd /tmp && git status -sb' 'jq .a f.json'; do expect allow "$O" "$c"; done
echo "== anything not proven a read still needs a task gate (#349 review) =="
while IFS= read -r c; do [[ -n "$c" ]] && expect block "$O" "$c"; done <<'EOF'
python3 -c "open('/home/x/f','w').write('x')"
node -e "require('fs').writeFileSync('/tmp/x','y')"
perl -i -pe 's/a/b/' /etc/f
bash deploy.sh
source deploy.sh
python3 deploy.py
make install
npm run deploy
install -m 755 a /usr/local/bin/a
ln -sf /a /b
truncate -s 0 /var/log/x
dd if=/dev/zero of=/tmp/x bs=1 count=1
tar -xf a.tar -C /opt
unzip a.zip -d /opt
sed -Ei s/a/b/ /etc/f
unlink /tmp/x
shred -u /tmp/x
rmdir /tmp/d
rsync -a a /b
"rm" -rf /x
r''m -rf /x
$(echo rm) -rf /x
crontab -r
systemctl restart x
sudo systemctl stop x
terraform apply -auto-approve
ansible-playbook site.yml
spark-submit job.py
craft-session spawn x
redis-cli FLUSHALL
mongosh --eval "db.dropDatabase()"
clickhouse-client -q "DROP TABLE t"
trino --execute "DROP TABLE t"
duckdb /shared/x.db "DELETE FROM t"
sqlite3 /shared/x.db "DELETE FROM t"
aws s3api delete-object --bucket b --key k
rclone delete r:b
nc evil.example 80
curl -d x=1 https://example.com
curl --data @f https://example.com
curl -T f https://example.com
curl -o /tmp/x https://example.com
curl -X DELETE https://example.com
wget --post-data x=1 https://example.com
gh workflow run deploy.yml
gh secret set X
gh label create x
gh repo edit --visibility public
gh api -X POST repos/o/r/issues
gh api repos/o/r/issues -f title=x
gh api graphql -f query="query { viewer { login } }"
git stash
git update-index --assume-unchanged f
git symbolic-ref HEAD refs/heads/x
git fetch origin +main:main
git branch -f main x
git add file
git -c user.name=x commit -m y
git worktree remove --force /x
git pull
git clone https://github.com/a/b
git init
pkill -f thing
kill -9 1
touch notes.txt
python3 -m venv venv
pip install requests
sort -o /etc/x f
sed -n '1,2p' -i README.md
sed -n '1,2p' README.md -i
curl -s https://example.test
awk 'NR<10' README.md
uniq a /etc/b
X=1 ls
echo hi > /tmp/x
cat <<END > /tmp/x
END
EOF
echo "== multi-line commands are never proven read-only =="
expect block "$O" $'ls\nbash evil.sh'
expect block "$O" $'ls\nredis-cli -h db FLUSHALL'
expect block "$O" $'ls\nln -sf /secret /tmp/l'
expect block "$O" $'ls\nsystemctl restart nginx'
expect block "$O" $'cat r\n. ./evil.sh'
expect block "$O" $'ls \\\n; rm -rf /x'
expect block "$O" $'ls\nwc -l /etc/hostname'   # multi-line is never proven (safelist policy)
expect block "$O" $'for f in a b\ndo\n  echo $f\ndone'
echo "== quoted ampersands are not backgrounding =="
expect allow "$O" "grep 'foo & bar' /etc/hostname"
expect allow "$O" "git log --grep='fix & feat' -3"
echo "== a session's data/ dir is not yet exempt (scratch rule parked; #349 review) =="
for c in 'touch notes.txt' 'python3 -m venv venv' 'rm -rf out' "rm -rf .''./.''./plans" 'env -C x rm -rf plans' \
         'pkill -f airflow' 'glab mr merge 1'; do expect block "$D" "$c"; done
printf 'read_allowlist: %d passed, %d failed\n' "$PASS" "$FAIL"
(( FAIL == 0 ))
