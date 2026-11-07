"""Zincirden PostgreSQL'e: ingest x2 -> normalize -> anchor -> qa -> `export pg` (A10.4; SENTETIK).

6.236 ayetlik sentetik zincir (`tam_sablon`, gercek komutlarla kurulur) `mutalaa_test` veritabanina
yuklenir. Testler dis islem icinde kosar ve sonunda geri alinir (`test_export_pg.py` ile ayni
duzen). Sentetik Uthmani metni bilerek NFC degildir: yuklenen birimlerden dosya yeniden
kurulunca ham dosyayla bayt bayt ayni olmali (K-26). Gercek Kur'an metni testte yoktur.
"""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from zincir_yardimci import Zincir, ortam_kur, sablon_kopyala

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.run import komut_qa_run

TANZIL_KAYNAKLARI = (KAYNAK, EK_KAYNAK)


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """Test veritabanina baglanir (dis islem, sonunda geri alinir); Tanzil satiri kalmissa atlar."""
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        kalinti = baglanti.execute(
            "SELECT (SELECT count(*) FROM icerik.unit WHERE source_id = ANY(%s))"
            " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
            (list(TANZIL_KAYNAKLARI), list(TANZIL_KAYNAKLARI)),
        ).fetchone()
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde Tanzil kaynagi ya da birimi kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def z(tam_sablon: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Zincir:
    zincir = sablon_kopyala(tam_sablon, tmp_path / "t")
    ortam_kur(zincir, monkeypatch)
    kod = komut_qa_run(source=KAYNAK, run=None, gate=None, config=None, kok=zincir.kok)
    assert kod == 0
    return zincir


def yukle(z: Zincir, conn: psycopg.Connection, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(z.tmp),
        depo_kok=z.kok,
        source=KAYNAK,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(z: Zincir) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes()) for yol in sorted((z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [r for r in raporlar if r["komut"] == "export pg"]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


@pytest.mark.veritabani
def test_zincirden_ilk_yukleme_sonra_ikinci_kosu_sifir_degisiklik(
    z: Zincir, conn: psycopg.Connection
) -> None:
    assert yukle(z, conn) == 0
    ilk = son_sayilar(z)
    assert (ilk["staging"], ilk["eklenen"], ilk["guncellenen"], ilk["degismeyen"]) == (
        6236,
        6236,
        0,
        0,
    )
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (2, 0)
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", KAYNAK) == 6236
    assert say(conn, "SELECT count(*) FROM icerik.unit") == 6236
    assert (
        say(conn, "SELECT count(*) FROM icerik.source WHERE slug = ANY(%s)", [*TANZIL_KAYNAKLARI])
        == 2
    )
    bozuk = say(
        conn,
        "SELECT count(*) FROM icerik.unit WHERE source_id = %s"
        " AND content_hash <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')",
        KAYNAK,
    )
    assert bozuk == 0

    assert yukle(z, conn) == 0  # ikinci kosu: hicbir satir degismez
    ikinci = son_sayilar(z)
    assert (ikinci["eklenen"], ikinci["guncellenen"], ikinci["degismeyen"]) == (0, 0, 6236)
    assert (ikinci["kaynak_eklenen"], ikinci["kaynak_guncellenen"]) == (0, 0)
    assert ikinci["kaynak_degismeyen"] == 2
    assert say(conn, "SELECT count(*) FROM icerik.pipeline_run WHERE komut = 'export pg'") == 2


@pytest.mark.veritabani
def test_yuklenen_birimlerden_dosya_bayt_bayt_yeniden_kurulur(
    z: Zincir, conn: psycopg.Connection
) -> None:
    """K-26 dairesi: ham dosya -> PostgreSQL -> dosya; NFC olmayan metin de aynen kalir."""
    assert yukle(z, conn) == 0
    satirlar = conn.execute(
        "SELECT anchor, metin, ord FROM icerik.unit WHERE source_id = %s ORDER BY ord", (KAYNAK,)
    ).fetchall()
    bildirim = conn.execute(
        "SELECT notice_text FROM icerik.source WHERE slug = %s", (KAYNAK,)
    ).fetchone()
    assert bildirim is not None
    govde = b""
    for sira, (capa, metin, ord_) in enumerate(satirlar, start=1):
        _, sure, ayet = capa.split(":")
        assert ord_ == sira
        govde += f"{sure}|{ayet}|{metin}\n".encode()
    yeniden = govde + bildirim[0].encode("utf-8")
    assert lineage.sha256_bayt(yeniden) == lineage.sha256_bayt(z.veriler["uthmani"])
    assert yeniden == z.veriler["uthmani"]


@pytest.mark.veritabani
def test_ar_norm_provenance_ve_surum_yuklenir(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn) == 0
    satir = conn.execute(
        "SELECT ar_norm, data_version, provenance->'ar_norm'->>'kaynak',"
        " (provenance->'ar_norm'->>'ar4')::boolean, kind::text, metin_durumu::text,"
        " lower(ayah_range), upper(ayah_range) FROM icerik.unit WHERE anchor = 'q:2:255'"
    ).fetchone()
    assert satir is not None
    assert satir[0] and satir[0].strip() != ""
    assert satir[1:6] == ("tanzil-uthmani@1.1", EK_KAYNAK, True, "ayet", "onayli")
    assert satir[6:] == (262, 263)  # 2:255 kuresel sira 7 + 255
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE ar_norm IS NULL OR ar_norm = ''") == 0


@pytest.mark.veritabani
def test_dry_run_veritabanina_hicbir_sey_yazmaz(z: Zincir, conn: psycopg.Connection) -> None:
    assert yukle(z, conn, dry_run=True) == 0
    rapor = son_sayilar(z)
    assert (rapor["eklenen"], rapor["kaynak_eklenen"]) == (6236, 2)  # yazilsaydi
    assert say(conn, "SELECT count(*) FROM icerik.unit WHERE source_id = %s", KAYNAK) == 0
    assert (
        say(conn, "SELECT count(*) FROM icerik.source WHERE slug = ANY(%s)", [*TANZIL_KAYNAKLARI])
        == 0
    )
