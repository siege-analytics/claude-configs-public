# Fixture — PASS

Trivial-against-state Category `local-only` with a full evidence chain
must remain valid per `_authoring-against-state-rules.md`. This is the
legitimacy-preserved case.

## Trivial-against-state declaration

Category: local-only
Cannot produce error: Change is a private helper in scripts/local-utils.sh that runs only during local development; no shared cluster state contacted.
Evidence: `git diff --stat` shows 1 file (scripts/local-utils.sh) changed, 3 insertions.
Falsification: If any file outside scripts/ is modified, or if the helper is imported by a deployed path, this declaration is wrong.
