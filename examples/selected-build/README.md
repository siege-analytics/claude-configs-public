# Selected resolver-content builds

This executable dependency of #1027 binds scaffold, content bundles and project
sources independently, then invokes the normal `bin/build.py --selection` CLI
and existing composer. It produces both resolver layouts. It does not yet
produce selected settings/native registrations or coherent runtime generations.

Run the independent project and the explicit Siege composition example:

```sh
python3 -B examples/selected-build/run.py --case independent --output /tmp/selected-independent
python3 -B examples/selected-build/run.py --case siege --output /tmp/selected-siege
```

Use new output directories. Each contains the synthetic source repository,
`selection.json`, the built `package/`, `build-receipt.json`, and `rendered.txt`.
The Siege case also compares its output with the compatibility composer and
writes `parity.json`. All Git configuration and fixture commits are disposable.
The independent source contains only scaffold code/schema and project inputs;
legacy skills, bundles, hooks, examples and Craft inputs are physically absent.

The fixture's synthetic review URL and generated registration digest are test
setup, not approval evidence for an actual organization. In a real integration,
the reviewed host/repository registration must supply the policy root,
registration source and pin separately. Never obtain that pin from the candidate
selection, a bundle, the generated receipt or a newly written lock.

## Selected input contract

Schema version 1 supports local Git objects and the `resolver-only` backend.
The input contains:

- `scaffold`: identity, exact revision, ordered source paths and content digest;
- `bundles`: independently pinned components and their pinned bundle descriptors;
- `project`: identity and the selected project's directory at its own revision;
- `identity`, `workflow_profile`: canonical project and previously approved profile;
- `content_root`, `content`: explicit publisher, resident, route and graph inputs;
- `required_capabilities`: empty for this dependency. Any requested registration
  adapter rejects because none is implemented here.

Component digests cover canonical path, raw-byte SHA-256 and executable mode.
Components can share a revision while retaining distinct identities and digests.
A bundle owns exactly its descriptor and published skill root. Its descriptor
names the publisher and any required profiles; missing adoption diagnoses and
never adopts the profile. Profile adoption must equal the independently loaded
approved project policy. Selection is non-authorizing even when those match.

The build reads exact Git objects, checks the executing scaffold against the
selected scaffold, materializes only that closure, and uses the existing
composer/graph/renderers. Dirty unselected checkout content cannot change output.
`--check` performs the same validation/rendering without publishing a package.
The destination must be new. Cooperating publishers serialize in its parent;
rendering failures leave no usable destination. Publication is a directory rename
from a completed private staging directory. This is not generation activation.

Generated targets have one owner across rendered skills, copied assets, rules
and generated metadata. A second claim rejects even when the bytes match;
publisher order never selects a winner. Case/Unicode aliases and file/directory
conflicts also reject before either layout is written. Diagnostics name the
target and source-relative owners, without copying source contents or absolute
source roots. An existing destination is refused and preserved.

## Acceptance boundary and remaining work

| #1027 requirement | Evidence in this dependency | Still required |
| --- | --- | --- |
| Explicit versioned inputs and separate trust | Selected CLI/API; candidate fields closed; independent policy pin; profile checks | Selected host registration must consume the same input |
| Existing path and Siege compatibility | Normal build CLI delegates to existing composer; explicit Siege composition matches compatibility | Migrate full legacy export and repository governance onto selected build |
| Independent source closure | Executable copied normal builder/composer/resolver; no legacy source directories | Generated settings/native registration and real Git allow/deny decisions |
| Content versus profile | Content-only publisher leaves approved policy unchanged; required profiles fail closed | Full registered Siege-content-only decision corpus |
| Strict Siege preservation | Existing suites and composition parity | Selected full settings/hooks, managed inventory and registered decisions parity |
| Coherent component transitions | Separate source identities/digests; bundle-only content upgrade preserves project source | Existing generation receipts/locks, mixed/stale pair rejection and rollback at a fresh epoch |
| Examples, ontology, complexity | Runnable examples, actual content-bundle term and measurements below | Registration/generation examples after those mechanisms consume selections |
| Negative cases | Pin replacement, bytes/modes, scope, duplicate/ambiguous names, cycles, unsupported adapters/backends, interrupted publication | Partial activation and old-operation-receipt rejection for selected generations |

The remaining native migration is an authority boundary, not packaging glue:
`bin/install-hooks.sh` requires fixed review-risk/native dependencies;
`.githooks/pre-push` runs those fixed gates; the protected-range adapter calls
the Siege policy wrapper and has its own promotion rule. Copying that stack into
an independent project would silently impose Siege obligations. Implementing
another local evaluator to avoid it would violate the accepted single-engine
plan. This dependency therefore rejects registration requirements, retains the
strict legacy path and leaves #1027 open for the adapter/generation extraction.

## Complexity measurements

These are counts of defined source paths/algorithms, not a claim of completion.

| Measure | Before | This dependency |
| --- | ---: | ---: |
| Policy evaluators | 1 | 1 |
| Procedure graph/composer algorithms | 1 | 1 |
| Immutable Git snapshot implementations used by these paths | 1 | 1, shared with generation |
| Hardcoded legacy hook/policy sources retired | 0 | 0 |
| Full legacy build/export paths retained | 1 | 1 |
| New alternate rendering engines | 0 | 0 |
| Selected snapshot scaffold files | absent | 9 |
| Siege bundle/legacy directories in independent fixture | absent proof | 0 |
| Settings/native registrations emitted by selected build | absent | 0; unsupported |

`python3 -B bin/_test/package_selection_test.py` verifies the source closure,
component receipts and rendered inventory. The executable Siege example records
its exact file comparison. The existing full export is a retained compatibility
path; this dependency does not claim it has been unified or retired.

Selected registration is a separate explicit backend. See
[the selected registration fixture](../selected-registration/README.md) for its
independent inputs, installer and real local Git evidence. The default
`resolver-only` path described here remains composition-only.
