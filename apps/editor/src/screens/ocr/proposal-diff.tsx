import { useId } from 'react';
import { TextDiff } from '@/components/text-diff';
import { trOcr } from '@/i18n/tr-ocr';
import { readTextPayload } from '@/lib/payload';
import type { ReviewDetail } from '@/review/types';

/**
 * The proposed change of an OCR record: previous text to proposed text as a word level difference, and, when the
 * first approver edited the text, proposed to edited. The texts come from `onceki`, `onerilen` and `duzenlenen`;
 * a payload that cannot be read counts as absent.
 */
export function ProposalDiff({ review }: { review: ReviewDetail }) {
  const headingId = useId();
  const before = readTextPayload(review.onceki)?.metin ?? null;
  const after = readTextPayload(review.onerilen)?.metin ?? null;
  const edited = readTextPayload(review.duzenlenen)?.metin ?? null;
  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="ocr-diff"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {trOcr.diff.heading}
      </h3>
      {after === null ? (
        <p className="text-sm text-muted-foreground">{trOcr.diff.noProposal}</p>
      ) : before === null ? (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-muted-foreground">{trOcr.diff.proposedOnly}</p>
          <p lang="tr" className="text-sm whitespace-pre-wrap">
            {after}
          </p>
        </div>
      ) : before === after ? (
        <p className="text-sm text-muted-foreground">{trOcr.diff.same}</p>
      ) : (
        <div className="flex flex-col gap-1">
          <p className="text-xs text-muted-foreground">{trOcr.diff.beforeAfter}</p>
          <TextDiff before={before} after={after} className="text-sm" />
        </div>
      )}
      {edited !== null && after !== null ? (
        <div className="flex flex-col gap-1">
          <h4 className="text-xs font-medium">{trOcr.diff.editedHeading}</h4>
          {edited === after ? (
            <p className="text-sm text-muted-foreground">{trOcr.diff.same}</p>
          ) : (
            <>
              <p className="text-xs text-muted-foreground">{trOcr.diff.editedDiff}</p>
              <TextDiff before={after} after={edited} className="text-sm" />
            </>
          )}
        </div>
      ) : null}
    </section>
  );
}
