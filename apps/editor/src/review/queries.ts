import type { QueryClient, InfiniteData } from '@tanstack/react-query';
import type { Api } from '@/api/client';
import type { ReviewDetail, ReviewItem, ReviewListPage } from './types';

// Shared query options and cache helpers of the review area. Screens call
// `$api.useQuery` / `$api.useInfiniteQuery` themselves with these inits and options (no wrapper hooks).

export const REVIEWS_PATH = '/api/v1/reviews' as const;
export const REVIEW_STATS_PATH = '/api/v1/reviews/stats' as const;
export const REVIEW_PATH = '/api/v1/reviews/{id}' as const;
export const ME_PATH = '/api/v1/auth/me' as const;

/** Page size of the queue lists (the API allows 1 to 200). */
export const QUEUE_PAGE_SIZE = 50;
/** Page size of the sure adi queue, which loads every page. */
export const SURE_ADI_PAGE_SIZE = 200;

/** Options shared by the router loader and the `me` query hooks: the session is re-checked at most every 30 s. */
export const SESSION_QUERY_OPTIONS = {
  staleTime: 30_000,
  retry: false,
  refetchOnWindowFocus: true,
} as const;

/**
 * Order of a queue list (`sira`): `dalga` is the word wave order, only for `lemma` and `lemma_gloss` targets;
 * `sinif` is the link candidate class order (tutarsız, toplu, gri, diğer), only for the `xref` target.
 */
export type QueueOrder = 'olusturma' | 'dalga' | 'sinif';

/** Status of the listed records: `acik` (default) or `uzmanda` (sent to an expert, K-51 madde 2). */
export type QueueStatus = 'acik' | 'uzmanda';

/** Link candidate class of the `sinif` filter (`xref` target only). */
export type LinkClass = 'tutarsiz' | 'toplu' | 'gri' | 'diger';

/** Approval path filter of the Turkish lemma mapping list (`onay_yolu`, `lemma` target only). */
export type ApprovalParam = 'otomatik' | 'editor' | 'aday';

export interface QueueFilter {
  hedef_tablo: string;
  /** Field of the review; optional (a queue of every field of the target, e.g. `quran_word_fix`). */
  alan?: string;
  /** Source slug of the unit (`unit` targets only), e.g. `elmalili-meal`. */
  kaynak?: string;
  /** Approval stage: `ilk` (open, no reviewer yet) or `ikinci` (open, waiting for the second approval). */
  asama?: 'ilk' | 'ikinci';
  /** List order; left out for the API default (`olusturma`). A change gives a new query, so the cursor starts over. */
  sira?: QueueOrder;
  /** Status of the records; left out for `acik`. */
  durum?: QueueStatus;
  /** Link candidate class (`xref` only); the server filters. */
  sinif?: LinkClass;
  /** Approval path of a Turkish lemma mapping (`lemma` only); the server filters. */
  onay_yolu?: ApprovalParam;
}

/** Init of the queue list: open records of one target and field, optionally of one source and stage. */
export function reviewListInit(filter: QueueFilter, limit: number = QUEUE_PAGE_SIZE) {
  return {
    params: {
      query: {
        hedef_tablo: filter.hedef_tablo,
        ...(filter.alan !== undefined ? { alan: filter.alan } : {}),
        durum: filter.durum ?? 'acik',
        ...(filter.kaynak !== undefined ? { kaynak: filter.kaynak } : {}),
        ...(filter.asama !== undefined ? { asama: filter.asama } : {}),
        ...(filter.sira !== undefined ? { sira: filter.sira } : {}),
        ...(filter.sinif !== undefined ? { sinif: filter.sinif } : {}),
        ...(filter.onay_yolu !== undefined ? { onay_yolu: filter.onay_yolu } : {}),
        limit,
      },
    },
  };
}

/**
 * Options of the queue list `useInfiniteQuery`. The first request must not carry a cursor: the library
 * default for `initialPageParam` is 0, which would send `cursor=0` (400), so it is `null` here (tested).
 */
export const reviewListOptions = {
  initialPageParam: null,
  getNextPageParam: (last: ReviewListPage) => last.next_cursor ?? undefined,
};

export function reviewDetailInit(id: number) {
  return { params: { path: { id } } };
}

/** Query key of one review detail (the same key `$api.useQuery('get', REVIEW_PATH, reviewDetailInit(id))` uses). */
export function reviewDetailKey(api: Api, id: number) {
  return api.$api.queryOptions('get', REVIEW_PATH, reviewDetailInit(id)).queryKey;
}

/** The list item part of a detail record (drops the detail-only fields). */
export function toListItem(detail: ReviewDetail): ReviewItem {
  const { gerekce, ikinci_gerekce, sure_ms, hedef, dogrulanmis, ...item } = detail;
  void gerekce;
  void ikinci_gerekce;
  void sure_ms;
  void hedef;
  void dogrulanmis;
  return item;
}

type ListData = InfiniteData<ReviewListPage, unknown>;

function isListData(value: unknown): value is ListData {
  return typeof value === 'object' && value !== null && Array.isArray((value as ListData).pages);
}

function mapPages(data: ListData, change: (items: ReviewItem[]) => ReviewItem[]): ListData {
  return { ...data, pages: data.pages.map((page) => ({ ...page, items: change(page.items) })) };
}

/** Status a cached list was requested with (`durum` of its query; `acik` when the query names none). */
function listStatus(queryKey: readonly unknown[]): string {
  const init = queryKey[2];
  if (typeof init === 'object' && init !== null) {
    const query = (init as { params?: { query?: { durum?: unknown } } }).params?.query;
    if (typeof query?.durum === 'string') return query.durum;
  }
  return 'acik';
}

/**
 * Replaces the record in every cached queue list; a record whose status no longer matches the status of a list
 * (`acik` list, `uzmanda` list) leaves that list.
 */
export function patchReviewInLists(
  queryClient: QueryClient,
  fresh: ReviewDetail | ReviewItem,
): void {
  const item: ReviewItem =
    'hedef' in fresh || 'dogrulanmis' in fresh ? toListItem(fresh as ReviewDetail) : fresh;
  for (const [key, old] of queryClient.getQueriesData<ListData>({
    queryKey: ['get', REVIEWS_PATH],
  })) {
    if (!isListData(old)) continue;
    const keep = item.durum === listStatus(key);
    queryClient.setQueryData<ListData>(
      key,
      mapPages(old, (items) =>
        keep
          ? items.map((existing) => (existing.id === item.id ? item : existing))
          : items.filter((existing) => existing.id !== item.id),
      ),
    );
  }
}

/** Removes records from every cached queue list. */
export function removeReviewsFromLists(queryClient: QueryClient, ids: readonly number[]): void {
  const gone = new Set(ids);
  queryClient.setQueriesData<ListData>({ queryKey: ['get', REVIEWS_PATH] }, (old) =>
    isListData(old) ? mapPages(old, (items) => items.filter((item) => !gone.has(item.id))) : old,
  );
}

/** Stats and lists are stale after any decision. */
export function invalidateReviewCounts(queryClient: QueryClient): Promise<void> {
  return queryClient.invalidateQueries({ queryKey: ['get', REVIEW_STATS_PATH] });
}
