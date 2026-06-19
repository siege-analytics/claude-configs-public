## Assumptions
Domain(s): agent workflow, MCP server
Geospatial cross-cut: no
Goal source: tickets #453, #454, #455, #456
Goal source verification: Manual — tickets filed from Codex hostile-review findings on #443.
Plan reference: remediation of Codex review findings
Pre-author-inventory: cross-review-server.py (426 lines, existing file)
Investigate-artifact: TRIVIAL (see declaration below)
Pre-mortem-artifact: TRIVIAL (see declaration below)

## Trivial-investigation declaration
Targeted fixes to a single file. #453 (resolve_skill traversal) and #455 (unknown provider KeyError) already fixed by another agent on develop — verified by reading current file. #454 (`_op_get` SU-1 violation) and #456 (inconsistent result shapes) still present and fixed in this changeset.

## Trivial-pre-mortem declaration
Risk surface: changes to `_op_get()`, `_resolve_credential()`, `_discover()`, `list_providers()`, and the unknown-tool handler. All changes are to the MCP cross-review server — a standalone tool with no downstream callers in the library. Failure mode: if credential lookup now raises instead of returning None, `_discover()` catches it and records the error. Result shape changes are additive (new keys, same JSON format). No existing callers break because the server is stdio-based.

## Peer review

### Syntax check
Python: `ast.parse()` passes, no syntax errors.

### Test suite
No test suite for this standalone server script. Verified via AST parse only.

### Build validation
No build changes. Server is a standalone script.

### Shelf: conventions
SU-1 compliance restored: `_op_get()` now raises `CredentialLookupError` on failures instead of returning None. Result shapes standardized to JSON across all tool responses.

## Lead review

### Phase A: Structural coherence
#454 fix: `_op_get()` distinguishes three states — `op` not installed (returns None), `op` present but lookup failed (raises CredentialLookupError with actionable message), credential found (returns value). `_discover()` catches CredentialLookupError and records it in `_errors` dict. `list_providers()` includes errors in response.

#456 fix: All three response paths (list_providers, review, unknown tool) now return JSON. Empty provider list includes `setup_hints`. Errors from credential lookup included in `errors` key.

### Phase B: Did this close the gap?
- [x] #454: `_op_get()` no longer silently swallows failures — raises typed exception
- [x] #454: `_resolve_credential()` propagates the exception
- [x] #454: `_discover()` catches and records errors per-provider
- [x] #456: `list_providers` returns JSON always (with optional `errors` and `setup_hints` keys)
- [x] #456: Unknown tool returns JSON with `error` and `available_tools` keys
- [x] #453: Already fixed on develop (is_relative_to checks present)
- [x] #455: Already fixed on develop (PROVIDER_DEFS.get() safe lookup, review() calls get_client() first)

### Phase C: Findings triage

## Findings

No findings.

## Quantified claims
- "Three states in _op_get" — verified: FileNotFoundError → None, TimeoutExpired/bad-rc/bad-JSON/empty-value → CredentialLookupError, success → str. Correct.
- "All response paths return JSON" — verified: list_providers (JSON), review (JSON), unknown tool (JSON). Correct.

## Evidence-predates-work
Artifact: plans/self-review-453-456.md
