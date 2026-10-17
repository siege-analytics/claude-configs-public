# Self-review: session evidence verifier scope (#1035)

## Assumptions

- Craft workspace session `data/` directories are evidence storage, not supported session or project working-directory roots.
- A session root itself can be a working directory and remains an active instruction surface.
- Exact relative path segments, not substring/glob matches, define the exclusion.

## Review focus

- `is_session_evidence_path` reads exactly four fields so the final field absorbs the remaining suffix while the first three segments stay exact.
- The same predicate gates directory-symlink and instruction-file findings.
- Root `CLAUDE.md`/`AGENTS.md` checks are unchanged.
- Existing recursive, case-variant, root-symlink, and broad-bundle negative tests remain unchanged.

## Falsification ledger

- Initial direct test invocation refused an unbuilt tree (`full build required before kernel digest fixtures`); this is correct harness behavior, not a product result.
- After canonical build, the complete verifier suite passed 38/38, including the new exact evidence pass, session-root failure, both lookalike/deeper-path failures, and existing root/symlink/case-variant negatives.
- The patched source verifier passed against the real v3.5.64 installation after the separate root `AGENTS.md` remediation. Blocking wrapper, local block, native deny/allow, pinned kernel, root mounts, and recursive boundaries all passed. Live host invocation remains unverified.
- Representative archived-review and private-audit instruction bytes remained unchanged; the stale root `AGENTS.md` was preserved under a non-policy `.txt` filename with SHA-256 `27979e0c3ed17f4f1c0ef1ede94252aa557a1fb2e9feca341f0d2740972ce068` before replacement with `AGENTS.md -> KERNEL.md`.
- Build freshness, generated-source authority (198 sources / 804 snapshots / 2,916 mappings), skill inventory, review-risk metrics, ontology (39 terms / 160 bound values), review-risk tests, generated-source tests, and all 36 hook suites passed with zero failures.

## Lead verdict

Accept for independent review. The patch changes only verifier classification for one exact operational-storage path shape, preserves every active-policy negative boundary tested, does not mutate stored evidence, and passes the real installed-workspace replay. No live-host capability claim is made.

## Authorization

This verifier fact does not authorize policy, mutation, provider, or live-host behavior. It changes only which stored paths are classified as potential active instruction mounts.
