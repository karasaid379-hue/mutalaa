import { describe, expect, it } from 'vitest';
import { trLemma } from '@/i18n/tr-lemma';
import { reviewListInit } from '@/review/queries';
import { QUEUES } from '@/review/queues';
import {
  DEFAULT_LEMMA_ORDER,
  LEMMA_FILTERS,
  LEMMA_TAB_IDS,
  hasWaveOrder,
  isLemmaTab,
  isQueueOrder,
  lemmaFilter,
} from '@/screens/lemma/config';
import {
  CONSISTENT_SHARE_THRESHOLD,
  consistencyOf,
  hasArabicLetters,
  isAnchor,
  isReadyCandidate,
  isShare,
  readConfidence,
  readDistribution,
  readLemmaValue,
  readYzRecord,
} from '@/screens/lemma/payload';
import { formatPercent } from '@/lib/format';
import { glossLength, trimGloss } from '@/lib/text';
import { SHA_A, SHA_B, YZ_KAYDI } from './fixtures-lemma';

describe('readLemmaValue', () => {
  it('is null for null and undefined (no value to show)', () => {
    expect(readLemmaValue(null)).toBeNull();
    expect(readLemmaValue(undefined)).toBeNull();
  });

  it('reads a plain string', () => {
    expect(readLemmaValue('Deneme anlam')).toMatchObject({ plain: 'Deneme anlam', known: true });
  });

  it('reads the draft fields of an object', () => {
    const value = readLemmaValue({
      anlam_kisa: 'Deneme anlam 1; Deneme anlam 2',
      kuran_anlamlari: ['Deneme madde 1', 7, 'Deneme madde 2'],
      turkce_es_kelime: 'Deneme-kelime',
      status: 'onayli',
      emin_degil: true,
      yalnizca_etimolojik_adayi: false,
      dayanak_ayetler: ['q:1:2', 'bozuk'],
      gerekce: 'Deneme gerekçe',
      guven: 0.5,
    });
    expect(value).toEqual({
      plain: null,
      anlamKisa: 'Deneme anlam 1; Deneme anlam 2',
      kuranAnlamlari: ['Deneme madde 1', 'Deneme madde 2'],
      turkceEsKelime: 'Deneme-kelime',
      status: 'onayli',
      eminDegil: true,
      yalnizcaEtimolojikAdayi: false,
      dayanakAyetler: ['q:1:2', 'bozuk'],
      gerekce: 'Deneme gerekçe',
      guven: 0.5,
      known: true,
    });
  });

  it('ignores fields of the wrong type instead of throwing', () => {
    const value = readLemmaValue({
      anlam_kisa: 5,
      kuran_anlamlari: 'tek',
      emin_degil: 'evet',
      guven: '0.9',
      dayanak_ayetler: { a: 1 },
    });
    expect(value).toMatchObject({
      anlamKisa: null,
      kuranAnlamlari: [],
      eminDegil: null,
      guven: null,
      dayanakAyetler: [],
      known: false,
    });
  });

  it('marks an object or an array without a known field as not known (the raw value is shown instead)', () => {
    expect(readLemmaValue({ baska: 1 })).toMatchObject({ known: false, plain: null });
    expect(readLemmaValue([1, 2])).toMatchObject({ known: false });
    expect(readLemmaValue(42)).toMatchObject({ known: false });
  });

  it('keeps the text exactly as stored (no trim, no normalization)', () => {
    const stored = '  Deneme anlam  ';
    expect(readLemmaValue({ anlam_kisa: stored })?.anlamKisa).toBe(stored);
  });
});

describe('readYzRecord', () => {
  it('reads the three keys of the G-YZ record', () => {
    expect(readYzRecord(YZ_KAYDI)).toEqual({
      promptId: 'deneme-istem-v1',
      promptSha256: SHA_A,
      inputSha256: SHA_B,
    });
  });

  it('is null for a value that is not an object', () => {
    expect(readYzRecord(null)).toBeNull();
    expect(readYzRecord('x')).toBeNull();
    expect(readYzRecord([YZ_KAYDI])).toBeNull();
  });

  it('gives null for a missing key', () => {
    expect(readYzRecord({ prompt_id: 'a' })).toEqual({
      promptId: 'a',
      promptSha256: null,
      inputSha256: null,
    });
  });
});

describe('readConfidence', () => {
  it('prefers the API field, then onerilen, then yz_kaydi', () => {
    expect(readConfidence({ guven: 0.9, onerilen: { guven: 0.5 }, yz_kaydi: { guven: 0.1 } })).toBe(
      0.9,
    );
    expect(
      readConfidence({ guven: null, onerilen: { guven: 0.5 }, yz_kaydi: { guven: 0.1 } }),
    ).toBe(0.5);
    expect(readConfidence({ guven: undefined, onerilen: null, yz_kaydi: { guven: 0.1 } })).toBe(
      0.1,
    );
  });

  it('keeps zero (a real value) and is null when nothing carries one', () => {
    expect(readConfidence({ guven: 0 })).toBe(0);
    expect(
      readConfidence({ guven: null, onerilen: { anlam_kisa: 'x' }, yz_kaydi: YZ_KAYDI }),
    ).toBeNull();
    expect(readConfidence({})).toBeNull();
  });

  it('ignores a confidence that is not a finite number', () => {
    expect(readConfidence({ guven: Number.NaN, onerilen: { guven: '0.4' } })).toBeNull();
  });
});

describe('isAnchor', () => {
  it('uses the shared anchor parser', () => {
    expect(isAnchor('q:1:2')).toBe(true);
    expect(isAnchor('q:1:2:3-4')).toBe(true);
    expect(isAnchor('Q:1:2')).toBe(false);
    expect(isAnchor('q:115:1')).toBe(false);
    expect(isAnchor('')).toBe(false);
  });
});

describe('readConfidence (ready-source candidate)', () => {
  it('reads the dominant share of onerilen after the API field', () => {
    expect(readConfidence({ guven: 0.9, onerilen: { baskin_pay: 0.5 } })).toBe(0.9);
    expect(readConfidence({ guven: null, onerilen: { baskin_pay: 0.5, guven: 0.1 } })).toBe(0.5);
  });
});

describe('consistencyOf', () => {
  it('uses the named threshold 0,8: at and above is consistent, below is inconsistent', () => {
    expect(CONSISTENT_SHARE_THRESHOLD).toBe(0.8);
    expect(consistencyOf(0.8)).toBe('tutarli');
    expect(consistencyOf(1)).toBe('tutarli');
    expect(consistencyOf(0.79)).toBe('tutarsiz');
    expect(consistencyOf(0)).toBe('tutarsiz');
  });

  it('is shown as a Turkish percentage that cannot round up over the threshold', () => {
    expect(formatPercent(0.87)).toBe('%87');
    expect(formatPercent(0.795)).toBe('%79,5');
  });
});

describe('readDistribution', () => {
  it('reads the meaning and the count of each entry and drops unreadable ones', () => {
    expect(
      readDistribution({
        dagilim: [{ anlam: 'Deneme anlam 1', sayi: 5 }, { anlam: 3, sayi: 1 }, { anlam: 'x' }, 'x'],
      }),
    ).toEqual([{ anlam: 'Deneme anlam 1', sayi: 5 }]);
  });

  it('is empty when there is no distribution', () => {
    expect(readDistribution(null)).toEqual([]);
    expect(readDistribution({ dagilim: 'x' })).toEqual([]);
    expect(readDistribution({})).toEqual([]);
  });
});

describe('lemmaFilter', () => {
  it('adds the order to the meaning and status tabs and leaves the correction tab without one', () => {
    expect(DEFAULT_LEMMA_ORDER).toBe('dalga');
    expect(lemmaFilter('anlam', 'dalga')).toEqual({
      hedef_tablo: 'lemma_gloss',
      alan: 'anlam_kisa',
      sira: 'dalga',
    });
    expect(lemmaFilter('durum', 'olusturma')).toEqual({
      hedef_tablo: 'lemma',
      alan: 'status',
      sira: 'olusturma',
    });
    expect(lemmaFilter('duzeltme', 'dalga')).toEqual({ hedef_tablo: 'quran_word_fix' });
    expect(hasWaveOrder('duzeltme')).toBe(false);
    expect(lemmaFilter('kok', 'dalga')).toEqual({ hedef_tablo: 'lemma', alan: 'kok_eslemesi' });
    expect(hasWaveOrder('kok')).toBe(false);
    expect(isQueueOrder('dalga')).toBe(true);
    expect(isQueueOrder('baska')).toBe(false);
  });

  it('adds the server approval path filter (onay_yolu) on the Turkish mapping tab only; "hepsi" sends none', () => {
    expect(lemmaFilter('kok', 'dalga', 'hepsi')).toEqual({
      hedef_tablo: 'lemma',
      alan: 'kok_eslemesi',
    });
    for (const path of ['otomatik', 'editor', 'aday'] as const) {
      expect(lemmaFilter('kok', 'dalga', path)).toEqual({
        hedef_tablo: 'lemma',
        alan: 'kok_eslemesi',
        onay_yolu: path,
      });
      expect(reviewListInit(lemmaFilter('kok', 'dalga', path)).params.query).toEqual({
        hedef_tablo: 'lemma',
        alan: 'kok_eslemesi',
        durum: 'acik',
        onay_yolu: path,
        limit: 50,
      });
      // The other tabs never carry it (the API answers 400 for a target other than lemma).
      expect(lemmaFilter('anlam', 'dalga', path)).not.toHaveProperty('onay_yolu');
      expect(lemmaFilter('duzeltme', 'dalga', path)).not.toHaveProperty('onay_yolu');
    }
  });

  it('makes a list request with and without alan and sira', () => {
    expect(reviewListInit(lemmaFilter('anlam', 'dalga')).params.query).toEqual({
      hedef_tablo: 'lemma_gloss',
      alan: 'anlam_kisa',
      durum: 'acik',
      sira: 'dalga',
      limit: 50,
    });
    const fix = reviewListInit(lemmaFilter('duzeltme', 'dalga')).params.query;
    expect(fix).toEqual({ hedef_tablo: 'quran_word_fix', durum: 'acik', limit: 50 });
    expect('alan' in fix).toBe(false);
    expect('sira' in fix).toBe(false);
  });
});

describe('tabs', () => {
  it('match the lemma queue of queues.ts, in the same order', () => {
    const lemma = QUEUES.find((queue) => queue.id === 'lemma');
    expect(lemma?.filters).toEqual(LEMMA_TAB_IDS.map((id) => LEMMA_FILTERS[id]));
  });

  it('knows its four ids only, in this order', () => {
    expect(LEMMA_TAB_IDS).toEqual(['anlam', 'durum', 'duzeltme', 'kok']);
    expect(isLemmaTab('kok')).toBe(true);
    expect(isLemmaTab('anlam')).toBe(true);
    expect(isLemmaTab('durum')).toBe(true);
    expect(isLemmaTab('duzeltme')).toBe(true);
    expect(isLemmaTab('baska')).toBe(false);
    expect(isLemmaTab(null)).toBe(false);
  });

  it('have a label and a hint each', () => {
    for (const id of LEMMA_TAB_IDS) {
      expect(trLemma.tabs[id]).not.toBe('');
      expect(trLemma.tabHints[id]).not.toBe('');
    }
  });
});

describe('formatPercent never rounds up over a threshold', () => {
  it('cuts to one decimal: 0,7996 is %79,9, not %80', () => {
    expect(formatPercent(0.7996)).toBe('%79,9');
    expect(formatPercent(0.8)).toBe('%80');
    expect(formatPercent(0.29)).toBe('%29');
    expect(consistencyOf(0.7996)).toBe('tutarsiz');
  });
});

describe('isShare', () => {
  it('accepts 0 to 1 inclusive only', () => {
    expect(isShare(0)).toBe(true);
    expect(isShare(1)).toBe(true);
    expect(isShare(1.5)).toBe(false);
    expect(isShare(-0.1)).toBe(false);
  });
});

describe('isReadyCandidate', () => {
  it('is true for a kaynak: origin or a dominant share, and false when an AI model is set', () => {
    expect(isReadyCandidate({ yz_modeli: null, hedef: { origin: 'kaynak:deneme' } })).toBe(true);
    expect(isReadyCandidate({ yz_modeli: null, onerilen: { baskin_pay: 0.9 } })).toBe(true);
    expect(isReadyCandidate({ yz_modeli: 'deneme-model', onerilen: { baskin_pay: 0.9 } })).toBe(
      false,
    );
    expect(isReadyCandidate({ yz_modeli: 'deneme-model', hedef: { origin: 'kaynak:x' } })).toBe(
      false,
    );
    expect(isReadyCandidate({ yz_modeli: null, onerilen: { anlam_kisa: 'x' } })).toBe(false);
    expect(isReadyCandidate({ yz_modeli: null, hedef: { origin: 'editor' } })).toBe(false);
  });
});

describe('hasArabicLetters', () => {
  it('finds letters of the four Arabic blocks and nothing else', () => {
    for (const code of [0x0633, 0x0750, 0xfb50, 0xfe70]) {
      expect(hasArabicLetters(`1${String.fromCodePoint(code)}`)).toBe(true);
    }
    expect(hasArabicLetters('1001')).toBe(false);
    expect(hasArabicLetters('pos:N')).toBe(false);
    expect(hasArabicLetters('')).toBe(false);
  });
});

describe('trimGloss and glossLength', () => {
  it('trims only space, tab and line feed', () => {
    const nbsp = String.fromCodePoint(0xa0);
    expect(trimGloss(` \tDeneme\n `)).toBe('Deneme');
    expect(trimGloss(`${nbsp}Deneme`)).toBe(`${nbsp}Deneme`);
  });

  it('measures the trimmed NFC text in code points', () => {
    expect(glossLength(`${'a'.repeat(200)} `)).toBe(200);
    expect(glossLength((String.fromCodePoint(0x65) + String.fromCodePoint(0x301)).repeat(3))).toBe(
      3,
    );
    expect(glossLength(String.fromCodePoint(0x1d7d8).repeat(5))).toBe(5);
    expect(glossLength('')).toBe(0);
  });
});
