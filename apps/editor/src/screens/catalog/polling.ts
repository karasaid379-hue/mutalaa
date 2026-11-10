// Polling of releases that are being prepared. The Publisher (`watch`) does the work after a request; the
// panel only reads `durum`, so a row in `hazirlaniyor` is polled every 5 seconds.
//
// TanStack Query pauses an interval while the tab is hidden (`refetchIntervalInBackground` stays false), so
// there is no polling in a background tab; the user can also stop it with a button (`enabled` false).

/** Interval between two reads of a release that is being prepared. */
export const RELEASE_POLL_MS = 5000;

/** The `durum` of a release the Publisher has not finished yet. */
export const PREPARING = 'hazirlaniyor';

export function isPreparing(durum: string | null | undefined): boolean {
  return durum === PREPARING;
}

/** The `refetchInterval` value: 5 s while the release is being prepared and polling is on, else off. */
export function pollInterval(enabled: boolean, preparing: boolean): number | false {
  return enabled && preparing ? RELEASE_POLL_MS : false;
}
