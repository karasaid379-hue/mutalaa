import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Api } from '@/api/client';
import { AnnounceProvider } from './announce-provider';
import { ApiContext } from './api-context';

// The shadcn `Toaster` (components/ui/toast.tsx) is not mounted: no code raises a toast, and an empty toast
// region would be a second live region next to the announcer. Mount it here when the first toast is needed.
/** Everything the screens need outside the router: API, query cache, live region (browser and tests). */
export function AppProviders({
  api,
  queryClient,
  children,
}: {
  api: Api;
  queryClient: QueryClient;
  children: ReactNode;
}) {
  return (
    <ApiContext value={api}>
      <QueryClientProvider client={queryClient}>
        <AnnounceProvider>{children}</AnnounceProvider>
      </QueryClientProvider>
    </ApiContext>
  );
}
