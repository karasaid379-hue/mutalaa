import { tr } from '@/i18n/tr';

/** Fallback shown while a route loader runs for the first time. */
export function Loading() {
  return (
    <div aria-busy="true">
      <p className="p-6 text-sm">{tr.ui.loading}</p>
    </div>
  );
}
