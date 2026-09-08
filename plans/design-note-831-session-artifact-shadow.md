# Design note: #831 stale session-scoped artifact gate shadowing

## Goal source

siege-analytics/claude-configs-public#831

## Problem

A long-lived coordinator session can have a current `think-gate.json` for task B and stale session-scoped artifact gates for task A. `universal-mutation-gate.sh` selects the current think-gate, then calls `resolve-think-gate.py --resolve-many` for artifact gates. Before this fix, the resolver returned the stale session-scoped artifact gates without checking whether they matched the current think-gate ticket/task, so current workspace/repo-scoped artifacts were shadowed.

A second defect compounded debugging: `universal-mutation-gate.sh` called `resolve-think-gate.py --session-known`, but the resolver did not implement that flag.

## Design

- Validate session-scoped gate candidates with the same repo/session scope check used for workspace/repo-local candidates before returning them.
- Add task/ticket-aware `resolve_many`: resolve the current think-gate first, derive its `ticket` or `task`, and reject artifact gates whose `ticket`/`task` does not match that current value.
- For artifact gates resolved through `--resolve-many`, require explicit scope: non-empty `repo_root`, a current-session marker when a session id is known, and an explicit current `ticket`/`task`. Generic no-ticket/no-repo workspace artifacts do not authorize mutation.
- Compare repo identity by realpath or matching git remote origin, not basename alone, so same-basename unrelated repositories cannot share artifact gates.
- If the first artifact candidate is stale wrong-ticket, scan the remaining candidate paths in resolver priority order and pick the first scope-valid, ticket-matching gate.
- Implement `--session-known` so the existing mutation-gate caller stops degrading on an unrecognized resolver flag.

## Non-goals

- Do not accept foreign-session workspace-root gates.
- Do not make artifact gates workspace-global.
- Do not weaken missing-artifact blocking when no current matching artifact exists.
- Do not change issue-reporting carve-outs or standing-order automation behavior.

## Validation

- `hooks/_test/universal_mutation_gate_831.test.sh` constructs the exact stale-session-shadow scenario.
- Existing mutation-gate and session-signal tests run to protect prior scoping fixes.

### Verified Shapes

**S1** PROBED: current session think-gate plus stale wrong-ticket session artifact gates plus current workspace repo-scoped artifacts permits mutation.
**S2** PROBED: same stale wrong-ticket session artifact gates with no current artifacts blocks with missing-artifacts diagnostic.
**S3** PROBED: generic no-ticket session artifacts and generic workspace-root artifacts do not authorize current-task mutation.
**S4** PROBED: same-basename different repositories do not share artifact gates.
**S5** PROBED: `--session-known` returns `1` when `CRAFT_SESSION_ID` is present.

### Tiger 1

**Severity:** HIGH
Likelihood: medium
Mitigation: ticket-aware `resolve_many` rejects stale artifact candidates and tests both pass and block sides.
Trigger: wrong-ticket session artifacts still satisfy or shadow current artifact requirements.
Fallback: make `universal-mutation-gate.sh` perform ticket validation itself after resolver output.

### Tiger 2

**Severity:** MEDIUM
Likelihood: low
Mitigation: session-scoped candidates now use `_gate_matches_scope` before return; existing session-signal tests protect foreign-session rejection.
Trigger: a foreign session's gate authorizes mutation.
Fallback: remove session-scoped artifact resolution for mutation-gate until resolver can rank safely.
