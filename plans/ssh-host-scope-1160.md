---
ticket_refs:
  - siege-analytics/claude-configs-public#1160: comment posted
---

# Self-review: ssh gated by host allowlist, not as a local cwd mutation (#1160)

Branch `bugfix/ssh_host_scope`, base `origin/develop` 94dd034f2c. Tier C: enforcement hooks and the review-risk policy.

This is the implementer's own self-review. A cross-family hostile review rejected head 03b5d24 with one merge blocker (R1, the policy loader). Fix round 1 below addresses it. Re-review is required at the new pinned head.

## Fix round 1 (2026-11-06): physical policy-file boundary (review R1)

Authorized by the Siege Claude Hub (261106-neat-boulder, 21:45 CST). Review record: https://github.com/siege-analytics/claude-configs-public/pull/1170#issuecomment-6701689802. Root's concern 3 in https://github.com/siege-analytics/claude-configs-public/pull/1170#issuecomment-6692828625 raises the same issue. D2(a) is unchanged.

- **Defect at 03b5d24.** `ssh_allowlist()` used a plain `open` + `json.load`. It followed symlinks, accepted hard links and duplicate keys, read without a byte bound, and blocked on a FIFO. Policy content outside the fixed file could therefore grant admission.
- **Fix** (`hooks/lib/task_actions.py`, `ssh_allowlist`):
  - a fixed path under the real hooks/lib directory;
  - a symlink is refused, and `os.open` uses `O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC`;
  - `fstat` on the descriptor before any read requires a regular file, `st_nlink == 1` and a size of at most 4096 bytes;
  - a bounded `os.read`;
  - `json.loads` with an `object_pairs_hook` that rejects duplicate keys;
  - a strict schema: exactly `{"hosts": [...]}`, every entry a hostname.
  - Any failure admits no host. The gate exits 2, naming the allowlist and the specific reason, and never stalls.
- **Per-case results.** Gate exit with no task gate, from disposable copied trees with a 15 s bound. These are the reviewer's cases plus three added ones. "develop" is 6cae44a; "new" is the fix-round tree.

  | Policy fixture | Command | develop | 03b5d24 | new |
  |---|---|---|---|---|
  | normal policy (control) | `ssh cyberpower true` | 2 | 0 | 0 |
  | symlink to another JSON file naming outsider | `ssh outsider true` | 2 | **0** | 2 (symbolic link) |
  | hard link to that file | `ssh outsider true` | 2 | **0** | 2 (2 hard links) |
  | `{"hosts":[],"hosts":["outsider"]}` | `ssh outsider true` | 2 | **0** | 2 (duplicate key) |
  | 1,100,000 spaces + valid policy | `ssh cyberpower true` | 2 | **0** | 2 (larger than 4096 bytes) |
  | FIFO | `ssh cyberpower true` | 2 | **stall, killed at 15 s** | 2 in about 0.4 s (not a regular file) |
  | `{"hosts":["cyberpower"],"extra":1}` | `ssh cyberpower true` | 2 | **0** | 2 (must be exactly hosts) |
  | `{"hosts":["cyberpower",""]}` | `ssh cyberpower true` | 2 | 2 | 2 |

  develop denies every row, because it has no ssh branch and ssh falls back to the cwd gate.
- **New harness cases (11).** They are bounded at 10 s each, so a stalling policy fails its case instead of hanging the suite:
  - a symlink, for both outsider and the allowlisted host;
  - a hard link, including an update through the secondary path after linking;
  - duplicate key; 1.1 MB oversize; FIFO; a directory in place of the policy;
  - unknown key; empty-string entry; a non-object policy.
- **Revert proof R7.** Restoring the 03b5d24 loader body in a copied tree must fail the physical-policy cases.

### evaluate-ticket exemption for #1160 (writing-rules:4)

Observed output of `scripts/discipline/evaluate-ticket.sh 'siege-analytics/claude-configs-public#1160'`, at 03b5d24 on 2026-11-06 about 20:35 CST:

```
BLOCK: ticket siege-analytics/claude-configs-public#1160 has gaps before it is fit for execution:
  - missing sections: Context,Goal
  - no '## Assumptions' block
```

- **Reason:** the script matches the literal headings `Context`, `Goal` and `Assumptions` (`evaluate-ticket.sh:124-151`).
  - #1160 carries its context under `## Starting conditions` and `## Observed current outcome`.
  - It carries its goal under `## Intended outcome` and the AC1-AC5 list under `## Acceptance criteria`.
  - #1160 has **no** assumptions block of any name. The assumptions for this work are in this file's `## Assumptions` section and in the #1160 implementation-start comment.
  - The #1160 body is unchanged.
- **Evidence:**
  - #1160 body headings: Intended outcome, Starting conditions, Observed current outcome, Design decision (for review), Known blockers, Acceptance criteria, QA / Verification, Requested by.
  - This file's `## Assumptions` section (`Goal source: #1160`).
  - The implementation-start comment: https://github.com/siege-analytics/claude-configs-public/issues/1160#issuecomment-6649898192
  - Root's coordination review: https://github.com/siege-analytics/claude-configs-public/pull/1170#issuecomment-6650561457
  - The same exemption, posted on the PR: https://github.com/siege-analytics/claude-configs-public/pull/1170#issuecomment-6701053640
- **Falsification:**
  1. `gh issue view 1160 --json body --jq .body | grep -E '^## (Starting conditions|Observed current outcome|Intended outcome|Acceptance criteria|Design decision)'` prints 5 headings.
  2. This file contains `^## Assumptions` and `^Goal source: #1160`.
  3. Both comment URLs resolve to the cited content.
  4. Rerunning the script reports only the three gaps quoted above.

  If any of these fails, the exemption is false.

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
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1170#issuecomment-6701689802 (cross-family review at 03b5d24: REJECT, one blocker R1, addressed in fix round 1 above; re-review at the new head is PENDING)
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
  - Any loader defect yields an empty set, so every ssh is denied. Logical defects: absent file, 0-byte file, malformed JSON, non-list, non-string or non-hostname entry, duplicate or unknown key. Physical defects (since fix round 1): symlink, hard link, FIFO or other non-regular file, a file over 4096 bytes.
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

> **Historical (measured at c80664c on 2026-11-04).** The 133-case and five-proof figures in this section predate both integrations and fix round 1. Current-head figures are in "Fix round 1".

- writing-code:1 (smallest correct change):
  - One new branch in `_action().finish()`, placed before the operand pass that read remote text such as `'cat /etc/x'` as local paths.
  - One condition each in `resolve-think-gate.py` and the gate's EARLY_ALLOW.
  - `bash -n hooks/bash/universal-mutation-gate.sh` exit 0. `bash -n hooks/_test/universal_mutation_gate_ssh.test.sh` exit 0. `/usr/bin/python3` 3.9.6 import + classify check exit 0.
- writing-code (fail closed): allowlist defects deny. Harness cases for an absent file, a 0-byte file, malformed JSON, a non-list, an invalid entry, a non-string entry and an empty list all PASS.
- writing-tests:1 (negative paths):
  - `hooks/_test/universal_mutation_gate_ssh.test.sh`: 133 passed, 0 failed (historical). It covers AC1-AC4, about 40 option forms (several placed after the host), wrapper and path forms, allowlist defects, and a covering-gate fixture.
  - Hub conditions (a)-(c) are asserted against each guard's own skip predicate, and statically: no other guard reads `remote_contact_only`.
- writing-tests (revert proof). Each key change was reverted in a copied tree and the harness re-run:

  | Revert | Harness failures | What it proves |
  |---|---|---|
  | R1, gate EARLY_ALLOW line removed | 25 | every AC1 allow case depends on it |
  | R2, ssh branch removed | 101 | AC1 plus every host/option deny reason |
  | R3, `metadata_only` reused for ssh | 3 | the destructive-guard and guard-predicate cases catch it |
  | R4, no option re-parse after the host | 5 | ProxyCommand/-L/-F after the destination is caught |
  | R5, unproven companions dropped | 1 | the new case catches it (see the finding below) |

- R5 finding (found by the revert proof): the first harness had **no** case for an unproven reader companion beside ssh. Reverting the companion rule passed 131/131. A probe then found `printenv` (also `hostname`, `md5`, `file`, `xxd`): `reader()` admits it, but the released classifier does not prove it (verdict 1). I added `ssh cyberpower uptime; printenv`, which must stay "Unscoped mutation". After that, R5 fails exactly that case.
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

Current head (fix round 1): see the evidence table in "Fix round 1". The figures below are **historical**, measured at c80664c on 2026-11-04.

- ssh harness: 133 passed, 0 failed (historical).
- Revert proofs: 5 of 5 reverts make named cases fail (25 / 101 / 3 / 5 / 1) (historical).
- Full `hooks/_test` (53 `*.test.sh` files at the time, pyenv 3.11.11 first on PATH, `dist/` built locally): 50 passed, 3 failed (historical). All 3 failed identically on a develop 94dd034 snapshot in the same environment, so they are pre-existing and unrelated:
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
- Host matching is lexical, on the destination name as typed; ssh config is never evaluated. The reviewer showed offline that an operator config can map `cyberpower` to another `HostName` and add `ProxyCommand` or `LocalCommand`. So this change does **not** prove that only allowlisted *effective* hosts are contacted, or that ssh has no local effects. It proves only that the hook adds no local target for the typed destination. Whether to treat ssh config as trusted is an open policy decision, not a test result.
- With unbound session identity, the Craft router still denies ssh (hub condition c).
- Test-receipt lane: in this session two gate copies run (workspace-installed + the shared clone's project hooks). Each demands its own `hooks/lib/test-evidence.py`, so no `test-gate.json` receipt could be produced. Tests were run directly under the worktree gate.
