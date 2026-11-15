import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { fieldLabel } from '@/i18n/labels';
import { trLemma } from '@/i18n/tr-lemma';
import { reasonProblem } from '@/review/action-helpers';
import { FormErrors } from '@/review/action-parts';
import { useFocusRequest } from '@/review/focus-request';
import type { FieldProblem } from '@/review/field-errors';
import { REVIEWS_PATH, invalidateReviewCounts } from '@/review/queries';
import {
  WORD_FIX_FIELDS,
  checkWordAnchor,
  checkWordFixValue,
  isWordFixField,
  type WordFixField,
} from './word-fix-input';

/**
 * "Kelime düzeltmesi öner" (K-51 madde 2, `createWordFix`): the editor opens a root or lemma correction for one
 * word: the word anchor, the corrected field, the new value and a required reason. The API opens the candidate
 * and a review record of its own; the form says which one. A 400 (invalid value) and a 409 (a correction of this
 * word and field exists) are shown in Turkish; the typed input stays. Focus: the anchor field when the form
 * opens, the error area (an alert that links to the fields) after a failed send, the heading after success.
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
    reasonError: useId(),
    summary: useId(),
  };
  const [open, setOpen] = useState(false);
  const [anchor, setAnchor] = useState('');
  const [field, setField] = useState<WordFixField>('root_id');
  const [value, setValue] = useState('');
  const [reason, setReason] = useState('');
  const [found, setFound] = useState<FieldProblem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [createdId, setCreatedId] = useState<number | null>(null);
  const text = trLemma.wordFixCreate;

  const anchorRef = useRef<HTMLInputElement>(null);
  const { attach: attachError, request: focusError } = useFocusRequest<HTMLDivElement>();
  const { attach: attachHeading, request: focusHeading } = useFocusRequest<HTMLHeadingElement>();
  const { attach: attachOpen, request: focusOpen } = useFocusRequest<HTMLButtonElement>();
  const messageOf = (fieldId: string) => found.find((entry) => entry.fieldId === fieldId)?.message;
  const anchorProblem = messageOf(ids.anchor);
  const valueProblem = messageOf(ids.value);
  const reasonMessage = messageOf(ids.reason);

  useEffect(() => {
    if (open) anchorRef.current?.focus();
  }, [open]);

  function validate(): FieldProblem[] {
    const list: FieldProblem[] = [];
    const anchorCode = checkWordAnchor(anchor);
    if (anchorCode !== null) list.push({ fieldId: ids.anchor, message: text.problems[anchorCode] });
    const valueCode = checkWordFixValue(field, value);
    if (valueCode !== null) list.push({ fieldId: ids.value, message: text.problems[valueCode] });
    const reasonText = reasonProblem(reason, text.reasonRequired);
    if (reasonText !== null) list.push({ fieldId: ids.reason, message: reasonText });
    return list;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.isPending) return;
    const list = validate();
    setFound(list);
    setError(null);
    if (list.length > 0) {
      focusError();
      return;
    }
    try {
      const result = await mutation.mutateAsync({
        body: { anchor: anchor.trim(), field, new_value: value, reason },
      });
      setCreatedId(result.review_id);
      setOpen(false);
      announce(text.done(result.review_id));
      focusHeading();
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void invalidateReviewCounts(queryClient);
    } catch (thrown) {
      setError(thrown);
      focusError();
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
      <h3
        id={ids.heading}
        ref={attachHeading}
        tabIndex={-1}
        className="text-sm font-medium outline-none"
      >
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
          <FormErrors
            regionRef={attachError}
            title={text.summaryTitle}
            problems={found}
            listId={ids.summary}
            summaryTestId="word-fix-summary"
          >
            {error !== null ? <ProblemMessage error={error} context="wordFix" /> : null}
          </FormErrors>
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.anchor}>{text.anchor}</Label>
            <Input
              id={ids.anchor}
              ref={anchorRef}
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
              aria-describedby={reasonMessage !== undefined ? ids.reasonError : undefined}
              onChange={(event) => setReason(event.target.value)}
            />
            {reasonMessage !== undefined ? (
              <p id={ids.reasonError} className="text-xs font-medium text-destructive">
                {reasonMessage}
              </p>
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
                focusOpen();
              }}
            >
              {text.cancel}
            </Button>
          </div>
        </form>
      ) : (
        <Button
          ref={attachOpen}
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
