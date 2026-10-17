# Siege reference inputs

This directory begins the Siege reference bundle extraction tracked in #1027.
`policy-inputs.json` names this repository's selected policy receipt, contract,
capability declarations and agreement fixtures. Existing callers explicitly use
this compatibility selection. The shared verifier also accepts a separately
pinned registration for another project, without reading this directory.

The expected registration digest comes from trusted caller configuration. For
the compatibility entrypoint it remains compiled into `bin/gate_contract.py`.
Changing this descriptor or supplying its new digest as candidate data cannot
replace that pin. The receipt then binds the exact policy Git revision/blob and
raw/canonical digests; the policy binds its contract. Each identity is retained.
The three existing operation kinds remain the bounded evaluator vocabulary.

These are declarations, not host observations. Loading a registration does not
adopt a workflow, select bundle content, install a hook or grant authorization.
A protected adapter must obtain its expected pin independently of candidate
content. No new CLI flag makes candidate-supplied pins authoritative.

`composition-inputs.json` declares the Siege compatibility content selection:
its legacy skill root, review aliases/prerequisite/route, and resident blocks.
The composer reads it only when the caller omits an explicit content selection.
Both selections use the same `ProcedureGraph`, renderer and package-link check.
The policy and content inputs are distinct: choosing a publisher does not adopt
its policy, establish a host capability or authorize an operation.

The [ontology](../../wiki/Ontology.md) calls the source namespace a
`content-publisher` and the configured composition data a `content-selection`.
A publisher is not a project scope. New publisher inputs normally use qualified
names (`publisher--skill`); the explicit `qualified: false` compatibility choice
retains the existing Siege names. Duplicate names fail rather than choosing a
publisher by directory order. Project-owned skills retain project scope and
cannot be borrowed through a publisher root.

For an independent composition, pass `--content-selection` relative to
`--source`, plus `--policy-root`, `--policy-inputs` and the independently held
`--policy-inputs-sha256`. These CLI inputs produce configured content only;
they are not a protected-host registration or a new way to approve policy.
Content selection has six fields: `schema_version`, `publishers`,
`policy_aliases`, `prerequisites`, `routes`, and `resident_blocks`. Publisher
entries name `id`, `skills_root` and explicit `qualified`; all other structures
reuse existing composition shapes. The only substitutions are the selected
policy's review procedure in routes, and its resident text/source in blocks.
Unknown policy substitutions reject. The block override modes and final budget
still apply after rendering; the Siege workflow/integrity blocks remain closed.

The source builder, runtime registration and coherent component transitions
still select Siege and remain #1027 work. Composition independence does not
establish that wider acceptance. This directory is not yet a complete bundle
format or an independently usable scaffold distribution.
