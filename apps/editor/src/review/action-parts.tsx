import { useId, type ReactNode, type Ref } from 'react';
import { ProblemMessage } from '@/components/problem-message';
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { tr } from '@/i18n/tr';
import { MAX_REASON_LENGTH } from './limits';
import { codePointCount } from '@/lib/text';
import { problemStatus, toProblem } from '@/lib/problem';
import { kodOf, showsServerDetail } from '@/lib/problem-text';
import { fieldA11y, type FieldProblem } from './field-errors';
import { ProblemList } from './problem-list';

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

export interface ReasonFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** Id of the textarea; the error summary links to it. */
  fieldId: string;
  /** The messages of the last submit and the id of their summary list (`aria-invalid` and `aria-describedby`). */
  problems: readonly FieldProblem[];
  listId: string;
  /** Lets a form move focus to the field (when it opens). */
  inputRef?: Ref<HTMLTextAreaElement>;
}

/** The reason field of an action form: its messages are in the error summary, the field points to them. */
export function ReasonField({
  label,
  value,
  onChange,
  fieldId,
  problems,
  listId,
  inputRef,
}: ReasonFieldProps) {
  const hintId = useId();
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={fieldId}>{label}</Label>
      <Textarea
        id={fieldId}
        ref={inputRef}
        value={value}
        rows={3}
        aria-required="true"
        {...fieldA11y(problems, fieldId, listId, hintId)}
        onChange={(event) => onChange(event.target.value)}
      />
      <p id={hintId} className="text-xs text-muted-foreground">
        {tr.review.reasonCount(codePointCount(value), MAX_REASON_LENGTH)}
      </p>
    </div>
  );
}

export interface FormErrorsProps {
  /** The region that takes focus after a failed submit (`useFocusRequest`). */
  regionRef: Ref<HTMLDivElement>;
  title: string;
  /** The field problems of the last submit (an alert with links to the fields). */
  problems: readonly FieldProblem[];
  listId: string;
  summaryTestId?: string;
  /** The answer's error (an `ActionError` or a `ProblemMessage`), shown under the summary. */
  children?: ReactNode;
}

/** The error area of an action form: an alert with the field problems and the answer's error; focus moves here. */
export function FormErrors({
  regionRef,
  title,
  problems,
  listId,
  summaryTestId,
  children,
}: FormErrorsProps) {
  if (problems.length === 0 && !children) return null;
  return (
    <div ref={regionRef} tabIndex={-1} className="flex flex-col gap-2 outline-none">
      {problems.length > 0 ? (
        <Alert variant="destructive" data-testid={summaryTestId}>
          <AlertTitle>{title}</AlertTitle>
          <AlertDescription>
            <ProblemList problems={problems} listId={listId} />
          </AlertDescription>
        </Alert>
      ) : null}
      {children}
    </div>
  );
}
