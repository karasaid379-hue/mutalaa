import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatDateTime, formatNumber } from '@/lib/format';
import type { UnitDetail as UnitDetailData } from '@/review/types';
import { checkUnitAnchor } from './anchor-check';
import { JsonBlock } from './json-block';
import { MarkedText, MarksTable } from './marked-text';
import { cpLength } from './readers';
import { SentencesTable } from './sentences-table';
import { UnitCorrection } from './unit-correction';

const UNIT_PATH = '/api/v1/units/{anchor}' as const;

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5 sm:grid sm:grid-cols-[12rem_minmax(0,1fr)] sm:gap-3">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-sm">{children}</dd>
    </div>
  );
}

function isArabicUnit(unit: Pick<UnitDetailData, 'kind' | 'kaynak_tur'>): boolean {
  return unit.kind === 'ayet' || unit.kaynak_tur === 'kuran_metni';
}

/** The detail of a loaded unit: the canonical text with its marks, the hashes and states, the derived ranges and the correction. */
export function UnitDetailView({ unit }: { unit: UnitDetailData }) {
  const length = cpLength(unit.metin);
  return (
    <article className="flex flex-col gap-4" aria-labelledby="unit-anchor">
      <header className="flex flex-col gap-1">
        <h2 id="unit-anchor" className="font-mono text-lg font-semibold break-all">
          {unit.anchor}
        </h2>
        <p className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="secondary">{labelOf(trc.unitKind, unit.kind)}</Badge>
          <Badge variant="secondary">{labelOf(trc.sourceKind, unit.kaynak_tur)}</Badge>
          <Badge variant="outline">{labelOf(tr.labels.textStatus, unit.metin_durumu)}</Badge>
          <Badge variant={unit.status === 'kullanim_disi' ? 'destructive' : 'outline'}>
            {labelOf(trc.unitStatus, unit.status)}
          </Badge>
        </p>
      </header>

      <section className="flex flex-col gap-1" aria-labelledby="unit-text">
        <h3 id="unit-text" className="text-sm font-medium">
          {trc.units.text}
        </h3>
        <p className="text-xs text-muted-foreground">{trc.units.textNote}</p>
        <div className="rounded-lg border p-3" data-testid="unit-text">
          <MarkedText text={unit.metin} marks={unit.marks} arabic={isArabicUnit(unit)} />
        </div>
      </section>

      <UnitCorrection key={`${unit.anchor}:${unit.content_hash}`} unit={unit} />

      <dl className="flex flex-col gap-2">
        <Row label={trc.units.contentHash}>
          <code className="break-all">{unit.content_hash}</code>
        </Row>
        <Row label={trc.units.textStatus}>{labelOf(tr.labels.textStatus, unit.metin_durumu)}</Row>
        <Row label={trc.units.status}>{labelOf(trc.unitStatus, unit.status)}</Row>
        <Row label={trc.units.sourceLink}>
          <Link
            to={{ pathname: '/kaynaklar', search: `?kaynak=${encodeURIComponent(unit.source)}` }}
            className="font-mono underline"
          >
            {unit.source}
          </Link>
        </Row>
        <Row label={trc.units.role}>{unit.role}</Row>
        <Row label={trc.units.ord}>{formatNumber(unit.ord)}</Row>
        <Row label={trc.units.rev}>{formatNumber(unit.rev)}</Row>
        <Row label={trc.units.parentPath}>
          {unit.parent_path ? (
            <span className="font-mono">{unit.parent_path}</span>
          ) : (
            trc.common.none
          )}
        </Row>
        <Row label={trc.units.ayahRange}>
          {unit.ayah_range ? <code>{JSON.stringify(unit.ayah_range)}</code> : trc.common.none}
        </Row>
        <Row label={trc.units.dataVersion}>{unit.data_version}</Row>
        <Row label={trc.units.createdAt}>{formatDateTime(unit.created_at)}</Row>
        <Row label={trc.units.updatedAt}>{formatDateTime(unit.updated_at)}</Row>
      </dl>

      <MarksTable marks={unit.marks} textLength={length} />
      <SentencesTable sentences={unit.sentences} textLength={length} />

      <div className="flex flex-col gap-2">
        <JsonBlock title={trc.units.attrs} value={unit.attrs} />
        <JsonBlock title={trc.units.successors} value={unit.successors} />
        <JsonBlock title={trc.units.provenance} value={unit.provenance} />
      </div>
    </article>
  );
}

/**
 * The right-hand side of the units screen: checks the anchor on the client first (an invalid one never
 * reaches the API), then loads `GET /units/{anchor}`. The anchor is handed over raw; the client encodes the
 * path segment once.
 */
export function UnitDetailPane({ anchor }: { anchor: string }) {
  const api = useApi();
  const check = checkUnitAnchor(anchor);
  const detail = api.$api.useQuery(
    'get',
    UNIT_PATH,
    { params: { path: { anchor } } },
    { enabled: check.ok, retry: false },
  );

  if (!check.ok) {
    return (
      <Alert variant="destructive" data-testid="anchor-invalid">
        <AlertTitle>{trc.units.anchorInvalidTitle}</AlertTitle>
        <AlertDescription className="flex flex-col gap-1">
          <p className="font-mono break-all">{anchor}</p>
          {check.reason === 'invalid' ? (
            <>
              <p>{trc.units.anchorErrors[check.code] ?? trc.units.anchorUnknownError}</p>
              <p>{trc.units.anchorErrorCode(check.code)}</p>
            </>
          ) : (
            <p>{trc.units.anchorNotUnit}</p>
          )}
        </AlertDescription>
      </Alert>
    );
  }
  if (detail.isPending) {
    return (
      <div className="flex flex-col gap-2" data-testid="unit-detail-loading">
        <Skeleton className="h-8" />
        <Skeleton className="h-32" />
      </div>
    );
  }
  if (detail.isError) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">{trc.units.detailFailed}</p>
        <ProblemMessage error={detail.error} />
        <div>
          <Button type="button" variant="outline" onClick={() => void detail.refetch()}>
            {tr.ui.retry}
          </Button>
        </div>
      </div>
    );
  }
  return <UnitDetailView unit={detail.data} />;
}
