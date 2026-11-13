import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { ProblemMessage } from '@/components/problem-message';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { formatIfMatch } from '@/lib/etag';
import {
  codePointCount,
  findUnwritable,
  glossLength,
  stripUnwritable,
  trimGloss,
} from '@/lib/text';
import { problemCode, problemStatus, toProblem } from '@/lib/problem';
import { canDecideStatus } from '@/lib/roles';
import { fieldA11y, type FieldProblem } from './field-errors';
import { ProblemList } from './problem-list';
import { RootMappingFields } from './root-mapping-fields';
import { MAX_GLOSS_LENGTH, MAX_REASON_LENGTH } from './limits';
import {
  ME_PATH,
  REVIEWS_PATH,
  SESSION_QUERY_OPTIONS,
  invalidateReviewCounts,
  patchReviewInLists,
  removeReviewsFromLists,
  reviewDetailInit,
  reviewDetailKey,
  REVIEW_PATH,
  toListItem,
} from './queries';
import {
  approveBlockReason,
  canEditValue,
  isFirstStageUnitText,
  isGlossEditable,
  isRootMappingEditable,
  parseIdInput,
  proposedGloss,
  proposedMapping,
  proposedText,
  type UnitEditInfo,
} from './rules';
import { StaleRecord } from './stale-record';
import type { DecisionEdit, DecisionKind, DecisionResult, ReviewDetail } from './types';

/**
 * An edit of the approval that a screen builds with fields of its own (the link target, span and type; the new
 * value of a word fix): `value` is the `duzenlenen` body (null = a plain approval) and `problems` block the
 * submit while the approval is chosen. The form sends it only with "Onayla".
 */
export interface ExtraEdit {
  value: DecisionEdit | null;
  problems: readonly FieldProblem[];
}

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
  /** The screen's own edit of the approval (see `ExtraEdit`); its fields are `extraFields`. */
  extraEdit?: ExtraEdit;
  /** The screen's own edit fields, drawn inside the form under the decision choice. */
  extraFields?: ReactNode;
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
 * The Turkish message of a server rejection that belongs to the edited meaning: a 400 `dogrulama` with an error
 * on `duzenlenen.anlam_kisa`, or a 409 (the target is not a candidate or the decision rule is broken). null for
 * everything else (it is shown as a normal problem).
 */
function glossProblemMessage(problem: ReturnType<typeof toProblem>): string | null {
  const status = problemStatus(problem);
  if (status === 409) return trLemma.edit.notCandidate;
  if (
    status === 400 &&
    problem.errors !== undefined &&
    Object.hasOwn(problem.errors, 'duzenlenen.anlam_kisa')
  ) {
    return trLemma.edit.serverInvalid;
  }
  return null;
}

/**
 * The Turkish message of a server rejection of an edited root mapping: a 400 `dogrulama` that is not about the
 * reason (root or Arabic lemma missing, the lemma is not Arabic, its root differs). The server's own message is
 * kept next to it. null for everything else.
 */
function mappingProblemMessage(problem: ReturnType<typeof toProblem>): string | null {
  if (problemStatus(problem) !== 400 || problemCode(problem) !== 'dogrulama') return null;
  if (problem.errors !== undefined && Object.hasOwn(problem.errors, 'gerekce')) return null;
  return problem.detail
    ? `${trLemma.kok.edit.serverInvalid} ${tr.problem.detail}: ${problem.detail}`
    : trLemma.kok.edit.serverInvalid;
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
  extraEdit,
  extraFields,
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
    gloss: useId(),
    glossHint: useId(),
    glossError: useId(),
    decision: useId(),
    summary: useId(),
    approveClosed: useId(),
    mapRoot: useId(),
    mapAr: useId(),
  };

  const [karar, setKarar] = useState<DecisionKind | ''>('');
  const [gerekce, setGerekce] = useState('');
  const [edited, setEdited] = useState<string | null>(null);
  const [gloss, setGloss] = useState<string | null>(null);
  // A Turkish lemma mapping (K-51 madde 9): the typed root id, Arabic lemma id and switch; null = untouched.
  const [mapRoot, setMapRoot] = useState<string | null>(null);
  const [mapAr, setMapAr] = useState<string | null>(null);
  const [mapEtym, setMapEtym] = useState<boolean | null>(null);
  const [problems, setProblems] = useState<FieldProblem[]>([]);
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
  const roleMissing = me.data !== undefined && !canDecideStatus(roles, current.durum);
  const block = approveBlockReason(current, me.data?.kullanici.email);
  const closed = block === 'closed' || done !== null;
  const canEdit = canEditValue(current, unitInfo) && !closed;
  const baseline = proposedText(current) ?? unitInfo?.metin ?? '';
  const editedValue = edited ?? baseline;
  // A word meaning review (K-50 madde 6): approval may carry an edited meaning; an edit equal to the proposal is not sent.
  const glossBaseline = proposedGloss(current) ?? '';
  const glossValue = gloss ?? glossBaseline;
  const glossAllowed = isGlossEditable(current) && !closed;
  const approveClosed = block === 'own-proposal' || block === 'same-first-approver';
  // A closed "Onayla" cannot stay selected.
  const selected: DecisionKind | '' = approveClosed && karar === 'onaylandi' ? '' : karar;
  const pending = decide.isPending;
  const showGloss = glossAllowed && selected === 'onaylandi';
  // The server measures and compares the meaning trimmed (space, tab, line feed) and in NFC; the sent value stays as typed.
  const glossChanged = showGloss && trimGloss(glossValue) !== trimGloss(glossBaseline);
  const glossCount = glossLength(glossValue);
  const glossProblems = problems.filter((problem) => problem.fieldId === ids.gloss);
  // An open candidate mapping review: approval may carry an edited mapping; an edit equal to the proposal is not sent.
  const baseMap = proposedMapping(current);
  const rootText = mapRoot ?? (baseMap.rootId !== null ? String(baseMap.rootId) : '');
  const arText = mapAr ?? (baseMap.arLemmaId !== null ? String(baseMap.arLemmaId) : '');
  const etymValue = mapEtym ?? baseMap.etymologicalOnly ?? false;
  const showMapping = isRootMappingEditable(current) && !closed && selected === 'onaylandi';
  const parsedRoot = parseIdInput(rootText);
  const parsedAr = parseIdInput(arText);
  const mappingChanged =
    showMapping &&
    (parsedRoot !== baseMap.rootId ||
      parsedAr !== baseMap.arLemmaId ||
      etymValue !== (baseMap.etymologicalOnly ?? false));

  const unwritable = {
    gerekce: findUnwritable(gerekce),
    edited:
      canEdit && selected === 'onaylandi'
        ? findUnwritable(editedValue)
        : { nul: false, loneSurrogate: false },
    gloss: showGloss ? findUnwritable(glossValue) : { nul: false, loneSurrogate: false },
  };
  const hasUnwritable =
    unwritable.gerekce.nul ||
    unwritable.gerekce.loneSurrogate ||
    unwritable.edited.nul ||
    unwritable.edited.loneSurrogate ||
    unwritable.gloss.nul ||
    unwritable.gloss.loneSurrogate;

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  function validate(): FieldProblem[] {
    const found: FieldProblem[] = [];
    const add = (fieldId: string, message: string) => found.push({ fieldId, message });
    if (selected === '') add(ids.decision, tr.review.chooseDecision);
    if (gerekce.trim() === '') add(ids.reason, tr.review.reasonRequired);
    const length = codePointCount(gerekce);
    if (length > MAX_REASON_LENGTH) {
      add(ids.reason, tr.review.reasonTooLong(length, MAX_REASON_LENGTH));
    }
    if (unwritable.gerekce.nul || unwritable.gerekce.loneSurrogate) {
      add(ids.reason, `${tr.review.reason}: ${tr.review.unwritable}`);
    }
    if (canEdit && selected === 'onaylandi') {
      if (editedValue.trim() === '') add(ids.edited, tr.review.editedEmpty);
      if (unwritable.edited.nul || unwritable.edited.loneSurrogate) {
        add(ids.edited, `${tr.review.editedText}: ${tr.review.unwritable}`);
      }
    }
    if (glossChanged) {
      if (trimGloss(glossValue) === '') add(ids.gloss, trLemma.edit.empty);
      else if (glossCount > MAX_GLOSS_LENGTH) {
        add(ids.gloss, trLemma.edit.tooLong(glossCount, MAX_GLOSS_LENGTH));
      }
      if (unwritable.gloss.nul || unwritable.gloss.loneSurrogate) {
        add(ids.gloss, trLemma.edit.unwritable);
      }
    }
    if (extraEdit && selected === 'onaylandi') found.push(...extraEdit.problems);
    if (showMapping) {
      if (parsedRoot === 'invalid') add(ids.mapRoot, trLemma.kok.edit.rootInvalid);
      else if (parsedRoot === null) add(ids.mapRoot, trLemma.kok.edit.rootRequired);
      if (parsedAr === 'invalid') add(ids.mapAr, trLemma.kok.edit.arInvalid);
    }
    return found;
  }

  async function refresh(before: ReviewDetail) {
    try {
      // Through the query client, so a 401 reaches the session bridge of the query cache; the client also
      // stores the fetched record under its detail key.
      const data = await queryClient.fetchQuery({
        ...api.$api.queryOptions('get', REVIEW_PATH, reviewDetailInit(before.id)),
        staleTime: 0,
      });
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
    const sendGloss = glossChanged;
    const sendMapping = mappingChanged && typeof parsedRoot === 'number' && parsedAr !== 'invalid';
    const sendExtra = selected === 'onaylandi' ? (extraEdit?.value ?? null) : null;
    const snapshot = current;
    try {
      const result = await decide.mutateAsync({
        params: { path: { id: snapshot.id }, header: { 'If-Match': formatIfMatch(snapshot.xmin) } },
        body: {
          karar: selected,
          duzenlenen: sendEdit
            ? { metin: editedValue }
            : sendGloss
              ? { anlam_kisa: glossValue }
              : sendMapping
                ? { root_id: parsedRoot, ar_lemma_id: parsedAr, etymological_only: etymValue }
                : sendExtra,
          gerekce,
        },
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
      // A rejected edited meaning is shown next to its field (400 on the field, 409 for a target that is not a candidate).
      const glossMessage = sendGloss ? glossProblemMessage(problem) : null;
      const mappingMessage = sendMapping ? mappingProblemMessage(problem) : null;
      if (glossMessage !== null) {
        setProblems([{ fieldId: ids.gloss, message: glossMessage }]);
        setError(null);
      } else if (mappingMessage !== null) {
        setProblems([{ fieldId: ids.mapRoot, message: mappingMessage }]);
        setError(null);
      } else {
        setError(problem);
      }
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
    if (showGloss) setGloss(stripUnwritable(glossValue));
  }

  if (roleMissing) {
    return (
      <section className={className} aria-labelledby={ids.form}>
        <h3 id={ids.form} className="text-base font-medium">
          {tr.review.decisionHeading}
        </h3>
        <p className="text-sm text-muted-foreground" data-testid="decision-role-note">
          {current.durum === 'uzmanda' ? tr.review.expertPending : tr.review.noRole}
        </p>
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
          <p
            id={ids.approveClosed}
            className="text-sm text-muted-foreground"
            data-testid="approve-closed-reason"
          >
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
                  <ProblemList problems={problems} listId={ids.summary} />
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
          id={ids.decision}
          aria-label={tr.review.decisionLegend}
          {...fieldA11y(problems, ids.decision, ids.summary)}
          value={selected}
          disabled={closed}
          onKeyDown={onKeyDown}
          onValueChange={(value) => setKarar(value === 'onaylandi' ? 'onaylandi' : 'reddedildi')}
        >
          <Label className="min-h-6 gap-2 font-normal">
            <RadioGroupItem
              value="onaylandi"
              disabled={closed || approveClosed}
              aria-describedby={approveClosed ? ids.approveClosed : undefined}
            />
            {tr.review.approve}
          </Label>
          <Label className="min-h-6 gap-2 font-normal">
            <RadioGroupItem value="reddedildi" disabled={closed} />
            {tr.review.reject}
          </Label>
        </RadioGroup>

        {extraFields}

        {showGloss ? (
          <div className="flex flex-col gap-1" data-testid="gloss-edit">
            <Label htmlFor={ids.gloss}>{trLemma.edit.label}</Label>
            <Input
              id={ids.gloss}
              lang="tr"
              value={glossValue}
              onChange={(event) => setGloss(event.target.value)}
              onKeyDown={onKeyDown}
              aria-invalid={glossProblems.length > 0 ? true : undefined}
              aria-describedby={
                glossProblems.length > 0 ? `${ids.glossHint} ${ids.glossError}` : ids.glossHint
              }
            />
            <p id={ids.glossHint} className="text-xs text-muted-foreground">
              {`${trLemma.edit.hint} ${trLemma.edit.count(glossCount, MAX_GLOSS_LENGTH)}`}
            </p>
            {glossProblems.length > 0 ? (
              <div id={ids.glossError} className="flex flex-col gap-0.5">
                {glossProblems.map((problem) => (
                  <p key={problem.message} className="text-xs font-medium text-destructive">
                    {problem.message}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {showMapping ? (
          <RootMappingFields
            rootFieldId={ids.mapRoot}
            arFieldId={ids.mapAr}
            summaryId={ids.summary}
            problems={problems}
            root={rootText}
            arLemma={arText}
            etymologicalOnly={etymValue}
            onRoot={setMapRoot}
            onArLemma={setMapAr}
            onEtymologicalOnly={setMapEtym}
            onKeyDown={onKeyDown}
          />
        ) : null}

        {showEdit ? (
          <div className="flex flex-col gap-1">
            <Label htmlFor={ids.edited}>{tr.review.editedText}</Label>
            <Textarea
              id={ids.edited}
              value={editedValue}
              onChange={(event) => setEdited(event.target.value)}
              onKeyDown={onKeyDown}
              {...fieldA11y(problems, ids.edited, ids.summary, ids.editedHint)}
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
            {...fieldA11y(problems, ids.reason, ids.summary, ids.reasonHint)}
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
