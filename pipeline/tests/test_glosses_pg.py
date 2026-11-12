"""`export pg --source quranwbw-tr`: lemma_gloss adaylari ve review (A17.6; SENTETIK).

Sentetik zincir (Tanzil, QAC ve QuranWBW; "Deneme anlam N" metinleri) `mutalaa_test`
veritabanina yuklenir: Tanzil -> QAC -> QuranWBW. Testler dis islem icinde kosar ve sonunda geri
alinir. Veritabani yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
Yazma kurali: yalniz ekler; onayli, red ve review'u olan lemmaya dokunulmaz. Hicbir anlam metni
hafizadan yazilmaz.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from qac_yardimci import QacZinciri, qac_hazirla
from quranwbw_yardimci import QuranwbwZinciri, ihracat, quranwbw_hazirla, tanzil_qa
from ust_veri_yardimci import UstVeriZinciri

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.glosses import GLOSSES_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi

KAYNAK = "quranwbw-tr"
QAC = "qac-morfoloji"
TANZIL = "tanzil-uthmani"
SLUGLAR = [KAYNAK, QAC, TANZIL, "tanzil-simple-clean"]


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
            " + (SELECT count(*) FROM icerik.lemma_gloss)"
            " + (SELECT count(*) FROM icerik.quran_word)"
            " + (SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'lemma_gloss')"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (SLUGLAR,),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde root/lemma/lemma_gloss/quran_word satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def wz(
    ust_veri_zinciri: UstVeriZinciri, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> QuranwbwZinciri:
    qz: QacZinciri = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    qz.hepsi()
    tanzil_qa(qz.z)
    zincir = quranwbw_hazirla(qz, monkeypatch)
    zincir.hepsi(1)
    return zincir


def onkosul(wz: QuranwbwZinciri, conn: psycopg.Connection) -> None:
    """Tanzil ve QAC yuklenir (lemma ve lemma_dalga satirlari)."""
    assert ihracat(wz.z, conn, TANZIL) == 0
    assert ihracat(wz.z, conn, QAC) == 0


def yukle(wz: QuranwbwZinciri, conn: psycopg.Connection, **kw: object) -> int:
    return ihracat(wz.z, conn, KAYNAK, **kw)


def son_sayilar(wz: QuranwbwZinciri) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes()) for yol in sorted((wz.z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [
        r
        for r in raporlar
        if r.get("komut") == "export pg" and r["parametreler"]["source"] == KAYNAK
    ]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def goruntu(conn: psycopg.Connection) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    gloss = [
        tuple(s)
        for s in conn.execute("SELECT * FROM icerik.lemma_gloss ORDER BY lemma_id").fetchall()
    ]
    review = [tuple(s) for s in conn.execute("SELECT * FROM icerik.review ORDER BY id").fetchall()]
    return gloss, review


def staged_adaylar(wz: QuranwbwZinciri) -> list[dict[str, object]]:
    return wz.staged(KAYNAK, GLOSSES_ADI)


# --- yukleme -----------------------------------------------------------------------------


@pytest.mark.veritabani
def test_ilk_yukleme_aday_ve_review_ikinci_kosu_sifir_degisiklik(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    adaylar = staged_adaylar(wz)
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    assert yukle(wz, conn) == 0
    ilk = son_sayilar(wz)
    assert ilk["gloss_staging"] == ilk["gloss_eklenen"] == ilk["review_eklenen"] == len(adaylar)
    assert (ilk["gloss_degismeyen"], ilk["gloss_mevcut"], ilk["gloss_mevcut_farkli"]) == (0, 0, 0)
    assert ilk["tutarli"] + ilk["tutarsiz"] == len(adaylar)
    assert ilk["tutarsiz"] == sum(1 for a in adaylar if a["tutarsiz_hazir_anlam"])
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == len(adaylar)
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once + len(adaylar)
    once = goruntu(conn)
    assert yukle(wz, conn) == 0
    ikinci = son_sayilar(wz)
    assert (ikinci["gloss_eklenen"], ikinci["review_eklenen"]) == (0, 0)
    assert ikinci["gloss_degismeyen"] == len(adaylar) and ikinci["gloss_mevcut"] == len(adaylar)
    assert goruntu(conn) == once  # tablolar bayt bayt ayni


@pytest.mark.veritabani
def test_gloss_satiri_alanlari_aday_origin_version_content_hash(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss WHERE status <> 'aday'") == 0
    assert (
        say(conn, "SELECT count(*) FROM icerik.lemma_gloss WHERE origin <> 'kaynak:quranwbw-tr'")
        == 0
    )
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss WHERE version <> '1'") == 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.lemma_gloss WHERE content_hash::text <>"
            " encode(sha256(convert_to(anlam_kisa, 'UTF8')), 'hex')",
        )
        == 0
    )
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.lemma_gloss WHERE turkce_es_kelime IS NOT NULL"
            " OR yalnizca_etimolojik OR editor_notu IS NOT NULL",
        )
        == 0
    )
    for a in staged_adaylar(wz):
        satir = conn.execute(
            "SELECT g.anlam_kisa, g.kuran_anlamlari, g.content_hash::text FROM icerik.lemma_gloss g"
            " JOIN icerik.lemma l ON l.id = g.lemma_id WHERE l.qac_ref = %s",
            (a["qac_ref"],),
        ).fetchone()
        assert satir is not None
        assert satir[0] == a["anlam_kisa"] and satir[1] == a["kuran_anlamlari"]
        assert len(satir[1]) <= 3
        assert satir[2] == content_hash(str(a["anlam_kisa"]))


@pytest.mark.veritabani
def test_review_alanlari_onerilen_guven_ve_dalga_sirasi(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    adaylar = {str(a["qac_ref"]): a for a in staged_adaylar(wz)}
    satirlar = conn.execute(
        "SELECT r.hedef_tablo, r.hedef_anahtar, r.alan, r.eylem, r.koken::text, r.oneren,"
        " r.onceki, r.onerilen, r.guven::float8, r.yz_modeli, r.yz_kaydi, r.durum::text,"
        " l.qac_ref, d.dalga, d.sira FROM icerik.review r JOIN icerik.lemma l"
        " ON l.id::text = r.hedef_anahtar JOIN icerik.lemma_dalga d ON d.lemma_id = l.id"
        " WHERE r.hedef_tablo = 'lemma_gloss' ORDER BY r.id"
    ).fetchall()
    assert len(satirlar) == len(adaylar)
    onceki_anahtar = (-1, -1)
    for (
        tablo,
        _,
        alan,
        eylem,
        koken,
        oneren,
        onceki,
        onerilen,
        guven,
        ym,
        yk,
        durum,
        ref,
        d,
        s,
    ) in satirlar:
        a = adaylar[str(ref)]
        assert (tablo, alan, eylem, koken, oneren, onceki, ym, yk, durum) == (
            "lemma_gloss",
            "anlam_kisa",
            "oner",
            "hat",
            "hat",
            None,
            None,
            None,
            "acik",
        )
        assert set(onerilen) == {"anlam_kisa", "dagilim", "baskin_pay"}
        assert onerilen["anlam_kisa"] == a["anlam_kisa"] and onerilen["dagilim"] == a["dagilim"]
        pay = int(str(a["baskin_sayi"])) / int(str(a["toplam"]))
        assert abs(onerilen["baskin_pay"] - pay) < 1e-6 and abs(guven - pay) < 1e-6
        assert (d, s) > onceki_anahtar  # kuyruk dalga ve sira sirasini izler
        onceki_anahtar = (d, s)


@pytest.mark.veritabani
def test_yalniz_secilen_dalgalarin_lemmalari_yuklenir(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.lemma_gloss g JOIN icerik.lemma_dalga d"
            " ON d.lemma_id = g.lemma_id WHERE d.dalga > 1",
        )
        == 0
    )
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == say(
        conn, "SELECT count(*) FROM icerik.lemma_dalga WHERE dalga <= 1"
    )


@pytest.mark.veritabani
def test_kaynak_satiri_yalniz_quranwbw_ve_ham_dosyadan(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    qac_once = conn.execute("SELECT * FROM icerik.source WHERE slug = %s", (QAC,)).fetchone()
    assert yukle(wz, conn) == 0
    satir = conn.execute(
        "SELECT tur::text, dosya_sha256, alinma_tarihi::text, surum FROM icerik.source"
        " WHERE slug = %s",
        (KAYNAK,),
    ).fetchone()
    assert satir is not None and satir[0] == "kelime_anlami" and satir[3] == "v4-version-1"
    assert son_sayilar(wz)["kaynak_eklenen"] == 1
    assert (
        conn.execute("SELECT * FROM icerik.source WHERE slug = %s", (QAC,)).fetchone() == qac_once
    )


# --- var olan satirlara dokunmama --------------------------------------------------------


@pytest.mark.veritabani
@pytest.mark.parametrize("durum", ["onayli", "red"])
def test_onayli_ve_red_gloss_satirina_dokunulmaz(
    wz: QuranwbwZinciri, conn: psycopg.Connection, durum: str
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    conn.execute(
        "UPDATE icerik.lemma_gloss SET status = %s::icerik.xref_status,"
        " anlam_kisa = 'Deneme duzen', origin = 'editor', version = '2', content_hash = %s"
        " WHERE lemma_id = (SELECT min(lemma_id) FROM icerik.lemma_gloss)",
        (durum, content_hash("Deneme duzen")),
    )
    once = goruntu(conn)
    assert yukle(wz, conn) == 0
    sayilar = son_sayilar(wz)
    assert (sayilar["gloss_eklenen"], sayilar["review_eklenen"]) == (0, 0)
    assert sayilar["gloss_korunan"] == 1 and sayilar["gloss_mevcut_farkli"] == 1
    assert goruntu(conn) == once  # editorun degeri, durumu ve review'lari aynen


@pytest.mark.veritabani
def test_review_kaydi_olan_ama_gloss_satiri_olmayan_lemma_atlanir(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    kimlik = say(conn, "SELECT min(lemma_id) FROM icerik.lemma_gloss")
    conn.execute("DELETE FROM icerik.lemma_gloss WHERE lemma_id = %s", (kimlik,))
    once = goruntu(conn)
    assert yukle(wz, conn) == 0
    sayilar = son_sayilar(wz)
    assert (sayilar["gloss_eklenen"], sayilar["review_eklenen"]) == (0, 0)
    assert sayilar["review_nedeniyle_atlanan"] == 1
    assert goruntu(conn) == once


@pytest.mark.veritabani
def test_gloss_ve_review_ikisi_de_silinmisse_yeniden_eklenir(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    assert yukle(wz, conn) == 0
    kimlik = say(conn, "SELECT min(lemma_id) FROM icerik.lemma_gloss")
    conn.execute("DELETE FROM icerik.lemma_gloss WHERE lemma_id = %s", (kimlik,))
    conn.execute(
        "DELETE FROM icerik.review WHERE hedef_tablo = 'lemma_gloss' AND hedef_anahtar = %s",
        (str(kimlik),),
    )
    assert yukle(wz, conn) == 0
    sayilar = son_sayilar(wz)
    assert (sayilar["gloss_eklenen"], sayilar["review_eklenen"]) == (1, 1)
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == len(staged_adaylar(wz))


@pytest.mark.veritabani
def test_baska_tablolarin_review_kayitlarina_dokunulmaz(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    conn.execute(
        "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, koken, oneren)"
        " VALUES ('surah_alias', '1:Deneme', 'status', 'oner', 'hat', 'hat')"
    )
    once = conn.execute("SELECT * FROM icerik.review WHERE hedef_tablo = 'surah_alias'").fetchall()
    assert yukle(wz, conn) == 0
    assert (
        conn.execute("SELECT * FROM icerik.review WHERE hedef_tablo = 'surah_alias'").fetchall()
        == once
    )


# --- onkosullar --------------------------------------------------------------------------


@pytest.mark.veritabani
def test_dry_run_hicbir_sey_yazmaz(wz: QuranwbwZinciri, conn: psycopg.Connection) -> None:
    onkosul(wz, conn)
    once = goruntu(conn)
    assert yukle(wz, conn, dry_run=True) == 0
    assert goruntu(conn) == once
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0
    assert son_sayilar(wz)["gloss_eklenen"] == len(staged_adaylar(wz))  # yazilsaydi


@pytest.mark.veritabani
def test_qac_lemmasi_veritabaninda_yoksa_cikis_2_ve_hicbir_sey_yazilmaz(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    assert ihracat(wz.z, conn, TANZIL) == 0  # QAC yuklenmedi
    assert yukle(wz, conn) == 2
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0


@pytest.mark.veritabani
def test_lemma_dalga_yoksa_cikis_2_dalga_farkliysa_cikis_1(
    wz: QuranwbwZinciri, conn: psycopg.Connection
) -> None:
    onkosul(wz, conn)
    conn.execute(
        "UPDATE icerik.lemma_dalga SET dalga = 4 WHERE lemma_id ="
        " (SELECT min(lemma_id) FROM icerik.lemma_dalga WHERE dalga <= 1)"
    )
    assert yukle(wz, conn) == 1
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == 0
    conn.execute("DELETE FROM icerik.lemma_dalga WHERE dalga = 4")
    assert yukle(wz, conn) == 2
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == 0


@pytest.mark.veritabani
def test_qa_raporu_yoksa_cikis_1(
    ust_veri_zinciri: UstVeriZinciri,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    conn: psycopg.Connection,
) -> None:
    qz = qac_hazirla(ust_veri_zinciri, tmp_path / "t", monkeypatch)
    qz.hepsi()
    tanzil_qa(qz.z)
    zincir = quranwbw_hazirla(qz, monkeypatch)
    assert zincir.ingest() == 0 and zincir.enrich(1) == 0  # qa kosulmadi
    onkosul(zincir, conn)
    assert yukle(zincir, conn) == 1
    assert say(conn, "SELECT count(*) FROM icerik.lemma_gloss") == 0
    assert zincir.qa() == 0
    assert yukle(zincir, conn) == 0
