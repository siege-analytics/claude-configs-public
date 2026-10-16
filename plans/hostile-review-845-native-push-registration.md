# Hostile review: #845 native push registration and range semantics

## Attack surface

- generated and installed `.githooks/pre-push` bytes;
- `core.hooksPath` target selection;
- pre-push stdin, exact pushed range, new branches, and interior commits;
- missing/no-op runtime dependencies;
- direct invocation presented as registration evidence;
- local bypass presented as protected acceptance.

## Findings replayed

Local adversarial corpus exercises missing/non-executable runtime files, no-op wrapper/range implementation, foreign registration, missing policy/helper, invalid interior followed by valid head, force/multi-ref updates, other-remotes/fabricated tracking, unknown destination objects and malformed protocol. Rejected actual pushes must leave all destination refs unchanged; repaired pushes must advance the intended ref.

Falsified assumptions during implementation:

- Bash 3 with `set -u` rejects a simple empty-array expansion. The range argv now always starts with the local commit and safely appends optional exclusions; the existing 12-case review-policy suite passes.
- A packaged artifact is not an installed root workspace. Verifier tests explicitly materialize only the documented compact-kernel/resolver/compatibility root mounts before assessing native behavior.
- JSON and shell paths must be independently quoted. Installer JSON uses Python serialization and shell commands use `shlex.quote`; verifier paths are argv, including spaces, apostrophes and ampersands.

Independent exact-head hostile review remains pending.

## Remaining deliberate boundaries

Native Git hooks remain bypassable with `--no-verify` and are local feedback only. They cannot replace the #1002 provider-bound exact-range check, required branch protection, #1003 live host evidence, or #1004 activation/rollback evidence.
