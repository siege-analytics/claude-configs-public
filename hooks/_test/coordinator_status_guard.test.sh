#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "$ROOT/hooks/_test/run_scenarios.sh"
HOOK="$ROOT/hooks/bash/coordinator-status-guard.sh"

payload() {
  python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"tool_input": {"command": sys.argv[1]}}))
PY
}

expect_block \
  "completion without evidence blocks" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_block \
  "completion with unresolved blocker blocks" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Blocked with no owner response.'")"

expect_block \
  "blocked state without reason blocks" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: blocked.'")"

expect_pass \
  "blocked state with reason passes" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: blocked. Blocker: owner approval thread missing at https://github.com/siege-analytics/claude-configs-public/pull/165#issuecomment-1.'")"

expect_pass \
  "completion with required evidence passes" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Owner approval thread: https://github.com/siege-analytics/claude-configs-public/pull/165#issuecomment-1. Target branch: develop. Merge evidence: PR #165 merged at abc1234. UAT: not applicable for prose-only rule update.'")"

expect_block \
  "issue close without evidence blocks" \
  "$HOOK" \
  "$(payload "gh issue close 165 --reason completed")"

expect_pass \
  "ordinary non-status comment passes" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'I am investigating the review thread now.'")"

expect_block \
  "absolute gh path completion without evidence blocks" \
  "$HOOK" \
  "$(payload "/opt/homebrew/bin/gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_block \
  "command wrapper gh completion without evidence blocks" \
  "$HOOK" \
  "$(payload "command gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_block \
  "env wrapper gh completion without evidence blocks" \
  "$HOOK" \
  "$(payload "env GH_TOKEN=redacted gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_block \
  "which wrapper gh completion without evidence blocks" \
  "$HOOK" \
  "$(payload "\$(which gh) issue comment 31 --body 'Status: complete. Lane done.'")"

expect_block \
  "stdin body-file blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "cat status.md | gh issue comment 165 --body-file -")"

expect_block \
  "unreadable body-file blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body-file /tmp/ccp-609-does-not-exist.md")"

expect_block \
  "dev stdin body-file blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "generate_status | gh issue comment 165 --body-file /dev/stdin")"

expect_block \
  "dev fd zero body-file blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "generate_status | gh issue comment 165 --body-file /dev/fd/0")"

expect_block \
  "proc self fd zero body-file blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "generate_status | gh issue comment 165 --body-file /proc/self/fd/0")"

expect_block \
  "negative owner evidence blocks completion" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Owner approval missing. Target branch: develop. UAT: n/a.'")"

expect_block \
  "pending owner evidence blocks completion" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Owner approval pending. Merge evidence: PR #165. UAT: n/a.'")"

expect_block \
  "command substitution body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body \"\$(cat /tmp/status.md)\"")"

expect_block \
  "environment variable body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "BODY='Status: complete' gh issue comment 165 --body \"\$BODY\"")"

expect_block \
  "braced environment variable body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body \"\${STATUS_BODY}\"")"

expect_block \
  "positional parameter body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "set -- 'Status: complete. Lane done.'; gh issue comment 165 --body \"\$1\"")"

expect_block \
  "indirect variable body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body \"\${!MSG}\"")"

expect_block \
  "gh api issue comment completion without evidence blocks" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/issues/165/comments -f body='Status: complete. Lane done.'")"

expect_block \
  "gh api issue close without evidence blocks" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/issues/165 -X PATCH -f state=closed -f state_reason=completed")"

expect_block \
  "gh api method-before-endpoint comment blocks" \
  "$HOOK" \
  "$(payload "gh api -X POST repos/siege-analytics/claude-configs-public/issues/165/comments -f body='Status: complete. Lane done.'")"

expect_block \
  "gh api method-before-endpoint dynamic body blocks" \
  "$HOOK" \
  "$(payload "gh api --method POST repos/siege-analytics/claude-configs-public/issues/165/comments -f body=\"\$MSG\"")"

expect_block \
  "gh api file-backed body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/issues/165/comments -F body=@status.md")"

expect_block \
  "gh api stdin-backed body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "generate_status | gh api repos/siege-analytics/claude-configs-public/issues/165/comments -F body=@-")"

expect_block \
  "gh api input payload blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/issues/165/comments --input payload.json")"

expect_block \
  "issue editor body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "GH_EDITOR=/tmp/status-editor gh issue comment 165 --editor")"

expect_block \
  "issue web body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --web")"

expect_block \
  "pr review editor body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh pr review 165 --comment --editor")"

expect_block \
  "issue editor equals true body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --editor=true")"

expect_block \
  "issue web equals true body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --web=true")"

expect_block \
  "pr review editor equals true body blocks because body is uninspectable" \
  "$HOOK" \
  "$(payload "gh pr review 165 --comment --editor=true")"

CURLED_APOSTROPHE=$(printf '\342\200\231')
expect_block \
  "future gate plan comment blocks as non-evidence status update" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body \"Understood. I${CURLED_APOSTROPHE}ll stop treating ticket comments as the work. I${CURLED_APOSTROPHE}m going to re-run the gates in the correct order: verify automated tests, prove the develop deployment/UAT state for #31, then only decide whether hotfix/staging movement is allowed.\"")"

expect_block \
  "ascii future gate plan comment blocks as non-evidence status update" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body \"Understood. I will stop treating ticket comments as the work. I am going to rerun the gates in the correct order: verify automated tests, prove the develop deployment/UAT state for #31, then only decide whether hotfix/staging movement is allowed.\"")"

report
