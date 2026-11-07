"""`staged`: units.jsonl okuma ve yazma (SENTETIK veri)."""

import json
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur, depo_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.base import StagedUnit, units_satiri
from mutalaa_pipeline.staged import (
    UNITS_ADI,
    Satir,
    satir_baytlari,
    satirlari_oku,
    units_baytlari,
    units_yaz,
)

BEH, FETHA = chr(0x0628), chr(0x064E)  # sentetik harf ve hareke (kaynak ASCII kalir)


def satir(capa: str, **ek: object) -> dict[str, object]:
    kayit: dict[str, object] = {"anchor": capa, "text": f"Deneme {capa}", "n": 1}
    kayit.update(ek)
    return kayit


def test_satir_baytlari_kanonik_ascii_ve_lf() -> None:
    veri = satir_baytlari({"z": 1, "a": BEH + FETHA, "m": {"y": [1, 2], "b": None}})
    assert veri == (b'{"a":"\\u0628\\u064e","m":{"b":null,"y":[1,2]},"z":1}\n')
    assert veri.isascii()


def test_ingest_satir_bicimiyle_ayni() -> None:
    """normalize/anchor adimlari ingest ile ayni serilestirmeyi kullanir."""
    birim = StagedUnit(
        anchor="q:1:1",
        text="Deneme " + BEH + FETHA,
        attrs={},
        provenance={"file": "x.txt", "line": 1, "bayt": [4, 9], "steps": []},
    )
    beklenen = units_satiri("deneme", birim).encode("utf-8")
    kayit = {
        "anchor": birim.anchor,
        "source_id": "deneme",
        "text": birim.text,
        "attrs": birim.attrs,
        "provenance": birim.provenance,
    }
    assert satir_baytlari(kayit) == beklenen


def test_okuma_yazma_gidis_donus() -> None:
    kayitlar = [satir("q:1:2"), satir("q:1:1", ic={"x": [True, None, BEH]})]
    veri, sayi = units_baytlari(kayitlar)
    assert sayi == 2
    satirlar = satirlari_oku(veri, "deneme")
    assert [s.metin("anchor") for s in satirlar] == ["q:1:1", "q:1:2"]  # okuma sirasi
    assert satirlar[0].veri == kayitlar[1]
    assert satirlar[0].etiket == "deneme"
    assert [s.no for s in satirlar] == [1, 2]
    # yeniden yazmak ayni baytlari verir (deterministik)
    assert units_baytlari([s.veri for s in satirlar])[0] == veri


def test_siralama_okuma_sirasidir_metin_sirasi_degil() -> None:
    kayitlar = [satir("q:10:1"), satir("q:2:255"), satir("q:2:3"), satir("q:1:7")]
    veri, _ = units_baytlari(kayitlar)
    capalar = [s.metin("anchor") for s in satirlari_oku(veri, "d")]
    assert capalar == ["q:1:7", "q:2:3", "q:2:255", "q:10:1"]


@pytest.mark.parametrize(
    ("kayitlar", "parca"),
    [
        ([satir("q:1:1"), satir("q:1:1")], "yinelenen capa: q:1:1"),
        ([satir("q:1:1"), {"text": "x"}], "birim 2: anchor"),
        ([satir("q:1:1"), {"anchor": 5}], "birim 2: anchor"),
        ([satir("q:115:1")], "birim 1: capa gecersiz"),
        ([satir("q:2:255@0-10")], "birim 1: capa gecersiz"),
        ([satir("kotu")], "birim 1: capa gecersiz"),
    ],
)
def test_yazma_hatalari(kayitlar: list[dict[str, object]], parca: str) -> None:
    with pytest.raises(GirdiHatasi, match=parca):
        units_baytlari(kayitlar)


def test_okuma_baytlar_kati_denetlenir() -> None:
    gecerli = b'{"a":1}\n{"a":2}\n'
    assert [s.sayi("a") for s in satirlari_oku(gecerli, "d")] == [1, 2]
    for bozuk, parca in (
        (b"", "bos"),
        (b'{"a":1}', "LF ile bitmiyor"),
        (b'{"a":1}\r\n', "CR"),
        (b'{"a":1}\n\n', "satir 2: JSON gecersiz"),
        (b'{"a":1,"a":2}\n', "satir 1: JSON gecersiz"),
        (b'{"a":1.5}\n', "satir 1: JSON gecersiz"),
        (b'{"a":NaN}\n', "satir 1: JSON gecersiz"),
        (b"[1]\n", "satir 1: nesne degil"),
        (b'{"a":1}\n{\xff}\n', "satir 2: UTF-8"),
    ):
        with pytest.raises(GirdiHatasi, match=parca):
            satirlari_oku(bozuk, "d")


def test_okuma_iletisi_icerik_tasimaz() -> None:
    with pytest.raises(GirdiHatasi) as hata:
        satirlari_oku(b'{"text":"Deneme gizli","a":}\n', "d")
    assert "gizli" not in str(hata.value)
    assert str(hata.value).isascii()


def test_alan_erisimcileri_tip_denetler() -> None:
    s = Satir("e", 7, {"m": "x", "n": 3, "b": True, "o": {"k": 1}})
    assert (s.metin("m"), s.sayi("n"), s.nesne("o"), s.var("m"), s.var("yok")) == (
        "x",
        3,
        {"k": 1},
        True,
        False,
    )
    for cagri in (
        lambda: s.metin("n"),
        lambda: s.metin("yok"),
        lambda: s.sayi("m"),
        lambda: s.sayi("b"),  # bool tam sayi sayilmaz
        lambda: s.nesne("m"),
    ):
        with pytest.raises(GirdiHatasi, match=r"^e: satir 7: '[a-z]+' "):
            cagri()


def test_units_yaz_dry_run_yazmaz_ve_cikti_ozeti_verir(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    ctx = ctx_kur(tmp_path, kok, adim="normalize", dry_run=True)
    cikti = units_yaz(ctx, "deneme", [satir("q:1:2"), satir("q:1:1")])
    assert cikti.satir == 2
    assert cikti.yol == f"staged/deneme/{ctx.run_id}/{UNITS_ADI}"
    assert not (tmp_path / "data" / "staged").exists()

    gercek = ctx_kur(tmp_path, kok, adim="normalize")
    yazilan = units_yaz(gercek, "deneme", [satir("q:1:2"), satir("q:1:1")])
    dosya = tmp_path / "data" / "staged" / "deneme" / gercek.run_id / UNITS_ADI
    assert dosya.read_bytes().endswith(b"\n")
    assert lineage.sha256_dosya(dosya) == yazilan.sha256 == cikti.sha256
    assert [json.loads(s)["anchor"] for s in dosya.read_bytes().splitlines()] == ["q:1:1", "q:1:2"]
