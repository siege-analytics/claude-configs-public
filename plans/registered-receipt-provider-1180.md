# Registered receipt provider across hook stacks

Goal source: https://github.com/siege-analytics/claude-configs-public/issues/1180, Part-of #1156. Baseline4312e8fc8f3c548cd8880d927490bd6eae160b85. Recorded before implementation in fix/registered_receipt_provider_1180.

## Investigated facts

The actual native author261104-active-coral transcript's last45 records contain two contradictory denials: the absolute workspace producer is rejected by the clone universal gate; the clone-relative producer is rejected by the workspace universal gate. Both request the executing policy generation's exact producer. Placeholders shown by the client are normalization, not an invented literal host path.

Existing task_actions._test_receipt_record selects its sibling producer from __file__. Existing external router registration verifies physical singly-linked metadata, global registration ownership, workspace policy and generation hashes, plus payload SDK/session identity. Registration does not pin test-evidence.py today. The source provider therefore cannot be selected from arbitrary task/env fields or trusted only because its basename matches.

## Design before code

An enrolled Craft context uses one fixed workspace hooks/lib/test-evidence.py across clone and workspace stacks. Discover the physical workspace from the host session directory, validate the standard host router registration using trusted local registration code, then bind payload SDK to a unique registered session. Add test_evidence_sha256 to the registration receipt, installer source comparison and generation verification. Only after those checks select the fixed workspace provider; preserve its physical regular singly-linked file checks. Never import caller-chosen provider code during classification.

Missing/corrupt enrollment fails closed, with no local-producer fallback in an enrolled context. An unregistered context retains the existing exact local-generation provider; a raw marker alone grants no alternate provider. The existing literal-command grammar, known Python, exact own implementing task, repository/source containment and adjacent output checks remain unchanged. No blanket script lane, hook disabling, fake success artifact or live settings write.

## Risks and test plan

Launch-blocking Tiger: attacker supplies an arbitrary workspace/provider. Red/negative fixtures must exercise two distinct hook locations against one disposable registered workspace; exact bound workspace provider passes both, unrelated/clone-local/changed/symlink/hardlink providers fail. Corrupt/missing generation pin, forged or unresolved SDK/session and foreign output fail. The standard registered host path is used, not a task-selected receipt path.

Launch-blocking Tiger: registration activation fails to pin the producer or races with it. Compare accepted-source provider bytes before activation and recheck before the active receipt is published; router generation verification checks the provider digest. Existing registration repair remains the exact-main operator path.

Use the existing real registration installer fixture with source-authority observation replaced by candidate fixture bytes only inside tests; no claim of production publication. Hook decision fixtures never execute the requested command. Receipt success claims require an actual bounded test-evidence producer run in disposable storage. Focused dual-hook, registration and task/output controls precede candidate publication; protected CI supplies the complete suite. Root owns installation and actual local-author re-entry proof.
