-- Paket yazımından sonra çalışır (içerikli tablolar; Arama §2). Yayınlayıcı satırları yazdıktan sonra.
INSERT INTO unit_fts(unit_fts) VALUES('rebuild');
INSERT INTO unit_tri(unit_tri) VALUES('rebuild');
INSERT INTO unit_fts(unit_fts, rank) VALUES('rank', 'bm25(1.0, 0.4, 1.0)');
INSERT INTO unit_fts(unit_fts) VALUES('optimize');
INSERT INTO unit_tri(unit_tri) VALUES('optimize');
