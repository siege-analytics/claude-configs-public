# Bounded diff-files pre-mortem recovery

Goal source: siege-analytics/claude-configs-public#1327.

## Recovery timing

This risk memo was authored after source edits and focused tests, during the
publication coordinator's authorized recovery of missing durable prerequisites.
It records the risks reviewed in the tool history and the current evidence. It
is not represented as a pre-edit artifact or as independent hostile review.

## Failure modes and controls

| Failure mode | Consequence | Control and falsifier |
|---|---|---|
| Broad common-diff-options admission | A reader could write output or enable a program | Admit only the exact `--quiet` tail after existing vetoes; helper/output and unknown-option controls must deny |
| Assuming quiet suppresses trusted helpers | Executable behavior could escape the mutation gate | Official diff implementation review and a synthetic trusted-helper marker control show `--ext-diff` can execute despite quiet; that shape stays vetoed |
| Inconsistent composed-command parsing | A harmless probe could block a valid owned write or lend authority to another write | Task parser reuses the authoritative grammar; exact allowed and denied Task/file targets are tested |
| Confusing directory and index selection | A successful comparison could be reported against the wrong index | Real Git fixture contrasts dirty default index with an empty pre-existing private index; later native acceptance must identify its actual index context |
| Config/dynamic/shell authority expansion | A different command could borrow the reader exception | Existing configuration, expansion, redirection, pipeline, and companion-write denials remain under focused negative controls |
| Treating source tests as deployed acceptance | The original runtime blocker could be falsely declared resolved | Source work, reviewed publication, deployment, and genuine native callback acceptance are separate owner steps |

## Canary and rollback boundary

The isolated real Git fixture and hook callbacks are local source canaries.
They do not establish installed native runtime acceptance. The publication owner
must use the normal reviewed release path, then observe a genuine intended
native callback with its actual repository/index context. If that introduces a
regression, revert the bounded source change through the same reviewed path;
do not restore stale authority or modify Task phase evidence to force a pass.
