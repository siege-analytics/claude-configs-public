# Non-git mutation inversion design

Issue: siege-analytics/claude-configs-public#128

## Decision

Adopt the authoritarian inversion as the target model: git/PR workflow is the low-friction path, and non-git mutation surfaces carry proof requirements before execution.

This is not a ban on non-git work. It is a routing rule: if a mutation changes shared state, the agent must either route it through a durable workflow artifact or produce the same class of ticket, investigation, pre-mortem, and self-review evidence expected for code changes.

## Current shipped state

The repository has already grown most of the primitives that #128 proposed:

- `hooks/write/branch-guard.sh` blocks repo-path writes on protected branches at write time.
- `hooks/bash/universal-mutation-gate.sh` fail-closes known Bash mutation shapes unless the pipeline state is implementing and required artifacts exist.
- `hooks/bash/destructive-guard.sh` catches high-risk destructive command shapes.
- `hooks/resolver/pipeline-state-guard.sh` pushes investigation, pre-mortem, and self-review artifacts into the same enforcement path.
- Coordinator/status and spawn guards make ticket-visible external updates part of the workflow rather than invisible chat state.

The remaining work is to keep applying that model to new mutation surfaces as they become hookable.

## Mutation surface policy

| Surface | Default | Required disciplined path | Escape hatch |
|---|---|---|---|
| Repo file writes | Block on protected branches; allow on feature branches | Branch + ticket + review artifacts; push through PR | Session `plans/` and `data/` dirs; documented tool-specific carve-outs |
| Bash network mutations (`curl -X POST/PUT/PATCH/DELETE`, infra CLIs) | Block unless implementing pipeline artifacts exist | Use repo-owned workflow, script, IaC, deploy job, or documented runbook with dry-run/check evidence | Operator-approved one-shot with ticket comment naming scope and rollback |
| Database or production infra mutations | Block by pattern where detectable | Migration, job definition, IaC, or runbook in git; dry-run or read-only preview first | Emergency-only operator approval plus post-hoc ticket and self-review |
| External-state MCP/API writes | Require ticket reference and action-owned status update | Platform skill or source workflow that records target, mutation, evidence, and rollback/follow-up | Source-specific allow-list with audit comment |
| Browser/UI mutations | Confirm by default when the target action is Save/Submit/Merge/Delete/Publish or equivalent | Prefer API/git workflow; otherwise capture URL, intended action, before/after evidence, and ticket reference | Operator confirmation in the moment |
| Local scratch/prototype work | Allow outside repos/shared targets | Keep in `/tmp`, session `data/`, or feature branch | N/A |

## Escape hatch requirements

Escape hatches must be auditable and narrow:

1. Name the target system and exact action.
2. Name why the normal git/workflow route is unavailable or slower than the operational risk allows.
3. Name rollback or containment.
4. Leave durable evidence on the ticket or PR before declaring done.
5. Expire after the action; no reusable blanket bypass.

Self-authorization is not an escape hatch. A marker like `mutation-acknowledged` is insufficient because it proves only that the agent saw the rule, not that the operator accepted the risk.

## Phasing

### Phase 1 - Git and Bash surfaces

Status: shipped in current hooks.

- Write-time branch guard for repo paths.
- Universal Bash mutation gate with pipeline-state artifacts.
- Destructive Bash deny patterns.

### Phase 2 - External tool surfaces

Target behavior:

- For each MCP/API source that can mutate external state, document which operations are writes and require ticket/reference evidence.
- Where hookable, block source mutation calls without a ticket reference and artifact path.
- Where not hookable, require the owning skill to produce the same evidence before invoking the source.

### Phase 3 - Browser/UI surfaces

Target behavior:

- Detect obvious mutation verbs in browser actions and require operator confirmation before click/submit.
- Prefer source/API/git workflows over UI mutation when both exist.
- Record URL, element/action, before/after state, and ticket reference for unavoidable UI writes.

### Phase 4 - Policy saturation

Target behavior:

- New tools and sources must declare mutation/read surfaces as part of source setup.
- CI validates source docs include write-surface guidance before enabling new mutation-capable sources.
- Post-incident reviews add missing mutation indicators to the relevant hook or source guide.

## Design tradeoffs

- Friction increases for one-off changes, but the friction is concentrated on shared-state writes where mistakes are expensive.
- False positives should route to a documented workflow or explicit operator approval, not to hidden bypass strings.
- Local exploration remains cheap when it stays outside repos and shared systems.
- The model is asymmetric: reads are easy, writes require evidence.

## Acceptance mapping

- Write tool to repo paths gated: covered by write-time branch guard.
- Write to repo paths off-branch carries evidence: covered at commit/push and by pipeline-state mutation gates for non-trivial changes; future work may add line/file-count write-time thresholds.
- Network mutations blocked outside approved channels: covered for Bash patterns by universal mutation gate; source-specific coverage remains Phase 2.
- External-state MCP writes require ticket/self-review evidence: target model documented; source-specific hookability remains Phase 2.
- Browser mutation confirmation: target model documented; implementation remains Phase 3.

## Recommendation

Keep #128 as the design anchor and close it once this design ships. File implementation tickets per unhooked surface rather than expanding #128 into a catch-all epic. The shipped policy should say: git/workflow first, external mutation only with durable evidence, and no self-authorized bypasses.
