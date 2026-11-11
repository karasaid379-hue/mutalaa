import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';
import { problemStatus } from '@/lib/problem';

export type SessionSignal = 'unauthorized' | 'forbidden';

/**
 * Carries session signals from the query caches to the app shell. The shell subscribes
 * while it is mounted; with no shell (login page) a signal is dropped, which is what we want.
 */
export class SessionBridge {
  private handler: ((signal: SessionSignal) => void) | null = null;

  /** Registers the handler (the shell); returns the function that removes it again. */
  subscribe(handler: (signal: SessionSignal) => void): () => void {
    this.handler = handler;
    return () => {
      if (this.handler === handler) this.handler = null;
    };
  }

  emit(signal: SessionSignal): void {
    this.handler?.(signal);
  }
}

const ME_PATH = '/api/v1/auth/me';

export interface QueryClientOptions {
  /** Tests switch retries off. */
  retry?: boolean;
}

/**
 * The panel's QueryClient. 401 from any query or mutation signals `unauthorized` (the shell navigates to
 * the login page first and clears the cache afterwards); 403 on the session query signals `forbidden`.
 */
export function createQueryClient(
  bridge: SessionBridge,
  options: QueryClientOptions = {},
): QueryClient {
  const signal = (error: unknown, isSessionQuery: boolean) => {
    const status = problemStatus(error);
    if (status === 401) bridge.emit('unauthorized');
    else if (status === 403 && isSessionQuery) bridge.emit('forbidden');
  };
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => signal(error, query.queryKey[1] === ME_PATH),
    }),
    mutationCache: new MutationCache({
      onError: (error) => signal(error, false),
    }),
    defaultOptions: {
      queries: {
        refetchOnWindowFocus: false,
        // An answer with a status is final; only a missing answer (network) is retried, once.
        retry:
          options.retry === false
            ? false
            : (failureCount, error) => problemStatus(error) === undefined && failureCount < 1,
      },
    },
  });
}
