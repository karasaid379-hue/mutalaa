import { useId, type MouseEvent } from 'react';
import { Button } from '@/components/ui/button';
import { tr } from '@/i18n/tr';

export interface OpenQuestionButtonProps {
  /** Name of the action that has no API counterpart yet (Turkish, from tr.ts). */
  label: string;
  /** The stage that will decide it: A16, A17 or A18. */
  phase: 'A16' | 'A17' | 'A18';
}

/**
 * A control for an action whose API counterpart is undecided or deferred (K-48 madde 2). It stays in the
 * tab order (`aria-disabled`, not `disabled`), carries the "Açık soru: A1x" label and never sends a request.
 * The explanation is hidden text tied with `aria-describedby` (a `title` is not read on touch or by every
 * screen reader), and the pressed-down movement is off while the control is closed.
 */
export function OpenQuestionButton({ label, phase }: OpenQuestionButtonProps) {
  const hintId = useId();
  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-disabled="true"
        aria-describedby={hintId}
        data-open-question={phase}
        className="cursor-not-allowed opacity-60 hover:bg-background hover:text-foreground dark:hover:bg-input/30"
        onClick={(event: MouseEvent<HTMLElement>) => event.preventDefault()}
      >
        {`${label} · ${tr.openQuestion(phase)}`}
      </Button>
      <span id={hintId} className="sr-only">
        {tr.openQuestionHint}
      </span>
    </>
  );
}
