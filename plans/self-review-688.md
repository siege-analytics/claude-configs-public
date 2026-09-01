---
ticket_refs:
  - siege-analytics/claude-configs-public#688: comment posted
  - siege-analytics/claude-configs-public#251: originating ticket for the guard, cited not modified
---

# Self-review: ticket #688 (ticket-propagation-guard ignores frontmatter on large artifacts)

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #688
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 688` -> `PASS: ticket 688 is fit for execution`
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/688 (inline `## Design` section, corrected by https://github.com/siege-analytics/claude-configs-public/issues/688#issuecomment-5489061994)
Pre-author-inventory: measured before authoring, recorded in `## Pre-author inventory` below
Investigate-artifact: the ticket body's `## Context` section is the investigation record; the defect was reproduced before the ticket was filed and the repro is quoted in it
Pre-mortem-artifact: NONE (see `## Pre-mortem exemption`)
Hostile-review-artifact: PENDING. `mcp__cross-review__review` was the intended mechanism and is unavailable (OpenAI returned `insufficient_quota` on all four models; no Anthropic or Google key is resolvable from 1Password). A sibling session is being spawned against this branch and will post findings to #688. This artifact is updated with the URL before push.
Project-contribution: restores a discipline guard that was silently degraded on exactly the artifacts it most needed to govern, and closes a bypass by which quoting the guard's own error message into a document disabled the guard for that document.

## Pre-author inventory

The diff authors executable code, so the shapes it was authored against were measured rather than assumed.

- **Harness API.** `hooks/_test/run_scenarios.sh` exports `expect_block`, `expect_pass` and `report`, and maintains `_HARNESS_PASS`, `_HARNESS_FAIL` and `_HARNESS_FAILED_NAMES`. Verified by reading the file: `expect_block` is exit 2, `expect_pass` is exit 0, and `report` exits non-zero if `_HARNESS_FAIL > 0`. Load-bearing because scenario (e) asserts on message *content*, which the harness cannot express, so it manipulates those three variables directly and must match their names and semantics exactly.
- **Guard input contract.** The guard reads a JSON payload on stdin and extracts `tool_input.file_path` and `tool_name` via `hooks/lib/extract-json.py`. For `tool_name == "Edit"` it reads content from disk, not from the payload. Verified by reading `hooks/write/ticket-propagation-guard.sh:52-68`. Load-bearing because the test fixtures are files on disk and the payload's `old_string`/`new_string` are never read.
- **Path filter.** Only `*/plans/*.md` and `*/docs/investigations/*.md` are in scope, and `scratch-*` basenames are exempt. Verified by reading `:42-48`. Load-bearing because the fixtures are written to `$TMP/plans/` for the guard to fire at all.
- **Pipe buffer.** 64KB on this darwin host, established by bisection: a 100-byte payload takes the frontmatter branch and a 200KB payload does not. The fix removes the dependency, so the exact value is not load-bearing; the test uses 200KB to stay clear of platform variation.
- **Existing compliant artifacts.** Three `plans/*.md` files carry `ticket_refs:` frontmatter, all under the buffer. Confirmed they pass both before and after, so no existing artifact depends on the old behaviour.

## Pre-mortem exemption

Reason: the change is a defect fix with a fully characterised mechanism and a mechanical falsifier, not a design with open choices. The pre-mortem question "what could make this wrong" has one substantive answer and it was tested directly: that the fix disables the guard rather than repairing it. That is checked by the paired non-compliant scenarios (b), (d) and (f), which must stay red-to-block in both the fixed and reverted states.
Evidence: with the fix reverted, the suite reports `3 passed, 3 failed`, and the three failures are exactly the three compliant/bypass scenarios. Scenarios (b) and (d) pass in both states.
Falsification: a reviewer finds a class of artifact that the new frontmatter split handles differently from the old one in a way no scenario covers. The nearest candidate is CRLF line endings, which `${CONTENT%%$'\n'*}` would leave a trailing `\r` on; this is stated as finding L-3 rather than claimed as handled.

## Peer review (mechanics, correctness, craft floor)

**writing-tests:1 (a test must be shown to fail without the fix).** This is the load-bearing shelf for this diff and it is what turned a wrong fix into a right one. The one-line change named in the ticket's `## Design` section made scenario (a) still fail. Had I asserted the fix and moved on -- the change matched the ticket, and `grep -c 'CONTENT" | head'` returned 0, so AC1 passed -- I would have shipped a guard that was still broken while claiming otherwise. Run-with-fix and run-with-fix-reverted are both quoted in `## Quantified claims`.

**writing-tests:4 (mock fidelity).** No mocks. The fixtures are real files on disk fed through the real hook via its real stdin contract, because the defect is size-dependent and any fixture that shortcut the content would not reproduce it. This is the case where fidelity is the whole test: a mocked `CONTENT` under the pipe buffer passes against the broken guard.

**writing-tests:7 (every AC names a falsifiable observable).** Four ACs, four observables: a `grep -c` returning 0, and three scenario outcomes with stated exit codes. AC3 is the one that could not be expressed as an exit code and is asserted on the blocked message's text instead, which is why scenario (e) bypasses the harness.

**writing-claims:2 and writing-claims:8 (countable claims cite their producing command).** Every count in this artifact, the commit message, the ticket comment and the PR body is reproduced under `## Quantified claims` with its command. The check bit: the ticket asserted the fix was one line, and the count of defect sites is three. That claim was published before it was tested and is corrected in the ticket rather than quietly restated.

**writing-claims:11 (class-completion claims enumerate the set).** "No reader in the guard exits early on a large variable" is a class-completion claim. It is backed by enumerating every pipeline in the file that is fed by `$CONTENT`, `$BODY` or `$FRONTMATTER` after the fix: exactly one remains, `FOUND_REFS=$(echo "$BODY" | { grep -oE ... || true; } | sort -u)` at `:91`, and it is safe because `grep -o` and `sort` both read their input to completion. Named rather than waved at.

**writing-rules:4 (a negative claim carries the same evidence chain).** The `## Pre-mortem exemption` above walks its reasoning rather than asserting doc-only triviality, and the CRLF gap is recorded as a finding instead of being covered by a blanket "handled".

**writing-prose:1 and writing-prose:3.** Scanned before asserting, and the scan corrected the claim I had drafted. The first version of this paragraph said the banned-codepoint scan returns 0 over both changed files; it returns 2, at `ticket-propagation-guard.sh:93` and `:115`, and both predate this diff (`git show origin/develop:hooks/write/ticket-propagation-guard.sh | grep -c` returns the same 2). `:115` is inside a hunk this diff re-authors, so it is fixed; `:93` is on an untouched line and is left alone rather than swept up. So: 0 introduced, 1 of 2 pre-existing fixed because the diff was already there, 1 left. The adverb scan returned one hit and it was rephrased; the scan now returns one match, which is this sentence naming the word it caught. No AI or assistant attribution appears in any file, the test output, the commit message or the PR body; the only matches for `claude` are occurrences of the repository's own name. The commit is authored by passing `-c user.name` / `-c user.email` on the command line.

## Lead review (adversarial pass)

*Software engineering.* Did the Junior fix the defect, or fix the symptom that was in front of them?

**Approach-fit verdict: fit, and it was not fit an hour ago.** The first attempt fixed the site the ticket named and stopped. That fix was *correct* and *insufficient*, which is the most dangerous combination available, because every check I had written pointed at it: the ticket said one line, AC1 passed, and the reported ref list visibly improved from four refs to one. Only the end-to-end scenario said no. The generalisable lesson is that I searched for `head` -- an instance of the defect -- rather than for *early-exit readers*, the class. `grep -q` is the same thing wearing a different name, and it was two lines below the line I was editing.

**Is the blast radius honestly stated?** Partly, and I want to be precise about which part I got for free. The SIGPIPE defect fails closed: the guard blocks work it should allow, which is annoying and visible. The frontmatter over-capture fails *open*: it allows work it should block. I did not go looking for the second one. I found it because the first fix did not work and I had to read the extraction to find out why. Had the one-line fix happened to work, I would have shipped a green suite with the bypass intact and written a confident self-review about it. That is worth stating plainly because the process did not catch the open failure -- a test failure did, incidentally.

**Does the test suite prove the fix, or prove the guard is off?** This is the question I would ask of someone else's guard PR, because "make the guard pass" is trivially achievable by making the guard useless. Every compliant scenario is paired with a non-compliant one at the same size: (a) with (b), (c) with (d). Both controls pass in the fixed and the reverted state, so the suite distinguishes the two hypotheses. Scenario (f) is the bypass, and it is the only scenario asserting a *new* block rather than a preserved one.

**Scope.** The ticket said one file, and it is one file plus a new test. The judgement call I made without asking is folding the `propagation-deferred` bypass into this ticket rather than splitting it. My reasoning is that the same three lines must be rewritten to fix the SIGPIPE regardless, so splitting would put two tickets in one `if` block; I have stated that in the ticket comment so a reviewer can disagree with it rather than discover it.

**The uncomfortable one.** I filed this ticket because the guard blocked *me*. I was mid-correction on an unrelated epic, the guard stood between me and a commit, and I diagnosed it. The incentive to conclude "the guard is broken" was strong and pointed exactly where I ended up. What protects the conclusion is that the reproduction is independent of my artifact -- a synthetic 200KB file in `/tmp` with no relation to #682 -- and that the bypass I found makes the guard *stricter*, which is against that incentive. But a reviewer should weigh that I am not a disinterested party here, and should check scenario (b), (d) and (f) specifically, since those are the ones a motivated author would have been tempted to leave out.

**Unrelated observation, not fixed here.** `hooks/_test/detect_ai_fingerprints.test.sh` fails on a clean `origin/develop` (verified by stashing this diff and re-running: exit 1). It is unrelated to this change and predates it. Not fixed here per one-at-a-time; it needs its own ticket and is flagged in the PR body.

## Quantified claims

- "three defect sites, not one" -- enumerated by reading: `echo "$CONTENT" | head -1 | grep -q` (early-exit reader `head`), `echo "$FRONTMATTER" | grep -qE '^ticket_refs:'` and `echo "$FRONTMATTER" | grep -qE '^propagation-deferred:'` (early-exit reader `grep -q`). All three are `set -o pipefail` pipelines whose writer is a large variable.
- "one remaining pipeline fed by a large variable, and it is safe" -- `grep -n 'echo "\$CONTENT"\|echo "\$BODY"\|echo "\$FRONTMATTER"' hooks/write/ticket-propagation-guard.sh` -> one hit, line 91. `grep -o` and `sort` are full-input readers.
- "AC1 holds" -- `grep -c 'CONTENT" | head' hooks/write/ticket-propagation-guard.sh` -> `0`.
- "6 passed, 0 failed with the fix" -- `bash hooks/_test/ticket_propagation_guard.test.sh` -> `Results: 6 passed, 0 failed`.
- "3 passed, 3 failed with the fix reverted" -- `git stash push hooks/write/ticket-propagation-guard.sh && bash hooks/_test/ticket_propagation_guard.test.sh` -> `Results: 3 passed, 3 failed`, failing scenarios `(a)`, `(e)`, `(f)`. Scenarios `(b)` and `(d)` pass in both states, which is the check that separates a repaired guard from a disabled one.
- "102KB of frontmatter from a 5-line frontmatter block" -- the old `FRONTMATTER=$(echo "$CONTENT" | sed -n '/^---$/,/^---$/p' | sed '1d;$d')` run against `plans/investigate-682-executable-path.md`; the captured region ran from the first `---` through the body's horizontal rules.
- "the bypass is real" -- a `plans/` document with no frontmatter, an unindented `propagation-deferred: <reason>` line inside a fenced block between two `---` rules, and an unpropagated ref in the body: old guard exit `0`, new guard exit `2`. The first fixture I built for this did **not** reproduce it, because I indented the line inside an indented code block and `^propagation-deferred:` is line-anchored. The claim was published in the ticket comment before that fixture was corrected; it survived, but it survived a check I ran after asserting it, which is the L-2 finding below.
- "detect_ai_fingerprints.test.sh fails on clean develop" -- `git stash -u && bash hooks/_test/detect_ai_fingerprints.test.sh; echo $?` -> `1`.
- "other hook tests unaffected" -- all five other `hooks/_test/*.test.sh` pass before and after.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L-1 | P0 | The fix named in the ticket's own Design section was insufficient. Applying it left scenario (a) failing, because the same defect class sits at two `grep -q` sites that a search for `head` does not find. Had the ticket's AC1 been the only check, this would have shipped as a fix that fixed nothing. | fixed -- all three sites rewritten to `awk`/parameter expansion, and the ticket's Design section corrected in public at issuecomment-5489061994 rather than silently restated. The generalisable rule is in the Lead review: search for the defect class, not the instance. |
| L-2 | P1 | I asserted the `propagation-deferred` bypass in a public ticket comment before I had reproduced it. When I then built the repro it did not fire, because my fixture indented the line. The claim was true and my basis for it at the time of writing was reading, not execution. | fixed -- reproduced with a corrected fixture (old exit 0, new exit 2) and pinned as scenario (f). Recorded here rather than elided because the artifact would otherwise read as though the repro preceded the claim. This is the same defect as #683's L-6: a claim carried from an internal belief and published before being checked. |
| L-3 | P2 | `${CONTENT%%$'\n'*}` leaves a trailing `\r` on CRLF input, so a CRLF artifact's first line would compare as `---\r` and take the no-frontmatter branch. The old `head -1 \| grep -q '^---$'` had the identical behaviour, so this is a preserved limitation, not a regression. | not fixed -- out of scope for a defect ticket, and no artifact in this repository uses CRLF. Named here so that "no reader exits early" is not read as "the split is now correct in all cases". Worth a follow-up ticket only if a CRLF artifact ever appears. |
| L-4 | P2 | The frontmatter over-capture was a fail-open bypass and I found it by accident, while debugging a fail-closed symptom. Nothing in my process was looking for it. | noted -- stated in the Lead review as the honest account. No mechanism is proposed here, because "audit every guard for fail-open paths" is a real piece of work and inventing it in this artifact would be scope creep. |
| L-5 | P3 | `hooks/_test/detect_ai_fingerprints.test.sh` fails on clean `origin/develop`, unrelated to this diff. | ticket -- flagged in the PR body for a separate ticket, not fixed here per one-at-a-time |
