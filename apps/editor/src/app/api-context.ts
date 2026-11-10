import { createContext, useContext } from 'react';
import type { Api } from '@/api/client';

/** The API instance built in main.tsx (a fake-fetch instance in tests). */
export const ApiContext = createContext<Api | null>(null);

/** The API instance of the nearest provider (`api.$api.useQuery`, `api.client.GET`). */
export function useApi(): Api {
  const api = useContext(ApiContext);
  if (!api) throw new Error('ApiContext is missing: wrap the tree in AppProviders.');
  return api;
}
