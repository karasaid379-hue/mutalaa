// Run-time readers for opaque JSON values (jsonb payloads of the API are typed `unknown`).
// Nothing here trusts the shape: every reader returns null instead of throwing.

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function readString(record: unknown, key: string): string | null {
  if (!isRecord(record)) return null;
  const value = record[key];
  return typeof value === 'string' ? value : null;
}

export function readNumber(record: unknown, key: string): number | null {
  if (!isRecord(record)) return null;
  const value = record[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

export function readBoolean(record: unknown, key: string): boolean | null {
  if (!isRecord(record)) return null;
  const value = record[key];
  return typeof value === 'boolean' ? value : null;
}

export function readArray(record: unknown, key: string): unknown[] | null {
  if (!isRecord(record)) return null;
  const value = record[key];
  return Array.isArray(value) ? value : null;
}
