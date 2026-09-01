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
Hostile-review-artifact: PR #686 round 1, sibling `260831-copper-island` (Opus 5), https://github.com/siege-analytics/claude-configs-public/pull/686#issuecomment-5488975509, verdict Block, seven findings (S1-1, S1-2, S2-1, S2-2, S2-3, S2-4, S3-1). All seven accepted and remediated, with one recorded disagreement on the direction of S2-3 (see L-2 and the FM-15 override paragraph in the pre-mortem). Remediation record and round-2 request: https://github.com/siege-analytics/claude-configs-public/pull/686#issuecomment-5489434788 The upstream #683 fact sheet this document rests on has had its own rounds 1 and 2: PR #684, sibling `260831-strong-nova` (GPT-5.5), Block both times, 8 findings, all accepted. This document is restated against the corrected fact sheet; see `## Upstream review revision` below.
Project-contribution: converts the #683 fact sheet from a list of defects into sixteen constraints the step-3 design must satisfy or decline. The specific thing it buys: six of the sixteen failure modes are ones a *correct-looking* Python translation produces, and three of those six are the ones the current green test suite would not catch. Without this document the design ticket's most likely output is a faithful port that passes 19 ported fixtures and ships four P0 defects.

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

**writing-tests:4 (mock fidelity).** Load-bearing here as subject matter rather than as a diff property, and it is the source of two of the sixteen failure modes. FM-9 is the named test-fragility pattern from `[skill:pre-mortem]` applied forward: the natural pytest port mocks the probe, which is the layer being rewritten. FM-5 is the same rule applied to templates: `scripts/probe/_test_probe_common.sh` writes its own copy of the shipped template, which is a fidelity failure and is the recorded mechanism by which F-N17 survived. Both produce constraints (C-9, C-5) rather than observations.

**writing-tests:7 (every AC names a falsifiable observable).** AC5 of this ticket is itself a writing-tests:7 check applied to prose: a kill criterion must contain a command, a numeric threshold, or a named test. Eight of eight pass, and the classifier that says so is reproduced below. The one bullet that is a judgement dressed as a threshold is the 2000-line diff limit, and the document says so in the bullet rather than hiding it.

**writing-prose:1 and writing-prose:3.** Scanned before asserting, this time. The banned-character scan over the pre-mortem returns 0 across all fourteen codepoints in the rule. The adverb scan initially returned six hits (`deliberate` once, `explicit`/`explicitly` five times); all six were rephrased and the rescan is clean. This is the direct correction of the #683 rework-ledger row where compliance was asserted before the scan was run. No AI or assistant attribution appears in either file or in the commit message, and the commit is authored by passing `-c user.name` / `-c user.email` on the command line.

**Citation resolution.** Ran a resolver over every `- **Fact-sheet basis:**` line: each `F-N<n>` and `#668 P<x>-<y>` / `#672 P<x>-<y>` token must appear in the fact sheet, and each `path:line` must exist with the line within the file's length. 24 finding IDs and 25 `file:line` pairs, 0 unresolved, re-run after the FM-15 and FM-16 additions. `#683`'s L-6 applies here too: resolution is not support, and no script checks that a cited line means what the Mechanism paragraph says it means.

## Lead review (adversarial pass)

*Software engineering.* Did the Junior produce a risk enumeration, or a list of things that sound bad?

**Approach-fit verdict: fit, with one structural weakness that is stated in the document rather than hidden.** The weakness is that `[skill:pre-mortem]` Step 1 requires a design note as input and there is no design. A pre-mortem with no design cannot stress-test anything; it can only enumerate what the *source* makes likely. The document opens by saying this and by naming the cost: no failure mode can cite a design decision. That is the honest framing, and it is the epic's chosen sequencing rather than a skipped step, but it does mean this document is weaker evidence than a post-design pre-mortem would be, and the step-3 design ticket should get its own adversarial pass rather than treating this one as discharged.

**Is every failure mode grounded, or is some of it anxiety?** The hard rule is no Tiger without a `file:line`. All sixteen carry one and the resolver confirms all resolve. The harder question is whether the *mechanism* follows from the citation, which no script checks. Two are weaker than the rest and I would flag them if I were reviewing someone else's document. FM-7 (importable module widens the dangerous surface) is a prediction about future callers, grounded in the current code only insofar as `_common.sh:145` and `:86` are the operations that would be exposed; it is reasoning, not evidence. FM-13 (half-done migration) is grounded in the existence of a process boundary and in F-N15's duplicate-file precedent, which is suggestive rather than probative, and it is the one entry classified Elephant rather than Tiger for that reason.

**Did the severity scoring do any work, or is it decoration?** It did work in one place, was decoration in the rest, and is now derived throughout. FM-6 scored 83 and moved from a middling intuition to the highest-priority item in the document, which changed C-6 from "use argv lists" to "privilege tiers are part of the policy vocabulary". The other fifteen composites were assigned to be consistent with tiers already chosen, which is the failure mode the skill warns about in reverse. I recorded that as L-2 and, in the first draft of this remediation, proposed to leave it recorded. The push guard would not accept a P1 resolved as "partly fixed", and the guard was right. Deriving the fourteen moved eleven of them down, moved five by ten points or more, and cut the number of entries above 60 from eight to three. It also surfaced something an assertion could not: five of the sixteen tiers disagree with their derived band, and the common cause is that 60% of the formula's weight measures how far damage *spreads* while most of this epic's failure modes make the deliverable silently wrong on a machine the operator can repair by hand. That critique is now in the document with a falsifier attached. Round 2 cost it some of its force: the count was six and was said to run in both directions, and the one downward case, FM-13, was not an override at all (R2-S2-1). Five overrides all running upward says the scoring sits systematically low, which is a claim about calibration rather than evidence that the formula is non-load-bearing in both directions.

The PR #686 round-1 review is what turned that admission into evidence. It found three separate things that only an underived score can produce. FM-6's composite appeared as 85, 84 and 85 in three places for one score, and the arithmetic under it has always been 83 (S3-1) -- three inconsistent copies of a number nobody had added. Three rows carried the band `Mitigate-before-ship` in the Urgency column, so FM-4, FM-9 and FM-14 recorded no tier at all and two of them turned out to be Launch-Blocking (S2-2). And FM-15 sat at Fast-Follow with a composite whose band says Track, which nobody noticed because nobody had checked a band (S2-3). All three are downstream of the same skip. L-2 is re-rated from P2 to P1 on that basis, and the P2 rationale in its row -- "deriving fifteen more tables would add length without changing a single tier" -- is now falsified: deriving one of them, FM-15, moved its score by seven points, and checking the bands moved two tiers.

**Blast radius.** Zero at push: two prose files, nothing executes, no `hooks/` or `skills/` change. Load-bearing at merge in the same way #683 is: the step-3 design is scoped against these sixteen constraints, so a missing failure mode becomes a missing constraint becomes a defect that ships.

**The uncomfortable one.** The document's own E-1 says the epic's premise (H1: a majority of findings dissolve structurally) is untested and that the fact sheet's preliminary read is 10 structural to 5 incidental out of 55, which is 15 of 55 classified at all. I wrote a kill criterion against that threshold. I should be clear that writing a kill criterion is not the same as being willing to pull it: if the classification comes back at 27 of 55, one short of the threshold, the correct action is to descope a multi-ticket epic that has already consumed two units of work, and the pressure at that point will be to argue the threshold rather than honour it. Naming that here is the only mechanism this document has against it.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| L-1 | P1 | The first draft inherited "six P0 findings" from the fact sheet's totals line without counting the table, and propagated it into a design constraint (C-8) and a kill criterion as a numeric threshold. The table has five. | fixed -- corrected to 5 throughout, the five IDs enumerated (F-N1, F-N11, F-N13, F-N14, F-N22), and a `## Fact-sheet correction check` section added recording the discrepancy and the command that found it. Two further count corrections (26 new findings not 25, 55 total not 54) came from the same pass. |
| L-2 | P1 | Composite severity scores are shown with a full dimension breakdown for FM-6 only; the other fifteen are asserted. A reader could take all sixteen as derived. **Raised P2 -> P1** after the PR #686 round-1 review found three defects downstream of it: FM-6's total appeared as 85, 84 and 85 for one score whose arithmetic is 83 (S3-1); FM-4, FM-9 and FM-14 carried a band label in the Urgency column and so had no tier, two of them Launch-Blocking (S2-2); and FM-15's tier and band contradicted each other unnoticed (S2-3). | fixed -- all sixteen are now derived, in a `### Every composite is derived` table showing the five dimension scores per row alongside the previous total. I first wrote this resolution as "partly fixed, fourteen still asserted", and the `hooks/git/self-review.sh` push guard refused it, which was correct: "partly fixed" is not a resolution. Deriving the fourteen was not cosmetic. Eleven moved down, two up, three were already right, five moved by ten points or more, and the count of entries scoring 60 or above fell from eight to three, mean change -6.6. FM-3 alone fell 66 to 41, because the S2-1 blast-radius correction had never been propagated into its score. A distribution that moves almost entirely one way when it is finally computed is the evidence for the allegation this finding could previously only make. Five tiers now override their band and are marked as such, and the reason is written up as a critique of the formula rather than as five separate judgement calls. |
| L-3 | P2 | FM-7 is a second-order risk created by FM-2's own mitigation. One pass found one such interaction; there is no reason to think it is the only one. | ticket -- named as the falsifier in the `## Trivial-investigation declaration` and flagged to the hostile-review sibling as a specific hunting instruction |
| L-4 | P2 | The document is pinned to `feat/683-investigate-executable-path`, which is unmerged and under hostile review on PR #684. If that review revises severities, four of the then-five Launch-Blocking entries change tier. | resolved -- both rounds landed and both revised severities. F-N14 went P0 to P1 in round 1, F-N22 in round 2, F-N18 went P1 to P0 in the round-2 rubric pass, and two findings were added. No Launch-Blocking tier changed. The re-weighting rule E-3 stated in advance was applied once, on FM-8, not twice: the PR #686 review showed the claimed FM-3 application rested on a false premise. What the rule protects is one of my own entries, and `## Upstream review revision` states that as the thing to challenge rather than as a result. |
| L-5 | P3 | Detection signals are stated as tests that must be written. E-2 records that this repository has no CI invocation of either suite, so none of them will fire on its own. | noted -- E-2 states the cost of deferral (every mitigation degrades to a promise unless its detection signal ships in the same PR as the mitigation) and that clause is the operative constraint |
| L-6 | P1 | The first version of this document was written against a fact sheet whose severity counts were wrong in both halves and which contained a claim contradicting the line it cited. The `## Fact-sheet correction check` caught the arithmetic and stated that fixing it belonged to the PR #684 review. It did not catch the contradicted claim, because the check audited counts and nothing else. | fixed at the document level -- the correction check now has a second run with a before/after table and the two new findings are written up as FM-15 and FM-16 rather than absorbed. Not fixed at the method level: a count audit cannot find a false mechanism claim, and the only control that found this one was a second reader. |
| L-7 | P0 | The document claimed F-N14 was FM-3's fact-sheet basis, and built E-3's "the rule fired and the prediction held" narrative and this artifact's headline self-examination on that dependency. FM-3's basis is F-N13, which was never downgraded. There was no tension and nothing for the rule to resolve. Found by the PR #686 round-1 review (S1-1), not by me, after two of my own passes over the same paragraph. | fixed -- struck from the pre-mortem at the correction-check section and at E-3, and rewritten here. P0 because it is L-6's class again in a merged-candidate artifact, and worse than L-6: L-6 inherited a false claim from upstream, L-7 manufactured one. The mechanism is written up in `## Upstream review revision` -- I had a pre-registered rule ready for "a P0 was downgraded", saw a P0 downgraded, and applied it without checking which failure mode the finding sat under. A pre-registered rule creates an appetite for the situation it governs. |
| L-8 | P1 | The round-2 remediation bundled two unrelated corrections into one "deferred, and why" paragraph and justified the pair with the reason that applied to only one of them. The denominator correction (57/29/9/4 to 55/27/10/5) was already committed at `7d50cce` in this PR's own base; the severity split (`4 P0, 17 P1, 7 P2` to `5 P0, 14 P1, 9 P2`) genuinely is not. Nine sites carried the superseded denominator into a merge candidate, three of them executable mechanisms. Found by the PR #686 round-3 review (R3-S2-3). | fixed -- the denominator is propagated in round 3 and the severity split stays deferred with its own reason, stated separately. The method-level residue is not closed: a bundled deferral is remembered by its strongest justification, so the weak half is never re-read. The check is per-item and cheap -- name the commit each deferred figure lives in and ask whether it is reachable from the PR base -- and I did not run it because the paragraph read as already-justified. This is the same shape as L-1 and L-6, an inherited claim treated as settled, with the twist that the claim was one I wrote myself one round earlier. |

L-6 and L-7 are P1 and P0 and both are resolved at the document level with their method-level residue stated rather than closed. L-2 is now P1 and is resolved by derivation rather than by argument, and the derivation is what turned it from an admission into a result: the scores were inflated in one direction, and the five band overrides that fall out of correcting them are a finding about the scoring formula that no amount of further asserting would have produced. The method-level residue on L-6 and L-7 is the same in both cases and is not closed: a count audit cannot find a false mechanism claim, and both were found by a second reader.

## Quantified claims

- "16 failure modes" -- `grep -c '^### FM-' plans/pre-mortem-682-python-rewrite.md` -> `16`. It was 14 at first push; FM-15 and FM-16 were added from F-N26 and F-N27, both surfaced by the PR #684 round-1 review
- "eight subheaders on every entry" -- `for h in Category Mechanism "Fact-sheet basis" Probability "Blast radius" Mitigation "Detection signal" "Owning ticket"; do grep -c "^- \*\*$h:\*\*" ...; done` -> `16 16 16 16 16 16 16 16`
- "all six categories present" -- `for c in faithful-port contract-drift blast-radius coverage-theatre scope operational; do grep -c "^- \*\*Category:\*\* $c$" ...; done` -> `4 3 2 2 2 3`
- "0 unresolved citations" -- two passes, each stated precisely enough to re-derive, because #683's L-11 records a claim of this exact shape whose stated rule returned a different number than the one published. Pass one, finding IDs: over the sixteen `- **Fact-sheet basis:**` lines, take every `F-N<n>[b]` and every `#668 P<x>-<y>` / `#672 P<x>-<y>` token and assert it appears in `plans/investigate-682-executable-path.md` -> `basis lines: 16, finding IDs checked: 29, unresolved: 0`. Pass two, file:line: over the whole document, take every backticked token matching `path.ext:N` or `path.ext:N-M` where `ext` is a source or document extension, resolve a bare basename against `git ls-files`, and assert the file exists and that *both* bounds of a range fall within its line count -> `entries checked: 59, unresolved: 0`. Over this document together with `plans/self-review-685.md` the same pass gives `70, 0`; the figure moves when this bullet itself names a `file:line`, which it does twice below, and it is quoted after the last such edit rather than before. Round 2 published `58` and `65` against an artifact measuring 58 and 69 at `f4f3090`, so exactly one of the two was stale, and which one is the finding. The single-file figure survived because the round-2 remediation added no citation to the pre-mortem; every one of the four it added went into this file, which is the figure the sentence claiming "quoted after the last such edit" was written to protect and did not (R3-S3-1). A claim guarding an ordering can be false while every number it guards except one stays true, and the one that moves is the one the guard was for. The stated rule is also ambiguous about whether the whole backticked span must be the token or whether tokens are extracted from inside it. Both readings are implemented and both return `59 / 11 / 70`, so the ambiguity does not bite here; it is named because a rule that two implementations happen to agree on is not the same as a rule that specifies one. Resolution is not support: no pass checks that a cited line means what the sentence citing it says, which is the failure the PR #686 review found twice (S2-1, and the FM-6 basis line where `k6.sh:12` and `_common.sh:145` both resolved and neither said what was claimed)
- "the three mandatory categories are restated in Design constraints with FM ids" -- `python3` regex over the Design-constraints section -> `faithful-port OK, coverage-theatre OK, blast-radius OK`
- "8 of 8 kill criteria are observables" -- per-bullet classifier for a backticked command, a digit, or a `test_` name -> `AC5: 8/8`
- "4 P0 findings" -- `grep -oE '^\| F-N[0-9]+b? \| P[012]' plans/investigate-682-executable-path.md | awk '{print $4}' | sort | uniq -c` -> `4 P0, 17 P1, 7 P2`. At first push this was `5 P0, 14 P1, 7 P2` against a fact sheet whose own prose said `6 P0, 13 P1, 7 P2`; the round-1 review corrected the fact sheet and downgraded F-N14
- "28 distinct new findings" -- `grep -oE '^\| F-N[0-9]+b?' plans/investigate-682-executable-path.md | sort -u | wc -l` -> `28`, with `F-N12b` counted as its own row per the unit of analysis fixed by review finding 1-3
- "15 Tigers and 1 Elephant" -- `grep -c '| Tiger |'` -> `15`; `grep -c '| Elephant |'` -> `1`
- "7 Launch-Blocking, 8 Fast-Follow, 1 Track" -- urgency tier is column 9 now that the band has a column of its own. The command has to select the risk table alone and has to disclose that it strips the `(override)` suffix, because `/^\| FM-/` matches the `### Every composite is derived` table as well and the raw column mixes suffixed and unsuffixed values. The risk table's second column is a word and the derived table's is a number, which separates them without line numbers that would rot: `RISK='/^\| FM-/ && $3 !~ /^ *[0-9]+ *$/'` then `awk -F'|' "$RISK {gsub(/^ +| +$/,\"\",\$9); sub(/ \(override\)$/,\"\",\$9); print \$9}" plans/pre-mortem-682-python-rewrite.md | sort | uniq -c` -> `8 Fast-Follow, 7 Launch-Blocking, 1 Track`, sixteen rows. The command published at round 1 was `awk '/^\| FM-/{split($0,a,"|"); gsub(/^ +| +$/,"",a[9]); print a[9]}'`, and its stated output was `7 Fast-Follow, 1 Fast-Follow (override), 7 Launch-Blocking, 1 Track`. That output is not what that command prints: it omits the sixteen bare numbers the second table contributes, strips `(override)` from the Launch-Blocking rows but not from the Fast-Follow row, and prints `Track (override)` as `Track`. Two undisclosed normalizations and one undisclosed exclusion (round-2 finding R2-S2-2). The claim was true and remains true; the command offered as its evidence was not the command that produced it. The first push said `5 Launch-Blocking, 3 Mitigate-before-ship, 7 Fast-Follow, 1 Track`, which was not a tier distribution at all: three rows carried a band label where a tier belongs, so they recorded no tier (S2-2). Two of those three (FM-4, FM-14) are Launch-Blocking
- "the band column is derived, not chosen" -- bands come from the composite via the `[skill:pre-mortem]` table and are counted separately from tiers. Same scoping as the tier bullet above, because `/^\| FM-/` alone also selects the sixteen rows of the `### Every composite is derived` table, whose column 8 is a bare number: `RISK='/^\| FM-/ && $3 !~ /^ *[0-9]+ *$/'` then `awk -F'|' "$RISK {gsub(/^ +| +$/,\"\",\$8); print \$8}" plans/pre-mortem-682-python-rewrite.md | sort | uniq -c`, printed rather than paraphrased:

  ```text
   1 Accept-and-document
   1 Emergency-stop
   2 Mitigate-before-ship
  12 Monitor-after-ship
  ```

  Sixteen rows, from `awk -F'|' "$RISK {print \$2}" plans/pre-mortem-682-python-rewrite.md | wc -l` -> `16`. Round 2's R2-S2-2 named two commands with the same defect and this remediation fixed only the tier one; the round-3 review found the other still unscoped, still publishing an output that the published command does not print. The unscoped form emits the sixteen derived-table composites as thirteen distinct numeric lines above the four band names. That is R2-S2-2's fourth instance, and the pattern in all four is the same: a finding phrased as "the command for X" gets applied to the one command the finding quoted rather than to the class it named
- "all sixteen composites are derived, and the column re-computes from its own dimensions" -- read the five dimension columns out of the `### Every composite is derived` table, apply the 25/25/20/15/15 weights, round to the nearest integer, and compare against the Composite column of the risk table: `16 rows, 16 agree, 0 disagree`
- "eleven moved down, two up, three unchanged; five by 10 or more; the count at 60-plus fell from 8 to 3; mean change -6.6" -- differencing the `Composite` and `Was` columns of the same table. This is the load-bearing number in the whole revision, because it is what converts L-2 from an admission that scores were asserted into evidence that asserting them was wrong in a consistent direction
- "5 of 16 tiers override their band" -- `grep -cE '^\| FM-.*\(override\)' plans/pre-mortem-682-python-rewrite.md` -> `5`, split 5 upward (FM-1, FM-2, FM-3, FM-14 from `Monitor-after-ship` to `Launch-Blocking`; FM-15 from `Accept-and-document` to `Fast-Follow`), 0 downward. Two corrections here, both round 2. The count was 6 and included FM-13, whose composite of 43 puts it in `Monitor-after-ship`, a band whose permitted urgencies are `Fast-Follow or Track`; FM-13 is `Track`, so it was inside its band and the `(override)` marker was wrong (R2-S2-1). And the published command was `grep -c '(override)'` unanchored, which the bullet described as being "over the risk table rows" -- a narrowing the command does not contain. **The unanchored command returns `7` at both revisions, and that stability is the trap rather than a reassurance.** Before the fix the 7 was 6 table rows plus one prose restatement; after it, it is 5 table rows plus two prose mentions, because the paragraph recording the correction names `(override)` as well. The figure the bullet exists to report went 6 to 5 while the command offered as its evidence never moved, so running that command to check this fix would have confirmed a number that had changed. Anchored, `grep -cE '^\| FM-.*\(override\)'` returns `6` before the FM-13 fix and `5` after, which is the discrimination the unanchored form lacks. This is R2-S2-2's third instance in this one verification list
- "16 design constraints" -- `grep -c '^- \*\*C-'` -> `16`
- "3 paper tigers, 3 elephants" -- `grep -c '^\*\*PT-'` -> `3`; `grep -c '^\*\*E-'` -> `3`
- "419 lines" -- `wc -l < plans/pre-mortem-682-python-rewrite.md` -> `419`. It was 326 before the round-2 remediation, 387 after it, and 419 after round 3. Round 2's 61 lines are the Band column preamble, the three per-row tier reasons, the FM-15 worked-score table and override, the C-15 completeness clause, the PT-2 second paragraph, and the `### Every composite is derived` section with its sixteen-row table. Round 3's 32 are the fourth count-audit run with its derivation fence and the distrust note under the count table. The figure published at round 2 was `385` against an artifact of 387, because it was quoted from the middle of the remediation rather than after its last edit (R3-S3-1); this bullet and the citation bullet above are both re-derived as the final action before this commit, which is the only ordering under which either can be true
- "0 banned prose characters" -- `python3` count over the fourteen codepoints named in writing-prose:1 -> `total banned: 0`
- "ticket #685 is fit for execution" -- `bash scripts/discipline/evaluate-ticket.sh 685` -> `PASS`

## Upstream review revision

This document was pushed against the #683 fact sheet at `4a81bf5`. That fact sheet has since been corrected at `cd91ccb` in response to the PR #684 round-1 hostile review, and this document is restated against the corrected version rather than left pinned to a superseded one.

What the restatement changed, and what it did not. It did not change which failure modes exist, because every mode cites finding IDs and `file:line` rather than counts, which is the property the first draft's correction check was written to preserve. It did change every numeric threshold that referenced the totals: C-8's five-tests rule, the H1 kill criterion's denominator, FM-11's detection signal, and E-1's classification base. It added FM-15 and FM-16, because F-N26 and F-N27 are failure modes of the rewrite and not restatements of existing ones. FM-15 is the more interesting of the two: it is a guard that is correct for the sink it was written for and wrong for a sink it also feeds, which is a shape none of the original fourteen covered.

This paragraph used to say that the uncomfortable part was FM-3: that its fact-sheet basis F-N14 had been downgraded from P0 to P1, that FM-3 kept Launch-Blocking anyway, that this was "either the right answer or motivated reasoning", and that the defence was E-3's pre-registered re-weighting rule. The PR #686 round-1 review found that the premise is false (S1-1), and it was the most consequential of the seven findings because this document's headline self-examination was built on it.

F-N14 is not FM-3's fact-sheet basis. FM-3's `Fact-sheet basis` line names F-N13, at `scripts/probe/playwright.sh:33` and `scripts/probe/vitest.sh:26`, and F-N13 was never downgraded. F-N14 is a k6 finding about an `unsupported-os:` prose string reaching `eval`, with no relationship to the shim, to playwright, or to vitest. There was no tension between the review and FM-3's tier, so there was nothing for the rule to resolve and nothing uncomfortable to sit with. I manufactured a dilemma and then congratulated myself for having pre-registered its resolution, which is worse than either having the dilemma or not having it.

The mechanism of the error is worth naming, because it is not carelessness in the usual sense. I read the round-1 review, saw a P0 go to P1, and reached for the rule I had written for exactly that event without going back to check which failure mode the downgraded finding actually sat under. The rule was ready, so I used it. A pre-registered rule creates an appetite for the situation it governs, and that appetite is itself a bias the pre-registration does not protect against. What F-N14's downgrade actually moves is C-8's test-count threshold and nothing else.

Round 2 is where the rule actually fired, and once rather than twice. F-N11 was reproduced and holds at P0, so FM-2 is untouched. F-N22 was downgraded to P1 and FM-8 kept Launch-Blocking under the rule. With the FM-3 application struck, this is the sole application, so it carries the entire weight of the pre-registration on its own and cannot be defended by "the rule has been applied consistently". What makes it defensible is that round 2 also strengthened FM-8's independent basis: `test_path_traversal_rejected` creates its escape target with `mktemp -d` at `hooks/_test/scaffold_test_stub.test.sh:283` before the hook runs, so the fixture cannot detect the escaped directory even with the missing assertion added. FM-8's tier rests on that, not on F-N22's label, and C-8 now says the fixture must be rewritten rather than extended. If a reviewer thinks the rule is doing the work instead, that is the finding I want.

The upstream review also produced a finding I should have caught here and did not. Three of the eight #684 findings were severity corrections, and the root cause was that no severity rubric had ever been written down. This document's own composite scores had the same defect in a milder form: the five-dimension weights come from `[skill:pre-mortem]`, so the scale existed, but only FM-6's score was derived from it and the other fifteen were asserted against it. That is L-2, filed as P2.

The sequence from there is worth recording, because the severity was wrong in the same direction and for the same reason as the three #684 severity corrections. L-2 was filed P2 on the reasoning that an asserted score is a presentation defect. The round-1 review supplied the evidence that moved it: an unchecked scale had already produced three separate corrections upstream, which makes it a correctness defect, so L-2 was raised to P1. It is now closed, by the `### Every composite is derived` table, which re-derives all sixteen composites from their five dimension columns under the published 25/25/20/15/15 weights and agrees with the risk table on all sixteen rows. Deriving them was not cosmetic: eleven composites moved down, two up, three were unchanged, and the count at 60-plus fell from 8 to 3, which is the record at `:105`.

The part still worth carrying is not the finding but its severity. P2 was too low, and the reason it was too low is the same reason the three #684 assignments were too low, which is that "the number is asserted rather than derived" was being scored as a documentation gap instead of as an unverified claim.

## Hostile-review remediation (PR #686, round 2)

Four reviewer findings, all reproduced independently against the branch before
being accepted, and all fixed here.

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| R2-S2-1 | S2 | FM-13 is marked `(override)` and is not one. Composite 43 is the `Monitor-after-ship` band, whose permitted urgencies are `Fast-Follow or Track` per `skills/pre-mortem/SKILL.md:133-138`; FM-13 is `Track`, inside its band | fixed. `:238` drops the marker; the override count goes 6 to 5 at four sites; the concession that the "both directions" argument does not survive is written into the pre-mortem at `:276` and here at `:69` |
| R2-S2-2 | S2 | The two published count commands select `/^\| FM-/`, which matches the risk table and the `### Every composite is derived` table both. The published outputs reproduce only under two undisclosed normalizations and one undisclosed exclusion | fixed. Both commands at `:102` and `:106` are replaced with forms scoped to the risk table and disclosing the suffix strip. The underlying claims were true and stay true |
| R2-S2-3 | S2 | `:127` still said only FM-6's composite is derived, the other fifteen asserted, and L-2 open at P2. `:82` already said L-2 is fixed. The document contradicted itself | fixed. `:127` rewritten to record the sequence (filed P2, raised to P1 on the round-1 evidence, closed by the derivation table) and to keep the part still worth carrying, which is that P2 was too low for the same reason the three #684 severity assignments were |
| R2-S3-1 | S3 | `plans/pre-mortem-682-python-rewrite.md:48` cites `plans/self-review-685.md:112` for the struck F-N14/FM-3 claim. Line 112 is blank | fixed. Citation moved to `:119-121`, which is the supporting text |

**Three findings inside the remediation, all author-found, recorded rather than
repaired quietly.**

The first is the L-6 sweep doing its job. The first draft of the R2-S2-1 fix
named `:238` and the override paragraph, because those are where the correction is
*argued*. Four further sites restate the count without arguing it: `:274` and
`:306` in the pre-mortem, and `:106` and `:69` here. `:69` is the one worth naming:
it spells the figure as the word "six" and states the "in both directions" claim in
a paragraph about whether the scoring is decoration, several sections away from any
override discussion. A grep for the digit would have missed it.

The second is a citation defect committed inside the document that fixes a citation
defect. The first draft of this section cited `plans/self-review-685.md:105` for the
override count; `:105` is the composite-movement claim and the override line is
`:106`. That is R2-S3-1's class exactly, a citation that resolves and supports
something other than what it is offered for, and the epic now has four instances of
it. It is left on the record because the frequency is the evidence for ticket #691,
and a suppressed instance is a datapoint removed from the case for the checker that
would have caught it.

The third is a control that does not discriminate. The superseded
`grep -c '(override)'` returns `7` both before and after this remediation. Before,
that is 6 table rows plus one prose restatement; after, 5 table rows plus two prose
mentions, the second being the paragraph recording the correction. The quantity the
bullet reports moved from 6 to 5 while its published command sat still, so running
that command as the check on this fix would have returned an unchanged number and
been read as confirmation. This is the same shape as #684's finding 3-2 and as
L-15's rule that a verification matrix needs a row required to come back positive.
Here the positive control was the anchored command, which does move, 6 to 5.

**Deferred, and why -- corrected in round 3.** The round-2 entry here treated two
separate corrections as one deferral and deferred both. They have different sources
and only one of them was ever blocked.

The first is the denominator: the fact sheet at `7d50cce` moved the prior-live count
to 27, H1's denominator to 55, the threshold to 28, and the preliminary structural
read to 10/5/40. **That commit is in this PR's base**, so nothing about it was ever
uncommitted, and the reason given for deferring it was false as soon as the base
advanced. It is applied in round 3 across nine sites, three of them executable
mechanisms rather than prose: FM-11's detection signal, E-1's classification base,
and the H1 kill criterion. C-11 itself needed no edit, because it states the
disposition table without a row count; FM-11's detection signal is where that count
lives.

The second is the severity split, `4 P0, 17 P1, 7 P2` to `5 P0, 14 P1, 9 P2`. That
one is still deferred and the original reason still holds: those figures exist only
in an unapplied draft on `feat/683-investigate-executable-path`, and propagating a
number from an uncommitted source is the defect this epic keeps finding rather than
a fix for it. It is genuinely independent of the denominator, because the split runs
over the 28 new findings alone and the denominator correction moved only the prior-live
side.

The lesson is the deferral itself. Bundling two corrections under one justification
means the weaker of the two justifications is never re-examined, because the bundle
is remembered by its strongest member. The check that would have caught it is cheap
and was not run: for each deferred item separately, name the commit its source lives
in and ask whether that commit is reachable from the PR base. Filed as L-8.

## Hostile-review remediation (PR #686, round 3)

Four reviewer findings, each reproduced independently against the branch before
being accepted, and all fixed here.

| ID | Sev | Finding | Disposition |
|---|---|---|---|
| R3-S2-1 | S2 | The R2-S2-1 override sweep missed two present-tense statements in this file that still said six. | fixed at `:82` and `:89`. Re-derived rather than accepted: `grep -cE '^\| FM-.*\(override\)' plans/pre-mortem-682-python-rewrite.md` -> `5`, and the five rows are FM-1, FM-2, FM-3, FM-14 upward and FM-15 upward |
| R3-S2-2 | S2 | R2-S2-2 named two commands with one defect and the remediation fixed one of them. The Band command was still unscoped and still published an output it does not print. | fixed at the band bullet: same `RISK` scoping as the tier bullet, and the output is now printed in a fence beside it rather than paraphrased inline |
| R3-S2-3 | S2 | The deferred 57/29/9/4 propagation became a live base mismatch once `7d50cce` entered this PR's base. | fixed. Nine sites propagated to 55/27/10/5, threshold 28. Base merged into the branch so the cited fact-sheet lines resolve against the version that will merge. Written up as L-8 |
| R3-S3-1 | S3 | The remediation created two fresh stale counts: the pre-mortem line count and the two-file citation total. | fixed. Both re-derived after the last edit of this commit rather than transcribed from the review; see the quantified-claims bullets |

**Three findings inside the remediation.**

The first is about the round-2 sweep, and it is sharper than a missed grep. That
sweep is written up above as "the L-6 sweep doing its job": it found four restatement
sites and singled out `:69` for spelling the figure as a word. It then missed two
more sites in this same file, one of which also spells it as a word. A sweep that
narrates its own thoroughness is the least likely thing in the document to be
re-swept, because the narration reads as evidence that the sweep ran. That is the
eighth instance of L-6's class in this epic and the first where the previous
instance's own fix is the thing that went stale.

The second is that R3-S2-3 was findable by me at any point after the base advanced,
by a command I had already written down. The round-2 deferral names
`feat/683-investigate-executable-path` explicitly as the branch the figures were
waiting on. Checking whether the thing you are waiting for has arrived is one
`git log HEAD..origin/<branch>` away, and I never ran it because "deferred" had
become a state rather than a condition. Deferrals need a stated resumption trigger
that is a command, in the same way kill criteria do; a deferral without one is
indistinguishable from an omission the moment its blocker clears.

A third, caught before it was pushed rather than after. The first draft of this
commit's `Self-Review-Source` trailer named sibling `260901-ivory-island` as the
round-3 reviewer. That session is `hr692-round2`. The round-3 reviewer of this PR is
`260901-ivory-swamp`, and the two differ by one word. Nothing in the PR thread
carries the session ID, so the trailer is unfalsifiable from the artifact it is
attached to and would have stood. It is recorded here because provenance trailers
are exactly the kind of claim that is never re-read: they are written once, checked
by nobody, and cited later as evidence of who reviewed what. The check is
`list_sessions` filtered to the label, and it takes one call.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Inherited "six P0" from the fact sheet's prose and built a design constraint and a kill criterion on it (L-1) | treated a summary line in an artifact I wrote yesterday as evidence rather than as a claim needing the same grep as anyone else's | one `grep -oE \| awk \| uniq -c` over the findings table, ~10s | correct 9 occurrences across two documents via a scripted replace, add a correction-check section, re-run all five ACs, ~7 min | ~42x |
| Ticket #685 blocked by `evaluate-ticket.sh` on "title lacks a verb token" | filed the ticket with a noun-phrase title without running the gate that every sub-ticket is required to pass | `bash scripts/discipline/evaluate-ticket.sh 685`, ~3s | read the heuristic at `scripts/discipline/evaluate-ticket.sh:119`, retitle via `gh issue edit` with a destructive-ok block, re-run, ~3 min | ~60x |
| Branched `feat/685` off `epic/682-python-executable-path`, where the fact sheet does not exist | assumed the #683 work was on the epic branch because the PR targets it, without checking that the PR is unmerged | `ls plans/investigate-682-executable-path.md` after checkout, ~2s | delete the branch and re-cut from `feat/683-investigate-executable-path`, ~1 min | ~30x |
| Six writing-prose:3 adverb hits found after the document was written | wrote the whole document before running the scan, again, despite this being a row in the #683 ledger | running the two prose scans against each chunk as written, ~5s | scripted rephrase of six sites plus rescan, ~2 min | ~24x |
| Shipped a merge candidate carrying a denominator its own PR base had already corrected (L-8, R3-S2-3) | wrote a deferral naming the branch it was waiting on and then never asked whether that branch had moved; "deferred" became a state rather than a condition with a resumption trigger | `git log HEAD..origin/feat/683-investigate-executable-path`, ~2s | merge the base, propagate 55/27/10/5 across nine sites, re-derive the two counts the edit invalidates, write the finding up, ~30 min | ~900x |
| The round-2 override sweep missed two sites in the file the sweep was written in (R3-S2-1) | reported the sweep's own thoroughness in prose, which made it the passage least likely to be re-swept | re-running the sweep's own anchored grep against the word forms as well as the digit, ~5s | two edits plus the write-up of why the previous fix went stale, ~5 min | ~60x |

Six rows. Four are the #683 ledger's stated pattern, acting on an internal belief that a sub-ten-second command would have checked, and the deferral row is the worst instance of it by ratio in either ticket: the command was not only available, it was implied by a sentence I had already written naming the branch. The branch cut is the one that is new in kind, an assumption about *git state* rather than about file contents. The sweep row is new in a different way: the skip was not a missing check but a narrated one, where writing down that the check ran displaced running it again. The prose-scan row is the one I have no excuse for, because the previous ticket's ledger names it and the fix was to scan first.

## Evidence-predates-work

The five AC checks, the citation resolver, the two prose scans, the fact-sheet count audit, and `evaluate-ticket.sh 685` were all executed against the assembled document, and the count audit produced L-1, which changed the document's numeric thresholds. The document's `file:line` citations were taken from the #683 fact sheet, which established them by same-turn execution on this branch, and the resolver re-checked every one against the working tree rather than trusting the fact sheet's transcription. The one thing this artifact does not claim is that the sixteen failure modes are exhaustive; a single adversarial pass by the author of the fact sheet is precisely the input a hostile review exists to correct, and L-3 names the specific place to look first.
