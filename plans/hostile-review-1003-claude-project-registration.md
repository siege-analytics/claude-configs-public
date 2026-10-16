# Hostile review: #1003 fixture-local Claude project registration

## Review target

Falsify the claim that the fixture repository receives exactly one byte-identical, canonical Claude project registration whose commands execute only pinned workspace-payload files, while setup and imported evidence remain non-authorizing and Pi remains unsupported.

## Attacks

1. Append `; command`, prepend `sh`, substitute a foreign absolute path, add arguments, add a hook, add a group, or alter a matcher/timeout. Expected: full inventory mismatch or exact-vector rejection.
2. Preserve command text but mutate the workspace executable. Expected: workspace/payload byte comparison rejects it.
3. Replace `.claude` with a symlink, existing file, or non-directory. Expected: preflight refusal before setup mutation.
4. Create the target after temporary-file completion. Expected: exclusive publication rejects it, preserves the raced file, and removes only the temporary file.
5. Rename `.claude`, replace it with an outside-directory symlink, and place a matching temporary filename outside before publication. Expected: held descriptor identity check rejects before linking; no outside `settings.json`, no success receipt and no descriptor-relative temporary residue.
6. Change source settings after validation but before publication. Expected: no destination and no temporary residue.
7. Supply startup/no-op metadata naming `$WORKSPACE_ROOT/.claude/settings.json`. Expected: evidence rejection requiring the fixture-local path.
8. Copy fixture registration metadata to Pi. Expected: evidence rejection; Pi remains `unsupported-unverified`.
9. Claim host invocation in the setup receipt. Expected: receipt rejection; setup must record `host_invocation_observed: false`.
10. Change fixture settings before cleanup or provide unequal registered/observed digests. Expected: operator/validator stops on digest conflict; SHA syntax or parent-directory absence cannot replace the comparison.
11. Re-run registration over an existing target. Expected: refusal, not merge or idempotent rewrite.

## Required replay

- Focused 14-test suite with `PYTHONDONTWRITEBYTECODE` absent.
- Isolated temporary-home end-to-end setup path.
- Proposal validation and negative approval check.
- Build, generated freshness, risk metrics, inventory, progressive loading and clean-tree checks.
- Review the exact diff and confirm no production deploy, general installer, `wire-enforcement.py`, lifecycle schema, application bridge, provider, release, or `main` behavior changed.

## Acceptance bar

Any reproducible inventory substitution, foreign executable, partial/overwritten target, workspace-only evidence acceptance, Claude-to-Pi transfer, self-authorization, or cleanup conflict erasure is a blocker regardless of green CI.
