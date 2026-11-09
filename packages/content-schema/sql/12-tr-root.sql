-- kelime-kok, tefsir-elmalili, hadis-* ve risale-dizin paketlerinde; core'da yok (K-44 madde 3).
-- QAC'ye bağlı; yalnız onaylı satırlar uygulanır (P-09).
CREATE TABLE tr_root_index (
  anchor TEXT NOT NULL, span_start INTEGER NOT NULL, span_end INTEGER NOT NULL,
  root_id INTEGER NOT NULL, tr_lemma_id INTEGER NOT NULL, etymological_only INTEGER NOT NULL,
  PRIMARY KEY (anchor, span_start)
) WITHOUT ROWID;
CREATE INDEX tr_root_index_root ON tr_root_index(root_id);
