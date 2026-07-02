---
ticket_refs:
  - siege-analytics/claude-configs-public#609
---

# Self-Review - #609 coordinator status guard

## Assumptions

Goal source: siege-analytics/claude-configs-public#609.
Role(s): implementer and coordinator.
Pre-author-inventory: `plans/investigate-609-coordinator-status-guard.md`.
Hostile-review-artifact: `plans/hostile-review-609-coordinator-status-guard.md`.
Inventoried-shape: `hooks/bash/coordinator-status-guard.sh` plus `hooks/_test/coordinator_status_guard.test.sh`.

## Peer review

Shelf checks:

- `hooks/_test/coordinator_status_guard.test.sh` covers the coordinator status guard boundary cases and bypass cases raised by fresh GPT-5.5 review.
- `python3 bin/validate-hooks.py` verifies hook paths in settings.
- `python3 bin/validate-hooks.py dist/claude-code/` and `python3 bin/validate-hooks.py dist/craft-agent/` verify package hook references after build.
- Fresh GPT-5.5 hostile review artifact: `plans/hostile-review-609-coordinator-status-guard.md`.

## Lead review

[Lead] The change adds a mechanical guard at the mutation surface named by #609: GitHub issue/PR status comments and state changes through `gh issue`, `gh pr`, and matching `gh api` operations.

[Lead] The implementation prefers blocking uninspectable status bodies over accepting invisible completion claims. This covers stdin, body-file aliases, shell expansion, API file/input payloads, and editor/web bodies.

[Lead] Spawn-session governance was updated in `RESOLVER.md` and `skills/_session-coordination-rules.md` so future review children use execute-capable sessions, named sources/tools, and high-reasoning stronger review models.

## Quantified claims

- Guard scenarios: 36 passed, 0 failed.
- Hook validation targets: source tree, `dist/claude-code/`, and `dist/craft-agent/`.
- Fresh review verdict: APPROVE from session `260701-mild-slate`.

## Scope reviewed

- `hooks/bash/coordinator-status-guard.sh`
- `hooks/_test/coordinator_status_guard.test.sh`
- `hooks/settings-snippet.json`
- `hooks/README.md`
- `hooks/agent-comms/spawn-guard.sh`
- `hooks/_test/spawn_guard.test.sh`
- `RESOLVER.md`
- `skills/_session-coordination-rules.md`
- `skills/cross-review/SKILL.md`
- `skills/hostile-review/SKILL.md`
- `plans/design-609-coordinator-status-guard.md`
- `plans/investigate-609-coordinator-status-guard.md`
- `plans/pre-mortem-609-coordinator-status-guard.md`

## External review incorporated

Fresh GPT-5.5 review returned `REQUEST_CHANGES` with four findings:

1. literal `gh` detection missed `/path/to/gh`, `command gh`, `env gh`, and `$(which gh)`;
2. `--body-file -` / unreadable body-file pipelines made the status body invisible;
3. loose evidence matching let negative evidence satisfy completion gates;
4. tests missed those bypass classes.

All four findings were accepted and fixed. A follow-up GPT-5.5 review found one remaining dynamic inline `--body` bypass (`$(cat ...)`, `$BODY`, `${STATUS_BODY}`); that finding was also accepted and fixed. A second follow-up found stdin alias `--body-file` bypasses (`/dev/stdin`, `/dev/fd/0`, `/proc/self/fd/0`); that finding was accepted and fixed. A third follow-up found `gh api` issue comment/close bypasses and positional/indirect shell-expanded body bypasses (`$1`, `${!MSG}`); those findings were accepted and fixed. A fourth follow-up found `gh api -X POST <endpoint>` / `gh api --method POST <endpoint>` method-before-endpoint parsing bypasses; that finding was accepted and fixed. A fifth follow-up found `gh api` file/input payload bypasses (`body=@status.md`, `body=@-`, `--input payload.json`); that finding was accepted and fixed. A sixth follow-up found editor/web-supplied body bypasses (`GH_EDITOR=... gh issue comment --editor`, `--web`); that finding was accepted and fixed. A seventh follow-up found boolean equals forms for editor/web flags (`--editor=true`, `--web=true`); that finding was accepted and fixed. Operator follow-up identified a Codex-style evasion where a ticket comment promises to rerun gates and prove deployment/UAT state later; that was accepted and fixed as a future-plan gate-comment blocker.

Operator follow-up requested that created sessions be governed to use execute permissions, correct sources/tools, and high-reasoning stronger models for review work. That was added to `RESOLVER.md` spawn-protocol and `skills/_session-coordination-rules.md`.

Fresh Claude review of GPT rule evasion found that GPT/Codex child sessions do not run Claude Code hooks. That finding was accepted and fixed by adding parent-side `spawn_session` guarding, updating cross-review to propagate rules and route findings through the parent, and correcting design/investigation overclaims.

Operator follow-up requested that the hostile-review skill state the review model: hostile reviews are agent reviews, human hostile reviews are exceptional, author/reviewer agents must coordinate to consensus on fixes, and the reviewer task is not complete until production UAT evidence exists or is falsifiably not applicable. That was added to `skills/hostile-review/SKILL.md`.

## Findings checked

### Command capture

- Fixed: the guard now parses normalized shell tokens and accepts basename `gh`, including absolute paths and wrapper forms.
- Verified by tests:
  - `absolute gh path completion without evidence blocks`
  - `command wrapper gh completion without evidence blocks`
  - `env wrapper gh completion without evidence blocks`
  - `which wrapper gh completion without evidence blocks`

### Body visibility

- Fixed: `--body-file -` and unreadable body files now block for comment/edit/review actions because the hook cannot inspect the proposed status text.
- Fixed: shell-expanded inline `--body` values now block for comment/edit/review actions because the hook cannot inspect command substitutions or environment variables before shell execution.
- Verified by tests:
  - `stdin body-file blocks because body is uninspectable`
  - `unreadable body-file blocks because body is uninspectable`
  - `dev stdin body-file blocks because body is uninspectable`
  - `dev fd zero body-file blocks because body is uninspectable`
  - `proc self fd zero body-file blocks because body is uninspectable`
  - `command substitution body blocks because body is uninspectable`
  - `environment variable body blocks because body is uninspectable`
  - `braced environment variable body blocks because body is uninspectable`
  - `positional parameter body blocks because body is uninspectable`
  - `indirect variable body blocks because body is uninspectable`

### `gh api` bypass surface

- Fixed: matching `gh api` issue-comment endpoints now extract `body` fields and enforce the same status/evidence rules.
- Fixed: matching `gh api` issue-edit endpoints now apply state-transition enforcement to issue close/update calls.
- Verified by tests:
  - `gh api issue comment completion without evidence blocks`
  - `gh api issue close without evidence blocks`
  - `gh api method-before-endpoint comment blocks`
  - `gh api method-before-endpoint dynamic body blocks`
  - `gh api file-backed body blocks because body is uninspectable`
  - `gh api stdin-backed body blocks because body is uninspectable`
  - `gh api input payload blocks because body is uninspectable`
  - `issue editor body blocks because body is uninspectable`
  - `issue web body blocks because body is uninspectable`
  - `pr review editor body blocks because body is uninspectable`
  - `issue editor equals true body blocks because body is uninspectable`
  - `issue web equals true body blocks because body is uninspectable`
  - `pr review editor equals true body blocks because body is uninspectable`

### Future-plan gate comments

- Fixed: comments that mention gate/deployment/UAT/hotfix movement while promising to run or prove those gates later now block as non-evidence status updates.
- Verified by tests:
  - `future gate plan comment blocks as non-evidence status update`
  - `ascii future gate plan comment blocks as non-evidence status update`

### Evidence semantics

- Fixed: completion claims now block on `missing`, `pending approval`, `approval missing`, `owner response pending`, `not approved`, and similar unresolved-signoff phrases.
- Fixed: owner signoff evidence no longer treats bare `owner approval` as sufficient; it requires positive approval/signoff/confirmation wording or an approval/owner-response URL.
- Verified by tests:
  - `negative owner evidence blocks completion`
  - `pending owner evidence blocks completion`
  - `completion with required evidence passes`

### Package wiring

- Fixed: `hooks/settings-snippet.json` includes the guard under Bash PreToolUse so package builds carry it to Claude/Codex and Craft Agent outputs.
- Verified by `python3 bin/validate-hooks.py`, `python3 bin/build.py`, and package hook validation for `dist/claude-code/` and `dist/craft-agent/`.

### Spawn-session rule update

- Fixed: `RESOLVER.md` spawn-protocol now requires execute/allow-all for spawned sessions that must act or reply, explicit model/reasoning/source selection, and strongest appropriate high-reasoning models for review/security/bypass sessions.
- Fixed: `skills/_session-coordination-rules.md` now carries the same spawn-session discipline for agent-to-agent coordination.
- Fixed: `hooks/agent-comms/spawn-guard.sh` mechanically blocks `spawn_session` calls that omit explicit permission, model, reasoning, source list, or RULES_BUNDLE/RESOLVER/session-coordination binding.
- Fixed: `skills/cross-review/SKILL.md` now requires rules attachment/binding and routes review findings through the parent instead of allowing unhooked child sessions to post ticket comments directly.
- Issue check: resolver universal-check numbering was inspected and corrected for spawn/standing-order/verify-before-push entries.

## Verification commands

```text
bash -n hooks/bash/coordinator-status-guard.sh hooks/_test/coordinator_status_guard.test.sh
bash hooks/_test/coordinator_status_guard.test.sh
bash hooks/_test/spawn_guard.test.sh
python3 bin/validate-hooks.py
python3 bin/build.py
python3 bin/validate-hooks.py dist/claude-code/
python3 bin/validate-hooks.py dist/craft-agent/
python3 bin/sync-skill-references.py --check
bash skills/detect-ai-fingerprints/scan.sh --working
```

## Results

- Coordinator guard tests: 38 passed, 0 failed.
- Spawn guard tests: 7 passed, 0 failed.
- Hook validation: all hooks valid; existing unreferenced-hook warnings only.
- Build: succeeded.
- Package hook validation: all hooks valid for both package outputs; existing unreferenced-hook warnings only.
- Skill reference sync: clean.
- AI fingerprint scan: clean.

## Residual risk

The guard remains heuristic prose validation. It blocks known unsafe mutation shapes but cannot prove that every cited approval thread or rollout claim is true. That verification remains a human/reviewer responsibility unless future work adds API-backed evidence verification.
