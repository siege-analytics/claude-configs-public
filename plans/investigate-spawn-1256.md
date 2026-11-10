# Spawn isolation investigation — #1256 item 3

## Scope and chronology

Root assigned only the sibling-worktree spawn issue; other #1256 items and live
publication remain separate. This durable record was authored after the initial
implementation. The issue/source reads, proposed design and failing real-Git
fixture preceded the runtime edit in the native task transcript. This record
makes no claim to have existed before that edit.

## Pre-author inventory

Inputs read: #1256 body/comments; closed #248; current develop ce21650c;
installed-source a0dc815f; spawn-guard.sh and its existing scenario suite.

Knowledge requirements: native spawn payload workingDirectory/cwd semantics,
Git primary versus linked worktrees, per-worktree gitdir registration, and the
existing read-only/non-Git routes.

Contact-point measurements: installed Mac spawn-guard SHA256 is
`a7e4067f1e94e763340c4a9dac9d14c7ce96668f3027eb2aceef909db7b82198`,
byte-identical to `git show a0dc815f:hooks/agent-comms/spawn-guard.sh`.
The installed checksum comparison occurred during review preparation, not before
implementation. Current develop retained the same lexical worktree waiver.

Surface areas: actual mcp__session__spawn_session JSON; primary, sibling and
nested linked directories; aliases; copied .git pointers; host normalization;
Git-unavailable ordinary directories; read-only review; malformed admin metadata.

Hypothesis: spelling a phrase/path cannot establish isolation; Git ownership can
accept an existing registered sibling without granting authority from its name.

Conclusions: the initial real-Git suite failed 5 of 8 tests against the unchanged
guard. Valid sibling/subdirectory targets failed; primary checkouts with magic
phrases/path names and a missing target could pass. #248 was historical origin,
not a current duplicate fix. #1256 remains the umbrella tracking issue.

## Bounded design and acceptance

Inspect the actual literal absolute child target. Require linked Git admin state,
its registered backpointer and separation from the known parent's checkout for
write-capable Git work. Bound metadata reads; no network, sessions or live config
writes. Existing non-Git directories and explicit read-only review keep their
routes. Prepare the child directory before spawning; leave the parent in its own
workspace. Neither a phrase nor a directory basename proves isolation.

Root independently verified the actual Craft 0.15.8 host path behavior: relative
paths use host process.cwd, omitted targets remain undefined, HOME expressions
expand, and lexical normalization precedes filesystem symlink traversal. The
guard therefore requires literal absolute writer paths without those HOME
substitutions and uses normpath before realpath. No relative-target host claim
is made from a Python-only fixture.
