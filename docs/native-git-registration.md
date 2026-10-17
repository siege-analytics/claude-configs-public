# Native Git registration

Siege supplies a canonical `.githooks/pre-push` wrapper for direct clones and the Craft package. It validates the native Git update stream through `hooks/git/pre-push-self-review.sh`. This protocol is different from tool-event JSON, so the range hook is not registered as a `PreToolUse` command.

Use the source installer with explicit consumer and package roots:

```sh
bash bin/install-hooks.sh --workspace /path/to/workspace --hooks-root /path/to/package --git-repo /path/to/consumer
```

`--git-repo` must name the exact consumer worktree root. The installer merges hook settings while preserving unrelated project settings and hooks. Commands that resolve to managed `hooks/git/pre-push-*` scripts are retired from Claude event arrays because those scripts consume the native push-update protocol and belong only behind `.githooks`; other dual-use `hooks/git` guards and non-command operator hooks retain their canonical registrations, and malformed existing command hooks fail before mutation. It rejects conflicting current entries or a different native hooks registration before writing. Reconcile conflicts before installation; installation does not grant permission to replace project policy. No-option direct-clone installation registers that clone. Settings-only options, including `--relative` and `--target-file`, do not implicitly register the source repository.

For each native push, the range validator checks every new non-merge commit, including an invalid interior commit followed by a valid head. Already-published ancestry on the actual destination is excluded, preserving historical promotion behavior. Other remotes and local tracking refs cannot exclude new commits. If a destination head object is unavailable locally, fetch that destination and retry. Incomplete protocol/object evidence blocks the operation; it does not count as a clean result. This implementation accepts SHA-1 object identifiers and fails closed for unsupported formats.

The source verifier can check a selected consumer registration and use the installed wrapper in a disposable repository and bare remote:

```sh
bash bin/verify-enforcement.sh --target /path/to/installed-workspace --git-repo /path/to/consumer
```

It observes a rejected invalid range with unchanged remote refs and a repaired range that advances the intended ref. A missing/no-op/non-executable wrapper, no-op range hook, or wrong registered path fails. Without `--git-repo`, consumer registration remains unverified. Root workspace mounts must already exist; extracting an archive alone does not install them.

These are local executable probes. Git hooks remain bypassable with `--no-verify`; they do not establish protected server acceptance or live Craft/backend invocation. Retained legacy branch/test dispatch is not new native-branch proof. Its migration and retirement remain tracked separately under #1002, #1003 and #849.
