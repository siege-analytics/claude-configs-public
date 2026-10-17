# Pre-mortem: coherent selected generations (#1027)

Accepted immutable parent: 9a884ec172f7c5cddbbc0edc5626807f18fb5f66.
Workspace: /private/tmp/cc-1027-coherent-selected-generations.
Branch: feat/1027-coherent-selected-generations.
This supersedes the stopped plan at rejected 5fc9250, not its falsification.
The accepted df1afab native correction and all earlier evidence remain history.

## Investigation and pre-author inventory

Read /Users/dheerajchand/AGENTS.md; #1027 and every comment, including accepted
boundaries 6225067704/6225119253; #1031 rejected/accepted history and #1032 body,
evidence and reviews. Cached API snapshots: cache/coherent-generations/history.
Read generation, selection and registration source/tests/docs, pre-mortem,
self-review, hostile-review, commit and the nested data-intensive shelf.
No additional worker: the issue retains the existing coordinator/reviewer.

Current behavior and call chain:

- bin/package-generation.py:134 stage builds release/runtime plus composition;
  :300 select holds a store lock and replaces current.json once; :332 resolve
  returns a fixed payload and epoch. It has no selected registration inventory.
- bin/package_selection.py:82 selected_inputs verifies separate source components
  and approved policy. :191 build runs the existing composer, then registration.
- bin/selected_registration.py:47 load_definition seals the selection digest and
  external policy pin. :249 verify_package rebuilds complete bytes. :398 publish
  journals settings/Git config independently of generation selection.
- bin/native_git.py:62 parse_arguments separates native data from settings controls.
  :97 main verifies binding before dispatch. Its accepted argv/no-op behavior stays.
- Existing generation tests retain release verification, provider boundaries,
  damaged-active rollback, epoch checks and customization. Selected build tests
  retain canonical-caseless generated ownership and separate source inventories.

## Design and pre-implementation comprehension

Extend existing generation staging/select/resolve and selected registration;
no new evaluator, composer, installer or activation state machine. A selected
stage uses the normal builder and registration verifier. Its manifest/lock retain
canonical source inventories and distinct scaffold, content bundle, workflow/policy,
project and registration identities even at a shared revision. Independent policy
and registration pins enter through explicit caller arguments; candidate receipts
cannot establish them. Store copied selection/provenance as derived evidence.

The sole commit point stays current.json. Stage and verify the complete package
before activation; never write active settings/native files one at a time during
an upgrade. Extend existing registration to bind a generation store. Each selected
consumer obtains one complete token under a shared store lock, checks the complete
inventory and dispatches the selected runtime. Activation takes the same lock
exclusively, rechecks independent pins, corpus, prior epoch and inventory, then
replaces the token once. Settings event/group shapes must remain compatible with
the registered consumer; incompatible shapes fail before activation. Registration
bootstrap retains the existing journal/recovery path.

Rollback names the exact previous complete set, revalidates its external pins,
restores its bytes/identities, and emits new generation-selection and activation
receipts at a new epoch. No operation/provider receipt is copied or made current.
Project replacement skills/resident content remain independently pinned. Cleanup
only removes unselected staging candidates and cannot traverse into generations.

Sequence: this issue record and Tier C artifacts; hostile red tests; extend the
existing APIs; real baseline/single-component transitions and rollback; independent
and explicit Siege examples; exact byte/decision and complexity measurements;
implemented ontology/risk/doc updates; normal-hook additive commits; full final
exact-head matrix; normal push and draft PR to develop. Never merge/close #1027.

## Adversarial comprehension check

A pointer alone does not make readers coherent: a settings process can hold an old
binding while a native process reads a new one. The consumer must resolve once,
verify the epoch, and retain the lock while using that package. Old receipts must
fail even after rollback restores identical content. A mutable external selection
filename must not invalidate retained rollback input: copy canonical selection
bytes but continue to require independently supplied policy/registration pins.

The plan must not confuse registration bootstrap recovery with generation atomicity,
source inventories with generated inventories, policy allowance with authorization,
or same-revision components with one identity. All must be falsified at public
boundaries, including real Git ref outcomes and preserved operator settings.

## Tigers

| Risk and source | Scores integrity/scope/reversibility/dependency/latency | Mitigation designed before implementation |
| --- | --- | --- |
| Candidate supplies its own trust pins; selected_inputs:82/load_definition:47 | 100/90/70/90/90; 88.5, launch-blocking | Independent activation inputs; rebuild/compare before token publication |
| Mixed settings/native/runtime during switch; publish:398/main:97 | 95/90/70/90/90; 87.25, launch-blocking | Single existing current.json commit point; shared reader/exclusive writer lock; complete inventory verification |
| Rollback revives evidence; select:300 | 100/80/80/90/90; 88, launch-blocking | New epoch and fresh selection/activation receipts; reject old tokens and operation/provider evidence |
| Cleanup or symlink removes retained bytes; stage:134 | 95/80/90/80/80; 85.75, launch-blocking | Confined staging directories, no generation GC, no symlink traversal; lock/race/interruption probes |

Mitigations are grounded in the existing lock, atomic_json, immutable Git reader,
GeneratedFiles ownership guard and independently pinned registration verifier.
Implementation may proceed to executable falsification; none is a passing claim.

## Paper tigers

Generated ownership already fails closed in GeneratedFiles.add (compose-project.py:
190). Native payload options are fixed at df1afab (native_git.py:62); keep the full
real-alias/no-op corpus. The existing evaluator retains unknown final authorization.

## Elephants

The full Siege exporter, legacy native bodies and compatibility wrappers remain
explicit measured debt. No directory rename is removal. Generic generation use
must physically omit their source closure. #1003 live host/provider capability,
#847 Git-free source provenance and #849 broader retirement remain separate.
Power-loss filesystem guarantees and malicious operators replacing trusted code
are outside the accepted local artifact/registration contract.

DDIA design score: provisional 7/10. Git/independent adoption are sources of truth;
packages/receipts are derived. Single commit-point and reader lifetime are explicit;
process-death/race/rollback proof is required before final assessment.

## Candidate-head rejection and correction plan

Head fa94d48ebeadefa003f6833055f2e534d291d69f is rejected for acceptance despite
its passing working matrix. A new adversarial fixture preserves the independent
registration pin, commits an unapproved marker-writing scaffold, and rehashes the
candidate source/declaration/manifest. Activation returns an error, but the marker
exists: candidate code executed before the selection seal was checked.

The retained builder must never establish its own approval to run. Before any
subprocess, compare the candidate declaration digest with the independently pinned
registration's selection digest. Also compare top-level project identity and derived
composition-tool hashes with the already verified source inventory. Keep the normal
builder's full validation and the old-scaffold rollback behavior. Add a regression
asserting no marker write and no active-state change, then rerun normal registration,
strict scaffold rollback, the complete generation suite and the final exact-head
matrix. Use an additive correction commit; do not amend or erase fa94d48 evidence.
This is a candidate defect, not a new defect in accepted parent 9a884ec.

RED log SHA-256: ed78c7e879a5f1e5feb19cebbbf26aeeea28e81b85e55d9ad283181a4d4fdd88.
