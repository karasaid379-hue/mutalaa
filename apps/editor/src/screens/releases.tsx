import { useQueryClient } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router';
import type { components } from '@/api/schema';
import { useApi } from '@/app/api-context';
import { PageHeading } from '@/components/page-heading';
import { ProblemMessage } from '@/components/problem-message';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatDateTime } from '@/lib/format';
import { canPublish } from '@/lib/roles';
import { cn } from '@/lib/utils';
import { ME_PATH, SESSION_QUERY_OPTIONS } from '@/review/queries';
import { isPreparing, pollInterval } from './catalog/polling';
import { NewReleasePanel, type ReleaseAccepted } from './catalog/release-actions';
import { ReleaseDetailPane } from './catalog/release-detail';
import { parseId, withParams } from './catalog/search-params';

type ReleaseListPage = components['schemas']['ReleaseListResponse'];

const RELEASES_PATH = '/api/v1/releases' as const;
const PAGE_SIZE = 50;
const ALL = 'tumu';
const FLAVOR_FILTERS = [ALL, 'dev', 'internal', 'public'] as const;

/**
 * Releases (A15.5): the list (`GET /releases?derleme=&cursor=`) and the detail of one release with its quality
 * gate report, digests and manifest. A release that is being prepared is read again every 5 seconds (the user
 * can stop it; a hidden tab does not poll). Admins can preview and request a release, promote an internal release
 * and roll back; everyone else sees none of those buttons. The selected release is kept in `?yayin=`.
 */
export function Component() {
  const api = useApi();
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const filterLabelId = useId();
  const flavor = params.get('derleme');
  const selectedId = parseId(params.get('yayin'));
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [detailPreparing, setDetailPreparing] = useState(false);

  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);
  const admin = me.data !== undefined && canPublish(me.data.roller);

  const list = api.$api.useInfiniteQuery(
    'get',
    RELEASES_PATH,
    { params: { query: { derleme: flavor || undefined, limit: PAGE_SIZE } } },
    {
      // The first request carries no cursor (the library default would send `cursor=0`).
      initialPageParam: null,
      getNextPageParam: (last: ReleaseListPage) => last.next_cursor ?? undefined,
      refetchInterval: (query) =>
        pollInterval(
          autoRefresh,
          query.state.data?.pages.some((page) =>
            page.items.some((item) => isPreparing(item.durum)),
          ) ?? false,
        ),
    },
  );
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
  const items = useMemo(() => list.data?.pages.flatMap((page) => page.items) ?? [], [list.data]);
  const listPreparing = items.some((item) => isPreparing(item.durum));
  const polling = listPreparing || detailPreparing;

  const hrefFor = (id: number) => `?${withParams(params, { yayin: String(id) }).toString()}`;

  function accepted(result: ReleaseAccepted) {
    void queryClient.invalidateQueries({ queryKey: ['get', RELEASES_PATH] });
    setParams(withParams(params, { yayin: String(result.id) }));
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeading>{tr.nav.releases}</PageHeading>
      {polling ? (
        <div className="flex flex-wrap items-center gap-3" data-testid="release-polling">
          <p className="text-sm">
            {autoRefresh ? trc.releases.autoRefreshOn : trc.releases.autoRefreshOff}
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh((value) => !value)}
          >
            {autoRefresh ? trc.releases.autoRefreshStop : trc.releases.autoRefreshStart}
          </Button>
        </div>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-[minmax(18rem,26rem)_minmax(0,1fr)]">
        <section aria-label={trc.releases.listLabel} className="flex min-w-0 flex-col gap-3">
          <div className="flex flex-col gap-1">
            <span id={filterLabelId} className="text-sm font-medium">
              {trc.releases.filterLabel}
            </span>
            <Select
              value={flavor ?? ALL}
              onValueChange={(value) =>
                setParams(withParams(params, { derleme: value === ALL ? null : value }))
              }
            >
              <SelectTrigger aria-labelledby={filterLabelId}>
                <SelectValue>
                  {(value: string | null) =>
                    value === null || value === ALL
                      ? trc.releases.filterAll
                      : labelOf(trc.flavor, value)
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {FLAVOR_FILTERS.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item === ALL ? trc.releases.filterAll : labelOf(trc.flavor, item)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {admin ? <NewReleasePanel onAccepted={accepted} releaseHref={hrefFor} /> : null}

          {list.isPending ? (
            <div className="flex flex-col gap-2" data-testid="releases-loading">
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          ) : list.isError ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">{trc.releases.loadFailed}</p>
              <ProblemMessage error={list.error} />
              <div>
                <Button type="button" variant="outline" onClick={() => void list.refetch()}>
                  {tr.ui.retry}
                </Button>
              </div>
            </div>
          ) : items.length === 0 ? (
            <Empty data-testid="releases-empty">
              <EmptyHeader>
                <EmptyTitle>{trc.releases.empty}</EmptyTitle>
                <EmptyDescription>{trc.releases.emptyHint}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {items.map((item) => {
                const current = item.id === selectedId;
                return (
                  <li key={item.id}>
                    <Link
                      to={{ search: hrefFor(item.id) }}
                      aria-current={current ? 'true' : undefined}
                      className={cn(
                        'flex min-h-6 flex-col gap-1 rounded-lg border p-2 hover:bg-muted',
                        current && 'border-primary bg-muted',
                      )}
                    >
                      <span className="font-medium break-all">
                        {trc.releases.rowTitle(item.id, item.surum)}
                      </span>
                      <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="secondary">{labelOf(trc.flavor, item.derleme)}</Badge>
                        <Badge variant={item.durum === 'basarisiz' ? 'destructive' : 'outline'}>
                          {labelOf(trc.releaseStatus, item.durum)}
                        </Badge>
                        <span>{labelOf(trc.request, item.talep)}</span>
                        <span>{formatDateTime(item.created_at)}</span>
                      </span>
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

        <section aria-label={trc.releases.detailLabel} className="flex min-w-0 flex-col gap-4">
          {selectedId === null ? (
            <p className="text-sm text-muted-foreground">{trc.releases.selectPrompt}</p>
          ) : (
            <ReleaseDetailPane
              key={selectedId}
              id={selectedId}
              autoRefresh={autoRefresh}
              canPublish={admin}
              onAccepted={accepted}
              releaseHref={hrefFor}
              onPreparingChange={setDetailPreparing}
            />
          )}
        </section>
      </div>
    </div>
  );
}
