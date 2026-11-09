-- mushaf-b (İçerik paketleri §3.5). page_map (Türk düzeni): 31-page-map.sql.
-- Görsel biçimi ve cüzlere bölünme Açık soru (MM-7).
-- Sütun türleri A26/A27.2/A40'ta kesinleşir.
CREATE TABLE page_image (page INTEGER NOT NULL, format TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
                         data BLOB NOT NULL, sha256 TEXT NOT NULL,
                         PRIMARY KEY (page, format));
CREATE TABLE ayah_box (page INTEGER NOT NULL, anchor TEXT NOT NULL, seq INTEGER NOT NULL,
                       x REAL NOT NULL, y REAL NOT NULL, w REAL NOT NULL, h REAL NOT NULL,
                       PRIMARY KEY (page, anchor, seq)) WITHOUT ROWID;
