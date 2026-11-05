# Self-review artifact contract

Required when authoring the applicable Tier B/C artifact under the generic Self-review procedure. Tier-specific conditions below remain binding; selection of a project replacement uses its own declared contract instead.

## Artifact format

The full format below is required for Tier C. Tier B uses only `## Assumptions` and `## Test plan`; Tier A uses the short trailer record.

```
## Assumptions
Domain(s): <software engineering | data engineering | data analysis & visualization>
Geospatial cross-cut: <yes | no>
Goal source: <ticket #N | design-note path | quoted user-request paragraph>
Goal source verification: <paste the PASS line from `bash <scripts>/discipline/evaluate-ticket.sh <ticket-ref>`>
Plan reference: <path-or-link to the design note this diff implements>
Pre-author-inventory: <ticket-link#pre-author-inventory | plans/path.md#pre-author-inventory | NONE>
Investigate-artifact: <ticket-comment-link | committed-file-path | plans/investigate-*.md | TRIVIAL (with declaration below)>
Pre-mortem-artifact: <ticket-comment-link | committed-file-path | plans/pre-mortem-*.md | TRIVIAL (with declaration below)>
Hostile-review-artifact: <ticket-comment-link | path to cross-review artifact | WAIVED (prose-only, with ## Hostile-review-waiver below)>
Project-contribution: <what this work produces beyond itself — the project-level outcome, not "completed the ticket">

## Pre-implementation comprehension (the Junior's first deliverable)

Before writing any code, the Junior must post on the ticket a maximal
description of what the task consists of. "Maximal" means over-describe.
The cost of over-describing is one extra paragraph. The cost of
under-describing is implementing the wrong thing.

The description must include:
1. **Current behavior** — what happens now, with evidence (command
   output, file contents, hook output). Not "the gate doesn't check
   tickets" but "running pipeline-state-guard.sh with pre-mortem-476.md
   for ticket #482 produces 'artifacts present' — it should produce
   BLOCKED."
2. **Intended behavior** — what should happen instead, stated as
   observable behavior, not code to write.
3. **Steps to get there** — what files change, in what order, with
   what dependencies between them.
4. **Success criteria** — how you will verify the intended result was
   achieved. This must be testable in the target environment (not just
   the repo checkout).
5. **What could go wrong** — at least one risk. If the Junior says
   "nothing," the Junior hasn't thought about it.

## Senior adversarial checklist (pre-implementation verification)

After the Junior posts the task description, the Senior runs these
10 questions. The questions are presumptive — they assume mistakes
exist and ask what they are. The Senior cannot answer "nothing" to
question 1 without demonstrating they checked each category.

1. **What hasty mistakes did the Junior make in this description?**
   Name at least one thing the Junior got wrong, glossed over, or
   left vague. If the Senior says "none," the Senior isn't looking
   hard enough. The Junior always makes hasty mistakes — the question
   is which ones, not whether.
2. **Did the Junior state the intended result as observable behavior?**
   "Add a ticket check" is code-to-write. "Wrong-ticket artifacts are
   blocked" is observable behavior. If the Junior described means
   instead of ends, send it back.
3. **Is the Junior over-focusing on one part?**
   What's getting all the Junior's attention, and what's being
   neglected? Tunnel vision on the code fix while ignoring deployment,
   testing, environment differences, or documentation is the most
   common form.
4. **What did the Junior leave out or minimize?**
   Adjacent concerns, deployment steps, environmental factors,
   edge cases, backwards compatibility.
5. **Has the Junior read the relevant prior work?**
   Prior tickets, skill files, documentation, existing hooks,
   recent git history. Can the Junior cite specific details, or
   are they working from assumptions?
6. **Is the Junior in the right environment?**
   Right repo, right branch, right directory. Does the Junior know
   where the deployed code runs vs. where the repo checkout lives?
7. **Does the Junior's plan test the failure case?**
   Happy-path-only testing is not testing. If the task is "block
   wrong-ticket artifacts," the test must include a wrong-ticket
   artifact that gets blocked.
8. **Instance or class?**
   Is the Junior fixing one occurrence or every occurrence? If the
   bug exists in one gate, does it also exist in the other?
9. **Does "done" match the ticket?**
   The Junior's definition of done is "code committed." The ticket's
   definition of done is "intended behavior observable in production."
   These are different.
10. **What would the Junior skip if nobody was watching?**
    Model the Junior's incentives. The Junior optimizes for speed.
    Which verification steps will the Junior rationalize away?
    Pre-commit to not skipping them.

Implementation does not begin until the Senior is satisfied.
Post both the Junior's description and the Senior's response on
the ticket.

## Peer review (the Junior's checklist -- mechanics, correctness, craft floor)
For each applicable shelf: what was checked, what was found.
Grep / test-output / file-read evidence inline per `_writing-claims-rules.md`.
Empty sections allowed only when the diff genuinely doesn't engage
that shelf; the omission itself is auditable.

## Lead review (the Lead's adversarial pass -- did the Junior actually solve this?)
Domain-tagged. For each finding and each dismissal in the peer
review: did this close the class or defer it? For each domain's
affirmative standards: does it hold, with evidence?
Approach-fit verdict. Blast radius declared. Sequencing assumption
that has to hold for this to be the right move.

## Findings
Classify each Lead finding by priority. The pre-push hook blocks
on unresolved P1 rows. Format:

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|

Priority levels (aligned with hostile-review S1/S2/S3):
- P1 (≈S1): Blocks push. Wrong on normal input, exploitable, or
  violates a stated invariant. Resolution must be "fixed".
- P2 (≈S2): Does not block push. Edge-case data issues, resource
  leaks, missing validation. Agent files a ticket; resolution is
  "ticket #NNN".
- P3 (≈S3): Noted in artifact. Design debt, defense-in-depth gaps.
  Resolution is "noted".

"No findings." is valid when the Lead produced none.

## Quantified claims
For every specific count stated in this PR's body, commit messages,
or this artifact itself, paste the command and output that produced it.
Format:
  - "<quoted claim>" -- `<command>` → <output>
An empty section when the PR body contains specific counts is a
writing-claims:8 violation visible to anyone reading the artifact.

## Rework ledger
For every rework cycle in this task (commit-amend, re-deploy,
hook block → fix → retry, test failure → fix → rerun), log:

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|

An empty ledger is valid (no rework occurred). A missing ledger
when rework visibly occurred (amend commits in the branch log,
multiple deploy cycles) is a writing-claims violation.

## Evidence-predates-work
Artifact: <path to this artifact>
First-added commit: <paste output of `git log -1 --diff-filter=A --follow --format=%H -- <artifact-path>`>
Work commit: <paste `git rev-parse HEAD`>
Verification: <paste output of `git merge-base --is-ancestor <first-added> <work-commit>; echo $?` -- must be 0>
```

## Pre-author-inventory field

The `Pre-author-inventory:` field in the Assumptions section is a **required
composability link** between this skill and
[rule:authoring-against-state]:6.

Before authoring any runtime artifact whose contact points trigger rules 1-5 of
that shelf, the agent must complete a pre-author investigation and record its
findings in the ticket (a `## Pre-author inventory` section per the template in
the shelf). The self-review artifact must then point at that record:

```
Pre-author-inventory: enterprise#2094#pre-author-inventory
```

or for session-local plan files:

```
Pre-author-inventory: plans/2094-silver-exp/pre-author-inventory.md
```

This makes the omission structurally visible: an agent that skipped the
pre-investigation cannot populate this field without fabricating a link, and a
fabricated link fails the first spot check.

**When NONE is acceptable:** if the change does not trigger any of the five
authoring-against-state contact categories (data-shape, config-state, topology,
plan-shape, version-resolution), the field may be `NONE` -- but only when a
`Trivial-against-state:` declaration is also present in the artifact. The
hook checks for the declaration; absence of the declaration with a NONE value
is a block.

**The field is NOT a quality gate on the inventory itself.** The hook checks
structural presence (field exists, value non-empty or NONE+declaration). Content
quality -- whether the inventory actually covered the relevant surfaces, whether
the hypothesis was falsifiable, whether the seven steps were followed -- remains
operator-auditable. The field's purpose is to make the composability explicit
and to block the pattern where a structurally-complete self-review was written
without any pre-investigation at all.

## Investigate-artifact and Pre-mortem-artifact fields

The `Investigate-artifact:` and `Pre-mortem-artifact:` fields in the
Assumptions section are **required composability links** between this
skill and the `investigate` → `pre-mortem` → implementation pipeline
defined in `think` Step 7.

For any non-trivial work, the agent must produce an investigate artifact
and a pre-mortem artifact before any artifact CRUD. Investigation is
non-discretionary (see `investigate/SKILL.md`). The artifacts live on the
ticket (preferred), in a committed repo file, or as a last resort in the
session plans folder. The self-review artifact must point at those records.

**When TRIVIAL is acceptable:** if the work is a single-line fix, typo,
doc-only edit, or pure research that does not touch existing entities or
modify behavior, the fields may be `TRIVIAL` -- but only when a
`## Trivial-investigation declaration` block is also present in the
artifact. The block follows the same format as Trivial-change
declaration (Category / Cannot produce error / Evidence / Falsification).

```
## Trivial-investigation declaration

Category: <single-line-fix | doc-only | config-only | test-only>
Cannot produce error: <one sentence stating why investigation would not
                       have surfaced additional context>
Evidence: <command output proving no entity-touching changes -- e.g.
          `git diff --stat` showing only test files changed>
Falsification: <observable that would prove skipping investigation was
                wrong -- e.g. "a downstream consumer breaks because of
                an assumption I didn't verify">
```

**Category is a default-deny allowlist.** The four tokens above are the
entire vocabulary for `Trivial-investigation`. Any other value —
including `local-only`, `internal-refactor`, `scoped-only`, and any
invented token — is rejected by `scripts/discipline/check-trivial-claim.sh`
with a diagnostic naming `[rule:writing-rules]` writing-rules:5 and
this section.

`local-only` deserves specific attention: it IS a legitimate Category
for `## Trivial-against-state declaration` blocks (per
`[rule:authoring-against-state]`), where it means "change to a code
path that does not run under shared cluster state." That token is
scoped to the authoring-against-state contact-point analysis. For
skipping investigation, the four tokens above are the only allowed
answers. If your intent was the authoring-against-state claim, use
that block instead. Otherwise, produce an investigate artifact.

**External-shape-modeling code is never eligible for
`Trivial-investigation` regardless of Category.** When the push diff
touches scanners, parsers, linters, hooks, or any code that models an
external shape space (source syntax, config, CLI arguments, API
payloads, schemas, notebooks, framework conventions), the four-token
allowlist is bypassed entirely — no `Trivial-investigation`
declaration is acceptable. The correct artifact is a full
`[rule:authoring-against-state]` step-6 inventory covering the six
required fields (Inputs read / Knowledge requirements / Contact-point
measurements / Surface areas / Hypothesis / Conclusions). This is
because the errors external-shape-modeling code produces are silent
misses against a shape space the author has not enumerated; the
inventory step IS the enumeration. See `[rule:writing-rules]`
writing-rules:5 for the filename patterns that trigger this bypass.

**Worked example (invalid — do not use):**

```
Investigate-artifact: TRIVIAL

## Trivial-investigation declaration

Category: local-only
Cannot produce error: AST logic, no external contact.
Evidence: git diff.
Falsification: NOT trivial if any external resource contacted.
```

This is what R5-R10 of the detect-ai-fingerprints scanner arc shipped,
five times. The check now fails it with two diagnostics: (1) `local-only`
is outside the four-token allowlist, and (2) if the diff touches
`skills/*/scan*.py` or `hooks/**` or similar, the never-trivial trigger
fires. The correct artifact is a full authoring-against-state:6
inventory naming the Python shape space the scanner claims to model.

**The enforcement mechanism:** the hook (`hooks/git/self-review.sh`)
checks structural presence of both fields, then delegates the
declaration block's content validation to
`scripts/discipline/check-trivial-claim.sh` with the current diff
scope. A missing or empty field blocks the push. `TRIVIAL` without the
declaration block also blocks. A declaration block with a Category
outside the allowlist blocks. A declaration block on a push that
touches external-shape-modeling code blocks regardless of Category.
Content quality of the investigate/pre-mortem artifacts themselves --
whether they trace the impact chain, classify risks -- remains
operator-auditable. The fields exist to make the omission structurally
visible and to block the pattern where agents skip `investigate` and
`pre-mortem` and go straight from `think` to implementation.

**Why this works where the think Step 7 checklist didn't:** Think Step 7
is a mental checklist inside the design workflow. The agent checks the
boxes and moves on. Self-review is a pre-push gate with hook
enforcement. By requiring the artifact paths in self-review, the
enforcement happens at the push boundary -- the agent cannot push without
either producing the artifacts or explicitly declaring the work trivial
with falsifiable evidence.

## Hostile-review-artifact field

The `Hostile-review-artifact:` field in the Assumptions section links the
self-review to independent hostile review evidence. The pre-push hook
enforces this field when the diff touches executable code.

Valid values:

- **Ticket comment link** -- URL of a cross-review findings comment on the
  ticket (preferred; most durable).
- **File path** -- path to a committed cross-review artifact or session
  plans file. The hook verifies the file exists.
- **WAIVED** -- accepted ONLY when the diff does not touch executable code
  (`.py`, `.sh`, `.js`, `.ts`, `.sql`, `.rb`, `.go`, `.rs`, `.java`, `.c`,
  `.cpp`, `.h`). Requires a `## Hostile-review-waiver` declaration:

```
## Hostile-review-waiver
Reason: <why hostile review cannot be obtained>
Scope: <what files are touched>
Compensating-control: <alternative verification performed>
```

The executable-file guard exists because hostile review is the only
independent validation in the pipeline. Every other artifact (investigate,
pre-mortem, self-review) is produced by the same agent that wrote the code.
For executable changes, independent review is non-waivable.

## Trivial-change declaration (when no ticket cited)

If the work is genuinely too small to warrant a ticket -- typo fix,
doc-only edit, single-character revert -- the artifact may include
this block in place of `Goal source verification`. The block itself
requires the same evidence chain as any "this doesn't apply" claim
(`_writing-rules-rules.md` writing-rules:4):

```
## Trivial-change declaration

Category: <token from the writing-rules:5 controlled vocabulary --
           prose-only-docs | comments-only | whitespace-only |
           commit-msg-only | private-rename |
           descriptive-docstring-fix | fixed-string-correction>
Cannot produce error: <one sentence stating the claim that this change
                       cannot generate empirical evidence contradicting
                       the agent's model of the system -- falsifiable>
Evidence: <command output proving the Category's Evidence-shape
          requirement per writing-rules:5 -- e.g. for `prose-only-docs`,
          the grep showing no behavior tokens in changed regions; for
          `private-rename`, the grep showing only-the-rename-site>
Falsification: <observable that would prove the Cannot-produce-error
                claim wrong; if this observable later surfaces, this
                block is the post-error revision trigger>
```

The local hook (`hooks/git/self-review.sh`) and the canonical script
(`scripts/discipline/check-trivial-claim.sh`) validate that all three
fields are present and that the Evidence field contains a verifiable
observation token (command output, file path with extension, fenced
code block, stat/count, or URL). Free-text assertions like "obviously
trivial" or "minor cleanup" fail.

### When the Falsification observable surfaces

The Falsification field is the writing-rules:6 trigger. If the observable named there later surfaces -- an `AttributeError` matching the renamed symbol, a behavior claim acted on from prose-only-docs, a non-comment line changed by what was claimed comments-only -- the Trivial-change declaration was wrong, and the response is **not** to just fix the bug.

Per writing-rules:6 (and [skill:post-error-revision]):

1. File a ticket retroactively, citing the failed Trivial-change block as Goal source.
2. Append a `## Post-error revision` block to the new ticket with the five required fields (Triggered by / Observed / Falsified assumption / Revised model / Implication).
3. THEN draft the fix PR with a `Refs:` + `Post-error-revision:` trailer pair.

Skipping this and just pushing the fix re-runs the same Assumption on the next change. The Trivial-change Falsification field exists to make the trigger explicit; ignoring it when it fires defeats the whole writing-rules:5 -> writing-rules:6 loop.

## Exemption blocks

When a specific `evaluate-ticket` criterion doesn't apply to your
work (e.g., a docs-only ticket can't state a falsification criterion
in the writing-tests:1 shape), paste an exemption block per criterion:

```
## Exemption: <criterion-name>

Reason: <why this criterion doesn't apply>
Evidence: <command output or verifiable observation supporting the
          exemption -- e.g. `git diff --stat | grep -v '\.md$'` returns
          no rows, proving no non-doc files changed>
Falsification: <observable that would make this exemption wrong>
```

Same validation as Trivial-change declaration. Same enforcement path.

## Adversarial shape audit

Required subsection when the diff modifies external-shape-modeling code (per `[rule:writing-rules]` writing-rules:5 definition: scanners, parsers, linters, hooks that infer semantics from source syntax, config, CLI arguments, API payloads, schemas, notebooks, or framework conventions — not Python-specific, not scanner-specific).

The subsection answers four questions, each requiring same-turn evidence per `[rule:verify-before-execute]` and `[rule:writing-claims]` writing-claims:2. Missing subsection when the diff touches ESM code is a self-review block. See `[skill:shape-space-audit]` for the discipline this subsection consumes.

```
## Adversarial shape audit

Shape space: <name the class of inputs, formats, or idioms this code claims to model>

Fixture-covered shapes: <enumeration with count per shape; cite fixture file + test name for each>

Prose-vs-implementation gap: <shapes SKILL.md prose claims to cover that fixtures do NOT exercise; each row either references a follow-up ticket OR includes an explicit "documented over-claim, corrected in this PR" line>

Adversarial frame this round: <one of: Scala/JVM skeptic | PyPI-top-100 CI operator | security engineer | Python newcomer | linter author (per shape-space-audit/SKILL.md rotation frames)>
Adversarial fixture from frame: <at least one adversarial fixture constructed from that frame's perspective; cite file path + how it exercises the frame's typical failure mode>
```

The four fields are load-bearing. Rationale per field:

- **Shape space** — makes the class-membership claim explicit rather than leaving it implicit in the code. Any downstream `covered` claim (per `[rule:writing-rules]` writing-rules:8) must be measurable against this stated shape space.
- **Fixture-covered shapes** — grounds the coverage claim in executable evidence. Prevents the writing-claims:3 class-membership over-claim shape ("catches try/except optional-import patterns" without enumeration).
- **Prose-vs-implementation gap** — surfaces the honest gap between SKILL.md aspirations and shipped fixtures. Each gap row either becomes a follow-up ticket OR gets closed in the current PR. Silent gap = writing-claims:3 violation.
- **Adversarial frame this round** — forces frame alternation (not just provider alternation). The R11-meta failure mode was ten rounds of provider alternation without frame alternation; this field is the mechanical fix.

**When one or more fields is genuinely N/A:** state `N/A: <one-sentence reason>` for that field. Silent omission fails the hook check. For example, a diff that adds ONLY a new fixture (no scanner change) can honestly declare `Prose-vs-implementation gap: N/A — this PR adds a fixture for the shape enumerated in <table row>; no scanner logic changed.`

**Composition with existing sections above:**

- The Assumptions block still ships (with Investigate-artifact / Pre-mortem-artifact / Hostile-review-artifact fields) — Adversarial shape audit is an ADDITION, not a replacement.
- If the diff also qualifies as authoring-against-state (per `[rule:authoring-against-state]` authoring-against-state:6), the full inventory ships too — shape audit is one layer of that inventory, not the whole thing.
- Trivial-change and Trivial-investigation declarations are INCOMPATIBLE with Adversarial shape audit. External-shape-modeling code is never-trivial per `[rule:writing-rules]` writing-rules:5; if the diff touches ESM code, no Trivial-* declaration is valid, and the Adversarial shape audit subsection is required.

**Enforcement:** planned. `hooks/git/self-review.sh` reuses PR A's `check-trivial-claim.sh --diff-files` external-shape-modeling detection to determine when this subsection is required. Missing section when the diff touches ESM code → BLOCK with diagnostic naming the four required fields. Presence-check only in v1; field-quality validation (does the enumeration actually list shapes; is the frame actually one of the five) is judgment-enforced via bounded hostile review pass. Mechanical field-quality validation is tracked as a v1.1 follow-up.

**Empirical evidence:** `siege-analytics/claude-configs-public#814` self-review dogfood already ships an implicit shape audit (the ESM never-trivial rule surfaced the requirement) but without the four-field structure — this subsection makes the structure explicit for future PRs. `siege-analytics/claude-configs-public#828` self-review is next-easiest fixture: a hook-editing PR touching ESM code that would naturally produce an Adversarial shape audit block if this subsection had been live at authoring time.

