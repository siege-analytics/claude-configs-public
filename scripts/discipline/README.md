# Discipline diagnostics

These legacy helpers are available when their specific checks are useful. The current installed hooks and role contract define enforcement; a helper output does not create execution authority or a universal veto. Verify the actual installed caller before claiming it runs one of these scripts.

| Script | Inputs | Legacy result | Diagnostic |
|---|---|---|---|
| `check-self-review.sh` | commit SHA and artifact path | 0 OK / 2 BLOCK | Historical trailer, section and artifact-history checks. Current proportional review uses the installed policy; do not impose this older format through a stale call reference. |
| `evaluate-ticket.sh` | GitHub ticket reference or local file | 0 PASS / 2 BLOCK | Historical six-part structural rubric. Missing structure is a gap list, not a prohibition on investigation, implementation or diff review. |
| `check-trivial-claim.sh` | artifact path | 0 OK / 2 BLOCK | Historical Reason/Evidence/Falsification block validation when that format is actually applicable. It is not a mandatory exemption procedure for routine work. |

Ticket evaluation is described by [skill:evaluate-ticket]. Read the user request, intended outcome and relevant evidence; resolve material ambiguity while continuing independent authorized work. A formal PASS does not establish factual correctness or permission, and a diagnostic BLOCK does not revoke an existing grant.

`evaluate-ticket.sh` reads GitHub through `gh issue view`. Linear/Jira identifiers are recognized but their fetchers are not implemented. An unavailable tracker adapter is a method limitation; use supplied or otherwise available evidence rather than requiring unrelated tool installation or pretending a fetch succeeded.

The script interfaces remain unchanged for compatibility. No current hook is newly registered or bypassed by this documentation.
