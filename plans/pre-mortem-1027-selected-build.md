# Pre-mortem: selected build input (#1027)

Base: c7d9d65e30dfd4450682a63b33fd0b53b979e2a0.
Goal: issue #1027, accepted boundary comments 6225067704 and 6225119253,
plus the operator's selected-build/registration instructions.

## Investigation and pre-author inventory

- `bin/build.py:1892` enters the normal builder; `:1916` validates Siege
  inputs unconditionally. `:1437` installs review-risk sources; `:1528`
  packages the hook directories; `:2040` builds fixed composition examples.
- `bin/compose-project.py:180` already consumes independent policy inputs
  and content selection. `:266` renders both layouts through ProcedureGraph
  and the existing token/link validators, before writing output.
- `bin/effective_policy.py:328` verifies independently supplied registration
  pins and immutable selected policy. This remains the policy authority seam.
- `bin/install-hooks.sh:88` accepts the fixed snippet prefix; `:114` requires
  the fixed native dependency closure. `.githooks/pre-push:18` requires the
  review-risk engine and `:49` invokes the command-oriented branch guard.
- `hooks/git/branch-guard.sh:120` uses a fixed protected-branch expression.
  `scripts/ci/protected-policy-range.py:434` loads the Siege wrapper, and
  `:458` treats promotion to main specially. Neither is a neutral adapter.
- `bin/package-generation.py:165` stages release-verified runtime plus a
  separately composed content tree; `:217` fixes the parent skill fixture.
  `:335` atomically selects a generation at a new epoch. Reuse these mechanisms;
  a new package descriptor is not authority to bypass release verification.
- #1028 and #1029 independently accepted policy and composition extraction.
  #1030 registers fixture-local Claude settings only, with no host invocation
  or authorization. Its accepted source cannot prove selected registration.

Knowledge loci: selected-package example README, normal builder CLI help,
composition contract, ontology bindings, this review record and issue #1027.

## Design and comprehension

Introduce a closed, versioned selected build input that binds scaffold,
selected content bundles and project inputs separately to immutable local Git
objects. Each component retains its own identity, revision and content digest,
even when revisions coincide. Snapshot only the selected closure; run the real
existing composer and resolver from that snapshot through the normal build CLI.
Validate workflow adoption against the independently registered policy, never
against a candidate-provided replacement pin. Content dependencies diagnose
missing profiles without adopting them. Publication is configured evidence.

Begin with this falsifiable build boundary. Then assess registration/generation
integration without substituting an alternate evaluator or weakening existing
release/native contracts. A build-only dependency must be labelled as such if
native authority extraction cannot be reviewed honestly in the same slice.

## Tigers

1. Candidate selects its own policy pin. Evidence: effective_policy.py:328 and
   build.py:1916. Scores (integrity, scope, reversibility, dependency, latency):
   100/90/70/90/90; weighted 88.5, launch-blocking. Mitigation: policy root,
   registration source and digest are separate required API arguments, absent
   from the candidate schema; delegate verification to load_registered_inputs.
2. Hidden source reads make absence cosmetic. Evidence: build.py:1437,1528.
   Scores 80/80/50/80/90; weighted 75, launch-blocking. Mitigation: construct
   an exact Git-source snapshot, execute copied normal builder/composer modules,
   and assert physical absence before execution, including all legacy inputs.
3. Mixed bytes or partial output pass as a selected set. Evidence:
   compose-project.py:371 writes multiple files after validation. Scores
   85/75/70/80/85; weighted 79, launch-blocking. Mitigation: verify component
   digests and matching scaffold tools, compose in a private staging directory,
   publish only the complete result, reject an existing destination.
4. Native independence is inferred from a build. Evidence: install-hooks.sh:114,
   protected-policy-range.py:434. Scores 100/85/80/90/95; weighted 90,
   launch-blocking for registration claims. Mitigation: keep publication
   non-authorizing, identify unsupported registration as such, retain the
   strict baseline, and require real native allow/deny tests before claiming
   that part complete. No parallel policy interpreter may fill this gap.

## Paper tigers

- Qualified identity, replacement and graph cycles already have one validator:
  procedure_composition.py ProcedureGraph and selected_composition_test.py.
  Exercise those gates through the selected normal build; do not duplicate them.
- A caller claiming verified capabilities cannot authorize an operation:
  effective_policy.py:507,588 always separates policy from final evidence.

## Elephants

Normal legacy export, native registration, protected policy, release generation
and host invocation are separate current paths. Calling all of them selected by
adding a descriptor would be false. Their migration remains required by #1027;
if this change stops at a dependency, record each unfulfilled acceptance item,
retain the old behavior and make no completion claim. Review the exact draft
before any integration. No additional worker, live session or shared install.

## Launch-blocking assessment

The mitigations above are designed from inspected call sites. Implementation
may proceed at the selected build boundary. Registration and generation claims
remain blocked until their real-path falsification matrix exists.
