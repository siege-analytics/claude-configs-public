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

- Full hook run: 45/46 initially passed. The four failing read cases used a Linux
  procfs path absent on macOS. A real root symlink now exercises the same escape;
  the rerun passed 354 cases. Updated focused suites are rerun after review fixes.
- Independent review: 15 runtime checks, 72 real-commit comparisons with zero
  mismatches, six optimized/unoptimized manifest controls, and a trailer-command
  non-execution sentinel.
- Package/deployment tests: 12/14 initially passed. Immutable-generation tests
  require the modified build tool to be in the committed source snapshot;
  registration tests also need physical macOS temporary paths. These two suites
  will be rerun after this local checkpoint with TMPDIR=/private/tmp.
- Live installed Claude session returned CRAFT_RECOVERY_OK; a separate Craft
  ChatGPT session using pi/gpt-6.1-sol returned CODEX_CRAFT_RECOVERY_OK. The older
  pi/gpt-5.5 option was rejected by the service and was removed from that local
  connection's offered models; its default is now the successfully tested model.

## Test plan

Complete immutable package/registration checks against the committed snapshot,
regenerate packages and inventories, verify freshness, install only the reviewed
runtime overlay with backups, then run installed allow/deny controls and a final
bounded live response check. Do not publish a release or mark unrun checks passed.
