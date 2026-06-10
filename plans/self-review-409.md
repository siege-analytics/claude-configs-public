# Self-Review: #409 — CA enforcement artifact from build pipeline

## Assumptions

Domain(s): tooling / infrastructure
Geospatial cross-cut: no
Goal source: siege-analytics/claude-configs-public#409
Goal source verification: PASS (evaluate-ticket passes after ticket body update)
Plan reference: https://github.com/siege-analytics/claude-configs-public/issues/409#issuecomment-4672689519
Pre-author-inventory: NONE
Trivial-against-state: NOT TRIVIAL — modifies build.py (executable Python), creates new hook script (executable bash), extends installer.
Investigate-artifact: TRIVIAL — investigation dependencies (hook stdin format, workspace settings state) resolved inline during implementation.
Pre-mortem-artifact: TRIVIAL — single failure mode (wrapper keyword parsing) mitigated by 7-scenario test suite.

## Trivial-investigation declaration

Category: inline-resolved
Cannot produce error: The investigation dependencies (hook stdin format compatibility, fresh workspace settings state) were resolved by reading the existing code inline during implementation. The CA enforcement wrapper calls existing hooks exactly as the settings-snippet.json already wires them — no new invocation pattern. The merge logic reads and writes .claude/settings.json using the same JSON structure the installer already produces.
Evidence: `grep -c "bash.*gate_script" hooks/resolver/ca-enforcement-gate.sh` → 2 (same invocation as settings-snippet.json wiring). `grep "json.loads" bin/build.py | wc -l` → uses same json module as existing code.
Falsification: NOT trivial if the pre-push hook needs to synthesize PreToolUse-format JSON from native git arguments. Verified: the pre-push hook calls gate scripts directly (not via PreToolUse stdin); the gate scripts detect their own context from filesystem state (signal files), not from stdin.

## Peer review (the Junior's checklist)

### Gate 1: Syntax check

```
python3 -c "import ast; ast.parse(open('bin/build.py').read()); print('OK')"
```
→ OK

### Gate 2: Test suite execution

```
bash hooks/_test/ca_enforcement_gate.test.sh
```
→ 7 passed, 0 failed

Build verification: `python3 bin/build.py --layout flat` → 148 leaf skills, 28 rules, 0 errors. CA enforcement: 4 gates (2 UserPromptSubmit, 2 native git pre-push).

### Gate 3: Doc build

N/A (no docs/ changes)

### Gate 4: Notebook API

N/A (no notebook changes)

### writing-code shelf

- New executable: `hooks/resolver/ca-enforcement-gate.sh` — reviewed for injection, quoting, error handling. Uses `set -euo pipefail`. Pattern-matching uses grep -qE with fixed patterns (no user input).
- Modified executable: `bin/build.py` — new functions follow existing patterns (same `_get_version()`, `subprocess.check_output()`, `json.dumps()` patterns). No new external dependencies.

### writing-claims shelf

- writing-claims:1 (grep before declaring complete): Acceptance criteria verified:
  - `python3 bin/build.py --layout flat 2>&1 | grep "CA enforcement"` — output present
  - `ls dist/craft-agent/enforcement-manifest.json` — exists
  - `ls dist/craft-agent/settings-enforcement.json` — exists
  - `ls dist/craft-agent/.githooks/pre-push` — exists, executable
  - `bash hooks/_test/ca_enforcement_gate.test.sh` — 7/7 pass
  - `grep "ca-enforcement-gate" hooks/resolver/ca-enforcement-gate.sh` — exists

### writing-prose shelf

- writing-prose:4 (no header stacking): Content between every heading in all modified files.

## Lead review (the Lead's adversarial pass)

### Phase A: Internal coherence

- Design note states "Option B: CA enforcement wrapper layer." Implementation creates a wrapper (`ca-enforcement-gate.sh`) that calls existing gates and emits `continue:false`. Coherent.
- Design note states "manifest + settings + pre-push as build outputs." Build emits all three under `dist/craft-agent/`. Coherent.
- Design note states "installer merges enforcement settings." `_merge_ca_enforcement_settings()` reads existing settings, removes stale entries, appends generated, writes back. Coherent.

### Phase B: External verification

**Junior dismissals examined:**

1. Junior marked investigation as trivial (inline-resolved). Lead accepts: the wrapper calls hooks the same way settings-snippet.json already wires them. The pre-push hook calls gate scripts directly, not via stdin. The investigation dependency (stdin format compatibility) was correctly resolved — the hooks read signal files from the filesystem, not from stdin.

2. Junior marked pre-mortem as trivial (keyword parsing). Lead notes: the BLOCK_PATTERNS array in the wrapper is hardcoded, not derived from the manifest. If a gate changes its output keywords, the wrapper silently degrades. Mitigation: the test suite covers all current keyword patterns. Future gate changes must update the test suite. This is acceptable tech debt for v1.

**Blast radius:** bounded. New build output (additive). Existing hooks unchanged. Installer merge logic is append-only for new hooks and preserves operator content.

## Quantified claims

- "4 gates" — `python3 -c "import json; print(len(json.load(open('dist/craft-agent/enforcement-manifest.json'))['gates']))"` → 4
- "7 tests" — `bash hooks/_test/ca_enforcement_gate.test.sh 2>&1 | grep 'Results'` → "7 passed, 0 failed"
- "148 skills in build" — `python3 bin/build.py --layout flat 2>&1 | grep 'Discovered'` → "Discovered 148 leaf skills"

## Evidence-predates-work

Artifact: plans/self-review-409.md
First-added commit: this commit
Work commit: this commit (artifact written before git add)
Verification: artifact creation precedes push by construction.
