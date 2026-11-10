# Copy inputs are reads; alias creation stays scoped (#1236)

## Prework and boundary

Follow-up to closed security issue #1100 and live diagnostic report #1238, preserving its hardlink/link-creation controls. Native `cp -pR` preservation commands were denied and agents treated broadening the source scope as normal procedure. Current code already excludes ordinary sources, but its 2,000-entry symlink inspection returns true on uncertainty and promotes the entire source to a write target.

Implement a finite supported copy-option grammar and bounded source-alias inspection. Ordinary source entries are reads. Preserved symlink endpoints, explicit link-copy endpoints and move sources remain scoped; all existing destination inspection and mixed-command checks remain. Explicit follow-all copying is a supported non-alias alternative, with its changed preservation semantics disclosed. Unknown syntax/inspection failures fail closed; never invent a source mutation.

## Validation

Red-first actual hook tests for the 2,000 threshold and a 19,033-entry ordinary-file source; paired source symlink/hardlink, destination escape, move, unknown-option and compound-write controls. No actor gate, instruction, settings, provider, session or business mutation. Canonical refresh and independent review precede any publication/merge. Native actor evidence remains private; no transcript dump in public artifacts.

## Status

Implementation in progress. No live or protected changes.

## Separate bundle read correction

Root supplied actual native refusal for `git bundle list-heads` on preserved evidence. A separate reader slice models only literal list-heads and verify with finite quiet syntax; create/unbundle, unknown flags and composed writes stay gated. Real Git fixture creates and inspects a bundle; no stdout mock. A synthetic bare mirror also proves supported fsck integrity flags leave every repository file unchanged; --lost-found/unknown/output flags and composed writes stay denied. This does not authorize bundle mutation or arbitrary shell runners.

## Assumptions

Source and destination inspection is point-in-time filesystem modeling, not a race-free snapshot or sandbox. Preserved aliases retain both-end authority. Clone flags create independent bytes; dereference flags change backup semantics and are not silently substituted. Existing destination inspection limits are unchanged. Unknown copy flags now reject rather than inheriting a modeled destination; CHANGELOG records the migration.

Pre-mortem-artifact: plans/copy-source-read-scope-1236.md#assumptions
Hostile-review-artifact: plans/copy-source-read-scope-1236.md#peer-review

## Peer review

Root independently inspected frozen runtime tree d2bbd7e74f83ec2b3c9db01a4c6143f2c2fd9477 and accepted the source in principle: alias endpoints, root-link handling, option precedence/value shielding, macOS clone flags and finite bundle reads. Final protected/integration review remains required; this is not a second invented reviewer or permission for release. Issue1238's remaining generic wrong-target diagnostic is not claimed complete.

## Lead review

Root accepted the bounded implementation direction and required real large-tree/real-bundle counterfactuals plus a breaking migration note. Author checked destination and mixed-write negatives; discovered the allowlist's old copy positive reused a source holding foreign symlinks, retained that as a negative and added a clean source positive. No alias protection was weakened to satisfy that fixture.

## Quantified claims

The pre-suffix broad producer passed copy4, reader20, corrected allowlist356, full risk and freshness with stable input blobs; that receipt is retained. After the bounded suffix-getopt correction, a new genuine receipt passed final copy5 plus real bundle/fsck2 and freshness on current blobs. GNU CLI parity executed real temporary copies and alias creation, not stdout mocks. Attached suffix data is not an option; a separate later link flag still needs both endpoints. Original large-copy implementation failed both 2,001/19,033 subcases and macOS clone shape. Real Git bundle fixture failed before the read branch and passed afterward. Initial legacy allowlist 354/1 failure is retained. Intermediate Gates59 passed but source/test changes overlapped that run, so it is supporting evidence, not final-blob full-suite proof. Canonical refresh passed; protected CI and no-live-deploy limits remain.

Verified-by: actual bounded fixture commands and immutable source/log hashes in the source review and content-bound test evidence receipts for #1236; no native actor mutation or installed-result claim.
