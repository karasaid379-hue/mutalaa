-- ses-katalog (İçerik paketleri §3.5, K-41). Ses dosyaları paket dışındadır; url kendi depomuzdaki
-- değişmez adrestir: audio/{kayit}/{dosya_surumu}/{sss}.mp3.
-- Sütun türleri A26/A27.2/A40'ta kesinleşir.
CREATE TABLE okuyucu (id TEXT PRIMARY KEY, ad TEXT NOT NULL, ad_ar TEXT, sira INTEGER NOT NULL) WITHOUT ROWID;
CREATE TABLE kayit (id TEXT PRIMARY KEY, okuyucu_id TEXT NOT NULL, tarz TEXT, rivayet TEXT,
                    zamanlama TEXT, zamanlama_surumu TEXT, dosya_surumu TEXT NOT NULL,
                    bit_hizi_kbps INTEGER, bit_hizi_turu TEXT, toplam_bayt INTEGER) WITHOUT ROWID;
CREATE TABLE kayit_sure (kayit_id TEXT NOT NULL, sure INTEGER NOT NULL, url TEXT NOT NULL,
                         bayt INTEGER NOT NULL, sha256 TEXT NOT NULL, sure_ms INTEGER NOT NULL,
                         PRIMARY KEY (kayit_id, sure)) WITHOUT ROWID;
