import { tryParse } from '@mutalaa/anchors';

/** The two Elmalılı meals (K-49 madde 1): the original text and the simplified ("sadeleştirilmiş") edition. */
export type MealEdition = 'orijinal' | 'sade';

/** Source slug of each edition (`unit.source_id`; the `kaynak` parameter of `GET /reviews`). */
export const MEAL_SOURCE_SLUG: Readonly<Record<MealEdition, string>> = {
  orijinal: 'elmalili-meal',
  sade: 'elmalili-sade-meal',
};

/** Meal id of the anchor (`meal:{id}:{sure}:{ayet}`) of each edition; the ids are never given to another text (K-26). */
const EDITION_BY_MEAL_ID: Readonly<Record<string, MealEdition>> = {
  elmalili: 'orijinal',
  'elmalili-sade': 'sade',
};

/** The edition a meal unit anchor belongs to; null for any other anchor or an unknown meal id. */
export function mealEditionOf(anchor: string): MealEdition | null {
  const ref = tryParse(anchor);
  if (ref === null || ref.anchor.t !== 'meal') return null;
  return Object.hasOwn(EDITION_BY_MEAL_ID, ref.anchor.meal)
    ? (EDITION_BY_MEAL_ID[ref.anchor.meal] ?? null)
    : null;
}
