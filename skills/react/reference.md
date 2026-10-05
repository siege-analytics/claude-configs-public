# React Reference Recipes

Load when the [SKILL.md](SKILL.md) decision tree points here for a specific recipe. Companion to `[`react`](../_react-rules.md)` and `[`typescript`](../_typescript-rules.md)`.

## Data fetching

### Server component (RSC-capable framework)

```tsx
// app/donors/page.tsx -- server component, no "use client"
import { db } from '@/lib/db';

export default async function DonorsPage() {
  const donors = await db.donor.findMany();
  return (
    <ul>
      {donors.map(d => <li key={d.id}>{d.name}</li>)}
    </ul>
  );
}
```

### Client component with React Query

```tsx
'use client';
import { useQuery } from '@tanstack/react-query';

export function DonorList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['donors'],
    queryFn: () => fetch('/api/donors').then(r => r.json()),
  });

  if (isLoading) return <Spinner />;
  if (error) throw error;  // let error boundary handle
  return <ul>{data.map(d => <li key={d.id}>{d.name}</li>)}</ul>;
}
```

### Effect-based fetch (legacy or non-framework)

Only when a data-fetching library is genuinely unavailable:

```tsx
'use client';
import { useEffect, useState } from 'react';

export function DonorList() {
  const [donors, setDonors] = useState<Donor[] | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch('/api/donors', { signal: ctrl.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error(r.statusText)))
      .then(setDonors)
      .catch(err => { if (err.name !== 'AbortError') setError(err); });
    return () => ctrl.abort();
  }, []);

  if (error) throw error;
  if (!donors) return <Spinner />;
  return <ul>{donors.map(d => <li key={d.id}>{d.name}</li>)}</ul>;
}
```

## Forms

### Server action with useOptimistic (React 19+)

```tsx
'use client';
import { useOptimistic } from 'react';
import { updateDonor } from './actions';

export function EditDonor({ donor }: { donor: Donor }) {
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

```ts
// actions.ts
'use server';
import { db } from '@/lib/db';
import { revalidatePath } from 'next/cache';

export async function updateDonor(donor: Donor) {
  await db.donor.update({ where: { id: donor.id }, data: donor });
  revalidatePath('/donors');
}
```

### Controlled form with per-keystroke validation

```tsx
'use client';
import { useState } from 'react';

export function DonationForm() {
  const [amount, setAmount] = useState('');
  const parsed = Number(amount);
  const error = amount && (Number.isNaN(parsed) || parsed <= 0)
    ? 'Amount must be a positive number'
    : null;

  return (
    <form>
      <label htmlFor="amount">Amount</label>
      <input
        id="amount"
        value={amount}
        onChange={e => setAmount(e.target.value)}
        aria-invalid={!!error}
        aria-describedby={error ? 'amount-error' : undefined}
      />
      {error && <div id="amount-error" role="alert">{error}</div>}
    </form>
  );
}
```

## Error boundaries

### Route-level boundary with reset

```tsx
'use client';
import { ErrorBoundary } from 'react-error-boundary';
import { Suspense } from 'react';

function Fallback({ error, resetErrorBoundary }: { error: Error; resetErrorBoundary: () => void }) {
  return (
    <div role="alert">
      <p>Something went wrong loading donors.</p>
      <pre>{error.message}</pre>
      <button type="button" onClick={resetErrorBoundary}>Try again</button>
    </div>
  );
}

export function DonorRoute({ filter }: { filter: string }) {
  return (
    <ErrorBoundary
      FallbackComponent={Fallback}
      resetKeys={[filter]}
      onError={(err, info) => logger.error('donor-route', { err, info })}
    >
      <Suspense fallback={<Spinner />}>
        <DonorList filter={filter} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

## Testing

### Setup (Vitest + Testing Library + MSW)

```ts
// vitest.setup.ts
import '@testing-library/jest-dom/vitest';
import { server } from './mocks/server';
import { beforeAll, afterEach, afterAll } from 'vitest';

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

```ts
// mocks/handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/donors', () =>
    HttpResponse.json([{ id: 'd1', name: 'Ada' }])
  ),
];
```

### Behavior test

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DonorList } from './DonorList';

test('renders donors from the API', async () => {
  render(<DonorList />);
  expect(await screen.findByRole('listitem', { name: /ada/i })).toBeInTheDocument();
});

test('clicking a donor calls onSelect', async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();
  render(<DonorCard donor={{ id: 'd1', name: 'Ada' }} onSelect={onSelect} />);

  await user.click(screen.getByRole('button', { name: /ada/i }));

  expect(onSelect).toHaveBeenCalledWith('d1');
});
```

### Testing a hook

```tsx
import { renderHook, act } from '@testing-library/react';
import { useCounter } from './useCounter';

test('increment advances the count by one', () => {
  const { result } = renderHook(() => useCounter(0));
  act(() => result.current.increment());
  expect(result.current.count).toBe(1);
});
```

## State patterns

### useReducer for multi-field transitions

```tsx
type State = { status: 'idle' | 'loading' | 'success' | 'error'; data?: Donor[]; error?: Error };
type Action =
  | { type: 'load' }
  | { type: 'success'; data: Donor[] }
  | { type: 'error'; error: Error };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'load':    return { status: 'loading' };
    case 'success': return { status: 'success', data: action.data };
    case 'error':   return { status: 'error', error: action.error };
  }
}
```

### Zustand store (when Context re-render cost bites)

```ts
import { create } from 'zustand';

interface FilterStore {
  query: string;
  setQuery: (q: string) => void;
}

export const useFilterStore = create<FilterStore>((set) => ({
  query: '',
  setQuery: (query) => set({ query }),
}));

// Component -- only re-renders when `query` changes
function SearchBox() {
  const query = useFilterStore(s => s.query);
  const setQuery = useFilterStore(s => s.setQuery);
  return <input value={query} onChange={e => setQuery(e.target.value)} />;
}
```

## Suspense granularity

Wrap Suspense at the level users perceive as one loading unit:

```tsx
// GOOD -- users see one loader for the page, then rows stream in
<Suspense fallback={<PageSpinner />}>
  <Header />
  <Suspense fallback={<TableSkeleton />}>
    <DonorTable />
  </Suspense>
  <Footer />
</Suspense>

// BAD -- one loader per row is visual noise
{donors.map(d => (
  <Suspense key={d.id} fallback={<Row skeleton />}>
    <DonorRow donor={d} />
  </Suspense>
))}
```
