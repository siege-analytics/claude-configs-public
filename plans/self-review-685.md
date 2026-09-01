---
ticket_refs:
  - siege-analytics/claude-configs-public#685: comment pending
  - siege-analytics/claude-configs-public#682: comment pending
  - siege-analytics/claude-configs-public#683: cited as evidence base
---

# Self-review: ticket #685 (pre-mortem for the epic #682 python rewrite)

Working as: software engineer

## Assumptions

Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #685 (epic #682, follows #683)
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 685` -> `PASS: ticket 685 is fit for execution`
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/682 (epic body; sequencing section places pre-mortem as step 2, design as step 3)
Pre-author-inventory: NONE (see `## Trivial-against-state declaration`)
Trivial-against-state: this diff authors no runtime artifact; see the declaration block below
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/683#issuecomment-5488627863
Pre-mortem-artifact: `plans/pre-mortem-682-python-rewrite.md` (this ticket's deliverable is itself the pre-mortem; the recursion is addressed in `## Trivial-investigation declaration`)
Hostile-review-artifact: WAIVED (see `## Hostile-review-waiver`)
Project-contribution: converts the #683 fact sheet from a list of defects into fourteen constraints the step-3 design must satisfy or decline. The specific thing it buys: five of the fourteen failure modes are ones a *correct-looking* Python translation produces, and three of those five are the ones the current green test suite would not catch. Without this document the design ticket's most likely output is a faithful port that passes 19 ported fixtures and ships five P0 defects.

## Trivial-against-state declaration

Reason: none of the five authoring-against-state contact categories is engaged. The diff adds two prose documents under `plans/` and changes no runtime artifact. Data-shape: no schema, query, or dataframe is written or read; the document *describes* a proposed dataclass but authors none. Config-state: no config file is authored or consumed; the document reasons about `tool_install_policy` resolution without reading a `PROJECT.md`, which this repository does not have. Topology: no service, path, or dependency wiring changes. Plan-shape: no execution plan, DAG, or pipeline definition is produced; the "design constraints" section is prose, not a machine-read artifact. Version-resolution: no dependency, pin, or lockfile is touched.
Evidence: `git diff --name-only <base>..HEAD` returns `plans/pre-mortem-682-python-rewrite.md` and `plans/self-review-685.md`. Both `.md`, both new, both under `plans/`. No file with a runtime extension (`.py`, `.sh`, `.json`, `.yaml`, `.toml`, `.lock`) appears, and no file under `hooks/`, `skills/`, `scripts/`, or `templates/` is modified, so no `python3 bin/build.py --deploy` is required.
Falsification: a reviewer identifies a runtime consumer that reads either file and changes behaviour as a result. The nearest candidate is the resolver guard reading a `plans/` path by convention; if such a consumer exists, this declaration is wrong and a pre-author inventory of its expected schema is required.

## Trivial-investigation declaration

Category: doc-only, with a recursion worth naming rather than eliding. The deliverable of this ticket *is* an adversarial risk pass, so "run a pre-mortem before writing the pre-mortem" would be an infinite regress. What the standing order actually wants at this point is evidence that the risks of the document being wrong were considered, and they were: the document's own kill criteria and the E-1 elephant are the pre-mortem of the pre-mortem, because both state the conditions under which this document's premise fails.
Cannot produce error: the artifact executes nothing. Its failure mode is being wrong, not breaking something, and being wrong is what the hostile review is for.
Evidence: `git diff --name-only` -> two new `.md` files under `plans/`; no source, hook, skill, or template file touched.
Falsification: the step-3 design ticket finds a failure-mode class this document omitted that would have changed the design. FM-7 is the reason to think the omission risk is real rather than theoretical: it exists only because a mitigation recommended in FM-2 creates a new risk, and there may be more second-order interactions of that shape that a single pass did not find.

## Hostile-review-waiver

Reason: hostile review by a sibling on a different model is required by standing order and is being obtained, but the PR does not exist at push time, so no review artifact can be cited. This waiver covers the push only, not the merge.
Scope: `plans/pre-mortem-682-python-rewrite.md`, `plans/self-review-685.md`. Both `.md`; the diff touches no file with an executable extension.
Compensating-control: all five ACs verified mechanically rather than by reading (per-category `grep -c` on the exact `- **Category:** <token>` line, per-subheader `grep -c` against N, a `python3` citation resolver over both finding IDs and `file:line` pairs, a scripted check that the Design-constraints coverage line names each mandatory category with an FM id, and a per-bullet classifier over the kill criteria). One correction was produced by the checks and is recorded as L-1 rather than folded in silently.

## Peer review (mechanics, correctness, craft floor)

**writing-claims:2 (countable claims need the falsifying grep) and writing-claims:8 (specific counts cite their producing command).** Every count in the document, the commit message, the PR body, and this artifact is reproduced under `## Quantified claims` with the command that produced it. The check bit: the document's first draft asserted "six P0 findings are live" because the fact sheet's totals line says so. Counting the table the totals line summarises returns five. The claim was inherited rather than checked, and the shelf is what caught it.

**writing-claims:11 (class-completion claims enumerate the set).** "The three mandatory categories are each mitigated by a constraint" is a class-completion claim over a set of three, and it is backed by a script that searches the Design-constraints section for each category name and asserts an `FM-` id within the same clause, rather than by eyeballing one sentence. Same treatment for the six category tokens in AC1: each is grepped for the exact `- **Category:** <token>` line-anchored form, so a category named only in prose would not count.

**writing-rules:4 (a "this does not apply" claim carries the same evidence chain as any other).** Three negative claims are made and each walks its categories individually rather than asserting the negative once: the `Trivial-against-state` block addresses all five contact categories by name, the `Trivial-investigation` block names the regress and its falsifier, and the document's three paper tigers each cite a `file:line` for the mitigation rather than asserting "already handled".

**writing-tests:4 (mock fidelity).** Load-bearing here as subject matter rather than as a diff property, and it is the source of two of the fourteen failure modes. FM-9 is the named test-fragility pattern from `[skill:pre-mortem]` applied forward: the natural pytest port mocks the probe, which is the layer being rewritten. FM-5 is the same rule applied to templates: `scripts/probe/_test_probe_common.sh` writes its own copy of the shipped template, which is a fidelity failure and is the recorded mechanism by which F-N17 survived. Both produce constraints (C-9, C-5) rather than observations.

**writing-tests:7 (every AC names a falsifiable observable).** AC5 of this ticket is itself a writing-tests:7 check applied to prose: a kill criterion must contain a command, a numeric threshold, or a named test. Seven of seven pass, and the classifier that says so is reproduced below. The one bullet that is a judgement dressed as a threshold is the 2000-line diff limit, and the document says so in the bullet rather than hiding it.

**writing-prose:1 and writing-prose:3.** Scanned before asserting, this time. The banned-character scan over the pre-mortem returns 0 across all fourteen codepoints in the rule. The adverb scan initially returned six hits (`deliberate` once, `explicit`/`explicitly` five times); all six were rephrased and the rescan is clean. This is the direct correction of the #683 rework-ledger row where compliance was asserted before the scan was run. No AI or assistant attribution appears in either file or in the commit message, and the commit is authored by passing `-c user.name` / `-c user.email` on the command line.

**Citation resolution.** Ran a resolver over every `- **Fact-sheet basis:**` line: each `F-N<n>` and `#668 P<x>-<y>` / `#672 P<x>-<y>` token must appear in the fact sheet, and each `path:line` must exist with the line within the file's length. 25 finding IDs and 33 `file:line` pairs, 0 unresolved.

## Lead review (adversarial pass)

*Software engineering.* Did the Junior produce a risk enumeration, or a list of things that sound bad?

**Approach-fit verdict: fit, with one structural weakness that is stated in the document rather than hidden.** The weakness is that `[skill:pre-mortem]` Step 1 requires a design note as input and there is no design. A pre-mortem with no design cannot stress-test anything; it can only enumerate what the *source* makes likely. The document opens by saying this and by naming the cost: no failure mode can cite a design decision. That is the honest framing, and it is the epic's chosen sequencing rather than a skipped step, but it does mean this document is weaker evidence than a post-design pre-mortem would be, and the step-3 design ticket should get its own adversarial pass rather than treating this one as discharged.

**Is every failure mode grounded, or is some of it anxiety?** The hard rule is no Tiger without a `file:line`. All fourteen carry one and the resolver confirms all resolve. The harder question is whether the *mechanism* follows from the citation, which no script checks. Two are weaker than the rest and I would flag them if I were reviewing someone else's document. FM-7 (importable module widens the dangerous surface) is a prediction about future callers, grounded in the current code only insofar as `_common.sh:145` and `:86` are the operations that would be exposed; it is reasoning, not evidence. FM-13 (half-done migration) is grounded in the existence of a process boundary and in F-N15's duplicate-file precedent, which is suggestive rather than probative, and it is the one entry classified Elephant rather than Tiger for that reason.

**Did the severity scoring do any work, or is it decoration?** It did work in one place and was decoration in the rest. FM-6 scored 85 and moved from a middling intuition to the highest-priority item in the document, which changed C-6 from "use argv lists" to "privilege tiers are part of the policy vocabulary". The other thirteen composites were assigned to be consistent with tiers already chosen, which is the failure mode the skill warns about in reverse. I have shown the full dimension breakdown for FM-6 only, and I am recording the rest as unshown rather than implying they were derived the same way. That is finding L-2.

**Blast radius.** Zero at push: two prose files, nothing executes, no `hooks/` or `skills/` change. Load-bearing at merge in the same way #683 is: the step-3 design is scoped against these fourteen constraints, so a missing failure mode becomes a missing constraint becomes a defect that ships.

**The uncomfortable one.** The document's own E-1 says the epic's premise (H1: a majority of findings dissolve structurally) is untested and that the fact sheet's preliminary read is 9 structural to 4 incidental out of 55, which is 13 of 55 classified at all. I wrote a kill criterion against that threshold. I should be clear that writing a kill criterion is not the same as being willing to pull it: if the classification comes back at 26 of 55, the correct action is to descope a multi-ticket epic that has already consumed two units of work, and the pressure at that point will be to argue the threshold rather than honour it. Naming that here is the only mechanism this document has against it.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L-1 | P1 | The first draft inherited "six P0 findings" from the fact sheet's totals line without counting the table, and propagated it into a design constraint (C-8) and a kill criterion as a numeric threshold. The table has five. | fixed -- corrected to 5 throughout, the five IDs enumerated (F-N1, F-N11, F-N13, F-N14, F-N22), and a `## Fact-sheet correction check` section added recording the discrepancy and the command that found it. Two further count corrections (26 new findings not 25, 55 total not 54) came from the same pass. |
| L-2 | P2 | Composite severity scores are shown with a full dimension breakdown for FM-6 only; the other thirteen are asserted. A reader could take all fourteen as derived. | noted in the Lead review above and stated in the document's own classification section as a worked example rather than a complete derivation. Not fixed: deriving thirteen more five-dimension tables would add length without changing a single tier, and the tiers are the actionable output. |
| L-3 | P2 | FM-7 is a second-order risk created by FM-2's own mitigation. One pass found one such interaction; there is no reason to think it is the only one. | ticket -- named as the falsifier in the `## Trivial-investigation declaration` and flagged to the hostile-review sibling as a specific hunting instruction |
| L-4 | P2 | The document is pinned to `feat/683-investigate-executable-path`, which is unmerged and under hostile review on PR #684. If that review revises severities, four of five Launch-Blocking entries change tier. | noted -- carried in the document as elephant E-3 with its revisit trigger; the branch is stacked on #683 so the rebase is a single operation |
| L-5 | P3 | Detection signals are stated as tests that must be written. E-2 records that this repository has no CI invocation of either suite, so none of them will fire on its own. | noted -- E-2 states the cost of deferral (every mitigation degrades to a promise unless its detection signal ships in the same PR as the mitigation) and that clause is the operative constraint |

No P1 rows remain unresolved.

## Quantified claims

- "14 failure modes" -- `grep -c '^### FM-' plans/pre-mortem-682-python-rewrite.md` -> `14`
- "eight subheaders on every entry" -- `for h in Category Mechanism "Fact-sheet basis" Probability "Blast radius" Mitigation "Detection signal" "Owning ticket"; do grep -c "^- \*\*$h:\*\*" ...; done` -> `14 14 14 14 14 14 14 14`
- "all six categories present" -- `for c in faithful-port contract-drift blast-radius coverage-theatre scope operational; do grep -c "^- \*\*Category:\*\* $c$" ...; done` -> `3 2 2 2 2 3`
- "0 unresolved citations" -- `python3` resolver over the fourteen `Fact-sheet basis` lines -> `finding IDs checked: 25, file:line checked: 33` / `unresolved: 0`
- "the three mandatory categories are restated in Design constraints with FM ids" -- `python3` regex over the Design-constraints section -> `faithful-port OK, coverage-theatre OK, blast-radius OK`
- "7 of 7 kill criteria are observables" -- per-bullet classifier for a backticked command, a digit, or a `test_` name -> `AC5: 7/7`
- "5 P0 findings, not 6" -- `sed -n '632,661p' plans/investigate-682-executable-path.md | grep -oE '^\| F-N[0-9]+b? \| P[012]' | awk '{print $4}' | sort | uniq -c` -> `5 P0, 14 P1, 7 P2`
- "26 distinct new findings, not 25" -- `sed -n '632,661p' ... | grep -oE '^\| F-N[0-9]+b?' | sort -u | wc -l` -> `26`
- "13 Tigers and 1 Elephant" -- `grep -c '| Tiger |'` -> `13`; `grep -c '| Elephant |'` -> `1`
- "5 Launch-Blocking, 3 Mitigate-before-ship, 5 Fast-Follow, 1 Track" -- `awk '/^\| FM-/{split($0,a,"|"); print a[8]}' | sort | uniq -c` -> `5 Fast-Follow, 5 Launch-Blocking, 3 Mitigate-before-ship, 1 Track`
- "14 design constraints" -- `grep -c '^- \*\*C-'` -> `14`
- "3 paper tigers, 3 elephants" -- `grep -c '^\*\*PT-'` -> `3`; `grep -c '^\*\*E-'` -> `3`
- "284 lines" -- `wc -l < plans/pre-mortem-682-python-rewrite.md` -> `284`
- "0 banned prose characters" -- `python3` count over the fourteen codepoints named in writing-prose:1 -> `total banned: 0`
- "ticket #685 is fit for execution" -- `bash scripts/discipline/evaluate-ticket.sh 685` -> `PASS`

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Inherited "six P0" from the fact sheet's prose and built a design constraint and a kill criterion on it (L-1) | treated a summary line in an artifact I wrote yesterday as evidence rather than as a claim needing the same grep as anyone else's | one `grep -oE \| awk \| uniq -c` over the findings table, ~10s | correct 9 occurrences across two documents via a scripted replace, add a correction-check section, re-run all five ACs, ~7 min | ~42x |
| Ticket #685 blocked by `evaluate-ticket.sh` on "title lacks a verb token" | filed the ticket with a noun-phrase title without running the gate that every sub-ticket is required to pass | `bash scripts/discipline/evaluate-ticket.sh 685`, ~3s | read the heuristic at `scripts/discipline/evaluate-ticket.sh:119`, retitle via `gh issue edit` with a destructive-ok block, re-run, ~3 min | ~60x |
| Branched `feat/685` off `epic/682-python-executable-path`, where the fact sheet does not exist | assumed the #683 work was on the epic branch because the PR targets it, without checking that the PR is unmerged | `ls plans/investigate-682-executable-path.md` after checkout, ~2s | delete the branch and re-cut from `feat/683-investigate-executable-path`, ~1 min | ~30x |
| Six writing-prose:3 adverb hits found after the document was written | wrote the whole document before running the scan, again, despite this being a row in the #683 ledger | running the two prose scans against each chunk as written, ~5s | scripted rephrase of six sites plus rescan, ~2 min | ~24x |

Four rows, and three of them are the same skip as the #683 ledger's stated pattern: acting on an internal belief that a sub-ten-second command would have checked. The one that is new in kind is the branch cut, which was an assumption about *git state* rather than about file contents, and the check for it is the same shape: look before writing. The prose-scan row is the one I have no excuse for, because the previous ticket's ledger names it and the fix was to scan first.

## Evidence-predates-work

The five AC checks, the citation resolver, the two prose scans, the fact-sheet count audit, and `evaluate-ticket.sh 685` were all executed against the assembled document, and the count audit produced L-1, which changed the document's numeric thresholds. The document's `file:line` citations were taken from the #683 fact sheet, which established them by same-turn execution on this branch, and the resolver re-checked every one against the working tree rather than trusting the fact sheet's transcription. The one thing this artifact does not claim is that the fourteen failure modes are exhaustive; a single adversarial pass by the author of the fact sheet is precisely the input a hostile review exists to correct, and L-3 names the specific place to look first.
