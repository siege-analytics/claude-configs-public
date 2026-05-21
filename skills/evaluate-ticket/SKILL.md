---
name: evaluate-ticket
description: "Always-on. Before any non-trivial work begins, verify the cited ticket is structurally fit for execution. Six-criterion rubric (title shape, required sections, investigated facts, /think link, Assumptions block, falsification for behavior-change tickets). Invoked by think/SKILL.md Step 0, self-review/SKILL.md Goal source verification, and coding/code-review/SKILL.md Pre-review section. The skill is the prose layer; scripts/discipline/evaluate-ticket.sh is the enforcement layer; they stay in sync."
disable-model-invocation: true
allowed-tools: Bash
---

# Evaluate Ticket

A ticket that meets `ticket-required` (a `#NNN` or `PROJ-NNN` reference exists in the commit message) is **cited**, not **fit**. "Cited" satisfies the bookkeeping layer; "fit" satisfies the work-can-be-grounded-against-it layer. This skill enforces the second.

Per the originating plan (`claude-configs-public#146`), every layer of discipline upstream of the work must either (a) confirm a verifiable fact about the ticket, or (b) carry an evidence chain for a "this doesn't apply" claim. This skill is the upstream gate the other discipline skills delegate to.

## When this skill applies

- **`thinking/think/SKILL.md` Step 0** — before producing the design note, the agent runs `evaluate-ticket` against the ticket the work cites. BLOCK means fix the ticket OR paste a trivial-claim block with the evidence chain (per `_writing-rules-rules.md` writing-rules:4) into the eventual self-review artifact.
- **`self-review/SKILL.md` Goal source verification** — the `Goal source:` line pastes the `PASS:` summary from `evaluate-ticket`; the local self-review hook re-runs `evaluate-ticket` and refuses the push if the cited ticket has gone BLOCK since.
- **`coding/code-review/SKILL.md` Pre-review section** — before reading the diff, the reviewer runs `evaluate-ticket` against the PR's linked ticket. BLOCK means the first review comment is the gap list; the diff is not reviewed until the ticket is fit or the author paste an exemption block.

## The rubric

Six checks, each falsifiable and individually diagnosable. The script (`scripts/discipline/evaluate-ticket.sh`) is the executable definition; this section is the prose explanation.

### 1. Title is a complete sentence with subject + verb + observable

`Login bug` fails (noun phrase). `Login flow returns 500 on empty username when LDAP timeout` passes. Conventional-commit shapes (`feat: ...`, `fix(scope): ...`) are accepted as pre-validated.

The heuristic in the script: ≥3 words, at least one verb-token (lowercase verb, `-ed`/`-ing` suffix, or one of the canonical verbs like `add`/`fix`/`enforce`/`block`).

### 2. Body has the canonical sections — Context / Goal / Acceptance

These three section names are **canonical across all repos** (per session 260502-vital-channel direction: "we want this to be generalisable"). No per-repo `.claude/ticket-template.md` override.

- **Context** — what exists today; why this work is being done now.
- **Goal** — the observable change the work delivers.
- **Acceptance** — the falsifiable conditions that say the work is done.

### 3. Body cites ≥1 falsifiable evidence token

At least one of:
- A fenced code block ``` ``` ```
- A file path with extension (e.g., `socialwarehouse/geo/signals.py`)
- A git command (`git diff/log/status/...`)
- A stat / count (e.g., "5 files, 42 lines")
- A URL (`https?://`)

The point: every ticket asserts facts (a bug is real; a feature is needed; a refactor is justified). Each assertion needs at least one falsifiable hook a reader can check. Pure prose ("we should refactor this for clarity") fails.

### 4. Body links to a `/think` design note

Recognized via:
- A `plans/think-*.md` path
- An explicit `Design: <path>` line
- An inline `## Design` (or `## Thinking`) section in the ticket body following the `think/SKILL.md` structure

The work upstream of the ticket is the design; this check enforces that the design exists somewhere readable and is referenced.

### 5. Body has an `## Assumptions` block

Same shape as `self-review/SKILL.md`'s Assumptions section — surfaces what the work is assuming about the world. A ticket without explicit assumptions is a ticket whose author hadn't considered them, which is the most common source of downstream rework.

### 6. (Behavior-change tickets only) Body states a falsification criterion

Tickets labeled `behavior-change`, `feature`, or `bug`: the body must state what observable would prove the work failed, in `writing-tests:1` shape — "Revert the implementation; `<test>` goes red because `<observable>`."

This is the writing-tests:1 invariant applied to the ticket layer: every behavior change has a test that goes red if the behavior reverts. The ticket states the test in advance so the author doesn't write the test against the implementation they happen to produce.

Non-behavior tickets (docs, infra, meta-rule, refactor without behavior change) skip this check.

## Invocation

```
$ bash scripts/discipline/evaluate-ticket.sh '#234'
PASS: ticket #234 is fit for execution
  title: "CI guard: enforce 'feature PRs target develop, not main'"
  sections: Context, Goal, Acceptance — present
  evidence: at least one falsifiable token in body
  /think link: present
  assumptions block: present
  falsification: stated (behavior-change label)
```

On BLOCK, exit code 2 and a per-criterion gap list with remediation. See the script for the exact format.

## What the caller does with the result

- **PASS** — proceed with the work.
- **BLOCK** — two acceptable responses:
  1. **Fix the ticket** to address the listed gaps. This is the default.
  2. **Paste an exemption block** in your self-review artifact citing the ticket, per `_writing-rules-rules.md` writing-rules:4. The exemption requires Reason / Evidence / Falsification fields; the self-review hook validates via `scripts/discipline/check-trivial-claim.sh`.

"Just ignore the BLOCK" is not an acceptable response. The downstream self-review hook re-runs `evaluate-ticket` against the cited Goal source and refuses the push if it BLOCKs and no exemption block is present.

## External-tracker support

GitHub is first-class (`gh issue view` integration). Linear (`TEAM-NNN`) and Jira (`PROJ-NNN`) refs are recognized but the fetchers are **stubbed in v1** — per session 260502-vital-channel direction: "Allow linear and jira but I don't use them in any significant way right now."

To enable Linear / Jira: edit `scripts/discipline/evaluate-ticket.sh`'s `fetch_ticket` function and ensure the corresponding CLI (`linear-cli` or `jira-cli`) is installed in the calling environment.

## Why this skill exists at all

Per `writing-rules:1`, every "always-do-X" rule needs paired automated enforcement. The "every ticket should be fit before work starts" rule is a directive; the script is the enforcement; this skill is what makes the script discoverable + invocable in the agent's natural workflow.

Per `writing-rules:3`, memory entries documenting "I should evaluate-ticket" are correction layers, not enforcement. The skill is the load-bearing surface; the script is the enforcement; memory entries that try to substitute for either are flagged.

## Originating evidence

- `claude-configs-public#146` (parent plan) — the multi-actor enforcement plan with full rationale.
- `claude-configs-public#147` (the canonical script).
- Session 260502-vital-channel, 2026-05-20 — user direction "If work is declared non-trivial, does it have a ticket, well written, with investigated facts stated, a path from /think chosen, assumptions stated, falsification criteria for tests stated? Can this be used by self-review and role assumed review?"
- Sibling-agent failure documented in the same session — agent pushed without self-review, wrote retroactive artifact, satisfied the form check, bypassed the discipline. This skill + the script's artifact-predates-work check closes that loop.
