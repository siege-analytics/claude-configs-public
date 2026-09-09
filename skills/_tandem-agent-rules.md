---
description: Always-on. Rules for coordinator, reviewer, and implementer agents working in tandem. Requires explicit role contracts, active collaborator supervision, review-only boundaries, authorization gates before role changes, durable handoffs, and re-review after implementation. No override flag except explicit operator authorization recorded in the work item or coordinator message.
---

# Tandem Agent Operating Model

These rules apply whenever two or more agents collaborate on the same work item, PR, repo, or epic. They close the gap between session-coordination cadence and the practical reviewer/implementer split.

## The six rules

**tandem-agent:1. Every collaborator needs a role contract before work starts.** A coordinator must state each collaborator's role, target, permission boundary, allowed tools/actions, output location, reporting channel, terminal condition, and whether the collaborator may write to the repo or tracker. A prompt that says "review this" without naming `review-only` versus `implementation-authorized` is incomplete.

Minimum contract fields:

- role: `coordinator`, `reviewer`, `implementer`, `verifier`, or `observer`;
- target: repo, branch, PR/ticket, and commit range or pinned head;
- permitted actions: read-only, comment-only, branch-write, PR-open, merge, release, etc.;
- forbidden actions: name destructive/high-risk actions explicitly when relevant;
- output: PR comment, ticket comment, plan file, message back to coordinator, or status field;
- evidence: tests, file:line citations, screenshots, logs, or artifacts expected;
- terminal signal: status change, baton message, archive label, or explicit waiting state.

**tandem-agent:2. Review-only means no implementation by implication.** A reviewer may inspect, run read-only/local verification, draft findings, and report. A reviewer must not edit source, commit, push, merge, revert, open implementation PRs, or spawn implementation workers unless the operator or coordinator gives a new explicit implementation authorization after the review findings are known. Green tests, a PR comment, a fixed config checkout, or "the fix is obvious" do not change the role.

If a reviewer discovers a one-line fix, the correct output is a finding with a proposed fix shape and proof fixture, not a commit.

**tandem-agent:3. Implementation authorization must be explicit and scoped.** A role change from reviewer/observer to implementer requires a fresh authorization message that names: work item, repo, branch, allowed files or modules, findings to fix, tests to run, whether pushing is allowed, and whether opening/updating a PR is allowed. Ambiguous phrases such as "handle it," "go ahead," or "looks good" authorize nothing beyond the current role unless paired with those fields.

When authorization is absent or ambiguous, stop and ask the coordinator/operator for the missing scope instead of inferring permission.

**tandem-agent:4. The coordinator actively supervises collaborators; no set-and-forget.** The coordinator must check collaborator state after every material handoff, after any expected wait, and before making decisions based on collaborator output. At minimum, check session status/last reply before saying a collaborator is done, stuck, paused, or safe to ignore. If a collaborator is paused for guidance/config changes, the coordinator must resume or retire it explicitly after the change lands.

Bounded-batch rule: do collaborator checks in short batches, then return the operator control surface with a checkpoint. Do not let internal `send_agent_message` churn hide the next operator decision.

**tandem-agent:5. Findings become durable before action.** Review findings that may drive implementation must be copied to a durable location the implementer and operator can inspect: PR comment, issue comment, checked-in plan, or tracker artifact. The durable finding must distinguish merge blockers from follow-ups, cite function/file/line evidence, name the affected function chain, and identify the proving fixture or missing fixture. Private session memory is not a handoff.

**tandem-agent:6. Implementation must be followed by re-review against the original findings.** After an authorized implementer fixes review findings, the coordinator must request re-review from the reviewer or an equivalent independent reviewer against the new commit range. The review gate closes only when the reviewer says the named blockers are resolved or the operator explicitly accepts the residual risk. A merged PR with an earlier stale review is not reviewed.

## Direct posting policy

Default: spawned reviewers report to the coordinator via `send_agent_message`; the coordinator posts external PR/ticket comments after checking the body. A reviewer may post directly to GitHub/Linear/etc. only when the role contract explicitly grants `comment-only` external posting and forbids code mutation. Direct comment permission is not implementation permission.

## Pause/resume protocol

When guidance, configs, or source-of-truth files are under revision, collaborators depending on them must be paused. The coordinator's resume message must include the promoted/synced revision identifier, the files to read, any invalid old instructions to avoid, and the unchanged permission boundary.

## Cross-references

- `[rule:session-coordination]` covers cadence, at-rest, baton, source selection, and retirement.
- `[rule:work-item-ownership]` covers owner stamping and material state reporting.
- `[rule:standing-approval]` covers readiness gates; standing approval does not grant role expansion.
- `[skill:cross-review]`, `[skill:code-review]`, and `[skill:hostile-review]` are primary consumers.

## Attribution

Defers to `[rule:output]`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
