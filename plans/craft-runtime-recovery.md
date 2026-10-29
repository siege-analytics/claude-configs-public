# Craft runtime recovery

Goal source: direct operator instruction, 2026-10-29: repair the reviewed defects and get local Craft Agents working.

## Investigation and design

The installed workspace was deployed from bcbb013. Its `enforcement-manifest.json`
is at the workspace root, while `hooks/lib/gate-registry.sh:37` searches the
hooks directory and source-build directory. `bin/build.py:1898` creates this
mismatch. The registry is consumed by the prompt wrapper and action gates;
the deployment must supply its colocated manifest without broadening lookup to
arbitrary parent directories.

The SDK transcript for session 261019-light-eddy records "Operation stopped by
hook" on the operator's status prompts. A marker-presence-only process probe
confirmed CRAFT_SESSION_DIR, CRAFT_IS_PACKAGED=true and
CLAUDE_CODE_ENTRYPOINT=sdk-ts on the Craft SDK child. The wrapper at
hooks/resolver/ca-enforcement-gate.sh:97 rejects this legitimate combination.
The manifest explicitly makes the three prompt checks advisory in Craft.
Standalone Claude/Codex and unknown runtimes must keep their blocking policy.

Prior knowledge: #892 established the per-runtime policy and anti-spoof guard;
docs/probes/craft-env.md already documents legitimate nested Claude markers.
The previous review reproduced each defect independently in disposable trees.
The two open branches were tested at db509fc (#1111, 119 cases) and 156900b
(#999, 398 cases). #1111 also accepts a ticket in a comment stripped by Git
when core.commentChar is non-default; an actual disposable commit confirmed
the final message contains no ticket. #999 needs reconciliation with develop.

Approaches considered: disabling prompt hooks would remove useful diagnostics;
trusting Craft environment variables alone would weaken the anti-spoof guard.
Selected: preserve fail-closed behavior for ambiguous markers unless OS process
ancestry identifies the packaged Craft host. Retain explicit child hard stops.
Deploy the manifest at the registry's existing trusted location. Test deployment,
nested SDK markers, standalone spoofing, and child hard-stop preservation.

Knowledge loci: README.md, craft-agent/README.md, docs/probes/craft-env.md,
the wrapper comments, and deployment integration tests. Update them with the
runtime distinction and avoid claiming live backend parity from package tests.

## Pre-mortem

- A forged marker could downgrade standalone enforcement: require a bounded
  process-ancestry check for mixed markers; missing ps or an unknown host keeps
  the block. Preserve existing spoof tests and add actual-host fixtures.
- A partial deployment could leave recovery broken: verify the colocated
  manifest and run the installed wrapper with a replay of the real hook payload.
- Restarting could lose task state: preserve session/task records and back up
  every installed file changed. Prefer hot-loaded hook repair before restart.
- Git cleanup could remove an accepted ticket: use Git's own cleanup semantics
  and test the hook against real final commit messages with custom comment chars.
- A broad installer could overwrite operator files or spawn automation sessions:
  deploy only reviewed runtime files with a rollback manifest; preserve settings,
  automations, root instructions, sessions, and task gates.

## Verification plan

Run affected hook suites, deployment/package fixtures and build validators.
Then replay installed hooks using the real session identity and marker shape,
check action-level deny/allow controls, and submit a bounded status-only UI
prompt that forbids resuming the old work. Record results here after execution.
