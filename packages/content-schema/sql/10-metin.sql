-- Metin paketleri: core, tefsir-elmalili, hadis-*, risale-{kitap} (İçerik paketleri §3.2).
CREATE TABLE unit (
  rowid         INTEGER PRIMARY KEY,         -- yalnız bu paket sürümünde geçerli
  anchor        TEXT NOT NULL UNIQUE,        -- kalıcı adres; kullanıcı verisi buna bağlanır
  kind          TEXT NOT NULL,               -- ayet | meal | tefsir | risale | hadis | hadis_ceviri
  role          TEXT NOT NULL DEFAULT 'govde',
  parent_path   TEXT,
  ord           INTEGER NOT NULL,            -- okuma sırası
  ayah_first    INTEGER, ayah_last INTEGER,  -- küresel âyet sırası 1..6236
  label         TEXT NOT NULL,               -- 'Sözler › 10. Söz › 3. Hakikat ¶4'; yayınlayıcı üretir
  text          TEXT NOT NULL,               -- kanonik metin (Tanzil aynen; kendi metnimiz NFC)
  marks TEXT, sentences TEXT, attrs TEXT,    -- JSON
  content_hash  TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'etkin',
  successors    TEXT                         -- JSON yönlendirme
);
CREATE INDEX unit_ord    ON unit(ord);
CREATE INDEX unit_parent ON unit(parent_path, ord);
CREATE INDEX unit_ayah   ON unit(ayah_first, ayah_last);
