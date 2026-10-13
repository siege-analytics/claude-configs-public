#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TANDEM="$ROOT/skills/_tandem-agent-rules.md"
SESSION="$ROOT/skills/_session-coordination-rules.md"
grep -q 'tandem-agent:4\. Compatibility alias for session-coordination:9' "$TANDEM"
grep -q 'session-coordination:9\. Check collaborators after handoffs' "$SESSION"
grep -q 'resume or retire paused collaborators' "$TANDEM"
grep -q 'short batches' "$TANDEM"
grep -q 'rule_id = \["tandem-agent:4", "session-coordination:9", "work-item-ownership:2"\]' "$ROOT/skills/_coverage.md"
echo 'coordination_alias: PASS'
