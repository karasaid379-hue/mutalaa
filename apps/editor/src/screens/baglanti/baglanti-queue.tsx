import { useState } from 'react';
import { MissingSection } from '@/components/missing-section';
import { OpenQuestionButton } from '@/components/open-question-button';
import { Checkbox } from '@/components/ui/checkbox';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { ApprovalStages, ReviewBadges } from '@/review/badges';
import { BulkDecision } from '@/review/bulk-decision';
import { DecisionForm } from '@/review/decision-form';
import { QueueLayout, type QueueDetailProps } from '@/review/queue-layout';
import type { ReviewItem } from '@/review/types';
import { BULK_ENABLED } from './config';
import { LinkEvidence, SampleEvidence } from './link-evidence';

const FILTER = { hedef_tablo: 'xref', alan: 'status' };

function Detail({ review, onDecided }: QueueDetailProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trBaglanti.detailHeading}</h2>
        <ReviewBadges review={review} showOrigin />
      </div>
      <LinkEvidence review={review} />
      <div className="grid gap-3 sm:grid-cols-2">
        <MissingSection title={trBaglanti.missing.highlighted} phase="A18" />
        <MissingSection title={trBaglanti.missing.evidence} phase="A18" />
        <MissingSection title={trBaglanti.missing.alternatives} phase="A18" />
        <MissingSection title={trBaglanti.missing.ordering} phase="A18" />
      </div>
      <section aria-label={trBaglanti.closedActions} className="flex flex-wrap gap-2">
        <OpenQuestionButton label={trBaglanti.closed.changeTarget} phase="A18" />
        <OpenQuestionButton label={trBaglanti.closed.fixRange} phase="A18" />
        <OpenQuestionButton label={trBaglanti.closed.changeType} phase="A18" />
        <OpenQuestionButton label={trBaglanti.closed.ima} phase="A18" />
        <OpenQuestionButton label={trBaglanti.closed.patternList} phase="A18" />
      </section>
      <ApprovalStages review={review} />
      <DecisionForm review={review} onDecided={onDecided} />
    </div>
  );
}

export interface BaglantiQueueProps {
  /**
   * Whether the bulk selection is open. The default is the constant `BULK_ENABLED` (false in production: K-48
   * karar 5). A test passes `true` to exercise the 10 percent sample flow.
   */
  bulkEnabled?: boolean;
}

/**
 * The link candidates queue (`xref` / `status`): the source paragraph, the candidate ayah and its meal, with
 * the missing A18 sections marked, a single decision form and a closed bulk selection. When `bulkEnabled` is on,
 * rows get a checkbox and the selection goes to `BulkDecision` with `sampling="tenth"`.
 */
export function BaglantiQueue({ bulkEnabled = BULK_ENABLED }: BaglantiQueueProps) {
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());

  function toggle(id: number, checked: boolean) {
    setSelected((previous) => {
      const next = new Set(previous);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  const clear = () => setSelected(new Set());

  return (
    <QueueLayout
      title={tr.nav.queueBaglanti}
      filter={FILTER}
      renderItem={(item: ReviewItem) =>
        bulkEnabled ? (
          <label className="flex min-h-6 items-center gap-2 text-sm">
            <Checkbox
              aria-label={trBaglanti.selectRow(item.hedef_anahtar)}
              checked={selected.has(item.id)}
              onCheckedChange={(value) => toggle(item.id, value)}
            />
            <span aria-hidden="true">{trBaglanti.selectShort}</span>
          </label>
        ) : null
      }
      renderListHeader={({ items, focusList }) => {
        if (!bulkEnabled) {
          return (
            <div>
              <OpenQuestionButton label={trBaglanti.closed.bulkSelect} phase="A18" />
            </div>
          );
        }
        const chosen = items.filter((item) => selected.has(item.id));
        return chosen.length === 0 ? null : (
          <section
            aria-label={trBaglanti.bulkRegion}
            className="flex flex-col gap-2 rounded-lg border p-3"
            data-testid="baglanti-bulk"
          >
            <p className="text-sm font-medium">{trBaglanti.selectedCount(chosen.length)}</p>
            <BulkDecision
              items={chosen}
              sampling="tenth"
              renderSample={(item) => <SampleEvidence item={item} />}
              onDone={() => {
                focusList();
                clear();
              }}
              onCancel={clear}
            />
          </section>
        );
      }}
      renderDetail={({ review, onDecided }) => (
        <Detail key={review.id} review={review} onDecided={onDecided} />
      )}
    />
  );
}
