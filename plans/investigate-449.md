# Investigation: Skill-enforcement-gate (#449)

Ticket: #449

## Task understanding

Add a UserPromptSubmit hook that blocks agent turns when required SKILL.md
files have not been Read in the current session. The hook parses the session
transcript (session.jsonl) for Read tool call receipts.

## Pre-author inventory

### Verified Shapes

**Session transcript availability**
- PROBED: `ls -la $CRAFT_SESSION_DIR/session.jsonl` → 51MB, 5740 lines
- PROBED: `env | grep CRAFT_SESSION_DIR` → environment variable available
- PROBED: parsed 5740 lines in 0.09s via Python JSON parsing

**Transcript schema for Read tool calls**
- PROBED: `toolName: "Read"`, `toolInput: {file_path: "..."}` as dict
- PROBED: 26 unique SKILL.md reads found in current session transcript
- ATTESTED: paths appear with leading `./` (normalized by stripping)

**ca-enforcement-gate.sh wrapper pattern**
- PROBED: lines 79-80 call `run_gate` for each gate script
- PROBED: BLOCK_PATTERNS include `^BLOCKED:` — gates output this prefix
- ATTESTED: wrapper converts to `{"continue": false}` JSON (sole stdout)

**Think-gate resolution**
- PROBED: resolve-think-gate.py handles repo-scoped and legacy singleton
- PROBED: universal-mutation-gate.sh uses same resolver (lines 131-157)

## Findings

| Finding | Disposition |
|---|---|
| Original ticket assumed transcript_path in hook stdin — not available | Use CRAFT_SESSION_DIR env var instead |
| Think-gate claim verification (ticket item 2) already in think-gate-guard.sh | No new work needed |
| Pre-mortem presence check (ticket item 4) already in pipeline-state-guard.sh | No new work needed |
