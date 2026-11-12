"""`export pg --source qac-morfoloji`: root, lemma, lemma_dalga, quran_word QAC sutunlari (A17.3).

SENTETIK zincir (`qac_hazirla`; 6.236 ayet) `mutalaa_test` veritabanina yuklenir: once Tanzil
(`quran_word` satirlari), sonra QAC. Testler dis islem icinde kosar ve sonunda geri alinir.
Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Hicbir
Arapca metin ya da sayi hafizadan yazilmaz.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from qac_yardimci import TARIH, QacZinciri, qac_hazirla
from quranwbw_yardimci import ihracat, tanzil_qa
from ust_veri_yardimci import UstVeriZinciri

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.morphology import cuz_baslangici
from mutalaa_pipeline.export import pg, pg_qac
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.qac import DOSYA_ADI

KAYNAK = "qac-morfoloji"
TANZIL = "tanzil-uthmani"
TANZIL_SUTUNLARI = (
    "anchor, surah, ayah, word, ayah_index, text_uthmani, norm, char_start, char_end,"
    " source_id, data_version"
)
KELIME_SUTUNLARI = "anchor, root_id, lemma_id, pos, features::text, morph_source"


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); kalinti varsa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.root) + (SELECT count(*) FROM icerik.lemma)"
            " + (SELECT count(*) FROM icerik.lemma_dalga)"
            " + (SELECT count(*) FROM icerik.quran_word)"
            " + (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (["tanzil-uthmani", "tanzil-simple-clean"], [KAYNAK, TANZIL, "tanzil-simple-clean"]),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde root/lemma/quran_word/Tanzil satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def qz(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QacZinciri:
    zincir = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    zincir.hepsi()
    tanzil_qa(zincir.z)
    return zincir


def tanzil_yukle(qz: QacZinciri, conn: psycopg.Connection) -> None:
    assert ihracat(qz.z, conn, TANZIL) == 0


def qac_yukle(qz: QacZinciri, conn: psycopg.Connection, **kw: object) -> int:
    return ihracat(qz.z, conn, KAYNAK, **kw)


def son_sayilar(qz: QacZinciri, source: str = KAYNAK) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes()) for yol in sorted((qz.z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [
        r
        for r in raporlar
        if r.get("komut") == "export pg" and r["parametreler"]["source"] == source
    ]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def tablo(conn: psycopg.Connection, sorgu: str) -> list[tuple[object, ...]]:
    return [tuple(s) for s in conn.execute(sorgu).fetchall()]  # type: ignore[arg-type]


def anlik(conn: psycopg.Connection) -> dict[str, list[tuple[object, ...]]]:
    """Dort tablonun tam goruntusu (degisiklik yok kanitlari icin)."""
    return {
        "root": tablo(conn, "SELECT * FROM icerik.root ORDER BY id"),
        "lemma": tablo(conn, "SELECT * FROM icerik.lemma ORDER BY id"),
        "dalga": tablo(conn, "SELECT * FROM icerik.lemma_dalga ORDER BY lemma_id"),
        "kelime": tablo(conn, f"SELECT {KELIME_SUTUNLARI} FROM icerik.quran_word ORDER BY anchor"),
    }


SIRA_SQL = (
    "WITH k AS (SELECT root_id, count(*) AS n FROM icerik.quran_word WHERE root_id IS NOT NULL"
    " GROUP BY root_id), ls AS (SELECT lemma_id, count(*) AS n FROM icerik.quran_word"
    " WHERE lemma_id IS NOT NULL GROUP BY lemma_id)"
    " SELECT d.lemma_id, row_number() OVER (PARTITION BY d.dalga ORDER BY (l.root_id IS NULL),"
    " CASE WHEN l.root_id IS NULL THEN 0 ELSE -k.n END, l.root_id, -ls.n, l.id) AS sira"
    " FROM icerik.lemma_dalga d JOIN icerik.lemma l ON l.id = d.lemma_id"
    " LEFT JOIN k ON k.root_id = l.root_id JOIN ls ON ls.lemma_id = l.id ORDER BY d.lemma_id"
)


# --- yukleme ve idempotentlik ------------------------------------------------------------


@pytest.mark.veritabani
def test_ilk_yukleme_sayilar_ikinci_kosu_sifir_degisiklik(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    kok_sayisi = len(qz.staged(KAYNAK, "roots.jsonl"))
    lemma_sayisi = len(qz.staged(KAYNAK, "lemmas.jsonl"))
    kelime_sayisi = len(qz.staged(KAYNAK, "words.jsonl"))
    assert qac_yukle(qz, conn) == 0
    ilk = son_sayilar(qz)
    assert (ilk["kok_staging"], ilk["kok_eklenen"], ilk["kok_guncellenen"]) == (
        kok_sayisi,
        kok_sayisi,
        0,
    )
    assert (ilk["lemma_staging"], ilk["lemma_eklenen"]) == (lemma_sayisi, lemma_sayisi)
    assert (ilk["dalga_staging"], ilk["dalga_eklenen"]) == (lemma_sayisi, lemma_sayisi)
    assert (ilk["kelime_staging"], ilk["kelime_guncellenen"]) == (kelime_sayisi, kelime_sayisi)
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (1, 0)
    assert say(conn, "SELECT count(*) FROM icerik.root") == kok_sayisi
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE lang = 'ar'") == lemma_sayisi
    assert say(conn, "SELECT count(*) FROM icerik.lemma_dalga") == lemma_sayisi
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE morph_source IS NULL") == 0
    once = anlik(conn)
    assert qac_yukle(qz, conn) == 0
    ikinci = son_sayilar(qz)
    for ad in (
        "kok_eklenen",
        "kok_guncellenen",
        "lemma_eklenen",
        "lemma_guncellenen",
        "dalga_eklenen",
        "dalga_guncellenen",
        "kelime_guncellenen",
        "kaynak_eklenen",
        "kaynak_guncellenen",
    ):
        assert ikinci[ad] == 0, ad
    assert ikinci["kaynak_degismeyen"] == 1
    assert anlik(conn) == once  # tablolar bayt bayt ayni


@pytest.mark.veritabani
def test_lemma_ve_kok_satirlari_onayli_qac_review_acilmaz(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    assert qac_yukle(qz, conn) == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE status <> 'onayli'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE origin IS DISTINCT FROM 'qac'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE source_id <> %s", KAYNAK) == 0
    assert say(conn, "SELECT count(*) FROM icerik.root WHERE source_id <> %s", KAYNAK) == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == 0
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once  # inceleme acilmaz


@pytest.mark.veritabani
def test_bos_dbde_kimlikler_ilk_gecis_sirasiyla(qz: QacZinciri, conn: psycopg.Connection) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    lemma_id = dict(tablo(conn, "SELECT qac_ref, id FROM icerik.lemma"))  # type: ignore[arg-type]
    kok_id = dict(tablo(conn, "SELECT letters_bw, id FROM icerik.root"))  # type: ignore[arg-type]
    for s in qz.staged(KAYNAK, "lemmas.jsonl"):
        assert lemma_id[str(s["qac_ref"])] == s["ilk_gecis"]
    for s in qz.staged(KAYNAK, "roots.jsonl"):
        assert kok_id[str(s["letters_bw"])] == s["ilk_gecis"]


@pytest.mark.veritabani
def test_yeni_kimlik_tablodaki_en_buyuk_kimligin_ustunden_ve_sira_sql_ile_ayni(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    conn.execute(
        "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni)"
        " VALUES ('test-tr-kaynak', 'sozluk', 'Deneme', '1', 'Deneme atif')"
    )
    conn.execute(
        "INSERT INTO icerik.lemma (id, lang, text, text_clean, source_id, data_version)"
        " VALUES (100000, 'tr', 'Deneme', 'deneme', 'test-tr-kaynak', 'x')"
    )
    assert qac_yukle(qz, conn) == 0
    en_kucuk = say(conn, "SELECT min(id) FROM icerik.lemma WHERE lang = 'ar'")
    assert en_kucuk == 100001  # Turkce lemmanin kimligi tabana girer
    ilk_gecis = {
        str(s["qac_ref"]): int(str(s["ilk_gecis"])) for s in qz.staged(KAYNAK, "lemmas.jsonl")
    }
    kimlik = dict(tablo(conn, "SELECT qac_ref, id FROM icerik.lemma WHERE lang = 'ar'"))  # type: ignore[arg-type]
    assert all(kimlik[r] == 100000 + n for r, n in ilk_gecis.items())
    # Python sirasi (veritabani kimlikleriyle) SQL siralamasiyla ayni
    assert tablo(conn, "SELECT lemma_id, sira FROM icerik.lemma_dalga ORDER BY lemma_id") == tablo(
        conn, SIRA_SQL
    )
    assert qac_yukle(qz, conn) == 0
    assert son_sayilar(qz)["lemma_eklenen"] == 0


@pytest.mark.veritabani
def test_lemma_dalga_bos_dbde_staged_sira_ile_ayni_ve_sql_ile_esit(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    staged = {
        str(s["qac_ref"]): (int(str(s["dalga"])), int(str(s["sira"])))
        for s in qz.staged(KAYNAK, "waves.jsonl")
    }
    db = {
        str(ref): (int(d), int(sira))
        for ref, d, sira in conn.execute(  # type: ignore[misc]
            "SELECT l.qac_ref, d.dalga, d.sira FROM icerik.lemma_dalga d"
            " JOIN icerik.lemma l ON l.id = d.lemma_id"
        ).fetchall()
    }
    assert db == staged  # bos DB: kimlikler ilk gecis sirasi -> sira staged ile ayni
    assert tablo(conn, "SELECT lemma_id, sira FROM icerik.lemma_dalga ORDER BY lemma_id") == tablo(
        conn, SIRA_SQL
    )


# --- quran_word --------------------------------------------------------------------------


@pytest.mark.veritabani
def test_tanzil_sutunlari_source_id_ve_data_version_degismez(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    once = tablo(conn, f"SELECT {TANZIL_SUTUNLARI} FROM icerik.quran_word ORDER BY anchor")
    assert qac_yukle(qz, conn) == 0
    assert tablo(conn, f"SELECT {TANZIL_SUTUNLARI} FROM icerik.quran_word ORDER BY anchor") == once
    assert say(conn, "SELECT count(*) FROM icerik.quran_word") == len(once)  # eklenmez, silinmez
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE source_id <> %s", TANZIL) == 0


@pytest.mark.veritabani
def test_lemma_ve_kok_govde_ile_yuzde_yuz_eslesir_ve_features_aynen(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    kelimeler = {str(k["anchor"]): k for k in qz.staged(KAYNAK, "words.jsonl")}
    satirlar = conn.execute(
        "SELECT w.anchor, l.qac_ref, r.letters_bw, w.pos, w.features::text, w.morph_source"
        " FROM icerik.quran_word w LEFT JOIN icerik.lemma l ON l.id = w.lemma_id"
        " LEFT JOIN icerik.root r ON r.id = w.root_id"
    ).fetchall()
    assert len(satirlar) == len(kelimeler)
    for capa, lemma, kok, pos, features, kaynak in satirlar:
        k = kelimeler[str(capa)]
        assert (lemma, kok, pos, kaynak) == (
            k["lemma_qac_ref"],
            k["root_letters_bw"],
            k["pos"],
            KAYNAK,
        )
        assert json.loads(str(features)) == k["features"]  # `govde`/`onek`/`sonek` aynen


@pytest.mark.veritabani
def test_turetilmis_sutunlar_staged_ile_ayni(qz: QacZinciri, conn: psycopg.Connection) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    for s in qz.staged(KAYNAK, "lemmas.jsonl"):
        satir = conn.execute(
            "SELECT occurrences, data_version FROM icerik.lemma WHERE qac_ref = %s", (s["qac_ref"],)
        ).fetchone()
        assert satir == (s["occurrences"], s["data_version"])
    for s in qz.staged(KAYNAK, "roots.jsonl"):
        satir = conn.execute(
            "SELECT occurrences, ayah_count, idf_q::float8, letters FROM icerik.root"
            " WHERE letters_bw = %s",
            (s["letters_bw"],),
        ).fetchone()
        assert satir is not None
        assert (satir[0], satir[1], satir[3]) == (s["occurrences"], s["ayah_count"], s["letters"])
        assert abs(float(satir[2]) - float(str(s["idf_q"]))) < 1e-5  # real (float4) duyarliligi


@pytest.mark.veritabani
def test_kaynak_satiri_dosya_sha256_ve_alinma_tarihi_ham_dosyadan(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    ham = qz.z.veri_kok / "raw" / KAYNAK / TARIH / DOSYA_ADI
    satir = conn.execute(
        "SELECT tur::text, dosya_sha256, alinma_tarihi::text, surum FROM icerik.source"
        " WHERE slug = %s",
        (KAYNAK,),
    ).fetchone()
    assert satir == ("morfoloji", lineage.sha256_dosya(ham), TARIH, "0.4")


@pytest.mark.veritabani
def test_tanzil_yuklemesi_qac_sutunlarini_fark_saymaz_ve_ezmez(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    once = anlik(conn)
    assert ihracat(qz.z, conn, TANZIL) == 0  # 0 fark: QAC sutunlari Tanzil'in isi degil
    sayilar = son_sayilar(qz, TANZIL)
    assert sayilar["kelime_eklenen"] == 0 and sayilar["kelime_degismeyen"] == len(once["kelime"])
    assert anlik(conn) == once


# --- degismezler ve geri alma ------------------------------------------------------------


def _ilk_yukleme_sonra_degistir(qz: QacZinciri, conn: psycopg.Connection, sql: str) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    conn.execute(sql)  # type: ignore[call-overload]


ILK_LEMMA = "WHERE id = (SELECT min(id) FROM icerik.lemma)"
ILK_KOK = "WHERE id = (SELECT min(id) FROM icerik.root)"


@pytest.mark.veritabani
@pytest.mark.parametrize(
    "degisim",
    [
        f"UPDATE icerik.lemma SET text = 'Deneme' {ILK_LEMMA}",
        f"UPDATE icerik.lemma SET text_clean = 'deneme' {ILK_LEMMA}",
        f"UPDATE icerik.lemma SET status = 'red' {ILK_LEMMA}",
        f"UPDATE icerik.lemma SET origin = 'editor' {ILK_LEMMA}",
        f"UPDATE icerik.lemma SET qac_ref = 'degisti-deneme' {ILK_LEMMA}",
        f"UPDATE icerik.root SET letters = 'D E N' {ILK_KOK}",
        f"UPDATE icerik.root SET letters_bw = 'degisti' {ILK_KOK}",
    ],
)
def test_onayli_qac_satirinda_degismez_sutun_degismisse_cikis_1_ve_geri_alinir(
    qz: QacZinciri, conn: psycopg.Connection, degisim: str
) -> None:
    _ilk_yukleme_sonra_degistir(qz, conn, degisim)
    kelime_degisimi = (
        "root_id = NULL, lemma_id = NULL, pos = NULL, features = NULL, morph_source = NULL"
    )
    conn.execute(f"UPDATE icerik.quran_word SET {kelime_degisimi} WHERE anchor = 'q:1:1:1'")  # type: ignore[call-overload]
    once = anlik(conn)
    assert qac_yukle(qz, conn) == 1  # QaKaldi
    assert anlik(conn) == once  # hicbir sey yazilmadi (kelime UPDATE'i dahil)


@pytest.mark.veritabani
def test_turetilmis_sutun_degisince_yalniz_o_sutun_duzelir(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    _ilk_yukleme_sonra_degistir(
        qz,
        conn,
        "UPDATE icerik.lemma SET occurrences = occurrences + 5, data_version = 'eski'"
        " WHERE id = (SELECT min(id) FROM icerik.lemma)",
    )
    conn.execute("UPDATE icerik.root SET ayah_count = 0, idf_q = 0")
    assert qac_yukle(qz, conn) == 0
    sayilar = son_sayilar(qz)
    assert sayilar["lemma_guncellenen"] == 1
    assert sayilar["kok_guncellenen"] == len(qz.staged(KAYNAK, "roots.jsonl"))
    assert sayilar["lemma_eklenen"] == sayilar["kok_eklenen"] == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma WHERE data_version = 'eski'") == 0


@pytest.mark.veritabani
def test_qac_lemmasi_staged_de_yoksa_cikis_1(qz: QacZinciri, conn: psycopg.Connection) -> None:
    _ilk_yukleme_sonra_degistir(
        qz,
        conn,
        "INSERT INTO icerik.lemma (id, lang, text, text_clean, qac_ref, origin, status, source_id,"
        " data_version) VALUES (999999, 'ar', 'Deneme', 'deneme', 'fazla-deneme', 'qac', 'onayli',"
        " 'qac-morfoloji', 'x')",
    )
    once = anlik(conn)
    assert qac_yukle(qz, conn) == 1
    assert anlik(conn) == once


@pytest.mark.veritabani
def test_quran_word_eksikse_cikis_1_ve_hicbir_sey_yazilmaz(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    conn.execute("DELETE FROM icerik.quran_word WHERE anchor = 'q:1:1:1'")
    assert qac_yukle(qz, conn) == 1
    assert say(conn, "SELECT count(*) FROM icerik.root") == 0  # root/lemma ekleri de geri alindi
    assert say(conn, "SELECT count(*) FROM icerik.lemma") == 0
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE morph_source IS NOT NULL") == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0


@pytest.mark.veritabani
def test_quran_word_fazlaysa_ve_baska_morph_source_varsa_cikis_1(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    conn.execute(
        "INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index, text_uthmani, norm,"
        " char_start, char_end, source_id, data_version)"
        " VALUES ('q:1:1:99', 1, 1, 99, 1, 'Deneme', 'deneme', 0, 6, %s, 'x')",
        (TANZIL,),
    )
    assert qac_yukle(qz, conn) == 1
    conn.execute("DELETE FROM icerik.quran_word WHERE anchor = 'q:1:1:99'")
    conn.execute(
        "UPDATE icerik.quran_word SET morph_source = 'tanzil-simple-clean' WHERE anchor = 'q:1:1:1'"
    )
    assert qac_yukle(qz, conn) == 1
    assert say(conn, "SELECT count(*) FROM icerik.root") == 0


@pytest.mark.veritabani
def test_dry_run_hicbir_sey_yazmaz(qz: QacZinciri, conn: psycopg.Connection) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn, dry_run=True) == 0
    assert say(conn, "SELECT count(*) FROM icerik.root") == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma") == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma_dalga") == 0
    assert say(conn, "SELECT count(*) FROM icerik.quran_word WHERE morph_source IS NOT NULL") == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0
    assert son_sayilar(qz)["lemma_eklenen"] > 0  # yazilsaydi


@pytest.mark.veritabani
def test_qa_raporu_yoksa_ya_da_kalmissa_cikis_1(
    ust_veri_zinciri: UstVeriZinciri,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    conn: psycopg.Connection,
) -> None:
    zincir = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    assert zincir.ingest() == 0 and zincir.enrich() == 0  # qa kosulmadi
    tanzil_qa(zincir.z)
    tanzil_yukle(zincir, conn)
    assert qac_yukle(zincir, conn) == 1  # QA raporu yok
    assert say(conn, "SELECT count(*) FROM icerik.root") == 0
    assert zincir.qa() == 0
    assert qac_yukle(zincir, conn) == 0


# --- degismezlerin SQL'i -----------------------------------------------------------------


@pytest.mark.veritabani
def test_lemma_tutarsiz_ve_fatiha_cuz30_dalga_sorgulari(
    qz: QacZinciri, conn: psycopg.Connection
) -> None:
    tanzil_yukle(qz, conn)
    assert qac_yukle(qz, conn) == 0
    manifest = lineage.son_basarili(qz.z.veri_kok / "staged" / KAYNAK, "anchor")
    assert manifest is not None
    cuz = tuple(manifest[2]["ayrintilar"]["cuz30_baslangic"])  # type: ignore[index]
    assert cuz == cuz_baslangici(qz.staged("tanzil-ust-veri", "markers.jsonl"))
    assert conn.execute(pg_qac.FATIHA_CUZ30_DALGA_DISI, cuz).fetchall() == []
    assert conn.execute(pg_qac.LEMMA_TUTARSIZ, (KAYNAK,)).fetchall() == []  # type: ignore[arg-type]
    # olumsuz denetim: Fatiha'daki bir lemmanin dalgasi 4 yapilirsa sorgu onu bulur
    conn.execute(
        "UPDATE icerik.lemma_dalga SET dalga = 4 WHERE lemma_id = (SELECT lemma_id FROM"
        " icerik.quran_word WHERE surah = 1 AND lemma_id IS NOT NULL ORDER BY ayah, word LIMIT 1)"
    )
    assert len(conn.execute(pg_qac.FATIHA_CUZ30_DALGA_DISI, cuz).fetchall()) == 1


def test_hazirla_dosya_onkosulu_zincir_yoksa_girdi_hatasi(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    zincir = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    ctx = zincir.ctx("export", [KAYNAK])
    with pytest.raises(GirdiHatasi):
        pg.hazirla(ctx, KAYNAK, None, ())  # enrich morphology calismamis
    assert ayarlar_kur(zincir.z.tmp).veri_kok == zincir.z.veri_kok
