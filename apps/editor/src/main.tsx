import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { createApi } from '@/api/client';
import { AppProviders } from '@/app/providers';
import { SessionBridge, createQueryClient } from '@/app/query-client';
import { createRoutes } from '@/app/routes';
import './index.css';

const bridge = new SessionBridge();
const queryClient = createQueryClient(bridge);
// Browser: same origin (Vite proxy in dev, nginx in Docker), so the base URL is empty.
const api = createApi({ baseUrl: '' });
const router = createBrowserRouter(createRoutes({ api, queryClient, bridge }));

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <AppProviders api={api} queryClient={queryClient}>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
);
