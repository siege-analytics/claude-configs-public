# Design: bounded Git repository bootstrap (#1240)

## Context and intended result

The existing action model calls `_git_toplevel` before understanding init/clone. A task-scoped scratch cannot become a repository. Supported init and explicit clone should identify their actual destination, pass ordinary task/risk checks, and run without modifying live hooks or weakening role boundaries.

## Approach

Add one bounded builtin init/clone destination model before the existing generic Git path. Preserve all other Git routing. Model a physical destination under an existing parent; normal init may preserve ordinary project files, while clone/bare init need an empty destination. Existing .git/bare/linked metadata, symlink destinations, helper/template/config redirects and unknown options remain rejected. Local directory sources require --no-local so objects are independent rather than hardlinked or borrowed through alternates. Local bundle input remains read-only.

Use unchanged task identity/scope and effective-risk selection. A fresh nested scratch may initially belong to its enclosing workspace task, but after creation a future index mutation must use the new actual repository identity in that same task and companions. Unknown new-tree risk remains conservative C, not a new user permission.

## Falsification and delivery

Real temporary Git operations plus all configured Bash PreToolUse hooks must allow supported shapes and deny foreign/wrong/lifecycle/scope/metadata/helper cases. An actual alternates-source fixture must produce an independent clone that survives loss of the original object source. Run existing task/risk/read regressions and normal generated validation. Independent source review, exact-head normal CI and later authorized publication/installation remain separate. The first review found local object aliases; require --no-local rather than treating a successful clone as proof of independence.

## Review-driven boundary corrections

- Native local clones may create hardlinks or retain borrowed alternates. Require unambiguous --no-local for directory sources and prove independence using actual inodes, no alternates and loss-of-source fsck.
- Git configuration can rewrite a nominal HTTPS source to a helper. Resolve exactly once with local-only `ls-remote --get-url`, validate the effective source, and leave the real command unchanged.
- Configured templates can copy a symlinked object directory and cause init to create outside metadata. Deny the unmodeled configured template, with an exact empty per-command --template= route that copies none; test both denial and successful own-destination creation. Never repair this by changing global settings or asking for repeat permission.
