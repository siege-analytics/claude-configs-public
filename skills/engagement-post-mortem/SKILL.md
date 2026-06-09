---
name: engagement-post-mortem
description: "Retrospective discipline for completed multi-PR / multi-decision engagement arcs. Classifies each artifact and decision as Confirmed (cost was paid), Latent (substance survived but process was broken — the substance-survived-by-luck cell), or Avoided (structural truth visible in retrospect that nobody named at the time). Sibling to `[skill:pre-mortem]` (adversarial risk gate before implementation) and `[skill:post-mortem]` (per-confirmed-failure root-cause analysis). Operates on the FULL ENGAGEMENT including its meta-arc, even when no single confirmed failure occurred. Runs after engagement close."
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Engagement Post-Mortem

Retrospective classification across an engagement arc. Given what actually shipped, ask: "Where did cost get paid? Where did substance survive but process broke? What structural truths could everyone see in retrospect and nobody named at the time?"

## Why

Per-failure post-mortems (`[skill:post-mortem]`) trace one bug back through the pipeline. Pre-mortems (`[skill:pre-mortem]`) classify risks before implementation. Neither captures the engagement-arc shape: multi-PR / multi-decision / multi-session work where the substance survives but the *path* the work took drifted from intent.

The failure this skill prevents: **substance survival mistaken for process validation.** An engagement that ships nine functional PRs while violating the discipline that produced them looks successful — and quietly trains the cohort to skip the discipline next time. The luck runs out on the engagement after; nobody knows why.

The metaphor (operator framing 2026-06-09T06:50Z): "In boxing I consume tapes. I look at combinations to see where they failed, I look at footwork to see where I mis-stepped. I listen to what I played over changes while reading lead sheets. And I do a rigorous post-mortem to learn."

- **Combinations** — sequences of decisions, PRs, messages. Most engagement failures are sequence-failures, not individual-decision failures (Step 4).
- **Footwork** — foundational small moves (the handshake before the PR, the grep before the claim). Footwork misstep → visible failure later (Step 5).
- **Lead sheet vs recording** — what you intended (rules, standing approvals, design notes) vs what you played (diffs, merges, messages). Most retrospectives read only the recording; the discipline is reading both (Step 6).

## Framework: Confirmed / Latent / Avoided

### Confirmed (real cost was paid)

A failure that:
- Produced measurable cost (revert, fix-PR, defect that shipped, dup work, lost time, broken artifact).
- Has a citable artifact (commit SHA / PR # / message ID / ticket #).
- Is grounded in the engagement's actual tape, not in counterfactual reasoning.

Confirmed failures get root-cause analysis via `[skill:post-mortem]` (one per failure). The engagement-post-mortem names them and points to where each per-failure analysis lives.

**Examples from the 2026-06-09 pour-now engagement:**
- Duplicate Iron rule 5 in `deploy-develop/SKILL.md` (PR #35) — cost: fix-PR #36.
- `[no-migration-check]` cheat-sheet drift from hook regex (PR #32) — cost: fix-PR #36.
- Citation pointing at wrong file in PR #35 — cost: fix-PR #36.
- Shell-syntax-broken bash placeholder in PR #33 — cost: fix-PR #36.
- Duplicate PR #31 racing PR #29 — cost: one closed PR + comment thread + reviewer attention.

### Latent (substance survived, process broke)

A failure that:
- DID NOT produce measurable cost — substance held under post-hoc review.
- DID involve a definite process violation (review skipped, gate not fired, rule violated).
- Has the conditions for cost present even though cost wasn't realized this time.

Latent failures are the **substance-survived-by-luck cell**. They look like success and are the most insidious failure mode the existing rules are written to address. A future engagement on broader surfaces running the same broken process will eventually produce Confirmed failures.

Latent failures are documented to prevent the cohort from training on the luck. Each must cite the process violation and name what the cost *would have been* if substance hadn't held.

**Examples from the 2026-06-09 pour-now engagement:**
- PRs #32, #33, #34, #35 — all merged solo within 7-30 seconds, no counterpart review. Substance held under post-hoc spot-check. Process violation: standing-approval misread. Cost-if-substance-had-failed: bad framework shipped, downstream operator-trap.
- The diagnosis doc — written solo, not reviewed. Substance held under operator read. Cost-if-substance-had-failed: a flawed canonical reference doc shipped to siege.
- Workspace `settings.local.json` — written solo, not verified to load. Process violation: no functional verification. Cost-if-substance-had-failed: hooks silently inactive.

### Avoided (structural truth nobody named)

A failure shape that:
- Was visible in retrospect (the engagement's tape shows it clearly).
- Was NOT named at the time despite being uncomfortable enough that naming would have changed behavior.
- Often involves coordination, scope, organizational structure, or architectural debt.

Avoided failures don't have a clean fix within the engagement. They must be documented in the post-mortem with rationale for why they went unnamed and a trigger for revisiting.

**Examples from the 2026-06-09 pour-now engagement:**
- **Parallel-actor invisibility** — an external actor (gh author `dheerajchand`, body-attribution "windy-bronze cohort", underlying session unidentified) opened PR #36 while I (also operating as smooth-gold cohort) was filing tracking issues for the same findings. Visible in `gh pr list` retroactively; nobody checked at the time. Why unnamed: the cohort identity convention conflated "another agent under cohort identity" with "the operator acting under the same gh PAT" — both fall into a single visibility gap.
- **Cohort-coherence drift** — "Theme A → Theme G → Gap A → Gap D" labels leaked from coordination chat into PR titles/bodies as canonical artifacts. Visible to anyone git-log-spelunking six months out. Why unnamed: each transition was individually coherent; cumulative incoherence had no slot in any discipline.
- **Framework-doesn't-eat-its-own-dogfood** — the engagement built a hook framework that enforces discipline on consumer PRs (`business-backend` migrations, ticket-authoring decomposition) but no hook enforces the same discipline on the framework's own PRs. Visible to anyone reading the hook scope. Why unnamed: hooks were authored from the consumer-side perspective; the framework-side perspective wasn't surfaced until frosty-panther's hostile review.

## The engagement-post-mortem process

### Step 1: Assemble the tape sources

Pull the artifacts. **Memory is suspect; the tape is canonical.** The post-mortem operates on what shipped, not on what was intended.

Required tape sources:

- `git log --since=<start> --until=<end> --pretty=format:'%h %ai %s'` per repo touched during the engagement.
- `gh pr list --search 'created:<start>..<end>' --state all` per repo.
- `gh issue list --search 'created:<start>..<end>' --state all`.
- Agent-message history (session transcripts, message logs).
- Tool-call timestamps from session JSONL files.
- Canonical memory entries written or extended during the engagement, with `git log` against the memory directory if version-tracked.
- Operator messages timestamped from the conversation transcript.

If you find yourself writing "I think this happened around..." or "around 03:30Z" — stop. Grep the artifact. The tape has the exact timestamp.

### Step 1b: Tape integrity check

Before classification, verify the tape itself is sound. The most common tape-integrity failure is **memory-substituted-for-artifact** — the agent recalls events without re-checking the source. Symptoms:

- Reconstructed timestamps without `git show` / `gh api` citations.
- "PRs #32-#35" bundled as a phrase rather than four separate timeline rows.
- Operator messages quoted from memory rather than from session transcript.
- Inferred motivations ("I think the operator meant X") presented as established fact.

For each, re-run the artifact pull. If a timestamp can't be exactly cited, the row is removed from the timeline until it is. Reconstructed engagement narratives that survive into Step 3+ contaminate every subsequent classification.

This is not a soft check. The dogfooding incident that motivated this rule: the 2026-06-09 engagement-post-mortem's first draft initially listed PR #36 as authored by "smooth-gold cohort (parallel, unknown to me)" without verifying — the `gh` metadata shows author `dheerajchand`. Initial draft conflated body-text attribution with GitHub author; corrected after re-pulling the artifact.

### Step 2: Timeline reconstruction

Merge the tape sources into a unified chronological log. Every entry has:

- Timestamp (UTC, exact to seconds where the artifact provides it).
- Actor (session ID for agents, named human for operators).
- Action (one sentence; the action, not the inference about why).
- Artifact reference (PR #, commit SHA, message ID, file path).

Mark transitions explicitly — points where the engagement's character changed (operator intervention, mode shift, scope expansion, queue-state change). Mark time gaps — idle windows, blocked waits, inbox-lag gaps. **The gap itself is signal.**

Common timeline-pass failures to avoid:

- Bundling close-in-time events ("PRs #32-#35"). Each gets its own line; the spacing reveals cadence.
- Skipping "trivial" events. They're often the footwork.
- Excluding meta-events (operator's mid-engagement messages, rate-limit signals, your own mode shifts).
- Editorializing in the Action column. Save analysis for later steps.

### Step 3: Classify each artifact and decision

For every PR / ticket / decision / message in the timeline, ask two questions:

- **Substance check:** does the artifact itself work? Does the code function? Does the design hold? Did factual claims survive verification?
- **Process check:** did the work reach the artifact through the discipline that exists for it? Was review-then-merge honored? Was the standing approval correctly interpreted? Was the asymmetric-expertise counterpart consulted?

Classify into the framework:

| Substance | Process | Classification |
|---|---|---|
| pass | pass | Healthy (not a finding) |
| pass | **fail** | **Latent** |
| **fail** | pass | **Confirmed** (process found nothing wrong, but the artifact is broken — a different process gap) |
| **fail** | **fail** | **Confirmed** (the canonical case) |

The (substance: pass, process: fail) cell is Latent. The other two failure cells are Confirmed. If both cells are empty, the engagement was healthy AND the post-mortem still has Avoided to surface — Step 3b.

### Step 3b: Surface Avoided patterns

For each combination of Confirmed and Latent findings, ask: what structural truth made this possible that nobody named at the time?

Probes:

- "What were we choosing not to look at while this was happening?"
- "What did the cohort find uncomfortable to name?"
- "What would the engagement have done differently if [common-knowledge-but-unnamed truth X] had been spoken aloud?"

Avoided findings are not Confirmed failures and not Latent failures. They're structural — usually involving coordination, scope, scope-creep, or framework-self-application. They need their own findings record because:

1. They explain WHY the Latent cell is large (the Avoided structural truth disables the discipline that would have caught the Latent failures).
2. They don't fix themselves in subsequent work unless explicitly surfaced — they remain Avoided.

### Named patterns

These are recurring shapes identified through dogfooding. Check for each explicitly during Steps 3 and 3b.

#### Self-violation-while-authoring pattern (Latent)

**Pattern:** The engagement's output includes a new rule or skill. The engagement itself violates that rule or skill within the same session — often within the same hour.

**How to detect:** For each rule/skill authored during the engagement, ask: "did the engagement comply with this rule when it was operating?" The default answer should be skeptical — rules are usually authored because the author has internalized the lesson, not because they exhibit the behavior.

**Classification:** Latent if substance survived; Confirmed if a defect shipped. In the 2026-06-09 engagement: `feedback_procedural_correctness_not_urgency_resistance` rule 4 ("grep hooks before shipping") was violated by the originating PR (#32) within the hour — Confirmed via the bypass-marker drift that fix-PR #36 corrected.

#### Substance-survival-mistaken-for-process-validation pattern (Latent → Confirmed if recurring)

**Pattern:** A series of solo-author auto-merges where each individual artifact's substance survives post-hoc review. The cohort treats the substance-survival as validation that the process is fine.

**How to detect:** Count solo-author-merges within a short time window. If more than 3 in 30 minutes, the cohort has entered the substance-survival cycle.

**Classification:** Latent on first occurrence. Promoted to Confirmed if recurring across engagements (which the 2026-06-09 + 2026-06-08 retrospective will determine).

#### Parallel-actor-invisibility pattern (Avoided)

**Pattern:** Multiple sessions operating under the same cohort identity (`smooth-gold cohort`) take independent action on the same finding set with no mutual visibility. Each is correct from its vantage; the cumulative effect is duplicate work.

**How to detect:** After spawning a child for review or fix work, the parent's next action assumes serial coordination. Check: did the parent verify no sibling was about to act on the same surface?

**Classification:** Avoided. The cohort-identity convention disabled the visibility mechanism. Naming the pattern requires admitting that the cohort-identity convention has a design gap — uncomfortable enough that the gap goes unnamed across engagements.

#### Framework-doesn't-eat-its-own-dogfood pattern (Avoided)

**Pattern:** The engagement ships a discipline-enforcement mechanism (hook, gate, rule) scoped to consumer behavior. The framework's own work is not subjected to the same mechanism.

**How to detect:** For each enforcement mechanism shipped, ask: would it have caught the engagement's own failures if applied to the engagement? If yes — the framework didn't apply it to itself.

**Classification:** Avoided. The framework-perspective is uncomfortable to apply to oneself; it gets surfaced by external review rather than self-review.

### Step 4: Combinations (sequence failures)

For the Confirmed and Latent findings from Step 3, identify the SEQUENCE of decisions that produced them. **Most engagement failures are sequence failures, not individual-decision failures.**

Canonical sequence-failure shapes:

- **Race conditions** — two actors moving on the same surface independently.
- **Inbox-lag races** — async messaging produces parallel work that should have been serial.
- **Standing-approval misreads** — the conditional gate dropped between message N and action N+5.
- **Cohort-coherence drift** — Theme A → Theme B → Theme C, each individually coherent, taken together incoherent.
- **Velocity overshoot** — early successes accelerate the cadence past what review can keep up with.
- **Self-violation under load** — the rule being authored is the rule being violated while authoring it.

For each combination failure, identify the **earliest possible interrupt point** — the footwork that would have prevented this sequence (Step 5 expands on this).

### Step 5: Footwork (foundation gaps)

For each Confirmed, Latent, and sequence failure from Steps 3-4, identify the missing footwork — the foundational habit whose absence enabled the visible failure.

Canonical footwork patterns:

- **The handshake before the PR** — a one-line "I'm about to draft X" check.
- **The grep before the claim** — verify symbol existence / regex match / state before stating it.
- **The wait before the merge** — the 60-second pause for review.
- **The re-read of the standing instruction** — re-grounding the conditional before each covered action.
- **The artifact lookup before the cite** — confirming "PR #29" vs "PR #31" against actual merge state.
- **The cross-rule consistency check** — grepping the hook to confirm a cheat-sheet's bypass-marker matches.

For each missing footwork, classify:

- **Skipped** (the rule exists; the operator knows it; it wasn't applied under pressure) → mechanical enforcement needed (hook, gate, build-check).
- **Absent** (no rule names this footwork yet) → teaching needed (new rule, skill, or memory entry).

Skipped footwork has higher priority than Absent — skipped means the rule already exists but isn't operative; the fix is mechanical enforcement of an existing rule, which is the highest-leverage intervention available.

### Step 6: Intent vs execution (lead sheet vs recording)

List the explicit intent sources active during the engagement:

- Standing approvals from the operator (with timestamp).
- Canonical rules (`[rule:standing-approval]`, `[rule:definition-of-done]`, etc.) referenced in the engagement.
- Pre-engagement plans, design notes, or tickets.
- Canonical skills the engagement was operating under.
- Workspace canonical memory entries.

For each intent source, identify 3-5 specific predictions: "if we were following `[rule:X]`, we would have done Y here."

Walk the actual execution and check each prediction. For each prediction that failed, identify the **drift point** — when the actual execution deviated from the intended — and the **cause of drift** (label it).

The most dangerous deviation pattern (caught here, not in earlier steps): **the rule being authored is the rule being violated while authoring it.** Self-application is a strong signal that the rule needs mechanical enforcement, not just documentation.

## Engagement-post-mortem artifact format

```markdown
# Engagement post-mortem — <engagement name> (<UTC date>)

**Author:** <session-id>
**Method:** `[skill:engagement-post-mortem]`
**Stance:** blameless; self-application included

## Scope
<start/end timestamps, repos touched, sessions involved, what got built>

## Tape sources
<list of artifacts pulled — git refs, PR numbers, ticket numbers, message-thread IDs, session paths, file paths>

## Step 2 — Timeline
<chronological log with citations>
<significant time gaps named>

## Step 3 — Findings

### Confirmed (real costs paid)
For each:
- **Failure:** <name>
- **Artifact:** <PR# / commit SHA / ticket #>
- **Cost:** <what was paid — revert PR, fix-PR, defect, lost time>
- **Per-failure post-mortem:** `[skill:post-mortem]` invocation needed? <yes — link to where | no — explain>

### Latent (substance survived, process broke)
For each:
- **Process violation:** <what discipline was skipped>
- **Substance survival:** <what kept the substance correct despite the broken process>
- **Cost-if-substance-had-failed:** <what would have shipped>
- **Recurrence risk:** <will this happen again under similar conditions?>

### Avoided (structural truths unnamed)
For each:
- **Truth:** <the uncomfortable structural observation>
- **Why unnamed:** <what made naming costly during the engagement>
- **Cost of remaining unnamed:** <what gets worse>
- **Trigger for revisiting:** <when this should be re-evaluated>

## Step 4 — Combinations
<sequence failures with earliest-interrupt points>

## Step 5 — Footwork
<missing-footwork inventory; skipped vs absent; mechanical vs training disposition>

## Step 6 — Intent vs execution
<per-source predictions vs actuals; drift points named>

## What worked
<positive signals; cohort-level patterns to repeat>

## Carry-forward changes
<small, specific, actionable; cite the step that surfaced each; cite where it gets filed>

## Open questions for operator
<things requiring operator judgment to sequence>

— <author>, <UTC timestamp>
```

## Solo-agent adaptation

The engagement-post-mortem's structure was designed assuming team retrospectives. In solo-agent execution:

- **There is no room full of perspectives.** Adopt the adversarial stance deliberately. The Avoided category specifically rewards naming uncomfortable truths the agent has been suppressing.
- **The agent's substance-survival bias is strong.** The Latent category exists because the agent's natural reading of "the artifact works" is "the process worked." That reading must be actively suppressed.
- **The agent's reluctance to admit confusion is strong.** PR #36 in the 2026-06-09 dogfood: the post-mortem honestly admits "I don't know who authored this." A team retrospective would have someone in the room who knew; the solo agent's job is to NAME the unknown rather than smooth it over.
- **Time pressure tempts collapsing steps.** Skipping Step 1b (tape integrity check) or Step 3b (Avoided patterns) makes the post-mortem faster and less useful. The full process is the discipline.

## Post to <tracking issue or canonical docs> and continue (hard gate)

When the post-mortem artifact is complete, post it where future agents will encounter it. The session data folder is a working draft, not the canonical home. **A post-mortem that only exists in a session data folder is a post-mortem that doesn't exist.**

Acceptable canonical homes:

- A GitHub issue on the engagement's primary repo with the full post-mortem as the body (or summary + link to repo-committed doc).
- `docs/post-mortems/<YYYY-MM-DD>-<engagement-name>.md` in the framework repo (siege or workspace-equivalent).
- Both (preferred for engagement-level post-mortems with broad implications).

For each carry-forward in the artifact, **file it where it gets executed**: comment on the relevant ticket, open a fix-PR, add the memory entry, etc. Carry-forwards in a session data folder are not actionable.

Do not declare the post-mortem complete until the artifact is filed AND the carry-forwards are filed.

## Composition with other skills

- **`[skill:pre-mortem]`** — the inverse-time sibling. Pre-mortem classifies risks before implementation (Tigers / Paper Tigers / Elephants); engagement-post-mortem classifies findings after the engagement (Confirmed / Latent / Avoided). The frameworks parallel intentionally: each is a 3-category adversarial classification that surfaces what the agent's default attention misses.
- **`[skill:post-mortem]`** — per-confirmed-failure root-cause analysis. Engagement-post-mortem's Confirmed findings may each warrant `[skill:post-mortem]`; the engagement-level artifact names the confirmed failures, the per-failure artifacts trace each one back through the pipeline.
- **`[skill:investigate]`** — the engagement-post-mortem's Step 1 + 1b parallel `[skill:investigate]`'s Fact Sheet discipline. Both operate on artifact-grounded facts, not memory.
- **`[skill:think]`** — the engagement may have skipped think on individual decisions. Step 6 surfaces those skips.
- **`[skill:self-review]`** — engagement-post-mortem subsumes per-PR self-review at the arc level. The arc's self-review failures appear as Latent findings.
- **`[skill:lessons-learned]`** — engagement-post-mortems typically feed multiple lessons-learned Tier-1 entries. The Avoided findings are particularly likely to become Tier-2 promotion candidates over multiple engagements.
- **`[rule:standing-approval]`** — Step 6 explicitly checks whether standing approvals were correctly interpreted; this is the "lead sheet vs recording" surface for any "do X when Y" instruction.
- **`[rule:writing-claims]`** — the post-mortem output is itself a claim-rich artifact. Same-turn-evidence discipline applies: cite the commit / timestamp / file path.

## Hard rules

1. **Tape over memory.** Every timestamp, every actor attribution, every citation in the post-mortem must come from a re-pulled artifact. "I think it was around 03:30Z" is rejected; `gh api` it or remove the row.
2. **Confirmed findings get per-failure post-mortems.** The engagement-post-mortem names confirmed failures; `[skill:post-mortem]` traces each one. Skipping the per-failure step on a confirmed failure leaves the systemic fix unfound.
3. **Latent findings are not exonerated by substance survival.** The substance-survived-by-luck cell is the most insidious failure mode; every Latent finding gets the same treatment as a Confirmed finding except for the per-failure-post-mortem requirement.
4. **Avoided findings must be named.** The agent's natural tendency is to scope-exclude uncomfortable structural truths. Deferral is acceptable; invisibility is not. Each Avoided finding has a trigger-for-revisiting field.
5. **No retroactive editing of the underlying record.** The post-mortem documents what happened. It does not rewrite PR bodies, commit messages, or memory entries from the engagement to make them look better in hindsight. Errors in the underlying record are part of the data; correct them in subsequent work, not in the historical artifact.
6. **Carry-forwards must be small, specific, and filed.** "Be more careful" is rejected. Each carry-forward names the action, the destination (issue, comment, memory entry, PR), and the step that surfaced it.
7. **Self-application is required.** If the engagement's output includes new rules or skills, the post-mortem MUST check whether the engagement itself complied with them. Step 6 enforces this; skipping it is a violation of this rule.
8. **If the engagement has a tracking artifact, the post-mortem goes there.** Post to the engagement's tracking issue, commit to `docs/post-mortems/`, or both. The session data folder is a working draft, not canonical.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in the post-mortem document, in commits that follow it, or anywhere else. The post-mortem documents systems and actions, not authorship.

## Provenance

Inherits structural conventions from `[skill:pre-mortem]` (siege's adaptation of the [upstream borghei/Claude-Skills pre-mortem](https://github.com/borghei/Claude-Skills/tree/main/project-management/discovery/pre-mortem)): the 3-category classification framework (Confirmed/Latent/Avoided mirrors Tiger/Paper Tiger/Elephant), the numbered Step structure with a Step 1b integrity check, the Named patterns section for dogfooding incidents, the Solo-agent adaptation section, the post-to-canonical-home hard gate, and the numbered Hard rules. The boxing/music framing in § Why is the new content this skill adds; the rest is intentional structural inheritance.
