import type { QueueFilter } from '@/review/queries';
import { MEAL_SOURCE_SLUG, type MealEdition } from './meal-source';

/** Target table and field of the OCR queue: the text of a unit (K-43 madde 4). */
export const OCR_BASE_FILTER = { hedef_tablo: 'unit', alan: 'metin' } as const;

/** Source tabs: every source, or one Elmalılı meal edition. */
export const OCR_SOURCE_TABS = ['hepsi', 'orijinal', 'sade'] as const;
export type OcrSourceTab = (typeof OCR_SOURCE_TABS)[number];

/** Stage views: every open record, those without a first approval, those waiting for the second one. */
export const OCR_STAGE_VIEWS = ['hepsi', 'ilk', 'ikinci'] as const;
export type OcrStageView = (typeof OCR_STAGE_VIEWS)[number];

export function isOcrSourceTab(value: unknown): value is OcrSourceTab {
  return OCR_SOURCE_TABS.some((tab) => tab === value);
}

export function isOcrStageView(value: unknown): value is OcrStageView {
  return OCR_STAGE_VIEWS.some((view) => view === value);
}

/** The queue filter of a source tab and a stage view (`kaynak` and `asama` of `GET /reviews`). */
export function ocrFilter(source: OcrSourceTab, stage: OcrStageView): QueueFilter {
  const edition: MealEdition | null = source === 'hepsi' ? null : source;
  return {
    ...OCR_BASE_FILTER,
    ...(edition !== null ? { kaynak: MEAL_SOURCE_SLUG[edition] } : {}),
    ...(stage !== 'hepsi' ? { asama: stage } : {}),
  };
}
