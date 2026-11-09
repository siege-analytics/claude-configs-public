# Structural GraphQL review workflow (#1210)

## Context and scope before implementation

Read the full issue and its two live evidence comments. Existing queue parsing
claims every literal GraphQL command and can mislabel review queries as enqueue
failures. The read classifier excludes GraphQL wholesale; the generic API path
cannot safely infer remote mutation authority from a local directory.

Implement one constrained structural GraphQL parser/transport helper. Supported
literal query documents are reads, with operation syntax parsed independently
of quoted data/comments; reject extra operations, unsupported syntax and
ambiguous transport. Support canonical literal -f/-F fields and --jq; mutable
--input documents remain unsupported with an actionable literal-form diagnostic.
Model only resolveReviewThread as a typed review write. Resolve its opaque ID
with a fresh bounded read of the actual thread, repository, PR and linked issue
identity, then bind it to one current-session own task and its existing review
permission/lifecycle. Reuse existing task binding/identity, no new repository
permission registry and no fabricated filesystem target. Role/lifecycle details
must respect actual review-only versus comment-capable grants; parent review
of that boundary precedes source freeze.

Preserve separately modeled queue/project/admin boundaries. Queue parsing must
not claim a structurally unrelated query or review operation. Every compound
member remains independently classified; remote permission never replaces a
local write gate. REST reply support is assessed against the same documented
workflow but cannot silently become arbitrary API permission. Coordinate with
the #1218 author; do not edit coordinator-status-guard in this lane.

## Risks and validation

Risks: mutation words in strings/comments, duplicate/extra operations, malformed
fields/method flags, unbound variables, mutable input-file races, unrelated
thread/PR/issue or task borrowing, planned/read-only review grants, and composed
file mutations. Add red-first actual-hook tests for the documented flow using
bounded fake GitHub read responses, never execute a live mutation. Fresh API
read proof is not actual remote mutation success or provider callback evidence.
Keep unsupported forms honest and canonical skill examples executable. Stage
authored source/plan before canonical refresh and obtain independent plus Root
source review before any commit/push. Normal publication/deployment and an
actual authorized native reviewer canary remain necessary for issue completion.
