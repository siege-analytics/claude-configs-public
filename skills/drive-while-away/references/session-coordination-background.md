# Session coordination background

Read this for a retrospective, coordination-tooling work or historical coverage accounting. These preserved records explain prior decisions; proposed tools and version-specific coverage notes are not claims about current runtime capabilities or additional requirements for routine dispatch. Operative coordination requirements remain in [`session-coordination`](../../_session-coordination-rules.md).

## Originating evidence

- **2026-06-05 incident, pour-now workspace.** `260605-brisk-spring` (testing-strategy successor, spawned earlier the same day after the original session hit a provider transient) and `260604-clear-lagoon` (Playwright) were collaborating on PR #181 / PR #183 work for the chain-picker UAT testing framework. clear-lagoon delivered v3 F1 signoff and B1 PR #183 URL, then went at-rest -- but without an explicit baton declaration of "present the unified plan to operator." brisk-spring continued sending drain-pressure pings ("Queue lag now ~30 min"). Operator read the silence as a stall and asked workspace governance (`260604-smooth-gold`) to verify the state. Governance read clear-lagoon's session.jsonl: last activity 114 seconds prior, no errors, deliberate "going silent until brisk-spring's queue drains" status. The cadence mismatch was real; the framing of it as a session failure was the error. The first four rules above name the discipline failures that produced the framing error.

- **2026-09-05 hub decision/control-surface correction, Craft Agent session `260905-clever-quasar`.** The operator described a Siege hub failure mode where the hub says it needs decisions on a list of vague topics, then captures the user-facing session with extended `send_agent_message` churn before the operator has a useful control surface. The historical correction concerned decision-dependent coordination; it asked each decision one at a time with context, options, a recommendation and a default. Apply rule 5 above, which defers the question procedure to [`ask-questions`](../../ask-questions/SKILL.md): ask as a survey, one question at a time, and route the answers only after the last one. Running and independent authorized work continues. If coordination must fan out, the hub should act like a COO with few direct reports by creating sub-managers rather than personally driving every spoke exchange in the foreground.

The incident is recurrence-1 for the cohort. Per writing-claims:4's carve-out (authoring a new rule artifact is the legitimate case for naming a new pattern in the same response as the failure being named), the rule artifact itself is the backing for the cohort introduction.

## Tooling status

Judgment-enforced via `[`code-review`](../../code-review/SKILL.md)` and `[`hostile-review`](../../hostile-review/SKILL.md)` at v3.x.

Mechanical detection candidates for v3.x.y, ordered by tractability:

- **session-coordination:3** is the most tractable: a workspace governance role with filesystem access to other sessions' `session.jsonl` can verify last-activity timestamps and flag escalation language ("stuck," "hung," "death spiral") in outbound messages against the actual partner state.
- **session-coordination:4** is next-most tractable: an outbound `send_agent_message` parser can detect closing-thread phrases ("at-rest," "going silent," "done here") without a corresponding baton phrase ("baton to you," "next move is yours," "present X to operator") and flag the message as rule-4 non-compliant.
- **session-coordination:1** requires comparing outbound and inbound message counts on a thread; if inbound has accumulated past a threshold without a substantive outbound, the parser flags missing at-rest declaration.
- **session-coordination:2** requires cross-session state visibility (was the partner's last message an at-rest declaration?) and operator-context awareness (did the operator declare the lag a problem?). Both are tractable for a workspace governance role; agent-side enforcement is harder.

All four are tractable but require runtime access to other sessions' state, which the framework does not yet expose to running agents directly. Workspace governance sessions (the role `260604-smooth-gold` occupied during the originating incident) have that access via filesystem reads of `session.jsonl`; the role is one place these rules can be mechanically enforced as a sibling-supervision layer.

## Coverage matrix

Nine judgment entries when `_coverage.md` is updated in a follow-up PR:

- `partner-silence-without-declaration` (session-coordination:1, judgment)
- `pinging-past-partner-at-rest` (session-coordination:2, judgment)
- `escalation-language-without-evidence` (session-coordination:3, judgment)
- `thread-closed-without-explicit-baton` (session-coordination:4, judgment)
- `decision-dump-without-checklist-gate` (session-coordination:5, judgment)
- `foreground-send-agent-message-control-surface-hijack` (session-coordination:6, judgment)
- `default-or-rate-blind-spoke-source-selection` (session-coordination:7, judgment)
- `stale-worker-reviewer-not-archived` (session-coordination:8, judgment)
- `collaborator-handoff-set-and-forget` (session-coordination:9, judgment)

Tooling-status counts after update: mechanical unchanged; judgment increases by five relative to the pre-hub-control version; gap unchanged.
