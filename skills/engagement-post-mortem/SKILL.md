---
name: engagement-post-mortem
description: "Rigorous, artifact-based debrief of a completed multi-PR / multi-decision engagement. Sibling to `[skill:post-mortem]` (per-confirmed-failure) — this skill operates on the FULL ENGAGEMENT including its meta-arc, even when no single confirmed failure occurred. Models the discipline of consuming game tapes (boxing: combinations + footwork) and listening to recordings while reading the lead sheet (music: intent vs execution). Five-pass structure: timeline / substance-vs-process / combinations / footwork / intent-vs-execution. Most engagement failures are sequence-failures, not individual-decision failures; standard per-failure post-mortems miss these."
user-invocable: true
allowed-tools: Read Grep Glob Bash
---

# Engagement Post-Mortem

## The "consume tapes" framing

Per operator framing 2026-06-09T06:50Z:

> "In boxing I consume tapes. I look at combinations to see where they failed, I look at footwork to see where I mis-stepped, and so forth. I listen to what I played over changes while reading lead sheets. And I do a rigorous post-mortem to learn."

This skill encodes that discipline for engineering engagement arcs. A post-mortem is not a write-up. The write-up is the artifact OF the watching. The watching is the work.

**The boxing analogies map to specific patterns:**

- **Combinations** — sequences of moves. In engineering: sequences of decisions, PRs, messages, hand-offs. Individual moves can be sound while the sequence fails. Most engagement failures are sequence failures, not individual-move failures. Pass 3 is about combinations.
- **Footwork** — the foundational small moves that enable the visible big moves. In engineering: the cadence of handshakes, the pause before pushing, the habit of grepping before claiming, the discipline of waiting for the asymmetric-expertise counterpart. Footwork misstep → visible failure later. Pass 4 is about footwork.

**The music analogy maps to:**

- **Lead sheet vs recording** — what you intended (the lead sheet — the rules, the standing approvals, the design notes, the canonical skills) vs what you played (the actual diffs, the actual merges, the actual messages). The discipline is listening to the recording WHILE reading the lead sheet. Most post-mortems read only the recording. Pass 5 is about intent vs execution.

## Distinction from `[skill:post-mortem]`

| Surface | `[skill:post-mortem]` | This skill |
|---|---|---|
| Trigger | Confirmed code failure / shipped bug / pre-mortem Tiger materialized | Engagement arc close, with or without confirmed failure |
| Scope | One ticket, one bug, one self-review miss | Multi-PR / multi-decision / multi-session arc |
| Method | Timeline + 5-Whys/Causal Tree + skill-pipeline trace-back | Five passes (timeline / substance-vs-process / combinations / footwork / intent-vs-execution) |
| Output destination | Goes on the ticket (mandatory) | Goes on a tracking issue, in `docs/post-mortems/`, or both |
| Primary signal | "Why did this specific bug ship?" | "Why did this engagement drift from intent?" |
| Both can fire | Together — engagement-post-mortem may find sub-failures that warrant per-failure post-mortems | |

When in doubt, use `[skill:post-mortem]` for confirmed code failures and `[skill:engagement-post-mortem]` for arc reviews. Both for engagements that close around a confirmed failure (the failure gets the per-failure post-mortem; the arc gets the engagement post-mortem).

## When this skill applies

**Required:**

- After a significant multi-PR / multi-decision engagement closes.
- After an incident is resolved (P0/P1).
- At the close of a long-running session before declaring done — operator-requested or self-initiated.
- When the operator asks for one.

**Recommended:**

- Proactively at periodic intervals during long engagements (a "between rounds" check).
- After an engagement that *felt* lucky — substance survived but you can't quite say why.
- After two or more sibling sessions co-author over a sustained period (sibling-handoff drift surfaces in arc review).

**Not applicable:**

- For per-PR / per-diff review. Use `[skill:code-review]`, `[skill:self-review]`.
- For ticket-level closure summaries. Use the ticket's own closure mechanism.
- For per-confirmed-failure investigation. Use `[skill:post-mortem]`.

## Iron laws

1. **Artifact-based, never memory-based.** Pull the actual artifacts — git log, commits, PR bodies, agent-messages, memory entries, ticket state, session transcripts. Memory is suspect; the artifact is canonical. The post-mortem MUST cite specific commits / timestamps / message IDs / file paths.

2. **Five passes, not one.** A single-pass debrief is a write-up, not a tape review. Each pass examines the same material through a different lens. Do not collapse passes; the value is the multiplicity of perspectives.

3. **Blameless framing.** When the actor is yourself, blameless still applies. The discipline is "what system / structure / habit / incentive produced this outcome," not "I screwed up." Self-blame is a poor substitute for systemic insight. Per `[skill:post-mortem]`'s Allspaw test: would the operator find this fair, accurate, and useful?

4. **Substance survival ≠ process validation.** If the substance survived but the process failed, the post-mortem must surface that distinction. Substance-survived-by-luck is a real failure mode and the most insidious one. Operators who treat substance-survival as vindication will rinse and repeat until substance doesn't survive.

5. **Name what worked alongside what failed.** Tape review captures positive signals too. A post-mortem that only catalogues failures becomes a self-flagellation exercise; the positive signals are what compound across engagements. Each pass's output explicitly includes "what worked here that I want to keep doing."

6. **Carry-forward changes must be small and specific.** "Be more careful" is not a carry-forward. "Add a `pre-push.sh` hook that blocks force-push to main" is. The output's actionability is measured by the specificity of the carry-forward set. Each carry-forward names where it lands (skill, rule, hook, ticket, memory entry).

7. **The post-mortem itself is auditable.** Write it so a future operator (you, six months from now; or a sibling agent on a different engagement) can re-read it and recover the reasoning. Cite enough that the reader doesn't have to trust your memory of the engagement.

8. **No retroactive editing of the underlying record.** The post-mortem documents what happened. It does not rewrite PR bodies, commit messages, or memory entries from the engagement to make them look better in hindsight. Errors in the underlying record are part of the data; correct them in subsequent work, not in the historical artifact.

9. **Carry-forwards must be filed where they will be seen.** A carry-forward in a session data folder is invisible. Per `[skill:post-mortem]` rule 5 (post on ticket): every actionable carry-forward gets filed as an issue, comment, or memory entry where future agents will encounter it.

## The five passes

### Pass 1 — Timeline reconstruction

**Purpose:** rebuild what happened, in order, with timestamps. This is the substrate the other passes operate on. Without an accurate timeline, every subsequent pass operates on imagined history.

**Method:**

1. Pull artifact list:
   - `git log --since=<start> --until=<end> --pretty=format:'%h %ai %s'` per repo touched
   - `gh pr list --search 'created:<start>..<end>' --state all` per repo
   - `gh issue list --search 'created:<start>..<end>' --state all`
   - Agent-message history (session-transcript or message log)
   - Tool-call timestamps from session JSONL
2. Merge into a unified timeline. Every entry has: timestamp (UTC), actor (session ID or human), action, artifact reference.
3. Mark major decision points and transitions. A transition is where the engagement's character changes (mode shift, scope expansion, operator intervention, queue-state change).
4. Identify time gaps: idle windows, blocked waits, inbox-lag gaps. The gap itself is signal.

**Output:** a chronological log, dense with citations. Not analysis — just facts. If you find yourself writing "I think this happened around..." stop and grep the artifacts.

**Common timeline-pass failures to avoid:**

- Reconstructing from memory. Get the exact timestamp from the artifact.
- Skipping "trivial" events. They're often the footwork.
- Excluding meta-events (operator's mid-engagement messages, rate-limit signals, queue-depth observations, your own mode shifts).
- Bundling close-in-time events ("PRs #32-#35"). Each gets its own line; the spacing reveals cadence.

### Pass 2 — Substance vs process

**Purpose:** distinguish what was correct in the artifact (substance) from what was correct in how the artifact got to be (process). These are different axes; both matter; conflating them is the #1 post-mortem failure mode.

**Method:**

1. For each PR / ticket / decision identified in Pass 1, ask two questions:
   - **Substance check:** is the artifact itself correct? Does the code work? Does the design hold? Does the rule fire when it should? Were factual claims accurate?
   - **Process check:** did the work get to the artifact through the discipline that exists for it? Was review-then-merge honored? Was the standing approval correctly interpreted? Was the asymmetric-expertise counterpart consulted? Did the relevant gates fire?
2. Tabulate into a 2×2:

   | | Process: pass | Process: fail |
   |---|---|---|
   | **Substance: pass** | Healthy | "Got lucky" — most insidious cell |
   | **Substance: fail** | Process failure of a different kind (gate caught nothing wrong) | Genuine systemic failure |

3. Pay attention to the (substance: pass, process: fail) cell. The artifacts here look fine but were produced by a broken process. Future engagements running the same broken process will eventually produce (fail, fail). The substance-survived-by-luck signal: if this cell is large, your process is degraded but your luck is good — the most dangerous state because it looks like success.

**Output:** a 2×2 table or per-artifact substance/process labels with brief evidence inline. Each cell entry cites the artifact.

### Pass 3 — Combinations (sequence failures)

**Purpose:** find failures that emerged from the SEQUENCE of decisions, not from any individual decision. Most engagement failures are combination failures.

**Method:**

1. From the timeline, identify sequences: "decision A → decision B → decision C." Three to five steps.
2. For each sequence, ask: did the sequence produce a failure that wouldn't have happened with the same decisions in a different order?
3. Look for the canonical sequence-failure shapes:
   - **Race conditions** — two actors moving on the same surface independently.
   - **Inbox-lag races** — async messaging produces parallel work that should have been serial.
   - **Standing-approval misreads** — the conditional gate dropped between message N and action N+5.
   - **Cohort coherence drift** — Theme A → Theme B → Theme C, each individually coherent, taken together incoherent.
   - **Velocity overshoot** — early successes accelerate the cadence past what review can keep up with.
   - **Self-violation under load** — the rule being authored is the rule being violated while authoring it.
4. For each combination failure, identify the **earliest possible interrupt point** — the footwork that would have prevented this sequence. This anchors Pass 4.

**Output:** named sequence failures with timeline citations + the interrupt point that would have caught each one.

### Pass 4 — Footwork (foundation gaps)

**Purpose:** identify the foundational habits, cadences, and small disciplines whose absence enabled the visible failures. Footwork misstep → visible failure later.

**Method:**

1. For each substance-failure and each combination-failure from Passes 2 and 3, ask: what foundational practice would have prevented this?
2. Look for the canonical footwork patterns:
   - **The handshake before the PR** — a one-line "I'm about to draft X" check.
   - **The grep before the claim** — verify symbol existence / regex match / state before stating it.
   - **The wait before the merge** — the 60-second pause for review.
   - **The re-read of the standing instruction** — re-grounding the conditional before each covered action.
   - **The artifact lookup before the cite** — confirming "PR #29" vs "PR #31" against actual merge state.
   - **The cross-rule consistency check** — when shipping a quick-ref that names a hook bypass-marker, grepping the hook to confirm the marker shape matches.
3. For each missing footwork, evaluate:
   - Is this footwork being **SKIPPED** (the operator knows it but doesn't do it under pressure)? → mechanical enforcement needed.
   - Is this footwork **ABSENT** (the operator doesn't know it)? → teaching / rule / skill needed.
4. Cross-reference against any existing canonical memory entries or rules that name the same footwork. If the footwork is canonically known and was skipped, this is a recurrence — flag for siege rule promotion or hook addition. If absent, flag for skill / rule / memory entry.

**Output:** a footwork-gap inventory with skipped/absent labels and mechanical-enforcement / training-needed dispositions.

### Pass 5 — Intent vs execution

**Purpose:** compare what you intended (the lead sheet — rules, skills, standing approvals, design notes) against what you actually shipped (the recording — diffs, merges, messages). Most engagements drift from intent; the question is by how much and where.

**Method:**

1. List the explicit intent sources active during the engagement:
   - Standing approvals from the operator.
   - Canonical rules (`[rule:standing-approval]`, `[rule:definition-of-done]`, etc.).
   - Pre-engagement plans, design notes, or tickets.
   - Canonical skills the engagement was operating under.
   - Workspace canonical memory entries.
2. For each intent source, identify 3-5 specific predictions: "if we were following `[rule:X]`, we would have done Y here."
3. Walk the actual execution and check each prediction. Did Y happen?
4. For each prediction that failed, identify the specific drift point. When did the actual execution deviate from the intended? What caused the deviation?
5. The most dangerous deviation pattern: **the rule you were authoring is the rule you violated while authoring it.** When the engagement's output includes new rules, check whether the engagement itself complied with those rules. Self-application failure is a strong signal that the rule needs mechanical enforcement, not just documentation.

**Output:** per-intent-source: predictions vs actuals, with drift points and the cause-of-drift labeled.

## Synthesis output format

After the five passes, synthesize:

```markdown
# Engagement post-mortem — <engagement name> (<UTC date>)

## Scope
<what's included; explicit start/end timestamps; repos and sessions touched>

## Tape sources
<list of artifacts pulled — git refs, PR numbers, ticket numbers, message-thread IDs, session paths, file paths>

## Pass 1 — Timeline
<chronological log with citations>

## Pass 2 — Substance vs process
<2×2 table; per-artifact analysis>
<"Got lucky" cell explicitly named>

## Pass 3 — Combinations
<sequence failures named, with earliest-interrupt points>

## Pass 4 — Footwork
<missing-footwork inventory; skipped vs absent; mechanical vs training>

## Pass 5 — Intent vs execution
<per-source predictions vs actuals; drift points>

## What worked
<positive signals to keep doing; positive cohort-level patterns>

## Carry-forward changes
<small, specific, actionable; cite the pass that surfaced each; cite where it gets filed>

## Open questions for operator
<things requiring operator judgment to sequence>

— <author session-id>, <UTC timestamp>
```

## Composition with `[skill:post-mortem]`

The two skills compose when the engagement contained a confirmed failure:

1. Run `[skill:engagement-post-mortem]` on the full arc first. The Pass 2 substance-fail entries point to individual failures.
2. For each individual failure, run `[skill:post-mortem]` per the existing skill. Its outputs (action items, codebase sweep, skill pipeline trace-back) ground the engagement-level carry-forwards.
3. The engagement post-mortem's carry-forwards include "run `[skill:post-mortem]` on failure X" as an action item for the operator if the post-mortem hasn't already happened.

## Relationship to other rules and skills

- `[rule:writing-claims]` — every claim in the post-mortem follows same-turn-evidence discipline. Cite the commit / timestamp / file path. The output is itself a claim-rich artifact.
- `[rule:standing-approval]` — Pass 5 explicitly checks whether standing approvals were correctly interpreted; this is the "lead sheet vs recording" surface for any "do X when Y" instruction in the engagement.
- `[rule:prospective-memory]` — Pass 4 looks for the missing re-grounding habit that would have caught conditional decay.
- `[rule:definition-of-done]` — Pass 2's process check leans heavily on whether the five DoD criteria were honored before merge.
- `[rule:verify-before-execute]` — the post-mortem output is itself a side-effecting artifact (changes future behavior); produce it under the same verification discipline.
- `[skill:lessons-learned]` — engagement post-mortems typically feed multiple lessons-learned entries. Capture the carry-forwards there if they meet the recurrence threshold.
- `[skill:rules-audit]` — periodic check of the rule corpus. A post-mortem may surface rules that need audit, but the audit itself is a separate skill.
- `[skill:hostile-review]` (when authored) — independent-session review. Complementary: hostile-review attacks the artifact; engagement-post-mortem studies the path that produced the artifact set.

## Cross-references

- `[skill:post-mortem]` — the sibling per-confirmed-failure skill.
- `[skill:lessons-learned]` — Tier-1 ledger entries fed by post-mortems.
- `[skill:distill-lessons]` — promotes lessons to Tier-2/3.
- `[skill:think]` — pre-action design gate; engagement-post-mortem may reveal where think wasn't run or didn't catch.
- `[skill:investigate]` + `[skill:pre-mortem]` — pre-action gates; engagement-post-mortem evaluates whether they fired.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in the post-mortem document, in commits that follow it, or anywhere else. The post-mortem documents systems and actions, not authorship.
