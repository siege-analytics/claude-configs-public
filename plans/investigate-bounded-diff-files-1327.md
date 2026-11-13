# Bounded diff-files investigation

Goal source: siege-analytics/claude-configs-public#1327.

## Recovery timing

This durable memo was written after the source edits and focused tests. Source
inspection and official Git implementation review preceded the edits in the
actual tool history, but no durable pre-edit investigation memo was created.
The publication coordinator authorized recovery of that missing memo within this
isolated reversible task. This record does not claim to predate implementation.

## Environment and source inventory

The canonical task-branch helper created
`fix/1327-bounded-diff-files-20261112` in an isolated worktree from freshly
selected remote develop `d3581bbd429d03ae82128187b9e46bcc624df278`.
The stale original checkout and installed runtime were not edited.

`hooks/lib/read-only-command.py` owns the released reader verdict.
`hooks/lib/task_actions.py` imports that reader for whole-command classification,
but its companion-mutation parser also needs the same exact probe grammar.
A classifier-only comparison of the protected source and candidate gives
unproven versus proven-read for the literal synthetic probe. This comparison
runs classifier Python only; it does not replay the refused Git command.

## Git semantics

The official [Git v2.47.3 plumbing entry point](https://github.com/git/git/blob/v2.47.3/builtin/diff-files.c)
loads basic diff configuration, initializes revisions, reads the selected index,
and compares it with the worktree. The shared
[diff implementation](https://github.com/git/git/blob/v2.47.3/diff.c)
handles external diff, text conversion, output options, and quiet status.
Quiet changes output and exit behavior; a trusted helper can still execute when
external diff is enabled. The candidate therefore proves only the exact
`diff-files --quiet` argument list after the existing unsafe-option vetoes.
It does not add this plumbing command to the broad Git reader set.

`-C` selects the repository directory. A pre-existing `GIT_INDEX_FILE` can select
a different index within the existing trusted environment boundary. No new
configuration or environment-assignment grammar is admitted.

## Intended behavior and verification

The literal probe is a reader without an active Task and during designing or
reviewing. A companion mutation still needs its own exact Task and file scope.
Unknown options, configuration overrides, dynamic arguments, helper enablement,
output writes, and shell companions do not borrow reader authority.

`hooks/_test/diff_files_reader.py` imports the authoritative reader and Task
parser, calls the real mutation hook with isolated fixtures, and exercises Git
in an isolated synthetic repository. The fixture checks clean/dirty status,
unchanged repository and index bytes, configured and environment external diff,
textconv defaults, a pre-existing private index, and an enabled trusted helper
as a negative control. This is source verification, not acceptance of the
particular refused native preflight.

## Publication boundary

Required review, scanner dispositions, full hook-suite results, and the normal
commit/push checks remain binding. The publication owner controls release,
deployment, later native callback acceptance, and any rollback. No phase flip,
private runtime gate edit, force operation, or hook bypass is part of this fix.

## Recovered inventory

Inputs read: the issue's observed refusal and bounded follow-up; the canonical
branch helper and its selected develop output; the authoritative reader, Task
parser and existing reader/Task fixtures; official Git plumbing and diff sources.

Knowledge requirements: Git global versus subcommand options, plumbing helper
defaults, trusted-helper quiet semantics, selected index versus worktree/HEAD,
and the distinction between whole-command reads and companion mutation targets.

Contact-point measurements: the base classifier returned unproven for the
synthetic literal probe; the candidate returned proven-read. Git reported Apple
Git 2.54.0. The actual fixture returned clean/dirty exit status against the
selected index, preserved its bytes, and invoked a trusted helper only in the
negative enabled-helper control. These measurements were made during this task;
the durable inventory record was recovered afterward as stated above.

Surface areas: the shared reader's `git_ok`, the Task parser's `reader`, their
existing shell expansion/output/config vetoes, and hook callbacks. The runtime
installation, Task phase state, release routing, and user private index contents
are outside the edit surface.

Hypothesis: the exact quiet plumbing tail is a read within the existing trusted
Git environment/configuration boundary, while common-diff-options as a class
cannot be admitted. Reusing the same predicate for a companion probe preserves
actual mutation scope.

Conclusions: focused production-import tests and the full hook suite support the
bounded source change. Independent scanner dispositions are required for the
complete non-clean scan. The original installed native callback remains unproven
until the publication owner observes it after reviewed deployment.
