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

export interface QueueFilter {
  hedef_tablo: string;
  alan: string;
}

/** Init of the queue list: open records of one target and field. */
export function reviewListInit(filter: QueueFilter, limit: number = QUEUE_PAGE_SIZE) {
  return {
    params: {
      query: { hedef_tablo: filter.hedef_tablo, alan: filter.alan, durum: 'acik', limit },
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

/** Replaces the record in every cached queue list; a record that is no longer open leaves the lists. */
export function patchReviewInLists(
  queryClient: QueryClient,
  fresh: ReviewDetail | ReviewItem,
): void {
  const item: ReviewItem =
    'hedef' in fresh || 'dogrulanmis' in fresh ? toListItem(fresh as ReviewDetail) : fresh;
  queryClient.setQueriesData<ListData>({ queryKey: ['get', REVIEWS_PATH] }, (old) => {
    if (!isListData(old)) return old;
    return mapPages(old, (items) =>
      item.durum === 'acik'
        ? items.map((existing) => (existing.id === item.id ? item : existing))
        : items.filter((existing) => existing.id !== item.id),
    );
  });
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
