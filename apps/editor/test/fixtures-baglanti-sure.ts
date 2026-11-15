// Synthetic fixtures of the link candidates and surah name queues (A15.4): made-up names and text only
// ("Deneme paragrafı 1", "Deneme-sure-1"), never Quran, meal, tafsir, hadith or Risale text. The Arabic
// strings are letter sequences built from code points; they are not Quran text.
import type { components } from '@/api/schema';
import { ok, type FakeApi } from './fake-api';
import { reviewDetail, reviewItem, stats } from './fixtures';

type S = components['schemas'];

/** A synthetic Arabic letter sequence (not Quran text). */
export const ARABIC_SAMPLE = String.fromCodePoint(0x0627, 0x0628, 0x062c, 0x062f);
export const ARABIC_SAMPLE_2 = String.fromCodePoint(0x0647, 0x0648, 0x0632);

// --- link candidates (xref) ---

export function xrefItem(id: number, over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return reviewItem({
    id,
    hedef_tablo: 'xref',
    hedef_anahtar: `00000000-0000-4000-8000-${String(id).padStart(12, '0')}`,
    alan: 'status',
    onceki: null,
    onerilen: null,
    xmin: 500 + id,
    sinif: 'toplu',
    ...over,
  });
}

/** The snapshot a link candidate review carries (A18.4): type, spans, score, evidence summary, highlighted sequence. */
export function linkTarget(
  src: string,
  dst: string,
  over: Partial<S['ReviewTargetSnapshot']> = {},
): S['ReviewTargetSnapshot'] {
  return {
    tablo: 'xref',
    src_anchor: src,
    dst_anchor: dst,
    status: 'aday',
    type: 'iktibas',
    src_span: [12, 16],
    dst_span: [1, 5],
    score: 0.91,
    confidence: 0.97,
    origin: 'hat',
    sinif: 'toplu',
    evidence_ozeti: {
      matched_words: 7,
      ayah_words: 9,
      coverage: 0.4,
      phrase_freq: 1,
      consistent_quote: false,
      position: 'govde',
      subtype: 'deneme-alt-tur',
      group: 'g1',
      alternatives: [{ dst: 'q:1:3', matched_words: 5 }, 'q:1:4'],
    },
    vurgulu_dizi: { sol: 'Deneme önce ', dizi: ARABIC_SAMPLE_2, sag: ' deneme sonra' },
    ...over,
  };
}

export function xrefDetail(
  id: number,
  src = `rn:deneme:p${id}`,
  dst = 'q:1:2',
  over: Partial<S['ReviewDetailDto']> = {},
): S['ReviewDetailDto'] {
  return reviewDetail({
    ...xrefItem(id),
    hedef: linkTarget(src, dst),
    ...over,
  });
}

export function unitText(anchor: string, metin: string): S['UnitDetail'] {
  return {
    anchor,
    kind: 'paragraf',
    role: 'govde',
    source: 'test-deneme',
    ord: 1,
    metin_durumu: 'taslak',
    status: 'aktif',
    rev: 1,
    content_hash: `hash-${anchor}`,
    parent_path: null,
    metin,
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
    kaynak_tur: 'risale',
  };
}

/** The synthetic text a unit of the link screens answers with (paragraph, ayah or meal). */
export function unitFor(anchor: string): S['UnitDetail'] {
  if (anchor.startsWith('q:')) return unitText(anchor, ARABIC_SAMPLE);
  if (anchor.startsWith('meal:')) return unitText(anchor, 'Deneme meal metni 1');
  return unitText(anchor, 'Deneme paragrafı 1');
}

/** Handlers of the link detail and of the three unit texts it shows (paragraph, ayah, meal). */
export function xrefHandlers(fake: FakeApi): void {
  fake.get('/api/v1/reviews/{id}', (call) => ok(xrefDetail(Number(call.params.id))));
  fake.get('/api/v1/units/{anchor}', (call) => ok(unitFor(call.params.anchor!)));
  // The queue reads the counts (class counts, records at the expert); registered after the detail route, which
  // would also match /reviews/stats.
  fake.get(
    '/api/v1/reviews/stats',
    ok(
      stats(
        [['xref', 'status', 3]],
        [
          ['tutarsiz', 1],
          ['toplu', 2],
        ],
        1,
      ),
    ),
  );
}

// --- surah name candidates (surah_alias) ---

export interface AliasSpec {
  id: number;
  sure: number;
  alias: string;
  kind?: string;
  risky?: boolean | null;
  anlam?: string;
  yazimlar?: string[];
  kaynaklar?: Record<string, unknown>[];
  tanzilFark?: Record<string, unknown>;
  /** Replaces the whole `onerilen` (for malformed payloads). */
  onerilen?: unknown;
  /** Replaces `hedef_anahtar` (default `{sure}:{alias}`). */
  anahtar?: string;
}

export function aliasPayload(spec: AliasSpec): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    kind: spec.kind ?? 'kanonik',
    alias: spec.alias,
    kaynaklar: spec.kaynaklar ?? [
      { kaynak: 'deneme-kaynak', dosya: 'deneme-liste.txt', satir: spec.id },
    ],
  };
  if (spec.risky !== null) payload.risky = spec.risky ?? false;
  if (spec.anlam !== undefined) payload.anlam = spec.anlam;
  if (spec.tanzilFark !== undefined) payload.tanzil_fark = spec.tanzilFark;
  payload.yazimlar = spec.yazimlar ?? [];
  return payload;
}

export function aliasItem(spec: AliasSpec): S['ReviewItemDto'] {
  return reviewItem({
    id: spec.id,
    hedef_tablo: 'surah_alias',
    hedef_anahtar: spec.anahtar ?? `${spec.sure}:${spec.alias}`,
    alan: 'status',
    onceki: null,
    onerilen: (spec.onerilen === undefined ? aliasPayload(spec) : spec.onerilen) as never,
    xmin: 900 + spec.id,
  });
}

export function aliasDetail(spec: AliasSpec): S['ReviewDetailDto'] {
  return reviewDetail({
    ...aliasItem(spec),
    hedef: { tablo: 'surah_alias', surah_no: spec.sure, alias: spec.alias, status: 'aday' },
  });
}

export const TANZIL_FARK = {
  alanlar: ['ayet', 'yer'],
  vikipedi: { ayet: 7, yer: 'deneme-yer-a', inis_sirasi: 5 },
  tanzil: { ayet: 8, yer: 'deneme-yer-b', inis_sirasi: 5 },
};
