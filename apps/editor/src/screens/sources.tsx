import { Link, useSearchParams } from 'react-router';
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
import { formatNumber } from '@/lib/format';
import { cn } from '@/lib/utils';
import { SourceDetailPane } from './catalog/source-detail';

const SOURCES_PATH = '/api/v1/sources' as const;

/**
 * Sources (A15.5): a read-only list and detail of the source records (`GET /sources`, `/sources/{slug}`).
 * The record lives in `pipeline/sources/{slug}.toml`; the panel only shows it. `notice_text` and the
 * citation are shown as stored inside `pre`. The selected source is kept in `?kaynak=`.
 */
export function Component() {
  const api = useApi();
  const [params] = useSearchParams();
  const selected = params.get('kaynak');
  const list = api.$api.useQuery('get', SOURCES_PATH, undefined, { retry: false });

  return (
    <div className="flex flex-col gap-4">
      <PageHeading>{tr.nav.sources}</PageHeading>
      <div className="grid gap-4 lg:grid-cols-[minmax(16rem,22rem)_minmax(0,1fr)]">
        <section aria-label={trc.sources.listLabel} className="flex flex-col gap-3">
          {list.isPending ? (
            <div className="flex flex-col gap-2" data-testid="sources-loading">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : list.isError ? (
            <div className="flex flex-col gap-2">
              <p className="text-sm font-medium">{trc.sources.loadFailed}</p>
              <ProblemMessage error={list.error} />
              <Button type="button" variant="outline" onClick={() => void list.refetch()}>
                {tr.ui.retry}
              </Button>
            </div>
          ) : list.data.length === 0 ? (
            <Empty data-testid="sources-empty">
              <EmptyHeader>
                <EmptyTitle>{trc.sources.empty}</EmptyTitle>
                <EmptyDescription>{trc.sources.emptyHint}</EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <ul className="flex flex-col gap-2">
              {list.data.map((source) => (
                <li key={source.slug}>
                  <Link
                    to={{ search: `?kaynak=${encodeURIComponent(source.slug)}` }}
                    aria-current={source.slug === selected ? 'true' : undefined}
                    className={cn(
                      'flex min-h-6 flex-col gap-1 rounded-lg border p-2 hover:bg-muted',
                      source.slug === selected && 'border-primary bg-muted',
                    )}
                  >
                    <span className="font-medium break-words">{source.baslik}</span>
                    <span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-mono">{source.slug}</span>
                      <Badge variant="secondary">{labelOf(trc.sourceKind, source.tur)}</Badge>
                      <span>{trc.sources.unitCount(formatNumber(source.birim_sayisi))}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
        <section aria-label={trc.sources.detailLabel} className="min-w-0">
          {selected === null || selected === '' ? (
            <p className="text-sm text-muted-foreground">{trc.sources.selectPrompt}</p>
          ) : (
            <SourceDetailPane key={selected} slug={selected} />
          )}
        </section>
      </div>
    </div>
  );
}
