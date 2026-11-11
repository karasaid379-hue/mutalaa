import { format, tryParse } from '@mutalaa/anchors';

/**
 * The meal a link points at; the meal anchor of an ayah is `meal:{id}:{sure}:{ayet}`. The link target is the
 * original meal (`meal:elmalili`); the simplified meal has its own anchor (`meal:elmalili-sade`, K-49) and is not
 * a link target. The link target is the original meal; it is reviewed again in A18.
 */
export const MEAL_ID = 'elmalili';

export interface TargetInfo {
  /** True when the target anchor is an ayah (`q:{sure}:{ayet}`): its text is Arabic and it has a meal. */
  ayah: boolean;
  /** Anchor of the meal of that ayah; null for other targets. */
  mealAnchor: string | null;
}

/** Reads the unit-level target anchor of a link (`dst_anchor`); parsing is done by `@mutalaa/anchors` only. */
export function targetInfo(anchor: string): TargetInfo {
  const ref = tryParse(anchor);
  if (ref === null || ref.anchor.t !== 'q') return { ayah: false, mealAnchor: null };
  return {
    ayah: true,
    mealAnchor: format({
      anchor: { t: 'meal', meal: MEAL_ID, sure: ref.anchor.sure, ayet: ref.anchor.ayet },
    }),
  };
}
