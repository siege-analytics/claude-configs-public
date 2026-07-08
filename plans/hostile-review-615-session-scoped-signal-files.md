---
ticket_refs:
  - siege-analytics/claude-configs-public#615
---

# Hostile Review - session-scoped signal files

Reviewer session: `260708-windy-obsidian`
Reviewer model: Claude Opus, high reasoning
Mode: read-only fresh-agent review
Verdict: APPROVE

## Summary

The fresh reviewer approved the staged diff with no blockers.

Key conclusions:

- Think, investigate, and review gates route through `hooks/lib/resolve-think-gate.py` and now check session directories first.
- Standing-order has its own session-first resolver.
- Legacy workspace-root singleton files remain backward-compatible fallbacks.
- Session-scoped files win over workspace-root files when session identity is available.

## Reviewer non-blocking recommendation

The reviewer noted that isolation depends on the runtime exposing session identity. If no recognized session env var exists, legacy workspace-root fallback remains shared.

## Follow-up applied after review

To address that risk, the implementation was hardened to derive session identity from hook input JSON as well as environment variables:

- `hooks/lib/resolve-think-gate.py` now reads `CCP_HOOK_INPUT_JSON` and extracts `sessionId`, `session_id`, nested `session`/`conversation`/`metadata` ids, or a session id from `transcript_path`.
- Resolver consumers export hook input JSON before invoking the helper.
- `standing-order-guard.sh` also extracts session id from hook input JSON.
- `hooks/_test/session_signal_resolution.test.sh` now verifies hook JSON session ids beat workspace-root signal files when session env vars are absent.

## Post-review regression evidence

```text
bash hooks/_test/session_signal_resolution.test.sh
```

Result:

```text
4 passed, 0 failed
```

## Final status

APPROVE remains valid. The only substantive residual risk was addressed with hook-input session-id extraction and regression tests.
