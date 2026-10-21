---
ticket_refs:
  - siege-analytics/claude-configs-public#1116: read classifier blocks docker management-form reads
---

# Self-review: #1116 docker management-form reads

## Assumptions

Pre-author-inventory: the electinfo#348 stopped-session audit (comment 6307130236) recorded a review session blocked on `docker image ls`. On main d51d598, with no task gate, `docker image ls ...` blocks while `docker images ...` passes. The 18 new allow cases fail on develop.
Investigate-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1116
Pre-mortem-artifact: plans/pre-mortem-1116-docker-mgmt-reads.md
Hostile-review-artifact: https://github.com/siege-analytics/claude-configs-public/issues/1116#issuecomment-6307463316
Project-contribution: a session can list and inspect images, containers, volumes and networks in Docker's current command form without opening a task gate. Every other verb under those objects still needs one.

1. `DOCKER_MGMT_READ` maps each of `image`, `container`, `volume` and `network` to its read verbs.
2. `simple_ok` admits `docker <object> <verb>` only when the object is the first argument and the verb the second, matched exactly. A global option, a bare object, or any other verb is not proven, as before.
3. Unchanged: compound commands, redirections, expansions, env prefixes and wrappers go through the existing checks.

## Peer review

- **writing-tests:** read_allowlist gains 19 allow cases (one, `docker images`, is pre-existing) and 28 block cases. The block cases cover every write verb of the four objects, a bare object, a global option, a compound, and the legacy `rmi` and `system prune`.
- **Hostile review:** no blockers and nothing to fix. Two nits, both already present for the bare forms admitted before this change, are left as they are:
  - Docker CLI plugin hooks and ssh contexts can launch a binary without showing in argv.
  - `container inspect` prints `Config.Env`, as `docker inspect` already does.

## Not done

- `git merge-tree --write-tree` and inline `python3 -c` package probes stay blocked. They match current policy: object writes count as writes (#1079), and inline execution is unbounded. The electinfo#348 audit cited them, and #1116 records why they are out of scope.

## Test plan

- read_allowlist 354/0 here. On develop's classifier, 336/18, the 18 being the new allow cases.
- review_risk_test; skill-inventory, generated-source-authority and review-risk-metrics `--check`.
- The full local validate job, hook suites with stdin closed.
