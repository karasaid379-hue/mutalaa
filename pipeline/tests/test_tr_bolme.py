# ruff: noqa: RUF001
"""Turkce on bolme (A18.2): `enrich/tr-bolme.jsonl` vektoru ve bolme kurallari.

Girdiler ACIKCA SENTETIKTIR ("Deneme", "kalem-i"): Kur'an, meal, tefsir, hadis ya da Risale metni
yoktur. Vektoru yalniz Python kosar (on bolme yalniz hatta yapilir).
"""

import json
from typing import Any

import pytest
import vektor_dosyalari as vd

from mutalaa_pipeline.enrich.tr_roots.bolme import (
    ROL_EK,
    ROL_IZAFET,
    ROL_TARIF,
    Parca,
    bol,
    kesme_tekle,
    parcalar,
)


def _yukle() -> list[dict[str, Any]]:
    veri = (vd.VEKTOR_KOKU / vd.TR_BOLME).read_bytes()
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


def test_vektor_her_kurali_ve_tuzagi_kapsar() -> None:
    notlar = " ".join(v["note"] for v in VEKTORLER)
    for kural in ("izafet", "tarif", "kesme", "iç kesme", "U+2019", "BMP"):
        assert kural in notlar, f"vektorde kural yok: {kural}"
    roller = {a[3] for v in VEKTORLER for a in v["expected"]["atlananlar"]}
    assert roller == {ROL_EK, ROL_IZAFET, ROL_TARIF}


@pytest.mark.parametrize("vektor", VEKTORLER, ids=[v["id"] for v in VEKTORLER])
def test_vektor(vektor: dict[str, Any]) -> None:
    sonuc = bol(vektor["input"])
    assert [[p.yuzey, p.bas, p.son] for p in sonuc.parcalar] == vektor["expected"]["parcalar"]
    assert [[a.metin, a.bas, a.son, a.rol] for a in sonuc.atlananlar] == vektor["expected"][
        "atlananlar"
    ]


@pytest.mark.parametrize("vektor", VEKTORLER, ids=[v["id"] for v in VEKTORLER])
def test_araliklar_yari_acik_ve_kod_noktasi(vektor: dict[str, Any]) -> None:
    metin: str = vektor["input"]
    for p in parcalar(metin):
        assert 0 <= p.bas < p.son <= len(metin)
        assert metin[p.bas : p.son] == p.yuzey


def test_anahtar_turkce_kucuk_harf_acik_esleme() -> None:
    p = Parca("İşte", 0, 4)  # Iste, noktali I
    assert p.anahtar == "işte"
    assert Parca("Işık", 0, 4).anahtar == "ışık"  # I -> noktasiz i
    assert Parca("Kur’ân", 0, 6).anahtar == "kur'ân"  # kesme bicimi tekillenir
    assert Parca("Kur’ân", 0, 6).lemmatizer_girdisi == "kurân"


def test_kesme_tekle_yalniz_kesme_bicimlerini_cevirir() -> None:
    assert kesme_tekle("a’b‘cʼd´e`f'g-h") == "a'b'c'd'e'f'g-h"


def test_bos_ve_sozcuksuz_metin() -> None:
    assert bol("").parcalar == ()
    assert bol("12 , ; -").parcalar == ()
    assert bol("-a").parcalar == (Parca("a", 1, 2),)


def test_sondaki_tire_ve_kesme_sozcuge_katilmaz() -> None:
    assert [p.yuzey for p in parcalar("kalem- ve kalem' ve")] == ["kalem", "ve", "kalem", "ve"]
