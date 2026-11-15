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
        min_ornek=kapi.KOK_MIN_REFERANSLI_TAHMIN,
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
    assert s.gate_tur == "benzer_ayet" and s.alt_tur == "sozluksel"


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


def test_onceki_kabul_kok_icin_orneklem_sarti_oncesi_gecti_raporu_sayilmaz(
    tmp_path: Path,
) -> None:
    """kok/tr_lemma: en az 30 referansli tahmin sarti getirilmeden once yazilmis `gecti` rapor
    (alani yok) yeni sarta gore kabul edilmis degildir; gerileme referansi olmaz. Sartli rapor
    olur."""
    eski = _sonuc({"kesinlik": 1.0}, "gecti", "1" * 64)
    eski.min_ornek = None  # sart oncesi bicim: `min_referansli_tahmin` alani yok
    kapi.rapor_yaz(tmp_path, eski, kapi.rapor_govdesi(eski, _an(9), []))
    assert "min_referansli_tahmin" not in kapi.rapor_govdesi(eski, _an(9), [])
    assert kapi.onceki_kabul_edilmis(tmp_path, "kok") is None
    yeni = _sonuc({"kesinlik": 0.97}, "gecti", "2" * 64)
    kapi.rapor_yaz(tmp_path, yeni, kapi.rapor_govdesi(yeni, _an(10), []))
    onceki = kapi.onceki_kabul_edilmis(tmp_path, "kok")
    assert onceki is not None and onceki["min_referansli_tahmin"] == 30
    assert onceki["data_version"] == yeni.data_version
    # baska turler bu sarttan etkilenmez (alan aranmaz)
    lemma = _sonuc({"tutarlilik": 1.0}, "gecti", "3" * 64)
    lemma.cli_tur = "lemma"
    lemma.min_ornek = None
    kapi.rapor_yaz(tmp_path, lemma, kapi.rapor_govdesi(lemma, _an(11), []))
    assert kapi.onceki_kabul_edilmis(tmp_path, "lemma") is not None


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
            alt_tur="",
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
            alt_tur="tr_lemma",
            set_sinifi="silver",
            set_surumu="s",
            sonuc="belki",
            set_kaynaklari=[],
            rapor_sha256=SHA,
            data_version="d",
        )


@pytest.mark.parametrize(
    ("tur", "alt_tur"),
    [
        ("kok", ""),  # kok icin bos alt tur yok
        ("kok", "alim"),
        ("benzer_ayet", ""),
        ("benzer_ayet", "xref"),
        ("lemma", "tr_lemma"),
        ("atif", "sozluksel"),
        ("iktibas", "x"),
    ],
)
def test_xref_gate_yaz_gecersiz_alt_tur_veritabanina_gitmeden_hata(tur: str, alt_tur: str) -> None:
    with pytest.raises(GirdiHatasi, match="alt tur"):
        kapi.xref_gate_yaz(
            None,  # type: ignore[arg-type]
            tur=tur,
            alt_tur=alt_tur,
            set_sinifi="silver",
            set_surumu="s",
            sonuc="gecti",
            set_kaynaklari=[],
            rapor_sha256=SHA,
            data_version="d",
        )


def test_cli_gate_esleme_veritabani_check_ile_ayni() -> None:
    assert kapi.CLI_GATE["kok"] == ("kok", "tr_lemma")
    assert kapi.CLI_GATE["kok-baglanti"] == ("kok", "xref")
    assert kapi.CLI_GATE["benzer-ayet"] == ("benzer_ayet", "sozluksel")
    assert kapi.CLI_GATE["benzer-ayet-alim"] == ("benzer_ayet", "alim")
    for ad in ("lemma", "atif", "iktibas"):
        assert kapi.CLI_GATE[ad] == (ad, "")
    for tur, alt in kapi.CLI_GATE.values():
        assert alt in kapi.ALT_TURLER[tur]
    assert tuple(kapi.CLI_GATE) == kapi.CLI_TURLERI


def test_tur_sonucu_alt_tur() -> None:
    s = _sonuc()
    assert (s.gate_tur, s.alt_tur) == ("kok", "tr_lemma")
    s.cli_tur = "benzer-ayet-alim"
    assert (s.gate_tur, s.alt_tur) == ("benzer_ayet", "alim")
    govde = kapi.rapor_govdesi(s, _an(10), [])
    assert govde["xref_gate_tur"] == "benzer_ayet" and govde["xref_gate_alt_tur"] == "alim"


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
        "alt_tur": "tr_lemma",
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
        "SELECT tur::text, alt_tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256,"
        " data_version, olculdu_at IS NOT NULL FROM icerik.xref_gate"
    ).fetchall()
    assert satir == [
        (
            "kok",
            "tr_lemma",
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
    ]  # ayni (tur, alt_tur, set_sinifi): tek satir


def test_xref_gate_pk_tur_alt_tur_ve_set_sinifi(conn: psycopg.Connection) -> None:
    _gate(conn, set_sinifi="silver")
    _gate(conn, set_sinifi="sentetik")
    _gate(conn, tur="iktibas", alt_tur="", set_sinifi="sentetik", sonuc="gecti")
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


def test_xref_gate_alt_tur_ayri_satir_ve_upsert_yalniz_kendi_satirini_gunceller(
    conn: psycopg.Connection,
) -> None:
    """(tur, alt_tur, set_sinifi) anahtari: kok/benzer_ayet alt turleri ayri satirdir."""
    _gate(conn, tur="kok", alt_tur="tr_lemma", set_sinifi="silver", sonuc="kaldi")
    _gate(conn, tur="kok", alt_tur="xref", set_sinifi="altin", sonuc="gecti")
    _gate(conn, tur="benzer_ayet", alt_tur="sozluksel", set_sinifi="altin", sonuc="kaldi")
    _gate(conn, tur="benzer_ayet", alt_tur="alim", set_sinifi="altin", sonuc="gecti")
    _gate(conn, tur="lemma", alt_tur="", set_sinifi="altin", sonuc="gecti")
    # ayni anahtarla ikinci yazim guncelleme: (benzer_ayet, alim, altin) kaldi olur, digerleri durur
    _gate(conn, tur="benzer_ayet", alt_tur="alim", set_sinifi="altin", sonuc="kaldi")
    satirlar = conn.execute(
        "SELECT tur::text, alt_tur, set_sinifi, sonuc FROM icerik.xref_gate ORDER BY 1, 2, 3"
    ).fetchall()
    assert satirlar == [
        ("benzer_ayet", "alim", "altin", "kaldi"),
        ("benzer_ayet", "sozluksel", "altin", "kaldi"),
        ("kok", "tr_lemma", "silver", "kaldi"),
        ("kok", "xref", "altin", "gecti"),
        ("lemma", "", "altin", "gecti"),
    ]


def test_xref_gate_alt_tur_check_ihlali(conn: psycopg.Connection) -> None:
    """Veritabani CHECK'i: kok icin '' ya da 'alim', benzer_ayet icin '' ya da 'xref', lemma icin
    'tr_lemma' reddedilir (Python dogrulamasi atlanarak dogrudan SQL ile)."""
    for tur, alt in (
        ("kok", ""),
        ("kok", "alim"),
        ("benzer_ayet", ""),
        ("benzer_ayet", "xref"),
        ("lemma", "tr_lemma"),
        ("atif", "sozluksel"),
    ):
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                kapi.UPSERT,
                (tur, alt, "silver", "s", "gecti", [], SHA, "d"),
            )
        conn.rollback()


def test_xref_gate_alt_tur_bos_olmayan_not_null(conn: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.NotNullViolation):
        conn.execute(kapi.UPSERT, ("kok", None, "silver", "s", "gecti", [], SHA, "d"))
    conn.rollback()
