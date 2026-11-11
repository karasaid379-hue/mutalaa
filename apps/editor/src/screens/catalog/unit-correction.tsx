import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { OpenQuestionButton } from '@/components/open-question-button';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { trc } from '@/i18n/tr-catalog';
import { toProblem } from '@/lib/problem';
import { canDecide } from '@/lib/roles';
import { codePointCount, isWritable } from '@/lib/text';
import { MAX_REASON_LENGTH } from '@/review/limits';
import { fieldA11y, focusField, type FieldProblem } from '@/review/field-errors';
import { ProblemList } from '@/review/problem-list';
import { ME_PATH, SESSION_QUERY_OPTIONS, invalidateReviewCounts } from '@/review/queries';
import { hasOffsetData } from '@/review/rules';
import type { UnitDetail } from '@/review/types';
import { isImmutableUnit } from './unit-rules';

export interface UnitCorrectionProps {
  unit: UnitDetail;
}

/**
 * The correction proposal of a unit text (`POST /units/{anchor}/corrections`, `{metin, gerekce}`).
 * - Immutable text (`duzeltilebilir` false, an `ayet` unit, a `kuran_metni` source): a note only, no button.
 * - A unit with offset data (`marks`, `sentences`): the button is closed ("Açık soru: A20"), no request.
 * - Otherwise a form behind a "Düzeltme öner" button, for editors and admins only.
 * The proposal opens a review row; the text changes only after an approval, so nothing is applied here.
 */
export function UnitCorrection({ unit }: UnitCorrectionProps) {
  const api = useApi();
  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);

  if (isImmutableUnit(unit)) {
    return <p className="text-sm text-muted-foreground">{trc.units.immutableNote}</p>;
  }
  if (hasOffsetData(unit)) {
    return (
      <div className="flex flex-col items-start gap-1">
        <OpenQuestionButton label={trc.units.correct} phase="A20" />
      </div>
    );
  }
  if (!me.data || !canDecide(me.data.roller)) return null;
  return <CorrectionForm unit={unit} />;
}

function CorrectionForm({ unit }: UnitCorrectionProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const announce = useAnnounce();
  const ids = {
    text: useId(),
    reason: useId(),
    reasonHint: useId(),
    summary: useId(),
    form: useId(),
    button: useId(),
  };
  const [open, setOpen] = useState(false);
  const [metin, setMetin] = useState(unit.metin);
  const [gerekce, setGerekce] = useState('');
  const [problems, setProblems] = useState<FieldProblem[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [doneId, setDoneId] = useState<number | null>(null);
  const [focusTick, setFocusTick] = useState(0);
  // Where focus goes after the form opens or closes; `n` makes a repeated request count.
  const [focusTo, setFocusTo] = useState<{ target: 'field' | 'button'; n: number } | null>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const propose = api.$api.useMutation('post', '/api/v1/units/{anchor}/corrections');

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  useEffect(() => {
    if (focusTo === null) return;
    if (focusTo.target === 'field') focusField(ids.text);
    else document.getElementById(ids.button)?.focus();
  }, [focusTo, ids.text, ids.button]);

  function requestFocus(target: 'field' | 'button') {
    setFocusTo((previous) => ({ target, n: (previous?.n ?? 0) + 1 }));
  }

  function validate(): FieldProblem[] {
    const found: FieldProblem[] = [];
    const add = (fieldId: string, message: string) => found.push({ fieldId, message });
    if (metin === '') add(ids.text, trc.units.correctionTextEmpty);
    else if (metin === unit.metin) add(ids.text, trc.units.correctionTextUnchanged);
    if (!isWritable(metin)) add(ids.text, trc.units.correctionTextUnwritable);
    if (gerekce.trim() === '') add(ids.reason, trc.units.correctionReasonRequired);
    const length = codePointCount(gerekce);
    if (length > MAX_REASON_LENGTH) {
      add(ids.reason, trc.units.correctionReasonTooLong(length, MAX_REASON_LENGTH));
    }
    if (!isWritable(gerekce)) add(ids.reason, trc.units.correctionReasonUnwritable);
    return found;
  }

  async function submit() {
    if (propose.isPending) return;
    const found = validate();
    setProblems(found);
    setError(null);
    setDoneId(null);
    if (found.length > 0) {
      setFocusTick((tick) => tick + 1);
      return;
    }
    try {
      // The path value is given raw: the client encodes it once.
      const result = await propose.mutateAsync({
        params: { path: { anchor: unit.anchor } },
        body: { metin, gerekce },
      });
      setDoneId(result.id);
      announce(trc.units.correctionDone(result.id));
      setOpen(false);
      setMetin(unit.metin);
      setGerekce('');
      requestFocus('button');
      void invalidateReviewCounts(queryClient);
    } catch (thrown) {
      setError(toProblem(thrown));
      setFocusTick((tick) => tick + 1);
    }
  }

  function onKeyDown(event: KeyboardEvent) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }

  function cancel() {
    setOpen(false);
    setProblems([]);
    setError(null);
    setMetin(unit.metin);
    setGerekce('');
    requestFocus('button');
  }

  return (
    <section className="flex flex-col gap-2" aria-label={trc.units.correctionHeading}>
      {doneId !== null ? (
        <p className="text-sm" data-testid="correction-done">
          {trc.units.correctionDone(doneId)}
        </p>
      ) : null}
      <div>
        <Button
          id={ids.button}
          type="button"
          variant="outline"
          aria-expanded={open}
          aria-controls={open ? ids.form : undefined}
          onClick={() => {
            setOpen(true);
            setDoneId(null);
            requestFocus('field');
          }}
        >
          {trc.units.correct}
        </Button>
      </div>
      {open ? (
        <form
          id={ids.form}
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
          noValidate
        >
          <h3 className="text-sm font-medium">{trc.units.correctionHeading}</h3>
          <p className="text-xs text-muted-foreground">{trc.units.correctionIntro}</p>

          {problems.length > 0 ? (
            <Alert ref={summaryRef} tabIndex={-1} variant="destructive">
              <AlertTitle>{trc.units.correctionSummaryTitle}</AlertTitle>
              <AlertDescription>
                <ProblemList problems={problems} listId={ids.summary} />
              </AlertDescription>
            </Alert>
          ) : null}
          {error !== null ? (
            <ProblemMessage ref={summaryRef} error={error} context="correction" />
          ) : null}

          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.text}>{trc.units.correctionText}</Label>
            <Textarea
              id={ids.text}
              value={metin}
              onChange={(event) => setMetin(event.target.value)}
              onKeyDown={onKeyDown}
              rows={6}
              aria-required="true"
              {...fieldA11y(problems, ids.text, ids.summary)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.reason}>{trc.units.correctionReason}</Label>
            <Textarea
              id={ids.reason}
              value={gerekce}
              onChange={(event) => setGerekce(event.target.value)}
              onKeyDown={onKeyDown}
              rows={3}
              aria-required="true"
              {...fieldA11y(problems, ids.reason, ids.summary, ids.reasonHint)}
            />
            <p id={ids.reasonHint} className="text-xs text-muted-foreground">
              {`${trc.units.correctionReasonHint} ${trc.units.correctionReasonCount(codePointCount(gerekce), MAX_REASON_LENGTH)} ${trc.units.correctionShortcut}`}
            </p>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={propose.isPending}>
              {propose.isPending ? trc.units.correctionSubmitting : trc.units.correctionSubmit}
            </Button>
            <Button type="button" variant="outline" onClick={cancel}>
              {trc.units.correctionCancel}
            </Button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
