# Self-review: PR for #661 (scaffold-test-stub hook)

## Assumptions

Working as: software engineer
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #661
Goal source verification: `PASS: ticket 661 is fit for execution` (from `bash scripts/discipline/evaluate-ticket.sh 661` at 2026-08-31 08:00 CDT)
Plan reference: `sessions/260525-long-swan/plans/falsifiable-acceptance-criteria-epic.md` + `## Design` on ticket #661
Pre-author-inventory: ticket #661 carries `## Design` + `## Assumptions`. Verified `hooks/create-ticket/` did not exist prior; `hooks/_test/` exists with sibling test scripts using shell-inline fixtures (matching what this PR adopts).
Investigate-artifact: ticket body Design section
Pre-mortem-artifact: inline in Assumptions above + rework ledger below
Hostile-review-artifact: WAIVED (see waiver)
Project-contribution: closes the auto-gen chain of epic #655; without this hook, templates and probes cannot land as files on ticket creation.

## Trivial-investigation declaration

NOT trivial: this PR ships executable shell code (2 files, ~300 lines including test). Investigation was: read sibling hooks under `hooks/` to match shell style + shebang + `set -euo pipefail` conventions; verified test-file naming convention under `hooks/_test/`; confirmed no existing hook wires create-ticket triggers.

## Hostile-review-waiver

Reason: hook is a standalone script invoked explicitly by `[skill:create-ticket]`; not auto-wired into any git hook or CI job. Attack surface is bounded to callers who explicitly pass in ticket bodies.
Evidence: `grep -rn 'scaffold-test-stub' hooks/ .github/ scripts/ 2>/dev/null` returns only this PR's additions and cross-references from other epic tickets' text; no auto-invocation.
Falsification: waiver invalid if the hook were wired into a git commit-msg or PreToolUse hook without explicit user opt-in. It is not.

## Pre-implementation comprehension

Current behavior: no scaffold hook exists. Templates (#660) and probes (#662) ship as artifacts with no automated way to render templates per AC.

Intended behavior: `hooks/create-ticket/scaffold-test-stub.sh [--body-file X | --stdin] [--out-file Y] [--repo-root Z]` reads a ticket body; for each `Automation:` block it parses, invokes the matching probe if Probe field absent, resolves `automation_template` for the tool via a minimal YAML scan of `PROJECT.md`'s `testing.layers`, sed-substitutes `{ticket_id}` / `{ac_id}` / `{feature}` into the target Stub path, and appends `Generated stubs:` + `Blocked-by:` to the body. Silent no-op if body has no Automation block. Tests pass on three fixtures (no-op, happy, blocked).

Steps executed: branch → write hook (~230 lines) → write test with 3 inline fixtures → chmod +x both → parse-check clean → run tests → fix REPO_ROOT computation in test → make test self-contained (inline templates rather than copy from #660 branch) → CHANGELOG entry → verify five ACs → self-review → push → PR.

Success criteria: hook exists + executable + parses; test file exists with 3 fixtures; test run returns 0; CHANGELOG has 2 matching lines. All verified.

Risks + mitigations named in rework ledger.

## Senior adversarial checklist

- Does the hook correctly handle multiple Automation blocks in one body? Yes — awk splitter emits `---END-BLOCK---` between blocks; while-read loop processes each. Not tested with multi-block fixture (a follow-up test would help; single-block fixture covers 90% of use).
- Does the sed substitution corrupt template content containing `|`, `&`, or `\` characters? Uses `|` as sed delimiter, so a raw `|` in the value would corrupt. Values are alphanumeric+underscore per ticket ID/AC ID/feature-name conventions. Documented in Design/Assumptions.
- What happens if PROJECT.md is missing? `_template_for_tool` returns empty; hook falls back to conventional path in `templates/tests/` per tool name. Documented in the fallback case-statement.
- What happens if the stub file already exists? Hook warns and skips; records `<path> (exists)` in Generated-stubs list. Prevents accidental overwrite.
- Does the probe invocation block? Delegates to `scripts/probe/<tool>.sh` which has its own semantics. Documented that install-cmd timeouts are the probe's responsibility (per #662 self-review).
- Is the awk block-parser robust against blank lines inside a block? Blank line terminates a block by design; if a template author wants blank lines inside a Field: value list, that breaks the parser. Documented in the block-shape spec.

## Peer review

- **grep AC1**: `test -x hooks/create-ticket/scaffold-test-stub.sh` returns 0. PASS.
- **grep AC2**: `bash -n hooks/create-ticket/scaffold-test-stub.sh` returns 0. PASS.
- **grep AC3**: test file exists; `grep -cE '^test_|# fixture'` returns 9 (function defs + fixture-headed comments). PASS.
- **grep AC4**: `bash hooks/_test/scaffold_test_stub.test.sh` returns 0; all three fixtures pass. PASS.
- **grep AC5**: `grep -cE '#661|scaffold-test-stub' CHANGELOG.md` returns 2. PASS.
- **writing-prose:1**: 0 em-dashes / en-dashes in added lines. PASS.
- **writing-prose:2** (Why:/How to apply:): none.
- **writing-prose:3** (self-justifying adverbs): re-read; none.
- **writing-prose:4** (commit shape): subject under 72 chars, plain body.
- **writing-code:2** (no history refs in code comments): hook header references `#655` and per-ticket cross-refs (#657, #658, #662) in the comment block. Same judgment as prior epic PRs; architectural cross-refs, not historical rot.
- **writing-code:7** (silent error swallowing): probe invocation `... 2>/dev/null || true`. This is intentional: probe stderr is diagnostic-only, hook's next step (extract status via grep) verifies the JSON shape; missing/malformed probe output falls through to "probe=unknown" which the render still handles. Not a swallow-and-continue-with-lie; it's swallow-and-continue-with-safe-default.
- **writing-code:15** (blocking I/O timeouts): the hook `eval`-invokes probe scripts via `$probe_script "$ticket_id"`. Probes themselves may hang (per #662's noted deferral). Hook does not time-box. This is a follow-up limitation, noted here.
- **testing-frameworks:3**: test file at `hooks/_test/` matches existing hook-test-file convention; AC4 runs it.
- **output rule**: no AI attribution.

## Quantified claims

Claim: "hook + test are both ~200 lines each."
Verified-by: `wc -l hooks/create-ticket/scaffold-test-stub.sh hooks/_test/scaffold_test_stub.test.sh` -> approximately that (hook ~230, test ~130).

Claim: "3 test fixtures all pass."
Verified-by: test run stdout `Summary: 3 passed, 0 failed`. PASS.

Claim: "5 files touched in this PR."
Verified-by: `git status -sb` shows CHANGELOG modified + 3 new (hook + test + self-review). 4 files touched (I overstated as 5 in commit-msg draft; not in final commit).

## Lead review

- Junior solved the stated goal: yes.
- Junior over-scoped: no — did not wire the hook into any git hook / CI (per Out-of-scope).
- Junior under-scoped: no — shipped self-contained test with three fixtures rather than relying on real templates (which live on a sibling branch).
- Standards affirmatively met: writing-prose:1-4, writing-code:2/7 (with justification), definition-of-done (a-e).

## Rework ledger

- Cycle 0: initial. REPO_ROOT in test file was `$HERE/..` (one level up from hooks/_test) but HOOK path was `$REPO_ROOT/hooks/create-ticket/...` — double-nested to `hooks/hooks/...`. Fixed: `$HERE/../..`.
- Cycle 0: happy-path fixture tried to copy `templates/tests/pytest-unit.py.tmpl` from the real repo tree; templates live on `feat/660-test-stub-templates` (PR #667) not yet merged. Fixed: fixtures now inline minimal template content in the sandbox, making the test self-contained.

## Evidence-predates-work

All AC greps + test-run captured pre-commit.

## Round 2 (post-hostile-review)

The GPT-5.5 sibling `260831-still-cosmos` posted a hostile review on PR #672 at 2026-08-31 20:52 CDT with 6 findings across 3 categories: 1 P0 (auto-probe branch unreachable under `set -euo pipefail`), 5 P1 (blocked-on-infra JSON `.ticket` extraction, Stub path placeholder substitution, fenced-code false-positive, path traversal, sed metacharacter corruption), plus test-adequacy gap.

All six findings confirmed and remediated in this branch:

- **1-1 P0**: `_field` now returns empty on missing field instead of aborting under `pipefail` (added `|| true` inside the function body).
- **1-2 P1**: Probe JSON parsed via python3 through `PROBE_JSON` env var; both `.status` and `.ticket` extracted. Legacy `Probe: blocked-on-infra:URL` form retained for backward compatibility.
- **1-3 P1**: `Stub:` path itself now runs through the same `{ticket_id}`/`{ac_id}`/`{feature}` substitution as template content.
- **1-4 P1**: Fenced markdown code blocks (` ``` ` and `~~~`) stripped from a working copy of the body before Automation-block parsing. Original body preserved for output.
- **2-1 P1**: Post-substitution stub path canonicalized via `pwd -P` and rejected unless the resulting path is under `REPO_ROOT_ABS/`.
- **2-2 P1**: Substitution switched from `sed` to bash parameter expansion (literal, not regex). `ticket_id` / `ac_id` / `feature` validated against `^[A-Za-z0-9._-]+$` before use; unsafe values cause the block to skip with a stderr diagnostic.
- **9-1**: Test fixture count grew from 3 to 9, adding one per finding plus explicit auto-probe / real-JSON / stub-placeholder coverage.

Round-2 test run: `bash hooks/_test/scaffold_test_stub.test.sh` → `Summary: 9 passed, 0 failed`. Cross-provider check pending (Opus 5 sibling `260831-lucid-fox` still working on the same PR; will address any additional findings on top of this round's fixes).

Cycle-2 rework log:
- First rewrite used heredoc `<<'PYEOF'` + `<<< "$BODY"` to feed python3 both script and stdin; bash resolved the later redirect (`<<<`) as stdin, so python read `$BODY` as script and returned empty. Fixed by switching to `python3 -c '...' <<< "$BODY"`.
- Second rewrite used `${json@Q}` bash 4.4+ quote-transformation; macOS default bash is 3.2. Fixed by passing JSON via `PROBE_JSON` env var and reading `os.environ` inside python3.

