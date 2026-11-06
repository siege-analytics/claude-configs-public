---
ticket_refs:
  - siege-analytics/claude-configs-public#1160: comment posted
---

# Self-review: ssh gated by host allowlist, not as a local cwd mutation (#1160)

Branch `bugfix/ssh_host_scope`, base `origin/develop` 94dd034f2c. Tier C: enforcement hooks and the review-risk policy.

This is the implementer's own self-review. The cross-family hostile review has **not** happened yet. The Siege Claude Hub commissions it at the pushed PR head, and its findings will be recorded on the PR and #1160.

## Integration with develop 1cd83f9 (2026-11-06)

Authorized by the Siege Claude Hub (261106-neat-boulder, 11:55 CST): D1 merge, D2 option (a), D3 hostile review at the post-integration head.

- `git merge origin/develop` (normal merge commit). Conflicts were in `task_actions.py`, `universal-mutation-gate.sh`, `catalog/review-risk-policy.json`, `CHANGELOG.md` and `catalog/review-risk-metrics.json`. `resolve-think-gate.py`, `review_risk_test.py` and `skills-inventory.json` auto-merged.
- Kept both sides, dropping neither:
  - develop's `remote_actions` (task-owned GitHub project actions, #1161/#1193) with `select_project_task` authorization and the `remote_only_authorized` EARLY_ALLOW;
  - develop's queue-enqueue lane (#1207/#1209);
  - develop's `mutation_commands`/`commit_commands` split;
  - develop's `github-project-policy.json` and `hook-path.sh` risk pins;
  - plus every #1160 change.
- **Interaction found and closed.** My `remote_contact_only` early return runs before develop's `remote_actions` project authorization in `resolve_action`. So the flag now also requires *no* `remote_actions`: a project action beside ssh can never bypass its project task. New test cases cover it, and revert proof R6 shows they catch it.
- Generated artifacts (`review-risk-metrics.json`, `skills-inventory.json`) were regenerated with the repo tools, not hand-merged.
- D2(a): the strict global allowlist is kept. The `ssh -T git@github.com` global-denial tradeoff is documented in the CHANGELOG and PR. Task-declared hosts are noted as a possible follow-up and not implemented.
- New D2(a) tests: with a covering task gate, the resolver output for allowlisted ssh carries `remote_contact_only` with no `gate`, `task`, `remote_only_authorized` or `tier`. A local write beside ssh still binds the task gate normally.
- Observed D2(a) outcome (`universal-mutation-gate.sh` from a copied tree, command `ssh cyberpower 'touch /srv/x'`):

  | Context | Hook exit | Result |
  |---|---|---|
  | No task gate | 0 | admitted |
  | Covering task gate | 0 | admitted |

  A remote mutating command on an allowlisted host passes this hook without any task gate. This is the accepted tradeoff: contact is not task authorization, and remote-side authority stays operator policy.
- Second integration (2026-11-06 ~15:35 CST): merged develop fe4e0e1, which contains main 9f47b03 (#1214, #1217). The only overlapping file was the generated `catalog/skills-inventory.json`. It auto-merged, and `bin/skill-inventory.py` regenerated it byte-identically.
- Post-integration evidence, measured on the merged tree before commit:

  | Check | Result |
  |---|---|
  | ssh harness | 138 passed, 0 failed |
  | Revert proofs | 6 of 6 make named cases fail: R1 25, R2 103, R3 3, R4 5, R5 1, R6 2 |
  | Full `hooks/_test` (69 files) | 66 pass |

  The 3 full-suite failures (`ca_enforcement_runtime` 4 cases, `session_signal_resolution` 2 cases, `universal_mutation_gate_empty_reporoot` `--session-known`) reproduce identically on a develop `1cd83f9` snapshot in this environment.

## Assumptions

Goal source: #1160 (operator request, Dheeraj 2026-11-04 22:25 CST, relayed by the Siege Claude Hub; AC1-AC5)
Working as: software engineer, tech lead
Pre-author-inventory: https://github.com/siege-analytics/claude-configs-public/issues/1160#issuecomment-6649898192
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1160#issuecomment-6649898192
Pre-mortem-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1160#issuecomment-6649898192
Hostile-review-artifact: PENDING. No independent hostile review exists at commit time. The Siege Claude Hub commissions a cross-family review at the pushed PR head, with findings to be posted on the PR and https://github.com/siege-analytics/claude-configs-public/issues/1160
Project-contribution: agents can reach the review host by ssh without borrowing a task gate. Remote reach becomes an explicit, operator-owned, reviewed list instead of an implicit side effect of any covering task gate.

Scope authorizations, all from the Siege Claude Hub:
- 22:25 contract: task_actions.py, helpers under hooks/lib/, tests, the allowlist + loader, CHANGELOG.
- 22:56: the `universal-mutation-gate.sh` EARLY_ALLOW line and the `resolve-think-gate.py` condition, under conditions (a)-(e).
- 22:58: the Tier C pin in `catalog/review-risk-policy.json` + `bin/_test/review_risk_test.py`, plus regenerating the metrics.
- 23:10: this committed artifact.

Assumptions checked against source:
- `metadata_only` is a bypass flag for other guards: `destructive-guard.sh:45`, `fix-shape-guard.sh:67`, `coordinator-status-guard.sh:70`, `craft-settings-router.py:516`. So ssh gets a separate `remote_contact_only` flag, read only by `resolve-think-gate.py` and `universal-mutation-gate.sh`.
- OpenSSH re-parses options after the destination unless `--` ended them (ssh.c `goto again`). So options are classified on both sides of the host.
- `shell_tokens` already rejects `$`, backticks, groups, `&`, heredocs and comments. Redirects add local targets regardless of argv0.
- The hook runtime interpreter is `/usr/bin/python3` 3.9.6. The new code imports and classifies correctly under it.

## Design

- **Allowlist:** `hooks/lib/ssh-host-allowlist.json`, exactly `{"hosts": ["cyberpower"]}`.
  - Matching is case-insensitive on the destination host as typed, after `user@` (split at the last `@`) or `ssh://[user@]host[:port]`.
  - It is pinned Tier C in `catalog/review-risk-policy.json`.
  - Any loader defect yields an empty set, so every ssh is denied: absent file, 0-byte file, malformed JSON, non-list, non-string or non-hostname entry.
- **ssh argv model (`ssh_destination`).** An allowlist, parsed before the destination and again after it until `--` or the first other word:
  - flags `-4 -6 -a -C -n -q -T -t -v -x`;
  - `-p <digits>`, `-l <login>`;
  - `-o` with `BatchMode, Compression, ConnectTimeout, ConnectionAttempts, ServerAliveInterval, ServerAliveCountMax, LogLevel, RequestTTY, Port, User` and validated plain values.
  - Every other option is denied, including -F, -E, -S, -M, -L/-R/-D, -f, -W, -J, -A, -X/-Y, -i, -G, -N, -O, -w, -V, long options, and ProxyCommand, LocalCommand, PermitLocalCommand, HostName, ProxyJump, Control*, UserKnownHostsFile, KnownHostsCommand, StrictHostKeyChecking.
  - The remainder is the remote command and names no local path.
- **Invocation (`ssh_invocation`):** only argv0 `ssh` or `/usr/bin/ssh` is modeled. These are denied:
  - another ssh path (`./ssh`, `/tmp/ssh`);
  - a `NAME=value` prefix;
  - exec wrappers that run ssh (timeout, nohup, xargs, sudo, env, command, watch and others).
- **Result:** `remote_contact_only` is true only when at least one destination passed the host check, there are no local paths and there is no diagnostic segment. Otherwise the command resolves local targets normally:
  - redirect, `tee` and chained mutations;
  - unproven reader companions keep the cwd as a target.
  - `metadata_only` is forced false whenever ssh is present.

## Peer review

This is the implementer's self-review, not an independent review.

- writing-code:1 (smallest correct change):
  - One new branch in `_action().finish()`, placed before the operand pass that read remote text such as `'cat /etc/x'` as local paths.
  - One condition each in `resolve-think-gate.py` and the gate's EARLY_ALLOW.
  - `bash -n hooks/bash/universal-mutation-gate.sh` → exit 0. `bash -n hooks/_test/universal_mutation_gate_ssh.test.sh` → exit 0. `/usr/bin/python3` 3.9.6 import + classify check → exit 0.
- writing-code (fail closed): allowlist defects deny. Harness cases for an absent file, a 0-byte file, malformed JSON, a non-list, an invalid entry, a non-string entry and an empty list → all PASS.
- writing-tests:1 (negative paths):
  - `hooks/_test/universal_mutation_gate_ssh.test.sh` → 133 passed, 0 failed. It covers AC1-AC4, about 40 option forms (several placed after the host), wrapper and path forms, allowlist defects, and a covering-gate fixture.
  - Hub conditions (a)-(c) are asserted against each guard's own skip predicate, and statically: no other guard reads `remote_contact_only`.
- writing-tests (revert proof). Each key change was reverted in a copied tree and the harness re-run:

  | Revert | Harness failures | What it proves |
  |---|---|---|
  | R1, gate EARLY_ALLOW line removed | 25 | every AC1 allow case depends on it |
  | R2, ssh branch removed | 101 | AC1 plus every host/option deny reason |
  | R3, `metadata_only` reused for ssh | 3 | the destructive-guard and guard-predicate cases catch it |
  | R4, no option re-parse after the host | 5 | ProxyCommand/-L/-F after the destination is caught |
  | R5, unproven companions dropped | 1 | the new case catches it (see the finding below) |

- R5 finding (found by the revert proof): the first harness had **no** case for an unproven reader companion beside ssh. Reverting the companion rule passed 131/131. A probe then found `printenv` (also `hostname`, `md5`, `file`, `xxd`): `reader()` admits it, but the released classifier does not prove it (verdict 1). I added `ssh cyberpower uptime; printenv` → must stay "Unscoped mutation". After that, R5 fails exactly that case.
- writing-claims:1: every count in this file was observed in this work cycle. Pre-existing failures were reproduced on a develop snapshot.

## Lead review

This is the implementer's self-review, not an independent review. The independent cross-family hostile review is PENDING (see Hostile-review-artifact).

- Tech lead: does the change do what #1160 asks, and no more?
  - AC1: allowlisted ssh passes with no gate, from a git repo, a non-git directory and `/`.
  - AC2: other hosts are denied, naming `hooks/lib/ssh-host-allowlist.json`, even under a covering task gate.
  - AC3: scp/rsync/sftp are unchanged. They are still gated without a task gate, and still pass with one.
  - AC4: redirect/tee/chain/substitution/background/heredoc forms keep local targets or fail closed.
  - AC5: the settings snippet and `.claude/settings.json` are unchanged; `validate-hooks.py` → exit 0.
  - Accepted behavior change: ssh to a non-allowlisted host (for example `ssh -T git@github.com`) used to pass under a covering task gate and is now denied.
- Software engineer: is any new path fail-open? None found by self-review:
  - allowlist errors deny;
  - unparsed options deny;
  - wrappers, assignment prefixes and other ssh paths deny;
  - the flag requires no local paths and no diagnostic segment.

## Quantified claims

- ssh harness: 133 passed, 0 failed.
- Revert proofs: 5 of 5 reverts make named cases fail (25 / 101 / 3 / 5 / 1).
- Full `hooks/_test` (53 `*.test.sh` files, pyenv 3.11.11 first on PATH, `dist/` built locally): 50 passed, 3 failed. All 3 failed identically on a develop 94dd034 snapshot in the same environment, so they are pre-existing and unrelated:
  - `ca_enforcement_runtime` (4 F4/ancestry cases; this host has a real Craft ancestor);
  - `session_signal_resolution` (2 unknown-session cases);
  - `universal_mutation_gate_empty_reporoot` (`--session-known` with live session env).
- CI-equivalent bin checks: 15 of 16 pass:
  - `validate-hooks.py` ×3 (source, dist/claude-code, dist/craft-agent);
  - `review_risk_test`;
  - `review_risk_policy` (12/12);
  - metrics current;
  - `build --check`;
  - gate contract + test;
  - effective policy + test;
  - generated-source authority;
  - kernel budget;
  - router test;
  - settings drift.
  - The 1 failure is `local_validation_test`: local PyYAML 6.0.2 vs the pinned 6.0.3, an environment pin that CI installs.
- Hosted CI on the PR head: reported in the PR, not here.

## Known limits

- The gate does not judge remote commands. Remote-side authority (for example `screen -X stuff`) stays operator policy, per the ticket.
- Indirect ssh is out of scope:
  - scp/rsync/sftp host contact (`rsync -e` runs a local program under a covering gate, as before);
  - git over ssh;
  - programs or scripts that spawn ssh under a covering gate.
- ssh may update `~/.ssh/known_hosts`. The operator's own `~/.ssh/config` (ControlMaster, ProxyCommand, Match exec) is trusted as operator-owned.
- With unbound session identity, the Craft router still denies ssh (hub condition c).
- Test-receipt lane: in this session two gate copies run (workspace-installed + the shared clone's project hooks). Each demands its own `hooks/lib/test-evidence.py`, so no `test-gate.json` receipt could be produced. Tests were run directly under the worktree gate.
