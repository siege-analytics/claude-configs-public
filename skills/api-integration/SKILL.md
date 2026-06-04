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

- [`vue`](../vue/SKILL.md) -- FE framework conventions (Pinia, routes, composables).
- [`django`](../django/SKILL.md) -- Backend framework conventions (models, views, serializers).
- [`pour-now-triage`](../pour-now-triage/SKILL.md) -- restoration overrides that freeze specific contract changes during triage.

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
  |       boundaries. See pour-now-triage for the catalog-write-API plan.
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

Backend produces this shape in `apps/api/exceptions.py::exception_handler` and `pournow/urls.py::django_500_handler`. FE consumes it in `src/services/api.ts` and `src/utils/normalizeApiErrorResponse`. See [business-backend wiki -- API Surface SS Custom error envelope](https://github.com/pour-now/business-backend/wiki/API-Surface#custom-error-envelope) and [business-admin wiki -- API Client SS Error handling contract](https://github.com/pour-now/business-admin/wiki/API-Client#error-handling-contract).

## 3. JWT + refresh rotation

**Current state (pour-now):** the FE stores `access` only; ignores `refresh`. The backend issues `{ access, refresh }` from `/auth/login/` with a [99999-day lifetime](https://github.com/pour-now/business-backend/wiki/Django-Deviations#12-jwt-lifetime-of-99999-days). No 401-retry-with-refresh exists in the axios interceptor.

**The coupled-change rule:** reducing the backend's `ACCESS_TOKEN_LIFETIME` **breaks every open FE tab** until the FE adds a 401-retry-with-refresh interceptor. The two PRs must merge on the same day.

**When rotation is enabled, the interceptor pattern:**

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
- Store both `access` and `refresh` when rotation is active. `refresh` goes in localStorage alongside `access` (or httpOnly cookies if the team migrates -- see pour-now-triage).
- The retry must be one-shot (`_retry` flag). Infinite retry loops on a truly-revoked token are a livelock.
- The 401 handler must NOT trigger logout on the first 401 -- it must attempt refresh first. Logout fires only when refresh itself fails.
- When rotation is disabled (current state): the 401 handler toasts and logs out immediately. This is correct for the 99999-day-lifetime regime.

See [business-admin wiki -- State Management SS JWT lifecycle](https://github.com/pour-now/business-admin/wiki/State-Management#jwt-lifecycle) and [business-backend wiki -- Django Deviations SS1.2](https://github.com/pour-now/business-backend/wiki/Django-Deviations#12-jwt-lifetime-of-99999-days).

## 4. Multi-tenant headers

The `X-Business-ID` pattern:

```ts
// FE request interceptor
config.headers['X-Business-ID'] = useBusinessStore().selectedBusiness?.id
```

**Rules:**

1. **Set explicitly, not by undefined-omission.** The current code sets the header to `undefined` when `selectedBusiness` is null, relying on axios to omit undefined headers from the wire. This works but is fragile. Prefer an explicit guard:
   ```ts
   const businessId = useBusinessStore().selectedBusiness?.id
   if (businessId) config.headers['X-Business-ID'] = businessId
   ```
2. **Backend `SKIP_NAMESPACES`** (`admin`, `moderation`, `business`) exempt specific URL namespaces from the `X-Business-ID` requirement. The FE's "list my businesses" call (`GET /businesses/`) runs in the `business` namespace and works without the header. Everything else requires it.
3. **The header is the tenant boundary.** A request without `X-Business-ID` to a non-skipped endpoint returns 401 from `JWTAuthentication`. This is auth-layer enforcement, not view-layer.
4. **When adding a new endpoint** that should work without tenant context (cross-tenant lookup, shared resource), register its URL name in `JWTAuthentication.SKIP_URL_NAMES` on the backend AND verify the FE's interceptor still sets the header for everything else.

See [business-backend wiki -- API Surface SS JWTAuthentication](https://github.com/pour-now/business-backend/wiki/API-Surface#jwtauthentication--tenancy-enforcement-at-the-auth-layer) and [business-admin wiki -- API Client SS Request interceptor](https://github.com/pour-now/business-admin/wiki/API-Client#request-interceptor--adds-auth--tenancy-on-every-call).

## 5. Distributed tracing

**Current state (pour-now):** broken. The FE's `tracePropagationTargets` is set to the Sentry quickstart placeholder (`/^https:\/\/yourserver\.io\/api/`), so FE traces never propagate to the backend. The backend has three separate APM stacks (Sentry errors-only, New Relic, AWS Application Signals) with no inbound trace context from the FE.

**The rules:**

1. **`tracePropagationTargets` must match the actual API host.** Replace the placeholder with the real backend URL pattern:
   ```ts
   tracePropagationTargets: ['localhost', /^https:\/\/api\.yourdomain\.com/]
   ```
2. **Pick one tracing stack.** Either Sentry propagation works end-to-end (FE -> backend), or document that "Sentry is errors-only; AWS Application Signals does tracing" and don't pretend otherwise.
3. **`tracesSampleRate`** should not be 1.0 in production for a high-traffic SPA. The current 100% sample rate is a cost concern; reduce to 0.1-0.2 once the propagation target is fixed.
4. **Cross-boundary incident correlation** without trace propagation requires manual timestamp + user/business-ID matching across two stacks. This is the current operational reality.

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

1. **Separate auth class** (`WebhookTokenAuthentication`). Never reuse `JWTAuthentication` for webhooks -- the identity model is different (partner token vs user JWT).
2. **Audit fields per-request:** `last_used_at`, `request_count`, `last_request_ip`. Written on every authenticated request.
3. **Hot-row caveat:** at high inbound volume, per-request `UPDATE` on the webhook-user row is a contention point. Mitigation: batched async write or periodic aggregation from the API log.
4. **Webhook endpoints are in `SKIP_NAMESPACES`** (no `X-Business-ID` required). The webhook payload carries its own tenant context.

## 8. What this skill is silent on

These are not covered because pour-now does not have them. The skill should be extended when they're introduced:

- **Feature flags / A-B testing infrastructure.** No feature-flag service is integrated. Feature gating is done by route-level `visibleEntityTypes` meta or backend permission checks, not by flag evaluation.
- **Real-time / WebSockets.** No WebSocket, SSE, or polling-based real-time updates. The SPA is request-response only.
- **GraphQL.** The API is REST (DRF). No GraphQL layer exists or is planned.
- **BFF (Backend-for-Frontend).** The SPA talks directly to the multi-service backend. There is no aggregation layer.
- **Rate-limit backoff on the FE.** The FE has no 429-aware retry logic. When the backend returns 429, the user sees a toast and retries manually. Backoff handling should be added alongside any backend rate-limit hardening.

## Attribution Policy

See [`_output-rules.md`](../_output-rules.md). NEVER include AI or agent attribution.
