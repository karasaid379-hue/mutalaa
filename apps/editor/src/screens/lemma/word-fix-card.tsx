import { useId, useState, type ReactNode } from 'react';
import { fieldLabel, labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { ArabicText } from '@/components/arabic-text';
import { ReviewBadges } from '@/review/badges';
import { DecisionForm } from '@/review/decision-form';
import type { QueueDetailProps } from '@/review/queue-layout';
import type { ReviewDetail } from '@/review/types';
import { hasArabicLetters } from './payload';

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-wrap gap-x-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </div>
  );
}

/**
 * A QAC or proposed value: Arabic letters are Arabic text (`ArabicText`: `lang="ar"`, right to left, the Quran
 * font); anything else (ids, tags, feature strings) is technical and reads left to right. Shown as given.
 */
function FixValue({ value, testId }: { value: string; testId: string }) {
  return hasArabicLetters(value) ? (
    <ArabicText text={value} className="text-xl break-all" data-testid={testId} />
  ) : (
    <code dir="ltr" className="break-all" data-testid={testId}>
      {value}
    </code>
  );
}

/**
 * The correction the review is about (`hedef` of a `quran_word_fix`): the word anchor, the corrected field,
 * the QAC value and the proposed value, the reason and the proposing editor. Anchors and technical values
 * read left to right and Arabic values are Arabic text; the reason is Turkish. Nothing is recomputed: the values are shown as the API gave them.
 */
function Fix({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const target = review.hedef;
  const mismatch = target?.field != null && target.field !== review.alan;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-1 rounded-lg border p-3"
      data-testid="fix-snapshot"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trLemma.fix.heading}
      </h3>
      {target ? (
        <dl className="text-sm">
          {target.anchor ? (
            <Row label={trLemma.fix.anchor}>
              <code dir="ltr" className="break-all">
                {target.anchor}
              </code>
            </Row>
          ) : null}
          {target.field ? (
            <Row label={trLemma.fix.field}>
              {fieldLabel(target.field)}{' '}
              <code dir="ltr" className="text-xs text-muted-foreground">
                {target.field}
              </code>
            </Row>
          ) : null}
          {target.qac_value !== null && target.qac_value !== undefined ? (
            <Row label={trLemma.fix.qacValue}>
              <FixValue value={target.qac_value} testId="fix-qac-value" />
            </Row>
          ) : null}
          {target.new_value !== null && target.new_value !== undefined ? (
            <Row label={trLemma.fix.newValue}>
              <FixValue value={target.new_value} testId="fix-new-value" />
            </Row>
          ) : null}
          {target.reason ? (
            <Row label={trLemma.fix.reason}>
              <span lang="tr" dir="auto">
                {target.reason}
              </span>
            </Row>
          ) : null}
          {target.editor ? (
            <Row label={trLemma.fix.editor}>
              <span dir="auto">{target.editor}</span>
            </Row>
          ) : null}
          {target.status ? (
            <Row label={trLemma.fix.status}>
              {labelOf(tr.labels.candidateStatus, target.status)}
            </Row>
          ) : null}
          <Row label={trLemma.fix.reviewField}>
            {fieldLabel(review.alan)}{' '}
            <code dir="ltr" className="text-xs text-muted-foreground">
              {review.alan}
            </code>
          </Row>
        </dl>
      ) : (
        <p className="text-sm text-muted-foreground">{trLemma.fix.missing}</p>
      )}
      {mismatch ? (
        <p className="text-sm font-medium" role="note" data-testid="fix-mismatch">
          {trLemma.fix.mismatch}
        </p>
      ) : null}
    </section>
  );
}

/**
 * The card of a root and lemma correction (`quran_word_fix`; K-13, BÇ-12): the correction, the proposer and
 * the decision form. Only approval and rejection exist; the proposed value is not edited here and nothing is
 * sent to an expert (BÇ-61, A18), so the card has no edit field and no closed action.
 */
export function WordFixCard({ review, onDecided }: QueueDetailProps) {
  const [refreshed, setRefreshed] = useState<{ from: ReviewDetail; to: ReviewDetail } | null>(null);
  const shown = refreshed && refreshed.from === review ? refreshed.to : review;
  return (
    <div className="flex flex-col gap-4" data-testid="fix-card">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trLemma.heading.duzeltme}</h2>
        <ReviewBadges review={shown} showOrigin />
      </div>
      <Fix review={shown} />
      <p className="text-sm text-muted-foreground">{trLemma.fix.note}</p>
      <DecisionForm
        review={review}
        onDecided={onDecided}
        onRefreshed={(fresh) => setRefreshed({ from: review, to: fresh })}
      />
    </div>
  );
}
