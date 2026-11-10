import createFetchClient from 'openapi-fetch';
import createClient from 'openapi-react-query';
import type { paths } from './schema';

export interface ApiOptions {
  /** '' in the browser (same origin, Vite proxy or nginx); an absolute URL in tests. */
  baseUrl: string;
  /** Test seam: a fake fetch. */
  fetch?: typeof globalThis.fetch;
}

/** The only place that builds the API client; the instance is created in main.tsx (and in tests). */
export function createApi({ baseUrl, fetch }: ApiOptions) {
  const client = createFetchClient<paths>({ baseUrl, ...(fetch ? { fetch } : {}) });
  return { client, $api: createClient(client) };
}

export type Api = ReturnType<typeof createApi>;
