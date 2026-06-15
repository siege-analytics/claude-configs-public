---
title: Concurrent build-and-publish runs race when main and tag pushed back-to-back
category: pipeline-operations
tags: [ci, github-actions, concurrency, force-push, release, race-condition]
ticket: siege-analytics/claude-configs-public#38
date: 2026-05-12
severity: S2
source: lessons-learned
---

## Problem

Pushing main and immediately pushing the version tag triggered two
GitHub Actions workflow runs ~2 seconds apart. Both force-pushed to
`release/nested` and `release/flat`. The second run failed with
`cannot lock ref` because the first run had already updated the ref.
The tag-push run lost, so `vX.Y.Z-nested` / `vX.Y.Z-flat` fan-out
tags were not created.

## Root cause

The workflow had no concurrency group. Two triggers on the same branch
targets ran in parallel and raced on the force-push step. Standard
release sequence (main push + tag push) always produces this race.

## Solution

Added `concurrency` group with `cancel-in-progress: false` to the
build-and-publish workflow so back-to-back triggers queue instead of
racing. Shipped in PR #39.

## Prevention

The workflow's concurrency group serializes all runs targeting the
same branch. New workflows that force-push to shared branches must
declare a concurrency group — this is now a review checkpoint in the
pipeline-operations category.
