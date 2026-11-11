import { IMMUTABLE_SOURCE_KIND, IMMUTABLE_UNIT_KIND } from '@/review/rules';
import type { UnitDetail } from '@/review/types';

/** Whether the unit's text is a ready source text (Tanzil): the API refuses a correction with 422 `degistirilemez-metin`. */
export function isImmutableUnit(
  unit: Pick<UnitDetail, 'kind' | 'kaynak_tur' | 'duzeltilebilir'>,
): boolean {
  return (
    !unit.duzeltilebilir ||
    unit.kind === IMMUTABLE_UNIT_KIND ||
    unit.kaynak_tur === IMMUTABLE_SOURCE_KIND
  );
}
