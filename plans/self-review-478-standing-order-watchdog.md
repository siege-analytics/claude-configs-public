---
ticket_refs:
  - siege-analytics/claude-configs-public#478
---

# Self-Review: #478 standing-order watchdog package artifacts

## Assumptions

Working as: software engineer, tech lead
Domain(s): software engineering
Geospatial cross-cut: no
Goal source: ticket #478
Goal source verification: `bash scripts/discipline/evaluate-ticket.sh 478` returned BLOCK because the legacy ticket uses Problem/Design/Acceptance instead of Context/Goal/Assumptions. See exemption below.
Plan reference: `plans/design-478-standing-order-watchdog.md`; ticket comment https://github.com/siege-analytics/claude-configs-public/issues/478#issuecomment-4858254152
Pre-author-inventory: #478 ticket body and comments; related #477; Craft Agent automations docs; cited source files in investigation artifact.
Investigate-artifact: `plans/investigate-478-standing-order-watchdog.md`; ticket comment https://github.com/siege-analytics/claude-configs-public/issues/478#issuecomment-4858254270
Pre-mortem-artifact: `plans/pre-mortem-478-standing-order-watchdog.md`; ticket comment https://github.com/siege-analytics/claude-configs-public/issues/478#issuecomment-4858254408
Hostile-review-artifact: plans/hostile-review-478-standing-order-watchdog.md (execute-mode fresh reviewer `260701-mild-aspen`: APPROVE, no blocking findings)
Project-contribution: release package parity for standing-order continuity across Claude/Codex-style runtimes and Craft Agent workspaces.

## Exemption: ticket #478 structural format

Reason: #478 predates the current ticket evaluator format and contains the needed execution details under `## Problem`, `## Design`, and `## Acceptance`; rewriting the legacy issue body is not required to finish the already-scoped final acceptance item.

Evidence: `bash scripts/discipline/evaluate-ticket.sh 478` produced:
```text
BLOCK: ticket 478 has gaps before it is fit for execution:
  - missing sections: Context,Goal
  - no '## Assumptions' block
```

Falsification: if #478 lacked an acceptance item naming the Craft Agent standing-order watchdog config, or if the ticket comment had not narrowed the remaining scope to that item, this exemption would be invalid and the ticket body should be updated before work proceeds.

## Pre-implementation comprehension

Current behavior: `hooks/resolver/standing-order-guard.sh` implements the signal-file hook, and `hooks/settings-snippet.json` wires it for hook-based runtimes. `bin/build.py` copies hooks and settings into consumer packages but did not copy Craft Agent automation artifacts into `dist/craft-agent/`.

Intended behavior: the Craft Agent consumer package includes `automations-snippet.json` and `standing-order-watchdog.json`. The Claude Code consumer package does not receive those Craft-only files.

Steps: add Craft Agent source artifacts, add a Craft-only copy branch in `build_consumer_packages()`, and document the dual runtime split.

Success criteria: build completes; source JSON parses; Craft package contains the watchdog files; Claude Code package does not; hook package validation still passes.

Risk: the package could overstate platform enforcement. The reference config states the watchdog is periodic/remedial and not a platform-level end-of-turn hard block.

## Senior adversarial checklist

1. Hasty mistake checked: source artifact copy could have landed outside the `target == "craft-agent"` branch. The diff places it inside that branch.
2. Intended result is observable: file presence/absence in `dist/` after build.
3. Attention balance: build behavior, source docs, runtime split, and platform limit were checked.
4. Left-out concern: automation cannot hard-block a stopped turn. Documented in `platform_limit`.
5. Prior work read: #478, #477, automations docs, existing hook, build.py, hook docs.
6. Environment: branch `task/478_standing_order_watchdog` in CCP repo.
7. Failure case tested: `test ! -e dist/claude-code/automations-snippet.json` and companion watchdog absence check.
8. Instance or class: this is a package artifact gap for one Craft-only artifact pair, not a recurring copy class.
9. Done matches ticket: it closes the named remaining acceptance item from the #478 comment.
10. Likely skipped check: JSON syntax. It was run on source and dist artifacts.

## Peer review

### Mechanical checks

Shelf references: writing-code:5, writing-claims:2, writing-prose:1.

- Ticket evaluator: `bash scripts/discipline/evaluate-ticket.sh 478` -> BLOCK for legacy section names; exemption recorded above.
- Python syntax: `python3 -c "import ast; ast.parse(open('bin/build.py').read())"` -> exit 0.
- JSON syntax: `python3 -m json.tool craft-agent/automations-snippet.json` and `python3 -m json.tool craft-agent/standing-order-watchdog.json` -> exit 0.
- Build: `python3 bin/build.py` -> exit 0; output ended with `Done. Output: .../dist/`.
- Artifact placement: shell `test -f` for the two Craft files and `test ! -e` for the two Claude Code paths -> exit 0.
- Hook validation: `python3 bin/validate-hooks.py dist/claude-code/` and `python3 bin/validate-hooks.py dist/craft-agent/` -> "All hooks valid." with pre-existing unreferenced-hook warnings.
- Fingerprint scan: `bash skills/detect-ai-fingerprints/scan.sh` -> clean, exit 0. The scanner also printed an existing `config_arg[@]` shell warning but returned success.

### Correctness

`build_consumer_packages()` already branches on target for settings filtering and Craft skill stripping. The new artifact copy follows the same target-specific pattern and therefore cannot place Craft automation files in the Claude Code package unless the branch condition is later changed.

### Security

The new automation uses prompt actions only. It does not add webhook URLs, credentials, filesystem writes, or shell execution.

### Data integrity

No data mutation path is added. The watchdog prompt tells the spawned watchdog not to modify user files.

### Resource management

The SchedulerTick cadence is ten minutes. That is low enough for a reference watchdog and avoids per-minute session churn.

### Readability

The reference config separates runtime split, signal file lifecycle, completion criteria, non-compliant behavior, and platform limit.

## Lead review

The diff satisfies the remaining acceptance item without changing the existing pure hook. It also records the operator decision that standing-order continuity targets batch work that must continue until complete, blocked, or deadline reached. The main limitation is platform capability: Craft automation can create watchdog prompts, but not force a stopped turn to call a tool. The implementation names that limitation rather than promising a hard block.

Approach-fit verdict: fit for #478. This is package completion work, not a new enforcement hook.

Blast radius: low. Runtime behavior changes only for consumers who merge the new Craft automation snippet. Build output changes in `dist/craft-agent/`; source hook behavior is unchanged.

## Findings

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| 1 | P3 | Craft watchdog is periodic/remedial, not a hard end-of-turn platform block. | Documented in `standing-order-watchdog.json` platform limit. |

## Quantified claims

- "ten minutes" - `grep -n '"cron"' craft-agent/automations-snippet.json` -> `"cron": "*/10 * * * *"`.
- "two Craft files" - `test -f dist/craft-agent/automations-snippet.json && test -f dist/craft-agent/standing-order-watchdog.json` -> exit 0.
- "two Claude Code paths absent" - `test ! -e dist/claude-code/automations-snippet.json && test ! -e dist/claude-code/standing-order-watchdog.json` -> exit 0.

## Rework ledger

| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| Fingerprint scanner flagged punctuation/adverb in staged prose. | Initial prose used blocked style tokens. | Seconds. | Edited affected lines and reran scanner. | Low. |

## Evidence-predates-work

Artifact: `plans/self-review-478-standing-order-watchdog.md`
First-added commit: pending first commit containing this artifact
Work commit: pending
Verification: artifact was written before commit creation; final commit will cite this artifact in `Self-Review:` trailer.
