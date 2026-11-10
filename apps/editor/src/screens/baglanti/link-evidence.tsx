import { useId } from 'react';
import { useApi } from '@/app/api-context';
import { ArabicText } from '@/components/arabic-text';
import { ProblemMessage } from '@/components/problem-message';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { REVIEW_PATH, reviewDetailInit } from '@/review/queries';
import type { ReviewDetail, ReviewItem } from '@/review/types';
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
    <section aria-labelledby={headingId} className="flex flex-col gap-1 rounded-lg border p-3">
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
        <p lang="tr" className="text-sm whitespace-pre-wrap">
          {unit.data.metin}
        </p>
      )}
    </section>
  );
}

/**
 * The evidence of a link candidate that the API gives: the source paragraph, the candidate ayah and its meal.
 * The texts come from the units endpoint exactly as stored. The highlighted sequence, the evidence summary
 * and the alternatives are not in the API yet; the screen marks them with `MissingSection`.
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
      {dst ? (
        <UnitSection label={trBaglanti.candidateAyah} anchor={dst} arabic={info?.ayah === true} />
      ) : null}
      {info?.mealAnchor ? (
        <UnitSection label={trBaglanti.meal} anchor={info.mealAnchor} />
      ) : dst ? (
        <p className="text-sm text-muted-foreground">{trBaglanti.mealNotShown}</p>
      ) : null}
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
