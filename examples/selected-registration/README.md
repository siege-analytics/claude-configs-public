# Explicit selected local registration

This extends #1031's composition-only dependency for one explicit backend,
`claude-code-local`. `resolver-only` still emits composition-only, non-authorizing
output with no usable registration. A successful selected build with the new
backend emits an **unregistered** inventory; the installer must rebuild and verify
it before binding settings and native hooks to a particular local Git repository.

Run synthetic examples from a checkout; all effects stay under the supplied new
output directory:

```sh
python3 -B examples/selected-registration/run.py --case independent --output cache/registration-independent
python3 -B examples/selected-registration/run.py --case siege --output cache/registration-siege
```

Both use the existing `bin/build.py --selection`, `bin/install-hooks.sh --selected`,
`bin/wire-enforcement.py --selected`, and `bin/verify-enforcement.sh --selected`
entrypoints. Each registration call requires `--source`, `--selection`,
`--policy-root`, `--policy-inputs`, `--policy-inputs-sha256`,
`--registration-inputs`, `--registration-inputs-sha256`, `--identity`, `--backend`,
`--hooks-root`, `--workspace`, and `--git-repo`. `--target-file` optionally names
settings inside that workspace. Wire and verify check an existing registration;
only install publishes one. No shared or default location is selected.

The externally pinned registration definition seals the selection digest, adopted
workflow profile, policy source/pin, adapter and protected target names. Selecting
content cannot supply any of those trust anchors or adopt a workflow profile.
Required capabilities are exactly `native-git` and `settings`; unknown backends,
adapters or capabilities fail before usable output. Complete immutable component
inventories and every generated path still pass the accepted canonical-caseless
ownership guard, including equal-byte collisions and parent/file conflicts.

Installation rebuilds from independently supplied sources and compares every
package path, executable flag and byte. It then binds that verified inventory
hash, exact interpreter, repository and independent inputs in local Git config.
Settings commands carry the same binding. Runtime checks compare against this
externally registered hash and independent policy pins; no generated receipt
provides its own expected digest. Public wire/verify always repeat the rebuild.
Unrelated settings, permissions, models and hooks are retained. A changed managed
command, interpreter, event, duplicate or unknown suffix is a conflict. Existing
native registrations or executable hooks are not displaced.

Publication stages settings and Git config, takes the selected-registration lock
and Git's config lock, and records the prior bytes before replacement. A pending
journal makes all newly registered settings/native entrypoints unusable. Ordinary
errors restore published bytes; process interruption retains recovery information.
`bin/install-hooks.sh --selected ... --recover` restores those prior bytes after
checking that no intervening operator edit or foreign Git lock would be overwritten.
This is recoverable two-file publication, not an atomic filesystem transaction or
a power-loss durability guarantee. The tests kill the installer after each
replacement and exercise refusal, recovery and a subsequent successful install.

The independent source physically lacks `bundles/siege`, legacy skills, hooks,
examples and defaults. Its settings invoke the existing selected resolver; its
native adapter asks `effective_policy.py`/the gate contract for ticket and explicit
protected-target decisions. Review procedure selection remains non-authorizing;
there is no implicit Siege review-trailer, ticket or branch contract. The separate
content-only probe selects a synthetic Siege skill without adopting its profile
and repeats real no-ticket/no-review commit and trunk/develop push operations.

The explicit Siege descriptor selects the retained compatibility exporter and its
complete pinned source closure. That adapter supports only the adopted
`strict-release` workflow; a different approved profile rejects before export. It uses the same selected API, installer, verifier
and outer native dispatcher. Settings add a checked dispatch wrapper around the
unchanged complete legacy payload vectors so pending publication cannot execute
them. The fixture verifies the full wrapper vectors, group metadata, full payload
vectors, all exported bytes/modes/managed paths, native inventory, seven complete
effective-policy explanations and actual allow/deny Git decisions against the
existing compatibility installer and exporter. It rejects an invalid commit and
an invalid interior commit in a pushed range; denied pushes leave destination refs
unchanged. A deterministic explicit `--source-date-epoch` makes the exporter
comparison cover generated timestamps as well as executable bytes.

The protected-range adapter takes explicit `--policy-root`, `--policy-inputs`,
`--policy-inputs-sha256` and its existing exact canonical identity arguments. It
uses the same evaluator and has no implicit promotion edge. The old invocation is
a named compatibility wrapper with a separately code-pinned Siege descriptor.
`--installed-pilot-receipt` remains the legacy #1003 consumer receipt contract;
it cannot substitute for selected registration verification. Provider/host
acceptance is outside this local registration API.

All registration receipts say configured/none. Evidence records actual disposable
local Git effects separately from unobserved live Claude/provider authority.
Local hooks remain operator-bypassable. These fixtures do not authorize a live
host, provider protection, release, deployment or organizational policy adoption.

## Measured complexity

- One direct protected-adapter `ep.load_inputs` call was replaced by explicit
  registration loading; its legacy invocation remains one named compatibility
  wrapper. One hardcoded promotion edge moved into the pinned Siege descriptor.
- Three existing native call sites gained explicit selected dispatch. Their three
  legacy bodies remain. The two generated native wrappers share one generic
  dispatcher; there is no second policy evaluator.
- Three existing public install/wire/verify entrypoints gained selected dispatch.
  One selected registration implementation owns rebuild, merge and publication.
- One existing full exporter remains behind one explicit Siege compatibility
  export function with one strict-release profile restriction. No legacy exporter or native policy body is claimed removed.
- Two Git range translators remain: the generic native protocol translator and
  the legacy self-review range script. They retain their different feedback
  contracts; only the existing effective-policy evaluator decides selected policy.
- The independent fixture injects one project review skill and zero Siege content
  files. The content-only probe adds exactly one qualified synthetic Siege skill.
- The Siege compatibility inventory in the precommit probe contains 831 managed
  files, 105 executable files and two native hooks. Exact-head fixture evidence
  records the current full count and inventory digest. Its settings contain 36
  commands across three events; wrappers are deliberate additional commands, not
  a claim of byte-identical outer registration.

Coherent generation identities and transitions across scaffold, bundle and project
sources remain the next #1027 dependency: upgrade, mixed/stale generation,
customization and generation rollback tests are not implemented here. Existing
component pins and interruption recovery are not a claim that generation
activation is complete. #1027 stays open.

### Native argument boundary

Generated hooks call `native_git.py commit-msg -- MESSAGE_FILE` or
`native_git.py pre-push -- REMOTE LOCATION`. The first separator belongs to the
dispatcher; everything after it is Git data, including another `--`, empty strings,
spaces and Unicode. Native events accept no control options and read their binding
only from the repository's local `scaffold.registration` configuration. Exact
argument counts, repository identity, pending journal and runtime verification
precede operation execution for both adapters. Direct native callers must supply
the separator too. Retained shell aliases consume their explicit `--selected`
sentinel and insert the separator before forwarding the remaining arguments.

Settings retain `prompt --binding JSON` and `settings --binding JSON --command
JSON`; bindings and command vectors must occur exactly once, with no abbreviated
options, extra arguments or event-local help. Only standalone `native_git.py
--help` / `-h` prints usage successfully. Git-owned help-like names never reach
that path. An empty filename is preserved and fails as an unusable file; it does
not become a missing control option.

Both executable examples exercise actual pushes through ordinary, option-like
and Unicode aliases pointing to one bare remote, recording allowed heads and
unchanged refs on denial in `consumer-native-arguments.json`. Siege also compares
the retained compatibility installation. Its denied release push contains invalid
unpublished history; the independent adapter denies the release target itself.
These preserve the two adapters' existing policy decisions.
