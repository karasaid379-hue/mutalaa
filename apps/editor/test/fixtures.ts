// Synthetic fixtures (A15.6): typed with the generated schema, texts are made up ("Deneme paragrafı 1"),
// never Quran, meal, tafsir, hadith or Risale text.
import type { components } from '@/api/schema';
import { ok, type FakeApi } from './fake-api';

type S = components['schemas'];

export const EDITOR_EMAIL = 'editor@deneme.test';
export const OTHER_EMAIL = 'baska@deneme.test';

export function session(roller: string[] = ['editor'], email = EDITOR_EMAIL): S['SessionResponse'] {
  return { kullanici: { id: 'kullanici-1', email }, roller };
}

export function reviewItem(over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return {
    id: 1,
    hedef_tablo: 'unit',
    hedef_anahtar: 'rn:deneme:p1',
    alan: 'metin',
    eylem: 'oner',
    durum: 'acik',
    koken: 'hat',
    oneren: 'hat',
    onceki: { metin: 'Deneme paragrafı 1', content_hash: 'hash-0' },
    onerilen: { metin: 'Deneme paragrafı 1 düzeltilmiş', content_hash: 'hash-1' },
    duzenlenen: null,
    created_at: '2026-11-01T10:00:00Z',
    xmin: 100,
    dogrulanmamis: false,
    ikinci_onay_bekliyor: false,
    ...over,
  };
}

export function reviewDetail(over: Partial<S['ReviewDetailDto']> = {}): S['ReviewDetailDto'] {
  return { ...reviewItem(), dogrulanmis: false, hedef: { tablo: 'unit' }, ...over };
}

export function unitDetail(over: Partial<S['UnitDetail']> = {}): S['UnitDetail'] {
  return {
    anchor: 'rn:deneme:p1',
    kind: 'paragraf',
    role: 'govde',
    source: 'test-deneme',
    ord: 1,
    metin_durumu: 'taslak',
    status: 'aktif',
    rev: 1,
    content_hash: 'hash-0',
    parent_path: null,
    metin: 'Deneme paragrafı 1',
    marks: [],
    attrs: {},
    sentences: null,
    ayah_range: null,
    successors: null,
    data_version: 'deneme-1',
    provenance: {},
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-01T10:00:00Z',
    duzeltilebilir: true,
    kaynak_tur: 'risale',
    ...over,
  };
}

export function stats(
  entries: [string, string, number][] = [['unit', 'metin', 3]],
  classes: [string, number][] = [],
  expert = 0,
): S['ReviewStatsResponse'] {
  return {
    kuyruklar: entries.map(([hedef_tablo, alan, acik]) => ({ hedef_tablo, alan, acik })),
    toplam_acik: entries.reduce((sum, [, , acik]) => sum + acik, 0),
    baglanti_siniflari: classes.map(([sinif, acik]) => ({ sinif, acik })),
    toplam_uzmanda: expert,
  };
}

export function page(
  items: S['ReviewItemDto'][],
  nextCursor: string | null = null,
): S['ReviewListResponse'] {
  return { items, next_cursor: nextCursor };
}

/** The shell's two requests: a signed-in session and the queue counts. */
/**
 * Empty answers for the list request every screen makes on opening (queues, sources, units, releases).
 * A test that wants real rows registers its own handler afterwards: the last registration wins.
 * `/reviews/{id}` must come before `/reviews/stats`, which `signedIn` registers after this.
 */
export function emptyScreens(fake: FakeApi): void {
  fake.get('/api/v1/reviews', ok(page([])));
  fake.get('/api/v1/sources', ok([]));
  fake.get('/api/v1/units', ok({ items: [], next_cursor: null }));
  fake.get('/api/v1/releases', ok({ items: [], next_cursor: null }));
}

/** The shell's two requests: a signed-in session and the queue counts (plus empty screen lists). */
export function signedIn(fake: FakeApi, roller: string[] = ['editor'], email = EDITOR_EMAIL): void {
  emptyScreens(fake);
  fake.get('/api/v1/auth/me', ok(session(roller, email)));
  fake.get('/api/v1/reviews/stats', ok(stats()));
}
