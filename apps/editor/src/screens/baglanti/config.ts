import type { LinkClass, QueueFilter, QueueStatus } from '@/review/queries';

/**
 * Bulk selection of the link candidates queue (K-13 politika 1, K-48 karar 5): open since A18.4, because the API
 * now gives the candidate class (`sinif`). The selection is offered only for records of the `toplu` class, the
 * approval asks for a random 10 percent sample (one "Hatalı" cancels it) and the server refuses any other class
 * with 422 `toplu-uygun-degil`.
 */
export const BULK_ENABLED = true;

/** The classes of a link candidate in queue order: inconsistent first, then bulk eligible, then the grey zone. */
export const LINK_CLASSES: readonly LinkClass[] = ['tutarsiz', 'toplu', 'gri', 'diger'];

export function isLinkClass(value: unknown): value is LinkClass {
  return LINK_CLASSES.some((entry) => entry === value);
}

/** The only class a bulk approval accepts. */
export const BULK_CLASS: LinkClass = 'toplu';

/** Views of the queue: open records, or the records sent to an expert (K-51 madde 2). */
export type LinkStatusView = QueueStatus;
export const LINK_STATUS_VIEWS: readonly LinkStatusView[] = ['acik', 'uzmanda'];

export function isLinkStatusView(value: unknown): value is LinkStatusView {
  return LINK_STATUS_VIEWS.some((entry) => entry === value);
}

/**
 * The list filter of the queue: the `xref` / `status` records in class order (`sira=sinif`), of one status and,
 * when chosen, of one class. A change is a new query, so the cursor starts over (cursors are typed by order).
 */
export function linkFilter(status: LinkStatusView, sinif: LinkClass | 'hepsi'): QueueFilter {
  return {
    hedef_tablo: 'xref',
    alan: 'status',
    sira: 'sinif',
    ...(status === 'uzmanda' ? { durum: 'uzmanda' as const } : {}),
    ...(sinif !== 'hepsi' ? { sinif } : {}),
  };
}
