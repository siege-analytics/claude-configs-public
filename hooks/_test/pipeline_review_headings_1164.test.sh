#!/usr/bin/env bash
# #1164: pipeline_state.py (the writer of junior-senior-gate.json and
# artifacts-posted-gate.json) recognizes posted artifacts by their skill-defined
# headings, not only by keyword stems. Headings below are the exact ones from the
# siege_utilities #1846 comments the stem counter missed (6650647548, 6650305812).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; pass=0; fail=0
ok(){ echo "  PASS: $1"; pass=$((pass+1)); }; bad(){ echo "  FAIL: $1" >&2; fail=$((fail+1)); }
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
REPO="$TMP/repo"; mkdir -p "$REPO"; git -C "$REPO" init -q
FAKE="$TMP/fakebin"; mkdir -p "$FAKE"
printf '#!/bin/sh\ncat "%s"\n' "$TMP/comments.txt" > "$FAKE/gh"; chmod +x "$FAKE/gh"

# run_case NAME COMMENTS -> prints "junior senior investigate premortem" from the written signals
run_case(){
  local sid="s-$1" dir
  dir="$TMP/ws/sessions/$sid/tasks/t"; mkdir -p "$dir"
  printf '{"ticket": "o/r#1846", "sessionId": "%s", "repo_root": "%s", "scope_paths": ["%s"], "status": "implementing"}\n' "$sid" "$REPO" "$REPO" > "$dir/think-gate.json"
  python3 - "$2" > "$TMP/comments.txt" <<'PYBODY'
import json, sys
for body in sys.argv[1].split('\x1e'):
    print(json.dumps(body))
PYBODY
  CRAFT_SESSION_DIR="$TMP/ws/sessions/$sid" CRAFT_SESSION_ID="$sid" PATH="$FAKE:$PATH" \
    python3 "$ROOT/hooks/lib/pipeline_state.py" "$dir/think-gate.json" "$TMP/ws" "$ROOT/hooks/lib" >/dev/null 2>&1
  python3 - "$dir" <<'PY'
import json, sys, os
d = sys.argv[1]
def get(name, key):
    try:
        return str(json.load(open(os.path.join(d, name)))[key]).lower()
    except Exception:
        return 'absent'
print(get('junior-senior-gate.json', 'junior_found'), get('junior-senior-gate.json', 'senior_found'),
      get('artifacts-posted-gate.json', 'investigate_posted'), get('artifacts-posted-gate.json', 'premortem_posted'))
PY
}
expect(){ [[ "$2" == "$3" ]] && ok "$1" || bad "$1 (expected '$3', got '$2')"; }

got=$(run_case real $'## Junior task description -- R-1846-7 / R-1846-7a\n\nScope of the task on the connector public-edge redaction boundary.\n\n## Senior adversarial checklist -- R-1846-7 / R-1846-7a\n\nPoints checked: retry_after keeps the sentinel via the asymmetric rule.')
expect "real #1846 junior and senior headings are recognized" "${got% * *}" "true true"

got=$(run_case artifacts $'## Investigation Fact Sheet\nTicket: o/r#1846\nShape probed at file:line.\n\n## Pre-Mortem\nTicket: o/r#1846\nOne classified risk.')
expect "investigation and pre-mortem headings are recognized" "${got#* * }" "true true"

got=$(run_case unrelated $'## Notes\nNothing about review here.')
expect "unrelated heading recognizes nothing" "$got" "false false false false"

got=$(run_case empty $'## Junior task description\n\n## Senior adversarial checklist\n')
expect "headings without content do not count" "${got% * *}" "false false"

got=$(run_case prose $'See the Junior task description and Senior adversarial checklist below.')
expect "a prose mention without a heading does not count" "${got% * *}" "false false"

got=$(run_case junior $'## Junior Review\nActual task description content.')
expect "known Junior Review heading counts" "${got% * *}" "true false"
got=$(run_case fenced $'```markdown\n## Junior Review\nQuoted description.\n## Senior review\nQuoted checklist.\n```')
expect "fenced templates do not supply reviews" "${got% * *}" "false false"
got=$(run_case falseclose $'```markdown\n```not-a-closing-fence\n## Junior Review\nQuoted description.\n## Senior review\nQuoted checklist.\n```')
expect "closing fence with text does not expose code headings" "${got% * *}" "false false"
got=$(run_case separated $'## Junior Review\x1eContent in another comment.\n## Senior review\x1eAnother unrelated comment.')
expect "headings cannot borrow another comment content" "${got% * *}" "false false"
got=$(run_case unknown $'## Junior Plan\nNot a review artifact.')
expect "unknown Junior heading does not supply review" "${got% * *}" "false false"

echo "pipeline_review_headings_1164: $pass passed, $fail failed"; [[ $fail -eq 0 ]]
