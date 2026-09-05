---
propagation-deferred: self-review artifact for the PR that will link this ticket; propagation is via the PR body, not via separate comments on referenced tickets
---

# Self-review: PR for #676 (#668 P0-1 sed -> python3 in _probe_file_infra_ticket)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #676
Goal source verification: `PASS: ticket 676 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 676` at 2026-08-31 22:00 CDT)
Plan reference: ticket #676 `## Design` section + noble-pulsar review of PR #668 (https://github.com/siege-analytics/claude-configs-public/pull/668#issuecomment-5487790658) finding P0-1
Pre-author-inventory: ticket #676 carries `## Design` + `## Assumptions`. Verified `_probe_file_infra_ticket` runs sed with three metacharacter-vulnerable placeholders (install_commands, blocking_tickets, tool) and one embedded shell substitution (`$(basename "$repo_root")`). Verified two shipped install commands (playwright.sh:33, k6.sh:16) actively trigger the bug in-tree.
Investigate-artifact: TRIVIAL (see declaration)
Pre-mortem-artifact: inline in this review under "Senior checklist"
Hostile-review-artifact: this PR IS the response to noble-pulsar's hostile review; not additionally reviewed pre-merge
Project-contribution: closes 1 of 5 P0 findings on epic #655's tool-availability-probe (#668). Other 4 P0s tracked in #677 #678 #679 #680; will land in separate PRs per user directive "isolate + one-at-a-time."

## Trivial-investigation declaration

Reason: single-function surgical edit in one shell file + one new self-contained test file. Function scope is 37 lines (86-122); the change is scoped to the body-render block (101-110). No consumer changes; no other callers of `_probe_file_infra_ticket`.
Evidence: `git diff --stat` shows 2 files (`scripts/probe/_common.sh` modified, `scripts/probe/_test_probe_common.sh` added). No other file touched.
Falsification: not trivial if the change affects any caller of `_probe_file_infra_ticket` outside the body-render block, or if it introduces a new dependency. Neither holds (python3 is already a dep).

## Pre-implementation comprehension

Current behavior: `_probe_file_infra_ticket` renders the infra-ticket body by running sed with 7 `-e` substitutions. Placeholders replaced from ticket-body-derived values (tool, install_cmd, blocking, layer) and computed values (repo, requester). Sed uses `|` as delimiter. Any `&` in a replacement value expands to the whole match; any `|` in a replacement value terminates the s-command. Under `set -euo pipefail` a sed abort kills the script.

Intended behavior: after this PR, `_probe_file_infra_ticket` renders the body via a python3 one-liner (`str.replace` per placeholder). Values pass through the environment; no shell/sed metacharacter interpretation on values.

Steps executed:
1. Branch `fix/676-sed-substitution-in-probe` off `origin/feat/662-tool-availability-probe`.
2. Restored ticket #676 body (was accidentally wiped by an earlier bad-sed pipe when I tried to add a `Goal` section via `gh issue edit --body "$(... | sed ...)"` — the sed pipe failed and produced empty output, which gh then wrote as the new body). Rewrote body full-length in one shot.
3. Re-ran `evaluate-ticket.sh 676` -> PASS.
4. Edited `_common.sh:101-110`: replaced the sed block with a python3 `str.replace` block, passing all seven placeholder values through the environment.
5. Wrote `scripts/probe/_test_probe_common.sh` with 4 fixtures (one per AC).
6. Ran test suite: `Summary: 4 passed, 0 failed` after one cycle of rework (AC4 initially failed on a trailing newline the gh stub's `echo` added; fixed by switching stub to `printf '%s'`).

Success criteria: 4 ACs pass. Verified in Peer review below.

Risks:
- (a) A future placeholder addition in `templates/infra-ticket-tool-install.md` would need a matching env-var mapping in the python block. Documented in the code comment.
- (b) The python3 dep is already required elsewhere in `_common.sh` (line 148 for JSON parsing); this change does not add a new dep.
- (c) macOS bash 3.2 vs newer bash: no bash-4+ syntax used.

## Senior adversarial checklist (embedded pre-mortem)

- What if a placeholder value contains a null byte? `str.replace` is byte-safe; no issue.
- What if `TEMPLATE_PATH` env var is unset (i.e. path expansion goes wrong)? python3 open() raises FileNotFoundError; script aborts under set -e; no silent success. Fine.
- What if the template file itself contains `{FOO}` placeholders we don't know about? The python loop only replaces the 7 known keys; unknown placeholders pass through literally. Same behavior as sed. Consumer (infra-ticket reader) would see the literal placeholder — better than corruption.
- What if a placeholder value is empty string (e.g. missing $CRAFT_AGENT_SESSION_DIR default fires)? The environment mapping uses `.get(k, "")` fallback, so it renders as an empty string. Same as sed with empty replacement. Fine.
- What if python3 crashes on a specific input? `body=$(...)` under `set -e` aborts the script. Fail-loud, not fail-silent. Fine.
- Is there a race between the python subprocess env inheritance and later gh call? No — sequential, `body=$(...)` completes before `url=$(gh ...)`.

## Peer review

- **grep AC1**: `awk '/^_probe_file_infra_ticket/,/^}/' scripts/probe/_common.sh | grep -c '^[[:space:]]*sed '` -> 0. PASS.
- **AC2 fixture** (playwright &&): test output `PASS: AC2: playwright && install command rendered cleanly`. Body contains literal `npm install -D @playwright/test && npx playwright install --with-deps`; no `{install_commands}` leftover.
- **AC3 fixture** (k6 |): test output `PASS: AC3: k6 pipe-bearing install command rendered without abort`. Probe exits 78 with valid JSON.
- **AC4 fixture** (byte-identical on plain input): test output `PASS: AC4: python3 render byte-identical to legacy sed render on plain input`. `diff` returns 0.
- **writing-prose:1**: 0 em-dashes / en-dashes in added lines (grep verified).
- **writing-prose:2** (Why:/How to apply:): none.
- **writing-prose:3** (self-justifying adverbs): re-read; none.
- **writing-prose:4** (commit shape): subject under 72 chars, plain body.
- **writing-code:2**: code comment names `#676` and `P0-1` -- architectural cross-ref to the driving ticket, not historical PR/sprint rot. Same judgment as prior epic PRs.
- **writing-code:5** (no hypothetical code): python3 is a real dep on this branch, verified by `grep -n 'python3' scripts/probe/_common.sh` returning matches at both line 148 (JSON parse) and the new render.
- **writing-code:15** (blocking I/O timeouts): python3 subprocess is bounded by its own operation; no external I/O. No timeout needed.
- **testing-frameworks:3**: test file at `scripts/probe/_test_probe_common.sh` matches existing convention (`hooks/_test/*.test.sh`). AC1-4 verified by same-turn test run.
- **output rule**: no AI attribution.

## Quantified claims

Claim: "4 ACs pass."
Verified-by: test output `Summary: 4 passed, 0 failed`.

Claim: "2 files touched."
Verified-by: `git status -sb` shows 1 modified + 1 added.

Claim: "sed block removed from `_probe_file_infra_ticket`."
Verified-by: awk-extract + grep -c returned 0.

## Lead review

- Junior solved the stated goal: yes (P0-1 addressed).
- Junior over-scoped: no -- did not touch the other 4 P0s (tracked in #677-#680) or any P1/P2. Per user directive "isolate + one-at-a-time."
- Junior under-scoped: no -- 4 ACs cover positive path, negative path, and equivalence-to-legacy on the affected function.
- Standards affirmatively met: writing-prose:1-4, writing-code:2/5/15, definition-of-done (a-e satisfied via ticket + PR).

## Rework ledger

- Cycle 0: initial fix + tests. AC4 failed on trailing newline because gh stub used `echo` (adds newline) while the python3 render doesn't. Fixed stub to `printf '%s'`. Not a fix in the production code; test-only.
- Ticket-body recovery: the ticket #676 body was accidentally wiped by an earlier bad sed pipe in `gh issue edit --body "$(... | sed ...)"`. When the sed pipe fails (macOS sed doesn't accept `\n` in replacement), it outputs empty and the gh edit sets body to "". Recovered by rewriting the body full-length. Lesson: verify pipe outputs before feeding them to destructive gh edits.

## Evidence-predates-work

All ACs verified against branch tip via `bash scripts/probe/_test_probe_common.sh` before commit. Same-turn: recorded in session `260525-long-swan/session.jsonl` prior to this artifact.
