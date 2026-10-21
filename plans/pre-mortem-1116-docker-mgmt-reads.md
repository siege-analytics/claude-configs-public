---
ticket_refs:
  - siege-analytics/claude-configs-public#1116: read classifier blocks docker management-form reads
---

## Pre-Mortem
Task: admit `docker image|container|volume|network` followed by one of that object's read verbs as a proven read.
Ticket: siege-analytics/claude-configs-public#1116

### Tigers

#### Tiger 1: an admitted verb writes under some option (Severity: high)

The admitted verbs are `ls`/`list`/`ps`, `inspect`, `history`, `logs`, `top` and `port`. None of them changes daemon state or writes a file under any option in the Docker CLI. `logs -f` follows output and writes nothing, the same as the bare `docker logs` that is already admitted. `--format` takes a Go template, which docker evaluates client-side and only to print.

Mitigation:
- The verb is matched exactly against a per-object set. The object must be `args[0]` and the verb `args[1]`, so a global option before the object (`docker -H x image ls`) is still unproven.
- A blocked case is pinned for every write verb of the four objects.

#### Tiger 2: the verb check reads the wrong word (Severity: medium)

`docker image --filter x rm`-style reordering is not valid Docker syntax: the verb must follow the object. A bare `docker image` (help only) is still unproven, which fails closed.

#### Tiger 3: a compound command rides in on a read (Severity: medium)

Unchanged. Compound commands still go through `compound_verdict`, and every segment must be proven. `docker image ls; docker image rm a` is pinned as blocked, and `docker image ls | head -3` as allowed.

### Launch-Blocking Assessment

None identified, provided the suites stay green and the hostile review finds no admitted verb that writes.
