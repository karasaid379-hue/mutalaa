// Ties form error messages to their fields: the field gets `aria-invalid` and the id of the message in
// `aria-describedby` (next to its hint), and a message in an error summary is a link that focuses the field.

export interface FieldProblem {
  /** Id of the form control the message is about; null for a message that belongs to no single field. */
  fieldId: string | null;
  message: string;
}

/** Id of the message at `index` of the summary list `listId`. */
export function problemId(listId: string, index: number): string {
  return `${listId}-${index}`;
}

/** Moves focus to a form control; for a radio group, to its first radio that is not disabled. */
export function focusField(fieldId: string): void {
  const element = document.getElementById(fieldId);
  if (!element) return;
  if (element.getAttribute('role') === 'radiogroup') {
    const radio = element.querySelector<HTMLElement>(
      '[role="radio"]:not([disabled]):not([aria-disabled="true"])',
    );
    (radio ?? element).focus();
    return;
  }
  element.focus();
}

/** `aria-invalid` and `aria-describedby` of a field, given the messages of the last submit. */
export function fieldA11y(
  problems: readonly FieldProblem[],
  fieldId: string,
  listId: string,
  hintId?: string,
): { 'aria-invalid': true | undefined; 'aria-describedby': string | undefined } {
  const own = problems
    .map((problem, index) => ({ problem, index }))
    .filter(({ problem }) => problem.fieldId === fieldId)
    .map(({ index }) => problemId(listId, index));
  const describedBy = [hintId, ...own].filter((part) => part !== undefined).join(' ');
  return {
    'aria-invalid': own.length > 0 ? true : undefined,
    'aria-describedby': describedBy === '' ? undefined : describedBy,
  };
}
