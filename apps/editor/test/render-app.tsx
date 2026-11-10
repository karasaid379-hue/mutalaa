import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { createApi } from '@/api/client';
import { AppProviders } from '@/app/providers';
import { SessionBridge, createQueryClient } from '@/app/query-client';
import { createRoutes } from '@/app/routes';
import { BASE, type FakeApi } from './fake-api';

function parts(fake: FakeApi) {
  const bridge = new SessionBridge();
  const queryClient = createQueryClient(bridge, { retry: false });
  const api = createApi({ baseUrl: BASE, fetch: fake.fetch });
  return { bridge, queryClient, api };
}

/** The whole panel (the real route list) on a memory router at `route`. */
export function renderApp(fake: FakeApi, route = '/kuyruk/ocr') {
  const { bridge, queryClient, api } = parts(fake);
  const router = createMemoryRouter(createRoutes({ api, queryClient, bridge }), {
    initialEntries: [route],
  });
  const user = userEvent.setup();
  const view = render(
    <AppProviders api={api} queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { ...view, router, queryClient, api, bridge, user };
}

/** One element at path `/` inside the providers and a memory router (for QueueLayout and other router users). */
export function renderInRouter(fake: FakeApi, element: ReactElement, route = '/') {
  const { queryClient, api } = parts(fake);
  const router = createMemoryRouter([{ path: '/', element }], { initialEntries: [route] });
  const user = userEvent.setup();
  const view = render(
    <AppProviders api={api} queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return { ...view, router, queryClient, api, user };
}

/** One element inside the providers, no router (DecisionForm, BulkDecision, ProblemMessage). */
export function renderWithProviders(fake: FakeApi, element: ReactElement) {
  const { queryClient, api } = parts(fake);
  const user = userEvent.setup();
  const view = render(
    <AppProviders api={api} queryClient={queryClient}>
      {element}
    </AppProviders>,
  );
  return { ...view, queryClient, api, user };
}
