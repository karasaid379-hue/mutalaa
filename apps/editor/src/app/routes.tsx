import type { QueryClient } from '@tanstack/react-query';
import { redirect, type RouteObject } from 'react-router';
import type { Api } from '@/api/client';
import { Component as ForbiddenPage } from '@/screens/forbidden';
import { Component as LoginPage } from '@/screens/login';
import { Component as NotFoundPage } from '@/screens/not-found';
import { Component as QueueBaglanti } from '@/screens/queue-baglanti';
import { Component as QueueLemma } from '@/screens/queue-lemma';
import { Component as QueueSureAdi } from '@/screens/queue-sure-adi';
import { Component as ReleasesPage } from '@/screens/releases';
import { RouteError } from '@/screens/route-error';
import { Component as SourcesPage } from '@/screens/sources';
import { Component as UnitsPage } from '@/screens/units';
import { AppShell } from './app-shell';
import { Loading } from './loading';
import { createLoginLoader, createRequireSession } from './loaders';
import type { SessionBridge } from './query-client';

/**
 * The eight routes of the panel (Proje yapisi 1, BÇ-12). `/giris` is the login page; the other seven need a
 * session: without one they redirect to `/giris?sonraki=...`.
 */
export const ROUTE_PATHS = [
  '/giris',
  '/kuyruk/ocr',
  '/kuyruk/lemma',
  '/kuyruk/baglanti',
  '/kuyruk/sure-adi',
  '/kaynaklar',
  '/birimler',
  '/yayinlar',
] as const;

export type RoutePath = (typeof ROUTE_PATHS)[number];

/** The routes behind the session check. */
export const PROTECTED_PATHS: readonly RoutePath[] = ROUTE_PATHS.filter(
  (path) => path !== '/giris',
);

export interface AppDeps {
  api: Api;
  queryClient: QueryClient;
  bridge: SessionBridge;
}

/**
 * Route objects of the panel; the browser (`createBrowserRouter`) and the tests (`createMemoryRouter`)
 * build their router from this same list. The root route `/` runs the `requireSession` loader; the data of a
 * screen is fetched by the screen. The OCR screen is loaded lazily.
 */
export function createRoutes(deps: AppDeps): RouteObject[] {
  return [
    {
      path: '/giris',
      loader: createLoginLoader(deps),
      Component: LoginPage,
      HydrateFallback: Loading,
      ErrorBoundary: RouteError,
    },
    { path: '/yetki-yok', Component: ForbiddenPage },
    {
      path: '/',
      loader: createRequireSession(deps),
      element: <AppShell bridge={deps.bridge} />,
      HydrateFallback: Loading,
      ErrorBoundary: RouteError,
      children: [
        { index: true, loader: () => redirect('/kuyruk/ocr') },
        { path: 'kuyruk/ocr', lazy: () => import('@/screens/queue-ocr') },
        { path: 'kuyruk/lemma', Component: QueueLemma },
        { path: 'kuyruk/baglanti', Component: QueueBaglanti },
        { path: 'kuyruk/sure-adi', Component: QueueSureAdi },
        { path: 'kaynaklar', Component: SourcesPage },
        { path: 'birimler', Component: UnitsPage },
        { path: 'yayinlar', Component: ReleasesPage },
        { path: '*', Component: NotFoundPage },
      ],
    },
  ];
}
