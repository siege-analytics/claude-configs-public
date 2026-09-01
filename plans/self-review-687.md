---
ticket_refs:
  - siege-analytics/claude-configs-public#687: comment pending
  - siege-analytics/claude-configs-public#682: comment pending
  - siege-analytics/claude-configs-public#683: cited as evidence base
  - siege-analytics/claude-configs-public#685: cited as constraint source
---

# Self-review: ticket #687 (design note for the epic #682 python rewrite)

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #687 (epic #682, follows #683 and #685)
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 687` -> `PASS: ticket 687 is fit for execution`
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/682 (epic body; sequencing places design as step 3)
Pre-author-inventory: NONE (see `## Trivial-against-state declaration`)
Trivial-against-state: this diff authors no runtime artifact; see the declaration block below
Investigate-artifact: `plans/investigate-682-executable-path.md` at `7d50cce` on `feat/683-investigate-executable-path`, PR #684. Present in this working tree at `7b5f6a1` / 979 lines, which is **stale**; the depended-on version is 1016 lines. The staleness is recorded in the design note's Investigation Dependencies section rather than papered over, and is L-2 below.
Pre-mortem-artifact: `plans/pre-mortem-682-python-rewrite.md` at `a9e8600` (this branch's tip before this commit), PR #686
Hostile-review-artifact: NOT YET OBTAINED. See `## Hostile-review-waiver`. The two upstream artifacts this note rests on have had reviews: PR #684 rounds 1 and 2 (sibling `260831-strong-nova`, GPT-5.5, Block both times, 8 findings, all accepted; round 3 requested and outstanding), and PR #686 round 1 (sibling `260831-copper-island`, Opus 5, Block, 7 findings, all accepted; round 2 outstanding).
Project-contribution: tests epic #682's premise instead of assuming it. H1 was registered by the epic and deferred twice; this note classifies all 55 live findings against a discriminator written before the classification and returns 31 structural against a pre-registered threshold of 28. The specific thing it buys beyond the ticket: the margin is 3, and the note names the four contestable calls that flip the verdict, so the epic's continue/descope decision is now falsifiable by a reviewer in an afternoon rather than resolvable only by building the thing.

## Trivial-against-state declaration

Reason: none of the five authoring-against-state contact categories is engaged. The diff adds two prose documents under `plans/` and changes no runtime artifact. Data-shape: no schema, query or dataframe is written or read; the note *specifies* eleven dataclasses and enums and authors none of them. Config-state: no config file is authored or consumed; the note reasons about `tool_install_policy` and proposes narrowing `allow`, but this repository has no `PROJECT.md` to read (#672 P1-3), so no config state is contacted. Topology: no service, path or dependency wiring changes; the proposed `sys.path` bootstrap is described, not written. Plan-shape: no DAG or pipeline definition is produced. Version-resolution: no dependency, pin or lockfile is touched; the note names Python 3.10 as a proposed floor without editing any manifest.
Evidence: `git diff --name-only a9e8600..HEAD` returns `plans/think-682-python-design.md` and `plans/self-review-687.md`. Both `.md`, both new, both under `plans/`. No file with a runtime extension appears, and nothing under `hooks/`, `skills/`, `scripts/` or `templates/` is modified, so no `python3 bin/build.py --deploy` is required.
Falsification: a reviewer identifies a runtime consumer that reads either file and changes behaviour as a result. The nearest candidate is `hooks/write/ticket-propagation-guard.sh`, which reads `plans/` frontmatter; it reads the `ticket_refs:` block for enforcement and does not read the body, so it is a consumer of the frontmatter and not of the design. If a consumer of the body exists, this declaration is wrong.

## Trivial-investigation declaration

Category: doc-only, resting on a completed investigation rather than skipping one. The `[skill:think]` Step 8 gate asks whether a Fact Sheet is required; the answer is yes and it exists, as #683's `plans/investigate-682-executable-path.md`. This ticket is the design that consumes it. No new investigation was run because the note dispositions findings the fact sheet established rather than deriving new ones, which is ticket #687's own stated assumption.
Cannot produce error: the artifact executes nothing. Its failure mode is being wrong about a classification, not breaking something.
Evidence: `git diff --name-only a9e8600..HEAD` -> two new `.md` files under `plans/`; no source, hook, skill or template file touched.
Falsification: the first implementation ticket finds a constraint whose Mechanism cannot be built as described. C-15 clause (b) is the most likely candidate, because "every value that reaches a sink passes a validator declared for that sink" is stated as a test over `AutomationBlock`'s fields, and whether that enumeration is decidable statically is not established here.

## Hostile-review-waiver

Reason: hostile review by a sibling on a different model is required by standing order and is being obtained, but the PR does not exist at push time, so no review artifact can be cited. This waiver covers the push only, not the merge.
Scope: `plans/think-682-python-design.md`, `plans/self-review-687.md`. Both `.md`; the diff touches no file with an executable extension.
Compensating-control: all six ACs verified mechanically rather than by reading. AC1 by `grep -c` on the four line-anchored bullet forms plus a token check over the Disposition values; AC2 and AC3 by a `python3` parser that extracts the table rows by regex and compares the id set against the three source lists by **set equality**, not count; AC4 by `mermaid_validate` plus a node-versus-public-surface cross-check; AC5 by counting the numbered claim bullets and reading each for a command, a threshold or a named test; AC6 by `grep -c` for the literal policy string. One correction was produced by the checks and is recorded as L-1 rather than folded in silently.
Waiver-invalid-if: this PR merges before a sibling review lands, or if the design note is treated as approved for implementation on the strength of the mechanical checks. The checks verify that the note has the shape ticket #687 asked for. They cannot verify that a classification is correct, and the classification is the whole deliverable.

## Peer review (mechanics, correctness, craft floor)

**writing-claims:2 and writing-claims:8 (countable claims carry the producing command).** Every count in the note, the commit message, the PR body and this artifact is reproduced under `## Quantified claims` with the command. Two of them were wrong on first write and both were caught by running the command rather than by reading: the H1 `grep -cE` published in the note's own H1 section returned 0 against its own table (the regex allowed one pipe between the id and the disposition where the table has two, and matched `#66[82]` where the ids are `#668` and `#672`), and the REDESIGN row count was asserted as 22 where the table has 21. Both are L-1.

**writing-claims:11 (class-completion claims enumerate the set).** Three class-completion claims are made and all three are backed by set operations rather than totals. "All 16 constraints have a disposition" is checked by four independent `grep -c` values agreeing at 16 plus a token check that every Disposition value is one of two words. "All 24 checklist items" is checked by parsing the table and by the epic body's own enumeration. "All 55 findings" is checked by building the expected id set from the three sources (20 #668 ids, 7 #672 ids, 27 `F-N` numbers plus `F-N12b`) and asserting set equality: 55 parsed, 55 unique, 0 missing, 0 extra. **Set equality rather than count equality is the direct consequence of fact-sheet finding 10-1**, which is the case where the count was right and the set was wrong, and where every check that ran was a check of the artifact against itself.

**writing-rules:4 (a negative claim carries the same evidence chain).** Four negative claims, each walked rather than asserted: the `Trivial-against-state` block names all five contact categories; the blast-radius section declines the CRITICAL backward-compatibility rule with the reason (no external caller) rather than ignoring the tier; the sibling-grep section states that the 99-file class is out of scope by decision rather than leaving the reader to assume it was missed; and Step 5b is skipped with the reason (no `PROJECT.md`), which is itself one of the findings the note dispositions.

**writing-tests:4 (mock fidelity).** Subject matter rather than a diff property, and it shapes two constraints. C-9's mechanism forbids substituting the object under test and the falsifier is a grep for exactly that (`monkeypatch.setattr.*orchestrate`). C-14 goes further than "the test default is a fake", because a default can be overridden by a test that means well: the falsifier is `grep -rn 'GhIssueFiler(' hooks/ tests/` returning exactly one site.

**writing-tests:7 (every AC names a falsifiable observable).** AC5 of ticket #687 is writing-tests:7 applied to prose, and 12 of 12 claims carry a command, a numeric threshold or a named test. The two weakest are claim 2 ("the classification is not reverse-engineered from the threshold", whose check is that the note's own list of reclassifications all run one way) and claim 12 ("the REDESIGN rows are not transcriptions", whose check is indirect through the C-8 floor). Both are named here rather than defended.

**writing-prose:1 and writing-prose:3.** Scanned before asserting. Banned-character scan over the design note returns 0 across all fourteen codepoints. The adverb scan returned 7 hits on first pass (`deliberately` x2, `explicitly` x3, `explicit` x1, `simply` x1, after excluding the 24 occurrences of the required `FIXED-EXPLICITLY` disposition token); all 7 were rephrased and the rescan returns 0. The residual hits this scan reports against *this* artifact are the backticked token names in this sentence and in the L-5 ledger row, not prose usage. The scan was run against the assembled document rather than against each chunk as written, which is the same skip the #685 ledger names, and it is a ledger row again.

**Citation resolution.** The existing resolver assumes a cited path exists, which is wrong for a design note: 82 of 157 citations are to files the note *proposes*. A design-aware variant partitions them. Existing artifacts: 75 citations, 0 unresolved, with every `file:line` checked against the file's length. Proposed artifacts: 82, all within the eleven declared modules or the `tests/executable_path/` tree. One false positive (`test.sh` inside a grep pattern) is classified as a pattern literal rather than counted as a citation. The partition itself is a claim a reviewer should check, because a typo in a proposed module name lands in the 82 and is invisible.

## Lead review (adversarial pass)

**The classifier and the hypothesis have the same author, and no mechanical check can fix that.** This is the exact weakness PR #684 round 2 found in the severity rubric (finding 9-3), one artifact upstream. Two mitigations are in place and both are weaker than independence: the discriminator was written before the classification, and every reclassification away from the fact sheet's preliminary read is listed with its direction. Three overturns that would have moved the count to 32, 33 and 34 were considered and declined on the ground that they flatter the hypothesis. That is the strongest available defence and it is still an author marking their own work. The instruction to the hostile reviewer is therefore to re-classify a sample rather than audit totals, because totals are what an author under H1 pressure gets right.

**The margin is 3 and the denominator is under review.** 31 of 55 against a threshold of 28. PR #684 is in round 3 and PR #686 in round 2; either can add a finding, which moves the denominator and the threshold together, or revise a severity, which does not. A round-3 finding that is incidental moves the count to 31 of 56 against 28.5, which rounds to 29 and survives. Two such findings do not. The note states the margin and names the four contestable structural calls; it does not claim the verdict is robust.

**The C-2 / C-7 resolution may be too clean.** The note argues the constraints conflict only under the assumption that the probe is one module, and dissolves the conflict by factoring. That is right as far as it goes, but the falsifier is a `sys.modules` assertion in a fresh interpreter, and the note itself points out that running it in-process makes it pass vacuously. A falsifier whose failure mode is silent success is a weak falsifier, and this one is load-bearing for the design's central architectural claim. A reviewer should attack the test, not the argument.

**The `allow` narrowing is a breaking change justified by a blast radius of zero in this repository.** That reasoning is correct here and is the kind that ages badly: "no `PROJECT.md` exists" is true of this repo and says nothing about a consumer that has one. The note handles it with a CHANGELOG entry rather than by softening the change, which is the right call for a P0, but the argument in the C-6 block leans on the local-zero more than it should.

**Nothing here has been built, and every falsifier is prospective.** Twelve claims, and none of them can be run today because the modules do not exist. The fact sheet's claims were established by same-turn execution; the pre-mortem's were grounded in shell code that exists; this note's are grounded in code that does not. That is inherent to a design note and it is a real drop in evidence grade between step 2 and step 3 of the epic, worth stating because the three artifacts otherwise look like they carry the same weight.

## Findings

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| L-1 | P1 | Two counts published in the note were wrong and both were caught by running the command the note itself quotes: the H1 `grep -cE` returned 0 against its own table, and "22 REDESIGN rows" is 21. | Both corrected. The H1 command is now the one that returns 31; the checklist paragraph now quotes the command that produces `21 REDESIGN, 2 PORT, 1 CREATE`. Root cause is writing the command from the intended table shape rather than from the table. |
| L-2 | P1 | The fact sheet in this working tree is 979 lines from `7b5f6a1`; the version the note depends on is 1016 lines at `7d50cce`. Every figure the note uses (20/7/27/55/28) comes from the corrected version and is absent from the checked-out copy. | Recorded in the note's Investigation Dependencies section with both `wc -l` figures and the `git show` command a reviewer needs. Not fixed by merging forward, because that breaks the epic's one-at-a-time isolation while two reviews are in flight. |
| L-3 | P1 | The citation resolver inherited from #685 reports 82 unresolved citations on this document and is not wrong: it assumes cited paths exist, which is false for a design note. Running it unmodified would have produced either a false alarm or, worse, a decision to stop citing proposed modules by path. | A design-aware variant partitions existing (75, 0 unresolved) from proposed (82). The partition is now a thing to check rather than a thing to trust, and it is a concrete argument for ticket #691: a checker that lives in `/tmp` gets re-derived per document and its assumptions drift. |
| L-4 | P2 | Two of the twelve falsifiable claims (2 and 12) are indirect: neither can be refuted by a single command. | Named in the Peer review rather than removed. A claim that is weak and labelled is more useful than a claim that is strong and false, but a reviewer should treat those two as prose. |
| L-5 | P2 | The prose scan ran against the assembled document rather than per chunk, for the third consecutive artifact. | Rework-ledger row. The fix is known and was not applied; recording it a third time without applying it is itself the finding. |

## Quantified claims

| Claim | Command | Value |
|---|---|---|
| 16 constraints, each with four fields | `grep -c '^#### C-'` and `grep -c` on each of the four `- **<Field>:**` forms | 16 / 16 / 16 / 16 |
| Every disposition is SATISFIED or DECLINED | `grep -o '^- \*\*Disposition:\*\* .*' \| sed \| sort \| uniq -c` | 16 SATISFIED, 0 DECLINED |
| 24 checklist rows | `python3` regex over `^\| (\d+) \| (.+?) \| (PORT\|REDESIGN\|CREATE) \| (.+?) \|$` | 24; 0 empty target modules |
| Checklist split | same parse, `Counter` on the token | 21 REDESIGN, 2 PORT, 1 CREATE |
| 55 finding rows, set equality against sources | `python3` parse of `^\| (#6(68\|72) P[012]-\d+\|F-N\d+b?) \| ([SI]) \| (\S+) \|` compared to the union of the three source id lists | 55 parsed, 55 unique, 0 missing, 0 extra, 0 duplicates |
| H1 structural count | `grep -cE '^\| (#6(68\|72) P\|F-N)[^\|]*\|[^\|]*\| DISCHARGED-BY-CONSTRUCTION'` | 31 |
| Disposition split | `Counter` over the parsed rows | 31 DISCHARGED, 22 FIXED, 2 DECLINED; 31+22+2=55 |
| H1 classification split | `Counter` over the `S`/`I` column | 31 S, 24 I |
| H1 verdict | 31 vs the pre-registered 28 | CONTINUE, margin 3 |
| 12 falsifiable claims | `python3` count of `^\d+\. \*\*` inside the section | 12 |
| Cutover policy stated | `grep -c 'partial merge is not permitted'` | 1 |
| Mermaid valid | `mermaid_validate` with `render: true` | `{"valid": true}` |
| Mermaid nodes covered by the public-surface table | 11 nodes vs 11 rows, compared by name | 11 / 11 |
| Existing-artifact citations | design-aware resolver | 75, 0 unresolved |
| Proposed-artifact citations | same | 82, all within the declared module set |
| Banned characters | `LC_ALL=C grep -c '[^ -~\t]'` | 0 |
| Adverb/hedge scan | `grep -ocE` over the rule's token list, excluding `FIXED-EXPLICITLY` | 0 after rephrase (7 before) |
| Design note length | `wc -l` | 558 |
| Ticket fitness | `bash scripts/discipline/evaluate-ticket.sh 687` | PASS |

Blast-radius figures quoted in the note come from `grep -rn <entity> --include='*.sh' --include='*.md' --include='*.py' . \| grep -v '^./plans/' \| wc -l`, with `_field` counted `-w` because the unbounded form matches `_fields` and returns 161 against a true 9. Sibling-grep figures come from the four queries in the note's sibling table, run this session.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| The H1 `grep -cE` published in the note returned 0 against the note's own table (L-1) | wrote the verification command from the table shape I intended rather than running it against the table I wrote | run the command once, ~1s | debug the regex against the real row format, correct it in the document, re-run all three table checks, ~4 min | ~240x |
| "22 REDESIGN rows" against a table with 21 (L-1) | counted by reading the table rather than by `uniq -c` | `grep -oE \| awk \| sort \| uniq -c`, ~1s | correct two sites, add the producing command to the prose, ~2 min | ~120x |
| Wrote the Investigation Dependencies paragraph claiming the fact sheet is absent from this branch, when it is present and stale (L-2) | asserted a git-state fact from memory of the branch topology instead of running `wc -l` on the file in the tree | `wc -l plans/investigate-682-executable-path.md` and `git show 7d50cce:... \| wc -l`, ~2s | rewrite the paragraph into a staleness warning with both figures and the `git show` command, ~5 min | ~150x |
| Citation resolver reported 82 unresolved and could not be used as-is (L-3) | reused a checker across a document class it was not written for, without checking its assumption | read the 20-line script before running it, ~30s | write a design-aware variant with a proposed-set partition, ~6 min | ~12x |
| Seven adverb hits found after the document was written (L-5) | wrote the whole document before running the scan, for the third artifact running | run the two prose scans per section as written, ~5s | scripted rephrase of seven sites plus two rescans, ~3 min | ~36x |

Five rows, and four of them are the same skip: acting on an internal belief that a sub-two-second command would have checked. The #683 and #685 ledgers both name that pattern; this is the third time. The one that is new in kind is L-3, which is not a skipped check but a *reused* check whose assumption did not survive the change of subject -- a tool built for artifacts that cite existing code, applied to an artifact that cites code it proposes. That is the same shape as fact-sheet finding 9-6 (a control described in prose drifts from the control that runs) at one remove: a control that was correct drifts when the thing it controls changes underneath it.

## Evidence-predates-work

The six AC checks, the design-aware citation resolver, the two prose scans, the mermaid validation, the blast-radius greps, the four sibling greps and `evaluate-ticket.sh 687` were all executed against the assembled document, and three of them produced corrections that changed the document: the H1 command, the REDESIGN count and the Investigation Dependencies paragraph. The blast-radius and sibling-grep figures were produced before the Proposals section was written, and they are what disqualified Proposal A and what scoped the class-level fix to the executable path.

What this artifact does not claim: that the 31/55 classification is correct. Every mechanical check above verifies the note's *shape* -- that 55 rows exist, that they partition their sources, that the totals agree with the commands. None of them verifies that `#672 P2-1` is structural rather than incidental, and that judgement, repeated 55 times by the author of the hypothesis it decides, is the deliverable. The four contestable calls are named in the note's H1 section and the three declined overturns are named beside them, so a reviewer has somewhere specific to start. That is the substitute for independence, and it is not an equivalent.
