import type { ReactNode } from 'react';
import { Link } from 'react-router';
import type { components } from '@/api/schema';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { ScrollRegion } from '@/components/scroll-region';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatDateTime, formatNumber } from '@/lib/format';
import { prettyJson } from './readers';

type Source = components['schemas']['SourceDto'];

const SOURCE_PATH = '/api/v1/sources/{slug}' as const;

function isWebAddress(value: string): boolean {
  return value.startsWith('https://') || value.startsWith('http://');
}

/** An address as a link when it is a web address, as plain text otherwise. */
function Address({ value }: { value: string }) {
  return isWebAddress(value) ? (
    <a href={value} rel="noreferrer noopener" target="_blank" className="break-all underline">
      {value}
    </a>
  ) : (
    <span className="break-all">{value}</span>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:grid sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  );
}

function Preformatted({
  value,
  label,
  dir,
}: {
  value: string;
  label: string;
  dir: 'auto' | 'ltr';
}) {
  // The text is placed as stored: no trim, no normalization (K-26). It scrolls, so it is a focusable region.
  return (
    <ScrollRegion
      label={trc.common.scrollArea(label)}
      dir={dir}
      className="max-h-96 overflow-auto rounded-lg border bg-muted/30 p-2 text-xs break-words whitespace-pre-wrap"
    >
      {value}
    </ScrollRegion>
  );
}

function SourceDetail({ source }: { source: Source }) {
  const sourceKind = labelOf(trc.sourceKind, source.tur);
  return (
    <article className="flex flex-col gap-4" aria-labelledby="source-title">
      <header className="flex flex-col gap-1">
        <h2 id="source-title" className="text-lg font-semibold">
          {source.baslik}
        </h2>
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="secondary">{sourceKind}</Badge>
          <span className="font-mono">{source.slug}</span>
        </p>
        <p className="text-xs text-muted-foreground">{trc.sources.readOnly}</p>
        <p className="text-xs text-muted-foreground">{trc.sources.recordNote(source.slug)}</p>
      </header>

      <dl className="flex flex-col gap-2">
        <Row label={trc.sources.slug}>
          <span className="font-mono">{source.slug}</span>
        </Row>
        <Row label={trc.sources.kind}>{sourceKind}</Row>
        <Row label={trc.sources.author}>{source.yazar ?? trc.common.notSet}</Row>
        <Row label={trc.sources.version}>{source.surum}</Row>
        <Row label={trc.sources.provider}>{source.provider ?? trc.common.notSet}</Row>
        <Row label={trc.sources.sourceUrl}>
          {source.kaynak_url ? <Address value={source.kaynak_url} /> : trc.common.notSet}
        </Row>
        <Row label={trc.sources.takenOn}>{source.alinma_tarihi ?? trc.common.notSet}</Row>
        <Row label={trc.sources.fileSha}>
          {source.dosya_sha256 ? (
            <code className="break-all">{source.dosya_sha256}</code>
          ) : (
            trc.common.notSet
          )}
        </Row>
        <Row label={trc.sources.units}>{formatNumber(source.birim_sayisi)}</Row>
        <Row label={trc.sources.citationUrl}>
          {source.atif_url ? <Address value={source.atif_url} /> : trc.common.notSet}
        </Row>
        <Row label={trc.sources.notes}>
          {source.notlar ? (
            <span dir="auto" className="whitespace-pre-wrap">
              {source.notlar}
            </span>
          ) : (
            trc.common.notSet
          )}
        </Row>
        <Row label={trc.sources.createdAt}>{formatDateTime(source.created_at)}</Row>
        <Row label={trc.sources.updatedAt}>{formatDateTime(source.updated_at)}</Row>
      </dl>

      <section className="flex flex-col gap-1" aria-labelledby="source-citation">
        <h3 id="source-citation" className="text-sm font-medium">
          {trc.sources.citation}
        </h3>
        <Preformatted value={source.atif_metni} label={trc.sources.citation} dir="auto" />
      </section>

      <section className="flex flex-col gap-1" aria-labelledby="source-notice">
        <h3 id="source-notice" className="text-sm font-medium">
          {trc.sources.notice}
        </h3>
        {source.notice_text !== null ? (
          <Preformatted value={source.notice_text} label={trc.sources.notice} dir="auto" />
        ) : (
          <p className="text-sm text-muted-foreground">{trc.common.notSet}</p>
        )}
      </section>

      {source.baski_bilgisi !== null && source.baski_bilgisi !== undefined ? (
        <section className="flex flex-col gap-1" aria-labelledby="source-print">
          <h3 id="source-print" className="text-sm font-medium">
            {trc.sources.printInfo}
          </h3>
          <Preformatted
            value={prettyJson(source.baski_bilgisi)}
            label={trc.sources.printInfo}
            dir="ltr"
          />
        </section>
      ) : null}

      <div>
        <Link
          to={{ pathname: '/birimler', search: `?kaynak=${encodeURIComponent(source.slug)}` }}
          className={buttonVariants({ variant: 'outline' })}
        >
          {trc.sources.showUnits}
        </Link>
      </div>
    </article>
  );
}

export function SourceDetailPane({ slug }: { slug: string }) {
  const api = useApi();
  const detail = api.$api.useQuery(
    'get',
    SOURCE_PATH,
    { params: { path: { slug } } },
    { retry: false },
  );
  if (detail.isPending) {
    return (
      <div className="flex flex-col gap-2" data-testid="source-detail-loading">
        <Skeleton className="h-8" />
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (detail.isError) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">{trc.sources.detailFailed}</p>
        <ProblemMessage error={detail.error} />
        <div>
          <Button type="button" variant="outline" onClick={() => void detail.refetch()}>
            {tr.ui.retry}
          </Button>
        </div>
      </div>
    );
  }
  return <SourceDetail source={detail.data} />;
}
