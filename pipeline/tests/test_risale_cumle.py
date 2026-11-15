# ruff: noqa: RUF001
"""Risale cumle ayirici (A20.2a, K-52 madde 8): ortak vektor kosucusu ve birim testleri.

Girdiler ACIKCA SENTETIKTIR ("Deneme cumlesi N", Arap alfabe harfleri): hicbir Kuran, hadis ya
da Risale metni yoktur. `extract/risale-cumle.jsonl` yalniz Python'da kosar (cumle sinirlari
yalniz hatta hesaplanir); TypeScript ve C# kosuculari dosyayi acikca atlar.
"""

import json
from typing import Any

import pytest
import vektor_dosyalari as vd

from mutalaa_pipeline.anchor.cumle import (
    CUMLE_SURUMU,
    KISALTMALAR,
    arapca_araliklari,
    cumleleri_ayir,
)

NBSP = chr(0xA0)  # U+00A0: gorunmez, kodda acik yazilir


def _yukle() -> list[dict[str, Any]]:
    yol = vd.VEKTOR_KOKU / vd.EXTRACT_RISALE_CUMLE
    if not yol.is_file():
        raise RuntimeError(f"vektor dosyasi yok: {vd.EXTRACT_RISALE_CUMLE}")
    veri = yol.read_bytes()
    assert not veri.startswith(b"\xef\xbb\xbf"), "BOM var"
    assert b"\r" not in veri, "CR var"
    satirlar = veri.decode("utf-8").split("\n")
    assert satirlar.pop() == "", "son satir LF ile bitmiyor"
    sonuc = [json.loads(s) for s in satirlar]
    kimlikler = [v["id"] for v in sonuc]
    assert len(set(kimlikler)) == len(kimlikler)
    assert kimlikler == sorted(kimlikler)
    return sonuc


VEKTORLER = _yukle()


def _ar(vektor: dict[str, Any]) -> list[tuple[int, int]]:
    return [(s, e) for s, e in vektor["input"].get("ar", [])]


def test_vektor_dosyasi_yeterince_dolu() -> None:
    assert len(VEKTORLER) >= 35
    assert any("ar" in v["input"] for v in VEKTORLER), "Arapca aralikli vaka yok"
    assert any(v["expected"]["cumleler"] == [] for v in VEKTORLER), "bos vaka yok"
    # en az bir BMP disi karakter (kod noktasi / UTF-16 farki)
    assert any(any(ord(c) > 0xFFFF for c in v["input"]["metin"]) for v in VEKTORLER)


@pytest.mark.parametrize("vektor", VEKTORLER, ids=[v["id"] for v in VEKTORLER])
def test_vektor(vektor: dict[str, Any]) -> None:
    sonuc = cumleleri_ayir(vektor["input"]["metin"], _ar(vektor))
    assert [list(r) for r in sonuc] == vektor["expected"]["cumleler"]


@pytest.mark.parametrize("vektor", VEKTORLER, ids=[v["id"] for v in VEKTORLER])
def test_vektor_degismezleri(vektor: dict[str, Any]) -> None:
    """Her vaka icin: artan, ayrik, bosluksuz kenarli, metin icinde ve bos olmayan araliklar."""
    metin = vektor["input"]["metin"]
    sonuc = cumleleri_ayir(metin, _ar(vektor))
    onceki = 0
    for bas, son in sonuc:
        assert onceki <= bas < son <= len(metin)
        dilim = metin[bas:son]
        assert dilim[0] not in " \t\n" + NBSP
        assert dilim[-1] not in " \t\n" + NBSP
        onceki = son


def test_surum_ve_kisaltma_listesi() -> None:
    assert CUMLE_SURUMU == "1.0"
    assert "hz" in KISALTMALAR
    assert all(k.isascii() and k.isalpha() and k == k.lower() for k in KISALTMALAR)


def test_kod_noktasi_ofseti_utf16_degildir() -> None:
    metin = "Deneme \U0001d400 cumle. Deneme 2."
    assert cumleleri_ayir(metin) == [(0, 15), (16, 25)]
    assert len(metin.encode("utf-16-le")) // 2 == len(metin) + 1  # UTF-16'da bir birim fazla


def test_yari_acik_aralik_dilimi_verir() -> None:
    metin = "Deneme 1. Deneme 2."
    (a, b), (c, d) = cumleleri_ayir(metin)
    assert (metin[a:b], metin[c:d]) == ("Deneme 1.", "Deneme 2.")
    assert b < c  # aralarindaki bosluk hicbir cumleye girmez


def test_metin_degismez_ve_belirlenimci() -> None:
    metin = "Deneme soru mu?  Deneme 2!\nDeneme 3"
    assert cumleleri_ayir(metin) == cumleleri_ayir(metin)
    assert [metin[b:s] for b, s in cumleleri_ayir(metin)] == [
        "Deneme soru mu?",
        "Deneme 2!",
        "Deneme 3",
    ]


def test_turkce_buyuk_kucuk_i_acik_esleme() -> None:
    # I (noktasiz buyuk) bolunur; U+0131 (kucuk noktasiz i) bolunmez; U+0130 (noktali buyuk) bolunur
    assert len(cumleleri_ayir("Deneme mi? Işık deneme.")) == 2
    assert len(cumleleri_ayir("Deneme mi? ışık deneme.")) == 1
    assert len(cumleleri_ayir("Deneme mi? İş deneme.")) == 2


def test_kisaltma_buyuk_kucuk_harften_bagimsiz() -> None:
    assert len(cumleleri_ayir("Deneme DR. Deneme geldi.")) == 1
    assert len(cumleleri_ayir("Deneme dr. Deneme geldi.")) == 1
    assert len(cumleleri_ayir("Deneme drz. Deneme geldi.")) == 2


def test_arapca_aralik_icinde_bolmez_disinda_boler() -> None:
    metin = "Deneme اب. تث sonu. Deneme 2."
    # aralik yok: Arap harfinden once gelen nokta boler
    assert len(cumleleri_ayir(metin)) == 3
    # aralik var: icindeki nokta bolmez
    assert cumleleri_ayir(metin, [(7, 13)]) == [(0, 19), (20, 29)]


def test_arapca_aralik_sinir_durumlari() -> None:
    metin = "Deneme 1. Deneme 2."
    # bitis isareti araligin ilk karakteridir: icinde sayilir
    assert cumleleri_ayir(metin, [(8, 9)]) == [(0, 19)]
    # bitis isareti araligin disinda (bitis dahil degil): boler
    assert len(cumleleri_ayir(metin, [(0, 8)])) == 2


@pytest.mark.parametrize(
    "araliklar",
    [[(-1, 3)], [(3, 3)], [(5, 3)], [(0, 99)], [(0, 5), (4, 8)]],
)
def test_gecersiz_arapca_araligi_hata_verir(araliklar: list[tuple[int, int]]) -> None:
    with pytest.raises(ValueError, match="Arapca"):
        cumleleri_ayir("Deneme 1. Deneme 2.", araliklar)


def test_arapca_araliklari_marks_listesinden_alir() -> None:
    marks = [
        {"s": 9, "e": 12, "t": "ar"},
        {"s": 1, "t": "hasiye", "a": "rn:test-ornek:hasiye-1:p1"},
        {"s": 0, "e": 3, "t": "ar"},
    ]
    assert arapca_araliklari(marks) == [(0, 3), (9, 12)]
    with pytest.raises(ValueError, match="ar isareti"):
        arapca_araliklari([{"t": "ar", "s": 1}])


@pytest.mark.parametrize("metin", ["", " ", " \n\t" + NBSP + " "])
def test_bos_metinde_cumle_yok(metin: str) -> None:
    assert cumleleri_ayir(metin) == []


def test_bitis_isareti_olmayan_metin_tek_cumledir() -> None:
    assert cumleleri_ayir("  Deneme paragrafi 1  ") == [(2, 20)]
