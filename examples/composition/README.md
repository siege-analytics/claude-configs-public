# Project content composition pilot

This fixture demonstrates the #1001 ontology terms `skill-replacement`, `skill-extension`, `procedure-binding`, `resident-block` and `resident-composition`. It uses the two synthetic repository identities already selected by #848. All skill text is synthetic; private consumer content is not copied here.

`bin/compose-project.py` reads the accepted #848 policy snapshot, selects the exact project and binds the logical `review` procedure to that project's configured identifier. Explicit invocation, automatic routes, aliases, prerequisites, generated skill/rule links and the on-demand rules bundle then traverse one `ProcedureGraph`. Namespaced skills are independent unless an explicit replacement declares otherwise.

The strict project replaces `self-review` with `strict-release--review` and appends `strict-release--checks` to that project procedure. The trunk project retains `hostile-review`. Both derive from the same unchanged parent content digest. Ordered extensions and shared prerequisites load once; conflicts, missing references and cycles reject with the involved identifiers/sources.

The builder reuses existing skill discovery, flat/nested layout conventions and token rendering. It produces separate consumer directories, omits replaced procedure files and includes only the selected project's content. Existing qualified skill/rule tokens are rebound; supporting files retain relative links. A raw link that points to an omitted default or foreign content rejects with a diagnostic; migrate that link to the explicit skill token. General source and existing production packages remain unchanged by the composition.

Link validation covers inline Markdown destinations, reference definitions and raw HTML `href`/`src` attributes, with package-relative paths normalized after entity/URL decoding. External links allow only `http`/`https` with a host and `mailto` with a recipient; local-resource schemes such as `file` reject. Same-document anchors remain allowed. This is conservative validation, not a Markdown renderer: local link examples in code must also name packaged content. Both layouts validate before either output is written.

## Build and inspect

The normal build emits `dist/composition-examples/{strict-release,synthetic-trunk}/{flat,nested}`. These are configured test artifacts, not installation or host-enforcement evidence. A standalone build requires a new destination outside the source tree:

```bash
python3 bin/compose-project.py \
  --identity github.example.invalid/synthetic-org/strict-release \
  --output /tmp/strict-composition-review

python3 /tmp/strict-composition-review/flat/bin/resolve-load-set.py \
  --repo github.example.invalid/synthetic-org/strict-release \
  --prompt '[skill:code-review]'
```

Inspect `composition.json` for source paths, binding traces, selected policy revision/digests, original resident blocks and final rendered size. Open `skills/RESIDENT.md`, `skills/RULES_BUNDLE.md` and the selected procedure paths. The nested fixture places the caller under `skills/coding/code-review`; the flat fixture uses `skills/code-review`, exercising different relative link depths.

A composed package rejects use with another repository identity. That identity is still a caller observation, not authenticated host evidence. The resolver output and package receipt carry `authorization_effect: none`; policy remains final `unknown` for a policy-allowed procedure. The #848 permission and required-evidence fields are copied into the receipt unchanged.

## Compatibility and resident budgets

Each project keeps its existing heading-based `CLAUDE.md`. `heading_map` explicitly maps each level-two heading to a stable block ID and `add`, `extend` or `replace` mode. No rewrite of every skill is needed. Unknown/repeated/case-ambiguous headings, unclosed fences and unmapped preambles reject. Parent blocks declare allowed modes; integrity and approved workflow blocks allow no prose override. New blocks must use the project's qualified ID.

The final resident includes shared integrity text, workflow text from the selected policy and the imported project overlay. Character and estimated-token limits apply again after token expansion. The estimate is characters divided by four, rounded up; it is not a host tokenizer measurement.

This bounded pilot does not migrate the production kernel, replace an enforcement adapter, implement every historical Markdown dialect, or install anything. #1002 owns protected operation evidence; #1003 owns live host delivery; #1004 owns activation and rollback. Procedure text can describe a requested action but cannot grant its permission.
