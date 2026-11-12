# Task evidence and lifecycle

Read before creating, selecting, updating or disposing task signals. For class-of-bug fixes and claim changes also read [premise claims](premise-claims.md). A signal records task state; it does not grant authority or release a hold.

## Signal file lifecycle

The `think-gate.json` signal file enables the `think-gate-guard.sh` hook
to verify the design's premises on every turn. It is the bridge between
the design (prose) and the enforcement (hook).

### Creating a signal file

After posting the design note (Step 7), write the signal to
`$CRAFT_SESSION_DIR/tasks/<task-slug>/think-gate.json`, or
`<workspace>/sessions/<session-id>/tasks/<task-slug>/think-gate.json`.
Task identity is the **full ticket reference**, or an explicit `task_id` for
untracked work. Choose a stable unique non-hidden directory slug; the resolver reads each
task directory's identity, not its spelling. The helper's `task_slug(identity)`
provides a collision-safe default for writers migrating a legacy session file.
Never derive a path from an unset session variable or write to the workspace root.

One session can have multiple tasks in the same repo. Declare absolute
`scope_paths` for each task (prefer isolated clone/worktree roots; optional
subdirectories/extra paths are supported). `repo_root` alone is the legacy
scope default. Canonical path-component containment, including symlinks,
selects the most-specific task; equal scopes fail closed with task names.
Use a leading in-command marker, `CCP_TASK_ID='owner/repo#NNN' command ...`,
to disambiguate a Bash tie. Agent-shell exports do not reach the Craft hook
process; Write/Edit/MultiEdit/NotebookEdit require unambiguous path ownership
and have no in-command binding channel. Binding never expands scope. Git
mutations belong to the repository toplevel's owner, not a nested path's task.
Split actions spanning multiple tasks; prefer isolated worktrees for independent
Git activity. Terminal disposed/complete/done-awaiting-pr gates are excluded
from active ownership. Preserve reserved tasks/.canonical/ per-task claims:
individual gate cleanup cannot resurrect that task's stale legacy copy, and
unrelated legacy tasks remain independent.

```json
{
  "ticket": "owner/repo#NNN",
  "sessionId": "current-session-id",
  "design_note_location": "URL to ticket comment",
  "status": "implementing",
  "lastUpdated": "2026-01-15T14:30:00Z",
  "repo_root": "/path/to/repo",
  "scope_paths": ["/path/to/repo/task-worktree"],
  "tier": "B"
}
```

**Tier (optional, #1086).** The task lifecycle uses the [canonical pre-edit tier contract](SKILL.md#before-an-edit-versus-before-a-commit). Declare a higher tier when needed; this field cannot lower the target-path floor. That entrypoint owns the evidence table, classification failure behavior and separation from commit review.

For turn-start companion derivation, an existing `CCP_TASK_ID` in the hook's
host environment takes precedence. When it is absent, use the host's
`task_id` metadata or one unfenced, unquoted standalone prompt line
`CCP_TASK_ID=owner/repo#NNN` within the hook's 1 MiB input bound. Separate a directive from preceding quoted material with a blank line; lazy quote continuations are not directives. Long prompt text is not exported to the hook environment. Use the full ticket when the Task has a `ticket`;
its separate `task_id` does not replace that identity. This selects only an
existing current-session Task for that turn's evidence derivation. It does not
bind later Write/Edit calls, expand scope or make a companion count as earned.
Without a host environment binding, conflicting metadata/prompt bindings or an
unknown selected Task derive no companions. An existing host binding selects
its Task even when metadata or prompt names another Task. Change or clear that
binding through the host's supported environment/session configuration before
the next event; unsetting it in a child shell cannot change an earlier host
callback. Do not handwrite companions to compensate. Retain other unfinished
Tasks rather than closing them to manufacture uniqueness or widening scope.

Keep investigate, junior-senior, artifacts-posted, review and test gate files
beside this task's think gate, with the same exact identity. Never overwrite
another task's signals. Legacy session-level `think-gate.json` and repo-suffixed
session files are read as legacy tasks; new writes always use task directories.
Workspace-root files cannot authorize mutations. The sole unknown-session
root read is diagnostic-only and requires an exact canonical repo match.

Own-session lifecycle files do not require an existing task gate: the host's
current session may create/edit/remove its task gate JSON and write its own
plans/data. Bounded mkdir/rmdir may scaffold task directories. Other sessions,
workspace-root signals, symlink escapes and opaque program execution are not
exempt. For a plain task ID, keep its pre-mortem in the current host session's `plans/`; shared workspace/repository plans are eligible only for a full repository-qualified ticket.

Bootstrap designing, write the investigation/pre-mortem evidence, then
transition the same gate to implementing; dispose and clean up after completion.

**Bootstrap without a ticket or shell helper.** Use the Write tool with the
literal, host-resolved own session path and a stable directory such as
`tasks/report-run/think-gate.json`. An explicit `task_id` is sufficient for an
operational request; a hash-suffixed directory and a GitHub issue are not
prerequisites. The gate's `repo_root` is the target project, not the Craft
workspace. A different task's gate never supplies or blocks this task's
authority. If the gate reports an unresolved or templated host binding, repair
that host binding before attempting lifecycle writes; no chosen path bypasses
it. A transcript displaying `{{SESSION_PATH}}` is normalization, not evidence
of a literal callback environment. Keep JSON companions beside the task gate
and its pre-mortem in this session's `plans/`, naming the task identity. Older memories
recommending UUID-keyed workspace-root files describe retired behavior and
must not be followed.

**Gate metadata for scratch execution (#1152).** `repo_root` names the Git
repository that physically contains the mutated or executed paths, not the
repository the files came from. Scratch extracted or created under this
session's `data/` belongs to the repository that contains that directory,
which is usually the workspace repository. The exception is a repository
nested inside `data/`, which needs its own clone-rooted gate. Declare that repository as
`repo_root` and keep `scope_paths` exact to the scratch directory. "Not the
Craft workspace" means not merely because it is the session cwd. It does not
apply when the workspace really is the physical target. Do not keep the source
checkout as `repo_root` for scratch edits or tests, and do not switch one
gate's `repo_root` mid-task. A read-only source operand (for example
`git -C <source> archive`) is not a reason to set `repo_root` to the source
repository or to widen write scope over it. Its target semantics are governed
by #1166. Until that lands, a refusal there is a known gap, not something to
work around with broader scope. Work outside any Git repository keeps its normal
operational route; a non-Git directory is not given a made-up Git identity.

**Canonical issue reports from non-Git data (#1319).** An existing own-session
Task may post descriptive evidence to its exact full `owner/repo#issue` without
a Git-backed scope witness. For a report prepared outside every Git repository,
declare the truthful absolute private report directory under this session's
`data/` as `repo_root` and its actual report paths as `scope_paths`. Keep the
full canonical ticket and current host-resolved `sessionId` in that Task's own
`tasks/<stable-slug>/think-gate.json`. Record its real status, such as
`reviewing`; reporting does not require an implementing Task or code artifacts.
Do not invent a clone or dummy Git witness, or borrow another Task's artifacts.
The Git-backed scratch execution rules above still apply when a repository
physically contains the work.

Use an explicit literal repository or canonical issue URL, for example:

```bash
CCP_TASK_ID='owner/repo#803' gh issue comment 803 --repo owner/repo --body 'Review complete; the owner hold remains.'
CCP_TASK_ID='owner/repo#803' gh issue comment https://github.com/owner/repo/issues/803 --body-file /absolute/own-session/data/review/report.txt
```

A file operand must be a bounded UTF-8 regular text file (at most 1 MiB),
physically inside the current session's `data/` and claimed by the selected
Task. Sensitive credential paths, symlinks within that private path boundary,
hardlinks and foreign or unclaimed files are rejected; benign suffixes and
hidden report names do not confer or remove authority. Literal inline text
does not require a file operand, but still requires that Task's own private
data scope. A binding selects an existing Task; missing or ambiguous ownership,
foreign tickets/repositories/sessions and host overrides do not gain authority.
This route grants descriptive issue comments only, not code mutation, state
changes, review approval, merge, general API access or release of an owner hold.

A positive reader classifier runs before gate lookup. Bounded diagnostics
(syntax checks, standard test/bytecode/lint commands, document/package readers,
and Git fetch) are also allowed without artifacts during designing/reviewing.
They are an explicit investigation allowance, not proof of no side effects:
tests execute project code and tools may write caches/metadata. Arbitrary
scripts, clones, source-fixing/output-file flags and opaque execution are not
investigation exceptions. Unknown shapes are not assumed read-only.
Unscoped mutations fail closed: open a scoped task gate,
never borrow another task's implementing state. In a non-git CWD, use an
in-command `cd`, `git -C`, an explicit target path, or a declared scope path.

The `lastUpdated` field (ISO 8601) is consumed by the temporal decay
check. Omitting it forces the hook to fall back to file modification
time, which is less reliable across machines and sessions.

### Task lifecycle before creating

Resolve the current host session and full task identity before writing a signal. An existing gate for that exact task may be resumed within its authorized scope. A new task uses its own task directory and declared scope; sharing a repository does not make another task's signal obsolete.

After an owned task completes, record its disposition and mark that task terminal/disposed while preserving its identity, evidence and canonical claims. Removal, when needed, is limited to that completed task's own authorized lifecycle files and must not resurrect a stale legacy signal. Never delete another active task's gate, clear a shared root signal or widen scope to make a new task pass. If ownership is ambiguous, diagnose the binding and hold only the affected mutation.

### Updating during work

Update `lastUpdated` when the task's status changes or when resuming
work after a significant pause. The hook warns at 4h (stale) and 24h
(expired) without an update.

Status transitions: `designing` then `implementing` then `done-awaiting-pr`

### Archiving after completion

When the PR is merged and work is complete:

1. Set the completed task to a terminal status such as `disposed`, with a `disposition` summarizing outcome
2. Post the disposition to the ticket if not already there
3. Retain its terminal record/evidence, or remove only that completed task's own lifecycle files when authorized cleanup is needed. Deleting a signal is not a prerequisite to starting another task.

Signal files are scoped per session/task. Terminal records no longer compete
with active tasks or authorize mutations. Own-session cleanup remains allowed
without reactivating implementation. Keep the reserved per-task canonical claims;
remove only individual task directories after their signal files. Keep implementing status through the final
push/PR operation; if new source or Git mutations are needed after a terminal
transition, reactivate implementing with current complete artifacts.
Never remove another session's signals.

## Attribution Policy

NEVER include AI or agent attribution in designs, documentation, or any output.

## Session binding compatibility

Literal unresolved placeholder identities such as `__SESSION_ID__` and `__SESSION_PATH__` are rejected, including directory basenames. Directory bindings must be absolute and cannot contain `{{`, `}}`, `${...}`, `$NAME` or `%NAME%`; a legitimate path containing those forms also fails closed and needs a different host binding. Do not create a literal placeholder directory. Native runtimes can bind `CLAUDE_SESSION_ID` or `CLAUDE_CODE_SESSION_ID`; a generic SDK UUID alone does not identify a Craft directory. Any parsed tool callback remains a host invocation even if identity fields are absent, so it cannot borrow terminal root test evidence. Truly unbound native Git stdin remains supported.

Only a fully qualified numeric `owner/repo#N` ticket uses repository-plan compatibility. A short `#N` is a plain task ID and requires a pre-mortem in its owning session's `plans/`.
