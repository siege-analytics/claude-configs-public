---
name: react
description: "React conventions for components, hooks, effects, server components, forms, and testing. TRIGGER: *.jsx/*.tsx files, *.js/*.ts importing from 'react', writing a component/hook/server action, or configuring an error boundary. Layers on top of typescript."
routed-by: coding-standards
user-invocable: false
paths: "**/*.jsx,**/*.tsx"
---

# React

## Companion shelves

Always-on: [`react`](../_react-rules.md), [`typescript`](../_typescript-rules.md), [`principles`](../_principles-rules.md).

For deeper rationale load:
- [`shelves--clean-code`](../shelves/engineering-principles/clean-code/SKILL.md) -- naming, function size, error handling.
- [`testing-frameworks`](../testing-frameworks/SKILL.md) -- which test runner and library the project declared.

Apply when editing code that imports from `react`. See [reference.md](reference.md) for recipes (data fetching, form patterns, error-boundary composition, testing patterns, RSC / client boundary).

Draws from:
- [React docs](https://react.dev) -- canonical since React 19
- Dan Abramov -- [overreacted.io](https://overreacted.io) (effects, closures, mental model)
- Kent C. Dodds -- [kentcdodds.com/blog](https://kentcdodds.com/blog) (component composition, testing philosophy)
- Josh W. Comeau -- [joshwcomeau.com](https://www.joshwcomeau.com) (rendering behavior, CSS-in-React)
- [Testing Library docs](https://testing-library.com/docs/react-testing-library/intro/) (test behavior, not implementation)

## Decision tree

```
START: I'm writing React code
  │
  ├─ What am I building?
  │   ├─ A component → function component with typed props; PascalCase name
  │   ├─ A hook → useX name; obeys rules-of-hooks; if it doesn't call hooks, it's a function not a hook
  │   ├─ A server component → RSC by default in RSC-capable frameworks; add "use client" only when needed
  │   ├─ A form → prefer uncontrolled + FormData + server action; controlled only when per-keystroke logic is needed
  │   ├─ A data fetch → framework loader (RSC, Next.js loader, React Query, SWR); NOT useEffect + fetch
  │   └─ A test → React Testing Library; query by role and name; mock at network layer (msw)
  │
  ├─ Am I reaching for useEffect?
  │   ├─ Can it be derived during render? → derive it, no effect
  │   ├─ Should it run in an event handler? → put it there, no effect
  │   ├─ Is the parent the right owner? → lift it, no effect
  │   └─ Am I synchronizing with an external system (subscription, non-React widget, legacy fetch)? → effect is correct
  │
  ├─ Am I reaching for memo / useMemo / useCallback?
  │   ├─ Did the profiler show a bottleneck? → yes, add it
  │   └─ No measurement? → don't add it; it's noise
  │
  └─ Am I about to disable exhaustive-deps?
      └─ Stop. Fix the underlying dependency shape (move to reducer, extract event handler, or lift state) instead of muting the linter
```

## Component shape

```tsx
// GOOD -- function component, typed props, one export per file
interface DonorCardProps {
  donor: Donor;
  onSelect: (id: string) => void;
}

export function DonorCard({ donor, onSelect }: DonorCardProps) {
  return (
    <button type="button" onClick={() => onSelect(donor.id)}>
      {donor.name}
    </button>
  );
}
```

**Rules:**

- Explicit `interface` for props; never `React.FC`
- Event handler names: `onSelect` on the prop; `handleSelect` inside the component when it wraps logic
- One exported component per file; internal helpers stay in the same file
- `type="button"` on every `<button>` unless it's genuinely a form submit -- default `type="submit"` inside forms causes bugs

## Effects -- what they're actually for

An effect synchronizes React with an external system. If the "external system" is React itself (parent state, derived data, another effect), the effect is wrong.

```tsx
// BAD -- deriving state in an effect
function Cart({ items }: { items: Item[] }) {
  const [total, setTotal] = useState(0);
  useEffect(() => {
    setTotal(items.reduce((sum, i) => sum + i.price, 0));
  }, [items]);
  return <div>{total}</div>;
}

// GOOD -- derived during render
function Cart({ items }: { items: Item[] }) {
  const total = items.reduce((sum, i) => sum + i.price, 0);
  return <div>{total}</div>;
}
```

```tsx
// BAD -- unguarded fetch, race condition on prop change
function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    fetch(`/api/users/${userId}`).then(r => r.json()).then(setUser);
  }, [userId]);
  // ...
}

// GOOD -- AbortController guards against stale responses
function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    fetch(`/api/users/${userId}`, { signal: ctrl.signal })
      .then(r => r.json())
      .then(setUser)
      .catch(err => { if (err.name !== 'AbortError') throw err; });
    return () => ctrl.abort();
  }, [userId]);
  // ...
}

// BETTER -- delegate to a data-fetching library
function UserProfile({ userId }: { userId: string }) {
  const { data: user } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetch(`/api/users/${userId}`).then(r => r.json()),
  });
  // ...
}
```

## Server components and the client boundary

In RSC-capable frameworks (Next.js App Router, Remix vNext, TanStack Start):

- **Server component (default):** may `await` async data, read the filesystem, query the database. Cannot use state, effects, or event handlers
- **Client component (`"use client"` at top of file):** may use state, effects, event handlers, browser APIs. Cannot import server-only modules
- **Server action (`"use server"` function):** runs on the server; callable from a client component (usually as a form action)

Rules:

- Add `"use client"` at the smallest scope that needs it -- keep leaves client, keep trees server
- Never import a server-only module (`fs`, database client, secret) into a client component. Use the `server-only` package to fail the build if the boundary is crossed
- Server actions receive `FormData`, not JSON. Validate the input; don't trust it

## State management

| Scope | Tool |
|---|---|
| One component's local state | `useState` |
| One component with multi-field transitions | `useReducer` |
| Cross-component but change-rare (theme, locale, auth user) | `useContext` |
| Cross-component and change-frequent | External store (Zustand, Jotai, Redux Toolkit) -- shelf takes no position on which |
| Server data (API responses, cache, mutations) | React Query, SWR, RTK Query, or RSC loader -- not `useState` + `useEffect` |
| URL-derived state (filters, tab selection) | Router (`useSearchParams`, framework loader) -- not local state |

## Forms

```tsx
// GOOD (React 19+) -- uncontrolled + server action + useOptimistic
import { useOptimistic } from 'react';
import { updateDonor } from './actions';

export function DonorForm({ donor }: { donor: Donor }) {
  const [optimistic, setOptimistic] = useOptimistic(donor);

  async function action(formData: FormData) {
    const next = { ...donor, name: String(formData.get('name')) };
    setOptimistic(next);
    await updateDonor(next);
  }

  return (
    <form action={action}>
      <label htmlFor="name">Name</label>
      <input id="name" name="name" defaultValue={optimistic.name} />
      <button type="submit">Save</button>
    </form>
  );
}
```

Controlled inputs (`value` + `onChange` on every keystroke) are for cases where you actually need per-keystroke logic: live validation, cross-field derivation, masked inputs.

## Error boundaries

```tsx
// Every route wraps its content in a boundary
import { ErrorBoundary } from 'react-error-boundary';

export function DonorRoute() {
  return (
    <ErrorBoundary
      FallbackComponent={ErrorFallback}
      resetKeys={[/* deps that should reset the boundary */]}
      onError={(err) => logger.error('donor-route', err)}
    >
      <Suspense fallback={<Spinner />}>
        <DonorList />
      </Suspense>
    </ErrorBoundary>
  );
}
```

Rules:

- Every route or major feature has a boundary. Unhandled errors must not blank the page
- `onError` sends to the observability system, not `console.error` alone
- `resetKeys` lets users retry without a full reload

## Testing

```tsx
// GOOD -- query by role and name; assert user-visible behavior
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('selecting a donor calls onSelect with the donor id', async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  render(<DonorCard donor={{ id: 'd1', name: 'Ada' }} onSelect={onSelect} />);

  await user.click(screen.getByRole('button', { name: /ada/i }));

  expect(onSelect).toHaveBeenCalledWith('d1');
});
```

Rules:

- Query by role + accessible name before `getByTestId`
- Test what a user sees and can do; do not test internal state or which hooks fired
- Mock at the network layer with MSW; do not mock hook return values
- One assertion per behavior, not per method call

## Anti-patterns

| Smell | Why | Fix |
|---|---|---|
| `useEffect` that only calls `setState` from `props` | Derived state in the wrong place | Compute during render |
| `useEffect` chain where one effect's setState triggers the next | Invisible control flow | Compute the derived value once |
| `React.FC<Props>` on component declarations | Hides children typing, implicit return type | Explicit `interface` for props |
| `memo` / `useMemo` / `useCallback` without profiler evidence | Adds noise, breaks equality reasoning | Remove until measured to matter |
| `<div onClick={...}>` for something that acts like a button | Not keyboard-reachable, no role | `<button type="button">` |
| Placeholder text used as label | Screen readers announce nothing when focused | `<label htmlFor="x">` |
| `getByTestId` as first-line query | Ties tests to internal markup | `getByRole` with accessible name |
| Fetch-in-effect without cleanup or AbortController | Race conditions on prop change | Data-fetching library or AbortController |
| Context used for frequently-changing state | Every consumer re-renders on any change | External store (Zustand, Jotai, Redux) |
| `// eslint-disable-next-line react-hooks/exhaustive-deps` | Muting the linter that catches the bug | Restructure state or use a ref for values that shouldn't retrigger |
| `try/catch` inside a component's render body | Boundary is the right layer | Wrap in `<ErrorBoundary>` |
| Array index as `key` on a reorderable list | Breaks identity across reorder | Stable id from the data |

## References

- [React docs](https://react.dev) -- always the newest source of truth
- Dan Abramov -- [overreacted.io](https://overreacted.io) (mental model, especially effects and closures)
- Kent C. Dodds -- [kentcdodds.com/blog](https://kentcdodds.com/blog) (component composition, testing philosophy)
- Josh W. Comeau -- [joshwcomeau.com](https://www.joshwcomeau.com) (rendering behavior, CSS-in-React)
- [Testing Library docs](https://testing-library.com/docs/react-testing-library/intro/)
- Ryan Florence and Michael Jackson (Remix / React Router docs) -- data-loading patterns

## Attribution Policy

See [`output`](../_output-rules.md). NEVER include AI or agent attribution.
