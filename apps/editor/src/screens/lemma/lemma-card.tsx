import { useId, useState, type ReactNode } from 'react';
import { ArabicText } from '@/components/arabic-text';
import { OpenQuestionButton } from '@/components/open-question-button';
import { TextDiff } from '@/components/text-diff';
import { Badge } from '@/components/ui/badge';
import { labelOf, originLabel, targetLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { formatNumber, formatPercent } from '@/lib/format';
import { ReviewBadges } from '@/review/badges';
import { DecisionForm } from '@/review/decision-form';
import type { QueueDetailProps } from '@/review/queue-layout';
import type { ReviewDetail } from '@/review/types';
import { JsonBlock } from '@/screens/catalog/json-block';
import { LemmaInfo } from './lemma-info';
import {
  CONSISTENT_SHARE_THRESHOLD,
  consistencyOf,
  isAnchor,
  isReadyCandidate,
  isShare,
  readConfidence,
  readDistribution,
  readLemmaId,
  readLemmaValue,
  readYzRecord,
  type LemmaValue,
} from './payload';

/** The source of a meaning or lemma: `kaynak:<slug>` is a ready source; an unknown origin is shown raw. */
function glossOriginLabel(origin: string): string {
  const prefix = 'kaynak:';
  return origin.startsWith(prefix)
    ? trLemma.snapshot.readySource(origin.slice(prefix.length))
    : labelOf(trLemma.snapshot.originNames, origin);
}

function yesNo(value: boolean): string {
  return value ? trLemma.snapshot.yes : trLemma.snapshot.no;
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

/** The target row as the API sees it now (`hedef`): ids and the Arabic lemma as stored, nothing recomputed. */
function Snapshot({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const target = review.hedef;
  // A lemma row carries `etymological_only`, a meaning row `yalnizca_etimolojik`: one row, whichever is there.
  const etymological = target?.etymological_only ?? target?.yalnizca_etimolojik ?? null;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="lemma-snapshot"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLemma.snapshot.heading}
      </h3>
      {target ? (
        <dl className="text-sm">
          <Row label={trLemma.snapshot.table}>{targetLabel(target.tablo)}</Row>
          {target.lemma_id !== null && target.lemma_id !== undefined ? (
            <Row label={trLemma.snapshot.lemmaId}>{String(target.lemma_id)}</Row>
          ) : null}
          {target.lang ? (
            <Row label={trLemma.snapshot.lang}>
              {labelOf(trLemma.snapshot.langNames, target.lang)}
            </Row>
          ) : null}
          {target.text ? (
            <Row label={trLemma.snapshot.lemma}>
              {target.lang === 'ar' ? (
                <ArabicText text={target.text} className="text-xl" />
              ) : (
                <span lang={target.lang ?? undefined}>{target.text}</span>
              )}
            </Row>
          ) : null}
          {target.anlam_kisa ? (
            <Row label={trLemma.snapshot.anlamKisa}>
              <span lang="tr">{target.anlam_kisa}</span>
            </Row>
          ) : null}
          {target.origin ? (
            <Row label={trLemma.snapshot.origin}>{glossOriginLabel(target.origin)}</Row>
          ) : null}
          {target.version ? <Row label={trLemma.snapshot.version}>{target.version}</Row> : null}
          {target.root_id !== null && target.root_id !== undefined ? (
            <Row label={trLemma.snapshot.root}>{String(target.root_id)}</Row>
          ) : null}
          {target.occurrences !== null && target.occurrences !== undefined ? (
            <Row label={trLemma.snapshot.occurrences}>{formatNumber(target.occurrences)}</Row>
          ) : null}
          {etymological !== null ? (
            <Row label={trLemma.snapshot.etymologicalOnly}>{yesNo(etymological)}</Row>
          ) : null}
          {target.status ? (
            <Row label={trLemma.snapshot.status}>
              {labelOf(tr.labels.candidateStatus, target.status)}
            </Row>
          ) : null}
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">{trLemma.snapshot.missing}</p>
      )}
    </section>
  );
}

function ValueView({ value, raw }: { value: LemmaValue; raw: unknown }) {
  return (
    <div className="flex flex-col gap-1 text-sm">
      {value.plain !== null ? <p lang="tr">{value.plain}</p> : null}
      <dl>
        {value.anlamKisa !== null ? (
          <Row label={trLemma.values.anlamKisa}>
            <span lang="tr">{value.anlamKisa}</span>
          </Row>
        ) : null}
        {value.kuranAnlamlari.length > 0 ? (
          <Row label={trLemma.values.kuranAnlamlari}>
            <ul className="list-disc pl-4" lang="tr">
              {value.kuranAnlamlari.map((entry, index) => (
                <li key={`${index}:${entry}`}>{entry}</li>
              ))}
            </ul>
          </Row>
        ) : null}
        {value.turkceEsKelime !== null ? (
          <Row label={trLemma.values.turkceEsKelime}>
            <span lang="tr">{value.turkceEsKelime}</span>
          </Row>
        ) : null}
        {value.status !== null ? (
          <Row label={trLemma.values.status}>
            {labelOf(tr.labels.candidateStatus, value.status)}
          </Row>
        ) : null}
        {value.dayanakAyetler.length > 0 ? (
          <Row label={trLemma.values.dayanak}>
            <ul className="flex flex-wrap gap-x-3">
              {value.dayanakAyetler.map((entry, index) => (
                <li key={`${index}:${entry}`} className="break-all">
                  {entry}
                  {isAnchor(entry) ? '' : ` (${trLemma.values.notAnchor})`}
                </li>
              ))}
            </ul>
          </Row>
        ) : null}
        {value.gerekce !== null ? (
          <Row label={trLemma.values.gerekce}>
            <span lang="tr">{value.gerekce}</span>
          </Row>
        ) : null}
      </dl>
      {value.eminDegil === true || value.yalnizcaEtimolojikAdayi === true ? (
        <span className="flex flex-wrap gap-1">
          {value.eminDegil === true ? (
            <Badge variant="outline">{trLemma.values.eminDegil}</Badge>
          ) : null}
          {value.yalnizcaEtimolojikAdayi === true ? (
            <Badge variant="outline">{trLemma.values.etimolojikAday}</Badge>
          ) : null}
        </span>
      ) : null}
      {value.known ? null : <p className="text-muted-foreground">{trLemma.values.unreadable}</p>}
      {value.plain === null ? <JsonBlock title={trLemma.values.raw} value={raw} /> : null}
    </div>
  );
}

function ValueSection({ label, raw, value }: { label: string; raw: unknown; value: LemmaValue }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-1">
      <h4 id={headingId} className="text-sm font-medium">
        {label}
      </h4>
      <ValueView value={value} raw={raw} />
    </section>
  );
}

/** The previous, proposed and edited values (the three opaque fields), each read with the lemma readers. */
function Values({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const before = readLemmaValue(review.onceki);
  const proposed = readLemmaValue(review.onerilen);
  const edited = readLemmaValue(review.duzenlenen);
  const beforeText = before?.anlamKisa ?? null;
  const proposedText = proposed?.anlamKisa ?? null;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-3 rounded-lg border p-3"
      data-testid="lemma-values"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLemma.values.heading}
      </h3>
      {before ? (
        <ValueSection label={trLemma.values.onceki} raw={review.onceki} value={before} />
      ) : null}
      {proposed ? (
        <ValueSection label={trLemma.values.onerilen} raw={review.onerilen} value={proposed} />
      ) : null}
      {beforeText !== null && proposedText !== null && beforeText !== proposedText ? (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-muted-foreground">{trLemma.values.diff}</p>
          <TextDiff before={beforeText} after={proposedText} className="text-sm" />
        </div>
      ) : null}
      {edited ? (
        <ValueSection label={trLemma.values.duzenlenen} raw={review.duzenlenen} value={edited} />
      ) : null}
      {!before && !proposed && !edited ? (
        <p className="text-sm text-muted-foreground">{trLemma.values.none}</p>
      ) : null}
    </section>
  );
}

/**
 * Origin of the draft, the G-YZ record of an AI draft and the dominant share of a ready-source candidate:
 * as a percentage, with the consistent or inconsistent mark (threshold `CONSISTENT_SHARE_THRESHOLD`) and the
 * distribution of the ready meanings, which is shown but never applied (K-50 madde 5).
 */
function Origin({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const distributionId = useId();
  const yz = readYzRecord(review.yz_kaydi);
  const confidence = readConfidence(review);
  const ready = isReadyCandidate(review);
  const readable = confidence !== null && isShare(confidence);
  const distribution = readDistribution(review.onerilen);
  return (
    <div className="flex flex-col gap-3">
      <section
        aria-labelledby={headingId}
        className="flex flex-col gap-1 rounded-lg border p-3"
        data-testid="lemma-origin"
      >
        <h3 id={headingId} className="text-sm font-medium">
          {trLemma.origin.heading}
        </h3>
        <dl className="text-sm">
          <Row label={trLemma.origin.origin}>{originLabel(review.koken)}</Row>
          <Row label={trLemma.origin.proposer}>{review.oneren}</Row>
          {review.yz_modeli ? <Row label={trLemma.origin.aiModel}>{review.yz_modeli}</Row> : null}
          {yz?.promptId ? <Row label={trLemma.origin.promptId}>{yz.promptId}</Row> : null}
          {yz?.promptSha256 ? (
            <Row label={trLemma.origin.promptSha}>
              <span className="break-all">{yz.promptSha256}</span>
            </Row>
          ) : null}
          {yz?.inputSha256 ? (
            <Row label={trLemma.origin.inputSha}>
              <span className="break-all">{yz.inputSha256}</span>
            </Row>
          ) : null}
          {confidence !== null && readable ? (
            <Row label={ready ? trLemma.origin.dominantShare : trLemma.origin.confidence}>
              {formatPercent(confidence)}
            </Row>
          ) : null}
        </dl>
        {confidence !== null && !readable ? (
          <p className="text-sm text-muted-foreground" data-testid="lemma-confidence-unreadable">
            {trLemma.origin.shareUnreadable}
          </p>
        ) : confidence !== null && ready ? (
          <p className="flex flex-wrap items-center gap-2 text-sm" data-testid="lemma-consistency">
            <Badge variant={consistencyOf(confidence) === 'tutarli' ? 'secondary' : 'outline'}>
              {consistencyOf(confidence) === 'tutarli'
                ? trLemma.origin.consistent
                : trLemma.origin.inconsistent}
            </Badge>
            <span className="text-muted-foreground">
              {trLemma.origin.consistentHint(
                formatPercent(confidence),
                formatPercent(CONSISTENT_SHARE_THRESHOLD),
              )}
            </span>
          </p>
        ) : confidence === null ? (
          <p className="text-sm text-muted-foreground" data-testid="lemma-confidence-none">
            {trLemma.origin.confidenceNone}
          </p>
        ) : null}
        {review.dogrulanmamis ? <p className="text-sm">{trLemma.origin.unverifiedNote}</p> : null}
        {review.yz_kaydi !== null && review.yz_kaydi !== undefined ? (
          <JsonBlock title={trLemma.origin.yzRaw} value={review.yz_kaydi} />
        ) : null}
      </section>
      {distribution.length > 0 ? (
        <section
          aria-labelledby={distributionId}
          className="flex flex-col gap-1 rounded-lg border p-3"
          data-testid="lemma-distribution"
        >
          <h3 id={distributionId} className="text-sm font-medium">
            {trLemma.origin.distribution}
          </h3>
          <p className="text-xs text-muted-foreground">{trLemma.origin.distributionNote}</p>
          <ul className="text-sm">
            {distribution.map((entry, index) => (
              <li key={`${index}:${entry.anlam}`} className="flex flex-wrap gap-x-2">
                <span lang="tr">{entry.anlam}</span>
                <span className="text-muted-foreground">
                  {trLemma.origin.distributionEntry(entry.sayi)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

/**
 * The card of one lemma review: the target's snapshot, the values the API gives (previous, proposed, edited),
 * origin and confidence, the lemma card of `GET /lemmas/{id}` (root, frequency, wave, same-root meanings,
 * KWIC), the closed actions and the decision form. A word meaning review (`lemma_gloss`) can be approved with
 * an edited meaning (the form shows the field); a lemma status review is a status approval or a rejection only.
 */
export function LemmaCard({ review, onDecided }: QueueDetailProps) {
  // After a 412 the form hands over the fresh record; it is shown until the parent gives a new object.
  const [refreshed, setRefreshed] = useState<{ from: ReviewDetail; to: ReviewDetail } | null>(null);
  const shown = refreshed && refreshed.from === review ? refreshed.to : review;
  const heading = shown.hedef_tablo === 'lemma' ? trLemma.heading.durum : trLemma.heading.anlam;
  return (
    <div className="flex flex-col gap-4" data-testid="lemma-card">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{heading}</h2>
        <ReviewBadges review={shown} showOrigin />
      </div>
      <Snapshot review={shown} />
      <Values review={shown} />
      <Origin review={shown} />
      <LemmaInfo lemmaId={readLemmaId(shown)} />
      <section aria-label={trLemma.closedActions} className="flex flex-col gap-1">
        <div className="flex flex-wrap gap-2">
          <OpenQuestionButton label={trLemma.closed.sendExpert} phase="A18" />
          <OpenQuestionButton label={trLemma.closed.redraft} phase="S-16" />
          <OpenQuestionButton label={trLemma.closed.etymologicalOnly} phase="A18" />
        </div>
        <p className="text-xs text-muted-foreground">{trLemma.closedNote}</p>
      </section>
      <p className="text-sm text-muted-foreground">
        {shown.hedef_tablo === 'lemma' ? trLemma.decisionNote.durum : trLemma.decisionNote.anlam}
      </p>
      <DecisionForm
        review={review}
        onDecided={onDecided}
        onRefreshed={(fresh) => setRefreshed({ from: review, to: fresh })}
      />
    </div>
  );
}
