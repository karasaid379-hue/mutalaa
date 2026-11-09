-- risale-dizin paketi (İçerik paketleri §3.4). İndeks içeriksizdir; metin yalnız kitap paketlerindedir.
-- unit_fts ve unit_tri: 21-arama-iceriksiz.sql. xref_idx, tr_root_index ve page_map: 11, 12, 31.
-- unit_ref.rowid, içeriksiz unit_fts ve unit_tri satır kimliğidir.
CREATE TABLE unit_ref (rowid INTEGER PRIMARY KEY, anchor TEXT NOT NULL UNIQUE,
                       pack_id TEXT NOT NULL, ord INTEGER NOT NULL, label TEXT NOT NULL);
