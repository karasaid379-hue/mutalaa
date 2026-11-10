import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { tr } from '@/i18n/tr';
import { toProblem, problemIds, type Problem } from '@/lib/problem';
import { problemText } from '@/lib/problem-text';
import { pickSample, sampleSize, type RandomUint32 } from '@/lib/sample';
import { codePointCount, findUnwritable, stripUnwritable } from '@/lib/text';
import { MAX_BULK, MAX_REASON_LENGTH } from './limits';
import {
  REVIEW_PATH,
  REVIEWS_PATH,
  invalidateReviewCounts,
  patchReviewInLists,
  removeReviewsFromLists,
  reviewDetailKey,
  toListItem,
} from './queries';
import type { BulkOutcome, ReviewItem } from './types';

/** Why a selected record is marked in the bulk view. */
export type RowMark =
  { kind: 'stale' | 'missing' | 'refresh-failed' } | { kind: 'violation'; problem: Problem };

type Verdict = 'dogru' | 'hatali';

export interface BulkDecisionProps {
  /** The selected records (1 to 100); each carries the `xmin` the API checks. */
  items: readonly ReviewItem[];
  /**
   * `tenth`: a random sample of ceil(n/10) records must be reviewed and a single "Hatalı" cancels the bulk
   * approval (bağlantı queue). `none`: no sample (sure adı queue; every row is on the card).
   */
  sampling: 'tenth' | 'none';
  /** Content of one sampled record (the screen draws its text); the id and anchor are always shown. */
  renderSample?: (item: ReviewItem) => ReactNode;
  /** Test seam: the random source of the sample (default: crypto.getRandomValues). */
  random?: RandomUint32;
  /** Called with the outcomes after the API accepted the whole batch. */
  onDone?: (results: BulkOutcome[]) => void;
  /** Called when the editor clears the selection. */
  onCancel?: () => void;
  /** Called whenever the row marks change (so a list can mark its own rows). */
  onMarksChange?: (marks: Readonly<Record<number, RowMark>>) => void;
  className?: string;
}

function parseIds(key: string): number[] {
  return key === '' ? [] : key.split(',').map(Number);
}

/**
 * Bulk approval (K-48 madde 6): 1 to 100 records, approval only, all or nothing, no `If-Match` (each item
 * carries its own `xmin` from the list). A 412 names the records that changed (`kimlikler`): only those are
 * fetched again and the cache is patched; a 404 `kimlikler` and a rule violation (`kimlik`) mark the row and
 * leave it out of the next attempt. With `sampling="tenth"` a random sample is checked first.
 */
export function BulkDecision({
  items,
  sampling,
  renderSample,
  random,
  onDone,
  onCancel,
  onMarksChange,
  className,
}: BulkDecisionProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const announce = useAnnounce();
  const ids = { heading: useId(), reason: useId(), reasonHint: useId() };
  const summaryRef = useRef<HTMLDivElement>(null);

  const [gerekce, setGerekce] = useState('');
  // A single "Hatalı" cancels the bulk approval of this selection for good: it lifts only when the selection changes.
  const [cancelledKey, setCancelledKey] = useState<string | null>(null);
  const [verdicts, setVerdicts] = useState<Readonly<Record<number, Verdict>>>({});
  const [marks, setMarks] = useState<Readonly<Record<number, RowMark>>>({});
  const [error, setError] = useState<unknown>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [done, setDone] = useState<BulkOutcome[] | null>(null);
  const [focusTick, setFocusTick] = useState(0);

  const blocked = (id: number) => {
    const kind = marks[id]?.kind;
    return kind === 'missing' || kind === 'violation';
  };
  const batch = items.filter((item) => !blocked(item.id));
  const batchKey = batch.map((item) => item.id).join(',');

  // The sample is drawn when the batch changes (and only then).
  const draw = (key: string) => ({
    key,
    ids: pickSample(
      parseIds(key),
      sampling === 'tenth' ? sampleSize(parseIds(key).length) : 0,
      random,
    ),
  });
  const [sample, setSample] = useState(() => draw(batchKey));
  if (sample.key !== batchKey) setSample(draw(batchKey));

  const decide = api.$api.useMutation('post', '/api/v1/reviews/decisions');
  const pending = decide.isPending;

  const sampled = sample.ids
    .map((id) => batch.find((item) => item.id === id))
    .filter((item): item is ReviewItem => item !== undefined);
  const wrongCount = sampled.filter((item) => verdicts[item.id] === 'hatali').length;
  const judgedCount = sampled.filter((item) => verdicts[item.id] !== undefined).length;
  const cancelled = sampling === 'tenth' && cancelledKey === batchKey;
  const sampleDone = sampling === 'none' || (judgedCount === sampled.length && wrongCount === 0);
  const countOk = batch.length >= 1 && batch.length <= MAX_BULK;
  const unwritable = findUnwritable(gerekce);
  const hasUnwritable = unwritable.nul || unwritable.loneSurrogate;
  const reasonLength = codePointCount(gerekce);

  useEffect(() => {
    onMarksChange?.(marks);
  }, [marks, onMarksChange]);

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  function validate(): string | null {
    if (!countOk) return tr.bulk.limit;
    if (cancelled) return tr.bulk.cancelledBody;
    if (!sampleDone) return tr.bulk.verdictPending(judgedCount, sampled.length);
    if (gerekce.trim() === '') return tr.review.reasonRequired;
    if (reasonLength > MAX_REASON_LENGTH)
      return tr.review.reasonTooLong(reasonLength, MAX_REASON_LENGTH);
    if (hasUnwritable) return `${tr.bulk.reason}: ${tr.review.unwritable}`;
    return null;
  }

  async function refreshRows(changed: number[]) {
    const results = await Promise.all(
      changed.map(async (id) => {
        try {
          const { data } = await api.client.GET(REVIEW_PATH, { params: { path: { id } } });
          return { id, data: data ?? null };
        } catch {
          return { id, data: null };
        }
      }),
    );
    const nextMarks: Record<number, RowMark> = {};
    for (const { id, data } of results) {
      if (data) {
        queryClient.setQueryData(reviewDetailKey(api, id), data);
        patchReviewInLists(queryClient, toListItem(data));
        nextMarks[id] = { kind: 'stale' };
      } else {
        nextMarks[id] = { kind: 'refresh-failed' };
      }
    }
    setMarks((previous) => ({ ...previous, ...nextMarks }));
    // A record that changed has to be looked at again: its earlier verdict no longer counts.
    setVerdicts((previous) => {
      const next = { ...previous };
      for (const id of changed) delete next[id];
      return next;
    });
  }

  async function submit() {
    if (pending || done) return;
    const message = validate();
    setError(null);
    setLocalError(message);
    if (message) {
      setFocusTick((tick) => tick + 1);
      return;
    }
    try {
      const result = await decide.mutateAsync({
        body: {
          kararlar: batch.map((item) => ({
            id: item.id,
            xmin: item.xmin,
            karar: 'onaylandi',
            duzenlenen: null,
            gerekce,
          })),
        },
      });
      const outcomes = result.sonuclar;
      removeReviewsFromLists(
        queryClient,
        outcomes.filter((outcome) => outcome.durum !== 'acik').map((outcome) => outcome.id),
      );
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void invalidateReviewCounts(queryClient);
      setDone(outcomes);
      announce(tr.bulk.done(outcomes.length));
      onDone?.(outcomes);
    } catch (thrown) {
      const problem = toProblem(thrown);
      setError(problem);
      setFocusTick((tick) => tick + 1);
      const affected = problemIds(problem);
      if (problem.status === 412 && affected.length > 0) {
        await refreshRows(affected);
      } else if (problem.status === 404 && affected.length > 0) {
        setMarks((previous) => ({
          ...previous,
          ...Object.fromEntries(affected.map((id) => [id, { kind: 'missing' } as RowMark])),
        }));
      } else if (typeof problem.kimlik === 'number') {
        const id = problem.kimlik;
        setMarks((previous) => ({ ...previous, [id]: { kind: 'violation', problem } }));
      }
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }

  const markedRows = Object.entries(marks)
    .map(([id, mark]) => ({
      id: Number(id),
      mark,
      item: items.find((item) => item.id === Number(id)),
    }))
    .filter((row) => row.item !== undefined);

  function markText(mark: RowMark): string {
    switch (mark.kind) {
      case 'stale':
        return tr.bulk.rowStale;
      case 'missing':
        return tr.bulk.rowMissing;
      case 'refresh-failed':
        return tr.bulk.rowRefreshFailed;
      case 'violation':
        return `${tr.bulk.rowViolation}: ${problemText(mark.problem, 'bulk')}`;
    }
  }

  return (
    <form
      aria-labelledby={ids.heading}
      aria-busy={pending}
      noValidate
      className={className}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div className="flex flex-col gap-4">
        <h3 id={ids.heading} className="text-base font-medium">
          {tr.bulk.heading}
        </h3>
        <p className="text-sm" data-testid="bulk-count">
          {tr.bulk.count(batch.length)}
        </p>
        <p className="text-sm text-muted-foreground">{tr.bulk.onlyApprove}</p>
        {!countOk ? <p className="text-sm text-destructive">{tr.bulk.limit}</p> : null}

        {error !== null || localError !== null ? (
          <div ref={summaryRef} tabIndex={-1} className="outline-none">
            {localError !== null ? (
              <Alert variant="destructive" data-testid="bulk-summary">
                <AlertTitle>{tr.bulk.summaryTitle}</AlertTitle>
                <AlertDescription>{localError}</AlertDescription>
              </Alert>
            ) : (
              <ProblemMessage error={error} context="bulk" />
            )}
          </div>
        ) : null}

        {sampling === 'tenth' ? (
          <fieldset className="flex flex-col gap-3" data-testid="bulk-sample">
            <legend className="text-sm font-medium">{tr.bulk.sampleHeading}</legend>
            <p className="text-sm">{tr.bulk.sampleIntro(sampled.length, batch.length)}</p>
            <p className="text-xs text-muted-foreground">
              {tr.bulk.verdictPending(judgedCount, sampled.length)}
            </p>
            {sampled.map((item) => (
              <div
                key={item.id}
                className="flex flex-col gap-2 rounded-lg border p-3"
                data-testid="bulk-sample-row"
              >
                <p className="text-sm font-medium">{`${tr.bulk.sampleRow} ${item.hedef_anahtar}`}</p>
                {renderSample?.(item)}
                <RadioGroup
                  aria-label={`${tr.bulk.verdictLegend}: ${item.hedef_anahtar}`}
                  value={verdicts[item.id] ?? ''}
                  disabled={done !== null}
                  onKeyDown={onKeyDown}
                  onValueChange={(value) => {
                    if (value === 'hatali') setCancelledKey(batchKey);
                    setVerdicts((previous) => ({
                      ...previous,
                      [item.id]: value === 'hatali' ? 'hatali' : 'dogru',
                    }));
                  }}
                  className="flex flex-row gap-4"
                >
                  <Label className="min-h-6 gap-2 font-normal">
                    <RadioGroupItem value="dogru" />
                    {tr.bulk.correct}
                  </Label>
                  <Label className="min-h-6 gap-2 font-normal">
                    <RadioGroupItem value="hatali" />
                    {tr.bulk.wrong}
                  </Label>
                </RadioGroup>
                {marks[item.id] ? (
                  <p className="text-sm text-destructive">{markText(marks[item.id]!)}</p>
                ) : null}
              </div>
            ))}
          </fieldset>
        ) : (
          <p className="text-sm text-muted-foreground">{tr.bulk.noSampling}</p>
        )}

        {cancelled ? (
          <Alert variant="destructive" data-testid="bulk-cancelled">
            <AlertTitle>{tr.bulk.cancelledTitle}</AlertTitle>
            <AlertDescription>{tr.bulk.cancelledBody}</AlertDescription>
          </Alert>
        ) : null}

        {markedRows.length > 0 ? (
          <section aria-label={tr.bulk.problemRows} data-testid="bulk-problem-rows">
            <h4 className="text-sm font-medium">{tr.bulk.problemRows}</h4>
            <ul className="list-disc pl-5 text-sm">
              {markedRows.map(({ id, mark, item }) => (
                <li
                  key={id}
                >{`${item?.hedef_anahtar ?? tr.bulk.recordLabel(id)}: ${markText(mark)}`}</li>
              ))}
            </ul>
          </section>
        ) : null}

        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.reason}>{tr.bulk.reason}</Label>
          <Textarea
            id={ids.reason}
            value={gerekce}
            onChange={(event) => setGerekce(event.target.value)}
            onKeyDown={onKeyDown}
            aria-describedby={ids.reasonHint}
            aria-required="true"
            disabled={done !== null}
            rows={3}
          />
          <p id={ids.reasonHint} className="text-xs text-muted-foreground">
            {`${tr.bulk.reasonHint} ${tr.review.reasonCount(reasonLength, MAX_REASON_LENGTH)}`}
          </p>
        </div>

        {hasUnwritable ? (
          <Alert data-testid="unwritable-warning">
            <AlertTitle>{tr.review.unwritableNote}</AlertTitle>
            <AlertDescription>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setGerekce((value) => stripUnwritable(value))}
              >
                {tr.review.unwritableAction}
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={pending || done !== null || cancelled}>
            {pending ? tr.bulk.confirming : tr.bulk.confirm}
          </Button>
          {onCancel ? (
            <Button type="button" variant="outline" onClick={onCancel} disabled={pending}>
              {tr.bulk.reset}
            </Button>
          ) : null}
        </div>

        {done ? <p className="text-sm">{tr.bulk.done(done.length)}</p> : null}
      </div>
    </form>
  );
}
