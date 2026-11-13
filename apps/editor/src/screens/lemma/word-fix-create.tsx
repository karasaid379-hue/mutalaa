import { useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { fieldLabel } from '@/i18n/labels';
import { trLemma } from '@/i18n/tr-lemma';
import { reasonProblem } from '@/review/action-helpers';
import { REVIEWS_PATH, invalidateReviewCounts } from '@/review/queries';
import {
  WORD_FIX_FIELDS,
  checkWordAnchor,
  checkWordFixValue,
  isWordFixField,
  type WordFixField,
} from './word-fix-input';

interface Found {
  field: 'anchor' | 'value' | 'reason';
  message: string;
}

/**
 * "Kelime düzeltmesi öner" (K-51 madde 2, `createWordFix`): the editor opens a root or lemma correction for one
 * word: the word anchor, the corrected field, the new value and a required reason. The API opens the candidate
 * and a review record of its own; the form says which one. A 400 (invalid value) and a 409 (a correction of this
 * word and field exists) are shown in Turkish; the typed input stays.
 */
export function WordFixCreate() {
  const api = useApi();
  const queryClient = useQueryClient();
  const announce = useAnnounce();
  const mutation = api.$api.useMutation('post', '/api/v1/word-fixes');
  const ids = {
    heading: useId(),
    anchor: useId(),
    anchorHint: useId(),
    value: useId(),
    valueHint: useId(),
    reason: useId(),
  };
  const [open, setOpen] = useState(false);
  const [anchor, setAnchor] = useState('');
  const [field, setField] = useState<WordFixField>('root_id');
  const [value, setValue] = useState('');
  const [reason, setReason] = useState('');
  const [found, setFound] = useState<Found[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [createdId, setCreatedId] = useState<number | null>(null);
  const text = trLemma.wordFixCreate;

  const anchorProblem = found.find((entry) => entry.field === 'anchor')?.message;
  const valueProblem = found.find((entry) => entry.field === 'value')?.message;
  const reasonMessage = found.find((entry) => entry.field === 'reason')?.message;

  function validate(): Found[] {
    const list: Found[] = [];
    const anchorCode = checkWordAnchor(anchor);
    if (anchorCode !== null) list.push({ field: 'anchor', message: text.problems[anchorCode] });
    const valueCode = checkWordFixValue(field, value);
    if (valueCode !== null) list.push({ field: 'value', message: text.problems[valueCode] });
    const reasonText = reasonProblem(reason, text.reasonRequired);
    if (reasonText !== null) list.push({ field: 'reason', message: reasonText });
    return list;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.isPending) return;
    const list = validate();
    setFound(list);
    setError(null);
    if (list.length > 0) return;
    try {
      const result = await mutation.mutateAsync({
        body: { anchor: anchor.trim(), field, new_value: value, reason },
      });
      setCreatedId(result.review_id);
      setOpen(false);
      announce(text.done(result.review_id));
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void invalidateReviewCounts(queryClient);
    } catch (thrown) {
      setError(thrown);
    }
  }

  function startAnother() {
    setAnchor('');
    setValue('');
    setReason('');
    setFound([]);
    setError(null);
    setCreatedId(null);
    setOpen(true);
  }

  return (
    <section
      aria-labelledby={ids.heading}
      className="flex flex-col gap-2 rounded-lg border p-3"
      data-testid="word-fix-create"
    >
      <h3 id={ids.heading} className="text-sm font-medium">
        {text.heading}
      </h3>
      <p className="text-xs text-muted-foreground">{text.hint}</p>
      {createdId !== null ? (
        <>
          <p className="text-sm" data-testid="word-fix-created">
            {text.done(createdId)}
          </p>
          <Button type="button" variant="outline" className="self-start" onClick={startAnother}>
            {text.another}
          </Button>
        </>
      ) : open ? (
        <form noValidate className="flex flex-col gap-3" onSubmit={(event) => void submit(event)}>
          {found.length > 0 ? (
            <Alert variant="destructive" data-testid="word-fix-summary">
              <AlertTitle>{text.summaryTitle}</AlertTitle>
              <AlertDescription>
                <ul className="list-disc pl-5">
                  {found.map((entry) => (
                    <li key={entry.message}>{entry.message}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          ) : null}
          {error !== null ? <ProblemMessage error={error} context="wordFix" /> : null}
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.anchor}>{text.anchor}</Label>
            <Input
              id={ids.anchor}
              dir="ltr"
              value={anchor}
              aria-required="true"
              aria-invalid={anchorProblem !== undefined ? true : undefined}
              aria-describedby={ids.anchorHint}
              onChange={(event) => setAnchor(event.target.value)}
            />
            <p id={ids.anchorHint} className="text-xs text-muted-foreground">
              {anchorProblem ?? text.anchorHint}
            </p>
          </div>
          <RadioGroup
            aria-label={text.field}
            value={field}
            className="flex flex-wrap items-center gap-x-4 gap-y-1"
            onValueChange={(next) => {
              if (isWordFixField(next)) setField(next);
            }}
          >
            <span className="text-sm font-medium" aria-hidden="true">
              {text.field}
            </span>
            {WORD_FIX_FIELDS.map((entry) => (
              <Label key={entry} className="min-h-6 gap-2 font-normal">
                <RadioGroupItem value={entry} />
                {fieldLabel(entry)}
              </Label>
            ))}
          </RadioGroup>
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.value}>{text.value}</Label>
            <Input
              id={ids.value}
              dir="ltr"
              value={value}
              aria-required="true"
              aria-invalid={valueProblem !== undefined ? true : undefined}
              aria-describedby={ids.valueHint}
              onChange={(event) => setValue(event.target.value)}
            />
            <p id={ids.valueHint} className="text-xs text-muted-foreground">
              {valueProblem ?? text.valueHints[field]}
            </p>
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.reason}>{text.reason}</Label>
            <Textarea
              id={ids.reason}
              rows={3}
              value={reason}
              aria-required="true"
              aria-invalid={reasonMessage !== undefined ? true : undefined}
              onChange={(event) => setReason(event.target.value)}
            />
            {reasonMessage !== undefined ? (
              <p className="text-xs font-medium text-destructive">{reasonMessage}</p>
            ) : null}
          </div>
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
                setFound([]);
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
    </section>
  );
}
