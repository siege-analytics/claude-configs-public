# Hostile-review preparation: selected build (#1027)

Pinned baseline: c7d9d65e30dfd4450682a63b33fd0b53b979e2a0.
Role: author-side attack plan, not an independent acceptance verdict.
Independent review: pending with the existing reviewer after draft publication.

## Attack chain

Normal build -> selected component verification -> immutable source snapshot ->
existing composer/ProcedureGraph -> resident and installed resolver -> package
publication. Independent registration source/digest enters separately.

Try candidate-supplied policy replacement, duplicate component/publisher IDs,
changed blob/mode/digest, wrong scaffold tools, unknown backend, missing declared
capability, missing workflow adoption, alias/prerequisite cycles, missing or
foreign project source, existing output, and interrupted publication. Inspect
actual files/receipts and resolver output, not just function return values.

Separately inspect native and generation call chains. Their current fixed
Siege sources are unresolved acceptance work, not a reason to redefine a
composition receipt as registered enforcement. Keep #1003 non-live boundaries.

## Findings

Pending implementation and falsification. No acceptance verdict yet.

## Author falsification results

`python3 -B bin/_test/package_selection_test.py` passed 18 tests (43.062s).
The cases execute the copied normal builder and installed resolver. Failure
cases cover independent pin replacement, missing profile adoption, changed
committed bundle bytes, wrong scaffold bytes, ambiguous names, graph cycles,
symlink blobs, foreign project sources, malformed/duplicate JSON, unsupported
adapters/backends, existing destinations and interrupted publication.

The existing installer was invoked against selected output with disposable
operator settings and a real fixture Git repository. It rejected the missing
settings snippet before changing those settings or core.hooksPath. This is a
negative registration-boundary test, not completed selected registration.

The executable Siege case checks the complete composition file set and bytes,
plus the existing evaluator's policy decisions with three capability states.
It does not claim native allow/deny observations. The full legacy export
comparison retained 3379 files, with no added/removed files. Working-source
byte changes were only build timestamps and the added Tier C source-path
patterns. Final committed-head comparison remains required before publication.

## Scope verdict

The selection-to-composition boundary can be reviewed independently. The
registration/generation acceptance remains blocked by the retained fixed
native/protected policy sources identified in the pre-mortem. The author does
not issue independent ACCEPT. Exact-head independent review remains required
before merge; no additional worker was started.
