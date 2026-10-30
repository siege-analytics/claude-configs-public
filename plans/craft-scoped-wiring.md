# Craft scoped policy wiring

Goal source: operator authorization to finish the remaining repairs, delegated
under #1134. Scope is normal installer orchestration, policy destination selection
and truthful installation documentation. The router/receipt implementation is a
separate slice. This worktree performs no global registration or live activation.

Investigation: the observed Craft SDK child used workspace/sessions/<session-id>
as its cwd. Workspace .claude/settings.json alone was not discovered there.
Trust alone did not make the no-gate mutation fail. A per-session settings link
with a fresh SDK child did produce the expected denial. These observations show
the missing delivery route; they do not establish final router invocation.

Plan: install managed commands into workspace/.claude/craft-settings.json, wire
and verify that explicit policy path, then require the bootstrap installer to
apply and verify its registration. Its receipt is
workspace/.claude/craft-hook-registration.json schema version one. The bootstrap
retains global operator hooks and retires only owned legacy project commands.
Default low-level wire/verify calls retain their previous settings filenames.

Pre-mortem: selecting a new file only in the writer would leave verification
checking an old copy; all settings assertions therefore use the explicit file.
Re-running build after migration could silently restore the legacy autoload
wrapper; any router receipt presence selects only the fixed new policy filename,
while actual receipt authority remains the helper's responsibility. Skipping a
missing helper would falsely report installation success; both normal entrypoints
refuse before deployment. Failed local verification cannot apply registration.

Validation: actual wire CLI calls prove default compatibility, explicit path
selection, workspace command-root resolution and idempotence. Actual deployment
and verifier calls prove receipt-based routing, legacy operator content
preservation and explicit-policy verification. Disposable fake-HOME shell
orchestration checks argument propagation, ordering, missing helper refusal and
failed-verification refusal. Local checks and registration receipts are separate
from the coordinator's live Craft callback canary. Pi/Codex hook parity remains
unsupported.
