-- risale-dizin: içeriksiz arama tabloları; metin kitap paketlerindedir (Arama §2).
-- unit_search yoktur. Satır kimliği unit_ref.rowid'dir. Satırlar doğrudan yazılır;
-- içeriksiz tabloda 'rebuild' çalışmaz (K-44 madde 4).
CREATE VIRTUAL TABLE unit_fts USING fts5(tr_wide, tr_stem, ar_norm, content='',
  tokenize='unicode61 remove_diacritics 0', prefix='2 3 4');
CREATE VIRTUAL TABLE unit_tri USING fts5(ar_norm, content='', tokenize='trigram');
