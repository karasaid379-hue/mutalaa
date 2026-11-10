// A15.2 smoke tests: the generated-client chain ($api.useQuery / useInfiniteQuery) works in jsdom with a fake
// fetch and an absolute base URL (a relative base cannot build a Request outside a browser).
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { useContext, type ReactNode } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { createApi } from '@/api/client';
import { ApiContext } from '@/app/api-context';

const BASE = 'http://panel.test';

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function setup(handler: (request: Request) => Response) {
  const calls: Request[] = [];
  const fetch = vi.fn((input: Request | string | URL) => {
    const request = input instanceof Request ? input : new Request(input);
    calls.push(request);
    return Promise.resolve(handler(request));
  });
  const api = createApi({ baseUrl: BASE, fetch: fetch as unknown as typeof globalThis.fetch });
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <ApiContext value={api}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ApiContext>
  );
  return { calls, wrapper };
}

function MeProbe() {
  const api = useContext(ApiContext);
  if (!api) throw new Error('no api');
  const { data, error, isPending } = api.$api.useQuery('get', '/api/v1/auth/me');
  if (isPending) return <p>pending</p>;
  if (error) return <p>error</p>;
  return <p data-testid="me">{JSON.stringify(data)}</p>;
}

function ListProbe({ initialPageParam }: { initialPageParam: null | undefined }) {
  const api = useContext(ApiContext);
  if (!api) throw new Error('no api');
  const { data, isPending } = api.$api.useInfiniteQuery(
    'get',
    '/api/v1/reviews',
    { params: { query: { limit: 50 } } },
    {
      initialPageParam,
      getNextPageParam: (last) => last.next_cursor ?? undefined,
    },
  );
  if (isPending) return <p>pending</p>;
  return <p data-testid="pages">{String(data?.pages.length)}</p>;
}

describe('openapi-react-query smoke', () => {
  it('useQuery GET goes through the fake fetch with an absolute URL', async () => {
    const { calls, wrapper } = setup(() => json({ probe: 'deneme' }));
    render(<MeProbe />, { wrapper });
    expect(await screen.findByTestId('me')).toHaveTextContent('{"probe":"deneme"}');
    expect(calls).toHaveLength(1);
    expect(calls[0]?.method).toBe('GET');
    expect(calls[0]?.url).toBe(`${BASE}/api/v1/auth/me`);
  });

  it('useInfiniteQuery: initialPageParam null keeps the first request free of a cursor', async () => {
    const { calls, wrapper } = setup(() => json({ items: [], next_cursor: null }));
    render(<ListProbe initialPageParam={null} />, { wrapper });
    expect(await screen.findByTestId('pages')).toHaveTextContent('1');
    const url = new URL(calls[0]?.url ?? '');
    expect(url.searchParams.get('limit')).toBe('50');
    expect(url.searchParams.has('cursor')).toBe(false);
  });

  it('useInfiniteQuery: initialPageParam undefined falls back to the library default 0 (cursor=0 is sent)', async () => {
    const { calls, wrapper } = setup(() => json({ items: [], next_cursor: null }));
    render(<ListProbe initialPageParam={undefined} />, { wrapper });
    expect(await screen.findByTestId('pages')).toHaveTextContent('1');
    expect(new URL(calls[0]?.url ?? '').searchParams.get('cursor')).toBe('0');
  });
});
