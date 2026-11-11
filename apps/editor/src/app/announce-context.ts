import { createContext, useContext } from 'react';

/** Speaks a short message through the single live region (`role="status"`) of the app. */
export type Announce = (message: string) => void;

export const AnnounceContext = createContext<Announce>(() => {});

export function useAnnounce(): Announce {
  return useContext(AnnounceContext);
}
