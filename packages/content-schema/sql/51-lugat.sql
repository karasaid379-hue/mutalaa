-- risale-dizin paketinin lugat tablosu (Icerik paketleri 3.4; K-51 madde 9, 10 ve 14). Basliksoz kaynaktaki baytlarla; tanim_tr lugat kaynagindan gelen
-- (origin 'kaynak', bayt bayt) ya da editorun yazdigi (origin 'editor', NFC) tanimdir (tanimsiz aday icin NULL; onayli maddede doludur). Ayni basliksoz
-- farkli kaynaktan ve/veya farkli anlam_no ile birden cok satir olabilir: anahtar (basliksoz, kaynak, anlam_no); kaynak kaynagin source_id'sidir.
-- status yalniz 'onayli' ya da 'aday'dir: aday yalniz dev ve internal paketlerinde bulunur ve uygulamada "dogrulanmamis" isaretini status sutunundan
-- turetir; red hic bir pakete girmez. Siklik, kitap sayisi ve Kelime-Frekans anlam basvurusu pakete girmez.
-- Arama icin FTS yoktur: basliksoz_norm uzerindeki dizin yeter. basliksoz_norm tekil degildir (farkli yazimlar ayni norm anahtarini paylasir).
CREATE TABLE lugat (basliksoz TEXT NOT NULL, basliksoz_norm TEXT NOT NULL, osmanlica_yazim TEXT, koken_dil TEXT, tanim_tr TEXT,
                    anlam_no INTEGER NOT NULL CHECK (anlam_no >= 1), kaynak TEXT NOT NULL,
                    duzey INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('onayli', 'aday')), origin TEXT NOT NULL,
                    version TEXT NOT NULL, content_hash TEXT NOT NULL,
                    PRIMARY KEY (basliksoz, kaynak, anlam_no),
                    CHECK (status <> 'onayli' OR (tanim_tr IS NOT NULL AND trim(tanim_tr) <> ''))) WITHOUT ROWID;
CREATE INDEX lugat_norm ON lugat(basliksoz_norm);
