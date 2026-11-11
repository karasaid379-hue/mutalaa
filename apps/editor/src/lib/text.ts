// Text safety helpers for user input that goes to the API (Backend API 4.2): NUL (U+0000) and lone
// surrogates are rejected by the server (400 `dogrulama`); the panel warns first and cleans only on request.
// No normalization anywhere (K-26): text is measured and checked, never rewritten silently.

function isHigh(unit: number): boolean {
  return unit >= 0xd800 && unit <= 0xdbff;
}

function isLow(unit: number): boolean {
  return unit >= 0xdc00 && unit <= 0xdfff;
}

/** Number of Unicode code points (the server limit for `gerekce` is counted this way). */
export function codePointCount(text: string): number {
  let count = 0;
  for (let i = 0; i < text.length; i++) {
    if (isHigh(text.charCodeAt(i)) && i + 1 < text.length && isLow(text.charCodeAt(i + 1))) i++;
    count++;
  }
  return count;
}

export interface UnwritableReport {
  nul: boolean;
  loneSurrogate: boolean;
}

/** What makes the text unwritable (NUL, lone surrogate); both false when it is fine. */
export function findUnwritable(text: string): UnwritableReport {
  const report: UnwritableReport = { nul: false, loneSurrogate: false };
  for (let i = 0; i < text.length; i++) {
    const unit = text.charCodeAt(i);
    if (unit === 0) {
      report.nul = true;
    } else if (isHigh(unit)) {
      if (i + 1 < text.length && isLow(text.charCodeAt(i + 1))) i++;
      else report.loneSurrogate = true;
    } else if (isLow(unit)) {
      report.loneSurrogate = true;
    }
  }
  return report;
}

export function isWritable(text: string): boolean {
  const report = findUnwritable(text);
  return !report.nul && !report.loneSurrogate;
}

/** Removes NUL and lone surrogates; everything else is kept as is. Called only from an explicit button. */
export function stripUnwritable(text: string): string {
  let out = '';
  for (let i = 0; i < text.length; i++) {
    const unit = text.charCodeAt(i);
    if (unit === 0 || isLow(unit)) continue;
    if (isHigh(unit)) {
      if (i + 1 < text.length && isLow(text.charCodeAt(i + 1))) {
        out += text.slice(i, i + 2);
        i++;
      }
      continue;
    }
    out += text.charAt(i);
  }
  return out;
}
