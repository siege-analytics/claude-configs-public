# Hostile review plan: native Git hooks in Claude settings (#1038)

Probe:

- absolute current-root and old-root `hooks/git/pre-push-*` commands;
- relative `hooks/git/pre-push-*` commands;
- symlink aliases into managed pre-push readers;
- intentional dual-use `hooks/git` guards that must remain;
- same basename outside an exact `hooks/git` path;
- operator hooks sharing event/matcher metadata;
- valid non-command prompt/agent hooks with no `command` field;
- malformed, empty, compound, quoted, and whitespace-bearing command hooks;
- repeated installation and interrupted/failed preflight;
- native `.githooks/pre-push` bytes and real deny/allow behavior after cleanup.

Reject if an operator or canonical dual-use hook is removed, a managed pre-push protocol reader survives any Claude event array, settings mutate on malformed input, or native Git registration is weakened.
