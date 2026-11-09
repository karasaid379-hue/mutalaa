-- core, tefsir-elmalili, hadis-*, risale-dizin; risale-{kitap}'ta yok (İçerik paketleri §3.2, §4).
-- Sütunlar Bağlantı modeli §13 ile aynı.
CREATE TABLE xref_idx (
  id TEXT PRIMARY KEY,                       -- editoryal xref.id
  src_anchor TEXT NOT NULL, src_start INTEGER, src_end INTEGER,
  dst_anchor TEXT NOT NULL, dst_start INTEGER, dst_end INTEGER,
  type TEXT NOT NULL, score REAL NOT NULL, confidence REAL NOT NULL,
  approved INTEGER NOT NULL, folded INTEGER NOT NULL,   -- yayınlayıcı görünüm kuralını önceden hesaplar
  evidence TEXT NOT NULL, data_version TEXT NOT NULL
);
CREATE INDEX xref_idx_src ON xref_idx(src_anchor, type);
CREATE INDEX xref_idx_dst ON xref_idx(dst_anchor, type);
