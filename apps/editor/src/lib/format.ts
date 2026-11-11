// Formatting is always tr-TR and explicit; nothing follows the device locale.

const LOCALE = 'tr-TR';

export const trCollator = new Intl.Collator('tr');

/** Turkish string ordering for lists (never `localeCompare` without a locale). */
export function compareTr(a: string, b: string): number {
  return trCollator.compare(a, b);
}

const numberFormat = new Intl.NumberFormat(LOCALE);
const dateTimeFormat = new Intl.DateTimeFormat(LOCALE, { dateStyle: 'medium', timeStyle: 'short' });

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

/** ISO date-time to a short Turkish date and time; the raw value when it cannot be parsed. */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateTimeFormat.format(date);
}
