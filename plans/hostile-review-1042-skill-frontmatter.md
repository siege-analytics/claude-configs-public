# Hostile review: #1042 Craft skill frontmatter

Review an immutable exact head. A changed head invalidates the verdict.

## Falsification targets

- missing opening delimiter, closing delimiter, `name`, or `description`;
- empty, quoted-empty, folded-empty, or whitespace-only required values;
- direct general, router, shelf-router, reference-shelf, and project skill paths;
- rule files incorrectly subjected to skill metadata requirements;
- archived/ignored project sources accidentally becoming blockers;
- source metadata present but missing or transformed in flat/nested output;
- duplicate or aliased consumer destinations;
- a filesystem-only pass without Craft native validation;
- flattening nested shelf books into ambient commands;
- installation overwriting unrelated local project skill work.

## Required verdict evidence

Reproduce the v3.5.65 failure, run focused negative fixtures, inspect both generated layouts, validate the replacement skill through Craft's native validator in an isolated consumer when possible, and post exact-head ACCEPT or REJECT on the PR.
