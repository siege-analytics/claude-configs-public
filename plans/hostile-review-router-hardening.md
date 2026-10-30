# Independent final router hardening review

ACCEPT bounded four-file hardening source in integration, matching all four SHA256 identities in /private/tmp/router-hardening-source-report.md. No remaining must-fix found. No source edits or live/global apply.

Independent checks: router25/25 PASS6.135s; wire_enforcement_automations_test PASS. Independently inspected constant shell program/positional argument quoting, exact canonical current and legacy ownership, global duplicate checks, decision normalization, whole-tool matching, main exception boundary and generated environment merge.

N1: native markerless callbacks exit in constant /bin/sh bootstrap before Python or router access. Marked missing router exits2. Router/workspace/event are separate shell positional arguments rendered with shlex.join, not inserted into executable shell code. Owned current command text is exact canonical identity; legacy direct command recognized only for migration, refused at runtime. Unknown operator text is not retired by approximation.

M1: PreToolUse explicit top-level block/continue=false normalizes to permissionDecision=deny. Allow/ask conflict fails closed; denied results remove approve/continue=true channels. Explicit JSON denial retains exit-zero protocol while failed hooks still return blocking status2. M2 uses fullmatch, preventing Write from matching TodoWrite or Edit from matching larger tool names.

M3: known exact physical workspace hook commands registered directly in global settings cause refusal, not auto-erasure. Exact global CLAUDE_CA_ENFORCE string1 also refuses with repair guidance; altered values survive. Installer policy validation/glue is covered by prior publication review and current real-router fixtures. M5 path resolution/enrollment errors now lie inside failclosed handler; markerless native path remains a cheap no-op. Supported /Applications host ancestry boundary remains limited; unresolved workspace templates do not invent enrollment.

Wire merge copies only generated known CLAUDE_CA_ENFORCE string1. It does not copy arbitrary generated environment keys; missing/altered source flag leaves existing operator values untouched. Malformed source or target environment rejects before replacing destination bytes. Known generated flag copying does not become session/task authority. Normal installer selects dedicated craft-settings policy; legacy direct-call default is retained for compatibility. Existing foreign command preservation and idempotence tests remain.

This source/fixture acceptance does not establish actual installed SDK delivery, Pi/Codex parity, a future-writer concurrency guarantee, or scanner disposition approval. Final aggregate source commit/full workflow/scanner evidence and live canary remain separate.
