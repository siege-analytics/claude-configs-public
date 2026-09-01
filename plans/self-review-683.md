---
ticket_refs:
  - siege-analytics/claude-configs-public#683: comment posted
  - siege-analytics/claude-configs-public#682: comment pending
---

# Self-review: ticket #683 (investigate the epic #682 executable path)

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #683 (epic #682)
Goal source verification: `PASS: ticket 683 is fit for execution`
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/682 (epic body carries the 24-item functions checklist this fact sheet is measured against)
Pre-author-inventory: NONE (see `## Trivial-against-state declaration`)
Trivial-against-state: this diff authors no runtime artifact; see the declaration block below
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/683#issuecomment-5488627863
Pre-mortem-artifact: TRIVIAL (see `## Trivial-investigation declaration`)
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/684 (rounds 1 and 2, GPT-5.5 sibling `260831-strong-nova`; 8 findings total, 2 S1, both rounds Block; all eight accepted and remediated -- see `## Hostile-review round 1` and `## Hostile-review round 2`)
Project-contribution: establishes the falsifiable baseline the epic #682 rewrite is measured against -- which of PR #668's and PR #672's findings are still live at the branch being replaced, what is newly broken, and which existing test fixtures actively protect defects. Without this, "the Python rewrite passes the same tests" would have been an acceptance signal, and it is not one.

## Trivial-against-state declaration

Reason: none of the five authoring-against-state contact categories is engaged. The diff authors no runtime artifact -- it adds two prose documents under `plans/`. Data-shape: no schema, query, or dataframe is written or read. Config-state: no config file is authored or consumed; the artifact *reports* that `PROJECT.md` is absent rather than authoring against it. Topology: no service, path, or dependency wiring changes. Plan-shape: no execution plan, DAG, or pipeline definition is produced. Version-resolution: no dependency, pin, or lockfile is touched.
Evidence: `git diff --stat HEAD~2 --name-only` -> `plans/investigate-682-executable-path.md`, `plans/self-review-683.md`. Both `.md`, both new, both under `plans/`. No file with a runtime extension (`.py`, `.sh`, `.json`, `.yaml`, `.toml`, `.lock`) appears in the diff, and no file under `hooks/`, `skills/`, `scripts/`, or `templates/` is modified.
Falsification: a reviewer identifies a runtime consumer that reads either of these two files and changes behaviour as a result. The session-scoped `investigate-gate-claude-configs-public.json` written alongside this work *is* read by the guard hooks, and it sits outside the repo and outside this diff; if that file were committed here, this declaration would be wrong and a real pre-author inventory of the guard's schema would be required.

## Trivial-investigation declaration

Category: doc-only
Cannot produce error: this ticket's entire deliverable is the investigation artifact itself; a pre-mortem of "what could go wrong when we write a fact sheet" would surface nothing the artifact's own falsification section does not already carry, and the epic sequences a dedicated pre-mortem ticket as the next unit of work against the actual rewrite.
Evidence: `git diff --stat HEAD~1 --name-only` -> `plans/investigate-682-executable-path.md`, `plans/self-review-683.md` -- two new files under `plans/`, no source, hook, skill, or template file touched.
Falsification: the pre-mortem ticket that follows surfaces a risk class that would have changed how the fact sheet was scoped -- e.g. it establishes that a whole file in the executable path was omitted from the #682 checklist and therefore from this inventory.

## Hostile-review-waiver

Reason: hostile review by a sibling on a different model is required by standing order and is being obtained, but the PR does not exist yet at push time, so no review artifact can be cited. This waiver covers the push only, not the merge.
Scope: `plans/investigate-682-executable-path.md`, `plans/self-review-683.md`. Both `.md`; the diff touches no file with an executable extension.
Compensating-control: all four ACs verified mechanically rather than by reading (scripted header enumeration, per-subheader grep counts, `json.loads` on the extracted fence, `mermaid_validate` on both diagrams), plus a citation-resolution pass over all 33 `file:line` pairs in the `verifiedShapes` block. A hostile-review sibling is spawned immediately after the PR is opened and its findings are remediated before merge; the `Hostile-review-artifact:` field is updated to the resulting artifact at that point.

## Peer review (mechanics, correctness, craft floor)

**writing-claims:8 (specific counts cite their producing command).** Every count in the commit messages, the PR body, and this artifact is reproduced under `## Quantified claims` with the command that produced it. Checked: no bare number appears in either document without a command beside it.

**writing-claims:2 (countable claims need the falsifying grep) and writing-claims:11 (class-completion claims enumerate the set).** "All 24 units on the #682 functions checklist" is a class-completion claim. It is backed by a script that enumerates the 24 names from the epic body and asserts `grep -qx "### <name>"` for each, printing OK/MISS per name, rather than by `grep -c '^### '`. The bare count is 29 and would have been wrong; the enumeration is 24/24 with 0 missing. Same treatment for the citations: the check resolves each path and line rather than counting entries. 55 after the round-1 remediation, 33 at first push.

**writing-tests:7 (every AC names a falsifiable observable).** No tests are added or changed by this diff, which is correct for an investigation ticket. The shelf still bites in the other direction: the artifact records that `probe_run` has zero coverage (F-N20) and that five of six probe wrappers have zero coverage, and it records which five existing fixtures pass while a new finding is live underneath them. Fixing any of that here would have been scope creep into the implementation tickets.

**writing-tests:4 (mock fidelity).** Relevant as a finding, not as a diff property: `scripts/probe/_test_probe_common.sh` writes its own private copy of `templates/infra-ticket-tool-install.md` rather than reading the shipped file (F-N19), which is a mock-fidelity failure and is the mechanism by which F-N17 survived. Recorded in the artifact.

**writing-rules:4 (a "this does not apply" claim carries the same evidence chain as any other).** Both declarations in this artifact walk their categories individually -- the `Trivial-against-state` block addresses each of the five contact categories by name rather than asserting the negative once, and each declaration states a falsifier that would prove the skip wrong.

**writing-prose:1 and writing-prose:3.** Failed on first pass and fixed. A scan of the two documents found 156 em-dashes, 3 en-dashes, 46 right-arrows and 5 ellipses in the fact sheet, and 29 em-dashes and 14 right-arrows in this artifact -- 253 banned characters across a diff whose entire subject is mechanical checkability. All replaced with ASCII (`--`, `-`, `->`, `...`); a re-scan of both files and of the gate JSON reports clean. Self-justifying adverbs ("deliberately") removed. No AI or assistant attribution appears in either file or in any commit message, and every commit is authored via explicit `-c user.name` / `-c user.email`.

**Citation resolution.** Ran a resolution pass over the `verifiedShapes` block: for each `file:line`, assert the file exists and the line number is within the file's length. 33 citations at first push, 0 unresolved; re-run after the round-1 remediation, 55 citations, 0 unresolved. The pass caught two wrong line numbers written from earlier-in-session notes (`_field` cited at `:133`, a comment line, actually `:135`; the infra-ticket verification block at `:35`, actually `:34`). Both corrected. Without the pass, both would have shipped, and both are exactly what `investigate-gate-guard.sh`'s Level 2 spot-check exists to catch.

**AC literalism.** AC2 is falsifiable by grep for eight subheaders. Fifteen entries used `- **Assumptions to verify at rewrite time:**` and two used a combined `- **Callers / Callees:**`, all of which read as compliant and are not. Normalised; the counts moved 9 to 24 and 22 to 24. A reader-satisfies-it standard is not an AC-satisfies-it standard.

## Lead review (adversarial pass)

*Software engineering.* Did the Junior actually solve #683, or produce a document that looks like a solution?

**Approach-fit verdict: fit, with one soft spot.** The ticket asks for an inventory, and the temptation on an inventory ticket is to paraphrase the source back at the reader -- 24 entries of "this function does what its name says". That would satisfy AC1 and AC2 while being worthless to the rewrite. The check I applied is whether each entry produces a *decision* for the rewrite, and the load-bearing ones do: F-N13 says the npx wrappers need an injectable detector; F-N14 says `eval` must become an argv list; F-N20 says `probe_run` is the first unit to cover. The soft spot is that a handful of the P2 entries (F-N3 changelog drift, F-N7 inert instruction, F-N16 layer-token spellings) are true but produce no rewrite decision on their own. They are kept because they are cheap to carry and because F-N16 in particular becomes load-bearing the moment the layer token is made a shared constant.

**Did each finding close a class or defer it?** All 28 defer -- this ticket fixes nothing by design. The classification that determines whether the rewrite closes them by construction or one at a time (H1) is explicitly named as the *design ticket's* first deliverable, not smuggled in here. Deferring is correct; deferring silently would not be, which is why the H1 falsification criterion states the threshold (structural ≥ 50%) in advance rather than after the classification is done.

**Blast radius: zero at push, load-bearing at merge.** Two new files under `plans/`; nothing executes, nothing deploys, no `hooks/` or `skills/` change so no `bin/build.py --deploy` is required. The real blast radius is downstream: every subsequent ticket in epic #682 is scoped against this document, so a wrong severity here misroutes implementation effort. That is the argument for the hostile review, not against it.

**Sequencing assumption that has to hold.** That the epic integration branch -- the first branch on which the hook (`feat/661`) and the probes (`feat/662` + `fix/676`) coexist -- is the correct baseline. If the epic instead rebases onto whatever `develop` looks like at implementation time, findings dispositioned LIVE here may have been fixed in the interim and findings dispositioned REMEDIATED may have regressed. Every disposition in this artifact is pinned to `epic/682-python-executable-path`, and re-verification is required if that base moves.

**Affirmative standard: does the artifact make its own claims falsifiable?** Yes for the mechanical ones (four ACs, 55 citations, two suite runs -- all with commands). Partially for the severity assignments, which are argued but not independently checked. That gap is stated below rather than left for a reviewer to find.

## Hostile-review round 1

Reviewer: sibling session `260831-strong-nova`, GPT-5.5 (`chatgpt-plus`), thinking level high, pinned to `4a81bf5`. Artifact: the PR #684 comment thread. Recommendation: **Block**. Six findings, two S1, all accepted; none disputed.

The dispositions are tabulated in the fact sheet's `## Hostile-review remediation (PR #684, round 1)` section rather than duplicated here. What belongs in the self-review is what the review says about my checks.

**The compensating control I claimed was insufficient, and the reviewer proved it.** The `## Hostile-review-waiver` above offers "all four ACs verified mechanically, plus a citation-resolution pass over all 33 `file:line` pairs" as the thing standing in for a human reviewer at push time. Finding 1-2 is a claim whose citation resolved perfectly and whose content was false. A resolution pass answers "does this line exist"; it cannot answer "does this line support the sentence attached to it". I described the pass in a way that implied the stronger guarantee. That is the finding I would have most wanted to catch myself and did not.

**The count discipline section was self-certifying.** `writing-claims:8` asserts every count cites its producing command. The single highest-value count in the PR -- the severity split -- was carried from prose to prose without ever being produced by a command, and the section asserting compliance did not check itself. Finding 1-1 is arithmetic: 6 + 13 + 7 = 26, not 25. It was visible without running anything.

**Two live defects were present in the source and recorded as something weaker than findings.** F-N26 was written into the `_safe_value` entry as an assumption to verify at rewrite time; it is a reproducible `SyntaxError` in generated code and should have been a finding. F-N27 was adjacent to F-N16 and got absorbed into it; it is a data-loss boundary, not a spelling inconsistency. Both re-verified independently on this branch before acceptance rather than taken on the reviewer's word.

**One severity was inflated and the reviewer did the work to show it.** F-N14 was P0 on source attestation with no executed repro, which L-3 above predicted would be the primary target. The reviewer ran the path with `uname` stubbed to Linux and no `apt-get`, got `rc=78`, and argued that the executed command name is fixed by the script rather than ticket-controlled. Downgraded to P1. L-3 is therefore resolved rather than open: the prediction was correct and the mechanism worked.

## Hostile-review round 2

Same reviewer, re-run against `cd91ccb` on the two narrow targets I asked for rather than a full re-read. Recommendation: **Block**. Two findings, both accepted, both re-verified here before acceptance.

**The round-1 corrections held under an independent re-derivation.** The reviewer recounted the table (28 rows, `4 P0, 17 P1, 7 P2`), recounted the citations (55 entries, 0 unresolved), re-read the four restated contract sites against `scripts/probe/_common.sh:31-34` and `hooks/create-ticket/scaffold-test-stub.sh:215-228`, and re-ran both suites. It also reproduced F-N11 in a temp repo, which was the first of the two targets: a probe writing to stderr and exiting 78 produced `rc=0`, `stub_exists=yes`, `stderr_len=0` at the hook. F-N11 holds at P0.

**The second target produced the finding.** F-N22 was P0 and is a coverage gap whose entire consequence is that F-N1 is invisible. Rating both P0 counted one blast radius twice. I verified this by reading `hooks/_test/scaffold_test_stub.test.sh:276-301` and found something the reviewer also caught and I had not: the fixture creates `$sibling` with `mktemp -d` at `:283` before invoking the hook, so it could not detect the escaped directory even if it asserted on one. The finding is not just that the assertion is missing; the fixture's own setup makes the assertion impossible. Downgraded to P1. Totals are now `3 P0, 18 P1, 7 P2`.

**The S3 is the same class as round 1's S1.** The `verifiedShapes` evidence label for H2 read "F-N5 and F-N22 repros". F-N5 has a byte-level repro, F-N1 has a directory-creation repro, F-N22 has neither. I grepped the artifact for an F-N22 repro transcript and there is none. Like round-1 finding 1-2, this survives a citation-resolution pass and a count audit, because it is a claim about what was *run*, and no check in this artifact examines its own evidence labels.

**What I am taking from two rounds.** Three of the eight findings are severity assignments: 1-1 on the totals, 2-3 on F-N14, 9-1 on F-N22. That is not three independent mistakes, it is one missing artifact. There was no written severity rubric, so an assignment could not be checked against anything, by the reviewer or by me. A rubric is now in the fact sheet as `## Severity rubric`, with the two rules the corrections imply stated as rules: a coverage gap does not inherit the severity of the defect it hides, and severity follows blast radius rather than how load-bearing a finding is for the document's argument. F-N22 was rated P0 partly because it is the best single illustration of this artifact's central thesis. That is an emphasis judgement wearing a severity label, and it is the honest description of what I did.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L-1 | P1 | Two `verifiedShapes` citations pointed at wrong lines (`_field` at `:133`, a comment; infra template at `:35`). Fabricated-adjacent citations are exactly what the guard's spot-check exists to catch. | fixed -- corrected to `:135` and `:34`; added a resolution pass over all citations (33 then, 55 after round-1 remediation), 0 unresolved |
| L-2 | P1 | AC2 failed a literal grep on 17 of 24 entries (`Assumptions to verify at rewrite time`, combined `Callers / Callees`) while reading as compliant. | fixed -- normalised to the eight exact subheaders; all eight now count 24 |
| L-3 | P2 | Severity assignment for the new findings has had no second reader; F-N13 and F-N14 are P0 on source attestation with no executed repro. | resolved -- the sibling reproduced both. F-N13 confirmed P0; F-N14 downgraded to P1 with a repro (`rc=78`, `blocked-on-infra`) and the argument that the executed command name is script-fixed rather than ticket-controlled. The artifact is amended accordingly. |
| L-4 | P2 | The `allow` and `prompt` policy branches -- which contain every dangerous operation, including a `sudo apt` chain -- were attested from source and never observed, because this repo has no `PROJECT.md` so `_probe_resolve_policy` always returns `block`. | noted in artifact and recorded as `SKIPPED` with reason in the gate; drives the recommendation that `probe_run` is the first unit to get coverage |
| L-8 | P1 | Severities were assigned across 28 findings with no written rubric, so no assignment could be checked against a standard. Three of the eight hostile-review findings across two rounds are severity corrections (1-1, 2-3, 9-1), and F-N22 in particular was rated P0 because it best illustrates the artifact's thesis rather than because of its blast radius. | fixed -- `## Severity rubric` added to the fact sheet with P0/P1/P2 defined by blast radius and two derived rules: a coverage gap does not inherit the severity of the defect it hides, and severity is not an emphasis axis. Every assignment in the tables is restated against it. Found by the reviewer three times before I recognised it as one cause. |
| L-5 | P3 | The 15-fixture -> finding mapping table is my reading of each fixture, not instrumented. A fixture marked "--" could also be masking a defect. | noted -- the rewrite's first act on the hook suite is to add byte-exact assertions, which would surface any additional masking |
| L-6 | P0 | The `verifiedShapes` block claimed the probe/hook contract is "consumed by regex not by a parser" with "no json module on either side". `_parse_probe_json:215` shells to `python3` and calls `json.loads`. The citation resolved to a real line while contradicting it, so the resolution pass I ran as a compensating control could not have caught it. | fixed -- all four sites restated to the real mechanism (three string-building producers, one `json.loads` consumer with a bare `except` at `:224` degrading failures to empty strings). Found by the PR #684 hostile review (1-2), not by me. |
| L-7 | P0 | The severity totals line said `6 P0, 13 P1, 7 P2` over "25 new findings". 6+13+7 is 26, and the table's actual split was `5 P0, 14 P1, 7 P2`. The claim was in the artifact, this self-review, and the PR body, and my `writing-claims:8` section asserted every count cites its producing command. | fixed -- unit of analysis stated before the count, totals produced by an inline command, corrected in all three places. Found by the PR #684 hostile review (1-1). |

No P1 rows remain unresolved. L-6 and L-7 are recorded at P0 because both were live in a merged-candidate artifact and both were found by the reviewer rather than by the checks I claimed as compensating controls.

## Quantified claims

- "894 lines" (commit-time figure; the file is now 896 after the AC2 normalisation added two split `Callers`/`Callees` lines) -- `wc -l < plans/investigate-682-executable-path.md` -> `896`
- "all 24 units on the #682 functions checklist" -- scripted `grep -qx "### <name>"` over the 24 names from the epic body -> `missing: 0` (24 OK, 0 MISS)
- "24 for each of the 8 subheaders" -- `for h in File Signature Callers Callees "Side effects" "Known failures" "Test coverage" Assumptions; do grep -c "^- \*\*$h:\*\*" ...; done` -> `24 24 24 24 24 24 24 24`
- "the embedded verifiedShapes block parses" -- extract the single json fence, `json.loads` -> `json fences found: 1` / `verifiedShapes blocks that parse: 1`
- "two validated mermaid diagrams" -- `grep -c '^```mermaid'` -> `2`; both submitted to `mermaid_validate` with `render: true` -> `{"valid": true}` twice
- "55 citations, 0 unresolved" -- walk the `citations` arrays, assert file exists and line ≤ file length -> `citations: 55  unresolved: 0`. Resolution is not the same as support: L-6 records that one resolved citation contradicted the claim attached to it
- "24 from #668, 5 from #672 remain live" -- counted from the live-defect ledger rows in the artifact, which were dispositioned individually by same-turn repro earlier in this session
- "28 new findings (3 P0, 18 P1, 7 P2)" -- `grep -oE '^\| F-N[0-9]+b? \| P[012]' plans/investigate-682-executable-path.md | awk '{print $4}' | sort | uniq -c` -> `3 P0, 18 P1, 7 P2` over 28 rows. Three revisions: "25 new findings (6 P0, 13 P1, 7 P2)" at first push, wrong in both halves and not self-summing (L-7); `4 P0, 17 P1, 7 P2` after round 1 downgraded F-N14; the current figure after round 2 downgraded F-N22. The P0 set is F-N1, F-N11, F-N13. Three of the eight review findings across both rounds are severity assignments, which is L-8
- "4 passed, 0 failed" -- `bash scripts/probe/_test_probe_common.sh` -> `Summary: 4 passed, 0 failed`
- "15 passed, 0 failed" -- `bash hooks/_test/scaffold_test_stub.test.sh` -> `Summary: 15 passed, 0 failed`
- "19 green fixtures" (commit message) -- 4 + 15 from the two runs above
- "10 findings, 8 verifiedShapes, 4 skipped in the gate file" -- `json.load` on `investigate-gate-claude-configs-public.json` -> `findings: 10 verifiedShapes: 8 skipped: 4`, and a schema check against the guard's stated rules (layer coverage, PROBED/ATTESTED/SKIPPED completeness, skipReason length) -> `problems: 0`

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Two wrong `file:line` citations (L-1) | wrote line numbers from earlier-in-session notes instead of re-resolving them against the checkout | one `sed -n` loop over 17 pairs, ~10s | rewrite two chunk files and run a `python3` string-replace pass over the assembled artifact, ~4 min | ~24x |
| AC2 grep failure on 17 entries (L-2) | wrote the subheaders for readability without checking them against the AC's literal grep | one `grep -c` loop over 8 patterns, ~5s | normalise 17 entries via a scripted replace and re-split two combined lines, ~5 min | ~60x |
| Push blocked by `hooks/git/self-review.sh` for missing `## Assumptions` / `## Peer review` / `## Lead review` | wrote the self-review artifact from the standing-order trailer requirements without reading `skills/self-review/SKILL.md` first | reading `## Artifact format`, ~30s | full rewrite of the artifact, ~8 min | ~16x |
| Push blocked by `hooks/git/self-review.sh` for `Pre-author-inventory: NONE` without a `Trivial-against-state:` declaration | treated NONE as a self-evident value rather than a claim requiring the same evidence chain as any other | reading the field's "When NONE is acceptable" paragraph, ~20s | write a declaration walking all five contact categories, ~4 min | ~12x |
| Push blocked by `hooks/git/self-review.sh` for a `## Peer review` section citing no shelf | wrote the peer review as prose headings ("writing-claims.") without the rule numbers the section is checked for | reading the hook's stated expectation, ~15s | rewrite the section with per-rule citations, ~6 min | ~24x |
| 253 writing-prose:1 banned characters across both documents, self-certified as compliant before being scanned | asserted prose-rule compliance in the artifact instead of running the scan first | one `python3` character count over two files, ~5s | scripted replacement plus re-verification of all four ACs and the JSON fence, ~4 min | ~48x |
| Write blocked by `ticket-propagation-guard` for missing `ticket_refs:` frontmatter | pasted full issue URLs into the artifact without adding the propagation metadata the guard requires | reading the guard's resolution block, ~15s | re-issue the Write with frontmatter, ~1 min | ~4x |
| Octopus merge failure building the epic branch | assumed `git merge A B` would handle a CHANGELOG conflict | knowing octopus refuses any conflict, ~0 | sequential merges with a Python union-resolver per conflict, ~6 min | high |
| First #668 P1-4 repro inconclusive | used `Tool: pytest`, which is installed, so the absent branch was never reached | checking `command -v pytest` before choosing the repro tool, ~2s | re-run with `great-expectations`, ~2 min | ~60x |
| Severity totals wrong in three places (L-7), found by the hostile reviewer | carried a hand-tallied count from prose to prose while the section next to it asserted that every count cites its producing command | one `grep -oE ... | uniq -c`, ~5s | correct the artifact, this file and the PR body, then re-verify AC3, ~6 min | ~72x |
| Severity assignments corrected three times across two review rounds (L-8) | assigned 28 severities by judgement without first writing the scale they were judged against | writing a four-paragraph rubric before the first assignment, ~5 min | three separate correction passes over the tables, the totals line, the summary section, the JSON block and the PR body, ~20 min | ~4x |
| Fabricated contract claim (L-6), found by the hostile reviewer | ran a citation-resolution pass and treated resolution as support, so the claim was never read against the line it cited | reading the 14 cited lines, ~90s | restate four sites, re-derive the coupling table row, re-run AC3, ~7 min | ~5x |

The pattern across all twelve: each was caused by acting on an internal belief that a five-to-thirty-second command would have checked. On a document whose entire value is that its claims are checkable, that is the failure mode to name explicitly rather than absorb.

## Evidence-predates-work

All suite runs, the two defect repros (F-N1 escaped directory, F-N5 trailing-newline byte comparison), and the `PROJECT.md` absence check were executed on `epic/682-python-executable-path` / `feat/683-investigate-executable-path` before the artifact text describing them was written. The AC and citation verification passes were run against the assembled artifact after it was written, and both produced corrections (L-1, L-2) that are recorded above rather than quietly folded in.
