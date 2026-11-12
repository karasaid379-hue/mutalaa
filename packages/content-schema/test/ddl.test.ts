import { readdirSync, readFileSync } from 'node:fs';
import type { DatabaseSync } from 'node:sqlite';
import { afterAll, describe, expect, it } from 'vitest';
import {
  buildPack,
  cleanup,
  loadPaketler,
  loadSql,
  newTempDir,
  runAfter,
  SQL_DIZINI,
} from './support/db.js';

afterAll(cleanup);

interface EnumsFile {
  enums: Record<string, string[]>;
}
const enumsJson = JSON.parse(
  readFileSync(new URL('../enums.json', import.meta.url), 'utf8'),
) as EnumsFile;

const PAKETLER = loadPaketler();
const TURLER = Object.keys(PAKETLER.turler);

/** Every pack type carries these three tables (Icerik paketleri 3.1). */
const ORTAK = ['attribution', 'pack_meta', 'pack_source'];

/**
 * Expected non-shadow table set per pack type: comparison table against
 * Icerik paketleri 3.1-3.5, Arama 2 and K-44.
 */
const BEKLENEN_TABLOLAR: Record<string, string[]> = {
  core: [
    ...ORTAK,
    'unit',
    'xref_idx',
    'unit_search',
    'unit_fts',
    'unit_tri',
    'quran_word',
    'quran_marker',
    'sure',
    'page_map',
  ],
  metin: [
    ...ORTAK,
    'unit',
    'xref_idx',
    'tr_root_index',
    'unit_search',
    'unit_fts',
    'unit_tri',
    'page_map',
  ],
  'risale-kitap': [...ORTAK, 'unit'],
  'risale-dizin': [
    ...ORTAK,
    'unit_ref',
    'xref_idx',
    'tr_root_index',
    'unit_fts',
    'unit_tri',
    'page_map',
  ],
  'kelime-kok': [
    ...ORTAK,
    'word_morph',
    'root',
    'lemma',
    'lemma_gloss',
    'tr_form',
    'tr_root_index',
  ],
  'mushaf-a-cuz': [...ORTAK, 'page_font', 'page_line', 'glyph_word'],
  'mushaf-b': [...ORTAK, 'page_image', 'ayah_box', 'page_map'],
  'ses-katalog': [...ORTAK, 'okuyucu', 'kayit', 'kayit_sure'],
  'ses-zaman': [...ORTAK, 'ayet_zaman', 'kelime_zaman', 'ozel_bolut'],
};

/** Column names (declaration order) per table, taken from the documents. */
const BEKLENEN_SUTUNLAR: Record<string, string[]> = {
  pack_meta: ['key', 'value'],
  pack_source: ['source_id'],
  attribution: ['source_id', 'title', 'version', 'source_url', 'required_credit', 'notice_text'],
  unit: [
    'rowid',
    'anchor',
    'kind',
    'role',
    'parent_path',
    'ord',
    'ayah_first',
    'ayah_last',
    'label',
    'text',
    'marks',
    'sentences',
    'attrs',
    'content_hash',
    'status',
    'approved',
    'successors',
  ],
  xref_idx: [
    'id',
    'src_anchor',
    'src_start',
    'src_end',
    'dst_anchor',
    'dst_start',
    'dst_end',
    'type',
    'score',
    'confidence',
    'approved',
    'folded',
    'evidence',
    'data_version',
  ],
  tr_root_index: [
    'anchor',
    'span_start',
    'span_end',
    'root_id',
    'tr_lemma_id',
    'etymological_only',
  ],
  unit_search: ['rowid', 'tr_wide', 'tr_stem', 'ar_norm'],
  unit_fts: ['tr_wide', 'tr_stem', 'ar_norm'],
  unit_tri: ['ar_norm'],
  quran_word: ['anchor', 'ayah_index', 'word', 'text_uthmani', 'norm', 'char_start', 'char_end'],
  quran_marker: ['kind', 'no', 'anchor', 'secde_turu'],
  sure: ['no', 'name', 'name_ar', 'ayah_count', 'variants'],
  page_map: [
    'layout',
    'volume',
    'page',
    'line',
    'start_anchor',
    'start_offset',
    'end_anchor',
    'end_offset',
  ],
  word_morph: ['anchor', 'root_id', 'lemma_id', 'pos', 'features'],
  root: ['id', 'letters', 'occurrences', 'ayah_count', 'idf_q', 'kok_anlami'],
  lemma: [
    'id',
    'lang',
    'text',
    'text_clean',
    'root_id',
    'occurrences',
    'ar_lemma_id',
    'etymological_only',
  ],
  lemma_gloss: [
    'lemma_id',
    'anlam_kisa',
    'kuran_anlamlari',
    'turkce_es_kelime',
    'yalnizca_etimolojik',
    'status',
    'origin',
  ],
  tr_form: ['key_wide', 'key_narrow', 'tr_lemma_id', 'freq'],
  unit_ref: ['rowid', 'anchor', 'pack_id', 'ord', 'label'],
  page_font: ['page', 'format', 'data', 'sha256'],
  page_line: ['page', 'line', 'line_type', 'centered', 'sure'],
  glyph_word: ['page', 'line', 'pos', 'anchor', 'ayah', 'glyph', 'is_ayah_end'],
  page_image: ['page', 'format', 'width', 'height', 'data', 'sha256'],
  ayah_box: ['page', 'anchor', 'seq', 'x', 'y', 'w', 'h'],
  okuyucu: ['id', 'ad', 'ad_ar', 'sira'],
  kayit: [
    'id',
    'okuyucu_id',
    'tarz',
    'rivayet',
    'zamanlama',
    'zamanlama_surumu',
    'dosya_surumu',
    'bit_hizi_kbps',
    'bit_hizi_turu',
    'toplam_bayt',
  ],
  kayit_sure: ['kayit_id', 'sure', 'url', 'bayt', 'sha256', 'sure_ms'],
  ayet_zaman: ['anchor', 'start_ms', 'end_ms'],
  kelime_zaman: ['anchor', 'kelime_no', 'start_ms', 'end_ms'],
  ozel_bolut: ['sure', 'tur', 'start_ms', 'end_ms'],
};

/**
 * Primary-key columns (in key order) of the tables whose key the documents fix:
 * Icerik paketleri 3.1-3.5. `rowid` is the integer primary key alias of unit and unit_ref.
 */
const BEKLENEN_PK: Record<string, string[]> = {
  pack_meta: ['key'],
  pack_source: ['source_id'],
  attribution: ['source_id'],
  quran_marker: ['kind', 'no'],
  quran_word: ['anchor'],
  tr_root_index: ['anchor', 'span_start'],
  word_morph: ['anchor'],
  tr_form: ['key_narrow', 'tr_lemma_id'],
  unit: ['rowid'],
  unit_ref: ['rowid'],
};

/** WITHOUT ROWID tables that Icerik paketleri 3.1-3.5 declares as such. */
const BELGELI_ROWIDSIZ = [
  'pack_meta',
  'pack_source',
  'quran_word',
  'quran_marker',
  'tr_root_index',
  'word_morph',
  'tr_form',
];

/**
 * WITHOUT ROWID tables of the mushaf and audio packs. The documents give no table options for
 * them (Mobil mimari 11 marks its page_line / glyph_word draft as a proposal, without the
 * option); the DDL files declare them WITHOUT ROWID and this list pins that.
 */
const DDL_ROWIDSIZ = [
  'page_line',
  'glyph_word',
  'ayah_box',
  'okuyucu',
  'kayit',
  'kayit_sure',
  'ayet_zaman',
  'kelime_zaman',
  'ozel_bolut',
];

/** Example pack_id values per pack type. */
const ORNEK_PACK_ID: Record<string, string[]> = {
  core: ['core'],
  metin: [
    'tefsir-elmalili',
    'hadis-tecrid',
    'hadis-kutub-i-sitte',
    'test-kucuk',
    'tefsir-test-ornek',
  ],
  'risale-kitap': ['risale-sozler', 'risale-mektubat', 'risale-dizin2'],
  'risale-dizin': ['risale-dizin'],
  'kelime-kok': ['kelime-kok'],
  'mushaf-a-cuz': [
    'mushaf-a-cuz-01',
    'mushaf-a-cuz-09',
    'mushaf-a-cuz-10',
    'mushaf-a-cuz-29',
    'mushaf-a-cuz-30',
  ],
  'mushaf-b': ['mushaf-b'],
  'ses-katalog': ['ses-katalog'],
  'ses-zaman': ['ses-zaman-ornek-kayit'],
};

function yeniVeritabani(tur: string): DatabaseSync {
  return buildPack(tur, `${newTempDir()}pack.db`);
}

function tablolar(db: DatabaseSync): string[] {
  const satirlar = db.prepare('PRAGMA table_list').all() as {
    schema: string;
    name: string;
    type: string;
  }[];
  return satirlar
    .filter(
      (s) =>
        s.schema === 'main' &&
        (s.type === 'table' || s.type === 'virtual') &&
        !s.name.startsWith('sqlite_'),
    )
    .map((s) => s.name)
    .sort();
}

function sutunlar(db: DatabaseSync, tablo: string): string[] {
  const satirlar = db.prepare(`PRAGMA table_info(${tablo})`).all() as { name: string }[];
  return satirlar.map((s) => s.name);
}

/** Primary-key column names of a table, in key order (PRAGMA table_info pk field). */
function pkSutunlari(db: DatabaseSync, tablo: string): string[] {
  const satirlar = db.prepare(`PRAGMA table_info(${tablo})`).all() as {
    name: string;
    pk: number;
  }[];
  return satirlar
    .filter((s) => s.pk > 0)
    .sort((a, b) => a.pk - b.pk)
    .map((s) => s.name);
}

/** Real tables (FTS5 shadow tables excluded) whose CREATE statement carries WITHOUT ROWID. */
function rowidsizTablolar(db: DatabaseSync): string[] {
  const satirlar = db.prepare("SELECT name, sql FROM sqlite_master WHERE type = 'table'").all() as {
    name: string;
    sql: string | null;
  }[];
  const gercek = new Set(tablolar(db));
  return satirlar
    .filter((s) => gercek.has(s.name) && /\bWITHOUT\s+ROWID\b/iu.test(s.sql ?? ''))
    .map((s) => s.name)
    .sort();
}

/** CREATE statement of a table, whitespace collapsed to single spaces. */
function olusturmaSql(db: DatabaseSync, ad: string): string {
  const satir = db.prepare('SELECT sql FROM sqlite_master WHERE name = ?').get(ad) as
    { sql: string } | undefined;
  return (satir?.sql ?? '').replace(/\s+/gu, ' ');
}

describe('paketler.json', () => {
  it('lists the nine pack types in order', () => {
    expect(TURLER).toEqual([
      'core',
      'metin',
      'risale-kitap',
      'risale-dizin',
      'kelime-kok',
      'mushaf-a-cuz',
      'mushaf-b',
      'ses-katalog',
      'ses-zaman',
    ]);
    expect(PAKETLER.version).toBe(1);
  });

  it('references only existing files, and every .sql file is listed', () => {
    const diskte = readdirSync(SQL_DIZINI)
      .filter((d) => d.endsWith('.sql'))
      .sort();
    const listelenen = new Set<string>();
    for (const tur of Object.values(PAKETLER.turler)) {
      for (const dosya of [...tur.ddl, ...tur.sonra]) {
        listelenen.add(dosya);
        expect(diskte, dosya).toContain(dosya);
      }
    }
    expect([...listelenen].sort()).toEqual(diskte);
  });

  it('has no duplicate file within a type', () => {
    for (const [ad, tur] of Object.entries(PAKETLER.turler)) {
      const hepsi = [...tur.ddl, ...tur.sonra];
      expect(new Set(hepsi).size, ad).toBe(hepsi.length);
    }
  });

  it('matches example pack ids to exactly their own type', () => {
    for (const tur of TURLER) {
      for (const packId of ORNEK_PACK_ID[tur] ?? []) {
        const eslesenler = TURLER.filter((t) =>
          new RegExp(PAKETLER.turler[t]?.desen ?? '^$').test(packId),
        );
        expect(eslesenler, packId).toEqual([tur]);
      }
    }
  });

  it('keeps risale-dizin out of risale-kitap and rejects out-of-range or malformed ids', () => {
    const kitap = new RegExp(PAKETLER.turler['risale-kitap']?.desen ?? '^$');
    expect(kitap.test('risale-dizin')).toBe(false);
    expect(kitap.test('risale-sozler')).toBe(true);

    const cuz = new RegExp(PAKETLER.turler['mushaf-a-cuz']?.desen ?? '^$');
    for (const kotu of [
      'mushaf-a-cuz-31',
      'mushaf-a-cuz-00',
      'mushaf-a-cuz-1',
      'mushaf-a-cuz-100',
    ]) {
      expect(cuz.test(kotu), kotu).toBe(false);
    }

    const hicbiri = [
      'Core',
      'core-x',
      'tefsir-',
      'test-',
      'Test-kucuk',
      'test_kucuk',
      'hadis_tecrid',
      'ses-zaman-',
      'kelime-kok-2',
    ];
    for (const kotu of hicbiri) {
      const eslesen = TURLER.filter((t) =>
        new RegExp(PAKETLER.turler[t]?.desen ?? '^$').test(kotu),
      );
      expect(eslesen, kotu).toEqual([]);
    }
  });
});

describe('DDL', () => {
  for (const tur of TURLER) {
    describe(tur, () => {
      it('installs on an empty file, user_version 1', () => {
        const db = yeniVeritabani(tur);
        const surum = db.prepare('PRAGMA user_version').get() as { user_version: number };
        expect(surum.user_version).toBe(1);
      });

      it('has the expected table set', () => {
        const db = yeniVeritabani(tur);
        expect(tablolar(db)).toEqual([...(BEKLENEN_TABLOLAR[tur] ?? [])].sort());
      });

      it('has the documented columns in every table', () => {
        const db = yeniVeritabani(tur);
        for (const tablo of tablolar(db)) {
          expect(sutunlar(db, tablo), tablo).toEqual(BEKLENEN_SUTUNLAR[tablo]);
        }
      });

      it('has the documented primary keys', () => {
        const db = yeniVeritabani(tur);
        for (const tablo of tablolar(db)) {
          const beklenen = BEKLENEN_PK[tablo];
          if (beklenen !== undefined) expect(pkSutunlari(db, tablo), tablo).toEqual(beklenen);
        }
      });

      it('declares WITHOUT ROWID on exactly the expected tables', () => {
        const db = yeniVeritabani(tur);
        const rowidsiz = new Set([...BELGELI_ROWIDSIZ, ...DDL_ROWIDSIZ]);
        const beklenen = tablolar(db).filter((t) => rowidsiz.has(t));
        expect(rowidsizTablolar(db)).toEqual(beklenen);
      });

      it('has no tr_stem_lex table (K-44 item 1)', () => {
        const db = yeniVeritabani(tur);
        const adlar = (
          db.prepare('SELECT name FROM sqlite_master').all() as { name: string }[]
        ).map((s) => s.name);
        expect(adlar.filter((a) => a.startsWith('tr_stem_lex'))).toEqual([]);
      });

      it('runs the post-write files on an empty database', () => {
        const db = yeniVeritabani(tur);
        expect(() => {
          runAfter(db, tur);
        }).not.toThrow();
      });
    });
  }

  it('lists every documented table name in the expected-column map', () => {
    const kullanilan = new Set(Object.values(BEKLENEN_TABLOLAR).flat());
    expect([...kullanilan].sort()).toEqual(Object.keys(BEKLENEN_SUTUNLAR).sort());
  });

  it('pins the primary key of every table named in the key map across the pack types', () => {
    const gorulen = new Set<string>();
    for (const tur of TURLER) {
      for (const tablo of tablolar(yeniVeritabani(tur))) {
        if (tablo in BEKLENEN_PK) gorulen.add(tablo);
      }
    }
    expect([...gorulen].sort()).toEqual(Object.keys(BEKLENEN_PK).sort());
  });

  it('declares the documented WITHOUT ROWID set (Icerik paketleri 3.1-3.5)', () => {
    const bulunan = new Set<string>();
    for (const tur of TURLER) {
      for (const tablo of rowidsizTablolar(yeniVeritabani(tur))) bulunan.add(tablo);
    }
    const belgeli = [...bulunan].filter((t) => BELGELI_ROWIDSIZ.includes(t)).sort();
    expect(belgeli).toEqual([...BELGELI_ROWIDSIZ].sort());
    expect([...bulunan].filter((t) => !BELGELI_ROWIDSIZ.includes(t)).sort()).toEqual(
      [...DDL_ROWIDSIZ].sort(),
    );
  });

  it('keeps attribution, unit, unit_ref, sure, xref_idx and unit_search as rowid tables', () => {
    for (const tur of TURLER) {
      const rowidsiz = rowidsizTablolar(yeniVeritabani(tur));
      for (const tablo of ['attribution', 'unit', 'unit_ref', 'sure', 'xref_idx', 'unit_search']) {
        expect(rowidsiz, `${tur}/${tablo}`).not.toContain(tablo);
      }
    }
  });

  it('keeps tr_root_index out of core (K-44 item 3)', () => {
    expect(tablolar(yeniVeritabani('core'))).not.toContain('tr_root_index');
  });

  it('keeps xref_idx and the search tables out of risale-kitap (K-44 item 3)', () => {
    const adlar = tablolar(yeniVeritabani('risale-kitap'));
    expect(adlar).not.toContain('xref_idx');
    expect(adlar).not.toContain('unit_fts');
    expect(adlar).not.toContain('unit_tri');
    expect(adlar).not.toContain('unit_search');
    expect(adlar).not.toContain('tr_root_index');
  });

  it('has no unit_search in risale-dizin (contentless index)', () => {
    expect(tablolar(yeniVeritabani('risale-dizin'))).not.toContain('unit_search');
  });

  it('keeps pack_meta.schema_version aligned with user_version (stored by the publisher)', () => {
    // The DDL only declares the table; this pins the PRAGMA literal itself.
    expect(loadSql('00-ortak.sql')).toContain('PRAGMA user_version = 1;');
  });
});

describe('enums', () => {
  it('uses a unit.status default that is a unit_status enum value', () => {
    const db = yeniVeritabani('core');
    const sutun = (
      db.prepare('PRAGMA table_info(unit)').all() as { name: string; dflt_value: string | null }[]
    ).find((s) => s.name === 'status');
    expect(sutun?.dflt_value).toBeDefined();
    const varsayilan = (sutun?.dflt_value ?? '').replace(/^'|'$/g, '');
    expect(varsayilan).toBe('etkin');
    expect(enumsJson.enums['unit_status']).toContain(varsayilan);
  });

  it('declares unit.approved as INTEGER NOT NULL DEFAULT 1 in the unit table of every unit pack (K-46 item 5)', () => {
    for (const tur of ['core', 'metin', 'risale-kitap']) {
      const sutun = (
        yeniVeritabani(tur).prepare('PRAGMA table_info(unit)').all() as {
          name: string;
          type: string;
          notnull: number;
          dflt_value: string | null;
        }[]
      ).find((s) => s.name === 'approved');
      expect(sutun?.type, tur).toBe('INTEGER');
      expect(sutun?.notnull, tur).toBe(1);
      expect(sutun?.dflt_value, tur).toBe('1');
    }
  });

  it('keeps the documented unit.kind values in the unit_kind enum', () => {
    const belgedeki = ['ayet', 'meal', 'tefsir', 'risale', 'hadis', 'hadis_ceviri'];
    for (const deger of belgedeki) {
      expect(enumsJson.enums['unit_kind'], deger).toContain(deger);
    }
  });
});

describe('FTS5 table options (Arama 2)', () => {
  for (const tur of ['core', 'metin']) {
    it(`${tur}: unit_fts is external-content with unicode61 (no diacritic removal) and prefix 2 3 4`, () => {
      const sql = olusturmaSql(yeniVeritabani(tur), 'unit_fts');
      expect(sql).toMatch(/^CREATE VIRTUAL TABLE unit_fts USING fts5\(/u);
      expect(sql).toContain("content='unit_search'");
      expect(sql).toContain("content_rowid='rowid'");
      expect(sql).toContain("tokenize='unicode61 remove_diacritics 0'");
      expect(sql).toContain("prefix='2 3 4'");
    });

    it(`${tur}: unit_tri is external-content with the trigram tokenizer`, () => {
      const sql = olusturmaSql(yeniVeritabani(tur), 'unit_tri');
      expect(sql).toMatch(/^CREATE VIRTUAL TABLE unit_tri USING fts5\(/u);
      expect(sql).toContain("content='unit_search'");
      expect(sql).toContain("content_rowid='rowid'");
      expect(sql).toContain("tokenize='trigram'");
    });

    it(`${tur}: unit_fts_config shadow table exists and holds the FTS5 version`, () => {
      const db = yeniVeritabani(tur);
      const surum = db.prepare("SELECT v FROM unit_fts_config WHERE k = 'version'").get() as
        { v: number | bigint } | undefined;
      expect(surum).toBeDefined();
    });
  }

  it('risale-dizin: both tables are contentless with the same tokenizers and prefixes', () => {
    const db = yeniVeritabani('risale-dizin');
    const fts = olusturmaSql(db, 'unit_fts');
    expect(fts).toContain("content=''");
    expect(fts).toContain("tokenize='unicode61 remove_diacritics 0'");
    expect(fts).toContain("prefix='2 3 4'");
    expect(fts).not.toContain('content_rowid');
    const tri = olusturmaSql(db, 'unit_tri');
    expect(tri).toContain("content=''");
    expect(tri).toContain("tokenize='trigram'");
  });
});

describe('FTS5 behaviour', () => {
  /** Synthetic Arabic-script letter run built from code points; not a Quran word. */
  const SENTETIK_DIZI = String.fromCodePoint(0x628, 0x62a, 0x62b, 0x62c, 0x62d, 0x62e);
  const BITISIK_EK = String.fromCodePoint(0x648);

  function satirEkle(
    db: DatabaseSync,
    rowid: number,
    trWide: string,
    trStem: string,
    arNorm: string | null,
  ): void {
    db.prepare('INSERT INTO unit_search(rowid, tr_wide, tr_stem, ar_norm) VALUES (?, ?, ?, ?)').run(
      rowid,
      trWide,
      trStem,
      arNorm,
    );
  }

  function rowidler(db: DatabaseSync, sql: string, ...parametreler: string[]): number[] {
    const satirlar = db.prepare(sql).all(...parametreler) as { rowid: number | bigint }[];
    return satirlar.map((s) => Number(s.rowid));
  }

  it('finds a column-filtered term after rebuild', () => {
    const db = yeniVeritabani('core');
    satirEkle(db, 1, 'deneme paragrafi 1 isik', 'deneme paragraf 1 isik', null);
    satirEkle(db, 2, 'deneme paragrafi 2 gunes', 'deneme paragraf 2 gunes', null);
    runAfter(db, 'core');

    expect(
      rowidler(db, 'SELECT rowid FROM unit_fts WHERE unit_fts MATCH ?', 'tr_wide : "isik"'),
    ).toEqual([1]);
    expect(
      rowidler(db, 'SELECT rowid FROM unit_fts WHERE unit_fts MATCH ?', 'tr_wide : "gunes"'),
    ).toEqual([2]);
    expect(
      rowidler(db, 'SELECT rowid FROM unit_fts WHERE unit_fts MATCH ?', 'tr_wide : "yok"'),
    ).toEqual([]);
  });

  it('supports 2-4 character prefix queries', () => {
    const db = yeniVeritabani('core');
    satirEkle(db, 1, 'deneme paragrafi 1 isik', 'deneme paragraf 1 isik', null);
    satirEkle(db, 2, 'deneme paragrafi 2 gunes', 'deneme paragraf 2 gunes', null);
    runAfter(db, 'core');

    for (const onek of ['is*', 'isi*', 'isik*']) {
      expect(
        rowidler(db, 'SELECT rowid FROM unit_fts WHERE unit_fts MATCH ?', `tr_wide : ${onek}`),
        onek,
      ).toEqual([1]);
    }
  });

  it('applies the bm25 column weights set by the rank option', () => {
    const db = yeniVeritabani('core');
    // Row 1 holds the term in tr_wide (weight 1.0), row 2 in tr_stem (weight 0.4).
    satirEkle(db, 1, 'isik', 'aaa', null);
    satirEkle(db, 2, 'bbb', 'isik', null);
    for (let i = 3; i <= 10; i += 1) {
      satirEkle(db, i, `dolgu${String(i)}`, `dolgu${String(i)}`, null);
    }
    runAfter(db, 'core');

    const satirlar = db
      .prepare('SELECT rowid, rank FROM unit_fts WHERE unit_fts MATCH ? ORDER BY rank')
      .all('isik') as { rowid: number | bigint; rank: number }[];
    expect(satirlar.map((s) => Number(s.rowid))).toEqual([1, 2]);

    const [birinci, ikinci] = satirlar;
    expect(birinci).toBeDefined();
    expect(ikinci).toBeDefined();
    if (birinci === undefined || ikinci === undefined) {
      return;
    }
    expect(birinci.rank).toBeLessThan(ikinci.rank);
    // bm25 weights the term frequency (tf = weight * count) and saturates it. Both rows have equal
    // length and the same idf, so the ratio is (0.4 * 2.2 / (0.4 + 1.2)) / (1.0 * 2.2 / (1.0 + 1.2))
    // = 0.55 with k1 = 1.2 and b = 0.75. Without the rank option the weights would be equal (ratio 1).
    expect(ikinci.rank / birinci.rank).toBeCloseTo(0.55, 2);
  });

  it('finds a substring of a synthetic Arabic-script run through the trigram table', () => {
    const db = yeniVeritabani('core');
    satirEkle(db, 1, 'deneme', 'deneme', SENTETIK_DIZI);
    satirEkle(db, 2, 'deneme', 'deneme', BITISIK_EK + SENTETIK_DIZI);
    satirEkle(db, 3, 'deneme', 'deneme', String.fromCodePoint(0x62f, 0x630, 0x631, 0x632));
    runAfter(db, 'core');

    const altDize = SENTETIK_DIZI.slice(1, 4);
    expect(
      rowidler(
        db,
        'SELECT rowid FROM unit_tri WHERE unit_tri MATCH ? ORDER BY rowid',
        `"${altDize}"`,
      ),
    ).toEqual([1, 2]);

    // A prefixed run is found with the bare run as the query, not the other way round.
    const onekli = BITISIK_EK + SENTETIK_DIZI;
    expect(
      rowidler(db, 'SELECT rowid FROM unit_tri WHERE unit_tri MATCH ?', `"${onekli}"`),
    ).toEqual([2]);
  });

  it('rejects rebuild on the contentless tables of risale-dizin (K-44 item 4)', () => {
    const db = yeniVeritabani('risale-dizin');
    expect(() => {
      db.exec("INSERT INTO unit_fts(unit_fts) VALUES('rebuild')");
    }).toThrow(/contentless/);
    expect(() => {
      db.exec("INSERT INTO unit_tri(unit_tri) VALUES('rebuild')");
    }).toThrow(/contentless/);
  });

  it('writes contentless rows directly and queries them with the post-write file applied', () => {
    const db = yeniVeritabani('risale-dizin');
    db.prepare(
      'INSERT INTO unit_ref(rowid, anchor, pack_id, ord, label) VALUES (1, ?, ?, 1, ?)',
    ).run('rn:deneme:p1', 'risale-deneme', 'Deneme paragrafi 1');
    db.prepare('INSERT INTO unit_fts(rowid, tr_wide, tr_stem, ar_norm) VALUES (1, ?, ?, ?)').run(
      'deneme paragrafi 1 isik',
      'deneme paragraf 1 isik',
      null,
    );
    db.prepare('INSERT INTO unit_tri(rowid, ar_norm) VALUES (1, ?)').run(SENTETIK_DIZI);
    runAfter(db, 'risale-dizin');

    const eslesen = db
      .prepare(
        'SELECT r.anchor AS anchor FROM unit_fts f JOIN unit_ref r ON r.rowid = f.rowid WHERE unit_fts MATCH ?',
      )
      .all('tr_wide : "isik"') as { anchor: string }[];
    expect(eslesen.map((s) => s.anchor)).toEqual(['rn:deneme:p1']);
    expect(
      rowidler(
        db,
        'SELECT rowid FROM unit_tri WHERE unit_tri MATCH ?',
        `"${SENTETIK_DIZI.slice(2, 5)}"`,
      ),
    ).toEqual([1]);
  });
});
