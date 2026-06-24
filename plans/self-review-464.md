---
ticket: "#464"
scope: "bin/cross-review-server.py"
---

# Self-Review — #464 cross-review fallback resilience

## Junior Assessment

**What changed:** Added `fallback` parameter (default `true`) to the
`review` tool and a `review_with_fallback()` method to `ProviderCollection`.
When the requested provider fails (unavailable key, network error, rate
limit, auth failure), the server automatically tries other available
providers, preferring cross-vendor alternatives first, then same-provider
with a different model.

**Response metadata:** When fallback fires, the response includes
`fallback_used: true`, `original_provider`, `original_model`,
`original_error`, and `attempts` so the caller knows exactly what happened.

**Backward compatibility:** `fallback` defaults to `true`, so existing
callers get resilience without changes. Setting `fallback: false` preserves
the old hard-failure behavior.

## Lead Assessment

**Error containment:** `review_with_fallback()` catches `Exception` broadly
because provider failures can surface as `ValueError` (unavailable),
`RuntimeError` (no content), `httpx.ConnectError`, `openai.APIError`, etc.
The broad catch is correct here — any failure should trigger fallback, not
just a curated list.

**Fallback order is sound:** Cross-vendor first (preserves review
independence), then same-vendor/different-model (less independent but better
than nothing). The `_fallback_order` method excludes the originally
requested model from same-provider retries.

**No infinite loops:** `_fallback_order` returns a finite list. Each
candidate is tried once. The method terminates with `RuntimeError` listing
all attempts if everything fails.

**SU-1 compliance:** When all providers are exhausted, raises `RuntimeError`
with all attempt errors — never returns an empty/fake review.

## Trivial-investigation declaration

Single file changed. Fallback logic is self-contained in `ProviderCollection`.

## Trivial pre-mortem declaration

No existing behavior changes when the primary provider succeeds. The
`fallback=false` escape hatch preserves the old contract exactly.
