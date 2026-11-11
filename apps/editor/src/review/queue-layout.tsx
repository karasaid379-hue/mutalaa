import { Fragment, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { useApi } from '@/app/api-context';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import { tr } from '@/i18n/tr';
import { cn } from '@/lib/utils';
import { ReviewBadges } from './badges';
import {
  QUEUE_PAGE_SIZE,
  REVIEW_PATH,
  REVIEWS_PATH,
  SURE_ADI_PAGE_SIZE,
  reviewDetailInit,
  reviewListInit,
  reviewListOptions,
  type QueueFilter,
} from './queries';
import type { DecisionKind, DecisionResult, ReviewDetail, ReviewItem } from './types';

export interface QueueDetailProps {
  /** The selected record, loaded from `GET /reviews/{id}` (its `xmin` is the `If-Match` value). */
  review: ReviewDetail;
  /** Pass to `DecisionForm`: moves to the next record and focus follows. */
  onDecided: (result: DecisionResult, decision: DecisionKind) => void;
}

export interface QueueLayoutProps {
  /** Screen title (the `h1`). */
  title: string;
  /** Target table and field of the queue. */
  filter: QueueFilter;
  /** Page size; default 50 (200 with `loadAll`). */
  pageSize?: number;
  /** Load every page without a button (sure adı queue). */
  loadAll?: boolean;
  /** Extra content after the link of a row (for example a selection checkbox); it is not inside the link. */
  renderItem?: (item: ReviewItem) => ReactNode;
  /**
   * Content above the list (tabs, bulk bar); receives the loaded records and `focusList`, which moves focus to
   * the list region (for content that disappears while it holds focus, such as the bulk bar after its approval).
   */
  renderListHeader?: (context: {
    items: readonly ReviewItem[];
    focusList: () => void;
  }) => ReactNode;
  /** The detail of the selected record. */
  renderDetail: (props: QueueDetailProps) => ReactNode;
  className?: string;
}

function parseId(raw: string | null): number | null {
  if (!raw || !/^[0-9]+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

/**
 * Common layout of the review queues: the open records on the left, the selected one on the right
 * (`?kayit=` holds its id), "Daha fazla yükle" for more pages. The first request carries no cursor
 * (`initialPageParam: null`). After a decision the next record opens and focus moves to it.
 */
export function QueueLayout({
  title,
  filter,
  pageSize,
  loadAll = false,
  renderItem,
  renderListHeader,
  renderDetail,
  className,
}: QueueLayoutProps) {
  const api = useApi();
  const [params, setParams] = useSearchParams();
  const selectedId = parseId(params.get('kayit'));
  const limit = pageSize ?? (loadAll ? SURE_ADI_PAGE_SIZE : QUEUE_PAGE_SIZE);

  const list = api.$api.useInfiniteQuery(
    'get',
    REVIEWS_PATH,
    reviewListInit(filter, limit),
    reviewListOptions,
  );
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
  const items = useMemo(() => list.data?.pages.flatMap((page) => page.items) ?? [], [list.data]);

  const detail = api.$api.useQuery('get', REVIEW_PATH, reviewDetailInit(selectedId ?? 0), {
    enabled: selectedId !== null,
    retry: false,
  });

  // Runs again whenever a page arrives (pageCount): a fast answer can land before a render with
  // isFetchingNextPage = true was ever committed, and the other dependencies would not change then.
  const pageCount = list.data?.pages.length ?? 0;
  useEffect(() => {
    if (loadAll && pageCount > 0 && hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [loadAll, pageCount, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // The two regions are held in state (callback refs) so the decision handler can move focus to them.
  const [listEl, setListEl] = useState<HTMLElement | null>(null);
  const [detailEl, setDetailEl] = useState<HTMLElement | null>(null);

  function onDecided(result: DecisionResult) {
    const index = items.findIndex((item) => item.id === result.id);
    const next = index >= 0 ? (items[index + 1] ?? items[index - 1]) : undefined;
    setParams(next ? { kayit: String(next.id) } : {}, { replace: true });
    // The regions stay mounted while their content changes: focus goes to the next record, or to the list when none is left.
    (next ? detailEl : listEl)?.focus();
  }

  function select(id: number): { search: string } {
    return { search: `?kayit=${id}` };
  }

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <PageHeading>{title}</PageHeading>
      <div className="grid gap-4 lg:grid-cols-[minmax(18rem,26rem)_minmax(0,1fr)]">
        <section
          ref={setListEl}
          tabIndex={-1}
          aria-label={tr.queue.listLabel}
          className="flex flex-col gap-3 outline-none"
        >
          {renderListHeader?.({ items, focusList: () => listEl?.focus() })}
          {list.isPending ? (
            <div className="flex flex-col gap-2" data-testid="queue-loading">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : list.isError ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">{tr.queue.loadFailed}</p>
              <ProblemMessage error={list.error} />
              <Button type="button" variant="outline" onClick={() => void list.refetch()}>
                {tr.ui.retry}
              </Button>
            </div>
          ) : items.length === 0 ? (
            <Empty data-testid="queue-empty">
              <EmptyHeader>
                <EmptyTitle>{tr.queue.empty}</EmptyTitle>
                <EmptyDescription>{tr.queue.emptyHint}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {items.map((item) => {
                const selected = item.id === selectedId;
                return (
                  <li key={item.id} className="flex flex-col gap-1">
                    <Link
                      to={select(item.id)}
                      aria-current={selected ? 'true' : undefined}
                      className={cn(
                        'flex min-h-6 flex-col gap-1 rounded-lg border p-2 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring',
                        selected && 'border-primary bg-muted',
                      )}
                    >
                      <span className="font-medium break-all">{item.hedef_anahtar}</span>
                      <ReviewBadges review={item} />
                    </Link>
                    {renderItem?.(item)}
                  </li>
                );
              })}
            </ul>
          )}
          {hasNextPage && !loadAll ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => void fetchNextPage()}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? tr.ui.loadingMore : tr.ui.loadMore}
            </Button>
          ) : null}
          {!list.isPending && !list.isError && items.length > 0 ? (
            <p className="text-xs text-muted-foreground">{tr.queue.loadedCount(items.length)}</p>
          ) : null}
        </section>

        <section
          ref={setDetailEl}
          tabIndex={-1}
          aria-label={tr.queue.detailLabel}
          className="flex min-w-0 flex-col gap-4 outline-none"
        >
          {selectedId === null ? (
            <p className="text-sm text-muted-foreground">{tr.queue.selectPrompt}</p>
          ) : detail.isPending ? (
            <div className="flex flex-col gap-2" data-testid="detail-loading">
              <Skeleton className="h-8" />
              <Skeleton className="h-32" />
            </div>
          ) : detail.isError ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">{tr.queue.detailFailed}</p>
              <ProblemMessage error={detail.error} />
            </div>
          ) : (
            <Fragment key={detail.data.id}>
              {renderDetail({ review: detail.data, onDecided })}
            </Fragment>
          )}
        </section>
      </div>
    </div>
  );
}
