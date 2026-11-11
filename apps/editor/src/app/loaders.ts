import { redirect, type LoaderFunctionArgs } from 'react-router';
import type { Api } from '@/api/client';
import { problemStatus } from '@/lib/problem';
import { loginHref, safeNext } from '@/lib/safe-next';
import { ME_PATH, SESSION_QUERY_OPTIONS } from '@/review/queries';
import type { QueryClient } from '@tanstack/react-query';

export interface LoaderDeps {
  api: Api;
  queryClient: QueryClient;
}

/**
 * Loader of the root route: every protected screen needs a session. 401 goes to `/giris?sonraki=...`
 * (the page asked for), 403 (a user without a role) to the "yetki yok" page. The result stays in the
 * query cache, where the shell reads it; data of the screens is fetched by the screens themselves.
 */
export function createRequireSession({ api, queryClient }: LoaderDeps) {
  return async ({ request }: LoaderFunctionArgs): Promise<null> => {
    try {
      await queryClient.fetchQuery({
        ...api.$api.queryOptions('get', ME_PATH),
        staleTime: SESSION_QUERY_OPTIONS.staleTime,
        retry: false,
      });
    } catch (error) {
      const status = problemStatus(error);
      const url = new URL(request.url);
      if (status === 401) throw redirect(loginHref(`${url.pathname}${url.search}`));
      if (status === 403) throw redirect('/yetki-yok');
      throw error;
    }
    return null;
  };
}

/**
 * Loader of `/giris`. After a logout (`?cikis=1`) it asks nothing: a signed-out page must not call `me`
 * (with the development auto login the call would sign the user straight back in). Otherwise a live
 * session skips the form and returns to `?sonraki=` (only local paths, see safeNext).
 */
export function createLoginLoader({ api, queryClient }: LoaderDeps) {
  return async ({ request }: LoaderFunctionArgs): Promise<Response | null> => {
    const url = new URL(request.url);
    if (url.searchParams.get('cikis') === '1') return null;
    try {
      // staleTime 0: a cached answer from before a 401 must not send the user back to the page that just failed.
      await queryClient.fetchQuery({
        ...api.$api.queryOptions('get', ME_PATH),
        staleTime: 0,
        retry: false,
      });
    } catch (error) {
      return problemStatus(error) === 403 ? redirect('/yetki-yok') : null;
    }
    return redirect(safeNext(url.searchParams.get('sonraki')));
  };
}
