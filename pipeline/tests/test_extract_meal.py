"""Cikarim vektoru kosucusu (A16.2, K-49 madde 13): `extract/meal.jsonl`.

Girdiler ACIKCA SENTETIKTIR ("Deneme meal parcasi N"): hicbir Kuran, meal, tefsir, hadis ya da
Risale metni yoktur. Vektoru yalniz Python kosar (cikarim yalniz hatta yapilir); TypeScript ve
C# kosuculari dosyayi acikca atlar. Bu dosya Vikikaynak cikarici cekirdegini (`sayfa_cikar`)
her satir icin sinar: ayni girdi ayni birimleri ve uyarilari verir ya da `hata` satirinda
`GirdiHatasi` (cikis 2) firlatir.
"""

import json
from typing import Any

import pytest
import vektor_dosyalari as vd

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.elmalili_epub import tanik_cikar
from mutalaa_pipeline.ingest.elmalili_sade import metin_cikar
from mutalaa_pipeline.ingest.elmalili_vikikaynak import sayfa_cikar


def _yukle() -> list[dict[str, Any]]:
    yol = vd.VEKTOR_KOKU / vd.EXTRACT_MEAL
    if not yol.is_file():
        raise RuntimeError(f"vektor dosyasi yok: {vd.EXTRACT_MEAL}")
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


def test_vektor_dolu_ve_her_tuzagi_kapsar() -> None:
    assert len(VEKTORLER) >= 40
    notlar = " ".join(v.get("note", "") for v in VEKTORLER)
    for tuzak in (
        "sablon",
        "ref",
        "br",
        "nowiki",
        "&nbsp;",
        "''",
        "satir sonu",
        "numarasiz",
        "aralikli",
        "ayni numarali",
        "besmele",
        "bolge",
    ):
        assert tuzak in notlar, f"vektorde tuzak yok: {tuzak}"


def _metinler(v: dict[str, Any]) -> list[str]:
    """Satirin beklenen ciktisindaki butun birim ve tanik metinleri."""
    e = v["expected"]
    sonuc = [b["metin"] for b in e.get("birimler", [])]
    sonuc += [p["metin"] for p in e.get("parcalar", [])]
    if "metin" in e:
        sonuc.append(e["metin"])
    return sonuc


def test_girdiler_ve_beklenenler_sentetiktir() -> None:
    """Girdiler 'Deneme' yer tutucu metnidir; her cikti metni 'Deneme' ile baslar ya da bostur."""
    for v in VEKTORLER:
        girdi = v["input"]
        ham = girdi.get("wikitext") or girdi.get("metin") or girdi.get("akis") or ""
        assert "Deneme" in ham, v["id"]
        for metin in _metinler(v):
            assert metin == "" or metin.startswith("Deneme"), (v["id"], len(metin))


def test_uc_kaynak_turu_vardir() -> None:
    assert {v["input"]["kaynak"] for v in VEKTORLER} == {"vikikaynak", "sade", "epub"}


@pytest.mark.parametrize("vektor", VEKTORLER, ids=[v["id"] for v in VEKTORLER])
def test_cikarim_vektoru(vektor: dict[str, Any]) -> None:
    girdi, beklenen = vektor["input"], vektor["expected"]
    hata = beklenen.get("hata") is True
    if girdi["kaynak"] == "sade":
        assert metin_cikar(girdi["metin"]) == beklenen["metin"]
        return
    if girdi["kaynak"] == "epub":
        if hata:
            with pytest.raises(GirdiHatasi):
                tanik_cikar(girdi["akis"], girdi["sure"])
            return
        satirlar, _, artik, yinelenen = tanik_cikar(girdi["akis"], girdi["sure"])
        assert [
            {"ayet": r["ayet"], "kapsam": r["kapsam"], "metin": r["metin"]} for r in satirlar
        ] == beklenen["parcalar"]
        assert (artik, yinelenen) == (beklenen["artik"], beklenen["yinelenen"])
        return
    kosul = {"sure": girdi["sure"], "ayet_sayisi": girdi["ayet_sayisi"], "eser": "elmalili"}
    if hata:
        with pytest.raises(GirdiHatasi):
            sayfa_cikar(girdi["wikitext"], **kosul)
        return
    cikti = sayfa_cikar(girdi["wikitext"], **kosul)
    assert [
        {"ayet": a.ayet, "metin": a.metin, "attrs": a.attrs, "uyari": list(a.uyari)}
        for a in cikti.ayetler
    ] == beklenen["birimler"]
    assert (cikti.on_bolge is not None) is beklenen["on_bolge"]
    assert (cikti.son_bolge is not None) is beklenen["son_bolge"]
