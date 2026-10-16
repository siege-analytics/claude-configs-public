# Coherent package generations

`bin/package-generation.py` stages a disposable package set and selects one
complete generation. It reuses the release handoff (#852), selected effective
policy (#848) and project composition (#1001). It does not register hooks, edit
an existing Craft workspace, reload cached instructions or grant tool permission.
The currently registered host stack remains authoritative during observation.

This is the artifact transition layer for #1004. Protected Git acceptance uses
#1002's separate adapter, and actual host delivery/registration remains #1003.
A successful `select` means coherent artifact selection, not live enforcement.

## Inputs and ownership

Supply an exact parent source commit, the four release archives and the canonical
SHA-256 of the independently selected `release-manifest.json`. The manifest and
archives must pass the existing release verifier against available exact Git
objects. No moving release branch is used. The parent checkout must be clean at
that source revision, and the executing composition/resolver dependencies must
match it. A newer incompatible tool requires its matching reviewed implementation.

Supply an exact consumer commit with a customization declaration such as:

```json
{
  "schema_version": 1,
  "identity": "github.example.invalid/synthetic-org/strict-release",
  "project_source": "project",
  "preserve": ["operator/local-skills"],
  "settings": "settings.json",
  "legacy_hooks": []
}
```

`project/` contains the existing `composition.json`, `CLAUDE.md` and project skills
accepted by the composer. Parent skills come from the exact source's
`examples/composition/skills` by default; `--composition-source` selects another
explicit source subtree following the same convention. Working files and ambient
untracked content never enter the package.

Declared `operator/` files retain nested paths and executable bits. Unrelated
settings are preserved as JSON in `operator-settings.json`; they are not merged
into or installed as active host registration. Project skill replacements and
resident overlays use the existing composition contract. Preserved files cannot
shadow the managed runtime or content namespaces.

A copied legacy hook must live under `compatibility/`. Its declaration names
`path`, `sha256`, `origin_revision`, `origin_path` and `contract_sha256`. The bytes
and executable mode must equal that exact parent Git object, and the declared
contract must match the generation's selected contract. These files are explicit
compatibility inputs, not automatically enabled hooks. An unsupported copy fails
staging rather than being overwritten or silently treated as an approved override.

## Stage, inspect and observe

Stage into a fresh, dedicated store outside active workspaces:

```sh
python3 bin/package-generation.py --store /absolute/disposable-store stage \
  --parent-root /absolute/exact-parent-checkout \
  --assets /absolute/release-assets \
  --release-digest CANONICAL_MANIFEST_SHA256 \
  --repository siege-analytics/claude-configs-public \
  --tag vX.Y.Z --source EXACT_PARENT_COMMIT \
  --consumer-root /absolute/consumer-repository \
  --consumer-revision EXACT_CONSUMER_COMMIT \
  --identity github.example.invalid/synthetic-org/strict-release
```

The output names a generation ID. Its manifest records the exact source,
consumer, artifact, selected policy, contract and composition-tool identities,
file hashes/modes and ownership. The transition fixtures check the scoped
`catalog/package-generation-bindings.json` against the shared ontology. `runtime/` is the verified consumer distribution;
`content/` is the selected project's composed package; `operator/` and
`compatibility/` hold the declared preserved inputs. Provenance is kept alongside
them. No selection changes during staging.

Use `verify --generation ID` to check the complete file set and manifest digest.
Missing, extra, changed, mode-mismatched and symlink files reject. Content-addressed
generation names detect alterations; this is not a signed attestation or a defense
against an operator who can replace both trusted code and selection state.

For initial artifact selection, use `select --generation ID --expected-epoch 0`.
For upgrades, `observe --generation NEXT_ID --operations corpus.json` compares the
same bounded operations through the existing policy resolver for the old and new
generations. The corpus is a JSON array of `feature-merge`, `ticket-commit` and
`review-procedure` operations. It records differences, both decisions and the
current epoch. Capabilities remain unverified; a configured observation cannot
turn a policy result into final host authorization.

Review all differences and pass the resulting exact observation digest to
`select --generation NEXT_ID --expected-epoch N --operations corpus.json
--accepted-observation DIGEST`. A stale epoch, changed corpus, different candidate
or mismatched observation rejects. Selection uses a store lock and one atomic
record replacement. An interrupted staging or pre-selection failure leaves the
prior selected generation intact.

## Readers, rollback and state

`resolve` returns one absolute payload path, generation ID, identity and epoch.
A caller must resolve once, use that fixed directory for every settings/content/
runtime read in the operation, and bind operation evidence to both generation
and epoch. Re-reading current separately for each file defeats coherence.
A reader already holding the old generation can finish with that complete set.

Rollback names the exact `previous` generation and uses the same observation and
selection checks:

```sh
python3 bin/package-generation.py --store /absolute/disposable-store rollback \
  --generation PREVIOUS_ID --expected-epoch N \
  --operations corpus.json --accepted-observation DIGEST
```

Rollback verifies the retained files again and increments the epoch. It never
restores an old operation receipt as current. Supported manifest and state schema
versions are explicit; incompatible versions fail. Task approval state is not
copied into generations. No automatic garbage collection removes rollback inputs.

This API guarantees a single artifact selection boundary for cooperating readers.
It does not claim power-loss recovery for every filesystem, automatic host context
reload, a second blocking stack, or a migration of the existing production installer.
Those claims require the separate host and protected-operation acceptance evidence.
