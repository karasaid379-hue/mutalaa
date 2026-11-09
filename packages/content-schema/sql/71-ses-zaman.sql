-- ses-zaman-{kayit} (İçerik paketleri §3.5). Zamanlar sure dosyasına göre ms, aralık yarı açık.
-- Tablo ve sütun adları A27.2'de kesinleşir.
-- Sütun türleri A26/A27.2/A40'ta kesinleşir.
CREATE TABLE ayet_zaman (anchor TEXT PRIMARY KEY, start_ms INTEGER NOT NULL, end_ms INTEGER NOT NULL) WITHOUT ROWID;
CREATE TABLE kelime_zaman (anchor TEXT NOT NULL, kelime_no INTEGER NOT NULL, start_ms INTEGER NOT NULL,
                           end_ms INTEGER NOT NULL, PRIMARY KEY (anchor, kelime_no)) WITHOUT ROWID;
CREATE TABLE ozel_bolut (sure INTEGER NOT NULL, tur TEXT NOT NULL, start_ms INTEGER NOT NULL,
                         end_ms INTEGER NOT NULL, PRIMARY KEY (sure, tur, start_ms)) WITHOUT ROWID;
