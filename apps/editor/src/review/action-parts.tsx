import { useId } from 'react';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { tr } from '@/i18n/tr';
import { MAX_REASON_LENGTH } from './limits';
import { codePointCount } from '@/lib/text';
import { problemStatus, toProblem } from '@/lib/problem';
import { kodOf, showsServerDetail } from '@/lib/problem-text';

// Building blocks shared by the one-reason action forms (lemma objection and etymology, link actions).

/** The Turkish message of the statuses an action knows; any other problem is shown as the generic problem. */
export function ActionError({
  error,
  messages,
  testId,
}: {
  error: unknown;
  messages: Readonly<Record<number, string>>;
  testId: string;
}) {
  const problem = toProblem(error);
  const status = problemStatus(problem);
  const message = status !== undefined && Object.hasOwn(messages, status) ? messages[status] : null;
  if (message === null || message === undefined) return <ProblemMessage error={error} />;
  return (
    <Alert variant="destructive" data-problem-code={kodOf(problem)} data-testid={testId}>
      <AlertTitle>{message}</AlertTitle>
      {showsServerDetail(problem) ? (
        <AlertDescription>{`${tr.problem.detail}: ${problem.detail}`}</AlertDescription>
      ) : null}
    </Alert>
  );
}

export function ReasonField({
  label,
  value,
  onChange,
  error,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error: string | null;
}) {
  const fieldId = useId();
  const hintId = useId();
  const errorId = useId();
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={fieldId}>{label}</Label>
      <Textarea
        id={fieldId}
        value={value}
        rows={3}
        aria-required="true"
        aria-invalid={error !== null ? true : undefined}
        aria-describedby={error !== null ? `${hintId} ${errorId}` : hintId}
        onChange={(event) => onChange(event.target.value)}
      />
      <p id={hintId} className="text-xs text-muted-foreground">
        {tr.review.reasonCount(codePointCount(value), MAX_REASON_LENGTH)}
      </p>
      {error !== null ? (
        <p id={errorId} className="text-xs font-medium text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}
