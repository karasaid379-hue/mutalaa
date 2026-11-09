-- Her pakette (İçerik paketleri §3.1).
PRAGMA user_version = 1;    -- paket şema sürümü; pack_meta.schema_version ile aynı

CREATE TABLE pack_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;

CREATE TABLE pack_source (source_id TEXT PRIMARY KEY) WITHOUT ROWID;

CREATE TABLE attribution (
  source_id TEXT PRIMARY KEY, title TEXT NOT NULL, version TEXT, source_url TEXT,
  required_credit TEXT NOT NULL, notice_text TEXT
);
