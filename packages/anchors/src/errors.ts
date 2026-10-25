export type AnchorErrorCode =
  'BICIM' | 'SURE_ARALIGI' | 'AYET_ARALIGI' | 'TERS_ARALIK' | 'KANONIK_DEGIL' | 'UZUNLUK';

/** Thrown by parse and format for an invalid anchor. Priority of codes: K-35 item 1. */
export class AnchorError extends Error {
  readonly code: AnchorErrorCode;

  constructor(code: AnchorErrorCode, input?: unknown) {
    const shown = typeof input === 'string' ? ` (${JSON.stringify(input.slice(0, 80))})` : '';
    super(`${code}${shown}`);
    this.name = 'AnchorError';
    this.code = code;
  }
}
