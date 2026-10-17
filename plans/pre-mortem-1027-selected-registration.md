# Pre-mortem: selected registration (#1027)

Base: e4298d6a7e9fe3a8f4f31f067bd92edc9978f36c.
Branch: feat/1027-selected-registration.
Goal source: #1027, accepted comments 6225067704 and 6225119253, and the
operator's registration instructions. The accepted #1031 dependency is immutable.

## Investigation and pre-author inventory

Inputs read: issue body and all comments; #1031 body, evidence and reviews for
rejected d00f73f and accepted 127383e; pre-mortem, self-review, hostile-review,
testing-frameworks and commit skills; the data-intensive shelf.

Knowledge requirements: distinguish immutable source selection, independently
pinned policy adoption, generated configuration, local Git effects and provider
authority. A receipt can establish only the first three observations.

Contact-point measurements and surface areas:

- bin/package_selection.py:82-172 verifies exact component Git snapshots and
  independent policy inputs. It accepts only resolver-only and rejects required
  registration capabilities. Existing receipts say composition-only/none.
- bin/compose-project.py:190-215 uses canonical caseless GeneratedFiles ownership.
  Every output must continue using that guard before filesystem publication.
- bin/install-hooks.sh:24-76 preserves unrelated settings; :88-128 assumes the
  entire legacy settings/native closure. :135-153 writes Git config and settings
  separately, with exception rollback. This is not crash-atomic multi-file state.
- bin/wire-enforcement.py:164-198 selects the fixed Craft wrapper. Selected local
  Claude registration must be explicit and cannot invoke this implicit backend.
- bin/verify-enforcement.sh:34-38 pins a Siege kernel; :100-148 assumes Craft
  guards. A selected branch must recompute expected bytes from verified inputs.
- .githooks/commit-msg:29-149 and hooks/git/pre-push-self-review.sh:43-193 impose
  the legacy review/ticket contract. Preserve them as measured compatibility
  behavior; independent projects must not import their content or requirements.
- scripts/ci/protected-policy-range.py:35-60 pins Siege dependencies, :434 loads
  ep.load_inputs, :459-477 hardcodes the promotion exception. Explicit selected
  inputs must reach the existing evaluator without transferring host authority.
- bin/effective_policy.py:328-378 verifies separately pinned inputs, and :511-554
  distinguishes a policy allow from final unknown. This evaluator remains shared.

Hypothesis: extending the existing selected builder and install/wire/verify
entrypoints with an independently pinned registration definition can produce
complete, reproducible local registration without importing the Siege closure.
Falsification: any usable registration with unverified inputs, any hidden Siege
read, changed command/helper accepted, or failed registration damaging prior state.

## Design and pre-implementation comprehension

Keep resolver-only exactly composition-only. Add an explicit local registration
backend, with separately supplied registration source/digest, policy source/digest
and identity. Its reviewed definition selects a bounded adapter and exact runtime
inventory; candidate selection, generated receipts and content bundles cannot
supply those trust anchors. Verify immutable inputs before generating settings or
native inventory. Installation/verifying recompute from those inputs, compare full
command vectors and executable bytes, and preserve operator settings.

Use the existing native/protected call sites and effective_policy/gate_contract
engine. Retain legacy behavior behind an explicit compatibility descriptor. No
arbitrary executable discovery, new policy language or inferred profile adoption.
Registration state is configured, not live/provider authority. Independent fixtures
physically omit all Siege bundle/legacy content before the normal builder runs.

Sequence: artifacts and issue comment; red normal-entrypoint tests; registration
input/build support; native/protected input propagation; installer/wire/verifier;
real local Git corpus and complete compatibility comparisons; docs/ontology/risk
coverage; full exact-head matrix, normal hooks, normal push and draft develop PR.

## Adversarial comprehension check

The initial plan's phrase "atomic registration" would gloss over separate Git
config and settings writes. A complete design must expose the commit point,
retain old bytes, reject incomplete registrations and test interruption/recovery.
A successful builder or a matching receipt is not a native decision test. Likewise,
legacy ticket escapes and review-tier checks cannot silently become new generic
policy. Complete vectors and compatibility effects must be measured in full.

## Tigers

1. Generated metadata becomes the expected value for its own verification.
   Evidence: package_selection.py:168-172; effective_policy.py:328-378.
   Scores integrity/scope/reversibility/dependency/latency: 100/90/70/90/90;
   weighted 88.5, launch-blocking. Mitigation: independent registration and policy
   pins at each public boundary; recompute output from immutable source inputs.
2. Extra command/interpreter or changed helper passes a presence-only check.
   Evidence: install-hooks.sh:88-103; verify-enforcement.sh:151 onward.
   Scores 95/90/70/90/90; weighted 87.25, launch-blocking. Mitigation: closed
   vectors, exact bytes/modes/inventory and adversarial settings/native probes.
3. An interrupted publish leaves partially usable settings/native registration.
   Evidence: install-hooks.sh:135-153. Scores 90/85/70/90/90; weighted 85,
   launch-blocking. Mitigation: preflight/stage before writes, explicit completion
   boundary, prior-state preservation, crash recovery and failing probes before
   claiming registration complete. No claim that multiple renames are atomic.
4. Compatibility leaks Siege policy into an independent project.
   Evidence: protected-policy-range.py:434,459; .githooks/commit-msg:29-149.
   Scores 90/90/60/85/85; weighted 82.5, launch-blocking. Mitigation: separate
   explicit adapter descriptor, physical absence, content-only adoption corpus,
   shared evaluator and full legacy/local-decision parity.

## Paper tigers

Generated output collisions are guarded by GeneratedFiles.add at
compose-project.py:190-215, including equal bytes and Unicode normalization.
Re-run the accepted direct/composed hostile corpus; extend the same guard to
registration outputs. No independent policy resolver is needed.

## Elephants

Coherent component generations remain required after registration. Unless this
session implements and verifies those transitions, #1027 remains open for that
remaining dependency. #1003 live host/provider limitations remain unchanged.
Legacy compatibility paths must be counted, not renamed and called removed.

## Launch-blocking assessment

The input and ownership mitigations are designed; implementation may proceed
with registration claims blocked until all failure and parity probes pass.
Persisted-state design is provisionally 6/10 against the data-intensive shelf;
interruption and recovery evidence is required to establish its actual guarantee.

## Implementation assessment

The selected backend now rebuilds the full inventory before registration. Both
native and settings dispatch reject pending publication; original settings/config
are compared under locks and recoverable after process interruption. The explicit
compatibility path retains the entire existing exporter and three native bodies.
The candidate's grouping and unknown-event defects were falsified and corrected;
see the self-review/hostile record. No accepted-parent defect was identified.

Generation transitions remain out of this dependency. Publication still requires
fresh exact-head review; configured/local fixture results grant no live authority.
