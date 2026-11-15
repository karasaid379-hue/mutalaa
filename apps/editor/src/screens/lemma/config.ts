import type { QueueFilter } from '@/review/queries';
import type { ApprovalFilter } from './approval';

export type LemmaTabId = 'anlam' | 'durum' | 'duzeltme' | 'kok';

export const LEMMA_TAB_IDS: readonly LemmaTabId[] = ['anlam', 'durum', 'duzeltme', 'kok'];

/**
 * The three queues of the screen. `anlam` is the word meaning draft (`lemma_gloss` + `anlam_kisa`) and the
 * default; `durum` is the lemma status (`lemma` + `status`); `duzeltme` is the root and lemma correction
 * (`quran_word_fix`, every field: `root_id`, `lemma_id`, `pos`, `features`; BÇ-12, K-13); `kok` is the Turkish
 * lemma root mapping (`lemma` + `kok_eslemesi`, A18.2: candidates and objections to automatic approvals). All
 * four take a status decision (A14); `anlam` also takes an edited meaning (K-50 madde 6) and `kok` an edited
 * mapping (K-51 madde 9).
 */
export const LEMMA_FILTERS: Readonly<Record<LemmaTabId, QueueFilter>> = {
  anlam: { hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa' },
  durum: { hedef_tablo: 'lemma', alan: 'status' },
  duzeltme: { hedef_tablo: 'quran_word_fix' },
  kok: { hedef_tablo: 'lemma', alan: 'kok_eslemesi' },
};

export function isLemmaTab(value: unknown): value is LemmaTabId {
  return value === 'anlam' || value === 'durum' || value === 'duzeltme' || value === 'kok';
}

/** The two orders of the lemma queues (the link class order belongs to the link queue). */
export type LemmaOrder = 'dalga' | 'olusturma';

export const LEMMA_ORDERS: readonly LemmaOrder[] = ['dalga', 'olusturma'];

/** Default order of the lemma queues: the word wave and root order of the editorial work (K-50 madde 7). */
export const DEFAULT_LEMMA_ORDER: LemmaOrder = 'dalga';

export function isQueueOrder(value: unknown): value is LemmaOrder {
  return value === 'dalga' || value === 'olusturma';
}

/**
 * Whether the tab's queue is listed in wave order: the wave and root order belongs to the Arabic lemma work (`lemma`
 * status and `lemma_gloss`); the Turkish mapping queue is in creation order, and the API answers 400 for the
 * correction target.
 */
export function hasWaveOrder(tab: LemmaTabId): boolean {
  return tab === 'anlam' || tab === 'durum';
}

/**
 * The list filter of a tab: its base filter plus `sira` where the order applies, and on the Turkish mapping tab
 * the server's approval path filter (`onay_yolu`; "hepsi" sends none).
 */
export function lemmaFilter(
  tab: LemmaTabId,
  order: LemmaOrder,
  approval: ApprovalFilter = 'hepsi',
): QueueFilter {
  const base = hasWaveOrder(tab) ? { ...LEMMA_FILTERS[tab], sira: order } : LEMMA_FILTERS[tab];
  return tab === 'kok' && approval !== 'hepsi' ? { ...base, onay_yolu: approval } : base;
}
