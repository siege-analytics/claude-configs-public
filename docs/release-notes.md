# Release notes discipline

Ref: claude-configs-public#610, claude-configs-public#625

## Rule

Every behavior-changing PR must update the top `[Unreleased]` section of `CHANGELOG.md` before merge.

Behavior-changing includes:

- always-on rule additions or edits
- hook additions or enforcement changes
- package layout or release workflow changes
- skill behavior changes that affect downstream sessions

## Why

The release workflow generates GitHub Release notes from `CHANGELOG.md`. If `[Unreleased]` is stale, the next release body is stale too. Writing accurate release notes is part of shipping the change, not a post-release cleanup task.

## Workflow

1. Add a short bullet under `[Unreleased]` in the same PR as the behavior change.
2. When backfilling after a release, move the consumed text into a concrete version section and create a fresh `[Unreleased]` section for the follow-up.
3. Run:

   ```bash
   python3 scripts/ci/release-notes.py --version <next-version> --check
   ```

4. Verify the generated notes mention the change being shipped, not an older release.
