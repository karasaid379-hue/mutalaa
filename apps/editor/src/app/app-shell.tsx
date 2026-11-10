import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState, type MouseEvent } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { roleLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { compareTr } from '@/lib/format';
import { loginHref } from '@/lib/safe-next';
import { problemStatus } from '@/lib/problem';
import { ME_PATH, SESSION_QUERY_OPTIONS } from '@/review/queries';
import type { SessionBridge, SessionSignal } from './query-client';
import { Sidebar } from './sidebar';

/**
 * Frame of every protected screen: skip link, session header, navigation and the main region. It also
 * answers the session signals of the query caches: a 401 in the middle of a page first navigates to
 * `/giris?sonraki=...` and only then clears the query cache; a 403 on the session query goes to the
 * "yetki yok" page. Logout goes to `/giris?cikis=1` (the login page does not ask `me` then).
 */
export function AppShell({ bridge }: { bridge: SessionBridge }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);

  const mainRef = useRef<HTMLElement>(null);
  const locationRef = useRef(location);
  const handling = useRef(false);
  // Set when the shell is about to be left because of a signed-out session: the cache is cleared when the
  // shell unmounts, i.e. after the navigation is committed (clearing while it is still mounted would refetch).
  const clearOnUnmount = useRef(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState<unknown>(null);

  useEffect(() => {
    locationRef.current = location;
  }, [location]);

  useEffect(() => {
    const handler = (signal: SessionSignal) => {
      if (handling.current) return;
      handling.current = true;
      const target =
        signal === 'unauthorized'
          ? loginHref(`${locationRef.current.pathname}${locationRef.current.search}`)
          : '/yetki-yok';
      // Navigate first, clear afterwards (on unmount below): clearing first would refetch the page we are leaving.
      void (async () => {
        clearOnUnmount.current = true;
        try {
          await navigate(target, { replace: true });
        } catch (thrown) {
          clearOnUnmount.current = false;
          throw thrown;
        } finally {
          handling.current = false;
        }
      })();
    };
    const unsubscribe = bridge.subscribe(handler);
    return () => {
      unsubscribe();
      if (clearOnUnmount.current) {
        clearOnUnmount.current = false;
        queryClient.clear();
      }
    };
  }, [bridge, navigate, queryClient]);

  async function logout() {
    setLogoutError(null);
    setLoggingOut(true);
    handling.current = true;
    try {
      const { error } = await api.client.POST('/api/v1/auth/logout');
      // 401: the session is already gone, which is what we wanted.
      if (error && problemStatus(error) !== 401) {
        setLogoutError(error);
        handling.current = false;
        return;
      }
    } catch (thrown) {
      setLogoutError(thrown);
      handling.current = false;
      return;
    } finally {
      setLoggingOut(false);
    }
    clearOnUnmount.current = true;
    try {
      await navigate('/giris?cikis=1', { replace: true });
    } catch (thrown) {
      clearOnUnmount.current = false;
      throw thrown;
    } finally {
      handling.current = false;
    }
  }

  function skip(event: MouseEvent<HTMLAnchorElement>) {
    event.preventDefault();
    mainRef.current?.focus();
  }

  const session = me.data;
  const roles = session ? [...session.roller].sort(compareTr) : [];

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        onClick={skip}
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded-lg focus:bg-background focus:p-2 focus:ring-2"
      >
        {tr.ui.skipToContent}
      </a>
      <header
        aria-label={tr.session.headerRegion}
        className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-2"
      >
        <p className="text-sm font-semibold">{tr.app.title}</p>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {session ? (
            <p>
              <span className="font-medium">{session.kullanici.email}</span>{' '}
              <span className="text-muted-foreground">
                {roles.length > 0
                  ? roles.map((role) => roleLabel(role)).join(', ')
                  : tr.session.noRoles}
              </span>
            </p>
          ) : null}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => void logout()}
            disabled={loggingOut}
          >
            {loggingOut ? tr.session.loggingOut : tr.session.logout}
          </Button>
        </div>
      </header>
      {logoutError !== null ? (
        <div className="px-4 pt-2">
          <ProblemMessage error={logoutError} />
        </div>
      ) : null}
      <div className="flex flex-1">
        <Sidebar />
        <main
          id="main"
          ref={mainRef}
          tabIndex={-1}
          aria-label={tr.session.mainRegion}
          className="min-w-0 flex-1 p-4 outline-none"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
