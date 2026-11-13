-- kelime-kok paketi (İçerik paketleri §3.3). tr_root_index: 12-tr-root.sql; xref_idx: 11-xref.sql (yalnız QAC'den türeyen kok ve lemma bağlantıları, K-51 madde 3).
-- core'daki meal birimlerinin Türkçe → kök indeksi (tr_root_index) bu pakette durur.
CREATE TABLE word_morph (anchor TEXT PRIMARY KEY, root_id INTEGER, lemma_id INTEGER, pos TEXT, features TEXT) WITHOUT ROWID;
CREATE INDEX word_morph_root  ON word_morph(root_id);
CREATE INDEX word_morph_lemma ON word_morph(lemma_id);

CREATE TABLE root  (id INTEGER PRIMARY KEY, letters TEXT NOT NULL, occurrences INTEGER NOT NULL,
                    ayah_count INTEGER NOT NULL, idf_q REAL, kok_anlami TEXT);

CREATE TABLE lemma (id INTEGER PRIMARY KEY, lang TEXT NOT NULL, text TEXT NOT NULL, text_clean TEXT NOT NULL,
                    root_id INTEGER, occurrences INTEGER NOT NULL, ar_lemma_id INTEGER, etymological_only INTEGER NOT NULL,
                    approval TEXT NOT NULL);  -- editor | auto | qac (K-51 madde 9)

CREATE TABLE lemma_gloss (lemma_id INTEGER PRIMARY KEY, anlam_kisa TEXT NOT NULL, kuran_anlamlari TEXT NOT NULL,
                          turkce_es_kelime TEXT, yalnizca_etimolojik INTEGER NOT NULL, status TEXT NOT NULL,
                          origin TEXT NOT NULL);

CREATE TABLE tr_form (key_wide TEXT NOT NULL, key_narrow TEXT NOT NULL, tr_lemma_id INTEGER NOT NULL,
                      freq INTEGER NOT NULL, PRIMARY KEY (key_narrow, tr_lemma_id)) WITHOUT ROWID;
CREATE INDEX tr_form_wide ON tr_form(key_wide);
