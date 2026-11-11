import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
  type Ref,
} from 'react';
import { Link } from 'react-router';
import type { components } from '@/api/schema';
import { useAnnounce } from '@/app/announce-context';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { labelOf } from '@/i18n/labels';
import { trc } from '@/i18n/tr-catalog';
import { isRecord } from '@/lib/payload';
import { toProblem, type Problem } from '@/lib/problem';
import { codePointCount, isWritable } from '@/lib/text';
import { ProblemLink } from '@/review/problem-list';
import { GateReportTable } from './gate-report-table';

export type ReleaseAccepted = components['schemas']['ReleaseAccepted'];
type ReleaseDetail = components['schemas']['ReleaseDetail'];

/** Largest `notlar` in code points (Backend API 4.1: the same limit as `gerekce`). */
const MAX_NOTES_LENGTH = 2000;

const FLAVORS = ['dev', 'internal', 'public'] as const;

/** Problem shown for a failed request, with the gate report the 422 `kalite-kapisi` answer carries. */
function RequestProblem({
  error,
  releaseHref,
  ref,
}: {
  error: unknown;
  releaseHref: (id: number) => string;
  ref?: Ref<HTMLDivElement>;
}) {
  const problem: Problem = toProblem(error);
  const report = isRecord(problem) ? problem['kapi_raporu'] : undefined;
  return (
    <div className="flex flex-col gap-2">
      <ProblemMessage
        ref={ref}
        error={problem}
        context="release"
        releaseLink={(id) => (
          <Link to={{ search: releaseHref(id) }} className="underline">
            {trc.releases.openReleaseLink}
          </Link>
        )}
      />
      {report !== undefined ? <GateReportTable report={report} /> : null}
    </div>
  );
}

function notesProblem(notes: string): string | null {
  if (!isWritable(notes)) return trc.releases.notesUnwritable;
  const length = codePointCount(notes);
  return length > MAX_NOTES_LENGTH ? trc.releases.notesTooLong(length, MAX_NOTES_LENGTH) : null;
}

function onModEnter(event: KeyboardEvent, submit: () => void) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    submit();
  }
}

function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  pending,
  onConfirm,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel: string;
  pending: boolean;
  onConfirm: () => void;
  children?: ReactNode;
}) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="sm:max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {children}
        <AlertDialogFooter>
          <AlertDialogCancel>{trc.releases.cancel}</AlertDialogCancel>
          <AlertDialogAction type="button" disabled={pending} onClick={onConfirm}>
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface PreviewState {
  /** The derleme and packs the preview ran for; a request is only opened for the same key. */
  key: string;
  report: unknown;
  warnings: string[];
}

export interface NewReleasePanelProps {
  /** Called when the API accepted the request (202). */
  onAccepted: (accepted: ReleaseAccepted) => void;
  /** Search string (`?yayin=...`) that opens a release; used for the link of a `yayin-suruyor` answer. */
  releaseHref: (id: number) => string;
}

/**
 * Admin form of a new release request: first the preview (`POST /releases/preview`), which shows the gate report;
 * only after a preview that the gate did not reject, for the same derleme and packs, the request
 * (`POST /releases`) can be opened, behind a confirmation dialog. The request only adds a release row; the
 * Publisher does the work.
 */
export function NewReleasePanel({ onAccepted, releaseHref }: NewReleasePanelProps) {
  const api = useApi();
  const announce = useAnnounce();
  const ids = {
    flavor: useId(),
    packs: useId(),
    packsHint: useId(),
    notes: useId(),
    notesHint: useId(),
    localProblem: useId(),
    previewHint: useId(),
  };
  const [flavor, setFlavor] = useState<string>('dev');
  const [packsText, setPacksText] = useState('');
  const [notes, setNotes] = useState('');
  const [preview, setPreview] = useState<PreviewState | null>(null);
  const [previewError, setPreviewError] = useState<unknown>(null);
  const [createError, setCreateError] = useState<unknown>(null);
  const [localProblem, setLocalProblem] = useState<string | null>(null);
  const [accepted, setAccepted] = useState<ReleaseAccepted | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [focusTick, setFocusTick] = useState(0);
  const summaryRef = useRef<HTMLDivElement>(null);
  const previewMutation = api.$api.useMutation('post', '/api/v1/releases/preview');
  const createMutation = api.$api.useMutation('post', '/api/v1/releases');

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  const packs = packsText
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part !== '');
  const key = `${flavor}|${packs.join(',')}`;
  const previewCurrent = preview !== null && preview.key === key;
  const noteIssue = notesProblem(notes);
  // The message in the summary is about the notes field only when it is the notes problem.
  const notesInvalid = localProblem !== null && localProblem === noteIssue;

  async function runPreview() {
    if (previewMutation.isPending) return;
    setPreviewError(null);
    setCreateError(null);
    setAccepted(null);
    setLocalProblem(null);
    setPreview(null);
    try {
      const result = await previewMutation.mutateAsync({
        body: { derleme: flavor, paketler: packs.length > 0 ? packs : null },
      });
      setPreview({ key, report: result.kapi_raporu, warnings: result.uyarilar });
      announce(trc.releases.previewDone);
    } catch (thrown) {
      setPreviewError(toProblem(thrown));
      setFocusTick((tick) => tick + 1);
    }
  }

  function askConfirm() {
    setCreateError(null);
    setAccepted(null);
    if (!previewCurrent) {
      setLocalProblem(trc.releases.previewNeeded);
      setFocusTick((tick) => tick + 1);
      return;
    }
    if (noteIssue !== null) {
      setLocalProblem(noteIssue);
      setFocusTick((tick) => tick + 1);
      return;
    }
    setLocalProblem(null);
    setConfirmOpen(true);
  }

  async function createRequest() {
    if (createMutation.isPending) return;
    try {
      const result = await createMutation.mutateAsync({
        body: {
          derleme: flavor,
          paketler: packs.length > 0 ? packs : null,
          notlar: notes === '' ? null : notes,
        },
      });
      setConfirmOpen(false);
      setAccepted(result);
      setPreview(null);
      setNotes('');
      announce(trc.releases.accepted(result.id, result.surum, labelOf(trc.flavor, result.derleme)));
      onAccepted(result);
    } catch (thrown) {
      setConfirmOpen(false);
      setCreateError(toProblem(thrown));
      setFocusTick((tick) => tick + 1);
    }
  }

  return (
    <section
      className="flex flex-col gap-3 rounded-lg border p-3"
      aria-labelledby={`${ids.flavor}-h`}
    >
      <h2 id={`${ids.flavor}-h`} className="text-sm font-medium">
        {trc.releases.newHeading}
      </h2>
      <p className="text-xs text-muted-foreground">{trc.releases.adminNote}</p>

      <div className="flex flex-col gap-1">
        <span id={ids.flavor} className="text-sm font-medium">
          {trc.releases.newFlavor}
        </span>
        <Select value={flavor} onValueChange={(value) => setFlavor(value ?? 'dev')}>
          <SelectTrigger aria-labelledby={ids.flavor}>
            <SelectValue>{(value: string | null) => labelOf(trc.flavor, value)}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {FLAVORS.map((item) => (
              <SelectItem key={item} value={item}>
                {labelOf(trc.flavor, item)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor={ids.packs}>{trc.releases.newPacks}</Label>
        <Input
          id={ids.packs}
          value={packsText}
          onChange={(event) => setPacksText(event.target.value)}
          aria-describedby={ids.packsHint}
          autoComplete="off"
          spellCheck={false}
        />
        <p id={ids.packsHint} className="text-xs text-muted-foreground">
          {trc.releases.newPacksHint}
        </p>
      </div>

      <div className="flex flex-col gap-1">
        <Label htmlFor={ids.notes}>{trc.releases.newNotes}</Label>
        <Textarea
          id={ids.notes}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          onKeyDown={(event) => onModEnter(event, askConfirm)}
          aria-invalid={notesInvalid ? true : undefined}
          aria-describedby={notesInvalid ? `${ids.notesHint} ${ids.localProblem}` : ids.notesHint}
          rows={3}
        />
        <p id={ids.notesHint} className="text-xs text-muted-foreground">
          {`${trc.releases.newNotesHint} ${trc.releases.shortcut}`}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="outline"
          onClick={() => void runPreview()}
          disabled={previewMutation.isPending}
        >
          {previewMutation.isPending ? trc.releases.previewing : trc.releases.preview}
        </Button>
        <Button
          type="button"
          onClick={askConfirm}
          disabled={!previewCurrent || createMutation.isPending}
          aria-describedby={!previewCurrent ? ids.previewHint : undefined}
        >
          {createMutation.isPending ? trc.releases.requesting : trc.releases.requestOpen}
        </Button>
      </div>
      {!previewCurrent ? (
        <p id={ids.previewHint} className="text-xs text-muted-foreground">
          {preview !== null ? trc.releases.previewStale : trc.releases.previewNeeded}
        </p>
      ) : null}

      {localProblem !== null ? (
        <Alert ref={summaryRef} tabIndex={-1} variant="destructive">
          <AlertTitle>{trc.releases.summaryTitle}</AlertTitle>
          <AlertDescription id={ids.localProblem}>
            <ProblemLink
              problem={{ message: localProblem, fieldId: notesInvalid ? ids.notes : null }}
            />
          </AlertDescription>
        </Alert>
      ) : null}
      {previewError !== null ? (
        <RequestProblem ref={summaryRef} error={previewError} releaseHref={releaseHref} />
      ) : null}
      {createError !== null ? (
        <RequestProblem ref={summaryRef} error={createError} releaseHref={releaseHref} />
      ) : null}
      {accepted !== null ? (
        <p className="text-sm" data-testid="release-accepted">
          {trc.releases.accepted(
            accepted.id,
            accepted.surum,
            labelOf(trc.flavor, accepted.derleme),
          )}
        </p>
      ) : null}

      {preview !== null ? (
        <div className="flex flex-col gap-2" data-testid="release-preview">
          <p className="text-sm">{trc.releases.previewDone}</p>
          {preview.warnings.length > 0 ? (
            <div>
              <p className="text-sm font-medium">{trc.releases.previewWarnings}</p>
              <ul className="list-disc pl-5 text-sm">
                {preview.warnings.map((warning, position) => (
                  <li key={`${position}:${warning}`}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <GateReportTable report={preview.report} />
        </div>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title={trc.releases.confirmCreateTitle}
        description={trc.releases.confirmCreateBody(labelOf(trc.flavor, flavor))}
        confirmLabel={trc.releases.confirm}
        pending={createMutation.isPending}
        onConfirm={() => void createRequest()}
      />
    </section>
  );
}

export interface ReleaseRequestButtonsProps {
  release: Pick<ReleaseDetail, 'id' | 'surum' | 'derleme' | 'durum'>;
  onAccepted: (accepted: ReleaseAccepted) => void;
  releaseHref: (id: number) => string;
}

type RequestKind = 'promote' | 'rollback';

/**
 * Promote (an `internal` release in the `yayinlandi` state goes to `public`) and rollback (a `yayinlandi` or
 * `geri_cekildi` release becomes the target of a new release) of one release, for admins. The buttons only
 * appear where the rule allows them; the API still has the last word (409 `durum-gecisi-gecersiz`, for
 * instance for the release that is current).
 */
export function ReleaseRequestButtons({
  release,
  onAccepted,
  releaseHref,
}: ReleaseRequestButtonsProps) {
  const api = useApi();
  const announce = useAnnounce();
  const ids = { notes: useId(), hint: useId(), problem: useId() };
  const [kind, setKind] = useState<RequestKind | null>(null);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [localProblem, setLocalProblem] = useState<string | null>(null);
  const [focusTick, setFocusTick] = useState(0);
  const summaryRef = useRef<HTMLDivElement>(null);
  const promote = api.$api.useMutation('post', '/api/v1/releases/{id}/promote');
  const rollback = api.$api.useMutation('post', '/api/v1/releases/{id}/rollback');
  const pending = promote.isPending || rollback.isPending;

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  const canPromote = release.derleme === 'internal' && release.durum === 'yayinlandi';
  const canRollback = release.durum === 'yayinlandi' || release.durum === 'geri_cekildi';
  if (!canPromote && !canRollback) return null;

  function open(next: RequestKind) {
    setError(null);
    setLocalProblem(null);
    setNotes('');
    setKind(next);
  }

  async function confirm() {
    if (kind === null || pending) return;
    const problem = notesProblem(notes);
    if (problem !== null) {
      setLocalProblem(problem);
      return;
    }
    setLocalProblem(null);
    const body = { notlar: notes === '' ? null : notes };
    const params = { path: { id: release.id } };
    try {
      const result =
        kind === 'promote'
          ? await promote.mutateAsync({ params, body })
          : await rollback.mutateAsync({ params, body });
      setKind(null);
      announce(trc.releases.accepted(result.id, result.surum, labelOf(trc.flavor, result.derleme)));
      onAccepted(result);
    } catch (thrown) {
      setKind(null);
      setError(toProblem(thrown));
      setFocusTick((tick) => tick + 1);
    }
  }

  const title =
    kind === 'promote' ? trc.releases.confirmPromoteTitle : trc.releases.confirmRollbackTitle;
  const body =
    kind === 'promote'
      ? trc.releases.confirmPromoteBody(release.id, release.surum)
      : trc.releases.confirmRollbackBody(release.id, release.surum);

  return (
    <section className="flex flex-col gap-2" aria-label={trc.releases.adminHeading}>
      <h3 className="text-sm font-medium">{trc.releases.adminHeading}</h3>
      <div className="flex flex-wrap gap-2">
        {canPromote ? (
          <Button
            type="button"
            variant="outline"
            onClick={() => open('promote')}
            disabled={pending}
          >
            {promote.isPending ? trc.releases.promoting : trc.releases.promote}
          </Button>
        ) : null}
        {canRollback ? (
          <Button
            type="button"
            variant="outline"
            onClick={() => open('rollback')}
            disabled={pending}
          >
            {rollback.isPending ? trc.releases.rollingBack : trc.releases.rollback}
          </Button>
        ) : null}
      </div>
      {error !== null ? (
        <RequestProblem ref={summaryRef} error={error} releaseHref={releaseHref} />
      ) : null}
      <ConfirmDialog
        open={kind !== null}
        onOpenChange={(next) => {
          if (!next) setKind(null);
        }}
        title={title}
        description={body}
        confirmLabel={trc.releases.confirm}
        pending={pending}
        onConfirm={() => void confirm()}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor={ids.notes}>{trc.releases.actionNotes}</Label>
          <Textarea
            id={ids.notes}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            onKeyDown={(event) => onModEnter(event, () => void confirm())}
            aria-invalid={localProblem !== null ? true : undefined}
            aria-describedby={localProblem !== null ? `${ids.hint} ${ids.problem}` : ids.hint}
            rows={3}
          />
          <p id={ids.hint} className="text-xs text-muted-foreground">
            {trc.releases.newNotesHint}
          </p>
          {localProblem !== null ? (
            <p id={ids.problem} role="alert" className="text-xs text-destructive">
              {localProblem}
            </p>
          ) : null}
        </div>
      </ConfirmDialog>
    </section>
  );
}
