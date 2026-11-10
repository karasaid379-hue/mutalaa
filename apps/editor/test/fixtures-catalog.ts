// Synthetic fixtures of the catalog screens (kaynaklar, birimler, yayinlar; A15.5), typed with the generated
// schema. Texts are made up ("Deneme paragrafı 1"); Arabic samples are plain letter sequences built with
// String.fromCodePoint, never Quran text. Shared fixtures stay in fixtures.ts.
import type { components } from '@/api/schema';

type S = components['schemas'];

/** Three Arabic letters (alef, beh, jeem) in a row: a letter sequence that is not a word of any text. */
export const ARABIC_SAMPLE = String.fromCodePoint(0x0627, 0x0628, 0x062c);

export function source(over: Partial<S['SourceDto']> = {}): S['SourceDto'] {
  return {
    slug: 'test-deneme',
    tur: 'risale',
    baslik: 'Deneme kaynağı',
    yazar: 'Deneme yazarı',
    surum: '1.0',
    provider: 'deneme-saglayici',
    kaynak_url: 'https://deneme.test/kaynak',
    alinma_tarihi: '2026-11-02',
    dosya_sha256: 'a'.repeat(64),
    baski_bilgisi: { baski: 'Deneme baskısı' },
    atif_metni: '  Deneme atıf satırı\n\nikinci satır  ',
    atif_url: 'https://deneme.test/atif',
    notice_text: '\n  Deneme bildirim metni\n  ikinci satır\n',
    notlar: 'Deneme notu',
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-02T10:00:00Z',
    birim_sayisi: 1234,
    ...over,
  };
}

export function unitItem(over: Partial<S['UnitListItem']> = {}): S['UnitListItem'] {
  return {
    anchor: 'rn:deneme:p1',
    kind: 'risale',
    role: 'govde',
    source: 'test-deneme',
    ord: 1,
    metin_durumu: 'taslak',
    status: 'etkin',
    rev: 1,
    content_hash: 'hash-0',
    parent_path: null,
    metin: 'Deneme paragrafı 1',
    ...over,
  };
}

export function unitPage(
  items: S['UnitListItem'][],
  nextCursor: string | null = null,
): S['UnitListResponse'] {
  return { items, next_cursor: nextCursor };
}

/** A unit of a Tanzil-like source: Arabic letters, immutable. */
export function tanzilUnit(over: Partial<S['UnitDetail']> = {}): S['UnitDetail'] {
  return {
    anchor: 'q:1:1',
    kind: 'ayet',
    role: 'govde',
    source: 'test-kuran',
    ord: 1,
    metin_durumu: 'onayli',
    status: 'etkin',
    rev: 1,
    content_hash: 'hash-q',
    parent_path: null,
    metin: ARABIC_SAMPLE,
    marks: [],
    attrs: {},
    sentences: null,
    ayah_range: null,
    successors: null,
    data_version: 'deneme-1',
    provenance: {},
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-01T10:00:00Z',
    duzeltilebilir: false,
    kaynak_tur: 'kuran_metni',
    ...over,
  };
}

export const RELEASE_GATE_REPORT = {
  flavor: 'internal',
  rejected: true,
  rows: [
    {
      kind: 'paket',
      id: 'deneme-paket',
      decision: 'girdi',
      rule: null,
      reason: 'uygun',
      count: 1,
    },
    {
      kind: 'kaynak',
      id: 'test-deneme',
      decision: 'girmedi',
      rule: 'P-07',
      reason: 'deneme gerekçe',
      count: 1,
    },
    {
      kind: 'birim',
      id: 'test-deneme',
      decision: 'girdi',
      rule: null,
      reason: 'uygun',
      count: 1500,
    },
  ],
  violations: [{ rule: 'P-11', subject: 'rn:deneme:p1', reason: 'deneme ihlal' }],
  violations_omitted: [{ rule: 'P-11', reason: 'deneme ihlal', count: 7 }],
};

export function releaseItem(over: Partial<S['ReleaseSummary']> = {}): S['ReleaseSummary'] {
  return {
    id: 7,
    surum: '2026.11.1',
    derleme: 'internal',
    durum: 'yayinlandi',
    talep: 'yayin',
    kaynak_release_id: null,
    paketler: null,
    olusturan: 'yonetici@deneme.test',
    created_at: '2026-11-03T10:00:00Z',
    yayinlandi_at: '2026-11-03T11:00:00Z',
    xmin: 500,
    ...over,
  };
}

export function releaseDetail(over: Partial<S['ReleaseDetail']> = {}): S['ReleaseDetail'] {
  const { xmin, ...summary } = releaseItem();
  return {
    ...summary,
    notlar: 'Deneme yayın notu',
    data_version: 'deneme-1',
    kapi_raporu: {
      ...RELEASE_GATE_REPORT,
      rejected: false,
      violations: [],
      violations_omitted: [],
    },
    ozetler: {
      kaynaklar: { 'test-deneme': 'ozet-kaynak-1' },
      paketler: { 'deneme-paket': 'ozet-paket-1' },
    },
    manifest: { surum: '2026.11.1', paketler: [{ id: 'deneme-paket' }] },
    xmin,
    ...over,
  };
}

export function releasePage(
  items: S['ReleaseSummary'][],
  nextCursor: string | null = null,
): S['ReleaseListResponse'] {
  return { items, next_cursor: nextCursor };
}

export function accepted(over: Partial<S['ReleaseAccepted']> = {}): S['ReleaseAccepted'] {
  return {
    id: 8,
    surum: '2026.11.2',
    derleme: 'internal',
    durum: 'hazirlaniyor',
    talep: 'yayin',
    ...over,
  };
}
