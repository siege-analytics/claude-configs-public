---
ticket_refs:
  - siege-analytics/claude-configs-public#1057: universal-mutation-gate blocks read-only commands
  - siege-analytics/claude-configs-public#1071: v3.5.69 release PR (CodeRabbit review findings)
---

# Self-review: close the #1071 review findings in the read classifier and gate

## Assumptions

Pre-author-inventory: on `develop` 4618d0c the gate allowed, with no task gate, `rg --pre sh .`, `gh api -iXDELETE …`, `git fetch --upload-pack=x …`, `cat f; bash evil.sh`, `env bash evil.sh`, `tree -o /etc/x .`, `cat f 2>/tmp/x` and `cat f &> /tmp/x`. All were observed with the gate harness.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1071
Pre-mortem-artifact: plans/pre-mortem-1071-classifier-review.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/pull/1071
Project-contribution: closes no-gate command-execution and write paths in every consumer workspace without changing designing-state behaviour.

- Exit codes: 0 means proven, 3 is a veto (counts as a mutation), 4 means unproven and skips the legacy safelist, 1 means unknown.
- Only the gate reads these codes.
- `printenv NAME` and bare `env` are still admitted by the legacy safelist. The classifier never proves them. Removing them from `SAFE_PATTERNS` is a policy change left out of this fix.

## Peer review

- **writing-code:** every change is tightening, except `cd` joining the plain verbs. With `cd` added, a compound command passes only when every segment is proven.
- **writing-tests:** `read_allowlist` passes 178/178 here and fails 46 cases against `develop`. Its must-block list covers every CodeRabbit reproducer and every hole found here.
- **Gate evidence:**
  - `read_allowlist`: 178/178.
  - `universal_mutation_gate`: 29/29.
  - `universal_mutation_gate_safelist`: 60/60.
  - `831`: PASS.
  - `empty_reporoot`: PASS.
  - `review_risk_policy`: 12/12.
  - `review_risk_test`: PASS. The first CI run failed here on helper-edge drift; I had run only the policy suite locally.
  - `build.py --check` and `generated-source-authority --check`: pass.
- **Hostile review:** the CodeRabbit review on #1071 is the hostile review. A delegated adversarial run was stopped before it executed any probe, so it contributes no findings. My own shell-parsing probes covered:
  - redirections (`>|`, `&>`, `>&`, `2>`, `1>`, `<<<`);
  - `#` comments;
  - `${…}` holding `;` and `|`;
  - escaped separators;
  - `$"…"`;
  - `exec` and `xargs`.

  They found the fd-redirect hole, which is fixed here.

- **Review-risk graph:** the gate's classifier call is now a standalone line, which the dependency audit detects as a helper edge. The edge is registered in `bin/_test/review_risk_test.py` and the pinned invocation-site digest is updated. The only new site is that call; the assignment/use digest is unchanged. `hooks/lib/read-only-command.py` is now Tier C in `catalog/review-risk-policy.json`, because it decides what the gate admits. That tightens review, and the metrics are regenerated.

## Lead review

- **Solves the #1071 findings:** yes. Each reproducer blocks with no gate.
- **Out of scope:**
  - #1051/#1055's task-keyed redesign.
  - The designing state still admits non-indicator commands (#574).
  - The policy on bare `printenv`/`env` in `SAFE_PATTERNS`.

## Quantified claims

- `read_allowlist`: 178 cases; 46 fail against `develop`.
- Replay: 2,845 commands. No-gate state: 194 newly allowed (all `cd` compounds), 37 newly blocked. Designing state: 0 real changes.

## Second CodeRabbit pass on #1071 (follow-up commit)

CodeRabbit found two more issues once #1072 reached the release PR.
- **`short_has` read option arguments as option letters.** `date -Iseconds` was vetoed as `-s`, a fail-closed false block. Each call now stops scanning at the letters that take an argument:
  - git grep: `efABCm`;
  - fetch/ls-remote: `jo`;
  - log/diff/show: `nSGLUMCB`;
  - gh api: `Hpqt`;
  - sort: `kStT`;
  - yq: `poI`;
  - date: `dfIr`;
  - sed: `efl`;
  - file: `mfFeP`;
  - tree: `LPI`;
  - xxd: `cglos`.
- **Unquoted `$"…"` (a locale string) was not treated as an expansion.** Bash drops the `$`, so `find . $"-delete"` ran `find . -delete` with no gate. It now counts as an expansion; a guarded verb fed one is "unproven".

Evidence:
- `read_allowlist`: 186/186. New must-block cases: `find . $"-delete"`, `sort $"-o" /etc/x f`, `date -us …`. New allow cases: `date -Iseconds`, `date -Ins`, `date -u -d @1`, `sort -t, -k2 f`, `grep -E "a$" f`.
- `universal_mutation_gate`: 29/29.
- `safelist`: 60/60.
- `831` and `empty_reporoot`: PASS.
- `review_risk_policy`: 12/12.
- `review_risk_test`: PASS.
- Replay of 2,845 commands, develop 41af50a vs this branch: 0 verdict changes in either gate state.
