import { useCallback, useState, type ReactNode } from 'react';
import { AnnounceContext } from './announce-context';

// The one live region of the app. Announcing the same text twice appends a no-break space so that
// screen readers still see a change.
export function AnnounceProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  const announce = useCallback((next: string) => {
    setMessage((previous) => (previous === next ? `${next}\u00a0` : next));
  }, []);
  return (
    <AnnounceContext value={announce}>
      {children}
      <div role="status" aria-live="polite" aria-atomic="true" className="sr-only">
        {message}
      </div>
    </AnnounceContext>
  );
}
