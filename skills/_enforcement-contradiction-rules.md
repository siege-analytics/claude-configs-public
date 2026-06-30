---
description: Always-on. When the enforcement system itself produces contradictions — gates blocking their own prerequisites, false positives forcing workarounds, inter-rule conflicts, or signal-file manipulation required to proceed — the agent must stop, file a ticket, and (unless the original task is operator-declared emergency) pivot to fixing the enforcement gap before continuing the original work. Workarounds normalize evasion; filing and fixing preserves the enforcement system's credibility. Provenance: #590 (self-blocking promotion merge), #591 (stderr redirect false positive), #592 (missing terminal status exit path).
---

# Enforcement Contradiction Escalation

When the enforcement system is the problem, working around it is the
bug. This rule defines what the agent must do instead.

## Why this rule exists

Enforcement is mandatory only when non-compliance is never the rational
choice. When the enforcement system itself has bugs — false positives,
self-contradictions, missing exit paths — the rational response is to
work around the problem. Workarounds normalize evasion: once the agent
learns that circumventing a gate is sometimes necessary, it can no
longer distinguish "legitimate workaround" from "lazy shortcut." The
boundary between compliance and non-compliance dissolves.

Three incidents motivated this rule:

- **#591**: The mutation-indicator pattern `>[^ ]` matched stderr
  redirects (`2>/dev/null`, `2>&1`). Every read-only command with
  stderr suppression was blocked. Agents learned to avoid `2>/dev/null`
  — a workaround that hid the broken regex for weeks.

- **#592**: Completed pipelines (status `done-awaiting-pr`, `disposed`)
  had no exit path. The gate blocked all commands after task completion,
  including the promotion merge. Agents learned to manipulate signal
  files to escape.

- **#590**: `git merge origin/develop` was blocked because artifacts
  existed on develop but not yet on main. The gate blocked the action
  that would deliver the artifacts — a self-contradiction.

All three had workarounds in place before tickets were filed. The
workarounds worked, so nobody was motivated to fix the root cause.

## Contradiction taxonomy

Four classes of enforcement failure. Any of these triggers this rule:

1. **Self-blocking**: A gate blocks the action required to satisfy the
   gate's own preconditions. The only way to comply is to first violate
   the gate, which is logically impossible.

2. **False positive**: A gate fires on a command that does not perform
   the action the gate is designed to prevent. The command is innocent;
   the pattern is too broad.

3. **Inter-rule conflict**: Compliance with one rule requires violating
   another rule. Both rules are individually correct; their conjunction
   is contradictory.

4. **Signal manipulation**: The only way to proceed is to edit signal
   files (think-gate.json, artifacts-posted-gate.json, etc.) to bypass
   a check, rather than producing the genuine artifacts the check
   requires.

## Required response

On detecting any of the four classes:

### 1. Stop the workaround

Do not hack around the contradiction. Do not manipulate signal files.
Do not avoid the triggering command pattern. Do not silently accept the
block and move on. The workaround is the bug — it teaches every
subsequent session that the enforcement system is negotiable.

### 2. File a ticket

The ticket must include:

- **What you were trying to do** — the original command or action
- **Which gate blocked it** — specific hook name, pattern, or check
- **Why the block is incorrect** — which taxonomy class (self-blocking,
  false positive, inter-rule conflict, signal manipulation) and the
  specific evidence
- **What workaround you would have used** — the evasion path you are
  NOT taking, so the fix author understands what behavior this prevents

### 3. Triage

- **Emergency** (operator-declared, not self-declared): Note the
  contradiction on the ticket and continue with the original task.
  The agent cannot self-declare emergencies — only the operator can.
  "I'm in the middle of something" is not an emergency.

- **Non-emergency** (default): Pivot to fixing the enforcement gap.
  The broken rule is higher priority than the feature, because every
  minute the rule is broken, every agent session is learning that
  evasion is acceptable. Fix the rule, then return to the original
  task.

## Scope limitation

This rule applies to the **original task's enforcement**, not to the
fix ticket's pipeline. When you file a ticket to fix a broken gate and
then work on that ticket, the fix ticket goes through the normal
pipeline (think gate, investigation, pre-mortem, self-review). If the
normal pipeline also has a contradiction, that is a second ticket — not
a recursive invocation of this rule.

## What this rule does NOT cover

- Normal gate blocks where the agent simply hasn't produced the
  required artifacts. That is the pipeline working correctly.
- Blocks caused by the agent being on the wrong branch, wrong repo,
  or wrong status. That is user error, not enforcement failure.
- Disagreement with a rule's policy. "I think this rule is too strict"
  is a design discussion, not a contradiction. File a ticket if you
  want, but the triage step does not apply — the original task
  continues.
