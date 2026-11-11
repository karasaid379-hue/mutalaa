import { tr } from './tr';

type LabelTable = Readonly<Record<string, string>>;

/** Turkish label of an API value; an unknown value is returned raw (never hidden, never guessed). */
export function labelOf(table: LabelTable, value: string | null | undefined): string {
  if (value === null || value === undefined) return '';
  return Object.hasOwn(table, value) ? (table[value] ?? value) : value;
}

export const statusLabel = (value: string | null | undefined) => labelOf(tr.labels.status, value);
export const actionLabel = (value: string | null | undefined) => labelOf(tr.labels.action, value);
export const fieldLabel = (value: string | null | undefined) => labelOf(tr.labels.field, value);
export const originLabel = (value: string | null | undefined) => labelOf(tr.labels.origin, value);
export const roleLabel = (value: string | null | undefined) => labelOf(tr.labels.role, value);
export const targetLabel = (value: string | null | undefined) => labelOf(tr.labels.target, value);
export const reviewFieldLabel = (value: string | null | undefined) =>
  labelOf(tr.labels.reviewField, value);
