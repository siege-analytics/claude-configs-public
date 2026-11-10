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

expect_pass \
  "#1245 descriptive metadata: completion without evidence passes" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_pass \
  "#1245 descriptive metadata: completion with unresolved blocker passes" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Blocked with no owner response.'")"

expect_pass \
  "#1245 descriptive metadata: blocked state without reason passes" \
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

expect_pass \
  "#1245 descriptive metadata: absolute gh path completion without evidence passes" \
  "$HOOK" \
  "$(payload "/opt/homebrew/bin/gh issue comment 31 --body 'Status: complete. Lane done.'")"

expect_pass \
  "#1245 descriptive metadata: command wrapper gh completion without evidence passes" \
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

expect_pass \
  "#1245 descriptive metadata: negative owner evidence passes completion" \
  "$HOOK" \
  "$(payload "gh issue comment 165 --body 'Status: complete. Owner approval missing. Target branch: develop. UAT: n/a.'")"

expect_pass \
  "#1245 descriptive metadata: pending owner evidence passes completion" \
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
expect_pass \
  "#1245 descriptive metadata: future gate plan comment passes as non-evidence status update" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body \"Understood. I${CURLED_APOSTROPHE}ll stop treating ticket comments as the work. I${CURLED_APOSTROPHE}m going to re-run the gates in the correct order: verify automated tests, prove the develop deployment/UAT state for #31, then only decide whether hotfix/staging movement is allowed.\"")"

expect_pass \
  "#1245 descriptive metadata: ascii future gate plan comment passes as non-evidence status update" \
  "$HOOK" \
  "$(payload "gh issue comment 31 --body \"Understood. I will stop treating ticket comments as the work. I am going to rerun the gates in the correct order: verify automated tests, prove the develop deployment/UAT state for #31, then only decide whether hotfix/staging movement is allowed.\"")"

# --- #940: read-only subcommands must never be gated, even when flag names
# contain the guard's state/transition vocabulary. ---

expect_pass \
  "pr view with --json state,mergedAt passes (read, not a status update)" \
  "$HOOK" \
  "$(payload "gh pr view 931 --json state,mergedAt,mergeCommit")"

expect_pass \
  "pr list --state passes (read)" \
  "$HOOK" \
  "$(payload "gh pr list --state open")"

expect_pass \
  "pr diff passes (read)" \
  "$HOOK" \
  "$(payload "gh pr diff 931")"

expect_pass \
  "pr checks passes (read)" \
  "$HOOK" \
  "$(payload "gh pr checks 931")"

expect_pass \
  "issue view with --json state passes (read)" \
  "$HOOK" \
  "$(payload "gh issue view 931 --json state,title")"

expect_pass \
  "issue list --search passes (read)" \
  "$HOOK" \
  "$(payload "gh issue list --search status")"

expect_pass \
  "gh api GET read (non-issue path, no body/method) passes" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/pulls/931")"

# Readiness #919: structure-proven numeric API reads and reopening preservation.
expect_pass \
  "numeric PR API GET with closed comparison is a read" \
  "$HOOK" \
  "$(payload "gh api repos/example/target/pulls/31 --jq '.state == \"closed\"'")"

expect_pass \
  "numeric issue API GET with done data is a read" \
  "$HOOK" \
  "$(payload "gh api repos/example/target/issues/31 --jq '.title == \"done\"'")"

expect_block \
  "issue reopen still requires transition evidence" \
  "$HOOK" \
  "$(payload "gh issue reopen 31")"

# #1164: gate-required think-pipeline artifacts (pre-mortem, investigation,
# junior/senior review) post as-is; the marker cannot launder status claims.
PREMORTEM_BODY=$'## Pre-Mortem\nTicket: siege-analytics/claude-configs-public#1164\n#### Tiger 1: guard rejects the post\n- **Severity:** 8 (P1)\n- Blocker risk: the gate will reject the comment and we will re-run the gate later.\n- **Status:** Mitigated'
UNMARKED_BODY=$'Pre-mortem notes\nTicket: siege-analytics/claude-configs-public#1164\n- Blocker risk: the gate will reject the comment and we will re-run the gate later.'

expect_pass \
  "AC1: marked pre-mortem with will/gate/blocker passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '$PREMORTEM_BODY'")"

expect_pass \
  "#1245 descriptive metadata: AC1 control: same text without the artifact heading still passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '$UNMARKED_BODY'")"

expect_pass \
  "marked investigation fact sheet with blocked status line passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Investigation Fact Sheet
Ticket: #1164
Status: blocked on nothing; the guard is the obstacle and we will rerun the gate.'")"

expect_pass \
  "AC3: marked junior task description passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Junior task description
Ticket: #1164
Current behavior: the lane is blocked and the gate rejects the post.
**Success criteria** — done when the gate accepts the post; tests green.
5. What could go wrong: missing fixtures leave the blocker unresolved.'")"

expect_pass \
  "AC3: marked senior adversarial checklist passes" \
  "$HOOK" \
  "$(payload "gh pr comment 1170 --body '### Senior adversarial checklist
Task-ID: siege-analytics/claude-configs-public#1164
1. Hasty mistakes: the blocker case is missing a fixture; we will re-run the gate.'")"

expect_pass \
  "AC3: junior/senior review with #N in the heading passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Junior/Senior review for #1164
The gate is blocked; we will re-run it after the fix.'")"

expect_pass \
  "marked artifact via gh api comments field passes" \
  "$HOOK" \
  "$(payload "gh api repos/siege-analytics/claude-configs-public/issues/1164/comments -f body='$PREMORTEM_BODY'")"

ARTIFACT_FILE="$(mktemp)"
trap 'rm -f "$ARTIFACT_FILE"' EXIT
printf '%s\n' "$PREMORTEM_BODY" > "$ARTIFACT_FILE"
expect_pass \
  "marked artifact via readable --body-file passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body-file $ARTIFACT_FILE")"

expect_pass \
  "conditional risk scenario naming merge/deploy is not a claim" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
- Scenario: the PR is merged before CI finishes and the hook is deployed broken.
- Mitigation: if CI is red the gate will hold.'")"

expect_pass \
  "#1245 descriptive metadata: AC2: unmarked finish claim without evidence still passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body 'The work is done and merged.'")"

expect_pass \
  "#1245 descriptive metadata: AC2: marked artifact asserting a deploy without evidence passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
The fix is merged and released.'")"

expect_pass \
  "#1245 descriptive metadata: AC2: marked artifact with a completion status line passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Design note
Ticket: #1164
**Status:** done'")"

expect_pass \
  "#1245 descriptive metadata: AC2: marked artifact with a line-leading merge claim passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Junior task description
Ticket: #1164
Merged and shipped.'")"

expect_pass \
  "marked artifact claim with full evidence passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
The fix is merged and released. Owner approval thread: https://github.com/x/y/pull/1#issuecomment-1. Target branch: develop. Rollout: UAT not applicable.'")"

expect_pass \
  "#1245 descriptive metadata: heading after a status update does not relabel it" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body 'Status: complete. Lane done.

## Pre-Mortem
Ticket: #1164'")"

expect_pass \
  "#1245 descriptive metadata: artifact heading without a task reference needs no status-wording proof" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
- Blocker risk: we will re-run the gate later.'")"

expect_pass \
  "#1245 descriptive metadata: artifact heading with Ticket: N/A needs no status-wording proof" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: N/A
- Blocker risk: we will re-run the gate later.'")"

expect_block_because \
  "artifact marker on issue close still needs transition evidence" \
  "$HOOK" \
  "$(payload "gh issue close 1164 --comment '## Pre-Mortem
Ticket: #1164
risk list'")" \
  "lacks required evidence"

expect_block_because \
  "approval review remains outside metadata-comment lane" \
  "$HOOK" \
  "$(payload "gh pr review 1170 --approve --body '## Senior review
Ticket: #1164
Looks done.'")" \
  "lacks required evidence"

expect_pass \
  "#1245 descriptive metadata: comment requires no artifact-format hint" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '$UNMARKED_BODY'")"

# Historical prose corpus (#1164): #1245 permits descriptive posts without changing state.
# Artifact completeness/identity belongs to its actual artifact consumer, not this word gate.
expect_pass \
  "#1245 descriptive metadata: laundering: unauxiliaried completion words and checkboxes is descriptive" \
  "$HOOK" \
  "$(payload "gh issue comment 1201 --body '## Investigation fact sheet
Ticket: #1201

Done — fix deployed to production. Lane complete.
- [x] Merged
- [x] Deployed'")"

expect_pass \
  "#1245 descriptive metadata: laundering: checkbox-only merge claim passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
- [x] Merged'")"

expect_pass \
  "#1245 descriptive metadata: laundering: a mid-line conditional word does not hide a claim" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
Status: shipped to prod before the release cut; no residual risk.'")"

expect_pass \
  "#1245 descriptive metadata: laundering: the heading line itself is scanned" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Senior review lane status: done #1164
Shipped.'")"

expect_pass \
  "#1245 descriptive metadata: laundering: a numbered list prefix does not hide a claim" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Junior task description
Ticket: #1164
1. Merged to develop.'")"

expect_pass \
  "a line opening with a conditional is not a claim" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: #1164
- If the PR is merged early, the gate will hold.
- Trigger condition: CI green on a stale head.'")"

expect_pass \
  "plural Design Notes heading is recognized" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Design Notes
Ticket: #1164
The blocker is the guard; we will re-run the gate after the fix.'")"

expect_pass \
  "#1245 descriptive metadata: Ticket: - is not a task reference" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '## Pre-Mortem
Ticket: -
- Blocker risk: we will re-run the gate later.'")"

expect_pass \
  "plans artifact with YAML front matter before the heading passes" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '---
ticket_refs:
  - siege-analytics/claude-configs-public#1164: comment pending
---
## Pre-Mortem
Ticket: siege-analytics/claude-configs-public#1164
- Blocker risk: the gate will reject the post; we will re-run the gate.'")"

expect_pass \
  "#1245 descriptive metadata: front matter does not hide a claim" \
  "$HOOK" \
  "$(payload "gh issue comment 1164 --body '---
status: done
---
## Pre-Mortem
Ticket: #1164'")"

out=$(printf '%s' "$(payload "gh issue comment 31 --body 'Status: complete. Lane done.'")" | bash "$HOOK" 2>&1)
if [[ "$out" == *"Ref: #1164"* ]]; then
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("plain status update gets no artifact hint")
  printf '  [FAIL] plain status update gets no artifact hint\n'
else
  _HARNESS_PASS=$((_HARNESS_PASS + 1)); printf '  [PASS] plain status update gets no artifact hint\n'
fi

# Keep the shell-suite entrypoint responsible for the actual JSON corpus.
if python3 "$ROOT/hooks/_test/metadata_comment_reporting.py"; then
  _HARNESS_PASS=$((_HARNESS_PASS + 1))
else
  _HARNESS_FAIL=$((_HARNESS_FAIL + 1)); _HARNESS_FAILED_NAMES+=("metadata comment corpus")
fi
report
