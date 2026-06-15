---
title: Agents take side-effecting actions without investigating actual state
category: conventions
tags: [verify, state, side-effects, investigate, mutation]
ticket: siege-analytics/claude-configs-public#34
date: 2026-05-12
severity: S1
source: lessons-learned
---

## Problem

Agents inferred state from prior context, stale memory, or conversation
summaries instead of observing the current state, then took actions that
had to be reverted. The pattern was recurring across multiple sessions.

## Root cause

Invisible discipline ("I checked in my head") does not fire reliably.
Without a visible, auditable verification step, the agent shortcuts
from inference to action. The cost of a wrong action (revert, rework)
is hours; the cost of verifying first is seconds.

## Solution

Created `_verify-before-execute-rules.md` (Tier 3) requiring a visible
Verify-before-execute block grounded in same-turn evidence before any
side-effecting action. Shipped in PRs #35 and #37.

## Prevention

Rule `verify-before-execute` is enforced as a Tier 3 rule. The
self-review Lead review checks for missing verification blocks on
side-effecting operations. The `think` skill's "measure twice, cut
once" iron law reinforces the pattern at design time.
