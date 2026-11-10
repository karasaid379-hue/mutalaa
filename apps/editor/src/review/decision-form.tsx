import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { ProblemMessage } from '@/components/problem-message';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { tr } from '@/i18n/tr';
import { formatIfMatch } from '@/lib/etag';
import { codePointCount, findUnwritable, stripUnwritable } from '@/lib/text';
import { problemCode, problemStatus, toProblem } from '@/lib/problem';
import { canDecide } from '@/lib/roles';
import { MAX_REASON_LENGTH } from './limits';
import {
  ME_PATH,
  REVIEW_PATH,
  REVIEWS_PATH,
  SESSION_QUERY_OPTIONS,
  invalidateReviewCounts,
  patchReviewInLists,
  removeReviewsFromLists,
  reviewDetailKey,
  toListItem,
} from './queries';
import {
  approveBlockReason,
  canEditValue,
  isFirstStageUnitText,
  proposedText,
  type UnitEditInfo,
} from './rules';
import { StaleRecord } from './stale-record';
import type { DecisionKind, DecisionResult, ReviewDetail } from './types';

export interface DecisionFormProps {
  /** The record being decided. Its `xmin` becomes the `If-Match` value. */
  review: ReviewDetail;
  /**
   * Unit facts for `canEditValue`. Leave it out and the form reads `/units/{anchor}` itself for a unit text
   * review; pass `null` to say "no unit information" (the edit field stays closed).
   */
  unit?: (UnitEditInfo & { metin?: string }) | null;
  /** Called once the API accepted the decision (the caches are already updated). */
  onDecided?: (result: DecisionResult, decision: DecisionKind) => void;
  /** Called with the fresh record after a 412 refresh. */
  onRefreshed?: (fresh: ReviewDetail) => void;
  className?: string;
}

interface Refreshed {
  from: ReviewDetail;
  to: ReviewDetail;
}

interface Stale {
  before: ReviewDetail;
  after: ReviewDetail | null;
  refreshError?: unknown;
}

/**
 * Decision form of one review (K-48): approve or reject must be chosen explicitly; `gerekce` is required
 * (at most 2.000 code points); the edited-text field exists only when `canEditValue` is true; NUL and lone
 * surrogates are reported and cleaned only by the button. The request carries `If-Match: "{xmin}"` and always
 * the body `{karar, duzenlenen, gerekce}`. On 412 the record is fetched again, the difference is shown and the
 * input is kept; nothing is resent automatically. "Onayla" is closed in advance for the editor's own proposal
 * and for the first approver (the API has the last word).
 */
export function DecisionForm({
  review,
  unit,
  onDecided,
  onRefreshed,
  className,
}: DecisionFormProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const announce = useAnnounce();
  const ids = {
    form: useId(),
    reason: useId(),
    reasonHint: useId(),
    edited: useId(),
    editedHint: useId(),
  };

  const [karar, setKarar] = useState<DecisionKind | ''>('');
  const [gerekce, setGerekce] = useState('');
  const [edited, setEdited] = useState<string | null>(null);
  const [problems, setProblems] = useState<string[]>([]);
  const [error, setError] = useState<unknown>(null);
  const [stale, setStale] = useState<Stale | null>(null);
  const [refreshed, setRefreshed] = useState<Refreshed | null>(null);
  const [done, setDone] = useState<{ kind: DecisionKind; result: DecisionResult } | null>(null);
  const [focusTick, setFocusTick] = useState(0);
  const summaryRef = useRef<HTMLDivElement>(null);

  // A fresh record after a 412 wins until the parent hands over a new object of its own.
  const current = refreshed && refreshed.from === review ? refreshed.to : review;

  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);
  const needsUnit = unit === undefined && isFirstStageUnitText(current);
  const unitQuery = api.$api.useQuery(
    'get',
    '/api/v1/units/{anchor}',
    { params: { path: { anchor: current.hedef_anahtar } } },
    { enabled: needsUnit, retry: false },
  );
  const unitInfo = unit !== undefined ? unit : (unitQuery.data ?? null);
  const decide = api.$api.useMutation('post', '/api/v1/reviews/{id}/decision');

  const roles = me.data?.roller;
  const roleMissing = me.data !== undefined && !canDecide(roles);
  const block = approveBlockReason(current, me.data?.kullanici.email);
  const closed = block === 'closed' || done !== null;
  const canEdit = canEditValue(current, unitInfo) && !closed;
  const baseline = proposedText(current) ?? unitInfo?.metin ?? '';
  const editedValue = edited ?? baseline;
  const approveClosed = block === 'own-proposal' || block === 'same-first-approver';
  // A closed "Onayla" cannot stay selected.
  const selected: DecisionKind | '' = approveClosed && karar === 'onaylandi' ? '' : karar;
  const pending = decide.isPending;

  const unwritable = {
    gerekce: findUnwritable(gerekce),
    edited:
      canEdit && selected === 'onaylandi'
        ? findUnwritable(editedValue)
        : { nul: false, loneSurrogate: false },
  };
  const hasUnwritable =
    unwritable.gerekce.nul ||
    unwritable.gerekce.loneSurrogate ||
    unwritable.edited.nul ||
    unwritable.edited.loneSurrogate;

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  function validate(): string[] {
    const found: string[] = [];
    if (selected === '') found.push(tr.review.chooseDecision);
    if (gerekce.trim() === '') found.push(tr.review.reasonRequired);
    const length = codePointCount(gerekce);
    if (length > MAX_REASON_LENGTH) found.push(tr.review.reasonTooLong(length, MAX_REASON_LENGTH));
    if (unwritable.gerekce.nul || unwritable.gerekce.loneSurrogate) {
      found.push(`${tr.review.reason}: ${tr.review.unwritable}`);
    }
    if (canEdit && selected === 'onaylandi') {
      if (editedValue.trim() === '') found.push(tr.review.editedEmpty);
      if (unwritable.edited.nul || unwritable.edited.loneSurrogate) {
        found.push(`${tr.review.editedText}: ${tr.review.unwritable}`);
      }
    }
    return found;
  }

  async function refresh(before: ReviewDetail) {
    try {
      const { data, error: refreshError } = await api.client.GET(REVIEW_PATH, {
        params: { path: { id: before.id } },
      });
      if (!data) {
        setStale({ before, after: null, refreshError });
        return;
      }
      queryClient.setQueryData(reviewDetailKey(api, before.id), data);
      patchReviewInLists(queryClient, toListItem(data));
      setRefreshed({ from: review, to: data });
      setStale({ before, after: data });
      onRefreshed?.(data);
    } catch (thrown) {
      setStale({ before, after: null, refreshError: thrown });
    }
  }

  async function submit() {
    if (pending || closed) return;
    const found = validate();
    setProblems(found);
    setError(null);
    if (found.length > 0 || selected === '') {
      setFocusTick((tick) => tick + 1);
      return;
    }
    setStale(null);
    const sendEdit = canEdit && selected === 'onaylandi' && editedValue !== baseline;
    const snapshot = current;
    try {
      const result = await decide.mutateAsync({
        params: { path: { id: snapshot.id }, header: { 'If-Match': formatIfMatch(snapshot.xmin) } },
        body: { karar: selected, duzenlenen: sendEdit ? { metin: editedValue } : null, gerekce },
      });
      setDone({ kind: selected, result });
      announce(
        result.ikinci_onay_bekliyor
          ? `${tr.review.decided(selected)} ${tr.review.secondPending}`
          : tr.review.decided(selected),
      );
      if (result.durum !== 'acik') removeReviewsFromLists(queryClient, [snapshot.id]);
      void queryClient.invalidateQueries({ queryKey: ['get', REVIEWS_PATH] });
      void queryClient.invalidateQueries({ queryKey: reviewDetailKey(api, snapshot.id) });
      void invalidateReviewCounts(queryClient);
      onDecided?.(result, selected);
    } catch (thrown) {
      const problem = toProblem(thrown);
      setError(problem);
      setFocusTick((tick) => tick + 1);
      if (problemStatus(problem) === 412 && problemCode(problem) === 'surum-uyusmazligi') {
        await refresh(snapshot);
      }
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void submit();
    }
  }

  function clean() {
    setGerekce((value) => stripUnwritable(value));
    if (canEdit) setEdited(stripUnwritable(editedValue));
  }

  if (roleMissing) {
    return (
      <section className={className} aria-labelledby={ids.form}>
        <h3 id={ids.form} className="text-base font-medium">
          {tr.review.decisionHeading}
        </h3>
        <p className="text-sm text-muted-foreground">{tr.review.noRole}</p>
      </section>
    );
  }

  const showEdit = canEdit && selected === 'onaylandi';
  const secondStage = current.ikinci_onay_bekliyor && current.hedef_tablo === 'unit';

  return (
    <form
      aria-labelledby={ids.form}
      aria-busy={pending}
      noValidate
      className={className}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      <div className="flex flex-col gap-4">
        <h3 id={ids.form} className="text-base font-medium">
          {tr.review.decisionHeading}
        </h3>

        {block === 'closed' ? (
          <Alert>
            <AlertTitle>{tr.review.closedTitle}</AlertTitle>
            <AlertDescription>{tr.review.closedBody}</AlertDescription>
          </Alert>
        ) : null}
        {approveClosed ? (
          <p className="text-sm text-muted-foreground" data-testid="approve-closed-reason">
            {block === 'own-proposal'
              ? tr.review.blockedOwnProposal
              : tr.review.blockedSameFirstApprover}
          </p>
        ) : null}
        {secondStage ? (
          <p className="text-sm text-muted-foreground">{tr.review.secondStageNote}</p>
        ) : null}

        {problems.length > 0 || error !== null ? (
          <div ref={summaryRef} tabIndex={-1} className="outline-none">
            {problems.length > 0 ? (
              <Alert variant="destructive" data-testid="decision-summary">
                <AlertTitle>{tr.review.summaryTitle}</AlertTitle>
                <AlertDescription>
                  <ul className="list-disc pl-5">
                    {problems.map((message) => (
                      <li key={message}>{message}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            ) : null}
            {error !== null && problems.length === 0 ? (
              <ProblemMessage error={error} context="decision" />
            ) : null}
          </div>
        ) : null}

        {stale ? (
          stale.after ? (
            <StaleRecord before={stale.before} after={stale.after} />
          ) : (
            <ProblemMessage error={stale.refreshError} context="decision" />
          )
        ) : null}

        <RadioGroup
          aria-label={tr.review.decisionLegend}
          value={selected}
          disabled={closed}
          onKeyDown={onKeyDown}
          onValueChange={(value) => setKarar(value === 'onaylandi' ? 'onaylandi' : 'reddedildi')}
        >
          <Label className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value="onaylandi" disabled={closed || approveClosed} />
            {tr.review.approve}
          </Label>
          <Label className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value="reddedildi" disabled={closed} />
            {tr.review.reject}
          </Label>
        </RadioGroup>

        {showEdit ? (
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.edited}>{tr.review.editedText}</Label>
            <Textarea
              id={ids.edited}
              value={editedValue}
              onChange={(event) => setEdited(event.target.value)}
              onKeyDown={onKeyDown}
              aria-describedby={ids.editedHint}
              rows={6}
            />
            <p id={ids.editedHint} className="text-xs text-muted-foreground">
              {tr.review.editedHint}
            </p>
          </div>
        ) : null}
        {needsUnit && unitQuery.isPending ? (
          <p className="text-xs text-muted-foreground">{tr.review.editedLoading}</p>
        ) : null}
        {needsUnit && unitQuery.isError ? (
          <p className="text-xs text-muted-foreground">{tr.review.editedUnavailable}</p>
        ) : null}

        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.reason}>{tr.review.reason}</Label>
          <Textarea
            id={ids.reason}
            value={gerekce}
            onChange={(event) => setGerekce(event.target.value)}
            onKeyDown={onKeyDown}
            aria-describedby={ids.reasonHint}
            aria-required="true"
            disabled={closed}
            rows={3}
          />
          <p id={ids.reasonHint} className="text-xs text-muted-foreground">
            {`${tr.review.reasonHint} ${tr.review.reasonCount(codePointCount(gerekce), MAX_REASON_LENGTH)}`}
          </p>
        </div>

        {hasUnwritable ? (
          <Alert data-testid="unwritable-warning">
            <AlertTitle>{tr.review.unwritableNote}</AlertTitle>
            <AlertDescription>
              <Button type="button" variant="outline" size="sm" onClick={clean}>
                {tr.review.unwritableAction}
              </Button>
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={closed || pending}>
            {pending ? tr.review.submitting : tr.review.submit}
          </Button>
          <span className="text-xs text-muted-foreground">{tr.review.shortcutHint}</span>
        </div>

        {done ? (
          <p className="text-sm" data-testid="decision-done">
            {tr.review.decided(done.kind)}
            {done.result.ikinci_onay_bekliyor ? ` ${tr.review.secondPending}` : ''}
          </p>
        ) : null}
      </div>
    </form>
  );
}
