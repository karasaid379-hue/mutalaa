import { TriangleAlertIcon } from 'lucide-react';
import { useId } from 'react';
import { Badge } from '@/components/ui/badge';
import { originLabel, statusLabel } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { formatDateTime } from '@/lib/format';
import type { ReviewItem } from './types';

type BadgeSource = Pick<ReviewItem, 'durum' | 'dogrulanmamis' | 'ikinci_onay_bekliyor' | 'koken'>;

/**
 * Status badges of a review. "Doğrulanmamış" (K-25) is drawn only from the API's `dogrulanmamis`
 * field, never recomputed from `yz_modeli`; "İkinci onay bekliyor" comes from `ikinci_onay_bekliyor`
 * and is separate from the status badge (a record waiting for its second approval is still `acik`).
 * The unverified badge is a bordered, high contrast label with a warning icon (never colour only) and its
 * explanation is hidden text tied with `aria-describedby`, not a `title`.
 */
export function ReviewBadges({
  review,
  showOrigin = false,
}: {
  review: BadgeSource;
  showOrigin?: boolean;
}) {
  const hintId = useId();
  return (
    <span className="flex flex-wrap items-center gap-1">
      <Badge variant="secondary">{statusLabel(review.durum)}</Badge>
      {review.dogrulanmamis ? (
        <>
          <Badge variant="destructive" aria-describedby={hintId}>
            <TriangleAlertIcon aria-hidden="true" />
            {tr.badge.unverified}
          </Badge>
          <span id={hintId} className="sr-only">
            {tr.badge.unverifiedHint}
          </span>
        </>
      ) : null}
      {review.ikinci_onay_bekliyor ? (
        <Badge variant="outline">{tr.badge.secondPending}</Badge>
      ) : null}
      {showOrigin ? <Badge variant="outline">{originLabel(review.koken)}</Badge> : null}
    </span>
  );
}

type StageSource = Pick<
  ReviewItem,
  | 'ikinci_onay_bekliyor'
  | 'inceleyen'
  | 'incelendi_at'
  | 'ikinci_inceleyen'
  | 'ikinci_incelendi_at'
  | 'durum'
  | 'oneren'
  | 'koken'
  | 'yz_modeli'
  | 'guven'
> & { gerekce?: string | null; ikinci_gerekce?: string | null };

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <dt className="text-muted-foreground">{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

/**
 * First and second approval as two separate groups (K-48 madde 4). The second group appears when the
 * record waits for a second approval or already has one; a single-stage record shows only the first.
 */
export function ApprovalStages({ review }: { review: StageSource }) {
  const hasSecond = review.ikinci_onay_bekliyor || !!review.ikinci_inceleyen;
  return (
    <div className="flex flex-col gap-3" data-testid="approval-stages">
      <section aria-label={tr.approval.firstHeading} data-testid="approval-first">
        <h3 className="text-sm font-medium">{tr.approval.firstHeading}</h3>
        <dl className="text-sm">
          <Row label={tr.approval.proposer} value={review.oneren} />
          <Row label={tr.approval.origin} value={originLabel(review.koken)} />
          <Row label={tr.approval.aiModel} value={review.yz_modeli} />
          <Row
            label={tr.approval.confidence}
            value={typeof review.guven === 'number' ? String(review.guven) : null}
          />
          <Row
            label={tr.approval.by}
            value={review.inceleyen ?? (review.durum === 'acik' ? tr.approval.notYet : null)}
          />
          <Row label={tr.approval.at} value={formatDateTime(review.incelendi_at)} />
          <Row label={tr.approval.reason} value={review.gerekce} />
        </dl>
      </section>
      {hasSecond ? (
        <section aria-label={tr.approval.secondHeading} data-testid="approval-second">
          <h3 className="text-sm font-medium">{tr.approval.secondHeading}</h3>
          <dl className="text-sm">
            <Row
              label={tr.approval.by}
              value={
                review.ikinci_inceleyen ??
                (review.ikinci_onay_bekliyor ? tr.approval.waiting : null)
              }
            />
            <Row label={tr.approval.at} value={formatDateTime(review.ikinci_incelendi_at)} />
            <Row label={tr.approval.reason} value={review.ikinci_gerekce} />
          </dl>
        </section>
      ) : null}
    </div>
  );
}
