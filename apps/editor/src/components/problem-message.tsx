import type { ReactNode, Ref } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { tr } from '@/i18n/tr';
import { isRecord, readNumber, readString } from '@/lib/payload';
import { problemIds, toProblem } from '@/lib/problem';
import { kodOf, problemText, showsServerDetail, type ProblemContext } from '@/lib/problem-text';

export interface ProblemMessageProps {
  /** Any thrown or returned error; it is turned into a Problem (network errors become `ag-hatasi`). */
  error: unknown;
  /** The operation the problem belongs to; selects the wording. */
  context?: ProblemContext;
  /** Optional link to an open release row (`yayin-suruyor`), supplied by the releases screen. */
  releaseLink?: (id: number) => ReactNode;
  /** Receives focus when an error summary has to take it (`tabIndex` is -1). */
  ref?: Ref<HTMLDivElement>;
  className?: string;
}

/**
 * Error summary for one ProblemDetails (or network) error: the Turkish message of the code (18 API codes
 * and the client codes `ag-hatasi`, `yanit-bozuk`), the server's own message where it adds information,
 * field errors, affected record ids, the open release and the trace id.
 */
export function ProblemMessage({
  error,
  context,
  releaseLink,
  ref,
  className,
}: ProblemMessageProps) {
  const problem = toProblem(error);
  const kod = kodOf(problem);
  const ids = problemIds(problem);
  const errors = problem.errors && isRecord(problem.errors) ? Object.entries(problem.errors) : [];
  const yayin = isRecord(problem.yayin) ? problem.yayin : null;
  const yayinId = readNumber(yayin, 'id');
  const anchorCode = readString(problem, 'capa_hata_kodu');
  const kimlik = readNumber(problem, 'kimlik');
  const status = typeof problem.status === 'number' && problem.status > 0 ? problem.status : null;
  const meta = [
    status !== null ? tr.problem.status(status) : null,
    typeof problem.traceId === 'string' ? `${tr.problem.traceId}: ${problem.traceId}` : null,
  ].filter((part): part is string => part !== null);

  return (
    <Alert
      ref={ref}
      tabIndex={-1}
      variant="destructive"
      data-problem-code={kod}
      className={className}
    >
      <AlertTitle>{problemText(problem, context)}</AlertTitle>
      <AlertDescription className="flex flex-col gap-1">
        {kimlik !== null ? <p>{tr.bulk.recordLabel(kimlik)}</p> : null}
        {showsServerDetail(problem) ? <p>{`${tr.problem.detail}: ${problem.detail}`}</p> : null}
        {errors.length > 0 ? (
          <div>
            <p className="font-medium">{tr.problem.fieldErrors}</p>
            <ul className="list-disc pl-5">
              {errors.map(([field, messages]) => (
                <li key={field}>
                  {`${field}: ${Array.isArray(messages) ? messages.join(' ') : String(messages)}`}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {anchorCode ? <p>{`${tr.problem.anchorCode}: ${anchorCode}`}</p> : null}
        {ids.length > 0 ? <p>{`${tr.problem.ids(ids.length)}: ${ids.join(', ')}`}</p> : null}
        {yayin && yayinId !== null ? (
          <p>
            {`${tr.problem.openRelease}: ${yayinId} ${readString(yayin, 'derleme') ?? ''} ${readString(yayin, 'durum') ?? ''} `}
            {releaseLink?.(yayinId)}
          </p>
        ) : null}
        {meta.length > 0 ? <p className="text-xs">{meta.join(' · ')}</p> : null}
      </AlertDescription>
    </Alert>
  );
}
