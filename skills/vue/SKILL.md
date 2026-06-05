---
name: vue
description: "Vue 3 conventions for Composition API, Pinia stores, route guards, and restoration-mode FE work. TRIGGER: *.vue, *.ts importing from vue/pinia/vue-router, or touching route/store/composable files. Stacks with api-integration and pour-now-triage sub-skills."
routed-by: coding-standards
user-invocable: false
paths: "**/*.vue,**/*.ts,**/router/**,**/store/**,**/features/**"
---

# Vue 3

## Companion shelves

For cross-boundary contract rules:
- [skill:api-integration] -- FE-backend contract (error envelope, JWT, X-Business-ID).
- [skill:pour-now-triage] -- restoration overrides that freeze specific migrations during triage.

For general TypeScript discipline:
- [rule:typescript] -- strictNullChecks, noUncheckedIndexedAccess, no ts-ignore without explanation.

Apply when editing `.vue` files, Pinia stores, route definitions, or composables. Draws from:
- Vue Style Guide (vuejs.org/style-guide) -- Priority A (Essential) and B (Strongly Recommended) rules
- Pinia docs (pinia.vuejs.org) -- setup-store syntax
- VueUse (vueuse.org) -- useStorage, utility composables

## 1. Decision tree

```
START: I'm touching Vue/FE code
  |
  +-- Where does this code live?
  |   +-- features/<feature>/  --> NEWER pattern. Add code here for new work.
  |   |   Self-contained: components/, composables/, constants/,
  |   |   routes.ts, services.ts, types.ts, views/
  |   |
  |   +-- src/components/Layout/<Feature>/  --> LEGACY. Touch-but-don't-grow.
  |   |   Fix bugs in place. Do NOT add new components here.
  |   |   Do NOT migrate to features/ during restoration (see pour-now-triage).
  |   |
  |   +-- src/components/Base/  --> Shared primitives (Button, Input, DataTable).
  |   |   Edit in place. New shared primitives go here too.
  |   |
  |   +-- src/store/<domain>.ts  --> Legacy Pinia stores. See section 4.
  |   +-- src/router/<domain>.ts  --> Legacy routes. See section 5.
  |   +-- src/services/{endpoints,calls}/  --> Legacy API layer. See api-integration.
  |   +-- src/composables/  --> Shared composables. New ones OK here or in features/.
  |
  +-- What am I building?
  |   +-- A new feature  --> features/<feature>/ with its own routes.ts, services.ts
  |   +-- A Pinia store  --> setup syntax, resetStore(), register in logout hierarchy
  |   +-- A route  --> meta keys from the canonical list (section 5)
  |   +-- A composable  --> Composition API only, typed return
  |   +-- A component  --> <script setup lang="ts">, props via defineProps<>()
  |
  +-- Am I touching the global guard (router/index.ts)?
      +-- YES  --> read section 5 first; the guard has specific sequencing rules
      +-- NO   --> proceed
```

## 2. Composition API + `<script setup>` doctrine

Every component uses `<script setup lang="ts">`. Never Options API.

```vue
<script setup lang="ts">
// Props: generic type syntax, not runtime declaration
const props = defineProps<{
  campaignId: number
  editable?: boolean
}>()

// Emits: typed
const emit = defineEmits<{
  save: [payload: CampaignPayload]
  cancel: []
}>()

// Composables for reactive logic
const { data, loading } = useCampaignDetails(props.campaignId)
</script>
```

**Rules:**
- Props typed via `defineProps<T>()`. Default values via `withDefaults()`.
- Emits typed via `defineEmits<T>()`. Event names are verbs.
- No `this.` -- `<script setup>` has no `this`.
- Reactive state via `ref()` / `computed()` / `watch()` -- not `reactive()` for top-level state (refs are explicit about `.value`).

**Auto-imports.** The team uses `unplugin-auto-import` configured for `vue`, `vue-router`, and `pinia`. `ref`, `computed`, `useRouter`, `useRoute`, `defineStore`, and all stores in `src/store/` are available without imports. New code respects this -- don't add explicit imports for auto-imported symbols. The tradeoff (invisible provenance) is accepted.

## 3. The two-organization split rule

The codebase has two parallel organizational patterns:

| Pattern | Where | Status |
|---|---|---|
| **Legacy: by layer** | `components/Layout/<Feature>/`, `store/<domain>.ts`, `router/<domain>.ts`, `services/{endpoints,calls}/<domain>.ts` | Frozen -- touch-but-don't-grow |
| **Newer: by feature** | `features/<feature>/{components,composables,constants,routes.ts,services.ts,types.ts,views}/` | Active -- new code goes here |

**The migration from legacy to feature is in stasis.** The rules:

1. **New features** go in `features/<feature>/`. No exceptions.
2. **Bug fixes in legacy code** happen in place. Don't extract to `features/` as part of a bug fix.
3. **Don't complete the migration during restoration.** The migration is a structural change that should happen either as a dedicated project or as part of the rewrite decision. Piecemeal extraction during bug fixes creates a third organizational pattern (partially migrated) that's worse than either extreme.
4. **Don't regress.** Don't add new files to `components/Layout/<Feature>/` or `router/<domain>.ts`.

Feature folders carry their own `services.ts` which bypasses the central `src/services/endpoints/` registry. This means the central endpoint registry is incomplete -- it covers legacy domains only. Anyone mapping FE-to-backend calls must also walk `features/*/services.ts`.

## 4. Pinia stores

All stores use **setup function syntax** (Pinia >= 2.x):

```ts
export const useFooStore = defineStore('foo', () => {
  // State: reactive refs, persisted via useStorage
  const items = useStorage('items', null, undefined, {
    serializer: StorageSerializers.object,
  })

  // Getters: computed
  const activeItems = computed(() =>
    items.value?.filter((i) => i.active) ?? []
  )

  // Actions: async functions
  const fetchItems = async () => {
    items.value = await fooApi.getItems()
  }

  // MANDATORY: resetStore nulls every field
  const resetStore = () => {
    items.value = null
  }

  return { items, activeItems, fetchItems, resetStore }
})
```

**Rules:**

- **`useStorage` with `StorageSerializers.object`** when the initial value is `null`. Without the serializer, `useStorage` defaults to string serialization and silently corrupts objects on round-trip. The third arg (`undefined`) is the storage target (defaults to localStorage).
- **Every store exposes `resetStore()`** that nulls every field. This is the convention for the logout fan-out.
- **Register in `resetAllStores()`** (`src/store/auth.ts`). If you add a store and don't register it, that store's data survives logout and leaks into the next session. There is no automatic registration -- this is convention-by-vigilance.
- **Feature stores** in `features/*/stores/` must also register. As of the current codebase, `features/plans/stores/` is NOT registered -- this is a known security gap.
- **Don't mutate store state from components.** Components call store actions; actions mutate state. The exception is simple boolean toggles where an action would add noise without value.

## 5. Route guards and meta keys

The global guard (`router.beforeEach` in `src/router/index.ts`) reads these meta keys:

| Meta key | Read by guard | Purpose |
|---|---|---|
| `requiresAuth` | Yes | If true, user must have a token; else redirect to `/login`. Set on `Admin` parent; all children inherit. |
| `title` | Yes (sets `document.title`) | i18n-resolved page title. |
| `mainRouteName` | No (layout reads it) | Sidebar/breadcrumb section name. |
| `permissionIdentifiers` | Yes | Array of `PermissionType`. User needs at least one. |
| `visibleEntityTypes` | Yes | Array of `AccountTypeId`. Current business's account type must be in the list. |
| `visibleAccountTypes` | **NO -- not read** | Same intent as `visibleEntityTypes` but used by newer feature routes. The guard does NOT check this key. |

**The `visibleAccountTypes` gap is a known bug** ([Vue Deviations SS4.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#42-router-guard-reads-visibleentitytypes-but-new-routes-set-visibleaccounttypes)). Routes setting only `visibleAccountTypes` are silently ungated on account type.

**Rules:**
- Use `visibleEntityTypes` (the legacy spelling) until the guard is updated. Adding `visibleAccountTypes` without extending the guard is a silent no-op.
- Don't introduce new meta keys without extending the guard in the same PR. An unread meta key is dead config that misleads the next reader.
- The guard checks in a specific order: 404 pass-through, auth check, authed-to-public bounce, business-data presence, entity-type gate, permission gate. Understand this sequence before modifying.

## 6. Error handling

**The rule:** never `try / catch / console.log(error)`. Either re-throw, or call `Sentry.captureException(error)`.

The axios response interceptor handles user-facing error presentation:
- 401 on auth-required routes -> toast + auto-logout
- Other 4xx/5xx -> normalize the error envelope + toast (unless `config.skipToastError`)

Component-level and composable-level code should not duplicate this:

```ts
// BAD -- swallows context, duplicates toast logic
try {
  await campaignApi.updateCampaign(id, payload)
} catch (error) {
  console.log(error)
  toast.error('Something went wrong')
}

// GOOD -- let interceptor handle the toast; capture for Sentry if needed
try {
  await campaignApi.updateCampaign(id, payload)
} catch (error) {
  Sentry.captureException(error)
  throw error  // or handle the specific recovery case
}

// ALSO GOOD -- if no recovery is needed, don't catch at all
await campaignApi.updateCampaign(id, payload)
// interceptor handles the error presentation
```

**`skipToastError`:** pass `{ skipToastError: true }` in the axios config when the caller needs to handle the error UI itself (e.g., inline form validation errors). The interceptor still logs to Sentry but suppresses the toast.

## 7. TypeScript discipline

Defers to [rule:typescript] for core rules. Vue-specific additions:

- **No `as Component` casts.** If TypeScript can't infer the component type, the import path or generic is wrong. Fix the type, don't cast.
- **Prefer narrowing over assertion.** `if (value !== null) { ... }` beats `value!.something`.
- **`strict: true` is the baseline.** The project's `tsconfig.app.json` enables it. Don't weaken it.
- **`noUncheckedIndexedAccess: true` is recommended** but not currently enabled. When accessing array elements or record keys by index, treat the result as potentially undefined.
- **`@ts-ignore` / `@ts-expect-error`** are allowed by ESLint config (the rule is disabled). Use `@ts-expect-error` with a comment explaining why, not `@ts-ignore` (which suppresses silently and survives after the error is fixed).

## 8. Restoration overrides

These are known deviations that are explicitly sanctioned during triage. Don't fix them as drive-by work; each has a coupling or sequencing constraint.

| Override | Vue Deviations ref | Why not now |
|---|---|---|
| Don't migrate `components/Layout/` to `features/` | [SS1.1](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#11-five-months-since-last-commit-on-this-repo) | Migration is a structural change; belongs in rewrite decision, not restoration |
| Don't rename `visibleEntityTypes` to `visibleAccountTypes` | [SS4.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#42-router-guard-reads-visibleentitytypes-but-new-routes-set-visibleaccounttypes) | Touch only the side the guard reads; full rename is a separate PR |
| Don't add refresh-rotation to axios interceptor | [SS5.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#52-refresh-tokens-issued-by-backend-are-ignored-by-fe) | Must ship with backend JWT lifetime reduction; standalone FE change is dead code |
| Don't fix `tracePropagationTargets` placeholder alone | [SS3.2](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#32-tracepropagationtargets-still-set-to-sentry-quickstart-placeholder) | Coordinate with backend observability consolidation |
| Don't remove dead deps (Stripe, etc.) | [SS7.1](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#71-stripestripe-js-listed-in-packagejson-but-never-imported) | Low-risk but belongs in a dedicated cleanup PR, not mixed with feature work |
| Don't unify the two permission constant catalogues | [SS4.3](https://github.com/pour-now/business-admin/wiki/Vue-Deviations#43-two-parallel-permission-constant-catalogues) | Both resolve to the same backend strings; unification is cosmetic during triage |

**When overrides lift:** these freeze when the team picks a path (continue `business-admin` vs resume `admin-business`). Until then, treat the FE as inherited code under the dormant-maintainer model (see `pour-now-triage`).

## 9. Anti-patterns

| Smell | Why | Fix |
|---|---|---|
| Options API (`data()`, `methods:`, `computed:`) | Dead pattern; Composition API is the standard | Rewrite with `<script setup>` |
| Business logic in `<template>` | Untestable, unreadable | Move to composable or computed |
| Mutating store state from components | Breaks the action-mutation contract | Call a store action instead |
| `watch` overuse (the Vue parallel to signals) | Hides control flow; creates implicit dependencies | Prefer `computed` for derived state; use `watch` only for side effects (API calls, DOM manipulation) |
| Inline `api.get('/some/url/')` in components | Bypasses the three-layer pattern (endpoints/calls/store) | Add to `services.ts` (feature) or `services/{endpoints,calls}/` (legacy) |
| `ref<any>()` | Defeats TypeScript | Provide the type: `ref<Campaign | null>(null)` |
| Catching errors just to `console.log` | Swallows context; duplicates interceptor | Let interceptor handle, or `Sentry.captureException` |
| New meta key without guard extension | Dead config that misleads readers | Extend guard in same PR |
| Store without `resetStore()` | Data leaks across logout | Add `resetStore()` and register in `resetAllStores()` |
| `reactive()` for top-level state | Loses reactivity on destructure; `ref` is explicit | Use `ref()` for top-level; `reactive()` for nested objects if needed |

## Attribution Policy

See [rule:output]. NEVER include AI or agent attribution.
