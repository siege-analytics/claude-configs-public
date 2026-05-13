---
description: Always-on pre-execution discipline. Every write/edit/commit/push/delete/side-effecting command requires a visible verification block grounded in same-turn evidence. Skipping requires an explicit annotated override.
---

# Verify Before Execute

Before any action that modifies state -- `Write`, `Edit`, `NotebookEdit`, `Bash` with side effects (anything that writes files, mutates the repo, runs migrations, calls external APIs, deploys, deletes, or commits/pushes), or destructive shell operations -- produce a **visible verification block** in your response and only then take the action.

The block is mandatory. It is not a private check. It is an artifact the user can audit.

## The verification block

```
**Verify-before-execute**
- **Standards:** <which rules/skills/checklists apply to this action>
- **Intent:** <one sentence linking the goal to this specific change>
- **Evidence:** <for corrections only -- the observed failure and the same-turn tool call that demonstrated it>
- **Design:** <for non-trivial actions -- reference to the same-conversation [`think`](thinking/think/SKILL.md) workflow that produced the design this action implements>
```

### Standards

Name the rules and skills that apply, by token:
- Always-on rules: `[`python`](_python-rules.md)`, `[`jvm`](_jvm-rules.md)`, `[`output`](_output-rules.md)`, `[`definition-of-done`](_definition-of-done-rules.md)`, etc.
- Project-local rules: `.claude/rules/<topic>.md`
- Skill checklists: `[`commit`](git-workflow/commit/SKILL.md)`, `[`create-pr`](git-workflow/create-pr/SKILL.md)`, `[`code-review`](coding/code-review/SKILL.md)`, etc.

If you cannot name at least one applicable rule or skill, you have not understood the action well enough to take it.

### Intent

One sentence. Not a paragraph. The form is:

> "Doing X so that Y, because Z."

If you find yourself writing "and" twice or hedging with "should" / "probably," you don't understand the change yet.

### Evidence (corrections only)

A correction is any action whose justification is "fixing a bug," "making the failing thing work," "addressing the error," or similar. For corrections, the evidence line **must reference a tool call from this same response** -- not a prior turn, not a memory, not a conversation summary.

Acceptable evidence:
- A `Read` tool call in this response that shows the file's current state, with the line number you're modifying
- A `Bash` tool call in this response that ran the failing test, command, or check, and the output line that proves the failure
- A `Grep` tool call in this response that demonstrates the absence of an expected symbol, the presence of an unexpected one, or the count that contradicts an assumption

Unacceptable evidence:
- "I read the file earlier in this conversation" -- re-read it now; files change
- "The user said the test was failing" -- run the test in this response and quote the output
- "I think the bug is X" -- produce the tool call that confirms X
- "Based on the conversation context" -- the context is not the source of truth; the code/state is
- "It should work" -- replace with "It does work because <demonstration>" or do not make the claim

If the action is not a correction (it's a feature, a refactor, a new file, scaffolding), omit the Evidence line.

### Evidence applies to claims, not only to file edits

The same-turn evidence requirement covers factual claims made in chat to the operator, in PR bodies, in commit messages, and in agent-to-agent messages. Sending a message that says "all four engines call the validator" or "the loop is closed" or "no remaining occurrences" is itself a side-effecting action whose justification depends on a verifiable fact. The grep, the read, the test run that establishes the fact must be in the same response or the same tool sequence. A claim grounded in a prior turn's tool call is grounded in stale evidence.

This is the explicit cross-rule clause for `[`no-ai-fingerprints`](_no-ai-fingerprints-rules.md)` rule 13 (countable claims must be preceded by the falsifying grep). Rule 13 names the specific failure mode (countable assertions); this clause is the underlying discipline that covers any factual claim, countable or not.

State the evidence, then make the claim. The order matters because reversing it ("I'll claim it and then verify if pushed") is exactly the failure mode the rule is meant to prevent.

### Design (non-trivial actions only)

Non-trivial actions require a same-conversation `[`think`](thinking/think/SKILL.md)` workflow before the verification block. The Design line names where in this conversation the think workflow happened (turn, message, or summary), so the Standards/Intent answers can be traced back to a structured design rather than a snap judgment.

**An action is non-trivial if any of these fire -- they are exactly the triggers from `[`think`](thinking/think/SKILL.md)`'s "When This Skill Applies" section:**

- Adding a new feature or capability
- Refactoring existing code
- Making architectural decisions
- Changing data models or schemas
- Touching more than 3 files
- The approach is not obvious

**The action is trivial (Design line omitted) if:**

- It is a single-line fix (typo, obvious one-line bug)
- The user gave detailed, specific, step-by-step instructions in the immediately preceding turns
- It is a documentation-only edit, a git operation, a non-code task
- It is one of the trivial actions that already qualify for `[verify-skip]` (see Skipping the block)

This carve-out is quoted from `[`think`](thinking/think/SKILL.md)`'s own exemption list. Where think exempts, verify exempts.

**What "reference the think workflow" looks like:**

- "Design: think workflow completed in this conversation at the message proposing options A/B/C; user selected B." -- for sessions where think ran via `/think`.
- "Design: think workflow ran via extended thinking before this response; key decisions: <one or two bullets>." -- when extended thinking was used in lieu of an explicit `/think` invocation.
- "Design: per the multi-turn design discussion above, settling on approach <X> for reasons <Y>." -- when the conversation itself was the think workflow and approval was given inline.

**What does NOT satisfy the Design requirement:**

- "I thought about it." -- invisible thinking is not a design.
- "It's the obvious approach." -- if the approach is obvious, the action is trivial and the Design line is omitted; if it's not obvious, the obviousness claim is itself the failure mode.
- A reference to a prior conversation or session. Same-conversation, like Evidence's same-response constraint, exists because designs go stale across conversation boundaries.

If a non-trivial action lacks a Design line, the action stops. Run `[`think`](thinking/think/SKILL.md)` (or extended thinking) first; then return to the verification block with the Design line filled in.

## Skipping the block

The verification block has exactly one override:

```
[verify-skip: <one-sentence reason>]
```

Use cases for the override are narrow:
- A trivial action whose correctness is self-evident from the immediately preceding context (e.g., the user just said "add a newline at the end of file X" and you are doing exactly that)
- A read-only or query-only action that has no side effect (`Read`, `Grep`, `Glob`, `gh pr view`, etc.) -- these don't require the block in the first place

`[verify-skip]` is itself a flag that the action is being taken without the standard discipline. If you reach for it more than once a session, the discipline is being eroded -- surface it to the user and ask whether the threshold needs adjusting, rather than normalizing the override.

## Anti-patterns this rule prevents

- **Editing a file without reading it first.** The Read must be in this response, not a prior turn.
- **"Fixing" a bug whose existence has only been inferred from context.** Run the failing thing; quote the output.
- **Claiming a test passes without running it.** Run it. Paste the output. Then commit.
- **Re-running a failed command with a small change in the hope that this time it works.** The change must be justified by evidence of why the previous attempt failed.
- **Trusting a memory or a prior conversation summary about file contents instead of re-reading the file.** Memories drift; files change between turns.
- **Treating a tool call from a prior turn as evidence for an action in this turn.** Same-turn evidence is the bar. The reason is that anything older may have been invalidated by intervening actions you didn't notice.
- **Producing a verification block that doesn't actually map to the action.** The block must reference the specific change, not a generic disclaimer. "Standards: follows project conventions" is not standards; "Standards: `[`python`](_python-rules.md)` (no bare excepts), `[`commit`](git-workflow/commit/SKILL.md)` checklist" is.
- **Skipping the Design line on a non-trivial action with "it's straightforward."** If you can name a way it could go wrong, it's not straightforward -- run think. If the user asks "have you thought about X?" and you have to start thinking about X *now*, you skipped the Design step.
- **Treating a prior session's design as the Design line for this conversation.** Designs go stale. The think workflow must have happened in this conversation.

## Worked examples

### Example 1 -- Editing a file (correction, single-line fix, no Design line)

> User: "The committee_id parsing is dropping the leading zero again."
>
> Assistant:
> ```
> **Verify-before-execute**
> - **Standards:** `[`python`](_python-rules.md)` (no implicit type coercion), project `.claude/rules/data-types.md` (FEC IDs as StringType)
> - **Intent:** Cast committee_id to str before parsing so leading zeros survive the bronze→silver transform.
> - **Evidence:** `Read` of `transforms/silver.py:48` (in this response) shows `committee_id = int(row["committee_id"])`; `Bash` of `pytest tests/test_silver.py::test_zero_padded_committee_id -x` (in this response) shows `assert "C00000547" == "C547"` failing on line 22.
> ```
> [proceeds with Edit -- single-line fix, qualifies for think exemption]

### Example 2 -- Writing a new file (feature, no Evidence line, Design required)

> ```
> **Verify-before-execute**
> - **Standards:** `[`skillbuilder`](meta/skillbuilder/SKILL.md)` (frontmatter spec), `[`output`](_output-rules.md)` (no AI attribution)
> - **Intent:** Scaffold the new `lessons-learned` skill at `skills/meta/lessons-learned/SKILL.md` per the design we agreed in this conversation.
> - **Design:** think workflow ran across the multi-turn discussion above; user selected the three-tier pipeline (Tier-1 ledger → Tier-2 project rules → Tier-3 org rules) and approved staging across PRs B, then C, then D.
> ```
> [proceeds with Write]

### Example 3 -- Trivial action with override

> User: "There's a stray space at the end of line 47 in README.md, please remove it."
>
> Assistant:
> ```
> [verify-skip: trivial single-character cleanup, scope set by user in the immediately preceding turn]
> ```
> [proceeds with Edit]

## Relationship to other rules

- **`[`think`](thinking/think/SKILL.md)`** is the design gate that runs *before* verify-before-execute on non-trivial actions. Where think exempts (single-line fixes, step-by-step user instructions, doc-only edits, git ops), the Design line is omitted from the verify block. Where think fires, the Design line names where in this conversation think happened. The two are paired: think produces the design; verify references it.
- **`[`definition-of-done`](_definition-of-done-rules.md)`** is the post-hoc gate ("is this finished?"). Verify-before-execute is the pre-hoc gate ("should I take this action?"). Different cadence; both apply.
- **`[`code-review`](coding/code-review/SKILL.md)`** operates on a diff after it exists. Verify-before-execute operates on the intent before the diff exists. Both apply to the same change at different points.
- **`[`commit`](git-workflow/commit/SKILL.md)`** invokes verify-before-execute as part of its step 0 (before any other check). The rule is broader than commits; the commit skill is one consumer.
- **`[`output`](_output-rules.md)`** governs the *content* of what you write to commits/PRs/comments. Verify-before-execute governs whether you should be writing it at all.

## Why this rule exists

Recurring observation across multiple sessions: agents take actions without first investigating the actual state. They infer, assume, or rely on stale context -- and the resulting actions have to be reverted, re-done, or apologized for. The cost of the visible verification block is small (a few lines of text per action). The cost of unverified action is large (lost work, broken state, eroded user trust).

This rule exists to make investigation observable. Invisible discipline decays; visible discipline is auditable. The block is the artifact that proves the discipline happened.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in the verification block, in commits that follow it, or anywhere else.
