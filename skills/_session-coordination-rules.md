---
description: Always-on. Cross-session coordination discipline for agent-to-agent message cadence. Nine rules covering processing-state declarations, ping discipline, slow-vs-stuck framing, explicit baton handoff, decision checklist gating, operator control-surface preservation, hub spoke-source selection, worker/reviewer retirement, and collaborator follow-up after handoffs. Operator-overridable in the rule body when the operator is waiting; no `[coordination-skip]` flag.
---

# Session coordination

These nine rules apply to multi-session work where two or more agents exchange `send_agent_message` to coordinate. They are complemented by `[rule:tandem-agent]`, which governs role contracts, reviewer/implementer boundaries, explicit authorization, active collaborator supervision, durable findings, and re-review. Originating evidence is a 2026-06-05 incident where two pour-now sessions (`260605-brisk-spring` testing-strategy, `260604-clear-lagoon` Playwright) entered a queue-lag spiral. One was sending updates faster than the other could process. The receiver went silent to drain its queue. The operator read the silence as a stall. Workspace governance (`260604-smooth-gold`) verified the silent partner was alive and processing -- session.jsonl mtime under two minutes -- and that the silence was a deliberate cadence choice, not a session failure. The first four rules name the discipline failures that produced the operator read-error: missing at-rest declaration with explicit re-engagement signal (rule 1), continued pinging past at-rest declaration (rule 2), "stuck" / "death spiral" framing applied to slow processing (rule 3), implicit-but-unstated baton hand-off after the signoff (rule 4). Rules 5 and 6 cover the later hub/COO failure mode where user decisions are dumped as a vague bundle and the main session is captured by foreground spoke-coordination churn.

## The nine coordination rules

**session-coordination:1. Declare your processing state when you cannot immediately respond.** When inbound messages from a partner are accumulating faster than you can substantively reply -- deep in another task, slow tool calls, queue backlog -- send a brief `at-rest` or `queue-draining` acknowledgment to the partner before going silent. Silence without declaration looks like a stall to the partner and to any operator monitoring the thread. The declaration must say what you are draining (specific thread, specific queue, specific predicate for re-engaging) and the form of the next signal you will emit. Scope the pause to that thread or dependency; an at-rest predicate in a handoff does not suspend other eligible assigned work or require a new message before continuing it.

Example acceptable: `Queue-draining on the B1 staging thread. Going silent until I have the PR URL to send. Will re-ping then.`

Example unacceptable: silence after the last substantive reply, with no signal of intent.

**session-coordination:2. When a partner declares at-rest, stop pinging on the thread the partner named.** If your partner says they are silent until X is true, do not send additional messages on that thread that pre-empt X. Drain pressure produces backlog; backlog produces apparent unresponsiveness; apparent unresponsiveness produces operator alarm. Wait for X or signal a genuinely new event on a different thread.

**Carve-out (operator override):** if the operator names the lag as a problem in the open -- "we're waiting on this," "hurry up," equivalent -- at-rest deference is suspended and the receiver of the operator complaint must push forward, even if that means breaking a partner's at-rest. The operator's waiting state outranks the partner's processing-cadence preference. The agent who breaks at-rest must say so in the next message to the partner ("breaking at-rest; operator is waiting"); the partner must accommodate the cadence change. This overrides only processing-cadence deference within the existing grant and assigned role; it does not release an owner hold, supply missing authority or waive required review.

**session-coordination:3. Distinguish slow from stuck before escalating to "stuck."** Check the partner's current operation, actual tool/result delivery and last substantive progress through the host's supported observations. Timestamps, an alive SDK process, an Active/Working label or newly queued inbound messages alone do not prove that the operation is advancing. Slow processing of substantive content -- signoffs, file reads, considered replies -- is not stuckness. An observation timeout is not proof of termination: recheck the same operation or inspect other authoritative state before deciding on recovery.

Escalation language ("stuck," "hung," "death spiral") implies a specific failure shape -- session crash, provider hiccup, infinite loop -- that you should not name unless evidence matches. If control or result delivery is uncertain, apply [skill:stalled-session-recovery] before interrupting or starting a successor. Preserve the predecessor and settle concurrent ownership; neither a quiet interval nor an activity label authorizes duplicate work.

**session-coordination:4. Hand off the baton explicitly when your work on a thread is complete.** When you have sent everything your partner needs to take the next step, say so plainly in the same message that delivers the last artifact: `You have everything for X; baton to you`. Pair the at-rest declaration of rule 1 with an explicit baton declaration; this prevents the receiver from waiting for additional messages they will not get.

Baton declarations name the action expected of the partner ("present the unified plan to operator," "open the consolidation PR," "merge after CI green") so the next move is unambiguous. An implicit baton -- "I'm done" without naming what the partner should now do -- is rule-4 non-compliance and produces the same read-error as a missing at-rest declaration.

**session-coordination:5. Collect user decisions and scope each dependency.** When a spoke needs an unresolved operator decision, present a concrete checklist of the actual decisions, with the context, options, tradeoffs and recommendation for each. Check prior instructions and available evidence first; do not ask again for a settled decision or treat routine technical methods as operator choices.

Hold only briefings or actions that depend on an unanswered decision. As soon as a slice has its required decisions and authorization, coordinate that slice; independent authorized work need not wait for the entire checklist. Summarize each decision as it is settled so collaborators use the same current scope. Do not substitute an assumed answer for missing authority.

Group independent questions when that makes answering easier; sequence questions only when a later question depends on an earlier answer. Keep the operator control surface responsive and avoid repeated status pings that add no new evidence. A checklist is a coordination aid, not a new approval gate.

**session-coordination:6. Preserve the operator control surface during spoke coordination.** The hub session may be the underlying messaging surface, but it must remain the operator's steering wheel. Internal spoke coordination must not become a long foreground activity that prevents the operator from correcting course, answering the next question, changing priority, or stopping the process.

Do not let `send_agent_message` churn monopolize the main session after an operator instruction. If foreground coordination is unavoidable, perform it in short bounded batches, checkpoint, and keep the operator interface responsive. Returning control means the operator can steer or interrupt; it does not mean ending unfinished authorized work or waiting for acknowledgment. Prefer background sessions, sub-agents, or delegated sub-managers for coordination that will fan out or take time.

Use a COO model: the hub should administer few spokes/tasks concurrently. This bounds **administrative load**, not messages or coordination threads. Put a standalone `CCP_TASK_ID=<full-task-id>` line in each spawn prompt so the actual hook payload identifies its accounting task; shell exports do not reach Craft hooks. A sole active canonical task gate is the fallback. Historical children with unknown tasks are not assigned to one enforced legacy bucket. Real `isArchived`/`sessionStatus` metadata, including needs-review and retired, concludes administration. Communication is never limited: operator/parent, own workers/reviewers/sub-hubs, adopted sessions, other hubs and stewards can always be contacted. Stewards (Traffic Cop, Workspace Config, Deep Think and the declared steward-role list) are never limited. Enforce a hub cap only where new administration is taken on, never on `send_agent_message`. The hook enforces it mechanically at spawn (`mcp__session__spawn_session`); adoption has no tool entrypoint for a hook, so a hub that adopts a session counts it against its own cap before accepting. When administered work expands beyond the cap, create or designate sub-managers for bounded domains such as infrastructure, database, application, QA, research, deployment, or documentation. Sub-managers absorb internal churn, coordinate their own spokes, summarize upward, and escalate only decisions, risks, blockers, or material status changes.

Visibility is not the main issue; control is. Even invisible coordination is non-compliant if it captures the hub's attention for an extended period and deprives the operator of a responsive control surface.

**session-coordination:7. Choose spoke AI sources deliberately.** Before spawning or reassigning a spoke, the hub must choose the AI source, model, reasoning level, and enabled external sources/tools for that spoke based on the work, not on default inheritance or convenience. The choice must consider at least: rate-limit pressure and current provider health, the model's strengths and weaknesses for the task, whether the task needs long-context synthesis, hostile review, code execution, browser/source access, structured extraction, or cheap parallel summarization, and the operator's cross-system preferences for which systems should own which work.

Do not overload one provider or one session family when a suitable alternative exists and rate limits or queueing are already visible. Do not send security, bypass, hostile-review, architecture, or final promotion review work to a weaker model merely because it is cheaper or already selected. Conversely, do not spend the strongest scarce model on simple rote extraction, file listing, or low-risk summarization when a smaller model/source can do it safely. If the requested source is unavailable, rate-limited, unauthenticated, or materially weaker for the task, the hub must state the degraded choice and mitigation in the spoke prompt or operator checkpoint.

A compliant spoke prompt names the selected provider/model class, or `unknown` if the platform hides it, reasoning level, permission mode, enabled sources/tools, expected output channel, status-setting requirement, and why that source is fit for the task. Record the rationale in the spoke prompt, hub plan, or operator checkpoint; unrecorded source selection is non-compliant even if the choice was good. If a reviewer must be independent, the hub must prefer a different provider/model family when available or state why independence is degraded.

**session-coordination:8. Retire unnecessary workers and reviewers.** Hubs must not keep stale spokes alive merely because they once had useful context. When a worker, reviewer, sub-manager, or observer has completed its bounded purpose and its knowledge can be safely discarded, the hub must archive it for operator deletion.

Before retirement, preserve only durable value: final findings, open risks, PR/ticket links, evidence paths, decisions made, and any successor handoff. The retirement record must name the durable handoff location, such as a ticket comment, plan path, PR comment, commit, or coordinator summary. Send a final baton/retirement message if another session depends on it. Then mark the child session with a retirement signal available in the environment, such as status `done` and/or labels like `archive-candidate`, `retired-worker`, or `retired-reviewer`, and tell the operator it is safe to delete after they no longer need audit history.

Do not retire a spoke that still owns an unmerged PR, an unresolved blocker, pending CI/UAT, unique credentials/browser state, or evidence not yet copied into the ticket/plan/PR. If the spoke is noisy but still needed, narrow its brief or move it under a sub-manager instead of archiving it.

**session-coordination:9. Check collaborators after handoffs; do not set-and-forget.** When you delegate review, implementation, verification, or investigation to another session, the delegation is not complete until you actively check the collaborator's status/result and either resume, redirect, retire, or report a bounded waiting state. Re-check after every material handoff, after any expected wait, and before making a decision that depends on collaborator output. Before saying a collaborator is done, stuck, paused, or safe to ignore, inspect both its current status and latest reply rather than relying on a prior message. If the operator asks about collaborator progress, inspect the collaborator immediately. Apply `[rule:tandem-agent]` for role boundaries and authorization before sending new work.

## Dispatch protocol

Canonical procedure for resolver check12 and the legacy Spawn-session discipline entry. Apply it to review, implementation, investigation and other delegated work; the code-writing WIP/isolation safeguards apply when the target can be mutated. This selects dispatch mechanics, not collaborator authority. Existing role boundaries and owner holds remain binding.

a. **Check for existing WIP and prior resolution before implementation dispatch.** This prevents duplicate implementation; it does not prohibit an independent review of an existing PR. Resolve the target project's approved integration ref through [skill:develop-guard] and K5 before using the examples below. For Siege this is origin/develop; another project must supply its own approved ref, not a guessed trunk/dev default. The examples call that verified value `APPROVED_INTEGRATION_REF`. For ticket N, perform two checks:

   **Check 1 - branch exists?** Enumerate local and remote branches with `git for-each-ref --format='%(refname:short)' refs/heads refs/remotes` and inspect active worker worktrees on each relevant local or remote host with `git worktree list --porcelain`. Match the target project's approved names and the ticket or PR's recorded head branch, including branches without a ticket ID; do not limit discovery to `fix/` or `feat/`. Inspect matching local/remote work, commits ahead of the approved integration ref and PR state via `gh pr list --head`:
   - Branch exists + PR already open -> do NOT spawn; review the PR instead.
   - Branch exists + no PR -> inspect commits; decide whether to push+PR (work complete) or resume (work incomplete).
   - No branch -> proceed to Check 2.

   **Check 2 - already resolved on the approved integration branch?** Search `git log "$APPROVED_INTEGRATION_REF" --oneline --grep="N"` using the ticket number, then check the ticket/PR's recorded branch and merge commit when the name or commit omits that ID. Missing an ID match is not proof that work is absent. If a fix commit is already merged:
   - Verify the ticket is closed or the code matches the fix description.
   - If resolved -> do NOT spawn; close the ticket if still open and move on.
   - If ambiguous -> spawn with explicit instruction to verify-before-implementing.

   (Incidents: (1) successor session spawned agent for #692 which was already committed and PR'd. (2) Spawned agents for #690 and #689 which were already fixed on develop - agents correctly identified this but wasted startup time re-deriving what a 2-second `git log --grep` would have shown.)

b. **Worktree isolation is required.** Parallel sessions sharing a single working tree cause stash collisions, branch drift, and commits landing on wrong branches. Use `isolation: "worktree"` or equivalent. If the tool doesn't support isolation (e.g., `spawn_session` has no worktree parameter), instruct agents to create their own worktree in the prompt: `git worktree add -b "$TASK_BRANCH" "$TASK_WORKTREE" "$APPROVED_INTEGRATION_REF" && cd "$TASK_WORKTREE"`, with a unique task branch, a unique isolated path and the verified approved integration ref. Choose an unused `TASK_BRANCH` within the project's approved naming rules; do not reuse another worker's branch. If worktrees are impractical, serialize - do not run parallel sessions on a shared checkout. (Incident: siege_utilities #800 session had its uncommitted edits stashed by sibling session #801; commit later landed on wrong branch via checkout race.)

c. **Supervision determines monitoring and reporting, not authority.** Follow the existing role contract and `[skill:think]` for authorization and required reviews in either mode.
   - **Supervised** (coordinator actively monitoring): post durable milestones to the ticket or agreed artifact channel; the coordinator reviews and sends corrections through the available channel.
   - **Unsupervised** (overnight or an unmonitored window): include durable reporting milestones for design, investigation findings, implementation and self-review in the prompt. Report each milestone and continue within the existing grant. User absence or an unanswered routine milestone is not a new approval gate.
   Wait only for an actual contract checkpoint, required review, unresolved decision or owner hold, and only before its dependent action. Continue independent authorized work. Preserve reviewer independence and availability requirements; do not self-approve or acquire another role because a reviewer is absent.

d. **Attach artifacts to tickets, not just session plans.** Session-scoped plan files are ephemeral. The coordinator must ensure that investigation Fact Sheets and self-review artifacts are posted to the ticket as comments (or committed to the repo and linked from the ticket) before the session is dismissed. The next agent who works on related code must be able to find these artifacts without re-deriving them.

e. **Investigation reads existing knowledge.** The spawn prompt must instruct the session to check for prior investigations, related tickets, and existing documentation before starting its own investigation (see `investigate` skill Phase 0). Re-deriving facts already documented elsewhere is wasted work.

f. **Configure permissions, model, reasoning and sources at creation time.** Apply the explicit role contract from [rule:tandem-agent]. Choose the host permission mode and enabled tools that permit the assigned actions and required reporting channel. A host tool prerequisite is not permission to exceed that contract. In CraftAgents, actions and tool-based replies may require execute/allow-all; use that mode only within the authorized role and scope. Safe/read-only remains suitable when the host can perform the assigned inspection and reporting there. Other hosts, including Codex, use their own supported permission controls; there is no universal execute/allow-all requirement.

   Honor explicit operator model/provider choices and the host's supported constraints first. Newly dispatched independent review uses a fresh session and the strongest appropriate review model available with high or higher reasoning; do not use a weaker/default model for hostile, security, bypass, architecture or regression review when a better suitable review model is available. Re-review may return to the original reviewer under tandem-agent:6; this does not require a fresh reviewer or another implementation approval. Apply session-coordination:7 to balance provider health, rate pressure, task fit, independence and operator source preferences. Do not rely on inherited defaults for model, reasoning or source/tool selection. Name the intended model class, reasoning level and enabled sources/tools in the call or prompt. Enable or authenticate required sources through existing authorized controls; if unavailable, state the degraded source set in the prompt and artifact rather than claiming access.

   The prompt must name the permission mode, reporting channel, status-setting requirement and retirement condition. A child that cannot reply is an unobservable background task, not a reviewer. A child without a retirement condition creates workspace clutter. Apply the complete tandem role contract rather than reproducing another role definition here.

**Mechanical test:** before a dispatch call, verify (a) the applicable existing-WIP, prior-resolution and isolation checks were completed for implementation work, without blocking independent review of an existing PR or authorized work that needs no ticket under its actual policy, (b) the prompt names durable reporting milestones, the reporting channel and any actual required review/decision checkpoints, with waits scoped to dependent actions, and (c) host permission mode, model/reasoning and required source/tool selection are explicit. Missing fields are preparation to complete within the existing grant, not a new approval request. Missing material authority or an actual owner hold still stops its dependent action.

## Orphan dispatch

Rule 3 above distinguishes slow from stuck for partners that ARE producing
output. Orphan dispatch is the different failure mode where the partner
never produces any output: `spawn_session` returns a sessionId but the
target session's model layer never fires. The parent must not conflate
"slow" with "orphaned"; they have different remediations and different
observable signals.

The canonical observable-signal definition and the retry ladder for
orphan dispatch live in `[skill:hostile-review]` under the
`## Dispatch verification and orphan fallback` subsection. That skill is
the primary consumer of spawn-based coordination and the canonical
implementation of the fallback. Other skills that spawn (spawn-session
tests, script-sandbox coordinators, downstream helpers) SHOULD cite the
same protocol rather than reinventing it.

Observable orphan signal (summary; see `[skill:hostile-review]` for the
full definition and example): at least ten minutes after spawn, three or
more of the following are true, `messageCount` at most three,
`outputTokens` under one hundred, `lastMessageRole` in `{user, error}`,
and `lastMessageAt` within sixty seconds of `createdAt`. Canonical case:
`260831-vast-marsh` (all four true; Opus 5 dispatch orphaned).

Retry ladder (summary): same-provider respawn once, different-provider
respawn once, cross-review MCP if available, review-deferred artifact
and move to next unit. Full spec in `[skill:hostile-review]`. Continuous
work is preserved: orphan-blocked reviews do not block progression on
other units in the epic.

## Override

These rules are mandatory. The carve-out in rule 2 (operator override) lives inside the rule body, not as an external flag. There is no `[coordination-skip]` override.

## Cross-references

- `[rule:writing-claims]` writing-claims:1-3 cover claims about prior actions. Declaring "I am at-rest" is itself a claim about what you will and will not do next; honor it (rule 2) or rescind it through the operator-override carve-out.
- `[rule:writing-prose]` writing-prose:5 covers future-tense commitments to action. A baton declaration is the present-tense sibling: "the next move is yours, not mine."
- `[rule:tandem-agent]` handles the role-contract and authorization side of multi-agent work; this file handles cadence and baton clarity.
- `[skill:drive-while-away]` handles operator-handoff cadence for autonomous sessions. session-coordination rules are the agent-to-agent analog.

## Originating evidence

- **2026-06-05 incident, pour-now workspace.** `260605-brisk-spring` (testing-strategy successor, spawned earlier the same day after the original session hit a provider transient) and `260604-clear-lagoon` (Playwright) were collaborating on PR #181 / PR #183 work for the chain-picker UAT testing framework. clear-lagoon delivered v3 F1 signoff and B1 PR #183 URL, then went at-rest -- but without an explicit baton declaration of "present the unified plan to operator." brisk-spring continued sending drain-pressure pings ("Queue lag now ~30 min"). Operator read the silence as a stall and asked workspace governance (`260604-smooth-gold`) to verify the state. Governance read clear-lagoon's session.jsonl: last activity 114 seconds prior, no errors, deliberate "going silent until brisk-spring's queue drains" status. The cadence mismatch was real; the framing of it as a session failure was the error. The first four rules above name the discipline failures that produced the framing error.

- **2026-09-05 hub decision/control-surface correction, Craft Agent session `260905-clever-quasar`.** The operator described a Siege hub failure mode where the hub says it needs decisions on a list of vague topics, then captures the user-facing session with extended `send_agent_message` churn before the operator has a useful control surface. The historical correction concerned decision-dependent coordination. Apply rule 5 above: present the complete checklist with context/options/recommendation, group independent questions, and wait only before actions that depend on the missing decisions. Continue independent authorized work. If coordination must fan out, the hub should act like a COO with few direct reports by creating sub-managers rather than personally driving every spoke exchange in the foreground.

The incident is recurrence-1 for the cohort. Per writing-claims:4's carve-out (authoring a new rule artifact is the legitimate case for naming a new pattern in the same response as the failure being named), the rule artifact itself is the backing for the cohort introduction.

## Tooling status

Judgment-enforced via `[skill:code-review]` and `[skill:hostile-review]` at v3.x.

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

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
