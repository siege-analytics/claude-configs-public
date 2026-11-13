# Explicit body-free REST GET reader

Task: siege-analytics/claude-configs-public#1349

## Assumptions

The coordinator's recorded refusal was before execution. Offline fixture admission reproduced the explicit-method failure for the bare request, independent of redirection. No live request was replayed.

Consulted the GH CLI API manual (https://cli.github.com/manual/gh_api), its api.go option declarations, and pflag's documented shorthand syntax (https://github.com/spf13/pflag#command-line-flag-syntax). GET is the default without fields; the method flag overrides it. This patch proves only body-free REST GET, consuming option values and short clusters. Fields/input remain outside this proof, even with GET. Task actions reuse that shared classifier instead of maintaining a second method ban.

## Test plan

Before the source change, the new focused fixture failed seven subcases: six explicit GET forms and owned output. The first test invocation had a Python quoting error, corrected before this red result. An initial inherited-suite invocation was interrupted after the test loader was narrowed to the new methods; that invocation is not counted as a complete test result.

The candidate passes the new preexecution controls for default/explicit GET, owned output and jq, foreign output, write compounds, body/input flags, malformed/dynamic methods, GraphQL endpoints and REST resources named graphql. The hook fixtures perform admission only; no request or redirected output runs. Existing reader controls passed 356/356, and GraphQLReview passed 11 tests.

Root reviewed the source and identified a false refusal for REST resource names ending in graphql. Replaced that suffix heuristic with standard URL path parsing of GraphQL API roots and added positive REST-name and negative GraphQL/malformed-URL controls. The endpoint regression is fixed and covered by positive REST-name and negative GraphQL/malformed-URL controls.

No runtime installation, remote metadata mutation, or permission policy change is included. This change does not authorize REST writes or grant output paths beyond the Task's scope. Unknown options remain unproven.

## Findings

The first candidate rejected legitimate REST resources named graphql. URL path parsing now distinguishes those from GraphQL API roots; regression controls pass. No remaining source blocker was found.

The complete staged scanner exited 1 with 35 findings (raw SHA256 ce231ecc7fb8177c4d059196a7c0c68c30f441c0092d74a98c621cafd745b957). The 32 task_actions handler bindings and one existing GraphQL binding match their base function AST. The new URL ValueError returns False and is exercised by the malformed-URL negative. Aggregate test discovery misses the hooks/_test tests; inherited coverage debt remains issue #1329. This is accepted disposition of non-clean output, not a clean scanner result.

## Independent review

External Codex Root inspected the final parser, shared reader delegate and source tests, verified all 35 raw rows and 33 inherited function/handler bindings, and independently ran the four focused methods (PASS, 10.044s). Root accepted the source and scanner dispositions at 2026-11-13T05:01:40Z. The durable independent record is `instruction-refactor-evidence-20261104/core1349-explicit-get-20261113/root-independent-review.json`; full per-finding author analysis and raw scan are alongside it. Review covers admission-only fixtures and source, not runtime installation or live API results.

Final author validation: four focused tests PASS (8.156s), actual four-source unbound test-evidence producer PASS (8.024s), reference sync/build/inventory/source-authority checks PASS, generated build PASS, language/data scope checks PASS. No tracked generated changes resulted.

The next review found that strict parsing had also refused `gh api --help`, `-h`, and endpoint-plus-help. Added option-consuming help handling and a fifth focused test: help is documentation, while a help-looking header/jq/template/method value cannot mask POST. Actual author five-method run passed (9.707s); Root read the small source delta and independently ran all five methods (PASS, 12.831s). The actual four-source test producer passed again. No handler family or body/write authority changed.

A post-commit freshness check found that the new test files needed registration in the skill inventory once Git tracked them. Refreshed the six entries with the normal inventory generator; no manual catalog editing or build-policy weakening. The earlier pretracking checks are retained as historical results, not final freshness proof.
