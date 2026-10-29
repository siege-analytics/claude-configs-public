# Self-review: Craft runtime recovery

## Assumptions

Goal source: plans/craft-runtime-recovery.md
Plan reference: plans/craft-runtime-recovery.md
Investigate-artifact: plans/craft-runtime-recovery.md
Pre-mortem-artifact: plans/pre-mortem-craft-runtime-recovery.md
Hostile-review-artifact: plans/hostile-review-craft-runtime-recovery.md
Project-contribution: Restore an agent's ability to explain and repair failed
prerequisites while preserving mechanical action checks and coherent deployment.

The operator authorized repair and local installation on 2026-10-29. Source work
is based on current develop plus the canonical main promotion merge. PR #1111
and draft PR #999 changes are integrated in this repair branch, with metadata
conflicts reconciled additively. Their historical review artifacts retain their
original scope; the independent review for this repair is the artifact above.

## Peer review

The implementer inspected the hook/registry/build/verifier/drift chain and
reproduced the installed failure before editing. The separate reviewer inspected
the runtime, deployment, cleanup, and malformed-claim changes. Three findings
were fixed and re-reviewed: trailer insertion after cleanup, assertion-dependent
verification, and omitted comment settings during isolated trailer processing.
The report pins reviewed source hashes and clearly limits its scope. No
cross-provider review or complete fresh audit of the imported classifier is claimed.

## Lead review

The repair follows the existing runtime policy instead of removing action gates.
Unknown/ambiguous hosts still block; verified packaged Craft can receive recovery
prompts; explicit child hard stops survive. The installer, registry, verifier and
drift checker agree on the colocated manifest. Custom Git cleanup is checked
against final real messages, not against a second hand-written expected parser.
Config snapshots exclude executable trailer commands and isolate interpretation
from a concurrent repository configuration change.

Blast radius: prompt wrapper, deployment, verification and ticket enforcement
are high-risk shared paths. Both newly imported helpers remain Tier C. Existing
task gates, native Git enforcement, settings and automation permissions remain
in place. Alternate/headless host ancestry support is still unproven and fails
closed. A reply-only live Codex check does not prove its tool-hook delivery.

## Quantified claims

- All 46 hook suites pass after the affected-suite reruns. The four initial
  read-case failures used a Linux procfs path absent on macOS. A real root symlink
  now exercises the same escape; that suite passes 354 cases. Final targeted
  results: 133 ticket cases, 15 runtime cases, 41 verifier cases, 5 malformed/KB
  diagnostic cases, and 398 imported classifier cases. Task-keyed coverage also
  passed all 50 tests.
- Independent review: 15 runtime checks, 72 real-commit comparisons with zero
  mismatches, six optimized/unoptimized manifest controls, and a trailer-command
  non-execution sentinel.
- All 14 selected package/deployment/authority suites pass. After the source
  checkpoint, immutable generation passed 19 tests and selected registration
  passed 14 tests with physical TMPDIR=/private/tmp. The initial failures were
  source-snapshot mismatch and the macOS /var symlink, respectively; neither was
  silenced by weakening the implementation's provenance/path checks.
- Live installed Claude session returned CRAFT_RECOVERY_OK; a separate Craft
  ChatGPT session using pi/gpt-6.1-sol returned CODEX_CRAFT_RECOVERY_OK. The older
  pi/gpt-5.5 option was rejected by the service and was removed from that local
  connection's offered models; its default is now the successfully tested model.

## Test plan

Immutable package/registration checks are complete. Regenerated packages and
inventories are checked for freshness. The current workspace passes local
enforcement probes, including native push deny/allow controls. The operator has
also explicitly authorized develop-to-main promotion. After green hosted checks
and promotion, install the canonical main revision with a rollback backup, then
repeat installed allow/deny and bounded live response checks. The historical
architecture audit is a subsequent, separately recorded deliverable.
