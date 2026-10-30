# Hub dispatch independent review

Pinned to d32c4e6 (source diff against origin/develop), 2026-10-29. Review-only.

Two must-fix S2 findings:

1. Failed mixed result envelopes still create a child. `spawned_session` can return a sessionId from an outer array before a sibling error. Although `result_failed` recognizes the error, the subsequent child append is unconditional on failure. Reproduced `[{'sessionId':'not-created'},{'isError':True,'error':'failed'}]`: pending reservation clears but permanent administered_spokes includes not-created. Missing metadata is considered active, so phantom load persists. Suppress success child extraction/append when the overall result is failed; test mixed nested/array errors.

2. Completed request pre-replay allows a new actual spawn beyond the cap. Reproduced fill three successful children, new request d blocks, completed request a Pre returns0, and actual subsequent success with extra-child grows spokes to4. Returning0 only makes accounting idempotent; it does not suppress tool execution. Refuse completed Pre replay and give the existing child receipt/path, while keeping duplicate Post events idempotent. Reused in-flight explicit fallback tokens need a clearly documented host-callback deduplication limitation; hook state alone cannot make tool execution idempotent.

Independent three targeted shipped tests passed in5.721s (protocol denial, outer-array lifecycle, token argument binding); the additional reproductions above expose missing cases. Protocol prevalidation is appropriately before reservation, fingerprint binding is useful, and PostToolUseFailure registrations preserve the intended cap/communication separation. Installed-host support was relayed as source evidence, not a live callback receipt. No independent live dispatch claim.

Correction re-review: completed Pre replay and direct/outer-array error suppression now address the original reproductions. Three targeted tests passed in 6.655 seconds. One same-class nested-envelope case remains: response={'structuredContent': {'isError': True, 'error': 'failed'}, 'content': [{'type':'text', 'text':'{"sessionId":"phantom"}'}]} still adds phantom to administered_spokes. Failure traversal must recognize the same structuredContent/tool_result/tool_response/text-JSON shapes as successful session extraction. No source edits made; re-review pending correction.

Final correction approved in working diff: failure detection now traverses JSON strings and the same text/structuredContent/tool_result/tool_response/content/toolResults wrappers as child extraction. Failed envelopes cannot append success children. Completed Pre replay blocks with existing-child guidance; repeated explicit-token pending Pre also blocks, while duplicate host callback identity retains its documented event-level behavior. Three focused tests passed independently in5.825s. Original reproduced blockers are resolved; no remaining must-fix in this slice. Exact follow-up commit receipt remains required. Host dispatch/UAT evidence remains separate.

Final reviewer message: APPROVED revised sources after all recognized JSON/text/error wrapper shapes were traversed; completed and explicit pending replay deny before another tool dispatch. Three targeted tests passed5.825s. No remaining must-fix in source; integrated full CI and actual host delivery remain separate.
