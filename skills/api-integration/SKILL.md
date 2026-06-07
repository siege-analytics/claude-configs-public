---
name: api-integration
description: "FE-backend integration contracts: error envelope, JWT lifecycle, multi-tenant headers, distributed tracing, SDK wrappers. TRIGGER: editing axios interceptors, API client code, auth flows, webhook handlers, or cross-boundary contracts."
routed-by: coding-standards
user-invocable: false
paths: "**/services/api.*,**/interceptor*,**/auth*,**/webhook*,**/clients/**"
---

# API Integration

Architectural doctrine for the contract between frontends and backends. Not framework syntax -- the rules that must hold for a request to cross the boundary correctly.

## Companion shelves

- [skill:vue] -- FE framework conventions (Pinia, routes, composables).
- [skill:django] -- Backend framework conventions (models, views, serializers).

## 1. Decision tree

```
START: I'm calling or receiving from an external service
  |
  +-- Direction?
  |   +-- FE --> backend
  |   |   Use the three-layer pattern:
  |   |     endpoints/<domain>.ts  (URL constants, :param placeholders)
  |   |     calls/<domain>.ts      (typed functions: api.get/post/patch/delete)
  |   |     store/<domain>.ts      (Pinia store orchestrating calls into state)
  |   |   OR, for feature-organized code:
  |   |     features/<feature>/services.ts  (endpoints + calls in one file)
  |   |
  |   +-- Backend --> external SDK (Stripe, Firebase, etc.)
  |   |   Wrap in core/clients/<service>/. Never import the SDK directly
  |   |   in a view, serializer, or model. The wrapper is the ACL.
  |   |
  |   +-- Partner --> backend (inbound webhook)
  |   |   Separate auth class. Audit fields per-request. See section 7.
  |   |
  |   +-- Backend --> backend (internal service call)
  |       HTTP or message queue, not direct DB writes across service
  |       boundaries.
  |
  +-- Am I changing the contract shape?
      +-- YES --> both sides must update in the same release window (section 2)
      +-- NO  --> proceed
```

## 2. The error envelope contract

The shape:

```
FE side (TypeScript):                    Backend side (Python):
interface ApiError {                     {
  error_code: ApiErrorCode                 "status_code": int,
  error_message: string                    "error_code": str,
  status_code: number                      "error_message": str,
  details: string |                        "details": str | dict[str, list[str]]
    Record<string, string[]>             }
}
```

**Rules:**

1. **Every non-2xx response carries this shape.** The FE's `normalizeApiErrorResponse` flattens `details` into a list for the toast. If the backend returns unenveloped JSON (bare Django exception, nginx error page), the normalizer crashes silently and the user sees a generic error.
2. **Any change to the envelope ships on both sides simultaneously.**
   - Adding a field (e.g. `trace_id`): FE interface extends first; backend ships after.
   - Renaming or removing a field: **both PRs merge together**.
   - New error code: FE's discriminated union falls through to default; add the new code to the FE type before the backend starts returning it.
3. **`error_message` is human-readable and safe to display.** The backend is the copy source; the FE does not rewrite error messages (except for toast formatting).

The backend produces this shape from a DRF `exception_handler` (project-defined) and the 500 handler in the project's root `urls.py`. The FE normalizes it (typically `normalizeApiErrorResponse` in the axios layer) before toasting. If the backend returns a bare DRF exception or an HTML error page, the normalizer's contract is violated -- fix the producer, not the normalizer.

## 3. JWT + refresh rotation

**The coupled-change rule:** reducing the backend's `ACCESS_TOKEN_LIFETIME` **breaks every open FE tab** unless the FE has a 401-retry-with-refresh interceptor. The two PRs must merge on the same day.

**The interceptor pattern when rotation is enabled:**

```ts
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const newAccess = await refreshToken(authStore.refreshToken)
      authStore.token = newAccess
      original.headers.Authorization = `Bearer ${newAccess}`
      return api(original)
    }
    return Promise.reject(error)
  }
)
```

**Rules:**
- Store both `access` and `refresh` when rotation is active. `refresh` lives in localStorage alongside `access`, OR in httpOnly cookies (more secure; requires CORS/CSRF alignment with the backend).
- The retry must be one-shot (`_retry` flag). Infinite retry loops on a truly-revoked token are a livelock.
- The 401 handler must NOT trigger logout on the first 401 -- it must attempt refresh first. Logout fires only when refresh itself fails.
- When rotation is disabled (long-lived access tokens, no refresh wired): the 401 handler should toast and log out immediately. This is correct for the no-rotation regime but is a known anti-pattern -- track removal of the long lifetime as a coordinated FE+BE change.

## 4. Multi-tenant headers

For multi-tenant backends, the FE sends a per-request tenant header (e.g. `X-Tenant-ID`, `X-Business-ID`, `X-Org-ID`). The exact name is project-specific; the pattern is universal.

```ts
// FE request interceptor (illustrative)
const tenantId = useTenantStore().selectedTenant?.id
if (tenantId) config.headers['X-Tenant-ID'] = tenantId
```

**Rules:**

1. **Set explicitly, not by undefined-omission.** Don't assign `undefined` to a header and rely on the HTTP client to strip it. Guard the assignment.
2. **Define skip-namespaces on the backend, not by URL inspection on the FE.** The backend's auth class is the source of truth for "this URL doesn't need a tenant header." The FE sends the header on every request; the backend decides what's required.
3. **The tenant header is an auth-layer boundary, not a view-layer concern.** A request without the header to a non-skipped endpoint should fail at the auth class (401), not deep inside a view.
4. **When adding a cross-tenant endpoint** (shared resource, cross-tenant lookup), register it in the backend's skip list AND verify the FE's interceptor still sends the header for everything else.

## 5. Distributed tracing

**The rules:**

1. **`tracePropagationTargets` must match the actual API host.** Sentry's quickstart placeholder (`/^https:\/\/yourserver\.io\/api/`) is dead config; if you see it in a real project, traces are not propagating. Replace with the real backend URL pattern:
   ```ts
   tracePropagationTargets: ['localhost', /^https:\/\/api\.yourdomain\.com/]
   ```
2. **Pick one tracing stack.** Either Sentry propagation works end-to-end (FE -> backend), or document that the FE and backend tracing stacks are intentionally separate and accept the manual-correlation cost.
3. **`tracesSampleRate`** should not be 1.0 in production for a high-traffic SPA. Reduce to 0.1-0.2 once the propagation target is fixed.
4. **Cross-boundary incident correlation** without trace propagation requires manual timestamp + user/tenant-ID matching across stacks -- expensive at incident time. Fix the propagation rather than relying on this.

## 6. External SDK wrappers

Every external SDK gets a wrapper:

| Side | Pattern | Example |
|---|---|---|
| Backend | `core/clients/<service>/` | Firebase, Stripe, SES, SQS |
| FE | `src/services/<service>/` or `features/<feature>/services.ts` | PostHog, Sentry, Radar |

**Rules:**

1. **Never import the SDK directly in a view, component, serializer, or model.** The wrapper is the Anti-Corruption Layer. It translates between the SDK's types and the project's domain types.
2. **The wrapper owns retry, error translation, and credential injection.** Callers see the project's error types (e.g. `ConnectorError`), not the SDK's.
3. **SDK version upgrades touch only the wrapper.** If an upgrade requires changes in callers, the wrapper's abstraction leaked.

## 7. Webhook auth

The inbound-webhook pattern (backend):

1. **Separate auth class** (e.g. `WebhookTokenAuthentication`). Never reuse the user-JWT auth class for webhooks -- the identity model is different (partner token vs user JWT) and conflating them creates privilege-escalation pathways.
2. **Audit fields per-request:** `last_used_at`, `request_count`, `last_request_ip`. Written on every authenticated request.
3. **Hot-row caveat:** at high inbound volume, per-request `UPDATE` on the webhook-user row is a contention point. Mitigation: batched async write or periodic aggregation from the API log.
4. **Webhook endpoints typically belong in the tenant-header skip list** -- the webhook payload carries its own tenant context; the request doesn't have an interactive user to provide one.

## 8. Topics this skill is silent on

These are not covered because they vary heavily by project. Extend the skill when introducing them, with explicit contract rules for each:

- **Feature flags / A-B testing infrastructure.** If a flag service is added, document where flag evaluation happens (FE? BE? both?) and how the contract crosses the boundary.
- **Real-time / WebSockets / SSE.** Reconnect semantics, message envelope, auth-on-connect -- all need explicit contracts.
- **GraphQL.** Schema versioning, error shape (GraphQL puts errors in a per-field array, not in a top-level envelope -- the rules in section 2 don't apply directly).
- **BFF (Backend-for-Frontend).** If introduced, the SPA-to-BFF and BFF-to-services contracts both need their own envelope/auth rules.
- **Rate-limit backoff on the FE.** When the backend returns 429, the FE needs explicit `Retry-After` handling -- don't toast-and-pray.

## Attribution Policy

See [rule:output]. NEVER include AI or agent attribution.
