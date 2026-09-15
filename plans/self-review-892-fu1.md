---
ticket_refs:
  - siege-analytics/claude-configs-public#892: comment pending
  - electinfo/craft-agents#49: comment pending
---

# Self-review: #892 FU1 -- runtime-aware ca-enforcement (manifest-driven)

## What changed
- `bin/build.py`: the three UserPromptSubmit gates (think-gate, investigate-gate,
  skill-enforcement-gate) now carry runtime_policy
  {craft: advisory, claude-code: block, codex-cli: block, unknown: block}
  (were all-advisory). Regenerated the manifest.
- `hooks/resolver/ca-enforcement-gate.sh`: before emitting continue:false, it
  consults each blocking gate's runtime_policy via gate-registry.sh +
  detect-host. hard_block (continue:false) only if a blocking gate's policy is
  "block" in the detected runtime; otherwise it narrates a
  <ca-enforcement-advisory> WITHOUT continue:false.
- `hooks/_test/ca_enforcement_runtime.test.sh` (new): 4 scenarios.

## Why
Central fix for the craft-agents#49 class: continue:false is recoverable in
Claude Code (injected, turn proceeds) but FATAL in Craft (hard-halts before the
model runs). Instead of hardcoding, the manifest now says block-where-recoverable,
advisory-in-craft, and ca-enforcement obeys it -- the intended payoff of the P0
primitives. User chose "manifest-driven per gate".

## Assumptions
- FAIL-CLOSED to the prior behavior: _ca_gate_blocks returns block UNLESS it can
  positively resolve an "advisory" policy for a positively-detected runtime. A
  missing manifest / undetected runtime keeps continue:false. This is the key
  safety property -- a missing manifest can never silently switch enforcement
  off. (Getting it backwards regressed the suite; see rework ledger.)
- CI and local runs are runtime=unknown -> block, so existing enforcement tests
  are unchanged (verified 11/0 + verify_enforcement 11/0).
- Only Craft downgrades to advisory, and only for these three design/guidance
  gates; the PreToolUse/pre-push mutation gates (self-review, branch-guard,
  test-guard) keep block in every runtime.

## Peer review (mechanics, correctness, craft floor)
- Syntax: bash -n ca-enforcement-gate.sh ok; build.py ast-parses.
- Direct runtime probe: craft -> advisory (no continue:false); claude-code ->
  continue:false; unknown -> continue:false. All tested.
- The advisory branch emits plain text (not the block JSON), so Craft does not
  parse it as a halt (per the #416 note that mixed/҂non-JSON stdout does not block).

## Lead review (adversarial: did this actually solve it?)
- Could a missing manifest disable enforcement? No -- fail-closed to block
  (tested via the copy-without-manifest enforcement suite, which stays 11/0 and
  would have flipped to advisory under the wrong default -- it did during dev).
- Does Claude Code enforcement change at all? No -- unknown/claude-code = block,
  identical to before (11/0 + verify_enforcement 11/0).
- Does Craft now deadlock on a design-gate block? No -- it narrates (tested).
- Do mutation gates weaken anywhere? No -- their runtime_policy is block in all
  runtimes; unchanged.

## Quantified claims
- "ca_enforcement_runtime 4/0" -- `bash hooks/_test/ca_enforcement_runtime.test.sh` -> `Results: 4 passed, 0 failed`
- "ca_enforcement_gate still 11/0" -- `bash hooks/_test/ca_enforcement_gate.test.sh` -> `Results: 11 passed, 0 failed`
- "verify_enforcement still 11/0" -- `bash hooks/_test/verify_enforcement.test.sh` -> `verify_enforcement: 11 passed, 0 failed`

## Review fixes (adversarial review of the first FU1 attempt, 4 findings)
The first attempt was reviewed and REJECTED (4 real findings). All fixed here:
- **F1/F2 (critical): enforcement silently disabled in deployed layouts + false
  fail-closed claim.** `gate_runtime_policy` fail-softs to "advisory"; the
  original `_ca_gate_blocks` treated non-advisory as block, so an unresolvable
  manifest downgraded every block. And the manifest lived only under
  dist/craft-agent/, unreachable from dist/claude-code/hooks/lib. Fix: (a) new
  `gate_runtime_policy_strict` echoes EMPTY (never a default) when unresolved, and
  `_ca_gate_blocks` downgrades ONLY on a literal "advisory" from it -- every other
  path blocks; (b) build.py colocates the manifest at hooks/enforcement-manifest.json
  so it travels with the hooks into every dist/* layout; (c) gate-registry.sh
  walks up from its own dir to find it. Verified: deployed claude-code layout now
  emits continue:false; missing/garbage manifest fails CLOSED even in craft.
- **F3: child continue:false was downgraded/mangled.** Fix: a child-emitted
  continue:false is captured and passed through VERBATIM as the sole stdout,
  unconditionally (never runtime-downgraded). Verified under craft.
- **F4: craft detection forceable by a spoofed CRAFT_* var.** Fix: do not honor a
  craft downgrade when CLAUDECODE is also set; that ambiguous case blocks.

## Review fixes round 2 (re-review found 3 MORE holes in the round-1 fix)
The round-1 fix (colocate at source hooks/ + walk-up resolver) was itself
flawed; re-review caught it. Round-2 fixes:
- **#2 (critical): colocation didn't reach the real deployables.**
  build_consumer_packages copies hooks/ SUBDIR-by-subdir, so a root-level
  hooks/enforcement-manifest.json is dropped; dist/claude-code/hooks/ had no
  manifest. Fix: write the manifest into EACH package's hooks/ dir inside
  build_consumer_packages (next to settings-snippet.json). Verified:
  dist/{claude-code,craft-agent}/hooks/enforcement-manifest.json now exist; the
  deployed claude-code hook hard-blocks; craft downgrades (anti-deadlock works
  in-package). Removed the source-tree hooks/enforcement-manifest.json (no
  committed generated file); repo-dev resolves via dist/craft-agent/.
- **#1 (critical): resolver walk-up picked up a FOREIGN manifest.** The
  round-1 walk-up climbed up to 6 parents; an isolated claude-code deploy under
  a parent holding an advisory manifest got downgraded. Fix: removed the walk-up
  entirely; resolver now trusts ONLY hooks/../enforcement-manifest.json
  (colocated) and the repo-dev dist path. Verified: an isolated package with a
  planted advisory parent manifest still BLOCKS (uses its own).
- **#4: F4 guard was asymmetric.** codex marker + spoofed CRAFT_* downgraded.
  Fix: the craft-downgrade guard now fires for CLAUDECODE OR CODEX_SANDBOX(_*)
  co-presence. Verified: codex+CRAFT blocks; legit craft still advisory.
- Manifest sync test now checks the BUILT manifest matches CA_ENFORCEMENT_GATES
  AND that it is colocated in both dist packages.

## Review fixes round 3 (re-review of round 2 found 2 more)
- **r3 #1: the drift test was tautological.** It rebuilt the manifest then
  compared to the same source in-process -> could never fail; corrupting the
  built manifest still "passed". Fix: snapshot the on-disk dist manifest BEFORE
  rebuilding and compare the snapshot to source. Verified: corrupting the
  on-disk manifest now FAILS the test.
- **r3 #2: F4 guard hardcoded a 3-var subset.** detect-host recognizes
  claude-code via CLAUDECODE + CLAUDE_CODE_ENTRYPOINT + CLAUDE_PROJECT_DIR; the
  guard only checked CLAUDECODE (+codex). Fix: reuse detect-host's own
  _DETECT_HOST_CLAUDE_VARS / _DETECT_HOST_CODEX_VARS via _detect_host_any_set so
  the guard can never drift from the detector. Verified: CLAUDE_CODE_ENTRYPOINT
  + CRAFT and CLAUDE_PROJECT_DIR + CRAFT now block.
- Also fixed a test-harness env leak: run_ca now scrubs the full marker set with
  env -u so results don't depend on the runner's ambient CLAUDE_CODE_ENTRYPOINT.

## Review round 4 (clean-ish) + fixes
Round 4 found NO active bug; all core security properties verified holding
(fail-closed on missing/garbage/empty/policy-absent manifest in every runtime;
no walk-up / no foreign-manifest pickup; colocated in both packages; child
continue:false verbatim). One latent robustness note + two cleanups, all fixed:
- **Latent (r4): set -u empty-array abort.** The F4 guard expanded detect-host's
  marker arrays; on bash 3.2 an empty array under set -u is an unbound-variable
  error that would abort the hook before emitting JSON. Fixed with `${arr[@]-}`.
  Verified: emptying a marker array no longer aborts and fails CLOSED (block).
- **Cleanup: drift test no longer rebuilds** (was a destructive dist/ clobber and
  the rebuild was unnecessary -- the check reads the on-disk manifest directly).
  Verified bidirectional (passes in sync, fails on corruption) and that it no
  longer self-heals the corruption.
- **Cleanup: removed dead tmp_out/snapshot vars.**

## Rework ledger
| Rework trigger | Root skip | Check cost | Rework cost | Ratio |
|---|---|---|---|---|
| enforcement suite went 4/7 fail on first attempt | fail-soft defaulted to advisory; test copies lack the manifest | one suite run | flip to fail-closed-block | high |
| adversarial review found deployed-layout disablement | I tested only the repo tree, never the dist/* deployed layout | full review | strict resolver + colocated manifest + 3 more findings | very high: this would have shipped enforcement-off to production |

## Trivial-investigation declaration
Not trivial -- this is the only enforcement-behavior change in #892; investigation
and pre-mortem for #892 exist and R1/R2 (silent-disable, CI-runtime flip) were
the explicit pre-mortem risks, both mitigated and tested.
