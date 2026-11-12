import type { QueueFilter } from './queries';
import type { ReviewStats } from './types';

export type QueueId = 'ocr' | 'lemma' | 'baglanti' | 'sure-adi';

export interface QueueDef {
  id: QueueId;
  path: string;
  /** The review queues (target table and field) that make up this screen; `lemma` has four tabs; a filter without `alan` counts every field of its target. */
  filters: readonly QueueFilter[];
}

/** The four review screens (BÇ-12: `kuyruk/sure-adi` is the eighth route). `quran_word_fix` is the third tab of `lemma` (A17, BÇ-12) and the Turkish lemma root mapping the fourth (A18.2). */
export const QUEUES: readonly QueueDef[] = [
  { id: 'ocr', path: '/kuyruk/ocr', filters: [{ hedef_tablo: 'unit', alan: 'metin' }] },
  {
    id: 'lemma',
    path: '/kuyruk/lemma',
    filters: [
      { hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa' },
      { hedef_tablo: 'lemma', alan: 'status' },
      { hedef_tablo: 'quran_word_fix' },
      { hedef_tablo: 'lemma', alan: 'kok_eslemesi' },
    ],
  },
  { id: 'baglanti', path: '/kuyruk/baglanti', filters: [{ hedef_tablo: 'xref', alan: 'status' }] },
  {
    id: 'sure-adi',
    path: '/kuyruk/sure-adi',
    filters: [{ hedef_tablo: 'surah_alias', alan: 'status' }],
  },
];

/** Open records of a screen from `GET /reviews/stats`; undefined while the stats are unknown. There is no per-editor count (K-25). */
export function openCount(stats: ReviewStats | undefined, queue: QueueDef): number | undefined {
  if (!stats) return undefined;
  return stats.kuyruklar
    .filter((entry) =>
      queue.filters.some(
        (f) =>
          f.hedef_tablo === entry.hedef_tablo && (f.alan === undefined || f.alan === entry.alan),
      ),
    )
    .reduce((sum, entry) => sum + entry.acik, 0);
}
