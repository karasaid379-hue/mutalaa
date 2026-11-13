"""`qa/gold/kapi.py`: rapor, onceki kabul edilmis kosu ve `xref_gate` upsert (A18.5; SENTETIK).

PG testleri `mutalaa_test` veritabanina dis islemde yazar ve sonunda geri alir; veritabani yoksa
atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir).
"""

import os
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest

from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import kapi
from mutalaa_pipeline.qa.gold.kapi import TurSonucu

SHA = "a" * 64


def _manifest(sinif: str = "silver") -> dict[str, object]:
    return {
        "set": "kok",
        "surum": "2026-11-13-0123abcd",
        "sinif": sinif,
        "olcum_turu": "dogruluk",
        "ornek_sayisi": 10,
        "kaynak": [
            {"source_id": "kaynak-b", "surum": "1", "madde": "m", "rol": "kanit"},
            {"source_id": "kaynak-a", "surum": "1", "madde": "m", "rol": "kanit"},
        ],
        "dogrulama_yontemi": "sentetik",
        "uretim_komutu": "komut",
    }


def _sonuc(
    olculer: dict[str, float] | None = None, sonuc: str = "gecti", ozet: str = "f" * 64
) -> TurSonucu:
    return TurSonucu(
        cli_tur="kok",
        manifest=_manifest(),
        sonuc=sonuc,
        olculer=olculer or {"kesinlik": 0.96, "duyarlilik": 0.85},
        esikler={"kesinlik": 0.95, "duyarlilik": 0.80},
        esik_sonuclari={"kesinlik": True, "duyarlilik": True},
        tahmin_ozeti=ozet,
        olculen_ornek=6,
        notlar=["not"],
        uretim_kaynaklari=["kaynak-z"],
    )


def _an(saat: int) -> datetime:
    return datetime(2026, 11, 13, saat, 0, 0, tzinfo=UTC)


def test_data_version_ve_rapor_yolu(tmp_path: Path) -> None:
    s = _sonuc()
    assert s.data_version == "gold1-2026-11-13-0123abcd-ffffffff"
    assert s.gate_tur == "kok" and s.set_sinifi == "silver"
    assert s.set_kaynaklari() == ["kaynak-a", "kaynak-b"]
    yol = kapi.rapor_yolu(tmp_path, s.data_version, "kok")
    assert yol.name == "gold1-2026-11-13-0123abcd-ffffffff-gold-kok.json"
    assert yol.parent == tmp_path / "reports"


def test_gate_tur_tire_altcizgi() -> None:
    s = _sonuc()
    s.cli_tur = "benzer-ayet"
    assert s.gate_tur == "benzer_ayet"


def test_rapor_yaz_oku_sha_ve_icerik_alanlari(tmp_path: Path) -> None:
    s = _sonuc()
    govde = kapi.rapor_govdesi(s, _an(10), [])
    yol, ozet = kapi.rapor_yaz(tmp_path, s, govde)
    rapor = kapi.rapor_oku(yol)
    assert rapor["rapor_sha256"] == ozet and len(ozet) == 64
    for alan in (
        "tur",
        "set_surumu",
        "sinif",
        "ornek_sayisi",
        "olculer",
        "esik",
        "sonuc",
        "referans_kapsami",
        "set_kaynaklari",
        "olculdu_utc",
        "data_version",
    ):
        assert alan in rapor
    assert rapor["tur"] == "kok" and rapor["sinif"] == "silver" and rapor["ornek_sayisi"] == 10
    assert rapor["olculdu_utc"] == "2026-11-13T10:00:00.000Z"


def test_rapor_bozulursa_hata(tmp_path: Path) -> None:
    s = _sonuc()
    yol, _ = kapi.rapor_yaz(tmp_path, s, kapi.rapor_govdesi(s, _an(10), []))
    yol.write_bytes(yol.read_bytes().replace(b"0.96", b"0.99"))
    with pytest.raises(GirdiHatasi, match="ozet"):
        kapi.rapor_oku(yol)


def test_onceki_kabul_yalniz_gecti_ve_en_son(tmp_path: Path) -> None:
    assert kapi.onceki_kabul_edilmis(tmp_path, "kok") is None  # ilk kosu
    a = _sonuc({"kesinlik": 0.96, "duyarlilik": 0.85}, "gecti", "1" * 64)
    b = _sonuc({"kesinlik": 0.97, "duyarlilik": 0.86}, "gecti", "2" * 64)
    c = _sonuc({"kesinlik": 0.50, "duyarlilik": 0.10}, "kaldi", "3" * 64)
    for s, saat in ((a, 9), (b, 11), (c, 12)):
        kapi.rapor_yaz(tmp_path, s, kapi.rapor_govdesi(s, _an(saat), []))
    onceki = kapi.onceki_kabul_edilmis(tmp_path, "kok")
    assert onceki is not None and onceki["data_version"] == b.data_version  # kaldi sayilmaz
    assert kapi.onceki_olculer(onceki) == {"duyarlilik": 0.86, "kesinlik": 0.97}
    assert kapi.onceki_kabul_edilmis(tmp_path, "lemma") is None  # baska tur
    assert kapi.onceki_olculer(None) is None


def test_onceki_kabul_bozuk_rapor_sessizce_atlanmaz(tmp_path: Path) -> None:
    s = _sonuc()
    yol, _ = kapi.rapor_yaz(tmp_path, s, kapi.rapor_govdesi(s, _an(9), []))
    yol.write_bytes(b"{}")
    with pytest.raises(GirdiHatasi):
        kapi.onceki_kabul_edilmis(tmp_path, "kok")


def test_tahmin_ozeti_sira_ve_icerige_duyarli() -> None:
    assert kapi.tahmin_ozeti(["a", "b"]) == kapi.tahmin_ozeti(["a", "b"])
    assert kapi.tahmin_ozeti(["a", "b"]) != kapi.tahmin_ozeti(["b", "a"])
    assert len(kapi.tahmin_ozeti([])) == 64


def test_xref_gate_yaz_gecersiz_girdi_veritabanina_gitmeden_hata() -> None:
    with pytest.raises(GirdiHatasi, match="tur"):
        kapi.xref_gate_yaz(
            None,  # type: ignore[arg-type]
            tur="anlamsal",
            set_sinifi="silver",
            set_surumu="s",
            sonuc="gecti",
            set_kaynaklari=[],
            rapor_sha256=SHA,
            data_version="d",
        )
    with pytest.raises(GirdiHatasi, match="sonuc"):
        kapi.xref_gate_yaz(
            None,  # type: ignore[arg-type]
            tur="kok",
            set_sinifi="silver",
            set_surumu="s",
            sonuc="belki",
            set_kaynaklari=[],
            rapor_sha256=SHA,
            data_version="d",
        )


# --- PG: xref_gate upsert ------------------------------------------------------------------------


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(neden)
    pytest.skip(neden)


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    try:
        baglanti = baglan(Ayarlar(), test=True)
    except GirdiHatasi as hata:
        _yok(f"test veritabani yok: {hata}")
        return
    try:
        satir = baglanti.execute("SELECT count(*) FROM icerik.xref_gate").fetchone()
        assert satir is not None
        if satir[0] != 0:
            baglanti.rollback()
            _yok("mutalaa_test icinde xref_gate satiri kalmis")
        yield baglanti
    except psycopg.errors.UndefinedTable:
        baglanti.rollback()
        _yok("xref_gate tablosu yok (goc uygulanmamis)")
    finally:
        baglanti.rollback()
        baglanti.close()


def _gate(conn: psycopg.Connection, **kw: object) -> None:
    arg: dict[str, object] = {
        "tur": "kok",
        "set_sinifi": "silver",
        "set_surumu": "2026-11-13-0123abcd",
        "sonuc": "kaldi",
        "set_kaynaklari": ["kaynak-a", "kaynak-b"],
        "rapor_sha256": SHA,
        "data_version": "gold1-x",
    }
    arg.update(kw)
    kapi.xref_gate_yaz(conn, **arg)  # type: ignore[arg-type]


def test_xref_gate_upsert_ekler_sonra_gunceller(conn: psycopg.Connection) -> None:
    _gate(conn)
    satir = conn.execute(
        "SELECT tur::text, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256,"
        " data_version, olculdu_at IS NOT NULL FROM icerik.xref_gate"
    ).fetchall()
    assert satir == [
        (
            "kok",
            "silver",
            "2026-11-13-0123abcd",
            "kaldi",
            ["kaynak-a", "kaynak-b"],
            SHA,
            "gold1-x",
            True,
        )
    ]
    _gate(conn, sonuc="gecti", set_surumu="2026-11-14-ffffffff", rapor_sha256="b" * 64)
    sonra = conn.execute("SELECT sonuc, set_surumu, rapor_sha256 FROM icerik.xref_gate").fetchall()
    assert sonra == [
        ("gecti", "2026-11-14-ffffffff", "b" * 64)
    ]  # ayni (tur, set_sinifi): tek satir


def test_xref_gate_pk_tur_ve_set_sinifi(conn: psycopg.Connection) -> None:
    _gate(conn, set_sinifi="silver")
    _gate(conn, set_sinifi="sentetik")
    _gate(conn, tur="iktibas", set_sinifi="sentetik", sonuc="gecti")
    sayi = conn.execute("SELECT count(*) FROM icerik.xref_gate").fetchone()
    assert sayi is not None and sayi[0] == 3
    sentetik = conn.execute(
        "SELECT tur::text, sonuc FROM icerik.xref_gate WHERE set_sinifi = 'sentetik' ORDER BY 1"
    ).fetchall()
    assert sentetik == [("iktibas", "gecti"), ("kok", "kaldi")]


def test_xref_gate_check_kisitlari(conn: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        _gate(conn, set_sinifi="gumus")
    conn.rollback()
    with pytest.raises(psycopg.errors.CheckViolation):
        _gate(conn, rapor_sha256="XYZ")
    conn.rollback()
