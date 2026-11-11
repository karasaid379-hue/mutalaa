import type { QueueFilter } from '@/review/queries';

export type LemmaTabId = 'anlam' | 'durum';

export const LEMMA_TAB_IDS: readonly LemmaTabId[] = ['anlam', 'durum'];

/**
 * The two queues of the screen. `anlam` is the word meaning draft (`lemma_gloss` + `anlam_kisa`) and the
 * default; `durum` is the lemma status (`lemma` + `status`). Both only take a status decision (A14).
 */
export const LEMMA_FILTERS: Readonly<Record<LemmaTabId, QueueFilter>> = {
  anlam: { hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa' },
  durum: { hedef_tablo: 'lemma', alan: 'status' },
};

export function isLemmaTab(value: unknown): value is LemmaTabId {
  return value === 'anlam' || value === 'durum';
}
