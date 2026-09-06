---
description: Always-on React standards drawn from the React 19 docs and canonical community writing. Apply when writing or reviewing React components, hooks, or JSX/TSX.
---

# React Standards

Apply these principles to all React code (`.jsx`, `.tsx`, and `.js`/`.ts` files that import from `react`). Layers on top of `[rule:typescript]` when the file is TypeScript.

## Components

- Use function components; do not write new class components. Class-only APIs (`getSnapshotBeforeUpdate`, `componentDidCatch` on non-boundary classes) are the only exceptions
- Component names are `PascalCase`; hooks are `useCamelCase`; event handlers are `handleX` on the component and `onX` on the prop
- One component per file for exported components; internal helper components may share a file when only used there
- Props are typed as an explicit `interface` or `type` -- never `React.FC` (it hides `children` typing and adds an implicit return type)
- Never mutate props or state -- always return a new object/array from setters and reducers

## Hooks

- Call hooks at the top level only -- never inside conditions, loops, or nested functions; enforced by `eslint-plugin-react-hooks/rules-of-hooks`
- Declare every reactive value read inside an effect or memo in its dependency array; enforced by `eslint-plugin-react-hooks/exhaustive-deps` -- do not disable the rule at call sites
- Custom hooks start with `use` and follow the same rules as built-in hooks; a helper that does not call hooks is a plain function, not a hook
- Extract complex `useState` chains into `useReducer` when the next state depends on multiple prior fields

## Effects

- Do not use `useEffect` for logic that can be derived during render, computed in an event handler, or lifted to a parent. Effects are for synchronizing with external systems (subscriptions, non-React widgets, network in legacy code)
- Every effect that acquires a resource returns a cleanup function; every subscription unsubscribes; every timer is cleared
- Effects that fetch data must either be replaced by a framework data loader (Next.js, Remix, React Query, RSC) or handle race conditions with an `AbortController` or ignore-flag pattern -- unguarded fetch-in-effect is a bug
- Do not chain effects that set state to trigger other effects; compute the derived value in one place

## Server components and data (React 19+)

- Server Components are the default in RSC-capable frameworks; add `"use client"` only when the file needs state, effects, browser APIs, or event handlers
- Do not import server-only modules (`fs`, database clients, secrets) into a file that may be reached by a client component; enforce with `server-only` / `client-only` marker packages
- Prefer server actions (`"use server"` functions) over client-side POST-then-refetch for form submission
- The `use()` hook unwraps promises and context in render; only call it inside components or other hooks, and only with stable promise references

## State management

- `useState` for local component state; `useReducer` for state with multiple related transitions; `useContext` for cross-cutting concerns that do not change often (theme, auth user)
- Do not use Context as a general state store -- every consumer re-renders on any change. For frequently-updated shared state, reach for an external store (Zustand, Jotai, Redux Toolkit); the shelf takes no position on which
- Colocate state as close to where it is used as possible; lift only when a second consumer appears
- Server state (API data, cache, mutations) belongs in a data-fetching library (React Query, SWR, RTK Query, RSC), not in `useState` + `useEffect`

## Performance

- Do not wrap components in `memo`, values in `useMemo`, or callbacks in `useCallback` by default. Add them only when a profiler measurement shows the render or the referential-identity churn is a bottleneck
- Split large lists with virtualization (`react-window`, `@tanstack/react-virtual`) at ~200 rows, not before
- Use `key` on every list item, and use a stable identifier -- never the array index unless the list is append-only and immutable
- Suspense boundaries scope loading UI and streaming; place them at the granularity users perceive as one unit, not per-component

## Error handling

- Every route or major feature is wrapped in an Error Boundary that logs to the observability system and renders a fallback -- unhandled errors in render must not blank the page
- Use `react-error-boundary` (or equivalent) with an explicit `resetKeys` so users can retry without a full reload
- Do not `try/catch` inside render; let the boundary catch it. `try/catch` is appropriate inside event handlers and effects

## Accessibility

- Use semantic HTML elements (`button`, `nav`, `main`, `label`, `dialog`) before reaching for `<div role="...">`. ARIA is a repair layer, not a first tool
- Every interactive element is keyboard-reachable and has a visible focus indicator; do not set `outline: none` without a replacement
- Every form input has an associated `<label>` (via `htmlFor` or wrapping) -- placeholder text is not a label
- Images have `alt` text; decorative images use `alt=""`. Icons that convey meaning have an accessible name (`aria-label` or visually-hidden text)
- Test with keyboard-only navigation and a screen reader (VoiceOver on macOS, NVDA on Windows) at least once before merging a new interactive component
- Enable `eslint-plugin-jsx-a11y` (recommended preset) as the mechanical pairing for the above bullets. Per `[rule:writing-rules]` writing-rules:1, accessibility discipline that depends on reviewer vigilance decays; the lint layer catches missing `alt`, missing labels, `outline: none` without replacement, non-interactive elements with click handlers, and role/aria mismatches at commit time

## Forms

- Prefer uncontrolled inputs with `FormData` and server actions for simple forms; reach for controlled inputs when you need per-keystroke validation or cross-field derivation
- Use `useOptimistic` for user-facing latency reduction on mutations that usually succeed; always reconcile with the server result
- Never disable a submit button without also communicating why (spinner, message) -- silent disable looks like a broken app

## Testing

- Use React Testing Library; query by accessible role and name (`getByRole('button', { name: /submit/i })`) before `getByTestId`. `data-testid` is an escape hatch, not the default
- Test behavior, not implementation -- assert what the user sees and can do, not which hooks fired or which props were passed
- Do not test styles, DOM structure, or component internal state directly; those are refactor-hostile
- Mock at the network layer (`msw`) rather than mocking hook return values; the mock survives refactors that move logic between hooks

## TypeScript interop

This section layers on top of `[rule:typescript]` -- the TypeScript rules there (strict-null-checks, no `any`, avoid non-null assertion, prefer union over enums for finite sets) apply unchanged; the bullets below are React-specific additions where the base TS rules under-specify.

- Prefer `type` for component props; use `interface` when the prop shape is genuinely extensible by third parties
- Type children explicitly: `children: React.ReactNode` -- do not rely on `React.FC` to inject it
- Event handlers use the specific React event type (`React.ChangeEvent<HTMLInputElement>`, `React.FormEvent<HTMLFormElement>`), not `any` or `Event`
- Component `ref` uses `React.Ref<T>` in React 19 (no `forwardRef` needed for new code); legacy code using `forwardRef` is fine until touched

## Areas the shelf takes no position on

The following remain actively debated in 2026; project convention decides:

- **Signals vs hooks.** Preact Signals, `@preact/signals-react`, and TC39 signals proposals compete with the hooks model. React 19 does not ship signals; frameworks may add them
- **CSS approach.** Tailwind, CSS Modules, vanilla-extract, styled-components, and Panda CSS all have advocates. The React docs take no position and neither does this shelf
- **State library.** Redux Toolkit, Zustand, Jotai, Valtio, XState, and MobX are all in active use. Pick per-project based on the state graph shape
- **Meta-framework.** Next.js, Remix, TanStack Start, and RedwoodJS have different data-loading models. RSC vs router-loader vs client-fetch is a framework choice
- **Testing runner.** Vitest and Jest are both current. React Testing Library sits above both

For each of these, document the project's choice in `README.md` or `docs/architecture.md`; do not invent a shelf-wide rule.

---

## Attribution

Principles distilled from the [React docs](https://react.dev) (react.dev/reference/react, react.dev/learn), [Dan Abramov's blog](https://overreacted.io), [Kent C. Dodds' blog](https://kentcdodds.com/blog), [Josh W. Comeau's blog](https://www.joshwcomeau.com), and the [Testing Library docs](https://testing-library.com/docs/react-testing-library/intro/). All sources are public and freely licensed.
