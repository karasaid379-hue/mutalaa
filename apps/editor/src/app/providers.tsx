import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import type { Api } from '@/api/client';
import { Toaster } from '@/components/ui/toast';
import { AnnounceProvider } from './announce-provider';
import { ApiContext } from './api-context';

/** Everything the screens need outside the router: API, query cache, live region and toasts (browser and tests). */
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
        <AnnounceProvider>
          <Toaster>{children}</Toaster>
        </AnnounceProvider>
      </QueryClientProvider>
    </ApiContext>
  );
}
