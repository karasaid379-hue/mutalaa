// Closed value sets shared with the database, the pipeline and the server.
// Source of truth: packages/content-schema/enums.json (order is significant).
// test/enums.test.ts keeps this file and the JSON identical.

export const LICENSE_STATUS = ['serbest', 'bekliyor', 'ic_kullanim', 'kapali'] as const;
export type LicenseStatus = (typeof LICENSE_STATUS)[number];

export const XREF_TYPE = [
  'atif',
  'iktibas',
  'ima',
  'kok',
  'lemma',
  'konu',
  'benzer_ayet',
  'anlamsal',
] as const;
export type XrefType = (typeof XREF_TYPE)[number];

export const XREF_STATUS = ['aday', 'onayli', 'red'] as const;
export type XrefStatus = (typeof XREF_STATUS)[number];

export const XREF_ORIGIN = ['hat', 'editor', 'kullanici_oyu'] as const;
export type XrefOrigin = (typeof XREF_ORIGIN)[number];

export const SOURCE_KIND = [
  'kuran_metni',
  'meal',
  'tefsir',
  'hadis',
  'hadis_ceviri',
  'risale',
  'kitap',
  'morfoloji',
  'kelime_anlami',
  'sozluk',
  'mushaf_duzeni',
  'mushaf_gorseli',
  'font',
  'baski',
  'ses',
  'zamanlama',
  'baglanti_verisi',
] as const;
export type SourceKind = (typeof SOURCE_KIND)[number];

export const DERLEME_TURU = ['dev', 'internal', 'public'] as const;
export type DerlemeTuru = (typeof DERLEME_TURU)[number];
