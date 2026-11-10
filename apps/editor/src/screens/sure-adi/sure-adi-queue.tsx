import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router';
import { useApi } from '@/app/api-context';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import { tr } from '@/i18n/tr';
import { trSureAdi } from '@/i18n/tr-baglanti-sure';
import { ApprovalStages, ReviewBadges } from '@/review/badges';
import { BulkDecision, type RowMark } from '@/review/bulk-decision';
import { DecisionForm } from '@/review/decision-form';
import {
  REVIEW_PATH,
  REVIEWS_PATH,
  SURE_ADI_PAGE_SIZE,
  reviewDetailInit,
  reviewListInit,
  reviewListOptions,
  type QueueFilter,
} from '@/review/queries';
import type { ReviewDetail } from '@/review/types';
import { groupBySurah, readSureAdiPayload, type SureAdiGroup } from './payload';
import { SureAdiCard } from './sure-adi-card';

/** Target table and field of the queue (K-43 madde 4). */
const SURE_ADI_FILTER: QueueFilter = { hedef_tablo: 'surah_alias', alan: 'status' };

function parseId(raw: string | null): number | null {
  if (!raw || !/^[0-9]+$/.test(raw)) return null;
  const id = Number(raw);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

interface GroupSectionProps {
  group: SureAdiGroup;
  selected: ReadonlySet<number>;
  currentId: number | null;
  marks: Readonly<Record<number, RowMark>>;
  onToggle: (id: number, checked: boolean) => void;
  onToggleGroup: (group: SureAdiGroup) => void;
}

function GroupSection({
  group,
  selected,
  currentId,
  marks,
  onToggle,
  onToggleGroup,
}: GroupSectionProps) {
  const headingId = `sure-adi-grup-${group.sure ?? 'bilinmiyor'}`;
  const selectable = group.rows.filter((row) => row.selectable);
  const allSelected = selectable.length > 0 && selectable.every((row) => selected.has(row.item.id));
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2"
      data-testid="sure-adi-group"
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className="text-base font-semibold">
          {group.sure === null ? trSureAdi.unknownGroup : trSureAdi.groupHeading(group.sure)}
        </h2>
        {selectable.length > 0 ? (
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-pressed={allSelected}
            onClick={() => onToggleGroup(group)}
          >
            {allSelected ? trSureAdi.clearGroup : trSureAdi.selectGroup}
          </Button>
        ) : null}
      </div>
      <p className="text-xs text-muted-foreground">
        {selectable.length > 0
          ? trSureAdi.groupCount(group.rows.length, selectable.length)
          : trSureAdi.noSelectable}
      </p>
      <ul className="flex flex-col gap-2">
        {group.rows.map((row) => (
          <SureAdiCard
            key={row.item.id}
            row={row}
            checked={selected.has(row.item.id)}
            onToggle={onToggle}
            current={row.item.id === currentId}
            marked={marks[row.item.id] !== undefined}
          />
        ))}
      </ul>
    </section>
  );
}

function Detail({ review, onDecided }: { review: ReviewDetail; onDecided: (id: number) => void }) {
  const payload = readSureAdiPayload(review.onerilen);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trSureAdi.detailHeading}</h2>
        <p className="font-medium break-words">{payload?.alias ?? review.hedef_anahtar}</p>
        <ReviewBadges review={review} showOrigin />
      </div>
      <p className="text-sm text-muted-foreground">{trSureAdi.singleOnlyNote}</p>
      <ApprovalStages review={review} />
      <DecisionForm review={review} onDecided={(result) => onDecided(result.id)} />
    </div>
  );
}

/**
 * The surah name queue (K-43 madde 4, İ-23): every open candidate, grouped by surah, each on its own card.
 * It loads every page (200 per page, the first request has no cursor). The bulk approval has no sample (the
 * whole row is on the card), covers approvals only and never contains risky names: those and every rejection
 * go through the single decision form on the right.
 *
 * It composes its own layout instead of `QueueLayout`: that component draws a flat list in API order and
 * cannot group.
 */
export function SureAdiQueue() {
  const api = useApi();
  const [params, setParams] = useSearchParams();
  const selectedId = parseId(params.get('kayit'));

  const list = api.$api.useInfiniteQuery(
    'get',
    REVIEWS_PATH,
    reviewListInit(SURE_ADI_FILTER, SURE_ADI_PAGE_SIZE),
    reviewListOptions,
  );
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
  const items = useMemo(() => list.data?.pages.flatMap((page) => page.items) ?? [], [list.data]);
  const groups = useMemo(() => groupBySurah(items), [items]);
  const ordered = useMemo(() => groups.flatMap((group) => group.rows), [groups]);

  const detail = api.$api.useQuery('get', REVIEW_PATH, reviewDetailInit(selectedId ?? 0), {
    enabled: selectedId !== null,
    retry: false,
  });

  // Every page is fetched without a button; runs again whenever a page arrives.
  const pageCount = list.data?.pages.length ?? 0;
  useEffect(() => {
    if (pageCount > 0 && hasNextPage && !isFetchingNextPage) void fetchNextPage();
  }, [pageCount, hasNextPage, isFetchingNextPage, fetchNextPage]);

  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const [marks, setMarks] = useState<Readonly<Record<number, RowMark>>>({});
  const [listEl, setListEl] = useState<HTMLElement | null>(null);
  const [detailEl, setDetailEl] = useState<HTMLElement | null>(null);

  // Only checked, bulk-selectable rows that are still in the list take part (a risky row never does).
  const selectedItems = useMemo(
    () =>
      ordered.filter((row) => row.selectable && selected.has(row.item.id)).map((row) => row.item),
    [ordered, selected],
  );

  function toggle(id: number, checked: boolean) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function toggleGroup(group: SureAdiGroup) {
    const ids = group.rows.filter((row) => row.selectable).map((row) => row.item.id);
    setSelected((previous) => {
      const next = new Set(previous);
      const all = ids.length > 0 && ids.every((id) => next.has(id));
      for (const id of ids) {
        if (all) next.delete(id);
        else next.add(id);
      }
      return next;
    });
  }

  function clearSelection() {
    setSelected(new Set());
    setMarks({});
  }

  function onDecided(id: number) {
    const index = ordered.findIndex((row) => row.item.id === id);
    const next = index >= 0 ? (ordered[index + 1] ?? ordered[index - 1]) : undefined;
    setParams(next ? { kayit: String(next.item.id) } : {}, { replace: true });
    (next ? detailEl : listEl)?.focus();
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeading>{tr.nav.queueSureAdi}</PageHeading>
      <div className="grid gap-4 lg:grid-cols-[minmax(22rem,34rem)_minmax(0,1fr)]">
        <section
          ref={setListEl}
          tabIndex={-1}
          aria-label={tr.queue.listLabel}
          className="flex flex-col gap-4 outline-none"
        >
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
            groups.map((group) => (
              <GroupSection
                key={group.sure ?? 'bilinmiyor'}
                group={group}
                selected={selected}
                currentId={selectedId}
                marks={marks}
                onToggle={toggle}
                onToggleGroup={toggleGroup}
              />
            ))
          )}
          {!list.isError && hasNextPage ? (
            <p className="text-xs text-muted-foreground">{tr.ui.loadingMore}</p>
          ) : null}
          {!list.isPending && !list.isError && items.length > 0 ? (
            <p className="text-xs text-muted-foreground">{tr.queue.loadedCount(items.length)}</p>
          ) : null}
        </section>

        <div className="flex min-w-0 flex-col gap-4">
          {selectedItems.length > 0 ? (
            <section
              aria-label={trSureAdi.bulkRegion}
              className="flex flex-col gap-2 rounded-lg border p-3"
              data-testid="sure-adi-bulk"
            >
              <p className="text-sm font-medium">{trSureAdi.selectedCount(selectedItems.length)}</p>
              <BulkDecision
                items={selectedItems}
                sampling="none"
                onDone={clearSelection}
                onCancel={clearSelection}
                onMarksChange={setMarks}
              />
            </section>
          ) : null}
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
              <Detail key={detail.data.id} review={detail.data} onDecided={onDecided} />
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
