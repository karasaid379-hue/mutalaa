-- Paket yazımından sonra çalışır (içeriksiz tablolar: risale-dizin).
-- 'rebuild' yoktur: SQLite 3.53.4 "'rebuild' may not be used with a contentless fts5 table"
-- hatası verir (K-44 madde 4). Yalnız rank ve optimize çalışır.
INSERT INTO unit_fts(unit_fts, rank) VALUES('rank', 'bm25(1.0, 0.4, 1.0)');
INSERT INTO unit_fts(unit_fts) VALUES('optimize');
INSERT INTO unit_tri(unit_tri) VALUES('optimize');
