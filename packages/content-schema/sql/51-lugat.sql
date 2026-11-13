-- risale-dizin paketinin lugat tablosu (Icerik paketleri 3.4; K-51 madde 9 ve 10). Basliksoz kaynaktaki baytlarla; tanim_tr editorun yazdigi tanimdir
-- (aday iken NULL olabilir; onayli maddede doludur). status yalniz 'onayli' ya da 'aday'dir: aday yalniz dev ve internal paketlerinde bulunur ve
-- uygulamada "dogrulanmamis" isaretini status sutunundan turetir; red hic bir pakete girmez. Siklik, kitap sayisi ve sozluk anlam basvurusu pakete girmez.
-- Arama icin FTS yoktur: basliksoz_norm uzerindeki dizin yeter. basliksoz_norm tekil degildir (farkli yazimlar ayni norm anahtarini paylasir).
CREATE TABLE lugat (basliksoz TEXT PRIMARY KEY, basliksoz_norm TEXT NOT NULL, osmanlica_yazim TEXT, koken_dil TEXT, tanim_tr TEXT,
                    duzey INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('onayli', 'aday')), origin TEXT NOT NULL,
                    version TEXT NOT NULL, content_hash TEXT NOT NULL,
                    CHECK (status <> 'onayli' OR (tanim_tr IS NOT NULL AND trim(tanim_tr) <> ''))) WITHOUT ROWID;
CREATE INDEX lugat_norm ON lugat(basliksoz_norm);
