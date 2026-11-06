## Context
Part-of #1156; local reader repair. Actual Craft block1654 at06:40:32 rejects the sed transform in a read pipeline: gh run view41975682106 --repo siege-analytics/siege_utilities --job127073848171 --log-failed | grep -E "FAILED " | sed -E 's/^.*Z FAILED //' | cut -c1-150 | sort | head -50. All other segments are proven readers. Existing sed_ok permits only sed -n Np [FILE]. Feature stacks on reviewed parent1185 d4feed and does not delay its publication.

## Goal
Recognize one bounded literal stdin-only sed substitution without general sed authority. Preserve existing line-print grammar.

## Acceptance criteria
- Original exact pipeline passes actual classifier and universal mutation gate without a task gate.
- Additional grammar accepts only optional leading safe -E/-r/-n options and one literal s-delimited expression; no file operands, late options, -e/-f/-i or multiple commands.
- Correctly parse escaped delimiters; reject e/w flags, newline/NUL, extra commands/separators, expansions, substitutions, redirects and composed writes through normal shell boundaries.
- Real BSD/GNU transform fixtures execute only installed actual binaries and report available coverage honestly.
- Preserve sibling reader denials; source/scanner peer review, focused tests and actual native Git evidence precede normal PR. No settings/install/protected merge.

## Assumptions
The GNU manual documents s execution e and write w flags; they must never become read authority. Supported ordinary method is a small recognizer, not a shell/sed parser. Root owns protected integration and deployment.

## Design and investigation
read-only-command.py234 sed_ok owns existing narrow -n numeric print grammar. Add a separate substitution recognizer after that exact branch, preserving old acceptance unchanged. Restrict delimiter to slash for the concrete case and escaped-slash coverage; parse two unescaped terminators with backslash state, then accept only empty/g/p/numeric flags as justified by real effects (or narrower empty/g/p). Reject all other suffixes. Whole command reader already handles shell syntax and every pipeline companion, so no substitution exception bypasses redirects or secondary mutation ownership.

## Pre-mortem
Launch-Blocking Tiger: sed e executes or w writes despite reader verdict. Mitigate whitelist flags after exact two-delimiter parse, reject multi-command/newline and real effects controls.
Launch-Blocking Tiger: escaped delimiter makes executable suffix appear inside replacement. Mitigate escaped-backslash parity and hostile escaped-delimiter cases.
Paper Tiger: missing GNU/BSD binaries claimed covered. Probe installed binaries only; distinguish actual observed variants.
Falsification: e/w/-i/-f/extra expression/files gain reader authority, old print shape changes, or any companion write is unscoped allowed.
