import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createApi } from '@/api/client';
import { ApiContext } from '@/app/api-context';
import { tr } from '@/i18n/tr';
import './index.css';

const queryClient = new QueryClient();
// Browser: same origin (Vite proxy in dev, nginx in Docker), so the base URL is empty.
const api = createApi({ baseUrl: '' });

const root = document.getElementById('root');
if (!root) throw new Error('#root not found');

createRoot(root).render(
  <StrictMode>
    <ApiContext value={api}>
      <QueryClientProvider client={queryClient}>
        <h1>{tr.app.title}</h1>
      </QueryClientProvider>
    </ApiContext>
  </StrictMode>,
);
