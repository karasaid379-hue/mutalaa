import { describe, expect, it } from 'vitest';
import {
  groupBySurah,
  isBulkSelectable,
  kindRank,
  readSureAdiPayload,
  surahNoOf,
} from '@/screens/sure-adi/payload';
import { ARABIC_SAMPLE, TANZIL_FARK, aliasItem, aliasPayload } from './fixtures-baglanti-sure';

describe('surahNoOf', () => {
  it.each([
    ['2:Deneme-sure-2', 2],
    ['114:Deneme-sure-114', 114],
    ['7:Deneme:iki-iki', 7],
    ['007:Deneme', 7],
  ])('reads the number of %s (only the part before the first colon)', (key, expected) => {
    expect(surahNoOf(key)).toBe(expected);
  });

  it.each([
    'Deneme-sure-1',
    ':Deneme',
    'x:Deneme',
    '1234:Deneme',
    '1 :Deneme',
    `${String.fromCodePoint(0x0663)}:Deneme`,
    '',
  ])('returns null for %j', (key) => {
    expect(surahNoOf(key)).toBeNull();
  });
});

describe('readSureAdiPayload', () => {
  it('reads the fields of the pipeline payload', () => {
    const payload = readSureAdiPayload(
      aliasPayload({
        id: 1,
        sure: 1,
        alias: 'Deneme-sure-1',
        kind: 'kanonik',
        risky: false,
        anlam: 'Deneme anlamı',
        yazimlar: ['Deneme-sure-1-yazim'],
        tanzilFark: TANZIL_FARK,
        kaynaklar: [
          { kaynak: 'deneme-kaynak', dosya: 'deneme-liste.txt', satir: 12 },
          { kaynak: 'kural', kural: 'sure-i' },
        ],
      }),
    );
    expect(payload).toEqual({
      kind: 'kanonik',
      alias: 'Deneme-sure-1',
      risky: false,
      anlam: 'Deneme anlamı',
      yazimlar: ['Deneme-sure-1-yazim'],
      kaynaklar: [
        {
          kaynak: 'deneme-kaynak',
          dosya: 'deneme-liste.txt',
          satir: 12,
          yol: null,
          alan: null,
          kural: null,
        },
        { kaynak: 'kural', dosya: null, satir: null, yol: null, alan: null, kural: 'sure-i' },
      ],
      tanzilFark: {
        alanlar: ['ayet', 'yer'],
        vikipedi: { ayet: '7', yer: 'deneme-yer-a', inis_sirasi: '5' },
        tanzil: { ayet: '8', yer: 'deneme-yer-b', inis_sirasi: '5' },
      },
    });
  });

  it('returns null for anything that is not an object', () => {
    for (const value of [null, undefined, 'metin', 3, ['kind']]) {
      expect(readSureAdiPayload(value)).toBeNull();
    }
  });

  it('never throws on malformed fields and leaves them empty', () => {
    const payload = readSureAdiPayload({
      kind: 3,
      alias: null,
      risky: 'evet',
      yazimlar: ['a', 2, null, 'b'],
      kaynaklar: 'x',
      tanzil_fark: [],
    });
    expect(payload).toEqual({
      kind: null,
      alias: null,
      risky: null,
      anlam: null,
      yazimlar: ['a', 'b'],
      kaynaklar: [],
      tanzilFark: null,
    });
  });

  it('keeps an Arabic alias exactly as stored (no trim, no normalization)', () => {
    const stored = ` ${ARABIC_SAMPLE}${String.fromCodePoint(0x0640)} `;
    expect(readSureAdiPayload({ alias: stored })?.alias).toBe(stored);
  });
});

describe('isBulkSelectable', () => {
  it('is true only for an explicit risky=false', () => {
    expect(isBulkSelectable(readSureAdiPayload({ risky: false }))).toBe(true);
    expect(isBulkSelectable(readSureAdiPayload({ risky: true }))).toBe(false);
    expect(isBulkSelectable(readSureAdiPayload({}))).toBe(false);
    expect(isBulkSelectable(readSureAdiPayload({ risky: 'false' }))).toBe(false);
    expect(isBulkSelectable(null)).toBe(false);
  });
});

describe('kindRank', () => {
  it('follows the pipeline order and puts unknown kinds last', () => {
    expect(['arapca', 'diger_ad', 'bilinmeyen', 'yazim', 'kanonik', null].map(kindRank)).toEqual([
      3, 2, 4, 1, 0, 4,
    ]);
  });
});

describe('groupBySurah', () => {
  const ids = (groups: ReturnType<typeof groupBySurah>) =>
    groups.map((group) => group.rows.map((row) => row.item.id));

  it('orders the groups by the surah number, numerically', () => {
    const groups = groupBySurah([
      aliasItem({ id: 1, sure: 10, alias: 'Deneme-sure-10' }),
      aliasItem({ id: 2, sure: 2, alias: 'Deneme-sure-2' }),
      aliasItem({ id: 3, sure: 114, alias: 'Deneme-sure-114' }),
      aliasItem({ id: 4, sure: 2, alias: 'Deneme-sure-2-b', kind: 'yazim' }),
    ]);
    expect(groups.map((group) => group.sure)).toEqual([2, 10, 114]);
    expect(ids(groups)).toEqual([[2, 4], [1], [3]]);
  });

  it('orders a group by kind and then by Turkish collation of the name', () => {
    const groups = groupBySurah([
      aliasItem({ id: 1, sure: 5, alias: 'Jeneme', kind: 'diger_ad' }),
      aliasItem({ id: 2, sure: 5, alias: ARABIC_SAMPLE, kind: 'arapca' }),
      aliasItem({ id: 3, sure: 5, alias: 'İdeneme', kind: 'diger_ad' }),
      aliasItem({ id: 4, sure: 5, alias: 'Ideneme', kind: 'diger_ad' }),
      aliasItem({ id: 5, sure: 5, alias: 'Zdeneme', kind: 'yazim' }),
      aliasItem({ id: 6, sure: 5, alias: 'Çdeneme', kind: 'diger_ad' }),
      aliasItem({ id: 7, sure: 5, alias: 'Kanonik-deneme', kind: 'kanonik' }),
    ]);
    // kanonik, yazim, then diger_ad: Turkish order (C, Ç, I, İ, J), then arapca.
    expect(ids(groups)).toEqual([[7, 5, 6, 4, 3, 1, 2]]);
    expect(groups[0]!.rows.map((row) => row.alias)).toEqual([
      'Kanonik-deneme',
      'Zdeneme',
      'Çdeneme',
      'Ideneme',
      'İdeneme',
      'Jeneme',
      ARABIC_SAMPLE,
    ]);
  });

  it('breaks ties by id so the order is stable', () => {
    const groups = groupBySurah([
      aliasItem({ id: 9, sure: 1, alias: 'Ayni-ad', kind: 'diger_ad' }),
      aliasItem({ id: 4, sure: 1, alias: 'Ayni-ad', kind: 'diger_ad' }),
    ]);
    expect(ids(groups)).toEqual([[4, 9]]);
  });

  it('puts keys without a readable surah number into a last group and reads nothing else of the key', () => {
    const groups = groupBySurah([
      aliasItem({ id: 1, sure: 1, alias: 'Deneme-sure-1', anahtar: 'bozuk-anahtar' }),
      aliasItem({ id: 2, sure: 3, alias: 'Deneme-sure-3' }),
    ]);
    expect(groups.map((group) => group.sure)).toEqual([3, null]);
    expect(groups[1]!.rows[0]!.alias).toBe('Deneme-sure-1');
  });

  it('shows the raw key as the name when the payload has none, and never makes such a row selectable', () => {
    const groups = groupBySurah([
      aliasItem({ id: 1, sure: 4, alias: 'x', onerilen: { kind: 'kanonik' } }),
      aliasItem({ id: 2, sure: 4, alias: 'y', onerilen: null }),
    ]);
    const rows = groups[0]!.rows;
    expect(rows.map((row) => row.alias).sort()).toEqual(['4:x', '4:y']);
    expect(rows.every((row) => !row.selectable)).toBe(true);
  });

  it('marks only explicit non-risky rows as selectable', () => {
    const rows = groupBySurah([
      aliasItem({ id: 1, sure: 1, alias: 'a-deneme', risky: false }),
      aliasItem({ id: 2, sure: 1, alias: 'b-deneme', risky: true }),
      aliasItem({ id: 3, sure: 1, alias: 'c-deneme', risky: null }),
    ])[0]!.rows;
    expect(rows.map((row) => [row.item.id, row.selectable])).toEqual([
      [1, true],
      [2, false],
      [3, false],
    ]);
  });

  it('returns no groups for an empty list', () => {
    expect(groupBySurah([])).toEqual([]);
  });
});
