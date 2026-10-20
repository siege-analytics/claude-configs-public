---
ticket_refs:
  - siege-analytics/claude-configs-public#1089: read classifier proves kubectl -n get delete, ss -K and gh --web
---

## Pre-Mortem
Task: stop the released read classifier proving `kubectl -n get delete`, `ss -K` and `gh … --web`.
Ticket: siege-analytics/claude-configs-public#1089

### Tigers

#### Tiger 1: kubectl reads stop being proven (Severity: medium)

Mitigation:
- Global options and their values are skipped by name (`-n`, `--namespace`, `--context`, `--cluster`, `--user`, `-s`, `--server`, `--kubeconfig`, `--token`, `--as`, `--request-timeout`, TLS flags, `-v`), and `--flag=value` is skipped whole.
- `kubectl get pods -n x`, `kubectl -n x get pods`, `kubectl --namespace=x logs p` and `kubectl -A get pods` are pinned as proven.
- The legacy gate blocks every `kubectl` through its own `'kubectl '` mutation indicator anyway. That is unchanged.

#### Tiger 2: gh short-option clusters falsely match -w (Severity: low)

Mitigation: the cluster scan stops at value-taking letters (`HpqtRJLSB`), so `gh api … -q .workflow` stays a read. That case is pinned.

### Launch-Blocking Assessment

None identified, provided the suites stay green at the head.
