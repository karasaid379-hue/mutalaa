import { useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { Button } from '@/components/ui/button';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { formatIfMatch } from '@/lib/etag';
import { problemStatus, toProblem } from '@/lib/problem';
import { reasonProblem } from '@/review/action-helpers';
import { ActionError, ReasonField } from '@/review/action-parts';
import {
  REVIEWS_PATH,
  invalidateReviewCounts,
  removeReviewsFromLists,
  reviewDetailKey,
} from '@/review/queries';
import type { ReviewDetail } from '@/review/types';

interface ReasonActionText {
  heading: string;
  open: string;
  hint: string;
  submit: string;
  submitting: string;
}

interface ReasonActionProps {
  text: ReasonActionText;
  testId: string;
  /** Sends the request with the typed reason; resolves with the success message. A rejection is shown. */
  run: (gerekce: string) => Promise<string>;
  /** Called after a 412 (the record changed under the editor), so the card is read again. */
  onStale: () => void;
}

/**
 * An action of one required reason (uzmana gönder, ima, kalıp listesi): a closed section that opens into a small
 * form. The reason is checked here (required, at most 2.000 code points, no NUL); the answer's status (403, 404, 409,
 * 412, 422) is shown in Turkish and the typed reason stays, so the editor can fix and send again.
 */
function ReasonAction({ text, testId, run, onStale }: ReasonActionProps) {
  const announce = useAnnounce();
  const headingId = useId();
  const [open, setOpen] = useState(false);
  const [gerekce, setGerekce] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [pending, setPending] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    const found = reasonProblem(gerekce, trBaglanti.actions.reasonRequired);
    setProblem(found);
    setError(null);
    if (found !== null) return;
    setPending(true);
    try {
      const message = await run(gerekce);
      setDone(message);
      setOpen(false);
      setGerekce('');
      announce(message);
    } catch (thrown) {
      setError(thrown);
      if (problemStatus(toProblem(thrown)) === 412) onStale();
    } finally {
      setPending(false);
    }
  }

  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid={testId}
    >
      <h4 id={headingId} className="text-sm font-medium">
        {text.heading}
      </h4>
      {done !== null ? (
        <p className="text-sm" data-testid={`${testId}-done`}>
          {done}
        </p>
      ) : null}
      {open ? (
        <form noValidate className="flex flex-col gap-2" onSubmit={(event) => void submit(event)}>
          <p className="text-xs text-muted-foreground">{text.hint}</p>
          <ReasonField
            label={trBaglanti.actions.reason}
            value={gerekce}
            onChange={setGerekce}
            error={problem}
          />
          {error !== null ? (
            <ActionError
              error={error}
              messages={trBaglanti.actions.errors}
              testId={`${testId}-error`}
            />
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={pending}>
              {pending ? text.submitting : text.submit}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={pending}
              onClick={() => {
                setOpen(false);
                setProblem(null);
                setError(null);
              }}
            >
              {trBaglanti.actions.cancel}
            </Button>
          </div>
        </form>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">{text.hint}</p>
          <Button
            type="button"
            variant="outline"
            className="self-start"
            onClick={() => {
              setOpen(true);
              setDone(null);
            }}
          >
            {text.open}
          </Button>
        </>
      )}
    </section>
  );
}

/** The caches an action changes: the record's detail, the lists and the counts (stats carry the class counts). */
function useRefresh(review: ReviewDetail) {
  const api = useApi();
  const queryClient = useQueryClient();
  return {
    refresh() {
      void queryClient.invalidateQueries({ queryKey: reviewDetailKey(api, review.id) });
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void invalidateReviewCounts(queryClient);
    },
    leave() {
      removeReviewsFromLists(queryClient, [review.id]);
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void invalidateReviewCounts(queryClient);
    },
  };
}

export interface LinkActionProps {
  review: ReviewDetail;
  /** The record left the open list: the queue moves to the next record. */
  onLeft: (id: number) => void;
}

/** "Uzmana gönder" (`sendReviewToExpert`, If-Match): the open record becomes `uzmanda`; only the expert role decides it. */
export function ExpertAction({ review, onLeft }: LinkActionProps) {
  const api = useApi();
  const mutation = api.$api.useMutation('post', '/api/v1/reviews/{id}/uzmana-gonder');
  const { refresh, leave } = useRefresh(review);
  const text = trBaglanti.actions.expert;
  return (
    <ReasonAction
      text={text}
      testId="link-expert"
      onStale={refresh}
      run={async (gerekce) => {
        await mutation.mutateAsync({
          params: { path: { id: review.id }, header: { 'If-Match': formatIfMatch(review.xmin) } },
          body: { gerekce },
        });
        leave();
        onLeft(review.id);
        return text.done;
      }}
    />
  );
}

/** "İma olarak işaretle" (`markReviewLinkAsIma`): a new ima row from the same source to the same target; the candidate stays. */
export function ImaAction({ review }: { review: ReviewDetail }) {
  const api = useApi();
  const mutation = api.$api.useMutation('post', '/api/v1/reviews/{id}/ima');
  const { refresh } = useRefresh(review);
  const text = trBaglanti.actions.ima;
  return (
    <ReasonAction
      text={text}
      testId="link-ima"
      onStale={refresh}
      run={async (gerekce) => {
        const result = await mutation.mutateAsync({
          params: { path: { id: review.id } },
          body: { gerekce },
        });
        refresh();
        return text.done(result.id);
      }}
    />
  );
}

/** "Kalıp listesine ekle" (`addReviewLinkToPatternList`, If-Match): the matched sequence joins the pattern list and the candidate is rejected. */
export function PatternAction({ review, onLeft }: LinkActionProps) {
  const api = useApi();
  const mutation = api.$api.useMutation('post', '/api/v1/reviews/{id}/kalip');
  const { refresh, leave } = useRefresh(review);
  const text = trBaglanti.actions.pattern;
  return (
    <ReasonAction
      text={text}
      testId="link-pattern"
      onStale={refresh}
      run={async (gerekce) => {
        const result = await mutation.mutateAsync({
          params: { path: { id: review.id }, header: { 'If-Match': formatIfMatch(review.xmin) } },
          body: { gerekce },
        });
        leave();
        onLeft(review.id);
        return text.done(result.anahtar);
      }}
    />
  );
}
