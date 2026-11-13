import { useId, type ReactNode } from 'react';
import { useApi } from '@/app/api-context';
import { ArabicText } from '@/components/arabic-text';
import { ProblemMessage } from '@/components/problem-message';
import { labelOf, originLabel } from '@/i18n/labels';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { formatDecimal, formatPercent } from '@/lib/format';
import { REVIEW_PATH, reviewDetailInit } from '@/review/queries';
import type { ReviewDetail, ReviewItem } from '@/review/types';
import { hasArabicLetters } from '@/screens/lemma/payload';
import {
  hasSummaryFacts,
  readEvidence,
  readHighlight,
  readSpan,
  type EvidenceFacts,
} from './link-snapshot';
import { targetInfo } from './target';

interface UnitSectionProps {
  label: string;
  anchor: string;
  /** Arabic text of an ayah: drawn with `ArabicText` (Amiri, RTL), as stored. */
  arabic?: boolean;
}

/** The text of one unit as the API gives it (`GET /units/{anchor}`); nothing is changed or written here. */
function UnitSection({ label, anchor, arabic = false }: UnitSectionProps) {
  const api = useApi();
  const headingId = useId();
  const unit = api.$api.useQuery(
    'get',
    '/api/v1/units/{anchor}',
    { params: { path: { anchor } } },
    { retry: false },
  );
  return (
    // A group, not a region landmark: the same names repeat in every sampled row (axe landmark-unique).
    <div
      role="group"
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {label}
      </h3>
      <p className="text-xs text-muted-foreground break-all">{anchor}</p>
      {unit.isPending ? (
        <p className="text-sm text-muted-foreground">{trBaglanti.textLoading}</p>
      ) : unit.isError ? (
        <div className="flex flex-col gap-1">
          <p className="text-sm font-medium">{trBaglanti.textFailed}</p>
          <ProblemMessage error={unit.error} />
        </div>
      ) : arabic ? (
        <ArabicText as="p" text={unit.data.metin} />
      ) : (
        <p lang="tr" dir="auto" className="text-sm whitespace-pre-wrap">
          {unit.data.metin}
        </p>
      )}
    </div>
  );
}

/**
 * The highlighted sequence of the source paragraph (`vurgulu_dizi`: before, sequence, after). The sequence is a
 * `<mark>`; an Arabic sequence is Arabic text (`lang="ar"`, right to left). When the paragraph changed after the
 * link was found, the API gives nothing and the section says "Metin güncel değil".
 */
function HighlightSection({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const highlight = readHighlight(review.hedef?.vurgulu_dizi);
  return (
    <div
      role="group"
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="link-highlight"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trBaglanti.highlight.heading}
      </h3>
      {highlight === null ? (
        <>
          <p className="text-sm font-medium" data-testid="link-highlight-stale">
            {trBaglanti.highlight.stale}
          </p>
          <p className="text-xs text-muted-foreground">{trBaglanti.highlight.staleHint}</p>
        </>
      ) : (
        <p dir="auto" className="text-sm whitespace-pre-wrap" data-testid="link-highlight-text">
          {highlight.before ? <span lang="tr">{highlight.before}</span> : null}
          {hasArabicLetters(highlight.sequence) ? (
            <mark lang="ar" dir="rtl" className="font-quran text-xl">
              {highlight.sequence}
            </mark>
          ) : (
            <mark lang="tr">{highlight.sequence}</mark>
          )}
          {highlight.after ? <span lang="tr">{highlight.after}</span> : null}
        </p>
      )}
    </div>
  );
}

/** "Kapsama %40 · 7 eşleşen kelime · Kur'an'da 1 âyette · açık atıf yok …": the facts of the evidence as one line. */
function summaryParts(facts: EvidenceFacts): string[] {
  const text = trBaglanti.evidence;
  const parts: string[] = [];
  if (facts.coverage !== null) parts.push(text.coverage(formatPercent(facts.coverage)));
  if (facts.matchedWords !== null) parts.push(text.matchedWords(facts.matchedWords));
  if (facts.ayahWords !== null) parts.push(text.ayahWords(facts.ayahWords));
  if (facts.phraseFreq !== null) parts.push(text.phraseFreq(facts.phraseFreq));
  if (facts.consistentQuote !== null) {
    parts.push(facts.consistentQuote ? text.quoteYes : text.quoteNo);
  }
  if (facts.identity !== null) parts.push(text.identity(formatPercent(facts.identity)));
  if (facts.position !== null) parts.push(text.position(facts.position));
  if (facts.subtype !== null) parts.push(text.subtype(facts.subtype));
  if (facts.group !== null) parts.push(text.group(facts.group));
  if (facts.editorFix) parts.push(text.editorFix);
  return parts;
}

function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

/** The type, origin, score, confidence and spans of the candidate (`hedef`), as the API gave them. */
function LinkFacts({ review }: { review: ReviewDetail }) {
  const target = review.hedef;
  if (!target) return null;
  const text = trBaglanti.evidence;
  const src = readSpan(target.src_span);
  const dst = readSpan(target.dst_span);
  return (
    <dl className="text-sm" aria-label={text.facts} data-testid="link-facts">
      {target.type ? <Fact label={text.type}>{labelOf(trBaglanti.types, target.type)}</Fact> : null}
      {target.origin ? <Fact label={text.origin}>{originLabel(target.origin)}</Fact> : null}
      {typeof target.score === 'number' ? (
        <Fact label={text.score}>{formatDecimal(target.score)}</Fact>
      ) : null}
      {typeof target.confidence === 'number' ? (
        <Fact label={text.confidence}>{formatDecimal(target.confidence)}</Fact>
      ) : null}
      {src ? (
        <Fact label={text.srcSpan}>
          <code dir="ltr">{text.spanValue(src[0], src[1])}</code>
        </Fact>
      ) : null}
      {dst ? (
        <Fact label={text.dstSpan}>
          <code dir="ltr">{text.spanValue(dst[0], dst[1])}</code>
        </Fact>
      ) : null}
    </dl>
  );
}

/** The evidence summary (`evidence_ozeti`) and the facts of the candidate. Nothing is invented for a missing value. */
function EvidenceSection({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const facts = readEvidence(review.hedef?.evidence_ozeti);
  return (
    <div
      role="group"
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="link-evidence-summary"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trBaglanti.evidence.heading}
      </h3>
      {facts !== null && hasSummaryFacts(facts) ? (
        <p className="text-sm" data-testid="link-evidence-line">
          {summaryParts(facts).join(' · ')}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">{trBaglanti.evidence.none}</p>
      )}
      <LinkFacts review={review} />
      <p className="text-xs text-muted-foreground">{trBaglanti.evidence.spanNote}</p>
    </div>
  );
}

/** The alternative targets of the evidence, as the API gave them (their keys are technical names). */
function AlternativesSection({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const facts = readEvidence(review.hedef?.evidence_ozeti);
  const alternatives = facts?.alternatives ?? [];
  return (
    <div
      role="group"
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="link-alternatives"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trBaglanti.alternatives.heading}
      </h3>
      {alternatives.length === 0 ? (
        <p className="text-sm text-muted-foreground">{trBaglanti.alternatives.none}</p>
      ) : (
        <ol className="flex flex-col gap-1 text-sm">
          {alternatives.map((alternative, index) => (
            <li key={index} className="flex flex-wrap gap-x-3" data-testid="link-alternative">
              <span className="text-muted-foreground">
                {trBaglanti.alternatives.item(index + 1)}
              </span>
              {alternative.entries.map((entry, entryIndex) => (
                <span key={entryIndex} dir="auto">
                  {entry.key !== null ? <code dir="ltr">{entry.key}</code> : null}
                  {entry.key !== null ? ': ' : null}
                  {entry.value}
                </span>
              ))}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

/**
 * The evidence of a link candidate: the source paragraph and its highlighted sequence, the candidate ayah and its
 * meal, the evidence summary and the alternatives. The texts come from the units endpoint exactly as stored; the
 * highlight, the summary and the alternatives come from the `hedef` snapshot of the record.
 */
export function LinkEvidence({ review }: { review: ReviewDetail }) {
  const src = review.hedef?.src_anchor ?? null;
  const dst = review.hedef?.dst_anchor ?? null;
  if (!src && !dst) {
    return <p className="text-sm text-muted-foreground">{trBaglanti.noAnchors}</p>;
  }
  const info = dst ? targetInfo(dst) : null;
  return (
    <div className="flex flex-col gap-3" data-testid="link-evidence">
      {src ? <UnitSection label={trBaglanti.sourceParagraph} anchor={src} /> : null}
      <HighlightSection review={review} />
      {dst ? (
        <UnitSection label={trBaglanti.candidateAyah} anchor={dst} arabic={info?.ayah === true} />
      ) : null}
      {info?.mealAnchor ? (
        <UnitSection label={trBaglanti.meal} anchor={info.mealAnchor} />
      ) : dst ? (
        <p className="text-sm text-muted-foreground">{trBaglanti.mealNotShown}</p>
      ) : null}
      <EvidenceSection review={review} />
      <AlternativesSection review={review} />
    </div>
  );
}

/** The evidence of one sampled record of the bulk approval: it fetches the detail the list item lacks. */
export function SampleEvidence({ item }: { item: ReviewItem }) {
  const api = useApi();
  const detail = api.$api.useQuery('get', REVIEW_PATH, reviewDetailInit(item.id), {
    retry: false,
  });
  if (detail.isPending)
    return <p className="text-sm text-muted-foreground">{trBaglanti.textLoading}</p>;
  if (detail.isError) return <ProblemMessage error={detail.error} />;
  return <LinkEvidence review={detail.data} />;
}
