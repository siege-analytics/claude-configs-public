# Adversarial implementation review: ontology (#1007)

This records local adversarial review and executable negatives. It is not an
independent reviewer verdict. Independent exact-head review is requested through
#1007 and the implementation PR.

## Boundaries examined

- Registry parsing rejects duplicate JSON keys, duplicate IDs/labels, alias
  collisions, invalid versions, unknown fields and dangling relationships.
- Machine references reject ambiguous, deprecated and unknown terms. Human
  display labels do not silently become machine IDs.
- Artifact bindings inspect real JSON fields and types, including every branch
  of a wildcard. An empty or incomplete collection cannot create a false pass.
- File access remains inside the selected repository. A local symlink at the
  generated page cannot redirect generation over unrelated content.
- Check mode does not rewrite a stale page. Repeated generation is deterministic.
- Prose lint preserves the advisory boundary. Canonical qualified phrases are
  masked before ambiguity warnings, and warnings do not deny tool use.
- The existing runtime manifest schema, policy resolver, gate scripts and host
  adapters are unchanged. Relationships are documentation, not an authority engine.

## Finding addressed during review

The first local implementation confined resolved paths to the repository but
would still follow a symlink to an unrelated file inside it during `--write`.
It now rejects symlink components. The CLI canary points the wiki output at a
separate work file, expects rejection and verifies that file remains unchanged.

## Limits

A type-correct semantic annotation can still be conceptually wrong. The checker
does not infer meaning from prose or execute a runtime canary. Reviewers must
assess definitions and mappings; #851/#848 and #1002/#1003 own operational contract
and behavioral acceptance. Only registered artifacts are covered. The separate
GitHub Wiki mirror is not claimed as published.
