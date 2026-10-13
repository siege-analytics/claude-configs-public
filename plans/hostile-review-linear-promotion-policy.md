# Hostile review: linear promotion and main-only deployment policy

Two independent adversarial passes were run against the complete policy diff before push.

## Round 1

| Severity | Finding | Resolution |
|---|---|---|
| S1 | Candidate PR could replace the topology script executed by its own check. | Switched to `pull_request_target`, checked out protected-base policy separately, set read-only permissions, and execute only the trusted script while treating candidate checkout as data. |
| S1 | Deleting the marker could disable deployment enforcement. | Policy activation is sticky once marker history exists and also inspects authoritative remote-main content/history. |
| S2 | PR retargeting did not rerun the guard. | Added the `edited` event. |
| S2 | Main could advance after initial source verification. | Added pre-mutation and post-mutation remote-main verification; post-write failure invalidates the deploy stamp. |
| S2 | Referenced checker absent from the plain unstaged diff. | Added and staged the checker with the implementation commit. |
| S3 | Fork branch named `develop` could impersonate canonical develop. | Main promotion requires both head name `develop` and canonical repository identity; regression added. |

## Round 2

| Severity | Finding | Resolution |
|---|---|---|
| S2 | Remote policy lookup could fail open for a checkout without local marker history. | All deployment now fails closed when authoritative `origin/main` cannot be read. |
| S2 | Main could move during workspace mutation. | Added final post-write verification and invalidates `deploy-stamp.json` on mismatch. This makes the copy non-authoritative until the new main is installed. |
| S2 | Required checks could deadlock a future GitHub merge queue. | Added `merge_group` triggers to validation and topology workflows; queued candidates must contain current main. |
| S3 | New referenced files did not appear in an unstaged plain diff. | All referenced scripts and fixtures are included in the implementation commit and CI paths. |

## Verdict

No unresolved S1 or S2 findings remain. The unavoidable filesystem copy interval is fail-closed by post-write source verification and stamp invalidation; an installation is authoritative only while its exact-main deploy stamp remains present and drift validation passes.
