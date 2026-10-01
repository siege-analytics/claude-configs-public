---
name: vue
description: "Vue 3 conventions for Composition API, Pinia stores, and route guards. TRIGGER: *.vue, *.ts importing from vue/pinia/vue-router, or touching route/store/composable files. Stacks with api-integration."
routed-by: coding-standards
user-invocable: false
paths: "**/*.vue,**/*.ts,**/router/**,**/store/**,**/features/**"
---

# Vue 3

## Companion shelves

For cross-boundary contract rules:
- [`api-integration`](../api-integration/SKILL.md) -- FE-backend contract (error envelope, JWT, multi-tenant headers).

For general TypeScript discipline:
- [`typescript`](../_typescript-rules.md) -- strictNullChecks, noUncheckedIndexedAccess, no ts-ignore without explanation.

Apply when editing `.vue` files, Pinia stores, route definitions, or composables. Draws from:
- Vue Style Guide (vuejs.org/style-guide) -- Priority A (Essential) and B (Strongly Recommended) rules
- Pinia docs (pinia.vuejs.org) -- setup-store syntax
- VueUse (vueuse.org) -- useStorage, utility composables

## 1. Decision tree

```
START: I'm touching Vue/FE code
  |
  +-- Where does this code live?
  |   Determine the codebase's organizational convention first (by-layer vs by-feature)
  |   and follow it. New components go alongside their peers. Shared primitives stay
  |   in the shared dir. Don't introduce a new organizational pattern as a side effect.
  |
  +-- What am I building?
  |   +-- A Pinia store  --> setup syntax, resetStore(), register in logout hierarchy
  |   +-- A route  --> meta keys must be read by the guard (section 4)
  |   +-- A composable  --> Composition API only, typed return
  |   +-- A component  --> <script setup lang="ts">, props via defineProps<>()
  |
  +-- Am I touching the global guard (router/index.ts)?
      +-- YES  --> read section 4 first; the guard has specific sequencing rules
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

**Auto-imports.** If the project uses `unplugin-auto-import` (typically configured for `vue`, `vue-router`, and `pinia`), respect it -- don't add explicit imports for auto-imported symbols. The tradeoff (invisible provenance) is accepted as part of the convention. If you don't see an `unplugin-auto-import` config, write explicit imports.

## 3. Pinia stores

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
- **Register in the project's logout fan-out** (typically a `resetAllStores()` in the auth store). If you add a store and don't register it, that store's data survives logout and leaks into the next session. There is no automatic registration -- this is convention-by-vigilance.
- **Stores in alternate locations** (e.g., `features/*/stores/`) must also register. An unregistered store is a security gap; treat it as a bug.
- **Don't mutate store state from components.** Components call store actions; actions mutate state. The exception is simple boolean toggles where an action would add noise without value.

## 4. Route guards and meta keys

The global guard (`router.beforeEach` in `src/router/index.ts`) reads a project-defined set of `route.meta` keys (typically `requiresAuth`, `title`, permission/role keys, tenant-scope keys). Before touching routes, inventory what the guard actually reads.

**Rules:**

- **An unread meta key is dead config.** Don't set a meta key on a route unless the guard (or a layout component you can name) reads it. Drift between "meta keys set on routes" and "meta keys checked by the guard" is a class of silent permission bug.
- **Don't introduce a new meta key without extending the guard in the same PR.** Two-PR splits leave a window where routes ship that nobody enforces.
- **Pre-existing key/value mismatches are real bugs, not just style.** If the guard reads `visibleEntityTypes` and newer routes set `visibleAccountTypes`, those newer routes are silently ungated. Fix the contract; don't paper over it.
- **Understand the guard's check ordering before modifying it.** A typical sequence is: 404 pass-through → auth check → authed-to-public bounce → tenant/business-scope check → entity/account-type gate → permission gate. Reordering these can silently change semantics for edge-case routes.

## 5. Error handling

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

## 6. TypeScript discipline

Defers to [`typescript`](../_typescript-rules.md) for core rules. Vue-specific additions:

- **No `as Component` casts.** If TypeScript can't infer the component type, the import path or generic is wrong. Fix the type, don't cast.
- **Prefer narrowing over assertion.** `if (value !== null) { ... }` beats `value!.something`.
- **`strict: true` is the baseline.** Don't weaken it without explicit team agreement and a record of what's being relaxed and why.
- **`noUncheckedIndexedAccess: true` is recommended.** When accessing array elements or record keys by index, treat the result as potentially undefined.
- **`@ts-expect-error` over `@ts-ignore`.** Use `@ts-expect-error` with a comment explaining why; `@ts-ignore` suppresses silently and survives after the underlying error is fixed.

## 7. Anti-patterns

| Smell | Why | Fix |
|---|---|---|
| Options API (`data()`, `methods:`, `computed:`) | Dead pattern; Composition API is the standard | Rewrite with `<script setup>` |
| Business logic in `<template>` | Untestable, unreadable | Move to composable or computed |
| Mutating store state from components | Breaks the action-mutation contract | Call a store action instead |
| `watch` overuse (the Vue parallel to signals) | Hides control flow; creates implicit dependencies | Prefer `computed` for derived state; use `watch` only for side effects (API calls, DOM manipulation) |
| Inline `api.get('/some/url/')` in components | Bypasses the project's API client layer | Route through the project's services / store / API client layer |
| `ref<any>()` | Defeats TypeScript | Provide the type: `ref<Campaign | null>(null)` |
| Catching errors just to `console.log` | Swallows context; duplicates interceptor | Let interceptor handle, or `Sentry.captureException` |
| New meta key without guard extension | Dead config that misleads readers | Extend guard in same PR |
| Store without `resetStore()` | Data leaks across logout | Add `resetStore()` and register in the logout fan-out |
| `reactive()` for top-level state | Loses reactivity on destructure; `ref` is explicit | Use `ref()` for top-level; `reactive()` for nested objects if needed |

## Attribution Policy

See [`output`](../_output-rules.md). NEVER include AI or agent attribution.
