# Independent review publication copy

Original receipt SHA256: `cb39d12172a45cf4c7c0289c8f65fb3c17c4d02f259efc9e3425c6a36a0c7f90`.
Only ASCII punctuation and a redundant word-list description are normalized in this publication copy. The individual acceptance and source identities are unchanged.

# Independent per-finding scanner disposition review

ACCEPT candidate/source-proposal dispositions for exactly F01-F27 below. This is not scanner PASS: actual completed scan remains exit1, 27 findings. No blanket baseline, suppression, ignore, clean-exit conversion or all-handler coverage claim is approved.

Binding: protected base 20bb5fb9c4eb88bc40c4f3f43b6c91e5a4fb7903; candidate tree cea67cd6b7e834a989a0e8481eefcd3a79820186. Raw SHA256 148441b6a8ba9f6efb7aed7fefb08e3737ccf86379a7f09e399bba7250faa172. Proposed Markdown SHA256 bf0d82ae1c03056d9773466e67bdf68de90a34f2db80de87bb73b6685a2d2234; metadata SHA256 9adce18b1fe477763fadf56dc7bba2ff24f6eaff426a3a718074f0f775e9e431.

Independently verified raw bytes, all36 source/test/scanner/policy candidate Git blob+SHA identities and protected-base blobs, current source equality, and all24 external artifact pins. Scanner AST/snapshot identities match protected base; pinned scan.sh changes do not remove rules. Candidate config absent/default, no override/ignore. Read every Reason/Evidence/Falsification and relevant new caller chains. Fifteen locator findings are accepted only as incorrect test-location observations, not proof every exception is covered. Eleven expected-outcome exceptions and one nested generator parameter finding accepted for specific reviewed behavior. Genuine earlier defects are repaired rather than deferred under this table.

| ID | Source finding | Independent disposition reason |
|---|---|---|
| F01 | bin/build.py:190 | ACCEPT: Mapped deployment and mount fixtures exercise immutable build/copy verification; locator misses bin/_test. |
| F02 | bin/craft-workspace-trust.py:352 | ACCEPT: Optional recovery manifest failure is followed unconditionally by not-verified failure; retained versions are untouched. |
| F03 | bin/craft-workspace-trust.py:44 | ACCEPT: Trust fixture imports helper and exercises real publication/race/non-main boundaries; locator misses bin/_test. |
| F04 | bin/install-craft-hook-router.py:232 | ACCEPT: Router fixture dispatches actual installer/migration/receipt activation; locator misses bin/_test. |
| F05 | bin/native_git.py:183 | ACCEPT: Reader safety and selected registration fixtures execute native adapter; locator misses actual fixture layout. |
| F06 | bin/validate-hooks.py:122 | ACCEPT: settings_drift_test imports actual comparison helper and checks registration drift; locator misses bin/_test. |
| F07 | bin/validate-local.py:97 | ACCEPT: local_validation_test executes copied actual CLI, including cancellation/error controls; locator misses bin/_test. |
| F08 | bin/wire-enforcement.py:55 | ACCEPT: Wire fixture dispatches actual CLI and merges/env failures; locator misses bin/_test. |
| F09 | hooks/lib/craft-settings-router.py:517 | ACCEPT: Audit failure returns already-computed decision, not fallback scope/authority; actual allow/deny controls preserve decisions. |
| F10 | hooks/lib/craft-settings-router.py:318 | ACCEPT: Only already-exited ProcessLookupError ignored during cleanup; original I/O failure propagates and leader is reaped. |
| F11 | hooks/lib/craft-settings-router.py:138 | ACCEPT: Path.relative_to nonmatch excludes foreign command from retirement; actual foreign ownership control passes. |
| F12 | hooks/lib/craft-settings-router.py:517 | ACCEPT: Router actual dispatch fixture exists and exercises boundary errors; locator misses bin/_test. |
| F13 | hooks/lib/git_command.py:247 | ACCEPT: Real CLI/protected Git/bytecode fixture executes git_command; locator misses hooks/_test. |
| F14 | hooks/lib/read-only-command.py:395 | ACCEPT: Reader fixture imports classifier and rejects malformed syntax; locator misses hooks/_test. |
| F15 | hooks/lib/resolve-think-gate.py:392 | ACCEPT: Uncomparable containment returns false, granting no scope; reviewed callers use containment positively. |
| F16 | hooks/lib/resolve-think-gate.py:631 | ACCEPT: Malformed callback/action returns no gate before native fallback; recovery regression denies legacy borrowing. |
| F17 | hooks/lib/resolve-think-gate.py:805 | ACCEPT: Git failure returns None, and lone-commit/directory callers fail closed to C instead of authoritative emptiness. |
| F18 | hooks/lib/resolve-think-gate.py:818 | ACCEPT: Unknown shell shape returns false for narrow lone-commit branch, retaining conservative classification. |
| F19 | hooks/lib/resolve-think-gate.py:896 | ACCEPT: Expected load failure returns no gate; callers require an actual loaded object. |
| F20 | hooks/lib/resolve-think-gate.py:117 | ACCEPT: Actual resolver imports/real-hook fixtures exist; locator misses hooks/_test. |
| F21 | hooks/lib/session_anchor.py:162 | ACCEPT: Unreadable/malformed/duplicate registered header returns no identity; direct strict mapping controls pass. |
| F22 | hooks/lib/session_anchor.py:42 | ACCEPT: Router strict identity and legacy anchor fixtures exercise actual helper; locator misses fixture locations. |
| F23 | hooks/lib/task_actions.py:207 | ACCEPT: Malformed Python returns false from proven-read predicate, preserving mutation requirements. |
| F24 | hooks/lib/task_actions.py:153 | ACCEPT: offset is read by nested generator any(p < offset for p in globs); grammar control distinguishes key/value offsets. |
| F25 | hooks/lib/task_actions.py:207 | ACCEPT: Task/reader fixtures import parser and execute real gate chains; locator misses hooks/_test. |
| F26 | hooks/lib/test-evidence.py:64 | ACCEPT: Producer fixture imports actual checker/producer and exercises actual Git/test commands; locator misses hooks/_test. |
| F27 | scripts/canary/craft-backend-canary.py:55 | ACCEPT: Canary fixture imports/dispatches actual helper for pinned/path/evidence errors; locator misses bin/_test. |

Independent direct controls rerun: router audit/cleanup/foreign ownership PASS; malformed/duplicate/unreadable strict header PASS; optional CAS metadata failure PASS. CAS control initially refused default /tmp symlink ancestry before exercising behavior, then passed with intended TMPDIR=/private/tmp. Earlier independent exact-source tests include router25, corrected trust17, reader9 and ResolverRecovery6; evidence maps remain narrow.

Each row retains the proposed falsifier: changed source/caller semantics, missing mapped fixture, control no longer reaching its chain, authority on expected error, or unused offset behavior invalidates its acceptance. New or changed findings require reconciliation/re-review; acceptance is not inherited by count. Mapping limitation is tracked in #1135, with no real defect deferred by ticket.

No source edits/global apply. Full Git-object workflow must pass after candidate commit before push/merge/install. Prior failed workflow remains failed evidence; this review authorizes only the enumerated source-proposal scanner dispositions.

Publication copy acceptance: independently verified plans/scanner-recovery-dispositions.md SHA256 c9dee08c097f038ee88e9090cf2b861ad3122cfb2f80e3e10608aae53f0c535f. After removing its provenance preface, it equals the reviewed original exactly under only em-dash-to-ASCII and removal of the two redundant adverbs with following spaces. No finding/evidence/falsifier/source identity or acceptance boundary changed. Copied metadata and raw output hashes remain 9adce18b1fe477763fadf56dc7bba2ff24f6eaff426a3a718074f0f775e9e431 and 148441b6a8ba9f6efb7aed7fefb08e3737ccf86379a7f09e399bba7250faa172. ACCEPT this documentation publication transformation; original historical pending/null statuses correctly remain separate from this independent receipt.
