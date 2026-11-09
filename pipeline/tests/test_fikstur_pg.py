# ruff: noqa: RUF001
"""`export pg` sentetik fiksturler: test-kucuk, test-tefsir-ornek, test-ses (A13.6; SENTETIK).

Zincir gercek komutlarla `tmp_path` veri kokunde kosar; yukleme `mutalaa_test` veritabanina yapilir.
Testler dis islem icinde kosar ve sonunda geri alinir (`test_export_pg.py` ile ayni duzen); sentetik
kaynaklar kalici olarak veritabaninda kalmaz. Veritabani yoksa atlanir
(`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from test_fikstur import SAYILAR, komut, zincir_kos

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku

SLUGLAR = ("test-kucuk", "test-tefsir-ornek", "test-ses")


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def veri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    kok = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(kok))
    return kok


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
            "SELECT (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (list(SLUGLAR), list(SLUGLAR)),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde fikstur kaynagi kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


def yukle(tmp_path: Path, conn: psycopg.Connection, slug: str, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(tmp_path),
        depo_kok=depo_koku(),
        source=slug,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(veri: Path) -> dict[str, int]:
    raporlar = [json.loads(p.read_bytes()) for p in sorted((veri / "reports").glob("*.json"))]
    export = [r for r in raporlar if r["komut"] == "export pg"]
    assert export
    return export[-1]["sayilar"]  # type: ignore[no-any-return]


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


@pytest.mark.veritabani
def test_kitap_yuklenir_taslak_ve_arama_sutunlariyla(
    tmp_path: Path, veri: Path, conn: psycopg.Connection
) -> None:
    zincir_kos("test-kucuk")
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    assert yukle(tmp_path, conn, "test-kucuk") == 0
    s = son_sayilar(veri)
    assert (s["staging"], s["eklenen"], s["guncellenen"], s["degismeyen"]) == (12, 12, 0, 0)
    assert (s["kaynak_eklenen"], s["korunan"]) == (1, 0)
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'test-kucuk'") == 12
    satir = conn.execute(
        "SELECT kind::text, metin_durumu::text, status::text, role, parent_path, ord,"
        " ayah_range, ar_norm, tr_wide, rev, left(metin, 19), run_id::text"
        " FROM icerik.unit WHERE anchor = 'k:test-kucuk:bolum-1:p3'"
    ).fetchone()
    assert satir is not None
    assert satir[:6] == ("kitap", "taslak", "etkin", "govde", "k:test-kucuk:bolum-1", 3)
    assert satir[6] is None  # kitap ayete bagli degil
    assert satir[7] is None  # ar_norm bos
    assert "isik" in str(satir[8]).split(" ")
    assert satir[9] == 1
    assert satir[10] == "Deneme paragrafı 3 "
    assert satir[11] is not None
    kaynak = conn.execute(
        "SELECT tur::text, surum, atif_metni, notice_text, alinma_tarihi, dosya_sha256"
        " FROM icerik.source WHERE slug = 'test-kucuk'"
    ).fetchone()
    assert kaynak == ("kitap", "1", "Sentetik test verisi (Mütâlaa).", None, None, None)
    # Sentetik birim icin editore anlamsiz review satiri acilmaz.
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once
    # Ikinci kosu: ayni icerik, sifir degisiklik.
    assert yukle(tmp_path, conn, "test-kucuk", force=True) == 0
    ikinci = son_sayilar(veri)
    assert (ikinci["eklenen"], ikinci["guncellenen"], ikinci["degismeyen"]) == (0, 0, 12)
    assert (ikinci["kaynak_eklenen"], ikinci["kaynak_degismeyen"]) == (0, 1)


@pytest.mark.veritabani
def test_tefsir_ayah_range_yari_acik(tmp_path: Path, veri: Path, conn: psycopg.Connection) -> None:
    zincir_kos("test-tefsir-ornek")
    assert yukle(tmp_path, conn, "test-tefsir-ornek") == 0
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'test-tefsir-ornek'") == 7
    sorgu = (
        "SELECT lower(ayah_range), upper(ayah_range), kind::text, metin_durumu::text,"
        " parent_path FROM icerik.unit WHERE anchor = %s"
    )
    assert conn.execute(sorgu, ("tf:test-ornek:2-255-257:p1",)).fetchone() == (
        262,
        265,
        "tefsir",
        "taslak",
        None,
    )
    assert conn.execute(sorgu, ("tf:test-ornek:1-1-7:p2",)).fetchone() is not None
    # 2:255 icin "ayah_range @> 262" sorgusu fikstur tefsirini bulur
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE ayah_range @> 262 AND source_id = %s",
            "test-tefsir-ornek",
        )
        == 3
    )


@pytest.mark.veritabani
def test_test_ses_yalniz_kaynak_satiri(
    tmp_path: Path, veri: Path, conn: psycopg.Connection
) -> None:
    """Zincir, anchor calistirmasi ve QA raporu olmadan: yalniz `source` satiri."""
    assert yukle(tmp_path, conn, "test-ses") == 0
    s = son_sayilar(veri)
    assert s == {"kaynak_eklenen": 1, "kaynak_guncellenen": 0, "kaynak_degismeyen": 0}
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = 'test-ses'") == 1
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'test-ses'") == 0
    assert say(conn, "SELECT tur::text = 'ses' FROM icerik.source WHERE slug = 'test-ses'") == 1
    manifest = conn.execute(
        "SELECT manifest FROM icerik.pipeline_run WHERE komut = 'export pg' ORDER BY baslangic DESC"
    ).fetchone()
    assert manifest is not None
    assert manifest[0]["yalniz_kaynak"] is True
    # Tekrar: degisiklik yok
    assert yukle(tmp_path, conn, "test-ses") == 0
    assert son_sayilar(veri)["kaynak_degismeyen"] == 1
    # --run anlamsiz
    assert yukle(tmp_path, conn, "test-ses", run="00000000-0000-7000-8000-000000000000") == 2


@pytest.mark.veritabani
def test_dry_run_hicbir_satir_yazmaz(tmp_path: Path, veri: Path, conn: psycopg.Connection) -> None:
    zincir_kos("test-kucuk")
    assert yukle(tmp_path, conn, "test-kucuk", dry_run=True) == 0
    assert son_sayilar(veri)["eklenen"] == 12
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'test-kucuk'") == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = 'test-kucuk'") == 0
    assert yukle(tmp_path, conn, "test-ses", dry_run=True) == 0
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = 'test-ses'") == 0


@pytest.mark.veritabani
def test_turetilmis_sutun_guncellenir_taslak_olmayana_dokunulmaz(
    tmp_path: Path, veri: Path, conn: psycopg.Connection
) -> None:
    zincir_kos("test-kucuk")
    assert yukle(tmp_path, conn, "test-kucuk") == 0
    bozuk, onayli = "k:test-kucuk:bolum-1:p1", "k:test-kucuk:bolum-1:p2"
    for capa in (bozuk, onayli):
        conn.execute("UPDATE icerik.unit SET tr_wide = 'elle bozuldu' WHERE anchor = %s", (capa,))
    conn.execute(
        "UPDATE icerik.unit SET metin_durumu = 'onayli', attrs = '{\"not\": 1}' WHERE anchor = %s",
        (onayli,),
    )
    assert yukle(tmp_path, conn, "test-kucuk") == 0
    s = son_sayilar(veri)
    assert (s["guncellenen"], s["korunan"], s["eklenen"]) == (1, 1, 0)
    wide = dict(
        conn.execute(
            "SELECT anchor, tr_wide FROM icerik.unit WHERE anchor = ANY(%s)", ([bozuk, onayli],)
        ).fetchall()
    )
    assert wide[bozuk] != "elle bozuldu"  # turetilmis sutun yeniden uretildi
    assert wide[onayli] == "elle bozuldu"  # insan kararina (onayli) dokunulmadi
    assert (
        say(
            conn,
            "SELECT count(*) FROM icerik.unit WHERE anchor = %s AND attrs = '{\"not\": 1}'",
            onayli,
        )
        == 1
    )


@pytest.mark.veritabani
def test_metin_farki_islemi_geri_alir_cikis_1(
    tmp_path: Path, veri: Path, conn: psycopg.Connection
) -> None:
    zincir_kos("test-kucuk")
    assert yukle(tmp_path, conn, "test-kucuk") == 0
    capa = "k:test-kucuk:bolum-2:p4"
    conn.execute("UPDATE icerik.unit SET metin = metin || ' (elle)' WHERE anchor = %s", (capa,))
    assert yukle(tmp_path, conn, "test-kucuk") == 1
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE metin LIKE %s", "% (elle)") == 1


@pytest.mark.veritabani
def test_baska_kaynagin_capasi_cikis_2(
    tmp_path: Path, veri: Path, conn: psycopg.Connection
) -> None:
    zincir_kos("test-kucuk")
    assert yukle(tmp_path, conn, "test-ses") == 0  # test-ses source satiri var
    metin = "Deneme"
    conn.execute(
        "INSERT INTO icerik.unit (anchor, kind, source_id, ord, metin, content_hash, data_version)"
        " VALUES ('k:test-kucuk:bolum-1:p1', 'kitap', 'test-ses', 1, %s,"
        " encode(sha256(convert_to(%s, 'UTF8')), 'hex'), 'x')",
        (metin, metin),
    )
    assert yukle(tmp_path, conn, "test-kucuk") == 2


@pytest.mark.veritabani
def test_qa_raporu_yoksa_cikis_1(tmp_path: Path, veri: Path, conn: psycopg.Connection) -> None:
    for adim in (["ingest", "fikstur"], ["normalize"], ["anchor"]):
        assert komut(*adim, "--source", "test-kucuk").exit_code == 0
    assert yukle(tmp_path, conn, "test-kucuk") == 1
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = 'test-kucuk'") == 0


def test_ek_kaynaklar_kumeleri_tutarli() -> None:
    for slug in SLUGLAR:
        assert pg.EK_KAYNAKLAR[slug] == ()
    assert {"test-kucuk", "test-tefsir-ornek"} == pg.FIKSTUR_KAYNAKLARI
    assert {"test-ses"} == pg.YALNIZ_KAYNAK_KAYNAKLARI
    assert not pg.FIKSTUR_KAYNAKLARI & pg.YALNIZ_KAYNAK_KAYNAKLARI
    assert set(SAYILAR) == pg.FIKSTUR_KAYNAKLARI


def test_export_pg_zincirsiz_fikstur_cikis_1_ya_da_2(tmp_path: Path, veri: Path) -> None:
    """Anchor calistirmasi yoksa veritabani acilmadan cikis 2 (dosya onkosulu)."""

    def acilmaz() -> psycopg.Connection:
        raise AssertionError("baglanti acilmamali")

    kod = pg.komut_export_pg(
        ayarlar_kur(tmp_path), depo_kok=depo_koku(), source="test-kucuk", baglanti=acilmaz
    )
    assert kod == 2
