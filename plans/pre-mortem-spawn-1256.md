# Spawn isolation risk review — #1256 item 3

This risk artifact was written after implementation and before publication. It
is not backdated pre-work approval. Root required genuine independent review,
read the resulting deltas and ran private fixtures before outward publication.

| Failure | Control and falsification |
|---|---|
| Accept shared primary checkout because prompt says worktree | Primary/magic-word/path negatives must deny; registered sibling must pass. |
| Accept copied .git pointer sharing another index | Registered admin backpointer must bind to actual inspected root. |
| Reject ordinary non-Git data/config writers | Existing plain directory must pass even with unavailable Git. |
| Child reuses parent's linked checkout | Same-root and inherited-directory negatives; parent stays outside child. |
| Metadata blocks the hook | Git subprocesses have bounded timeouts; nonblocking small regular backpointer read; FIFO and oversized inputs deny. |
| Inspect a different path from the host | Literal absolute target; exact HOME rewrite recognition; host-order lexical normalization before symlinks. |
| Revoke independent review access | Existing explicit read-only review and inherited review directory remain positive. |
| Imply production acceptance from unit results | No business session is spawned and no installed hook changes; live rollout belongs to the normal reviewed route. |

Rollback: this is an uninstalled feature candidate. Preserve current installed
files; a later regression is reverted through the ordinary reviewed source path.
No emergency disable, new registry, owner-GO prompt or arbitrary path exemption
is introduced by this fix.
