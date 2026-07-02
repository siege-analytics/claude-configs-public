---
ticket_refs:
  - siege-analytics/claude-configs-public#609
---

# Hostile Review - #609 coordinator status guard

Reviewer: fresh GPT-5.5 session `260701-mild-slate`
Mode: allow-all / execute-capable review session
Task: Review staged diffs for Codex/coordinator status bypass fix.

## Review rounds

The reviewer repeatedly returned `REQUEST_CHANGES` until known bypass classes were closed. Findings accepted and fixed:

1. Literal `gh` detection missed absolute-path and wrapper invocations.
2. `--body-file -` / unreadable body-file pipelines hid status text.
3. Negative/pending owner evidence could satisfy loose evidence regexes.
4. Shell-expanded inline `--body` hid status text.
5. `/dev/stdin` and fd aliases hid body-file content.
6. `gh api` issue comment/edit endpoints bypassed `gh issue` / `gh pr` detection.
7. Positional and indirect shell expansion (`$1`, `${!MSG}`) hid inline bodies.
8. `gh api -X POST <endpoint>` / `--method POST <endpoint>` method-before-endpoint forms bypassed endpoint detection.
9. `gh api` file/input payload bodies (`body=@status.md`, `body=@-`, `--input payload.json`) hid request bodies.
10. Editor/web-supplied bodies (`--editor`, `--web`) hid comment/review bodies.
11. Boolean equals editor/web forms (`--editor=true`, `--web=true`) bypassed bare flag detection.

## Final verdict

`APPROVE`

Final GPT status-guard approved diff: `ccp-609-full-staged-v9.diff`.

## Follow-up Claude runtime-boundary review

Reviewer: fresh Claude session `260702-new-reed`
Verdict: `REQUEST_CHANGES`

Finding: #609's Bash hook is real for hook-capable Claude Code runtimes but does not mechanically bind GPT/Codex child sessions, which do not run Claude Code hooks. The existing spawn-session rule text was prose only, and cross-review allowed child sessions to post ticket comments directly.

Accepted fixes:

1. Added `hooks/agent-comms/spawn-guard.sh` and wired it to `mcp__session__spawn_session` so parent sessions must specify permission, model, reasoning, sources, and child rule binding before spawning.
2. Added `hooks/_test/spawn_guard.test.sh` for parent-side spawn contract enforcement.
3. Updated `skills/cross-review/SKILL.md` to attach/inline rules and require reviewer findings to return through the hook-bound parent instead of direct child ticket posting.
4. Corrected design/investigation artifacts to state the runtime boundary accurately.
5. Applied non-blocking hardening: align spawn guard permission checks to the actual `allow-all` schema value and reject `gpt-4o` as a non-reasoning review model.
6. Added a regression for Codex-style future-plan ticket comments that promise to rerun gates and prove deployment/UAT/hotfix state later instead of posting current evidence.

## Verification at approval

- `bash -n hooks/bash/coordinator-status-guard.sh hooks/_test/coordinator_status_guard.test.sh`
- `bash hooks/_test/coordinator_status_guard.test.sh` -> 36 passed, 0 failed
- `python3 bin/validate-hooks.py` -> all hooks valid; existing unreferenced-hook warnings only
- `python3 bin/build.py` -> build succeeded
- `python3 bin/validate-hooks.py dist/claude-code/` -> all hooks valid; existing warnings only
- `python3 bin/validate-hooks.py dist/craft-agent/` -> all hooks valid; existing warnings only
- `python3 bin/sync-skill-references.py --check` -> clean
- `bash skills/detect-ai-fingerprints/scan.sh --working` -> clean
