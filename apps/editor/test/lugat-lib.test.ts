import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { problemText, showsServerDetail } from '@/lib/problem-text';
import { reviewListInit } from '@/review/queries';
import { QUEUES, openCount } from '@/review/queues';
import { isLugatEditable, lugatSourceDefinition } from '@/review/rules';
import { hasWaveOrder, isLemmaTab, lemmaFilter } from '@/screens/lemma/config';
import { parseLugatKey, readFrequency, readLugatReference } from '@/screens/lemma/lugat-payload';
import { reviewItem, stats } from './fixtures';
import { lugatItem, lugatSourceDetail, lugatSourceText } from './fixtures-lemma';

describe('lügat queue config', () => {
  it('lists lugat_madde + tanim_tr in descending frequency order whatever the wave order is', () => {
    expect(lemmaFilter('lugat', 'dalga')).toEqual({
      hedef_tablo: 'lugat_madde',
      alan: 'tanim_tr',
      sira: 'siklik',
    });
    expect(lemmaFilter('lugat', 'olusturma')).toEqual(lemmaFilter('lugat', 'dalga'));
    expect(hasWaveOrder('lugat')).toBe(false);
    expect(isLemmaTab('lugat')).toBe(true);
    expect(reviewListInit(lemmaFilter('lugat', 'dalga')).params.query).toEqual({
      hedef_tablo: 'lugat_madde',
      alan: 'tanim_tr',
      durum: 'acik',
      sira: 'siklik',
      limit: 50,
    });
  });

  it('adds no route: the lügat queue belongs to the lemma screen (K-13) and is counted there', () => {
    expect(QUEUES.map((queue) => queue.path)).toEqual([
      '/kuyruk/ocr',
      '/kuyruk/lemma',
      '/kuyruk/baglanti',
      '/kuyruk/sure-adi',
    ]);
    const lemma = QUEUES.find((queue) => queue.id === 'lemma')!;
    expect(
      openCount(
        stats([
          ['lemma_gloss', 'anlam_kisa', 2],
          ['lugat_madde', 'tanim_tr', 5],
          ['unit', 'metin', 9],
        ]),
        lemma,
      ),
    ).toBe(7);
  });
});

describe('readLugatReference', () => {
  it('reads the reference meanings, the frequency and the book count', () => {
    expect(
      readLugatReference({
        anlam_basvuru: [
          { anlam: 'Deneme anlam', sayi: 4 },
          { anlam: 'Deneme öteki' },
          { sayi: 3 },
          5,
        ],
        siklik: 120,
        kitaplar: 3,
      }),
    ).toEqual({
      meanings: [
        { anlam: 'Deneme anlam', sayi: 4 },
        { anlam: 'Deneme öteki', sayi: null },
      ],
      siklik: 120,
      kitaplar: 3,
      known: true,
    });
  });

  it('counts a list of books and ignores values that are not counts', () => {
    expect(readLugatReference({ siklik: -1, kitaplar: ['a', 'b'] })).toMatchObject({
      siklik: null,
      kitaplar: 2,
    });
    expect(readLugatReference({ siklik: 1.5, kitaplar: 'çok' })).toMatchObject({
      siklik: null,
      kitaplar: null,
      known: false,
    });
  });

  it('gives null for no value and an unknown one for a value without fields', () => {
    expect(readLugatReference(null)).toBeNull();
    expect(readLugatReference(undefined)).toBeNull();
    expect(readLugatReference('metin')).toEqual({
      meanings: [],
      siklik: null,
      kitaplar: null,
      known: false,
    });
    expect(readLugatReference({ baska: 1 })?.known).toBe(false);
  });

  it('reads the frequency of a list item', () => {
    expect(readFrequency(lugatItem(301))).toBe(699);
    expect(readFrequency(reviewItem({ onerilen: null }))).toBeNull();
  });
});

describe('isLugatEditable', () => {
  it('is true only for an open lugat_madde + tanim_tr review', () => {
    expect(isLugatEditable(lugatItem(301))).toBe(true);
    expect(isLugatEditable(lugatItem(301, { durum: 'onaylandi' }))).toBe(false);
    expect(isLugatEditable(lugatItem(301, { alan: 'status' }))).toBe(false);
    expect(isLugatEditable(reviewItem())).toBe(false);
  });
});

describe('problem text of the lügat decision', () => {
  const missing = {
    type: 'urn:mutalaa:problem:inceleme-desteklenmiyor',
    title: 'x',
    status: 422,
    kod: 'inceleme-desteklenmiyor',
    detail: 'Lugat maddesi bos tanimla onaylanamaz; duzenlenen.tanim_tr ile tanimi yazin.',
  };

  it('says in Turkish that a madde cannot be approved without a definition, and hides the raw detail', () => {
    expect(problemText(missing, 'decision')).toBe(tr.problem.lugatDefinitionRequired);
    expect(showsServerDetail(missing)).toBe(false);
  });

  it('keeps the generic message and the server detail for other 422 answers and for bulk', () => {
    const other = { ...missing, detail: 'Baska bir sebep.' };
    expect(problemText(other, 'decision')).toBe(tr.problem.codes['inceleme-desteklenmiyor']);
    expect(showsServerDetail(other)).toBe(true);
    expect(problemText(missing, 'bulk')).toBe(tr.problem.contexts.bulk['inceleme-desteklenmiyor']);
  });

  it('labels the target and the field of the review', () => {
    expect(tr.labels.target.lugat_madde).toBe('Lügat maddesi');
    expect(tr.labels.field.tanim_tr).toBe('Tanım');
  });
});

describe('parseLugatKey (K-52 madde 14)', () => {
  it('splits the three-part key and keeps colons in the headword', () => {
    expect(parseLugatKey('lugat-rnk:2:deneme')).toEqual({
      source: 'lugat-rnk',
      anlamNo: 2,
      basliksoz: 'deneme',
    });
    expect(parseLugatKey('lugat-rnk:12:a:b')).toEqual({
      source: 'lugat-rnk',
      anlamNo: 12,
      basliksoz: 'a:b',
    });
  });

  it('reads the legacy two-part key as meaning 1', () => {
    expect(parseLugatKey('risale-kelime-frekans:deneme')).toEqual({
      source: 'risale-kelime-frekans',
      anlamNo: 1,
      basliksoz: 'deneme',
    });
    expect(parseLugatKey('risale-kelime-frekans:a:b:c')?.basliksoz).toBe('a:b:c');
  });

  it('gives null for an unreadable key or a non-canonical meaning number', () => {
    for (const key of [
      '',
      'deneme',
      ':x',
      'a:',
      'a:0:x',
      'a:01:x',
      'a:32768:x',
      'a:2:',
      'a:2:  ',
    ]) {
      expect(parseLugatKey(key), key).toBeNull();
    }
  });
});

describe('lugatSourceDefinition', () => {
  it('is the definition only for a madde that came from a source with a non-blank definition', () => {
    expect(lugatSourceDefinition(lugatSourceDetail(301))).toBe(lugatSourceText(301));
    expect(lugatSourceDefinition(lugatSourceDetail(301, { tanim: null }))).toBeNull();
    const editor = lugatSourceDetail(301);
    expect(
      lugatSourceDefinition({ hedef: { ...editor.hedef, tablo: 'lugat_madde', origin: 'editor' } }),
    ).toBeNull();
    expect(
      lugatSourceDefinition({ hedef: { ...editor.hedef, tablo: 'lugat_madde', tanim_tr: '   ' } }),
    ).toBeNull();
    expect(lugatSourceDefinition({ hedef: null })).toBeNull();
  });
});
