import { useId, useState, type FormEvent } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { trLemma } from '@/i18n/tr-lemma';
import { problemStatus, toProblem } from '@/lib/problem';
import { ActionError, ReasonField } from '@/review/action-parts';
import { reasonProblem, useRefreshReview } from '@/review/action-helpers';
import { approvalLabel, readApprovalPath } from './approval';

export interface LemmaActionProps {
  /** The review whose card shows the lemma; its detail is read again after the action. */
  reviewId: number;
  lemmaId: number;
}

/**
 * "İtiraz et" (K-51 madde 9): the editor objects to an automatic approval with a required reason; the API opens
 * a review of its own, and another editor's approval returns the lemma to a candidate. After success the card
 * says "İtiraz kaydı açıldı" and offers no second objection.
 */
export function ObjectionForm({ reviewId, lemmaId }: LemmaActionProps) {
  const api = useApi();
  const announce = useAnnounce();
  const refresh = useRefreshReview(reviewId);
  const text = trLemma.kok.objection;
  const [open, setOpen] = useState(false);
  const [gerekce, setGerekce] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [openedId, setOpenedId] = useState<number | null>(null);
  const mutation = api.$api.useMutation('post', '/api/v1/lemmas/{id}/itiraz');
  const headingId = useId();

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.isPending) return;
    const found = reasonProblem(gerekce, text.reasonRequired);
    setProblem(found);
    setError(null);
    if (found !== null) return;
    try {
      const result = await mutation.mutateAsync({
        params: { path: { id: lemmaId } },
        body: { gerekce },
      });
      setOpenedId(result.id);
      setOpen(false);
      announce(text.doneId(result.id));
      refresh();
    } catch (thrown) {
      setError(thrown);
    }
  }

  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="lemma-objection"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {text.heading}
      </h3>
      {openedId !== null ? (
        <p className="text-sm" data-testid="objection-done">
          {text.doneId(openedId)}
        </p>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">{text.hint}</p>
          {open ? (
            <form
              noValidate
              className="flex flex-col gap-2"
              onSubmit={(event) => void submit(event)}
            >
              <ReasonField
                label={text.reason}
                value={gerekce}
                onChange={setGerekce}
                error={problem}
              />
              {error !== null ? (
                <ActionError error={error} messages={text.errors} testId="objection-error" />
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" disabled={mutation.isPending}>
                  {mutation.isPending ? text.submitting : text.submit}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  disabled={mutation.isPending}
                  onClick={() => {
                    setOpen(false);
                    setProblem(null);
                    setError(null);
                  }}
                >
                  {text.cancel}
                </Button>
              </div>
            </form>
          ) : (
            <Button
              type="button"
              variant="outline"
              className="self-start"
              onClick={() => setOpen(true)}
            >
              {text.open}
            </Button>
          )}
        </>
      )}
    </section>
  );
}

export interface EtymologyFormProps extends LemmaActionProps {
  /** The value the lemma has now (`hedef.etymological_only`). */
  current: boolean;
}

/**
 * The "yalnızca etimolojik" switch of an approved Turkish lemma (`markLemmaEtymological`): the new value and a
 * required reason; the lemma becomes editor approved. A value equal to the current one is not sent.
 */
export function EtymologyForm({ reviewId, lemmaId, current }: EtymologyFormProps) {
  const api = useApi();
  const announce = useAnnounce();
  const refresh = useRefreshReview(reviewId);
  const text = trLemma.kok.etym;
  const [value, setValue] = useState<boolean | null>(null);
  const [gerekce, setGerekce] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const mutation = api.$api.useMutation('post', '/api/v1/lemmas/{id}/etimolojik-isaret');
  const headingId = useId();
  const checkboxId = useId();
  const checked = value ?? current;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.isPending) return;
    setSaved(null);
    setError(null);
    if (checked === current) {
      setProblem(text.unchanged);
      return;
    }
    const found = reasonProblem(gerekce, text.reasonRequired);
    setProblem(found);
    if (found !== null) return;
    try {
      const result = await mutation.mutateAsync({
        params: { path: { id: lemmaId } },
        body: { etymological_only: checked, gerekce },
      });
      const path = readApprovalPath(result.onay_yolu);
      const message = text.saved(
        result.etymological_only ? trLemma.kok.yes : trLemma.kok.no,
        path ? approvalLabel(path) : result.onay_yolu,
      );
      setSaved(message);
      setValue(null);
      setGerekce('');
      announce(message);
      refresh();
    } catch (thrown) {
      setError(thrown);
      // A 412: the lemma changed under the editor; the card is read again and the typed value is kept.
      if (problemStatus(toProblem(thrown)) === 412) refresh();
    }
  }

  return (
    <section
      aria-labelledby={headingId}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="lemma-etymology"
    >
      <h3 id={headingId} className="text-sm font-medium">
        {text.heading}
      </h3>
      <p className="text-sm">{text.current(current ? trLemma.kok.yes : trLemma.kok.no)}</p>
      <form noValidate className="flex flex-col gap-2" onSubmit={(event) => void submit(event)}>
        <div className="flex min-h-6 items-center gap-2">
          <Checkbox
            id={checkboxId}
            checked={checked}
            onCheckedChange={(next) => {
              setValue(next === true);
              setProblem(null);
            }}
          />
          <Label htmlFor={checkboxId} className="font-normal">
            {text.checkbox}
          </Label>
        </div>
        <p className="text-xs text-muted-foreground">{text.hint}</p>
        <ReasonField label={text.reason} value={gerekce} onChange={setGerekce} error={problem} />
        {error !== null ? (
          <ActionError error={error} messages={text.errors} testId="etymology-error" />
        ) : null}
        <Button type="submit" className="self-start" disabled={mutation.isPending}>
          {mutation.isPending ? text.submitting : text.submit}
        </Button>
        {saved !== null ? (
          <p className="text-sm" data-testid="etymology-saved">
            {saved}
          </p>
        ) : null}
      </form>
    </section>
  );
}
