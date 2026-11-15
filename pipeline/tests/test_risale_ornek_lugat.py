# ruff: noqa: RUF001
"""Sentetik lugat maddeleri uretecu (A20.6): `test-risale-ornek` fiksturu."""

import unicodedata
from collections import Counter

from mutalaa_pipeline.export.ortak import kati_json
from mutalaa_pipeline.ingest.lugat_madde import MADDE_ALANLARI, madde_hash
from mutalaa_pipeline.ingest.risale_ornek_lugat import (
    ADET,
    KAYNAK,
    ornek_lugat_baytlari,
    ornek_lugat_satirlari,
)
from mutalaa_pipeline.staged import satirlari_oku


def test_on_bes_madde_basliklar_deneme_sozu() -> None:
    satirlar = ornek_lugat_satirlari()
    assert ADET == len(satirlar) == 15 and 10 <= len(satirlar) <= 20
    assert [s["basliksoz"] for s in satirlar] == [f"Deneme sözü {n}" for n in range(1, 16)]
    assert len({s["basliksoz"] for s in satirlar}) == 15


def test_aday_hat_test_oneki_ve_alanlar() -> None:
    assert KAYNAK.startswith("test-")  # `public` derlemeye girmez (P-12)
    for s in ornek_lugat_satirlari():
        assert set(s) == set(MADDE_ALANLARI)
        assert (s["status"], s["origin"], s["version"], s["source_id"]) == (
            "aday",
            "hat",
            1,
            KAYNAK,
        )
        assert s["osmanlica_yazim"] is None and s["koken_dil"] is None and s["ar_kok_id"] is None
        assert s["content_hash"] == madde_hash(str(s["basliksoz"]), s["tanim_tr"])  # type: ignore[arg-type]
        assert s["kaynaklar"]["fikstur"] is True  # type: ignore[index]


def test_uc_duzey_besere_madde_ve_ucte_biri_tanimsiz() -> None:
    satirlar = ornek_lugat_satirlari()
    assert Counter(s["duzey"] for s in satirlar) == {1: 5, 2: 5, 3: 5}
    tanimsiz = [s["basliksoz"] for s in satirlar if s["tanim_tr"] is None]
    assert tanimsiz == [f"Deneme sözü {n}" for n in (3, 6, 9, 12, 15)]
    for s in satirlar:
        if s["tanim_tr"] is not None:
            assert str(s["tanim_tr"]).startswith("Deneme tanımı ")  # acikca sentetik
        assert s["kaynaklar"]["siklik"] == s["onerilen_basvuru"]["siklik"]  # type: ignore[index]


def test_kendi_metnimiz_nfc_ve_ayni_baytlar() -> None:
    for s in ornek_lugat_satirlari():
        for alan in ("basliksoz", "tanim_tr"):
            if s[alan] is not None:
                assert unicodedata.is_normalized("NFC", str(s[alan]))
    assert ornek_lugat_baytlari() == ornek_lugat_baytlari()


def test_baytlar_kati_json_ve_basliksoza_gore_sirali() -> None:
    veri = ornek_lugat_baytlari()
    satirlar = [
        s.veri for s in satirlari_oku(veri, "lugat.jsonl")
    ]  # ondalik, NaN ve yinelenen anahtar yok
    basliklar = [str(s["basliksoz"]) for s in satirlar]
    assert basliklar == sorted(basliklar) and len(satirlar) == 15
    assert b"\r" not in veri and veri.endswith(b"\n")
    for satir in veri.splitlines():
        kati_json(satir.decode("utf-8"))
