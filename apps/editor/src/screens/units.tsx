import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { components } from '@/api/schema';
import { useApi } from '@/app/api-context';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import { Skeleton } from '@/components/ui/skeleton';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { cn } from '@/lib/utils';
import { withParams } from './catalog/search-params';
import { UnitDetailPane } from './catalog/unit-detail';
import { AnchorForm, FilterForm } from './catalog/unit-filters';
import type { Filters } from './catalog/unit-filter-types';
import { UnitPreview } from './catalog/unit-preview';

type UnitListPage = components['schemas']['UnitListResponse'];

const UNITS_PATH = '/api/v1/units' as const;
/** The API allows 1 to 200; the list shows whole texts, so the pages stay small. */
const PAGE_SIZE = 50;

const listOptions = {
  // The first request carries no cursor (the library default would send `cursor=0`).
  initialPageParam: null,
  getNextPageParam: (last: UnitListPage) => last.next_cursor ?? undefined,
};

/**
 * Units (A15.5): filters (source, anchor prefix, text query) over `GET /units` with a cursor, and the detail
 * of one unit (`GET /units/{anchor}`). The selected unit is kept in `?birim=`; the filters in `?kaynak=`, `?onek=`,
 * `?q=`. An invalid anchor is refused on the client without a request.
 */
export function Component() {
  const api = useApi();
  const [params, setParams] = useSearchParams();
  const filters: Filters = {
    kaynak: params.get('kaynak') ?? '',
    onek: params.get('onek') ?? '',
    q: params.get('q') ?? '',
  };
  const selected = params.get('birim') ?? '';

  const list = api.$api.useInfiniteQuery(
    'get',
    UNITS_PATH,
    {
      params: {
        query: {
          source: filters.kaynak || undefined,
          prefix: filters.onek || undefined,
          q: filters.q || undefined,
          limit: PAGE_SIZE,
        },
      },
    },
    listOptions,
  );
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
  const items = useMemo(() => list.data?.pages.flatMap((page) => page.items) ?? [], [list.data]);

  return (
    <div className="flex flex-col gap-4">
      <PageHeading>{tr.nav.units}</PageHeading>
      <div className="grid gap-4 lg:grid-cols-[minmax(18rem,28rem)_minmax(0,1fr)]">
        <section aria-label={trc.units.listLabel} className="flex min-w-0 flex-col gap-3">
          <FilterForm
            key={`${filters.kaynak}|${filters.onek}|${filters.q}`}
            initial={filters}
            onApply={(next) =>
              setParams(withParams(params, { kaynak: next.kaynak, onek: next.onek, q: next.q }))
            }
          />
          <AnchorForm
            key={selected}
            initial={selected}
            onOpen={(anchor) => setParams(withParams(params, { birim: anchor }))}
          />
          {list.isPending ? (
            <div className="flex flex-col gap-2" data-testid="units-loading">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          ) : list.isError ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">{trc.units.loadFailed}</p>
              <ProblemMessage error={list.error} />
              <div>
                <Button type="button" variant="outline" onClick={() => void list.refetch()}>
                  {tr.ui.retry}
                </Button>
              </div>
            </div>
          ) : items.length === 0 ? (
            <Empty data-testid="units-empty">
              <EmptyHeader>
                <EmptyTitle>{trc.units.empty}</EmptyTitle>
                <EmptyDescription>{trc.units.emptyHint}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {items.map((unit) => {
                const current = unit.anchor === selected;
                return (
                  <li key={unit.anchor}>
                    <Link
                      to={{ search: `?${withParams(params, { birim: unit.anchor }).toString()}` }}
                      aria-current={current ? 'true' : undefined}
                      className={cn(
                        'flex min-h-6 flex-col gap-1 rounded-lg border p-2 hover:bg-muted',
                        current && 'border-primary bg-muted',
                      )}
                    >
                      <span className="font-mono text-sm font-medium break-all">{unit.anchor}</span>
                      <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="secondary">{labelOf(trc.unitKind, unit.kind)}</Badge>
                        <span>{unit.source}</span>
                        <Badge variant="outline">
                          {labelOf(tr.labels.textStatus, unit.metin_durumu)}
                        </Badge>
                        {unit.status === 'etkin' ? null : (
                          <Badge variant="destructive">
                            {labelOf(trc.unitStatus, unit.status)}
                          </Badge>
                        )}
                      </span>
                      <UnitPreview unit={unit} />
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
          {hasNextPage ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => void fetchNextPage()}
              disabled={isFetchingNextPage}
            >
              {isFetchingNextPage ? trc.common.loadingMore : trc.common.loadMore}
            </Button>
          ) : null}
          {!list.isPending && !list.isError && items.length > 0 ? (
            <p className="text-xs text-muted-foreground">{trc.common.loadedCount(items.length)}</p>
          ) : null}
        </section>

        <section aria-label={trc.units.detailLabel} className="flex min-w-0 flex-col gap-4">
          {selected === '' ? (
            <p className="text-sm text-muted-foreground">{trc.units.selectPrompt}</p>
          ) : (
            <UnitDetailPane key={selected} anchor={selected} />
          )}
        </section>
      </div>
    </div>
  );
}
