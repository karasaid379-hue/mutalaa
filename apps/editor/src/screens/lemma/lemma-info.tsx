import { useId, type ReactNode } from 'react';
import type { components } from '@/api/schema';
import { useApi } from '@/app/api-context';
import { ArabicText } from '@/components/arabic-text';
import { ProblemMessage } from '@/components/problem-message';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { formatDecimal, formatNumber } from '@/lib/format';

type Detail = components['schemas']['LemmaDetailResponse'];
type Kwic = components['schemas']['LemmaKwicItem'];

const LEMMA_PATH = '/api/v1/lemmas/{id}' as const;

function Section({
  title,
  testId,
  children,
}: {
  title: string;
  testId: string;
  children: ReactNode;
}) {
  const headingId = useId();
  return (
    <section
      aria-labelledby={headingId}
      className="flex min-w-0 flex-col gap-1 rounded-lg border p-3"
      data-testid={testId}
    >
      <h4 id={headingId} className="text-sm font-medium">
        {title}
      </h4>
      {children}
    </section>
  );
}

/** A section with no data: a plain note, not an error. */
function NoData({ text = trLemma.info.noData }: { text?: string }) {
  return (
    <p className="text-sm text-muted-foreground" data-no-data="true">
      {text}
    </p>
  );
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

function RootSection({ kok }: { kok: Detail['kok'] }) {
  return (
    <Section title={trLemma.info.root.heading} testId="lemma-root">
      {kok === null ? (
        <NoData text={trLemma.info.root.none} />
      ) : (
        <dl className="text-sm">
          <Fact label={trLemma.info.root.letters}>
            <ArabicText text={kok.letters} className="text-xl" />
          </Fact>
          {kok.letters_bw ? (
            <Fact label={trLemma.info.root.buckwalter}>
              <code dir="ltr" lang="en" className="text-xs text-muted-foreground">
                {kok.letters_bw}
              </code>
            </Fact>
          ) : null}
          <Fact label={trLemma.info.root.occurrences}>{formatNumber(kok.occurrences)}</Fact>
          <Fact label={trLemma.info.root.ayahs}>{formatNumber(kok.ayah_count)}</Fact>
          {kok.idf_q !== null ? (
            <Fact label={trLemma.info.root.idf}>{formatDecimal(kok.idf_q)}</Fact>
          ) : null}
          {kok.kok_anlami ? (
            <Fact label={trLemma.info.root.meaning}>
              <span lang="tr">{kok.kok_anlami}</span>
            </Fact>
          ) : null}
        </dl>
      )}
    </Section>
  );
}

function PosSection({ rows }: { rows: Detail['tur_dagilimi'] }) {
  return (
    <Section title={trLemma.info.pos.heading} testId="lemma-pos">
      {rows.length === 0 ? (
        <NoData />
      ) : (
        <ul className="text-sm">
          {rows.map((row, index) => (
            <li key={`${index}:${row.pos ?? ''}`} className="flex flex-wrap gap-x-2">
              <span dir="ltr" lang="en">
                {row.pos ?? trLemma.info.pos.unknown}
              </span>
              <span className="text-muted-foreground">{trLemma.info.pos.count(row.sayi)}</span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

function FrequencySection({ siklik }: { siklik: Detail['siklik'] }) {
  return (
    <Section title={trLemma.info.frequency.heading} testId="lemma-frequency">
      <dl className="text-sm">
        <Fact label={trLemma.info.frequency.words}>{formatNumber(siklik.kelime)}</Fact>
        <Fact label={trLemma.info.frequency.ayahs}>{formatNumber(siklik.ayet)}</Fact>
      </dl>
    </Section>
  );
}

function WaveSection({ dalga }: { dalga: Detail['dalga'] }) {
  return (
    <Section title={trLemma.info.wave.heading} testId="lemma-wave">
      {dalga === null ? (
        <NoData />
      ) : (
        <p className="text-sm">{trLemma.info.wave.value(dalga.dalga, dalga.sira)}</p>
      )}
    </Section>
  );
}

function SameRootSection({ rows }: { rows: Detail['ayni_kok_anlamlari'] }) {
  return (
    <Section title={trLemma.info.sameRoot.heading} testId="lemma-same-root">
      {rows.length === 0 ? (
        <NoData />
      ) : (
        <ul className="flex flex-col gap-1 text-sm">
          {rows.map((row) => (
            <li key={row.lemma_id} className="flex flex-wrap items-baseline gap-x-2">
              <ArabicText text={row.text} className="text-lg" />
              <span lang="tr">{row.anlam_kisa}</span>
              <span className="text-muted-foreground">
                {trLemma.info.sameRoot.count(row.occurrences)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

/**
 * One KWIC example: the Tanzil context as stored (`sol`, `kelime`, `sag`; any of them may be null) and the
 * meal with its text status. Only a meal whose status is exactly `onayli` is shown without the unverified
 * mark; an unknown status is shown raw and still marked.
 */
function KwicRow({ item }: { item: Kwic }) {
  const hasText = item.sol !== null || item.kelime !== null || item.sag !== null;
  const meal = item.meal;
  const knownStatus =
    meal !== null && Object.hasOwn(trLemma.info.kwic.mealStatus, meal.metin_durumu);
  return (
    <li className="flex flex-col gap-1 rounded-md border p-2" data-testid="lemma-kwic-item">
      <p className="text-xs text-muted-foreground">
        {`${trLemma.info.kwic.ayah}: `}
        <code dir="ltr" className="break-all">
          {item.ayet_capa}
        </code>
        {` · ${trLemma.info.kwic.word}: `}
        <code dir="ltr" className="break-all">
          {item.kelime_capa}
        </code>
      </p>
      {hasText ? (
        <ArabicText as="p" className="text-lg">
          {item.sol}
          <mark className="rounded bg-primary/20 px-0.5 text-foreground">{item.kelime}</mark>
          {item.sag}
        </ArabicText>
      ) : (
        <p className="text-sm text-muted-foreground">{trLemma.info.kwic.textMissing}</p>
      )}
      {meal ? (
        <div className="flex flex-col gap-1 text-sm" data-testid="lemma-kwic-meal">
          <span className="flex flex-wrap items-center gap-1">
            <span className="text-muted-foreground">{trLemma.info.kwic.meal}</span>
            <Badge variant="outline">
              {labelOf(trLemma.info.kwic.mealStatus, meal.metin_durumu)}
            </Badge>
            {!knownStatus ? (
              <Badge variant="outline">{trLemma.info.kwic.mealUnverified}</Badge>
            ) : null}
          </span>
          <p lang="tr">{meal.metin}</p>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground" data-testid="lemma-kwic-no-meal">
          {trLemma.info.kwic.noMeal}
        </p>
      )}
    </li>
  );
}

function KwicSection({ rows }: { rows: Detail['kwic'] }) {
  return (
    <Section title={trLemma.info.kwic.heading} testId="lemma-kwic">
      {rows.length === 0 ? (
        <NoData />
      ) : (
        <>
          <p className="text-xs text-muted-foreground">{trLemma.info.kwic.note}</p>
          <ul className="flex flex-col gap-2">
            {rows.map((item) => (
              <KwicRow key={item.kelime_capa} item={item} />
            ))}
          </ul>
        </>
      )}
    </Section>
  );
}

export interface LemmaInfoProps {
  /** The lemma id (`hedef.lemma_id`); null when the review has no readable lemma, then nothing is requested. */
  lemmaId: number | null;
}

/**
 * The read-only lemma card of `GET /api/v1/lemmas/{id}` (BÇ-56): root, part of speech distribution, frequency,
 * wave and order, the approved meanings of the same root and the KWIC examples. A list with no rows or a
 * value that is null says "Veri yok" (it is not an error); nothing is invented. Every Arabic text is shown as
 * the API gave it (`lang="ar"`, `dir="rtl"`); Quran and meal text is never typed into the panel.
 */
export function LemmaInfo({ lemmaId }: LemmaInfoProps) {
  const api = useApi();
  const headingId = useId();
  const query = api.$api.useQuery(
    'get',
    LEMMA_PATH,
    { params: { path: { id: lemmaId ?? 0 } } },
    { enabled: lemmaId !== null, retry: false },
  );
  if (lemmaId === null) {
    return (
      <section aria-labelledby={headingId} className="flex flex-col gap-1" data-testid="lemma-info">
        <h3 id={headingId} className="text-sm font-medium">
          {trLemma.info.heading}
        </h3>
        <NoData text={trLemma.info.noId} />
      </section>
    );
  }
  return (
    <section
      aria-labelledby={headingId}
      aria-busy={query.isPending}
      className="flex flex-col gap-3"
      data-testid="lemma-info"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLemma.info.heading}
      </h3>
      {query.isPending ? (
        <div className="flex flex-col gap-2" data-testid="lemma-info-loading">
          <span className="sr-only">{trLemma.info.loading}</span>
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : query.isError ? (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">{trLemma.info.failed}</p>
          <ProblemMessage error={query.error} />
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="self-start"
            onClick={() => void query.refetch()}
          >
            {tr.ui.retry}
          </Button>
        </div>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <RootSection kok={query.data.kok} />
            <PosSection rows={query.data.tur_dagilimi} />
            <FrequencySection siklik={query.data.siklik} />
            <WaveSection dalga={query.data.dalga} />
          </div>
          <SameRootSection rows={query.data.ayni_kok_anlamlari} />
          <KwicSection rows={query.data.kwic} />
        </>
      )}
    </section>
  );
}
