# Literal command lookup and buildx version reads (#1222)

## Context and design before implementation

The native reviewer errors were compound read-intent calls, not a bake-print
attempt. On the unchanged parser, `command -v docker` becomes unsupported Git
mutation options; `docker buildx version` becomes an unproven cwd mutation.
`git log --oneline -5` is already proven read-only. Broader environment and
compound syntax remains independently unproven; this change does not exempt it.

Use the existing read-only classifier, not a new runner or alias engine.
Recognize literal `command -v/-V NAME...` only with nonempty non-option names;
make `command` expansion-guarded so dynamic names and command substitutions
cannot acquire read proof. Recognize exactly Docker argv `buildx version` with
no additional options. Preserve each compound member's proof and all existing
mutation/redirect/opaque execution controls. Unknown spellings remain unproven.
No new permission, task gate, Docker mutation or provider operation is granted.

## Risks and validation

A loose command wrapper could execute a child; require the exact lookup option.
A loose Docker prefix could admit build/create/rm; require the exact two words.
A lookup followed by a mutation must not donate read authority. Add actual
read-classifier and universal-hook positive/negative controls in the existing
reader fixture; run them red on baseline, then focused and existing reader
suite. Test commands are classified, not executed except disposable denied-effect
controls already provided by the fixture. Do not call Docker, print environment
values, or change a live session. Stage authored inputs before canonical refresh.
Root/independent source review is required before any commit or push.

## Initial validation and review

Both new actual universal-hook methods failed on the unchanged parser, as
expected: literal lookup hit unsupported Git options and buildx version was
unscoped. With the narrow classifier change, both passed, including unknown
options, executor forms, dynamic names/substitutions and compound next-write
negatives. The full existing reader safety fixture then passed 18 tests. These
classify candidate commands; they do not run Docker or claim a live provider
turn. Independent source review accepted the frozen runtime and fixture pins;
remaining allowlist/freshness checks and Root review remain separate evidence.
