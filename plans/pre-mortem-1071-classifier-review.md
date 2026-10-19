---
ticket_refs:
  - siege-analytics/claude-configs-public#1057: universal-mutation-gate blocks read-only commands
  - siege-analytics/claude-configs-public#1071: v3.5.69 release PR (CodeRabbit review findings)
---

## Pre-Mortem
Task: close the CodeRabbit findings on the #1057 read classifier (#1071 review) and the gate holes found while fixing them.
Ticket: siege-analytics/claude-configs-public#1057

### Tigers

#### Tiger 1: The classifier still proves a write is a read

Mitigation:
- Every CodeRabbit reproducer is a must-block case:
  - `rg --pre`;
  - wrapper flags;
  - `git grep -O`, `--upload-pack`, `reflog`;
  - `gh api -iX`/`-f` clusters;
  - abbreviated long options;
  - brace, `$` and glob expansion;
  - `file -C`;
  - `env`/`printenv`.
- Long options match any getopt abbreviation. Short-option clusters are scanned letter by letter.
- Expansion detection is quote-aware and runs per simple command.

#### Tiger 2: The legacy first-word safelist re-admits what the classifier rejects

The regex `SAFE_PATTERNS` match only a command's first word, so `cat f; bash evil.sh`, `env bash evil.sh` and `rg --pre sh .` passed with no gate before this change.

Mitigation:
- Classifier exit 3 (a definitively unsafe option) is treated as a mutation.
- Exit 4 (a compound command, or a guarded verb fed an expansion, that is not proven) skips `SAFE_PATTERNS`.

#### Tiger 3: Over-blocking ordinary reads, or blocking harder in the designing state

Mitigation:
- Exit 3 is reserved for named options. A known verb that is merely unproven (`git hash-object`) stays exit 1.
- A replay of 2,845 real session commands (old vs new gate, with no gate and with a designing gate) showed:
  - Designing state: no real command changed. 18 changes are commands cut off at 200 characters, each ending in a literal `2>/dev/n` write.
  - No gate: 194 newly allowed, all `cd …` compounds proven segment by segment. 37 newly blocked: environment dumps (`env | grep TOKEN`), code runs behind a leading `echo`/`cd`, and unproven segments.

#### Tiger 4: fd-prefixed redirects

`2>/tmp/x`, `1>f` and `&>f` were not detected as writes. This is pre-existing: the indicator skipped a digit or `&` before `>` to keep `2>&1` a read.

Mitigation:
- Strip `/dev/null` and `>&N` sinks, then treat any remaining fd-prefixed `>` as a write.
- Allow and block cases are covered both ways.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
