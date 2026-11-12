# Bounded diff-files source verification

Goal source: siege-analytics/claude-configs-public#1327.
Source base: `d3581bbd429d03ae82128187b9e46bcc624df278`.
Reviewed source-only staged tree: `74e2429a620ddf16d48d85852e841e0378248b71`.

## Focused verification

`bash hooks/_test/diff_files_reader.test.sh` passed through the normal native
`test-evidence.py record` producer without changing the session environment.
The ignored worktree receipt records the exact production files and successful
command. The focused fixture imports production modules, invokes the mutation
hook, and exercises Git in a synthetic repository; it never replays the refused
live command.

Classifier-only base/candidate comparison for the synthetic literal
`git -C /synthetic/owned-worktree diff-files --quiet` returned unproven/proven-read.
AST parsing of the changed Python sources and test, `bash -n` on the new wrapper,
and `git diff --cached --check` passed.

The standalone reader regression suites passed before the full hook run:
`read_allowlist.test.sh` reported 356 passed and no failures;
`reader_git_safety.test.sh` reported 20 tests, OK.

## Full hook suite and bounded reruns

Every `hooks/_test/*.test.sh` script was run using the same script set as CI,
with a bounded local harness and per-script logs. The first pass used parallel
subprocesses and reported 80 passes and these 6 failures:

| Script | Initial failure | Bounded correction and result |
|---|---|---|
| ca_enforcement_manifest | Clean worktree had no generated dist manifests | Normal local build; rerun passed |
| recovery_package | System Python lacked the pinned PyYAML dependency | Existing ccp venv with PyYAML 6.0.3; rerun passed |
| think_package | Same system Python dependency prerequisite | Existing ccp venv; rerun passed |
| coordinator_mechanical_completion | Synthetic gh fixture hit its existing deadline under parallel load | Serial rerun passed without source or timeout changes |
| github_project_status | Synthetic gh fixture hit its existing deadline under parallel load | Serial rerun passed without source or timeout changes |
| spawn_guard | Synthetic Git fixture hit its existing deadline under parallel load | Serial rerun passed without source or timeout changes |

All 86 hook scripts passed across that initial run and the bounded reruns.
This is not a claim that the initial parallel run was clean. The existing
`task_keyed_gates` suite reported 93 tests, OK. No production logic or test
deadline was changed to address prerequisite or load failures.

The build used `/Users/dheerajchand/.venvs/ccp/bin/python`, which already had the
pinned dependency. No package install, host setting rewrite, deployment, or
runtime gate mutation was required.

Verified-by: full-run tool session 78905 reported `Completed: 86` and the six
failure names above; corrected reruns exited zero. Raw per-script logs were
retained in the task's local `core-1327-hooks-bkvz9k4d` directory. Serial rerun
logs are `/tmp/1327-coordinator-serial.log`, `/tmp/1327-project-status-serial.log`,
and `/tmp/1327-spawn-serial.log`. The focused producer reported four tests OK;
standalone regression outputs supplied the counts recorded above.

## Scanner and runtime boundaries

The selected-source scanner completed with exit 1 and 31 findings. It is
non-clean. Independent per-finding disposition is required; inherited exception
coverage and scanner-discovery debt is tracked in
[siege-analytics/claude-configs-public#1329](https://github.com/siege-analytics/claude-configs-public/issues/1329).
The original output is retained with the independent review evidence.

No installed native callback was retried. The publication owner must complete
reviewed publication/deployment and observe the intended native callback with
its actual repository and index context before reporting runtime acceptance.
