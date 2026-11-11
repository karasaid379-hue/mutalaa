import { coveredAyahs, format, tryParse } from '@mutalaa/anchors';

/** How many Tanzil ayahs the card shows at most (a joined meal covers two; a long range is cut). */
export const MAX_SHOWN_AYAHS = 3;

export interface AyahAnchors {
  /** `q:{sure}:{ayet}` anchors of the ayahs the reviewed unit covers, at most `MAX_SHOWN_AYAHS`. */
  shown: string[];
  /** How many covered ayahs were left out. */
  hidden: number;
  /** True when the unit is itself an ayah (`q:`): its own text is the Tanzil text. */
  isAyah: boolean;
}

/** Tanzil ayah anchors behind a unit anchor; parsing and formatting come from `@mutalaa/anchors` only. */
export function ayahAnchors(anchor: string): AyahAnchors {
  const ref = tryParse(anchor);
  if (ref === null) return { shown: [], hidden: 0, isAyah: false };
  const all = coveredAyahs(ref).map((ayah) =>
    format({ anchor: { t: 'q', sure: ayah.sure, ayet: ayah.ayet } }),
  );
  return {
    shown: all.slice(0, MAX_SHOWN_AYAHS),
    hidden: Math.max(0, all.length - MAX_SHOWN_AYAHS),
    isAyah: ref.anchor.t === 'q',
  };
}
