---
description: Always-on. When the enforcement system itself produces contradictions — gates blocking their own prerequisites, false positives forcing workarounds, inter-rule conflicts, integrity failures, or context mismatches — the agent must capture evidence, classify the failure, file a ticket with a structured contradiction packet, and triage by blast radius. Workarounds normalize evasion; evidence-based escalation preserves the enforcement system's credibility. Provenance: #590 (self-blocking promotion merge), #591 (stderr redirect false positive), #592 (missing terminal status exit path), #595 (original rule), #597–#603 (cross-review hardening).
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

Seven classes of enforcement failure. Classification requires evidence
(see Detection threshold below).

1. **Self-blocking**: A gate blocks the action required to satisfy the
   gate's own preconditions. Test: can the precondition be satisfied
   WITHOUT performing the blocked action? If yes, it is not
   self-blocking — the agent simply has not done the prerequisite work.

2. **False positive**: A gate fires on a command that does not perform
   the action the gate is designed to prevent. Test: would the hook's
   STATED INTENT (not just its regex) block this command? If not, it is
   a false positive. Evidence must include command class and side-effect
   analysis — "the command is innocent" is not sufficient without
   showing why.

3. **Inter-rule conflict**: Compliance with one mechanically enforced
   rule requires violating another mechanically enforced rule. Both
   must be implemented as hooks or signal checks — a conflict between a
   hook and a human-authored principle is a policy disagreement, not a
   Class 3 contradiction. Precedence hierarchy for resolution:
   safety/security > operator explicit instruction > repository
   enforcement > workflow policy > advisory skill guidance. Only
   unresolved same-level conflicts qualify.

4. **Enforcement integrity failure**: The enforcement mechanism cannot
   reliably determine, explain, or permit compliant progress. Includes:
   altering enforcement inputs, metadata, execution environment, or
   provenance artifacts to satisfy a gate without performing the
   required underlying work (formerly "signal manipulation"); hook
   crash or dependency outage; version skew between local hooks and
   repo rules; ambiguous or missing gate attribution in block output;
   blocked observability (gate blocks read-only commands needed to
   diagnose compliance).

5. **Transient failure**: A gate fires on the first attempt but not on
   a subsequent attempt under identical conditions. Causes include race
   conditions in signal file writing, stale cache states, or
   timing-dependent hook behavior. Protocol: retry ONCE with the
   identical command, capture both outputs. If the second attempt
   succeeds, continue — file a ticket only if the transient failure is
   reproducible or recurrent. Do not pivot on a single unreproduced
   block.

6. **Context mismatch**: A gate is correctly implemented for its stated
   purpose but is firing for a ticket, task, or branch context that is
   not the current work. The gate is not broken — the context binding
   is stale or wrong. Protocol: verify the active task context, archive
   or update the stale signal file with a disposition comment on the
   prior ticket, and continue. File a ticket only if the context
   binding mechanism itself is broken (e.g., signal files lack
   task-scoping and cannot be disambiguated).

7. **Unresolvable prerequisite**: A gate's precondition is satisfiable
   in principle but the agent cannot satisfy it given current
   constraints: wrong access level, missing credentials, external
   service unavailable, or the required tool is not installed. The gate
   is not self-blocking (the precondition is not circular), but
   progress is impossible without external intervention. Protocol:
   file a ticket documenting the constraint, notify the operator, and
   continue with the original task if possible or wait for operator
   guidance.

## Detection threshold

A contradiction is not detected until ALL of the following are true:

1. A gate has actually fired and blocked a command. Speculative or
   pre-emptive claims ("this regex COULD match an innocent command")
   are not triggers — the block must have occurred.

2. The agent has captured the evidence (see Contradiction packet
   below). Bare allegations without evidence are treated as normal gate
   failures until proven otherwise.

3. The agent has performed bounded read-only diagnostics to confirm the
   classification: reading hook code, checking signal file contents,
   verifying branch and status state, or reproducing the block. No
   state mutation is permitted during diagnostics. Stop once
   classification is established — do not continue investigating after
   the class is clear.

If the block resolves on retry (Class 5 — Transient), continue without
filing. If the block is a stale context (Class 6), archive and
continue. For all other classes, proceed to the required response.

## Required response

On confirming a contradiction (Classes 1–4, 7, or persistent Class 5):

### 1. Stop the workaround

Do not hack around the contradiction. Do not alter enforcement inputs,
metadata, execution environment, or provenance artifacts to satisfy a
gate without performing the required work. Do not silently accept the
block and move on.

Semantically equivalent read-only diagnostic commands are permitted
AFTER evidence capture — running the same command without stderr
suppression to gather output is not evasion. Changing command shape to
hide a prohibited mutation IS evasion.

### 2. File a ticket with a contradiction packet

The ticket must include a structured contradiction packet with ALL of
the following fields. A ticket missing any field is incomplete and does
not satisfy this requirement.

- **Blocked command**: The exact command or action that was blocked
  (verbatim, not paraphrased).
- **Hook output**: The exact block output from the gate (captured, not
  summarized).
- **Gate identity**: Specific hook name, file path, and line number
  that triggered the block.
- **Protected invariant**: What the gate is designed to protect.
- **Taxonomy class**: Which class (1–7) and the specific evidence for
  that classification.
- **Reproduction**: Minimal steps to reproduce the block.
- **Why compliance is impossible**: Why ordinary compliance (producing
  the required artifacts) cannot resolve the block.
- **Bypass class** (if known): At minimum useful specificity, describe
  what category of workaround would bypass the gate. Do not search for
  additional bypasses to complete this field. Do not include
  step-by-step bypass instructions in public tickets.

If ticket creation is itself blocked by the enforcement pipeline, use
fallback in order: (1) append to a local enforcement-incident log,
(2) notify the operator directly with the required fields, (3) once
unblocked, backfill the durable ticket.

### 3. Triage by blast radius

Not all contradictions warrant pivoting away from the original task.
Route by severity:

- **Blocking + reproducible + same enforcement surface + agent owns
  the repo**: Pivot to fixing the enforcement gap. The broken rule is
  higher priority than the feature.

- **Non-blocking, advisory, unrelated enforcement surface, or low
  blast radius**: File the ticket and CONTINUE the original task. A
  minor false positive in an unrelated hook does not justify abandoning
  a feature.

- **Outside current repo or agent's authority**: File the ticket,
  notify the owner, and continue the original task (or ask the
  operator for guidance if the block prevents all progress).

- **Emergency** (operator-declared only): The operator must
  acknowledge the contradiction AFTER being shown it and explicitly
  authorize continuation using specific language ("emergency,"
  "production incident," or an emergency label/status). Pre-
  contradiction urgency statements ("keep moving," "don't let this
  block you") do not qualify. On emergency authorization: file the
  ticket, note the operator's authorization verbatim, and continue.
  This is a documented bypass, not a workaround exemption — it still
  risks normalizing gate evasion and must be closed promptly.

## Enforcement fix guardrails

When pivoting to fix an enforcement gap (per triage above), the fix
must meet these criteria before the enforcement gap ticket can be
closed:

1. **Failing regression test before fix**: Proves the false positive
   or contradiction is real and reproducible in the test harness.
2. **Passing regression test after fix**: Proves the fix resolves the
   reported contradiction.
3. **True-positive preservation test**: Proves the fix does not weaken
   enforcement — the gate still catches the mutations it is designed
   to catch.
4. **Minimal change**: The fix must be the narrowest pattern or parser
   change that resolves the contradiction. No broad bypasses or gate
   deletions without operator approval.
5. **Self-review focused on enforcement weakening**: The self-review
   must explicitly address whether the fix opens new evasion paths.
6. **Deployment path**: Document how the fix reaches the enforcement
   system (repo commit, hook rebuild, workspace sync).

## Scope limitation and cascade control

This rule applies to the **original task's enforcement**, not to the
fix ticket's pipeline. When you file a ticket to fix a broken gate and
then work on that ticket, the fix ticket goes through the normal
pipeline (think gate, investigation, pre-mortem, self-review).

**Cascade depth limit**: If the fix ticket's pipeline ALSO produces a
contradiction, attach the reproduction as a comment on the root
enforcement ticket — do NOT file a third ticket. A second-level
contradiction requires operator consultation before any further
pivoting. This prevents infinite ticket chains where each fix triggers
another contradiction.

**This rule cannot resolve contradictions it creates.** If the
escalation protocol itself produces a contradiction (e.g., the ticket
template is blocked by the gate being reported), escalate to the
operator — there is no automated resolution path for meta-level
contradictions.

## What this rule does NOT cover

- **Normal gate blocks** where the agent simply has not produced the
  required artifacts. That is the pipeline working correctly.

- **Correctable state errors** where the agent is on the wrong branch,
  wrong repo, or wrong status AND there is an allowed corrective
  command available AND the reported state is accurate. If the gate
  blocks the corrective command itself, or if the state is stale or
  impossible to update, that IS an enforcement failure (classify under
  the appropriate taxonomy class).

- **Policy disagreement**. "I think this rule is too strict" is a
  design discussion, not a contradiction. A conflict between a hook
  and a human-authored principle does not qualify as Class 3 — only
  hook-vs-hook conflicts at the same precedence level qualify. File a
  ticket if you want to discuss the policy, but the triage step does
  not apply — the original task continues.

## Mechanical enforcement

This rule depends on agent judgment at every step. To reduce gaming
surface, enforcement gates SHOULD:

- Include machine-readable gate identity and protected invariant in
  block output, so the contradiction packet can be populated
  mechanically rather than requiring the agent to read hook source.
- Capture blocked command logs automatically (not relying on the agent
  to record them honestly).
- Provide a classification prompt when a block fires, requiring the
  agent to declare "normal gate failure" or "enforcement contradiction
  + class + evidence" before proceeding.

Until mechanical enforcement is implemented (#602), this rule is
behavioral guidance enforced by self-review and operator oversight.
Agents that ignore it are not mechanically prevented from doing so —
but the self-review hook will flag the absence of a contradiction
packet when gate blocks appear in the session log.
