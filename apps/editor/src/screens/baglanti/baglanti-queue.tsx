import { useMemo, useState } from 'react';
import { useApi } from '@/app/api-context';
import { Checkbox } from '@/components/ui/checkbox';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { canSendToExpert } from '@/lib/roles';
import { ApprovalStages, ReviewBadges } from '@/review/badges';
import { BulkDecision } from '@/review/bulk-decision';
import { DecisionForm } from '@/review/decision-form';
import type { LinkClass } from '@/review/queries';
import { ME_PATH, REVIEW_STATS_PATH, SESSION_QUERY_OPTIONS } from '@/review/queries';
import { QueueLayout, type QueueDetailProps } from '@/review/queue-layout';
import type { ReviewDetail, ReviewItem } from '@/review/types';
import { BULK_CLASS, BULK_ENABLED, linkFilter, type LinkStatusView } from './config';
import { ExpertAction, ImaAction, PatternAction } from './link-actions';
import { ClassBadge, ClassFilter, StatusView } from './link-class';
import { useLinkEditForm } from './link-edit-fields';
import { LinkEvidence, SampleEvidence } from './link-evidence';

function Detail({ review, onDecided, onLeft }: QueueDetailProps) {
  const api = useApi();
  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);
  // After a 412 the form hands over the fresh record; it is shown until the parent gives a new object.
  const [refreshed, setRefreshed] = useState<{ from: ReviewDetail; to: ReviewDetail } | null>(null);
  const shown = refreshed && refreshed.from === review ? refreshed.to : review;
  const { extraEdit, fields } = useLinkEditForm(shown);
  const open = shown.durum === 'acik';
  const showActions = open && canSendToExpert(me.data?.roller);
  return (
    <div className="flex flex-col gap-4" data-testid="link-card">
      <div className="flex flex-col gap-1">
        <h2 className="text-base font-semibold">{trBaglanti.detailHeading}</h2>
        <span className="flex flex-wrap items-center gap-1">
          <ReviewBadges review={shown} showOrigin />
          <ClassBadge sinif={shown.sinif ?? shown.hedef?.sinif} />
        </span>
      </div>
      <LinkEvidence review={shown} />
      <ApprovalStages review={shown} />
      <DecisionForm
        review={review}
        onDecided={onDecided}
        onRefreshed={(fresh) => setRefreshed({ from: review, to: fresh })}
        extraEdit={extraEdit}
        extraFields={shown.durum === 'acik' || shown.durum === 'uzmanda' ? fields : null}
      />
      {showActions ? (
        <section
          aria-label={trBaglanti.actions.heading}
          className="flex flex-col gap-3"
          data-testid="link-actions"
        >
          <h3 className="text-base font-medium">{trBaglanti.actions.heading}</h3>
          <ImaAction review={shown} />
          <PatternAction review={shown} onLeft={onLeft} />
          <ExpertAction review={shown} onLeft={onLeft} />
        </section>
      ) : null}
    </div>
  );
}

export interface BaglantiQueueProps {
  /**
   * Whether the bulk selection is open. The default is the constant `BULK_ENABLED` (true since A18.4: the API
   * gives the candidate class). A test passes `false` to see the queue without it.
   */
  bulkEnabled?: boolean;
}

/**
 * The link candidates queue (`xref` / `status`) in class order (`sira=sinif`: tutarsız, toplu uygun, gri bölge,
 * diğer): the source paragraph with its highlighted sequence, the candidate ayah and its meal, the evidence
 * summary and the alternatives, the decision form with the target, span and type edit, and the actions (ima,
 * kalıp listesi, uzmana gönder). The list filters by class and shows the records sent to an expert in a view of
 * their own. Rows of the `toplu` class get a checkbox; the selection goes to `BulkDecision` with
 * `sampling="tenth"` (a random 10 percent sample, one "Hatalı" cancels).
 */
export function BaglantiQueue({ bulkEnabled = BULK_ENABLED }: BaglantiQueueProps) {
  const api = useApi();
  const stats = api.$api.useQuery('get', REVIEW_STATS_PATH, undefined, { staleTime: 15_000 });
  const [status, setStatus] = useState<LinkStatusView>('acik');
  const [sinif, setSinif] = useState<LinkClass | 'hepsi'>('hepsi');
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const filter = useMemo(() => linkFilter(status, sinif), [status, sinif]);

  const eligible = (item: ReviewItem) =>
    bulkEnabled && status === 'acik' && item.sinif === BULK_CLASS;

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
      filter={filter}
      announceCount
      renderItemMeta={(item) => <ClassBadge sinif={item.sinif} />}
      renderItem={(item: ReviewItem) =>
        eligible(item) ? (
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
        const chosen = items.filter((item) => eligible(item) && selected.has(item.id));
        return (
          <div className="flex flex-col gap-3">
            <StatusView value={status} onChange={setStatus} stats={stats.data} />
            <ClassFilter value={sinif} onChange={setSinif} stats={stats.data} />
            {bulkEnabled && status === 'acik' ? (
              <p className="text-xs text-muted-foreground">{trBaglanti.bulkNote}</p>
            ) : null}
            {chosen.length === 0 ? null : (
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
            )}
          </div>
        );
      }}
      renderDetail={({ review, onDecided, onLeft }) => (
        <Detail key={review.id} review={review} onDecided={onDecided} onLeft={onLeft} />
      )}
    />
  );
}
