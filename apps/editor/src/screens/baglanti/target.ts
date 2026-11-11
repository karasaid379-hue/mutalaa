import { format, tryParse } from '@mutalaa/anchors';

/** The single meal of the project (Elmalılı, K-13); the meal anchor of an ayah is `meal:{id}:{sure}:{ayet}`. */
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
