import { createContext } from 'react';
import type { Api } from '@/api/client';

/** The API instance built in main.tsx (a fake-fetch instance in tests). */
export const ApiContext = createContext<Api | null>(null);
