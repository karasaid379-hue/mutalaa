import { useQueryClient } from '@tanstack/react-query';
import { useApi } from '@/app/api-context';
import { tr } from '@/i18n/tr';
import { codePointCount, findUnwritable } from '@/lib/text';
import { MAX_REASON_LENGTH } from './limits';
import { REVIEWS_PATH, invalidateReviewCounts, reviewDetailKey } from './queries';

/** The first problem of a reason text: empty, over the limit or unwritable (NUL, lone surrogate); null when fine. */
export function reasonProblem(text: string, requiredText: string): string | null {
  if (text.trim() === '') return requiredText;
  const length = codePointCount(text);
  if (length > MAX_REASON_LENGTH) return tr.review.reasonTooLong(length, MAX_REASON_LENGTH);
  const unwritable = findUnwritable(text);
  if (unwritable.nul || unwritable.loneSurrogate) return tr.review.unwritable;
  return null;
}

/** The caches a lemma action changes: the record's detail (the lemma snapshot), the lists and the counts. */
export function useRefreshReview(reviewId: number) {
  const api = useApi();
  const queryClient = useQueryClient();
  return () => {
    void queryClient.invalidateQueries({ queryKey: reviewDetailKey(api, reviewId) });
    void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
    void invalidateReviewCounts(queryClient);
  };
}
