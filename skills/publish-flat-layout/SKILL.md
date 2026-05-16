---
name: publish-flat-layout
description: "How to generate the flat layout for Craft Agent and similar consumers, and verify the structural changes in skills/ + hooks/ mirror correctly to the published artifact. The repo ships two layouts (nested + flat); this skill scopes to the flat layout's source-to-consumer chain and the verification discipline that prevents structural drift."
disable-model-invocation: true
allowed-tools: Read Grep Glob Bash
---

# Publish flat layout

This skill captures the procedure for generating the `dist/flat/` artifact, verifying that structural changes in `skills/` and `hooks/` actually reach the published flat tag, and confirming a consumer can sync the result. The repository builds two layouts via `bin/build.py`; this skill scopes specifically to the flat layout because that is the surface Craft Agent and similar consumers read directly without the resolver hook's nested-path traversal.

For the broader consumer-side verification discipline, see `[`writing-releases`](../_writing-releases-rules.md)` writing-releases:5. This skill is the operational implementation of that rule for this repo's flat-layout consumer surface.

## When to invoke

Run this skill when any of the following happens in a feature branch you intend to merge:

- A new file is added at `skills/` root (e.g., a new `_*-rules.md` or root-level support file).
- A new skill directory is added at `skills/<slug>/` or `skills/<group>/<slug>/`.
- A skill directory is moved, renamed, or restructured.
- A file under `hooks/` is added, moved, or renamed.
- A top-level file documented to ship in the artifact (`README.md`, `LICENSE`, `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md`, `CONTRIBUTING.md`, `RESOLVER.template.md`) is added or restructured.
- A new top-level directory is added that should appear in the consumer artifact.

Do not run this skill for content-only edits to existing files that fit the established patterns; the workflow's automatic publish handles those. Run it when the *structure* changes, because the build script's globs and the workflow's rsync rules can quietly miss new shapes.

## Procedure

### 1. Generate locally and inspect

```bash
python3 bin/build.py
```

This produces `dist/nested/` and `dist/flat/` from the current `skills/` source. The script also writes `dist/<layout>/build-info.json` naming the layout, source ref, and timestamp.

Then inspect the flat output for what you changed:

```bash
ls dist/flat/skills/                              # top-level slugs as Craft Agent sees them
ls dist/flat/skills/<your-new-slug>/              # confirm SKILL.md present
cat dist/flat/skills/<your-new-slug>/SKILL.md     # confirm content matches source
git ls-tree --name-only HEAD -- dist/flat/        # if dist/ is tracked; otherwise diff against a known-good prior layout
```

If your structural change does not appear in `dist/flat/`, the build script's pattern-matching missed it. Stop here and update `bin/build.py` (the `find_rules()`, `ROOT_FILES`, and `copy_skill_dir()` functions are the usual sites). Do not proceed until the local build mirrors the change correctly.

### 2. Validate token resolution

```bash
python3 bin/build.py --check
```

This validates that every `[skill:<name>]` and `[rule:<name>]` token in source files resolves to an existing skill or rule in the layout being built. The angle-bracket form `[skill:<name>]` is the documentation-safe shape; literal slug-shaped placeholders are real references the resolver will try (and fail) to resolve. New skills that are not yet referenced by other content will not produce a check failure; new tokens that reference a misspelled name will. Run this before opening the PR.

### 3. PR + merge as usual

The publish workflow (`.github/workflows/build-and-publish.yml`) runs `python3 bin/build.py` on push to `main` and on tag push. On main pushes the workflow rsyncs `dist/nested/` to `release/nested` and `dist/flat/` to `release/flat`. On tag pushes (`v*`) the workflow additionally tags those branches as `vX.Y.Z-nested` and `vX.Y.Z-flat`.

The PR body should explicitly note that this is a structural change requiring the source-to-flat-to-consumer verification chain (per PR #86's worked example). Three steps spelled out in the PR body:

1. **Source-side fix:** the change in this PR. Cite the local `python3 bin/build.py` output as evidence.
2. **Flat-layout verification (post-merge):** after merge + tag fan-out, confirm the structural change actually appears in `release/flat`. The publish workflow should propagate it; the v2.0.0 RULES.md miss showed this is not fully trusted.
3. **Consumer-workspace verification:** sync from the new flat tag (or `release/flat` if no tag was cut) into a fresh consumer workspace per `UPSTREAM-UPDATE.md`; confirm the change is present at the expected consumer-shape path; exercise it where exercise is meaningful (a new scanner runs; a new rule is grep-able; a new hook fires).

### 4. Post-merge verification (steps 2 + 3 commands)

After the merge lands and the publish workflow completes, run from outside the repo:

```bash
# Step 2: confirm the change is in release/flat
TAG=release/flat   # or vX.Y.Z-flat after a tagged release
TMP=$(mktemp -d)
git clone --depth 1 --branch "$TAG" \
  https://github.com/siege-analytics/claude-configs-public.git "$TMP/repo"

# Verify the structural change appears at the expected path:
ls "$TMP/repo/skills/<your-new-slug>/"     # for new skills
ls "$TMP/repo/hooks/<group>/<file>"        # for new hook files
grep -c '<your new content>' "$TMP/repo/<file>"  # for content additions

# If anything is missing, that's a build-pipeline drift bug.
# File a separate ticket against bin/build.py or the publish workflow,
# do not patch the published artifact directly.
```

Then run Step 3 against an actual consumer workspace per `UPSTREAM-UPDATE.md` (rsync from the freshly-cloned flat tree into the workspace's `skills/` and `hooks/`, then exercise the change).

## Anti-patterns

- **Treating the workflow as a substitute for local `bin/build.py`.** The workflow runs `bin/build.py`. If `bin/build.py` is wrong, the workflow ships wrong. Local `python3 bin/build.py` + inspect catches build-script gaps before they ship.
- **Patching the published artifact directly.** If `release/flat` is missing something the source has, the fix is in the build script or the publish workflow, not in the flat branch directly. The flat branch is force-overwritten on every publish; manual edits get clobbered.
- **Declaring "shipped" before consumer-side verification.** The release is done when a consumer can sync the artifact and use it, not when the source merges or the tag pushes. Per writing-releases:5.

## Cross-references

- `[`writing-releases`](../_writing-releases-rules.md)` writing-releases:5: verify the published artifact loads in its consumption environment before declaring release done. This skill is the consumer-shape-specific implementation for the flat layout.
- `[`writing-releases`](../_writing-releases-rules.md)` writing-releases:1: BREAKING in changelog when public surface changes. Structural changes to skills/ or hooks/ that affect consumer integration may also be BREAKING (e.g., a renamed skill slug breaks consumer wiring); both rules apply.
- `bin/build.py`: the build script. The `find_rules()`, `ROOT_FILES`, and `copy_skill_dir()` symbols are the pattern-matching sites most likely to need updating when a structural change adds a new file shape.
- `.github/workflows/build-and-publish.yml`: the publish workflow that runs `bin/build.py` and rsyncs to `release/<layout>`.
- `UPSTREAM-UPDATE.md`: the consumer-side sync procedure (rsync from the flat tag into a workspace).
- LESSON 323a0f5: the v2.0.0 (2026-05-13) originating instance: build glob missed `RULES.md` and `_coverage.md` added at `skills/` root; v2.0.1 patched within the hour after sibling sync-verification surfaced the gap. The whole skill exists to default the discipline that sibling's manual verification provided in that case.
- PR #86: the worked example of the source-to-flat-to-consumer verification chain in a real PR body. The pattern this skill formalizes was first written in that PR's body for a specific structural fix; promoting it to a skill makes it the default for future structural changes.

## Attribution

Defers to `[`output`](../_output-rules.md)`. No AI / agent attribution in this skill or its outputs.
