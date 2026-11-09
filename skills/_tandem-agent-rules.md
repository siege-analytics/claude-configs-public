---
description: Always-on. Rules for coordinator, reviewer, and implementer agents working in tandem. Requires explicit role contracts, active collaborator supervision, review-only boundaries, authorization gates before role changes, durable handoffs, and re-review after implementation. No override flag except explicit operator authorization recorded in the work item or coordinator message.
---

# Tandem Agent Operating Model

These rules apply whenever two or more agents collaborate on the same work item, PR, repo, or epic. They close the gap between session-coordination cadence and the practical reviewer/implementer split. Read them with `_strategic-agency-rules.md`: collaborators should advance the mission with bounded initiative, not pause for more direction when safe tactical progress is available.

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

**tandem-agent:3. Implementation authorization must be explicit and scoped.** A reviewer/observer remains in that role until the operator or authorized coordinator grants the implementation role for the affected work. The grant must unambiguously cover the work item, repo/branch, allowed files or modules, findings to fix, required tests and whether pushing or opening/updating a PR is allowed. It may name those details directly or incorporate an established scoped contract and durable findings by reference. Inspect the existing contract and messages before asking for fields already supplied; authorization need not be repeated at each step.

Vague assent such as "looks good" does not itself expand a review-only role. A clear implementation instruction may use an established contract without restating it. If material authority or scope is genuinely missing or conflicting, keep that dependent action stopped and ask the coordinator/operator for the specific missing decision. Continue independent work already authorized in the current role. Required review and owner holds remain binding.

**tandem-agent:4. Compatibility alias for session-coordination:9.** Apply `[`session-coordination`](_session-coordination-rules.md)` session-coordination:9 for the canonical post-handoff check, status/result inspection, and resume/redirect/retire/waiting-state contract. Tandem-specific refinement: after guidance or configuration changes land, explicitly resume or retire paused collaborators. Perform collaborator checks in short batches, then return the operator control surface with a checkpoint; internal message churn must not hide the next operator decision.

**tandem-agent:5. Findings become durable before action.** Review findings that may drive implementation must be copied to a durable location the implementer and operator can inspect: PR comment, issue comment, checked-in plan, or tracker artifact. The durable finding must distinguish merge blockers from follow-ups, cite function/file/line evidence, name the affected function chain, and identify the proving fixture or missing fixture. Private session memory is not a handoff.

**tandem-agent:6. Implementation must be followed by re-review against the original findings.** After an authorized implementer fixes review findings, the coordinator must request re-review from the reviewer or an equivalent independent reviewer against the new commit range. The review gate closes only when the reviewer says the named blockers are resolved or the operator explicitly accepts the residual risk. A merged PR with an earlier stale review is not reviewed.

## Direct posting policy

Default: spawned reviewers report to the coordinator via `send_agent_message`; the coordinator posts external PR/ticket comments after checking the body. A reviewer may post directly to GitHub/Linear/etc. only when the role contract explicitly grants `comment-only` external posting and forbids code mutation. Direct comment permission is not implementation permission.

## Pause/resume protocol

When guidance, configs, or source-of-truth files are under revision, stop the affected dependent actions until their prerequisites are settled. State the affected scope and preserve any explicit owner hold; do not pause the whole collaborator when independent authorized work can continue. Before resuming the dependent action, provide the applicable promoted/synced revision identifier, files to read, invalid old instructions to avoid and unchanged permission boundary. A revision notification does not expand the role or release a hold.

## Cross-references

- `_strategic-agency-rules.md` covers why hubs and workers exist: turn strategic goals into tactical progress with bounded initiative and appropriate guidance-seeking.
- `[`session-coordination`](_session-coordination-rules.md)` covers cadence, at-rest, baton, source selection, and retirement.
- `[`work-item-ownership`](_work-item-ownership-rules.md)` covers owner stamping and material state reporting.
- `[`standing-approval`](_standing-approval-rules.md)` covers readiness gates; standing approval does not grant role expansion.
- `[`cross-review`](cross-review/SKILL.md)`, `[`code-review`](code-review/SKILL.md)`, and `[`hostile-review`](hostile-review/SKILL.md)` are primary consumers.

## Attribution

Defers to `[`output`](_output-rules.md)`. No AI / agent attribution in coordination messages, rule files, PR bodies, or commit messages.
