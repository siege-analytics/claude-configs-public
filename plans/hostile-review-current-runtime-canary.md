# Current runtime pin review

Reviewed exact commit 351b9ba against origin/develop, 2026-10-29. Verdict: approved, no must-fix findings.

Moving versions and digests into immutable approved run data preserves exact package identities, strict record fields, absolute paths and SHA256 syntax. approval_subject_sha256 still binds the entire installed_builds record; changing current runtime pins changes the approval subject. Discovery still compares installed artifact bytes, versions and adapter markers. Active selection requires separate host evidence; manifest/runtime capture cannot fabricate it. The read-only capture command returns authorization_effect none and does not mutate historical run manifests or approvals.

Independently ran craft_backend_canary_test.py with the pinned PyYAML interpreter: 15 tests passed in 20.404 seconds, including stale installed bytes, bad paths/versions/digests and changed approval subject. This is source/fixture acceptance, not live backend dispatch evidence. No deployment, capture of private state or external writes performed by reviewer.

Exact approved commit: 351b9bae8c6f4176163bfa286c3cead3b44de8e3. Approval does not claim current runtime canary completion or authorize changes to a recorded run's approval subject.

Additionally verified approval.proposal.json pins.approval_driver_sha256 equals actual script source SHA256 f2406a9516359f56c0ea9f764acf6f40606f553571fef7fee36b07c6e576665f.
