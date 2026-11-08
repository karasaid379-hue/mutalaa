"""`export pg --source tanzil-ust-veri`: quran_marker ve page_map (A11.6, K-43 madde 3; SENTETIK).

Sentetik ust veri zinciri (`ust_veri_zinciri`) `mutalaa_test` veritabanina yuklenir. Testler dis
islem icinde kosar ve sonunda geri alinir (`test_zincir_pg.py` ile ayni duzen). Veritabani yoksa
atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Hicbir deger hafizadan
yazilmaz; sayilar staged dosyalardan okunur.
"""

import json
import os
from collections.abc import Iterator
from typing import Any

import psycopg
import pytest
from hat_yardimci import ayarlar_kur
from ust_veri_yardimci import UstVeriZinciri
from zincir_yardimci import ortam_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK

DIGER_KAYNAKLAR = ("medine-604-duzen", "quran-meta")


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
        try:
            kalinti = baglanti.execute(
                "SELECT (SELECT count(*) FROM icerik.quran_marker WHERE source_id = %s)"
                " + (SELECT count(*) FROM icerik.page_map WHERE source_id = %s)"
                " + (SELECT count(*) FROM icerik.source WHERE slug = ANY(%s))",
                (KAYNAK, KAYNAK, [KAYNAK, *DIGER_KAYNAKLAR]),
            ).fetchone()
        except psycopg.errors.UndefinedTable:
            baglanti.rollback()
            _yok("mutalaa_test sema eski: quran_marker yok (scripts/test-db.ps1)")
            return
        assert kalinti is not None
        if kalinti[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde tanzil-ust-veri satiri kalmis")
        yield baglanti
    finally:
        baglanti.rollback()
        baglanti.close()


@pytest.fixture
def uz(ust_veri_zinciri: UstVeriZinciri, monkeypatch: pytest.MonkeyPatch) -> UstVeriZinciri:
    ortam_kur(ust_veri_zinciri.z, monkeypatch)
    return ust_veri_zinciri


def yukle(uz: UstVeriZinciri, conn: psycopg.Connection, **kw: object) -> int:
    return pg.komut_export_pg(
        ayarlar_kur(uz.z.tmp),
        depo_kok=uz.z.kok,
        source=KAYNAK,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def son_sayilar(uz: UstVeriZinciri) -> dict[str, int]:
    raporlar = [
        json.loads(yol.read_bytes()) for yol in sorted((uz.z.veri_kok / "reports").glob("*.json"))
    ]
    yuklemeler = [
        r for r in raporlar if r["komut"] == "export pg" and r["parametreler"]["source"] == KAYNAK
    ]
    assert yuklemeler
    sayilar = yuklemeler[-1]["sayilar"]
    assert isinstance(sayilar, dict)
    return sayilar


def say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()  # type: ignore[arg-type]
    assert satir is not None
    return int(satir[0])


def staged(uz: UstVeriZinciri, ad: str) -> list[dict[str, Any]]:
    son = lineage.son_basarili(uz.z.veri_kok / "staged" / KAYNAK, "anchor")
    assert son is not None
    return [json.loads(s) for s in (son[1] / ad).read_bytes().splitlines()]


def isaret_say(conn: psycopg.Connection) -> int:
    return say(conn, "SELECT count(*) FROM icerik.quran_marker WHERE source_id = %s", KAYNAK)


def sayfa_say(conn: psycopg.Connection) -> int:
    return say(conn, "SELECT count(*) FROM icerik.page_map WHERE source_id = %s", KAYNAK)


@pytest.mark.veritabani
def test_ilk_yukleme_sonra_ikinci_kosu_sifir_degisiklik(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    isaretler, sayfalar = staged(uz, "markers.jsonl"), staged(uz, "pages.jsonl")
    review_once = say(conn, "SELECT count(*) FROM icerik.review")
    assert yukle(uz, conn) == 0
    ilk = son_sayilar(uz)
    assert ilk["isaret_staging"] == ilk["isaret_eklenen"] == len(isaretler)
    assert ilk["sayfa_staging"] == ilk["sayfa_eklenen"] == len(sayfalar)
    assert (ilk["isaret_degismeyen"], ilk["sayfa_degismeyen"]) == (0, 0)
    assert (ilk["kaynak_eklenen"], ilk["kaynak_guncellenen"]) == (1, 0)
    assert isaret_say(conn) == len(isaretler)
    assert sayfa_say(conn) == len(sayfalar)
    # yalniz tanzil-ust-veri kaynagi yazilir; dogrulayicilar (QPC1, quran-meta) yuklenmez
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 1
    assert (
        say(conn, "SELECT count(*) FROM icerik.source WHERE slug = ANY(%s)", list(DIGER_KAYNAKLAR))
        == 0
    )
    assert say(conn, "SELECT count(*) FROM icerik.review") == review_once  # review acilmaz

    once = conn.execute("SELECT * FROM icerik.page_map ORDER BY page").fetchall()
    kimlik = conn.execute(
        "SELECT last_value FROM pg_sequences"
        " WHERE schemaname || '.' || sequencename = pg_get_serial_sequence('icerik.page_map', 'id')"
    ).fetchone()
    assert yukle(uz, conn) == 0  # ikinci kosu: hicbir satir degismez
    ikinci = son_sayilar(uz)
    assert (ikinci["isaret_eklenen"], ikinci["sayfa_eklenen"]) == (0, 0)
    assert (ikinci["isaret_degismeyen"], ikinci["sayfa_degismeyen"]) == (
        len(isaretler),
        len(sayfalar),
    )
    assert ikinci["kaynak_degismeyen"] == 1
    assert conn.execute("SELECT * FROM icerik.page_map ORDER BY page").fetchall() == once
    assert (
        conn.execute(
            "SELECT last_value FROM pg_sequences WHERE schemaname || '.' || sequencename ="
            " pg_get_serial_sequence('icerik.page_map', 'id')"
        ).fetchone()
        == kimlik
    )  # IDENTITY harcanmadi


@pytest.mark.veritabani
def test_yuklenen_isaret_ve_sayfa_satirlari_staged_ile_ayni(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(uz, conn) == 0
    for m in staged(uz, "markers.jsonl"):
        satir = conn.execute(
            "SELECT anchor, secde_turu, source_id, data_version FROM icerik.quran_marker"
            " WHERE kind = %s AND no = %s",
            (m["kind"], m["no"]),
        ).fetchone()
        assert satir == (m["anchor"], m["secde_turu"], m["source_id"], m["data_version"])
    sayfalar = staged(uz, "pages.jsonl")
    for p in sayfalar:
        satir = conn.execute(
            "SELECT start_anchor, end_anchor, data_version, volume, line, line_type, centered,"
            " start_offset, end_offset, glyphs FROM icerik.page_map"
            " WHERE source_id = %s AND page = %s",
            (KAYNAK, p["page"]),
        ).fetchone()
        assert satir == (
            p["start_anchor"],
            p["end_anchor"],
            p["data_version"],
            None,
            None,
            None,
            False,
            None,
            None,
            None,
        )
    ozet = conn.execute(
        "SELECT count(*), min(page), max(page) FROM icerik.page_map"
        " WHERE source_id = %s AND line IS NULL",
        (KAYNAK,),
    ).fetchone()
    assert ozet == (len(sayfalar), 1, len(sayfalar))
    turler = conn.execute(
        "SELECT kind, count(*), count(secde_turu) FROM icerik.quran_marker GROUP BY kind"
        " ORDER BY kind"
    ).fetchall()
    beklenen: dict[str, int] = {}
    for m in staged(uz, "markers.jsonl"):
        beklenen[m["kind"]] = beklenen.get(m["kind"], 0) + 1
    assert [(k, n) for k, n, _ in turler] == sorted(beklenen.items())
    assert [e for k, _, e in turler if k != "secde"] == [0] * (len(turler) - 1)
    assert dict((k, e) for k, _, e in turler)["secde"] == beklenen["secde"]


@pytest.mark.veritabani
def test_dry_run_hicbir_satir_yazmaz(uz: UstVeriZinciri, conn: psycopg.Connection) -> None:
    assert yukle(uz, conn, dry_run=True) == 0
    rapor = son_sayilar(uz)
    assert rapor["sayfa_eklenen"] == len(staged(uz, "pages.jsonl"))  # yazilsaydi
    assert (isaret_say(conn), sayfa_say(conn)) == (0, 0)
    assert say(conn, "SELECT count(*) FROM icerik.source WHERE slug = %s", KAYNAK) == 0


@pytest.mark.veritabani
@pytest.mark.parametrize(
    "degisim",
    [
        "end_anchor = 'q:1:1:1'",
        "start_anchor = 'q:1:1:1'",
        "data_version = 'x@0'",
        "centered = true",
    ],
)
def test_degismis_sayfa_satiri_cikis_1_ve_geri_alinir(
    uz: UstVeriZinciri, conn: psycopg.Connection, degisim: str
) -> None:
    assert yukle(uz, conn) == 0
    toplam = sayfa_say(conn)
    conn.execute(f"UPDATE icerik.page_map SET {degisim} WHERE page = 3")  # type: ignore[arg-type]
    conn.execute("DELETE FROM icerik.page_map WHERE page = 4")
    assert yukle(uz, conn) == 1
    assert sayfa_say(conn) == toplam - 1  # eksik satir yeniden eklenmedi: islem geri alindi


@pytest.mark.veritabani
def test_sayfa_satirinin_bos_olmasi_gereken_sutunu_dolarsa_cikis_1(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(uz, conn) == 0
    conn.execute("UPDATE icerik.page_map SET line_type = 'ayet', start_offset = 3 WHERE page = 3")
    assert yukle(uz, conn) == 1


@pytest.mark.veritabani
def test_degismis_isaret_satiri_cikis_1(uz: UstVeriZinciri, conn: psycopg.Connection) -> None:
    assert yukle(uz, conn) == 0
    toplam = isaret_say(conn)
    conn.execute("UPDATE icerik.quran_marker SET anchor = 'q:1:1' WHERE kind = 'cuz' AND no = 2")
    conn.execute("DELETE FROM icerik.quran_marker WHERE kind = 'rub' AND no = 7")
    assert yukle(uz, conn) == 1
    assert isaret_say(conn) == toplam - 1
    secde = conn.execute(
        "SELECT secde_turu FROM icerik.quran_marker WHERE kind = 'secde' AND no = 1"
    ).fetchone()
    assert secde is not None
    etiket = "obligatory" if secde[0] == "recommended" else "recommended"
    conn.execute(
        "UPDATE icerik.quran_marker SET secde_turu = %s WHERE kind = 'secde' AND no = 1", (etiket,)
    )
    assert yukle(uz, conn) == 1


@pytest.mark.veritabani
def test_veritabaninda_olup_staged_de_olmayan_satirlar_cikis_1_ve_silinmez(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(uz, conn) == 0
    sayfalar, isaretler = sayfa_say(conn), isaret_say(conn)
    conn.execute(
        "INSERT INTO icerik.page_map (source_id, page, start_anchor, end_anchor, data_version)"
        " VALUES (%s, 9999, 'q:1:1:1', 'q:1:1:2', 'x@1')",
        (KAYNAK,),
    )
    assert yukle(uz, conn) == 1
    assert sayfa_say(conn) == sayfalar + 1  # fazladan satir silinmedi
    conn.execute("DELETE FROM icerik.page_map WHERE page = 9999")
    conn.execute(
        "INSERT INTO icerik.quran_marker (kind, no, anchor, source_id, data_version)"
        " VALUES ('cuz', 999, 'q:1:1', %s, 'x@1')",
        (KAYNAK,),
    )
    assert yukle(uz, conn) == 1
    assert isaret_say(conn) == isaretler + 1


@pytest.mark.veritabani
def test_satir_duzeyindeki_page_map_satirlari_sayfa_satirini_etkilemez(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    """Kaynaga ait ama `line` dolu bir satir 'sayfa satiri' degildir: staged'de yok sayilir."""
    assert yukle(uz, conn) == 0
    conn.execute(
        "INSERT INTO icerik.page_map (source_id, page, line, start_anchor, end_anchor,"
        " data_version) VALUES (%s, 1, 1, 'q:1:1:1', 'q:1:1:2', 'x@1')",
        (KAYNAK,),
    )
    assert yukle(uz, conn) == 1  # staged'de olmayan, kaynaga ait satir: geri alinir


@pytest.mark.veritabani
def test_basarisiz_yukleme_basarisiz_pipeline_run_satiri_birakir(
    uz: UstVeriZinciri, conn: psycopg.Connection
) -> None:
    assert yukle(uz, conn) == 0
    conn.execute("UPDATE icerik.page_map SET end_anchor = 'q:1:1:1' WHERE page = 5")
    assert yukle(uz, conn) == 1
    durumlar = conn.execute(
        "SELECT durum FROM icerik.pipeline_run WHERE komut = 'export pg' ORDER BY baslangic"
    ).fetchall()
    assert [d[0] for d in durumlar] == ["basarili", "basarisiz"]


def test_qa_raporu_yoksa_ya_da_sayfa_ozeti_tutmuyorsa_cikis_1(
    ust_veri_zinciri: UstVeriZinciri, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Rapor, anchor calismasi ve iki dosya ozetine baglidir; baglanti acilmadan cikis 1."""
    from zincir_yardimci import sablon_kopyala

    kopya = sablon_kopyala(ust_veri_zinciri.z.tmp, tmp_path / "k")
    ortam_kur(kopya, monkeypatch)
    for rapor in (kopya.veri_kok / "reports").glob("*.json"):
        veri = json.loads(rapor.read_bytes())
        if veri.get("komut") == "qa run" and veri.get("kaynak") == KAYNAK:
            veri["sayfalar_sha256"] = "0" * 64
            rapor.write_bytes(json.dumps(veri).encode("utf-8"))

    def baglanti() -> psycopg.Connection:
        raise AssertionError("baglanti acilmamali")

    kod = pg.komut_export_pg(
        ayarlar_kur(kopya.tmp), depo_kok=kopya.kok, source=KAYNAK, baglanti=baglanti
    )
    assert kod == 1


def test_yukleme_sozlesmesi_k43_madde_3() -> None:
    from mutalaa_pipeline.export import pg_yapi

    for sorgu in (pg_yapi.INSERT_ISARET, pg_yapi.INSERT_SAYFA):
        assert "DELETE" not in sorgu.upper() and "UPDATE" not in sorgu.upper()
    assert KAYNAK in pg.YAPI_KAYNAKLARI
    assert pg.EK_KAYNAKLAR[KAYNAK] == ()
