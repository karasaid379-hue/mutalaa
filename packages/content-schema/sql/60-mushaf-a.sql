-- mushaf-a-cuz-NN (İçerik paketleri §3.5). Tablo ve sütun adları belgeden; sayfa, ilk âyetinin
-- bulunduğu cüzün paketine girer.
-- Sütun türleri A26/A27.2/A40'ta kesinleşir.
CREATE TABLE page_font (page INTEGER NOT NULL, format TEXT NOT NULL, data BLOB NOT NULL, sha256 TEXT NOT NULL,
                        PRIMARY KEY (page, format));
CREATE TABLE page_line (page INTEGER NOT NULL, line INTEGER NOT NULL, line_type TEXT NOT NULL,
                        centered INTEGER NOT NULL, sure INTEGER,
                        PRIMARY KEY (page, line)) WITHOUT ROWID;
CREATE TABLE glyph_word (page INTEGER NOT NULL, line INTEGER NOT NULL, pos INTEGER NOT NULL, anchor TEXT,
                         ayah INTEGER, glyph TEXT NOT NULL, is_ayah_end INTEGER NOT NULL,
                         PRIMARY KEY (page, line, pos)) WITHOUT ROWID;
