---
title: Load-verify the published artifact, not just the source, after structural changes
category: packaging-truth
tags: [build, publish, dist, verification, git-ls-tree, release]
ticket: siege-analytics/claude-configs-public#62
date: 2026-05-13
severity: S2
source: lessons-learned
---

## Problem

v2.0.0 shipped with two files (`skills/RULES.md` and
`skills/_coverage.md`) missing from the published `dist/` layouts.
Source-side audit, build `--check`, and self-scan all reported clean.
The gap was only discovered when a downstream consumer ran a
sync-verify pass on their workspace.

## Root cause

`bin/build.py`'s `find_rules()` matched `_*-rules.md` only, so the
two new file shapes added at v2.0.0 never reached `dist/`. All
verification checks operated on the source tree, not on the published
artifact. "It's in the source" is not the same as "it shipped."

## Solution

Fixed the build script's file discovery patterns. Added the discipline
of running `git ls-tree <release-tag>` after any major-version
structural change to confirm every new or moved file is present at
the expected path in the published artifact. Shipped as v2.0.1 patch
within an hour of discovery.

## Prevention

The `writing-claims` rule applies to publish-level claims the same
way it applies to code-level claims: "RULES.md and _coverage.md
shipped" is a countable claim that needs same-turn evidence (`git
ls-tree`). Post-major-version releases now include a load-verify
step in the release checklist.
