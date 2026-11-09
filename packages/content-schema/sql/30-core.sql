-- core paketine özgü tablolar (İçerik paketleri §3.2). page_map: 31-page-map.sql.
CREATE TABLE quran_word (                    -- Tanzil'den türetilen kelime bölmesi
  anchor TEXT PRIMARY KEY, ayah_index INTEGER NOT NULL, word INTEGER NOT NULL,
  text_uthmani TEXT NOT NULL, norm TEXT NOT NULL, char_start INTEGER NOT NULL, char_end INTEGER NOT NULL
) WITHOUT ROWID;
CREATE INDEX quran_word_ayah ON quran_word(ayah_index, word);

CREATE TABLE quran_marker (                  -- cüz, hizb, çeyrek ve secde işaretleri (K-43 madde 2)
  kind TEXT, no INTEGER, anchor TEXT, secde_turu TEXT,
  PRIMARY KEY (kind, no)
) WITHOUT ROWID;

CREATE TABLE sure (no INTEGER PRIMARY KEY, name TEXT NOT NULL, name_ar TEXT NOT NULL,
                   ayah_count INTEGER NOT NULL, variants TEXT NOT NULL);
