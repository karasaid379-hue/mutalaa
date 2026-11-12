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

const percentFormat = new Intl.NumberFormat(LOCALE, { style: 'percent', maximumFractionDigits: 1 });

/**
 * A share between 0 and 1 as a Turkish percentage (`0,87` gives `%87`). It is cut down to one decimal, never
 * rounded up, so a share just under a threshold is never shown as the threshold (0,7996 is "%79,9").
 */
export function formatPercent(share: number): string {
  return percentFormat.format(Math.floor(share * 1000 + 1e-9) / 1000);
}

const decimalFormat = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 2 });

/** A decimal number with at most two fraction digits (for example an IDF value). */
export function formatDecimal(value: number): string {
  return decimalFormat.format(value);
}
