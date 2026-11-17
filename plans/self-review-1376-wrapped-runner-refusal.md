---
propagation-deferred: published with the PR that closes #1376; the PR body summarizes this record and the hub relays it
---

# Self-review: #1376 opaque-runner refusal through command wrappers

Review-Tier: C (hooks/lib enforcement)

## Assumptions

Goal source: siege-analytics/claude-configs-public#1376 and the hub task brief. The goal is for the
opaque-runner refusal to apply to the command each supported wrapper would run, using the existing
wrapper model and repeating through nested wrappers. A wrapper whose behaviour cannot be modelled is
refused. Wrappers in front of ordinary, modelled commands keep their develop outcome.

Source consulted, and what it establishes:
- `hooks/lib/task_actions.py` `_action` on develop 1206bf61. The refusal was a single test:
  `args[0] in {eval, exec, bash, sh, zsh, dash, ksh}`, or python/python3 with any word starting
  `-c`. It ran after `_project_execution_wrapper` (top-level env/command). Nothing unwrapped
  `_WRAPPER_VALUES` wrappers first.
- `_WRAPPER_VALUES` / `_WRAPPER_STRINGS` / `_WRAPPER_NO_COMMAND` / `_wrapped_command`. This is the
  existing wrapper model, shared with the gh-admin merge path (`preserve_shell=True`) and the ssh
  path. It guesses where the command starts: an unknown option is skipped as a flag, so an
  abbreviated or unlisted value option moves the boundary.
- `_python_read`. An AST-checked, read-only `python3 -I -c` program. The bare form is admitted as
  read-only before the refusal is reached.
- `_env_split_string`. Returns None for env -S strings that GNU env rejects.
- Empirical checks on this host:
  - GNU timeout (homebrew) tries to exec `--` in `timeout 5 -- echo`.
  - flock 0.4.0 runs `--comm=...` and `--command=...` after the lock file as program names, and
    fails.
  - Both are therefore harmless shapes, not bypasses.

Design:
- `refuse_opaque_runner(args)` replaces the single test. It strips leading assignments and matches
  the first word by basename, case-insensitively. It unwraps each supported wrapper through
  `_wrapped_command(..., preserve_shell=True, strict=facts)`, repeating to a depth of 16.
- `strict=` is an explicit parameter, used only on this path. It applies exact option tables
  (`_WRAPPER_FLAGS`, `_WRAPPER_OPTIONAL`, `_STRICT_WRAPPER_VALUES`, `_WRAPPER_SHELLS`), so an
  unknown or abbreviated wrapper option is refused.
- The shared tables are byte-identical to develop, and callers that do not pass `strict` keep
  develop's parse.
- The following are refused because the model cannot bound them:
  - an unsplittable env -S string;
  - script without a command;
  - sudo -s/-i/--shell/--login and doas -s;
  - a wrapper that xargs feeds without a command of its own;
  - an xargs replacement string or env -S `${VAR}` in a command word, or in a wrapper's own
    option, value or positional;
  - util-linux `script -c` after FILE.
- Python inline code:
  - develop's any-word `-c` rule is kept as a floor for the bare (unwrapped) literal names
    python/python3, which is exactly where develop applied it;
  - `-c` inside a short cluster (`-Ic`) is detected in the option region;
  - path, case, versioned (`python3.12`) and ABI-flagged names (`python3.13t`, `python3.7m`,
    `python3.13d`, `python3.2mu`) are covered, and they and every wrapped form use the option-region
    scan;
  - under xargs, python is refused unless a script or module is already named and no replacement
    string reaches it;
  - behind a wrapper, the AST-checked read-only program keeps its develop outcome (names python and
    python3 only).

Scope decisions (hub-approved, 2026-11-17):
- In scope: unwrapping every supported wrapper, first-word spelling (path, case, assignments,
  python3.12, -Ic), and refusing unmodellable forms.
- Out of scope: widening the runner set (ash, fish, csh, tcsh, bash5, perl -e, node -e,
  bun --eval, and Python reading its program from stdin).

## Test plan

Executed (results recorded in the PR body and commit trailers):
Final code: develop ec4d1645 plus the red-test commit and the fix, replayed by cherry-pick;
task_actions.py blob f830db8d (hunk-identical to the reviewed 2d1df348, which was built on develop
dbd78db3), test blob 4488b6a7. The counts below were re-run on this final tree; develop's library
there is blob 9895ffb8.
- `hooks/_test/wrapped_opaque_runner_1376.test.sh`: 16 tests OK on the final code.
- The same test inside a `git archive` of develop ec4d1645 (library blob 9895ffb8, no fix;
  debug/v2-base-ec4d1645): 404 failing subtests, with the same per-method distribution as on the
  earlier develop dbd78db3 (blob 7347e750).
  - Every refused-row class fails there, including the 7 ABI-flag rows.
  - No keep-outcome row fails there.
  - The Python floor test fails only on its intended newly refused `-Ic` row.
- Guard proof (run on the earlier dbd78db3 tree, not re-run here): on the previous fix revision
  (blob 0f746e72) the final test fails exactly the 9 rows added for review pass 5 (7 ABI-flag
  refusals, 2 wrapped keep-outcome rows).
- Red proof before any fix: commit df3f8b3f (test only) failed 310 subtests on develop.
- Full `hooks/_test/*.test.sh` (92 suites) on develop ec4d1645 and on the final code, with system
  python3 3.9.6.
- The four build-dependent suites (think_package, recovery_package, verify_enforcement,
  ca_enforcement_manifest) also ran with the existing pyenv Python 3.11.11 against a scratch
  `bin/build.py` dist, on both develop and the fix. Nothing was installed.
- Guard suites for the shared wrapper model (universal_mutation_gate_ssh, github_merge_queue,
  explicit_target_operands, env_project_execution), plus develop's #1473 child-helper tests
  (git_bootstrap_targets) and `git --version` tests (reader_git_safety), before and after.
- A #1473 interaction probe matrix (22 commands: the credential-helper removal prefix combined with
  wrapped and bare runners), develop 9895ffb8 versus the fix.
- Probe comparisons (debug/probe), develop versus fix, over the reviewers' case files.

Limitations:
- The probes ran on macOS with GNU coreutils from homebrew.
- Linux-only wrapper behaviour (util-linux script/flock options) is modelled from documentation,
  not executed.
- Inline Python payloads were not executed live; the P1 rows rest on the probe plus documented
  Python option parsing.

## Findings

- P1: an xargs-supplied command or executable bypassed the refusal (first review, finding 1); Resolution: fixed
- P1: abbreviated GNU long options moved the command boundary (first review, finding 2); Resolution: fixed
- P1: unmodelled value options moved the command boundary (first review, finding 3); Resolution: fixed
- P1: a run-time word in a wrapper's own options or operands reshaped argv (re-review N1); Resolution: fixed
- P1: an xargs replacement string as the python script or option word (confirm pass on N2); Resolution: fixed
- P2: regression against develop found by the full suite run after merging develop 0b6c13ce.
  quoted_mutation_operands refused `/absolute/venv/bin/python -m pytest ... -c pyproject.toml`,
  because basename normalization applied develop's any-word `-c` floor to pytest's own `-c`.
  Fixed: the floor applies only to the literal names python/python3, where develop applied it;
  other spellings use the option-region scan. The fourth review pass confirmed it (APPROVE).
- Review pass 5 (after merging develop dbd78db3) found no regression and three gaps that develop
  also admits:
  - F1, fixed: ABI-flagged names (`python3.13t`, `python3t`, `python3.7m`) did not match the
    interpreter-name pattern, so their `-c` was not refused.
  - F3, fixed: the literal-name floor also fired behind wrappers (`nohup python3 -m pytest -c x`
    was refused, where develop gave mutation). The floor now applies only unwrapped.
  - F2, residual (#1450): Python 2's `-Q` value option is not modelled.
  - Pass 6 confirmed the F1/F3 delta CLEAN. Its side note, an over-refusal of a wrapped full-path
    or versioned python with an AST-safe `-I -c`, is a stricter-only residual documented in the PR.
- P3 findings, all fixed without loosening develop:
  - Python script arguments such as `-vc` were over-refused.
  - sudo value clusters such as `-usroot` were over-refused.
  - `xargs python3 ./tool.py` was over-refused (N2).
  - `script ... ls --color` was over-refused.
- Deliberate outcome changes, documented in the PR:
  - `watch` without -x (it runs `sh -c`);
  - `script` with no command, including macOS `script -p FILE`;
  - sudo -s/-i/-a/-c with a command, and `sudo --sh*`/`--lo*` abbreviations (N3);
  - `nohup ./sh -c` (basename matching);
  - Python inline code under a path, case, version or ABI-flag spelling, bare or wrapped;
  - full-path or versioned python with an AST-safe `-I -c` behind a wrapper;
  - `xargs python3` without a named script or module.

## Independent review

Seven passes:
1. a first review;
2. a fresh re-review;
3. a targeted confirm of the final delta;
4. a confirm of the post-merge python floor narrowing;
5. a targeted confirm on the tree merged with develop dbd78db3;
6. a confirm of the F1/F3 delta;
7. a targeted confirm after replaying the fix onto develop ec4d1645 (the #1473 interaction).

Each was done by a read-only subagent of the same model family as the author (same-family
independence, not cross-provider), given the code and the issue rather than the author's
conclusions. Passes 2-4 were done by a reviewer fresh to pass 1, passes 5-6 by a third reviewer
fresh to passes 1-4, and pass 7 by a fourth reviewer fresh to passes 1-6. Record:
plans/hostile-review-1376-wrapped-runner-refusal.md (verbatim reports). All P1 findings are fixed.
Final verdict: CLEAN on task_actions.py blob f830db8d, the committed code (hunk-identical to the
reviewed 2d1df348).
