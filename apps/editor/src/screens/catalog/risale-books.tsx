import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
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
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Textarea } from '@/components/ui/textarea';
import { labelOf } from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { formatBookIfMatch } from '@/lib/etag';
import { formatNumber } from '@/lib/format';
import { toProblem, problemCode, problemStatus } from '@/lib/problem';
import { canApproveBooks } from '@/lib/roles';
import { codePointCount, isWritable } from '@/lib/text';
import { ME_PATH, SESSION_QUERY_OPTIONS } from '@/review/queries';

type Book = components['schemas']['RisaleBookDto'];
type BookApproved = components['schemas']['RisaleBookApproveResult'];

const BOOKS_PATH = '/api/v1/risale/books' as const;
const BOOK_PATH = '/api/v1/risale/books/{kitap}' as const;
const APPROVE_PATH = '/api/v1/risale/books/{kitap}/approve' as const;

/** Largest `gerekce` in code points (the same limit as the review decisions). */
const MAX_REASON_LENGTH = 2000;

/** The source that carries every Risale book (K-51 madde 2); the book list is shown in its detail. */
export const RISALE_TEXT_SOURCE = 'risale-rnk-metin';

function reasonProblem(reason: string): string | null {
  if (reason.trim() === '') return trc.risale.reasonRequired;
  if (!isWritable(reason)) return trc.risale.reasonUnwritable;
  const length = codePointCount(reason);
  return length > MAX_REASON_LENGTH ? trc.risale.reasonTooLong(length, MAX_REASON_LENGTH) : null;
}

function onModEnter(event: KeyboardEvent, submit: () => void) {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    submit();
  }
}

interface ApprovalDialogProps {
  book: Pick<Book, 'slug' | 'baslik'>;
  onClose: () => void;
  onApproved: (result: BookApproved) => void;
}

/**
 * Confirmation of one book approval (admin). It reads the book again (`GET /risale/books/{kitap}`), shows the draft
 * count and the prerequisites, asks for the sample reading declaration (tur 2) and a reason, and sends
 * `POST /risale/books/{kitap}/approve` with `If-Match: "{ozet}"`. A 412 reloads the book and keeps the input; a 422
 * `on-kosul-eksik` lists the missing prerequisites. Nothing is resent automatically.
 */
function ApprovalDialog({ book, onClose, onApproved }: ApprovalDialogProps) {
  const api = useApi();
  const queryClient = useQueryClient();
  const announce = useAnnounce();
  const ids = { reason: useId(), reasonProblem: useId(), sample: useId(), sampleProblem: useId() };
  const [reason, setReason] = useState('');
  const [sample, setSample] = useState(false);
  const [reasonIssue, setReasonIssue] = useState<string | null>(null);
  const [sampleIssue, setSampleIssue] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [focusTick, setFocusTick] = useState(0);
  const summaryRef = useRef<HTMLDivElement>(null);
  const detail = api.$api.useQuery(
    'get',
    BOOK_PATH,
    { params: { path: { kitap: book.slug } } },
    { retry: false, refetchOnMount: 'always' },
  );
  const approve = api.$api.useMutation('post', APPROVE_PATH);

  useEffect(() => {
    if (focusTick > 0) summaryRef.current?.focus();
  }, [focusTick]);

  const data = detail.data;
  const refreshing = detail.isFetching && data !== undefined;

  async function submit() {
    if (approve.isPending || data === undefined) return;
    const reasonFound = reasonProblem(reason);
    const sampleFound = sample ? null : trc.risale.sampleRequired;
    setReasonIssue(reasonFound);
    setSampleIssue(sampleFound);
    setError(null);
    if (reasonFound !== null || sampleFound !== null) return;
    try {
      const result = await approve.mutateAsync({
        params: {
          path: { kitap: book.slug },
          header: { 'If-Match': formatBookIfMatch(data.ozet) },
        },
        body: { gerekce: reason, ornek_okuma_yapildi: true },
      });
      announce(trc.risale.approved(book.baslik, formatNumber(result.onaylanan_birim_sayisi)));
      void queryClient.invalidateQueries({ queryKey: ['get', BOOKS_PATH] });
      void queryClient.invalidateQueries({ queryKey: ['get', BOOK_PATH] });
      onApproved(result);
    } catch (thrown) {
      const problem = toProblem(thrown);
      setError(problem);
      setFocusTick((tick) => tick + 1);
      // The digest no longer matches (or the book moved on): read it again; the input stays as it is.
      if (problemStatus(problem) === 412 && problemCode(problem) === 'surum-uyusmazligi') {
        void detail.refetch();
        void queryClient.invalidateQueries({ queryKey: ['get', BOOKS_PATH] });
      }
    }
  }

  return (
    <AlertDialog open onOpenChange={(next) => (next ? undefined : onClose())}>
      <AlertDialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle>{trc.risale.dialogTitle(book.baslik)}</AlertDialogTitle>
          <AlertDialogDescription>
            {data !== undefined
              ? trc.risale.dialogBody(formatNumber(data.taslak_sayisi))
              : trc.risale.detailLoading}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {detail.isPending ? (
          <div className="flex flex-col gap-2" data-testid="risale-detail-loading">
            <Skeleton className="h-6" />
            <Skeleton className="h-6" />
          </div>
        ) : detail.isError ? (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium">{trc.risale.detailFailed}</p>
            <ProblemMessage error={detail.error} context="risaleBook" />
            <div>
              <Button type="button" variant="outline" onClick={() => void detail.refetch()}>
                {tr.ui.retry}
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <section aria-label={trc.risale.prerequisites} className="flex flex-col gap-1 text-sm">
              <h3 className="font-medium">{trc.risale.prerequisites}</h3>
              <ul className="list-disc pl-5" data-testid="risale-prerequisites">
                <li data-ok={data?.gbut_kaniti ? 'true' : 'false'}>
                  {data?.gbut_kaniti
                    ? trc.risale.evidenceOk
                    : trc.risale.evidenceMissing(formatNumber(data?.kanitsiz_birim_sayisi ?? 0))}
                </li>
                <li data-ok={data?.dogrulandi ? 'true' : 'false'}>
                  {data?.dogrulandi ? trc.risale.slugOk : trc.risale.slugMissing}
                </li>
              </ul>
              <p className="text-xs text-muted-foreground">
                {`${trc.risale.digestLabel}: `}
                <code className="break-all">{data?.ozet}</code>
              </p>
              {refreshing ? (
                <p className="text-xs text-muted-foreground" role="status">
                  {trc.risale.detailRefreshing}
                </p>
              ) : null}
            </section>

            <div className="flex flex-col gap-1">
              <Label htmlFor={ids.sample} className="min-h-6 gap-2 font-normal">
                <Checkbox
                  id={ids.sample}
                  checked={sample}
                  disabled={approve.isPending}
                  aria-invalid={sampleIssue !== null ? true : undefined}
                  aria-describedby={sampleIssue !== null ? ids.sampleProblem : undefined}
                  onCheckedChange={(value) => {
                    setSample(value);
                    if (value) setSampleIssue(null);
                  }}
                />
                {trc.risale.sampleLabel}
              </Label>
              <p className="text-xs text-muted-foreground">{trc.risale.sampleHint}</p>
              {sampleIssue !== null ? (
                <p id={ids.sampleProblem} role="alert" className="text-xs text-destructive">
                  {sampleIssue}
                </p>
              ) : null}
            </div>

            <div className="flex flex-col gap-1">
              <Label htmlFor={ids.reason}>{trc.risale.reasonLabel}</Label>
              <Textarea
                id={ids.reason}
                value={reason}
                rows={3}
                disabled={approve.isPending}
                onChange={(event) => setReason(event.target.value)}
                onKeyDown={(event) => onModEnter(event, () => void submit())}
                aria-invalid={reasonIssue !== null ? true : undefined}
                aria-describedby={reasonIssue !== null ? `${ids.reasonProblem}` : undefined}
              />
              <p className="text-xs text-muted-foreground">{`${trc.risale.reasonHint} ${trc.risale.shortcut}`}</p>
              {reasonIssue !== null ? (
                <p id={ids.reasonProblem} role="alert" className="text-xs text-destructive">
                  {reasonIssue}
                </p>
              ) : null}
            </div>
          </div>
        )}

        {error !== null ? (
          <ProblemMessage ref={summaryRef} error={error} context="risaleBook" />
        ) : null}

        <AlertDialogFooter>
          <AlertDialogCancel>{trc.risale.cancel}</AlertDialogCancel>
          <AlertDialogAction
            type="button"
            disabled={approve.isPending || data === undefined}
            onClick={() => void submit()}
          >
            {approve.isPending ? trc.risale.confirming : trc.risale.confirm}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/**
 * Book list of the Risale text source with the "kitabı onayla" button (A20.8, K-51 madde 11): counts per book from
 * `GET /risale/books`; the button shows only for admins and only where a draft unit exists, and opens the
 * confirmation dialog. The server decides (403 for a non-admin, 422 for missing prerequisites).
 */
export function RisaleBooksPanel() {
  const api = useApi();
  const me = api.$api.useQuery('get', ME_PATH, undefined, SESSION_QUERY_OPTIONS);
  const admin = me.data !== undefined && canApproveBooks(me.data.roller);
  const list = api.$api.useQuery('get', BOOKS_PATH, undefined, { retry: false });
  const [target, setTarget] = useState<Pick<Book, 'slug' | 'baslik'> | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <section className="flex flex-col gap-2" aria-labelledby="risale-books-title">
      <h3 id="risale-books-title" className="text-sm font-medium">
        {trc.risale.heading}
      </h3>
      <p className="text-xs text-muted-foreground">{trc.risale.intro}</p>
      {!admin && me.data !== undefined ? (
        <p className="text-xs text-muted-foreground">{trc.risale.adminOnly}</p>
      ) : null}
      {notice !== null ? (
        <p className="text-sm" data-testid="risale-approved">
          {notice}
        </p>
      ) : null}
      {list.isPending ? (
        <div className="flex flex-col gap-2" data-testid="risale-loading" aria-busy="true">
          <span className="sr-only">{tr.ui.loading}</span>
          <Skeleton className="h-8" />
          <Skeleton className="h-8" />
        </div>
      ) : list.isError ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium">{trc.risale.loadFailed}</p>
          <ProblemMessage error={list.error} />
          <div>
            <Button type="button" variant="outline" onClick={() => void list.refetch()}>
              {tr.ui.retry}
            </Button>
          </div>
        </div>
      ) : list.data.length === 0 ? (
        <p className="text-sm text-muted-foreground" data-testid="risale-empty">
          {trc.risale.empty}
        </p>
      ) : (
        <Table scrollLabel={trc.risale.scrollLabel}>
          <TableCaption className="sr-only">{trc.risale.tableCaption}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>{trc.risale.colBook}</TableHead>
              <TableHead>{trc.risale.colLanguage}</TableHead>
              <TableHead className="text-right">{trc.risale.colUnits}</TableHead>
              <TableHead className="text-right">{trc.risale.colDraft}</TableHead>
              <TableHead className="text-right">{trc.risale.colApproved}</TableHead>
              <TableHead>{trc.risale.colVerified}</TableHead>
              {admin ? <TableHead>{trc.risale.colAction}</TableHead> : null}
            </TableRow>
          </TableHeader>
          <TableBody>
            {list.data.map((book) => (
              <TableRow key={book.slug} data-book={book.slug}>
                <TableCell className="whitespace-normal">
                  <span className="font-medium break-words">{book.baslik}</span>
                  <span className="block font-mono text-xs text-muted-foreground">{book.slug}</span>
                </TableCell>
                <TableCell>{labelOf(trc.risale.language, book.dil)}</TableCell>
                <TableCell className="text-right">{formatNumber(book.birim_sayisi)}</TableCell>
                <TableCell className="text-right">{formatNumber(book.taslak_sayisi)}</TableCell>
                <TableCell className="text-right">{formatNumber(book.onayli_sayisi)}</TableCell>
                <TableCell>
                  <Badge variant={book.dogrulandi ? 'secondary' : 'outline'}>
                    {book.dogrulandi ? trc.common.yes : trc.common.no}
                  </Badge>
                </TableCell>
                {admin ? (
                  <TableCell>
                    {book.taslak_sayisi > 0 ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setNotice(null);
                          setTarget({ slug: book.slug, baslik: book.baslik });
                        }}
                      >
                        {trc.risale.approve}
                        <span className="sr-only">{trc.risale.forBook(book.baslik)}</span>
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">{trc.risale.noDraft}</span>
                    )}
                  </TableCell>
                ) : null}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      {target !== null ? (
        <ApprovalDialog
          key={target.slug}
          book={target}
          onClose={() => setTarget(null)}
          onApproved={(result) => {
            setNotice(
              trc.risale.approved(target.baslik, formatNumber(result.onaylanan_birim_sayisi)),
            );
            setTarget(null);
          }}
        />
      ) : null}
    </section>
  );
}
