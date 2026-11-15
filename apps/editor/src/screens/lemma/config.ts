import type { QueueFilter, QueueOrder } from '@/review/queries';

/** The two orders the editor can switch between on the wave tabs. */
export type WaveOrder = Extract<QueueOrder, 'dalga' | 'olusturma'>;

export type LemmaTabId = 'anlam' | 'durum' | 'duzeltme' | 'lugat';

export const LEMMA_TAB_IDS: readonly LemmaTabId[] = ['anlam', 'durum', 'duzeltme', 'lugat'];

/**
 * The four queues of the screen. `anlam` is the word meaning draft (`lemma_gloss` + `anlam_kisa`) and the
 * default; `durum` is the lemma status (`lemma` + `status`); `duzeltme` is the root and lemma correction
 * (`quran_word_fix`, every field: `root_id`, `lemma_id`, `pos`, `features`; BÇ-12, K-13). All three take a
 * status decision (A14); only `anlam` also takes an edited meaning (K-50 madde 6). `lugat` is the Risale lügat
 * (`lugat_madde` + `tanim_tr`; K-52 madde 9 and 10): its approval needs a definition the editor writes, and it is
 * listed in descending frequency order (`sira=siklik`).
 */
export const LEMMA_FILTERS: Readonly<Record<LemmaTabId, QueueFilter>> = {
  anlam: { hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa' },
  durum: { hedef_tablo: 'lemma', alan: 'status' },
  duzeltme: { hedef_tablo: 'quran_word_fix' },
  lugat: { hedef_tablo: 'lugat_madde', alan: 'tanim_tr' },
};

export function isLemmaTab(value: unknown): value is LemmaTabId {
  return value === 'anlam' || value === 'durum' || value === 'duzeltme' || value === 'lugat';
}

export const LEMMA_ORDERS: readonly WaveOrder[] = ['dalga', 'olusturma'];

/** Default order of the lemma queues: the word wave and root order of the editorial work (K-50 madde 7). */
export const DEFAULT_LEMMA_ORDER: WaveOrder = 'dalga';

export function isQueueOrder(value: unknown): value is WaveOrder {
  return value === 'dalga' || value === 'olusturma';
}

/** Whether the tab's queue can be listed in wave order: only `lemma` and `lemma_gloss` (the API answers 400 otherwise). */
export function hasWaveOrder(tab: LemmaTabId): boolean {
  return tab === 'anlam' || tab === 'durum';
}

/** The lügat queue has one fixed order: descending frequency (the API answers 400 for any other `sira` it does not know). */
export const LUGAT_ORDER: QueueOrder = 'siklik';

/** The list filter of a tab: its base filter plus `sira` where an order applies. */
export function lemmaFilter(tab: LemmaTabId, order: WaveOrder): QueueFilter {
  if (tab === 'lugat') return { ...LEMMA_FILTERS.lugat, sira: LUGAT_ORDER };
  return hasWaveOrder(tab) ? { ...LEMMA_FILTERS[tab], sira: order } : LEMMA_FILTERS[tab];
}
