// Synthetic fixtures of the word meaning queue (A15.4): made-up meanings and ids only, never Quran, meal,
// tafsir, hadith or Risale text. The Arabic strings are letter sequences built from code points; they are
// not Quran text.
import type { components } from '@/api/schema';
import { ok, type FakeApi } from './fake-api';
import { reviewDetail, reviewItem } from './fixtures';

type S = components['schemas'];

/** A synthetic Arabic letter sequence (not Quran text). */
export const LEMMA_ARABIC = String.fromCodePoint(0x0633, 0x0635, 0x0639, 0x0641);

/** Synthetic Arabic letter sequences for a root and a KWIC context (not Quran text). */
export const ROOT_ARABIC = String.fromCodePoint(0x0633, 0x0635, 0x0639);
export const KWIC_LEFT = String.fromCodePoint(0x0633, 0x0635, 0x0020);
export const KWIC_WORD = String.fromCodePoint(0x0639, 0x0641, 0x0633);
export const KWIC_RIGHT = String.fromCodePoint(0x0020, 0x0635, 0x0639);

/** A 64 character lowercase hexadecimal digest, as the G-YZ record carries it. */
export const SHA_A = 'a'.repeat(64);
export const SHA_B = 'b'.repeat(64);

export const YZ_KAYDI = {
  prompt_id: 'deneme-istem-v1',
  prompt_sha256: SHA_A,
  input_sha256: SHA_B,
};

/** A word meaning draft (`lemma_gloss` + `anlam_kisa`); the key is the lemma id. */
export function glossItem(id: number, over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return reviewItem({
    id,
    hedef_tablo: 'lemma_gloss',
    hedef_anahtar: String(1000 + id),
    alan: 'anlam_kisa',
    onceki: null,
    onerilen: { anlam_kisa: `Deneme anlam ${id}` },
    xmin: 300 + id,
    ...over,
  });
}

export function glossDetail(
  id: number,
  over: Partial<S['ReviewDetailDto']> = {},
): S['ReviewDetailDto'] {
  return reviewDetail({
    ...glossItem(id),
    hedef: {
      tablo: 'lemma_gloss',
      lemma_id: 1000 + id,
      anlam_kisa: `Deneme anlam ${id}`,
      status: 'aday',
    },
    ...over,
  });
}

/** A lemma status review (`lemma` + `status`). */
export function lemmaItem(id: number, over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return reviewItem({
    id,
    hedef_tablo: 'lemma',
    hedef_anahtar: String(2000 + id),
    alan: 'status',
    onceki: null,
    onerilen: { status: 'onayli' },
    xmin: 400 + id,
    ...over,
  });
}

export function lemmaDetail(
  id: number,
  over: Partial<S['ReviewDetailDto']> = {},
): S['ReviewDetailDto'] {
  return reviewDetail({
    ...lemmaItem(id),
    hedef: {
      tablo: 'lemma',
      lemma_id: 2000 + id,
      lang: 'ar',
      text: LEMMA_ARABIC,
      status: 'aday',
    },
    ...over,
  });
}

/** A list item of a ready-source candidate: the dominant share is `guven` and `onerilen.baskin_pay`. */
export function readyGlossItem(id: number, share: number): S['ReviewItemDto'] {
  return glossItem(id, {
    guven: share,
    onerilen: { anlam_kisa: `Deneme anlam ${id}`, baskin_pay: share },
  });
}

/** A ready-source candidate (K-50 madde 5): the dominant share is `guven`, the distribution is not applied. */
export function readyGlossDetail(
  id: number,
  over: Partial<S['ReviewDetailDto']> = {},
  share = 0.85,
): S['ReviewDetailDto'] {
  return glossDetail(id, {
    guven: share,
    onerilen: {
      anlam_kisa: `Deneme anlam ${id}`,
      dagilim: [
        { anlam: `Deneme anlam ${id}`, sayi: 17 },
        { anlam: 'Deneme öteki anlam', sayi: 3 },
      ],
      baskin_pay: share,
    },
    hedef: {
      tablo: 'lemma_gloss',
      lemma_id: 1000 + id,
      anlam_kisa: `Deneme anlam ${id}`,
      origin: 'kaynak:deneme-kaynak',
      version: '1',
      status: 'aday',
    },
    ...over,
  });
}

/** A synthetic uuid per correction id. */
export const fixUuid = (id: number) => `00000000-0000-4000-8000-${String(id).padStart(12, '0')}`;

/** A root and lemma correction (`quran_word_fix`); the key is the correction's uuid, the field is `alan`. */
export function fixItem(id: number, over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return reviewItem({
    id,
    hedef_tablo: 'quran_word_fix',
    hedef_anahtar: fixUuid(id),
    alan: 'lemma_id',
    onceki: null,
    onerilen: null,
    xmin: 500 + id,
    ...over,
  });
}

export function fixDetail(
  id: number,
  over: Partial<S['ReviewDetailDto']> = {},
): S['ReviewDetailDto'] {
  return reviewDetail({
    ...fixItem(id),
    hedef: {
      tablo: 'quran_word_fix',
      id: fixUuid(id),
      anchor: 'q:1:1:1',
      field: 'lemma_id',
      qac_value: '1001',
      new_value: LEMMA_ARABIC,
      reason: 'Deneme düzeltme gerekçesi',
      editor: 'editor@deneme.test',
      status: 'aday',
    },
    ...over,
  });
}

/** A synthetic lemma card: made-up letters and context (not Quran text), a draft meal. */
export function lemmaInfo(over: Partial<S['LemmaDetailResponse']> = {}): S['LemmaDetailResponse'] {
  return {
    lemma: {
      id: 1001,
      text: LEMMA_ARABIC,
      lang: 'ar',
      status: 'onayli',
      origin: 'qac',
      occurrences: 42,
      root_id: 7,
      qac_ref: 'deneme-ref',
      etymological_only: false,
    },
    kok: {
      id: 7,
      letters: ROOT_ARABIC,
      letters_bw: 'xyz',
      occurrences: 120,
      ayah_count: 80,
      idf_q: 1.2345,
      kok_anlami: 'Deneme kök anlamı',
    },
    tur_dagilimi: [
      { pos: 'N', sayi: 30 },
      { pos: null, sayi: 2 },
    ],
    siklik: { kelime: 42, ayet: 35 },
    dalga: { dalga: 1, sira: 3 },
    ayni_kok_anlamlari: [
      { lemma_id: 1002, text: LEMMA_ARABIC, anlam_kisa: 'Deneme kardeş anlam', occurrences: 9 },
    ],
    kwic: [
      {
        kelime_capa: 'q:1:1:1',
        ayet_capa: 'q:1:1',
        sol: KWIC_LEFT,
        kelime: KWIC_WORD,
        sag: KWIC_RIGHT,
        meal: { capa: 'meal:deneme:1:1', metin: 'Deneme meal metni 1', metin_durumu: 'taslak' },
      },
    ],
    ...over,
  };
}

/** Answers the detail of the queues by id: below 100 a word meaning draft, 100 to 199 a lemma status review, from 200 a correction; and the lemma card. */
export function lemmaHandlers(fake: FakeApi, info: S['LemmaDetailResponse'] = lemmaInfo()): void {
  fake.get('/api/v1/reviews/{id}', (call) => {
    const id = Number(call.params.id);
    return ok(id >= 200 ? fixDetail(id) : id >= 100 ? lemmaDetail(id) : glossDetail(id));
  });
  fake.get('/api/v1/lemmas/{id}', ok(info));
}
