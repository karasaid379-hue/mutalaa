// A12.5: node:sqlite experiment rig. Every test runs against real FTS5 tables built from the
// DDL files (paketler.json), filled with synthetic rows only: no Quran, hadith, tafsir or Risale
// text. Turkish rows read "Deneme paragrafi N ..."; Arabic-script rows are letter runs built
// from code points and are not words of any text.
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { tryParse } from '@mutalaa/anchors';
import { buildFtsQuery, normalizeTr, searchKeys, stemTr } from '@mutalaa/search';
import type { BuildFtsQueryOptions, FtsQuery, SearchKeys } from '@mutalaa/search';
import { afterAll, describe, expect, it } from 'vitest';
import { buildPack, cleanup, newTempDir, runAfter } from './support/db.js';

afterAll(cleanup);

// ---------------------------------------------------------------------------------------------
// Synthetic data
// ---------------------------------------------------------------------------------------------

/** Synthetic Arabic-script letter run (U+0628 U+062A U+062B U+062C U+062D U+062E). */
const AR_DIZI = String.fromCodePoint(0x628, 0x62a, 0x62b, 0x62c, 0x62d, 0x62e);
/** The same run with U+0648 attached in front (a conjunction-like prefix). */
const AR_ONEKLI = String.fromCodePoint(0x648) + AR_DIZI;
/** A run that shares no 3-character substring with AR_DIZI. */
const AR_BASKA = String.fromCodePoint(0x62f, 0x630, 0x631, 0x632, 0x633, 0x634);

interface SentetikSatir {
  anchor: string;
  kind: string;
  text: string;
}

/** Rows 1-14 (Turkish) have rowid = paragraph number; rows 15-17 are Arabic-script runs. */
const TR_METINLER: readonly string[] = [
  'Deneme paragrafı 1 ışık',
  'Deneme paragrafı 2 ışığın kaynağı',
  'Deneme paragrafı 3 ışıklar',
  'Deneme paragrafı 4 ışıkları',
  'Deneme paragrafı 5 ağaçları',
  'Deneme paragrafı 6 ağaçlar',
  'Deneme paragrafı 7 ağaç',
  'Deneme paragrafı 8 kitaplar',
  'Deneme paragrafı 9 kitap',
  'Deneme paragrafı 10 âlem',
  'Deneme paragrafı 11 alem',
  'Deneme paragrafı 12 sabır',
  'Deneme paragrafı 13 güneşin',
  'Deneme paragrafı 14 çiçekler',
];

/** Synthetic anchors only: rn:test:pN (Risale paragraph) and h:test:N (hadith); never q:. */
function trAnchor(n: number): string {
  return `rn:test:p${String(n)}`;
}

const SATIRLAR: readonly SentetikSatir[] = [
  ...TR_METINLER.map((text, i) => ({ anchor: trAnchor(i + 1), kind: 'risale', text })),
  { anchor: 'h:test:1', kind: 'hadis', text: AR_DIZI },
  { anchor: 'h:test:2', kind: 'hadis', text: AR_ONEKLI },
  { anchor: 'h:test:3', kind: 'hadis', text: AR_BASKA },
];

const ROWID_AR_DIZI = 15;
const ROWID_AR_ONEKLI = 16;
const ROWID_AR_BASKA = 17;

interface YukleSecenekleri {
  /** Index-side stem of a row; default is the device stemmer over the narrow key (K-44 item 1). */
  govde?: (keys: SearchKeys) => string;
}

function varsayilanGovde(keys: SearchKeys): string {
  return stemTr(keys.trNarrow);
}

/** Search columns of a text: tr_wide, tr_stem, ar_norm (null when empty). */
function aramaSutunlari(text: string, govde: (keys: SearchKeys) => string) {
  const keys = searchKeys(text);
  return {
    trWide: keys.trWide,
    trStem: govde(keys),
    arNorm: keys.arNorm === '' ? null : keys.arNorm,
  };
}

/** Writes one unit plus its unit_search row (rowid shared). Content tables: no FTS write here. */
function satirYaz(
  db: DatabaseSync,
  rowid: number,
  satir: SentetikSatir,
  sutunlar: { trWide: string; trStem: string; arNorm: string | null },
): void {
  db.prepare(
    `INSERT INTO unit(rowid, anchor, kind, ord, label, text, content_hash)
     VALUES (?, ?, ?, ?, ?, ?, ?)`,
  ).run(
    rowid,
    satir.anchor,
    satir.kind,
    rowid,
    `Deneme etiketi ${String(rowid)}`,
    satir.text,
    `test-hash-${String(rowid)}`,
  );
  db.prepare('INSERT INTO unit_search(rowid, tr_wide, tr_stem, ar_norm) VALUES (?, ?, ?, ?)').run(
    rowid,
    sutunlar.trWide,
    sutunlar.trStem,
    sutunlar.arNorm,
  );
}

/** Loads rows into unit and unit_search, then applies the type's post-write file. */
function veriYukle(
  db: DatabaseSync,
  tur: string,
  satirlar: readonly SentetikSatir[],
  secenekler: YukleSecenekleri = {},
): void {
  const govde = secenekler.govde ?? varsayilanGovde;
  satirlar.forEach((satir, i) => {
    satirYaz(db, i + 1, satir, aramaSutunlari(satir.text, govde));
  });
  runAfter(db, tur);
}

function yeniPaket(tur: string, ad = 'pack.db'): { db: DatabaseSync; yol: string } {
  const yol = `${newTempDir()}${ad}`;
  return { db: buildPack(tur, yol), yol };
}

function yeniDuzenek(
  satirlar: readonly SentetikSatir[] = SATIRLAR,
  secenekler: YukleSecenekleri = {},
): DatabaseSync {
  const { db } = yeniPaket('core');
  veriYukle(db, 'core', satirlar, secenekler);
  return db;
}

/** Content-less index (risale-dizin): unit_ref + direct FTS writes, then the post-write file. */
function risaleDizinYukle(
  db: DatabaseSync,
  paketKimligi: string,
  satirlar: readonly { anchor: string; text: string }[],
): void {
  satirlar.forEach((satir, i) => {
    const rowid = i + 1;
    const s = aramaSutunlari(satir.text, varsayilanGovde);
    db.prepare(
      'INSERT INTO unit_ref(rowid, anchor, pack_id, ord, label) VALUES (?, ?, ?, ?, ?)',
    ).run(rowid, satir.anchor, paketKimligi, rowid, `Deneme etiketi ${String(rowid)}`);
    db.prepare('INSERT INTO unit_fts(rowid, tr_wide, tr_stem, ar_norm) VALUES (?, ?, ?, ?)').run(
      rowid,
      s.trWide,
      s.trStem,
      s.arNorm,
    );
    if (s.arNorm !== null) {
      db.prepare('INSERT INTO unit_tri(rowid, ar_norm) VALUES (?, ?)').run(rowid, s.arNorm);
    }
  });
  runAfter(db, 'risale-dizin');
}

// ---------------------------------------------------------------------------------------------
// Query helpers
// ---------------------------------------------------------------------------------------------

function tirnak(metin: string): string {
  return `"${metin.replaceAll('"', '""')}"`;
}

/** rowids matched on unit_fts or unit_tri, ascending. */
function rowidler(db: DatabaseSync, tablo: 'unit_fts' | 'unit_tri', ifade: string): number[] {
  const satirlar = db
    .prepare(`SELECT rowid FROM ${tablo} WHERE ${tablo} MATCH ? ORDER BY rowid`)
    .all(ifade) as { rowid: number | bigint }[];
  return satirlar.map((s) => Number(s.rowid));
}

/** Anchors matched through unit (read order), for content tables. */
function capalar(
  db: DatabaseSync,
  ifade: string,
  tablo: 'unit_fts' | 'unit_tri' = 'unit_fts',
): string[] {
  const satirlar = db
    .prepare(
      `SELECT u.anchor AS anchor FROM ${tablo} JOIN unit u ON u.rowid = ${tablo}.rowid
       WHERE ${tablo} MATCH ? ORDER BY u.ord`,
    )
    .all(ifade) as { anchor: string }[];
  return satirlar.map((s) => s.anchor);
}

function matchOf(sorgu: string, secenekler: BuildFtsQueryOptions = { stem: stemTr }): string {
  const sonuc = buildFtsQuery(sorgu, secenekler);
  if (sonuc.match === null) {
    throw new Error(`No MATCH expression for: ${sorgu}`);
  }
  return sonuc.match;
}

/** Wrong on purpose: stems the WIDE word. The index stems the narrow word (K-44 note). */
function yanlisSorguGovdesi(darSozcuk: string): string {
  return stemTr(normalizeTr(darSozcuk, 'genis'));
}

let ortakDuzenek: DatabaseSync | undefined;
function duzenek(): DatabaseSync {
  ortakDuzenek ??= yeniDuzenek();
  return ortakDuzenek;
}

// ---------------------------------------------------------------------------------------------
// 9. SQLite build
// ---------------------------------------------------------------------------------------------

describe('SQLite build of node:sqlite', () => {
  it('is 3.34 or newer (trigram tokenizer) and has ENABLE_FTS5', () => {
    const db = duzenek();
    const surum = (db.prepare('SELECT sqlite_version() AS v').get() as { v: string }).v;
    const parca = /^([0-9]+)\.([0-9]+)\.([0-9]+)/u.exec(surum);
    expect(parca, surum).not.toBeNull();
    const buyuk = Number(parca?.[1]);
    const kucuk = Number(parca?.[2]);
    expect(buyuk > 3 || (buyuk === 3 && kucuk >= 34), surum).toBe(true);

    const secenekler = (
      db.prepare('PRAGMA compile_options').all() as { compile_options: string }[]
    ).map((s) => s.compile_options);
    expect(secenekler).toContain('ENABLE_FTS5');
  });

  it('can create both tokenizers the schema needs', () => {
    const db = duzenek();
    const tablolar = (
      db
        .prepare("SELECT name, sql FROM sqlite_master WHERE name IN ('unit_fts', 'unit_tri')")
        .all() as {
        name: string;
        sql: string;
      }[]
    ).sort((a, b) => (a.name < b.name ? -1 : 1));
    expect(tablolar.map((t) => t.name)).toEqual(['unit_fts', 'unit_tri']);
    expect(tablolar[0]?.sql).toContain("tokenize='unicode61 remove_diacritics 0'");
    expect(tablolar[1]?.sql).toContain("tokenize='trigram'");
  });
});

// ---------------------------------------------------------------------------------------------
// 1. Data loading
// ---------------------------------------------------------------------------------------------

describe('synthetic data loading', () => {
  it('writes unit, unit_search and both FTS tables for every row', () => {
    const db = duzenek();
    const sayi = (sql: string): number =>
      Number((db.prepare(sql).get() as { n: number | bigint }).n);
    expect(sayi('SELECT count(*) AS n FROM unit')).toBe(SATIRLAR.length);
    expect(sayi('SELECT count(*) AS n FROM unit_search')).toBe(SATIRLAR.length);
    expect(sayi('SELECT count(*) AS n FROM unit_fts')).toBe(SATIRLAR.length);
    expect(SATIRLAR.length).toBeGreaterThanOrEqual(15);
    expect(TR_METINLER.length).toBeGreaterThanOrEqual(12);
  });

  it('uses synthetic anchors that parse with the shared grammar and never look like q:', () => {
    for (const satir of SATIRLAR) {
      expect(satir.anchor.startsWith('q:'), satir.anchor).toBe(false);
      expect(tryParse(satir.anchor), satir.anchor).not.toBeNull();
    }
  });

  it('indexes the narrow stem and keeps tr_wide and tr_stem at the same word count', () => {
    const db = duzenek();
    const satirlar = db
      .prepare('SELECT rowid, tr_wide, tr_stem, ar_norm FROM unit_search ORDER BY rowid')
      .all() as { rowid: number; tr_wide: string; tr_stem: string; ar_norm: string | null }[];
    for (const satir of satirlar) {
      const sozcuk = (s: string): number => (s === '' ? 0 : s.split(' ').length);
      expect(sozcuk(satir.tr_stem), String(satir.rowid)).toBe(sozcuk(satir.tr_wide));
    }
    // stemTr over the already narrow key equals stemTr over the raw text.
    for (const satir of SATIRLAR) {
      expect(stemTr(searchKeys(satir.text).trNarrow), satir.anchor).toBe(stemTr(satir.text));
    }
    // The wide stem of "agaclari" is not the narrow stem: the index must use the narrow key.
    const bes = satirlar[4];
    expect(bes?.tr_wide).toBe('deneme paragrafi 5 agaclari');
    expect(bes?.tr_stem).toBe('dene paragraf 5 agac');
  });

  it('stores Arabic-script rows in ar_norm and leaves the Turkish columns empty', () => {
    const db = duzenek();
    expect(searchKeys(AR_DIZI).arNorm).toBe(AR_DIZI);
    expect(searchKeys(AR_ONEKLI).arNorm).toBe(AR_ONEKLI);
    const satir = db
      .prepare('SELECT tr_wide, tr_stem, ar_norm FROM unit_search WHERE rowid = ?')
      .get(ROWID_AR_ONEKLI) as { tr_wide: string; tr_stem: string; ar_norm: string };
    expect(satir.ar_norm).toBe(AR_ONEKLI);
    expect(satir.tr_wide).toBe('');
    expect(satir.tr_stem).toBe('');
  });

  it('applied the post-write file: rank option is stored', () => {
    const db = duzenek();
    const rank = db.prepare("SELECT v FROM unit_fts_config WHERE k = 'rank'").get() as {
      v: string;
    };
    expect(rank.v).toBe('bm25(1.0, 0.4, 1.0)');
  });
});

// ---------------------------------------------------------------------------------------------
// 2. Shared fq- vectors run on FTS5 without error
// ---------------------------------------------------------------------------------------------

interface VektorGirdisi {
  query: string;
  stems?: Record<string, string>;
  sures?: Record<string, number>;
  implicitPrefix?: boolean;
  exact?: boolean;
}

interface VektorSatiri {
  id: string;
  input: VektorGirdisi;
  expected: FtsQuery;
}

function vektorleriOku(): VektorSatiri[] {
  const require = createRequire(import.meta.url);
  const kok = dirname(require.resolve('@mutalaa/test-vectors/package.json'));
  const icerik = readFileSync(join(kok, 'fts-query', 'query.jsonl'), 'utf8');
  const satirlar = icerik.split('\n');
  if (satirlar.at(-1) === '') {
    satirlar.pop();
  }
  return satirlar.map((s) => JSON.parse(s) as VektorSatiri);
}

/** Options from the fixed lookups of a vector; Map avoids prototype keys such as "constructor". */
function vektorSecenekleri(girdi: VektorGirdisi): BuildFtsQueryOptions {
  const govdeler = new Map(Object.entries(girdi.stems ?? {}));
  const sureler = new Map(Object.entries(girdi.sures ?? {}));
  const secenekler: BuildFtsQueryOptions = {
    stem: (dar) => govdeler.get(dar),
    resolveSure: (anahtar) => sureler.get(anahtar),
  };
  if (girdi.implicitPrefix !== undefined) secenekler.implicitPrefix = girdi.implicitPrefix;
  if (girdi.exact !== undefined) secenekler.exact = girdi.exact;
  return secenekler;
}

describe('fts-query vectors on real FTS5 tables', () => {
  const satirlar = vektorleriOku();

  it('reads the vector file (fq- and, once added, fq-ar- rows)', () => {
    expect(satirlar.length).toBeGreaterThanOrEqual(40);
    for (const satir of satirlar) {
      expect(satir.id).toMatch(/^fq-(?:ar-)?[0-9]{4}$/u);
    }
  });

  for (const satir of satirlar) {
    it(`${satir.id}: match and tri expressions run without an FTS5 error`, () => {
      const db = duzenek();
      const sorgu = buildFtsQuery(satir.input.query, vektorSecenekleri(satir.input));
      expect(sorgu.match).toBe(satir.expected.match);
      expect(sorgu.tri).toBe(satir.expected.tri);
      if (sorgu.match !== null) {
        const ifade = sorgu.match;
        expect(() => rowidler(db, 'unit_fts', ifade)).not.toThrow();
      }
      if (sorgu.tri !== null) {
        const ifade = sorgu.tri;
        expect(() => rowidler(db, 'unit_tri', ifade)).not.toThrow();
      }
    });
  }

  it('executes at least 40 match expressions (the loop is not vacuous)', () => {
    const calisan = satirlar.filter((s) => s.expected.match !== null);
    expect(calisan.length).toBeGreaterThanOrEqual(40);
  });
});

// ---------------------------------------------------------------------------------------------
// 3. Queries from buildFtsQuery find the expected anchors; narrow / wide consistency
// ---------------------------------------------------------------------------------------------

describe('buildFtsQuery against the loaded index', () => {
  const ISIK_CAPALARI = [1, 2, 3, 4].map(trAnchor);
  const AGAC_CAPALARI = [5, 6, 7].map(trAnchor);

  it('ışık finds the wide row and the inflected rows through the stem branch', () => {
    const db = duzenek();
    const ifade = matchOf('ışık');
    expect(ifade).toBe('tr_wide : "isik" OR tr_stem : "isik"');
    expect(capalar(db, ifade)).toEqual(ISIK_CAPALARI);
    // The wide column alone only finds the exact word.
    expect(capalar(db, 'tr_wide : "isik"')).toEqual([trAnchor(1)]);
    // The stem column alone finds all four (ışığın, ışıklar and ışıkları stem to isik).
    expect(capalar(db, 'tr_stem : "isik"')).toEqual(ISIK_CAPALARI);
  });

  it('an inflected query form finds the base word and its other forms', () => {
    const db = duzenek();
    // ışığın is in the corpus; ışıkları too. The query form "ışıkları" stems to isik.
    expect(buildFtsQuery('ışıkları', { stem: stemTr }).match).toBe(
      'tr_wide : "isiklari" OR tr_stem : "isik"',
    );
    expect(capalar(db, matchOf('ışıkları'))).toEqual(ISIK_CAPALARI);
  });

  it('ağaçları finds ağaçları, ağaçlar and ağaç (dar word stemmed on the query side)', () => {
    const db = duzenek();
    const ifade = matchOf('ağaçları');
    expect(ifade).toBe('tr_wide : "agaclari" OR tr_stem : "agac"');
    expect(capalar(db, ifade)).toEqual(AGAC_CAPALARI);
    expect(capalar(db, matchOf('ağaç'))).toEqual(AGAC_CAPALARI);
    expect(capalar(db, matchOf('agaclar'))).toEqual(AGAC_CAPALARI);
  });

  it('regression lock: a query-side stem of the WIDE word misses the stem column', () => {
    const db = duzenek();
    // Wide "agaclari" stays "agaclari" (the vowel-harmony check fails for the dotless i written
    // as i), so tr_stem "agaclari" matches nothing, while the narrow word stems to "agac".
    expect(yanlisSorguGovdesi('ağaçları')).toBe('agaclari');
    expect(stemTr('ağaçları')).toBe('agac');

    const dogru = capalar(db, matchOf('ağaçları'));
    const yanlis = capalar(db, matchOf('ağaçları', { stem: yanlisSorguGovdesi }));
    expect(dogru).toEqual(AGAC_CAPALARI);
    expect(yanlis).toEqual([trAnchor(5)]);
    expect(yanlis).not.toContain(trAnchor(6));
    expect(yanlis).not.toContain(trAnchor(7));

    // Same for ışıkları: the wide stem "isiklar" does not reach the base word "ışık".
    const yanlisIsik = capalar(db, matchOf('ışıkları', { stem: yanlisSorguGovdesi }));
    expect(yanlisIsik).not.toContain(trAnchor(1));
    expect(yanlisIsik.length).toBeLessThan(ISIK_CAPALARI.length);
  });

  it('regression lock: an index built from the WIDE key stems differently and loses rows', () => {
    const yanlisIndeks = yeniDuzenek(SATIRLAR, { govde: (keys) => stemTr(keys.trWide) });
    const dogruIndeks = duzenek();
    const ifade = matchOf('ağaç');
    expect(capalar(dogruIndeks, ifade)).toEqual(AGAC_CAPALARI);
    // Row 5 holds "ağaçları": its wide-key stem is "agaclari", so the query stem "agac" misses it.
    const bulunan = capalar(yanlisIndeks, ifade);
    expect(bulunan).not.toContain(trAnchor(5));
    expect(bulunan).toEqual([trAnchor(6), trAnchor(7)]);
  });

  it('âlem: the narrow filter keeps âlem and drops alem', () => {
    const db = duzenek();
    const sorgu = buildFtsQuery('âlem', { stem: stemTr });
    expect(sorgu.narrow).toEqual(['âlem']);
    const ifade = sorgu.match;
    expect(ifade).toBe('tr_wide : "alem" OR tr_stem : "ale"');
    if (ifade === null) {
      return;
    }
    const metinler = db
      .prepare(
        `SELECT u.anchor AS anchor, u.text AS text FROM unit_fts JOIN unit u ON u.rowid = unit_fts.rowid
         WHERE unit_fts MATCH ? ORDER BY u.ord`,
      )
      .all(ifade) as { anchor: string; text: string }[];
    // Before the filter both spellings are present (the wide key folds â to a).
    expect(metinler.map((m) => m.anchor)).toEqual([trAnchor(10), trAnchor(11)]);

    // The narrow key of the stored text decides (tr_narrow is not a column of the pack).
    const suzulmus = metinler.filter((m) => {
      const kelimeler = normalizeTr(m.text, 'dar').split(' ');
      return sorgu.narrow.every((dar) => kelimeler.includes(dar));
    });
    expect(suzulmus.map((m) => m.anchor)).toEqual([trAnchor(10)]);
  });

  it('alem (no circumflex) has no narrow filter and finds both spellings', () => {
    const db = duzenek();
    const sorgu = buildFtsQuery('alem', { stem: stemTr });
    expect(sorgu.narrow).toEqual([]);
    expect(capalar(db, matchOf('alem'))).toEqual([trAnchor(10), trAnchor(11)]);
  });

  it('implicit prefix on the last term searches while typing', () => {
    const db = duzenek();
    const sorgu = buildFtsQuery('isi', { stem: stemTr, implicitPrefix: true });
    expect(sorgu.match).toBe('tr_wide : "isi"*');
    expect(capalar(db, sorgu.match ?? '')).toEqual(ISIK_CAPALARI);
  });

  it('two terms are joined with AND', () => {
    const db = duzenek();
    const ifade = matchOf('ağaçlar deneme');
    expect(ifade).toContain(' AND ');
    expect(capalar(db, ifade)).toEqual(AGAC_CAPALARI);
  });

  it('a quoted phrase is a phrase query on tr_wide', () => {
    const db = duzenek();
    const ifade = matchOf('"paragrafı 9 kitap"');
    expect(ifade).toBe('tr_wide : "paragrafi 9 kitap"');
    expect(capalar(db, ifade)).toEqual([trAnchor(9)]);
  });
});

// ---------------------------------------------------------------------------------------------
// 4. Ranking
// ---------------------------------------------------------------------------------------------

describe('ranking', () => {
  /** Row 1 holds the term in tr_wide, row 2 only in tr_stem; equal token counts; filler rows. */
  function siralamaDuzenegi(): DatabaseSync {
    const { db } = yeniPaket('core');
    const sentetik = (n: number): SentetikSatir => ({
      anchor: trAnchor(n),
      kind: 'risale',
      text: `Deneme paragrafı ${String(n)}`,
    });
    satirYaz(db, 1, sentetik(1), { trWide: 'zeytin', trStem: 'aaa', arNorm: null });
    satirYaz(db, 2, sentetik(2), { trWide: 'bbb', trStem: 'zeytin', arNorm: null });
    for (let n = 3; n <= 12; n += 1) {
      satirYaz(db, n, sentetik(n), {
        trWide: `dolgu${String(n)}`,
        trStem: `dolgu${String(n)}`,
        arNorm: null,
      });
    }
    runAfter(db, 'core');
    return db;
  }

  const IFADE = 'tr_wide : "zeytin" OR tr_stem : "zeytin"';

  it('ORDER BY rank puts the tr_wide hit before the tr_stem-only hit', () => {
    const db = siralamaDuzenegi();
    const satirlar = db
      .prepare('SELECT rowid, rank FROM unit_fts WHERE unit_fts MATCH ? ORDER BY rank')
      .all(IFADE) as { rowid: number | bigint; rank: number }[];
    expect(satirlar.map((s) => Number(s.rowid))).toEqual([1, 2]);
    expect(satirlar[0]?.rank).toBeLessThan(satirlar[1]?.rank ?? Number.NEGATIVE_INFINITY);
  });

  it('equal weights tie the two rows, so the order comes from the 0.4 weight alone', () => {
    const db = siralamaDuzenegi();
    const satirlar = db
      .prepare(
        'SELECT rowid, bm25(unit_fts, 1.0, 1.0, 1.0) AS s FROM unit_fts WHERE unit_fts MATCH ? ORDER BY rowid',
      )
      .all(IFADE) as { rowid: number | bigint; s: number }[];
    expect(satirlar).toHaveLength(2);
    expect(satirlar[0]?.s).toBeCloseTo(satirlar[1]?.s ?? Number.NaN, 12);
  });

  it('bm25(unit_fts, 1.0, 0.4, 1.0) gives the same values and order as the rank option', () => {
    const db = siralamaDuzenegi();
    const rankSatirlari = db
      .prepare('SELECT rowid, rank FROM unit_fts WHERE unit_fts MATCH ? ORDER BY rank')
      .all(IFADE) as { rowid: number | bigint; rank: number }[];
    const acikSatirlar = db
      .prepare(
        'SELECT rowid, bm25(unit_fts, 1.0, 0.4, 1.0) AS s FROM unit_fts WHERE unit_fts MATCH ? ORDER BY s',
      )
      .all(IFADE) as { rowid: number | bigint; s: number }[];
    expect(acikSatirlar.map((s) => Number(s.rowid))).toEqual(
      rankSatirlari.map((s) => Number(s.rowid)),
    );
    rankSatirlari.forEach((satir, i) => {
      expect(acikSatirlar[i]?.s).toBeCloseTo(satir.rank, 12);
    });
  });

  it('on the loaded index the exact word outranks the inflected rows for ışık', () => {
    const db = duzenek();
    const satirlar = db
      .prepare(
        `SELECT u.anchor AS anchor FROM unit_fts JOIN unit u ON u.rowid = unit_fts.rowid
         WHERE unit_fts MATCH ? ORDER BY rank`,
      )
      .all(matchOf('ışık')) as { anchor: string }[];
    expect(satirlar).toHaveLength(4);
    expect(satirlar[0]?.anchor).toBe(trAnchor(1));
  });
});

// ---------------------------------------------------------------------------------------------
// 5. Prefix queries (judged by the result only, never by the query plan)
// ---------------------------------------------------------------------------------------------

describe('prefix queries', () => {
  const ISIK_AILESI = [1, 2, 3, 4];

  it('2, 3 and 4 character prefixes return the expected rows', () => {
    const db = duzenek();
    // Wide tokens: isik, isigin, isiklar, isiklari.
    expect(rowidler(db, 'unit_fts', 'tr_wide : "is"*')).toEqual(ISIK_AILESI);
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isi"*')).toEqual(ISIK_AILESI);
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isik"*')).toEqual([1, 3, 4]);
  });

  it('longer prefixes (no prefix index) still return the right rows', () => {
    const db = duzenek();
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isikl"*')).toEqual([3, 4]);
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isikla"*')).toEqual([3, 4]);
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isiklar"*')).toEqual([3, 4]);
    expect(rowidler(db, 'unit_fts', 'tr_wide : "isiklari"*')).toEqual([4]);
  });

  it('a prefix with no match returns nothing', () => {
    expect(rowidler(duzenek(), 'unit_fts', 'tr_wide : "zq"*')).toEqual([]);
  });

  it('the prefix is a whole-token start: a middle part does not match', () => {
    expect(rowidler(duzenek(), 'unit_fts', 'tr_wide : "sik"*')).toEqual([]);
  });
});

// ---------------------------------------------------------------------------------------------
// 6. Trigram
// ---------------------------------------------------------------------------------------------

describe('unit_tri', () => {
  it('finds a 3+ character substring from the middle of an Arabic-script run', () => {
    const db = duzenek();
    const orta = AR_DIZI.slice(1, 4);
    expect(rowidler(db, 'unit_tri', tirnak(orta))).toEqual([ROWID_AR_DIZI, ROWID_AR_ONEKLI]);
    expect(rowidler(db, 'unit_tri', tirnak(AR_DIZI.slice(2, 6)))).toEqual([
      ROWID_AR_DIZI,
      ROWID_AR_ONEKLI,
    ]);
  });

  it('finds the U+0648-prefixed form with the bare run as the query', () => {
    const db = duzenek();
    expect(rowidler(db, 'unit_tri', tirnak(AR_DIZI))).toEqual([ROWID_AR_DIZI, ROWID_AR_ONEKLI]);
    // The word index is stricter: the prefixed token is a different word.
    expect(rowidler(db, 'unit_fts', `ar_norm : ${tirnak(AR_DIZI)}`)).toEqual([ROWID_AR_DIZI]);
    expect(rowidler(db, 'unit_fts', `ar_norm : ${tirnak(AR_ONEKLI)}`)).toEqual([ROWID_AR_ONEKLI]);
  });

  it('finds only the prefixed form when the query contains the prefix letter', () => {
    const db = duzenek();
    const onekliAlt = AR_ONEKLI.slice(0, 3);
    expect(rowidler(db, 'unit_tri', tirnak(onekliAlt))).toEqual([ROWID_AR_ONEKLI]);
  });

  it('a 2 character substring returns no row (and no error)', () => {
    const db = duzenek();
    const iki = AR_DIZI.slice(1, 3);
    expect([...iki]).toHaveLength(2);
    expect(rowidler(db, 'unit_tri', tirnak(iki))).toEqual([]);
    expect(rowidler(db, 'unit_tri', tirnak(AR_DIZI.slice(0, 1)))).toEqual([]);
  });

  it('does not match a run that shares no 3-character substring', () => {
    const db = duzenek();
    expect(rowidler(db, 'unit_tri', tirnak(AR_BASKA.slice(0, 3)))).toEqual([ROWID_AR_BASKA]);
    expect(capalar(db, tirnak(AR_DIZI.slice(0, 3)), 'unit_tri')).toEqual(['h:test:1', 'h:test:2']);
  });

  it('is filled from unit_search on rebuild: Turkish-only rows have no trigram', () => {
    const db = duzenek();
    expect(rowidler(db, 'unit_tri', tirnak('ışı'))).toEqual([]);
  });
});

// ---------------------------------------------------------------------------------------------
// 7. Content-less index (risale-dizin)
// ---------------------------------------------------------------------------------------------

describe('content-less risale-dizin', () => {
  function dizinDuzenegi(): DatabaseSync {
    const { db } = yeniPaket('risale-dizin');
    risaleDizinYukle(db, 'risale-test', SATIRLAR);
    return db;
  }

  it('answers MATCH joined to unit_ref by rowid', () => {
    const db = dizinDuzenegi();
    const satirlar = db
      .prepare(
        `SELECT r.anchor AS anchor, r.pack_id AS pack_id FROM unit_fts f JOIN unit_ref r ON r.rowid = f.rowid
         WHERE unit_fts MATCH ? ORDER BY r.ord`,
      )
      .all(matchOf('ağaçları')) as { anchor: string; pack_id: string }[];
    expect(satirlar.map((s) => s.anchor)).toEqual([5, 6, 7].map(trAnchor));
    expect(new Set(satirlar.map((s) => s.pack_id))).toEqual(new Set(['risale-test']));
  });

  it('answers the unqualified table-name form used by the search statement', () => {
    const db = dizinDuzenegi();
    const satirlar = db
      .prepare(
        `SELECT r.anchor AS anchor FROM unit_fts JOIN unit_ref r ON r.rowid = unit_fts.rowid
         WHERE unit_fts MATCH ? ORDER BY bm25(unit_fts, 1.0, 0.4, 1.0)`,
      )
      .all(matchOf('ışık')) as { anchor: string }[];
    expect(satirlar).toHaveLength(4);
    expect(satirlar[0]?.anchor).toBe(trAnchor(1));
  });

  it('keeps the rank option from the content-less post-write file', () => {
    const db = dizinDuzenegi();
    const rank = db.prepare("SELECT v FROM unit_fts_config WHERE k = 'rank'").get() as {
      v: string;
    };
    expect(rank.v).toBe('bm25(1.0, 0.4, 1.0)');
    const satirlar = db
      .prepare('SELECT rowid FROM unit_fts WHERE unit_fts MATCH ? ORDER BY rank')
      .all(matchOf('ışık')) as { rowid: number | bigint }[];
    expect(Number(satirlar[0]?.rowid)).toBe(1);
  });

  it('finds Arabic-script substrings through the content-less trigram table', () => {
    const db = dizinDuzenegi();
    expect(rowidler(db, 'unit_tri', tirnak(AR_DIZI.slice(1, 4)))).toEqual([
      ROWID_AR_DIZI,
      ROWID_AR_ONEKLI,
    ]);
    expect(rowidler(db, 'unit_tri', tirnak(AR_DIZI.slice(1, 3)))).toEqual([]);
  });

  it('refuses rebuild on the content-less tables', () => {
    const db = dizinDuzenegi();
    expect(() => {
      db.exec("INSERT INTO unit_fts(unit_fts) VALUES('rebuild')");
    }).toThrow(/contentless/);
  });
});

// ---------------------------------------------------------------------------------------------
// 8. ATTACH
// ---------------------------------------------------------------------------------------------

describe('ATTACH across packs', () => {
  interface PaketSatiri {
    anchor: string;
    kind: string;
    text: string;
  }
  const CORE_SATIRLARI: PaketSatiri[] = [
    { anchor: 'h:test:11', kind: 'hadis', text: 'Deneme paragrafı 1 ışık' },
    { anchor: 'h:test:12', kind: 'hadis', text: 'Deneme paragrafı 2 kitap' },
  ];
  const TEFSIR_SATIRLARI: PaketSatiri[] = [
    { anchor: 'tf:test:mukaddime:p1', kind: 'tefsir', text: 'Deneme paragrafı 3 ışığın' },
    { anchor: 'tf:test:mukaddime:p2', kind: 'tefsir', text: 'Deneme paragrafı 4 ağaçlar' },
  ];
  const RISALE_SATIRLARI = [
    { anchor: 'rn:test:p1', text: 'Deneme paragrafı 5 ışıklar' },
    { anchor: 'rn:test:p2', text: 'Deneme paragrafı 6 sabır' },
  ];

  interface Baglanti {
    core: DatabaseSync;
    tefsirYolu: string;
    risaleYolu: string;
  }

  /** core (main), tefsir-test (metin) and risale-dizin in three separate files, attached. */
  function baglantiKur(): Baglanti {
    const { db: core } = yeniPaket('core', 'core.db');
    veriYukle(core, 'core', CORE_SATIRLARI);

    const tefsir = yeniPaket('metin', 'tefsir-test.db');
    veriYukle(tefsir.db, 'metin', TEFSIR_SATIRLARI);
    tefsir.db.close();

    const risale = yeniPaket('risale-dizin', 'risale-dizin.db');
    risaleDizinYukle(risale.db, 'risale-test', RISALE_SATIRLARI);
    risale.db.close();

    core.prepare('ATTACH DATABASE ? AS p_tefsir_test').run(tefsir.yol);
    core.prepare('ATTACH DATABASE ? AS p_risale_dizin').run(risale.yol);
    return { core, tefsirYolu: tefsir.yol, risaleYolu: risale.yol };
  }

  let ortakBaglanti: Baglanti | undefined;
  function baglanti(): Baglanti {
    ortakBaglanti ??= baglantiKur();
    return ortakBaglanti;
  }

  const ISIK = matchOf('ışık');

  it('qualifies the table name in FROM and keeps MATCH on the bare table name', () => {
    const { core } = baglanti();
    const satirlar = core
      .prepare(
        `SELECT u.anchor AS anchor, bm25(unit_fts, 1.0, 0.4, 1.0) AS s
         FROM p_tefsir_test.unit_fts JOIN p_tefsir_test.unit u ON u.rowid = unit_fts.rowid
         WHERE unit_fts MATCH ?1 ORDER BY bm25(unit_fts, 1.0, 0.4, 1.0) LIMIT 20`,
      )
      .all(ISIK) as { anchor: string; s: number }[];
    expect(satirlar.map((s) => s.anchor)).toEqual(['tf:test:mukaddime:p1']);
    expect(satirlar[0]?.s).toBeLessThan(0);
  });

  /** The statement of Arama 5 with the test pack names; `adli` also names column 6 `s`. */
  function birlesikSql(adli: boolean): string {
    const ad = adli ? ' AS s' : '';
    const sira = adli ? 's' : '6';
    return `
SELECT * FROM (SELECT 'core' AS pack, u.anchor, u.kind, u.ord, u.label, bm25(unit_fts, 1.0, 0.4, 1.0) AS s
               FROM main.unit_fts JOIN main.unit u ON u.rowid = unit_fts.rowid
               WHERE unit_fts MATCH ?1 ORDER BY s LIMIT 20)
UNION ALL
SELECT * FROM (SELECT 'tefsir-test', u.anchor, u.kind, u.ord, u.label, bm25(unit_fts, 1.0, 0.4, 1.0)${ad}
               FROM p_tefsir_test.unit_fts JOIN p_tefsir_test.unit u ON u.rowid = unit_fts.rowid
               WHERE unit_fts MATCH ?1 ORDER BY ${sira} LIMIT 20)
UNION ALL
SELECT * FROM (SELECT r.pack_id, r.anchor, 'risale', r.ord, r.label, bm25(unit_fts, 1.0, 0.4, 1.0)${ad}
               FROM p_risale_dizin.unit_fts JOIN p_risale_dizin.unit_ref r ON r.rowid = unit_fts.rowid
               WHERE unit_fts MATCH ?1 ORDER BY ${sira} LIMIT 20)`;
  }

  interface BirlesikSatir {
    pack: string;
    anchor: string;
    kind: string;
    ord: number;
    label: string;
    s: number;
  }

  it('returns results from core, tefsir-test and risale-dizin in one UNION ALL (ORDER BY 6)', () => {
    const { core } = baglanti();
    const satirlar = core.prepare(birlesikSql(false)).all(ISIK) as unknown as BirlesikSatir[];
    expect(satirlar.map((s) => [s.pack, s.anchor, s.kind])).toEqual([
      ['core', 'h:test:11', 'hadis'],
      ['tefsir-test', 'tf:test:mukaddime:p1', 'tefsir'],
      ['risale-test', 'rn:test:p1', 'risale'],
    ]);
    for (const satir of satirlar) {
      expect(satir.s, satir.pack).toBeLessThan(0);
      expect(satir.label).toMatch(/^Deneme etiketi [0-9]+$/u);
    }
  });

  it('accepts ORDER BY s in every branch with the same result', () => {
    const { core } = baglanti();
    const sayili = core.prepare(birlesikSql(false)).all(ISIK) as unknown as BirlesikSatir[];
    const adli = core.prepare(birlesikSql(true)).all(ISIK) as unknown as BirlesikSatir[];
    expect(adli.map((s) => [s.pack, s.anchor])).toEqual(sayili.map((s) => [s.pack, s.anchor]));
  });

  it('keeps a branch empty when its pack has no hit', () => {
    const { core } = baglanti();
    const satirlar = core
      .prepare(birlesikSql(false))
      .all(matchOf('ağaçlar')) as unknown as BirlesikSatir[];
    expect(satirlar.map((s) => s.pack)).toEqual(['tefsir-test']);
  });

  it('measured syntax: MATCH on a schema-qualified table name fails with "no such column"', () => {
    // A28.0 / AR-6: write the FTS table of an attached pack in FROM as p_x.unit_fts, and in WHERE
    // as the bare name unit_fts. `WHERE p_x.unit_fts MATCH` does not resolve on this SQLite.
    const { core } = baglanti();
    expect(() =>
      core
        .prepare(
          `SELECT u.anchor FROM p_tefsir_test.unit_fts JOIN p_tefsir_test.unit u ON u.rowid = unit_fts.rowid
           WHERE p_tefsir_test.unit_fts MATCH ?1`,
        )
        .all(ISIK),
    ).toThrow(/no such column: p_tefsir_test\.unit_fts/);
  });

  it('measured syntax: an alias is not a MATCH target and not a bm25() argument', () => {
    const { core } = baglanti();
    expect(() =>
      core
        .prepare(
          `SELECT u.anchor, bm25(f) FROM p_tefsir_test.unit_fts AS f
           JOIN p_tefsir_test.unit u ON u.rowid = f.rowid WHERE f.unit_fts MATCH ?1`,
        )
        .all(ISIK),
    ).toThrow(/no such column: f/);
    expect(() =>
      core
        .prepare(
          `SELECT u.anchor FROM p_tefsir_test.unit_fts AS f
           JOIN p_tefsir_test.unit u ON u.rowid = f.rowid WHERE f MATCH ?1`,
        )
        .all(ISIK),
    ).toThrow(/no such column: f/);
  });

  it('measured syntax: the documented form is the unaliased table name (aliasing needs alias.unit_fts)', () => {
    // With an alias, only the hidden column spelled alias.unit_fts resolves; the documentation
    // writes the unaliased form, which this test keeps working.
    const { core } = baglanti();
    const takmaAdli = core
      .prepare(
        `SELECT u.anchor AS anchor FROM p_tefsir_test.unit_fts AS f
         JOIN p_tefsir_test.unit u ON u.rowid = f.rowid WHERE f.unit_fts MATCH ?1`,
      )
      .all(ISIK) as { anchor: string }[];
    const takmaAdsiz = core
      .prepare(
        `SELECT u.anchor AS anchor FROM p_tefsir_test.unit_fts
         JOIN p_tefsir_test.unit u ON u.rowid = unit_fts.rowid WHERE unit_fts MATCH ?1`,
      )
      .all(ISIK) as { anchor: string }[];
    expect(takmaAdli).toEqual(takmaAdsiz);
    expect(takmaAdsiz).toHaveLength(1);
  });

  it('ranks attached tables by their own statistics (rank option lives in each file)', () => {
    const { core } = baglanti();
    const rank = core
      .prepare("SELECT v FROM p_tefsir_test.unit_fts_config WHERE k = 'rank'")
      .get() as { v: string };
    expect(rank.v).toBe('bm25(1.0, 0.4, 1.0)');
  });

  it('measured limit: ten ATTACH succeed, the eleventh fails (MAX_ATTACHED=10)', () => {
    // A12.0 measured "too many attached databases - max 10"; documentation Arama 5 writes
    // "en cok 10 veritabani". The main database is not counted: main + 10 attached works.
    const { db, yol } = yeniPaket('metin', 'sinir.db');
    db.close();
    const baglanan = new DatabaseSync(yol);
    try {
      const secenekler = (
        baglanan.prepare('PRAGMA compile_options').all() as { compile_options: string }[]
      ).map((s) => s.compile_options);
      expect(secenekler).toContain('MAX_ATTACHED=10');

      const kullanilan: string[] = [];
      for (let i = 1; i <= 10; i += 1) {
        const takmaAd = `p_sinir_${String(i)}`;
        baglanan.prepare(`ATTACH DATABASE ? AS ${takmaAd}`).run(yol);
        kullanilan.push(takmaAd);
      }
      const liste = (baglanan.prepare('PRAGMA database_list').all() as { name: string }[]).map(
        (s) => s.name,
      );
      expect(liste.filter((a) => a.startsWith('p_sinir_'))).toHaveLength(10);

      expect(() => {
        baglanan.prepare('ATTACH DATABASE ? AS p_sinir_11').run(yol);
      }).toThrow(/too many attached databases - max 10/);

      // Detaching frees a slot again.
      baglanan.exec(`DETACH DATABASE ${kullanilan[0] ?? 'p_sinir_1'}`);
      expect(() => {
        baglanan.prepare('ATTACH DATABASE ? AS p_sinir_11').run(yol);
      }).not.toThrow();
    } finally {
      baglanan.close();
    }
  });
});
