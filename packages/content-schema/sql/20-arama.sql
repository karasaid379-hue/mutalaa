-- Metin paketlerinde (core, tefsir-elmalili, hadis-*): içerikli arama tabloları (Arama §2).
-- Gövde tablosu yoktur: gövdeyi cihazda stemTr üretir (K-44 madde 1). Simple Clean için ayrı
-- sütun ya da tablo yoktur; normalize hâli ar_norm içindedir (K-44 madde 2).
CREATE TABLE unit_search (rowid INTEGER PRIMARY KEY, tr_wide TEXT, tr_stem TEXT, ar_norm TEXT);  -- rowid = unit.rowid

CREATE VIRTUAL TABLE unit_fts USING fts5(
  tr_wide, tr_stem, ar_norm,
  content='unit_search', content_rowid='rowid',
  tokenize='unicode61 remove_diacritics 0',
  prefix='2 3 4'
);
CREATE VIRTUAL TABLE unit_tri USING fts5(
  ar_norm,
  content='unit_search', content_rowid='rowid',
  tokenize='trigram'
);
