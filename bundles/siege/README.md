# Siege policy inputs

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

The current build and composition entrypoints still select Siege. Independent
package construction, selected registrations, bundle-qualified procedures and
coherent component transitions remain #1027 work. This directory is not yet a
complete bundle format or an independently usable scaffold distribution.
