// Random sample for bulk approval (Iktibas tespiti 12): ceil(n/10) records, uniformly drawn with
// crypto.getRandomValues, rejection sampling (no modulo bias) and a partial Fisher-Yates shuffle.

export type RandomUint32 = () => number;

const TWO_POW_32 = 2 ** 32;

export function secureRandomUint32(): number {
  const buffer = new Uint32Array(1);
  crypto.getRandomValues(buffer);
  return buffer[0]!;
}

/** Sample size for `total` records: ceil(total / 10); 0 for an empty selection. */
export function sampleSize(total: number): number {
  return total <= 0 ? 0 : Math.ceil(total / 10);
}

/** Uniform integer in [0, max) by rejection sampling. */
export function randomBelow(max: number, random: RandomUint32 = secureRandomUint32): number {
  if (!Number.isInteger(max) || max < 1 || max > TWO_POW_32) {
    throw new RangeError('max must be an integer between 1 and 2^32');
  }
  const limit = TWO_POW_32 - (TWO_POW_32 % max);
  let value = random();
  while (value >= limit) value = random();
  return value % max;
}

/** `count` distinct items chosen uniformly at random (partial Fisher-Yates); the input is not changed. */
export function pickSample<T>(
  items: readonly T[],
  count: number,
  random: RandomUint32 = secureRandomUint32,
): T[] {
  const pool = items.slice();
  const take = Math.min(Math.max(count, 0), pool.length);
  for (let i = 0; i < take; i++) {
    const j = i + randomBelow(pool.length - i, random);
    const swap = pool[i]!;
    pool[i] = pool[j]!;
    pool[j] = swap;
  }
  return pool.slice(0, take);
}
