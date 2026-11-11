// Synthetic fixtures of the word meaning queue (A15.4): made-up meanings and ids only, never Quran, meal,
// tafsir, hadith or Risale text. The Arabic strings are letter sequences built from code points; they are
// not Quran text.
import type { components } from '@/api/schema';
import { ok, type FakeApi } from './fake-api';
import { reviewDetail, reviewItem } from './fixtures';

type S = components['schemas'];

/** A synthetic Arabic letter sequence (not Quran text). */
export const LEMMA_ARABIC = String.fromCodePoint(0x0633, 0x0635, 0x0639, 0x0641);

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

/** Answers the detail of both queues by id: below 100 a word meaning draft, from 100 a lemma status review. */
export function lemmaHandlers(fake: FakeApi): void {
  fake.get('/api/v1/reviews/{id}', (call) => {
    const id = Number(call.params.id);
    return ok(id >= 100 ? lemmaDetail(id) : glossDetail(id));
  });
}
