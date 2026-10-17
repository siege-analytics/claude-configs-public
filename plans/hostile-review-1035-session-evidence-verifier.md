# Hostile review plan: session evidence verifier scope (#1035)

Attack the exclusion with:

1. `sessions/<id>/CLAUDE.md` at the active session root.
2. `sessions/<id>/database/AGENTS.md` lookalike.
3. `sessions/<id>/archive/data/CLAUDE.md` wrong depth.
4. Case variants of `sessions` and `data`.
5. Directory symlinks outside evidence storage.
6. Noncanonical root `AGENTS.md`.
7. Exact `sessions/<id>/data/**` files and directory symlinks that must not mutate or fail the active-policy proof.

Reject the patch if any active/lookalike path is excluded, if evidence bytes are changed, or if source and installed verifier behavior differ.
