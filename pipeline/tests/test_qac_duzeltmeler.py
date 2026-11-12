"""Bagimsiz inceleme duzeltmeleri (A17): capa bicimleme/siralama ve `words.jsonl` surum tutarliligi.

SENTETIK veri; hicbir Kur'an ya da Arapca metin yoktur.
"""

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg_qac import kelime_satirlarini_oku
from mutalaa_pipeline.qa.checks.qac import ayet_capalari
from mutalaa_pipeline.staged import satir_baytlari


def test_ayet_capalari_okuma_sirasinda_sayisal_ve_anchor_ile_bicimli() -> None:
    capalar = ayet_capalari([(10, 1), (2, 255), (2, 3), (114, 1), (2, 3)])
    assert capalar == ["q:2:3", "q:2:255", "q:10:1", "q:114:1"]  # q:10:1, q:2:1'den SONRA


def test_ayet_capalari_gecersiz_cift_sona_etiketle_yazilir() -> None:
    capalar = ayet_capalari([(115, 1), (1, 1), (2, 300)])
    assert capalar[0] == "q:1:1"
    assert capalar[1:] == ["gecersiz:2:300", "gecersiz:115:1"]


def _satir(no: int, surum: str) -> dict[str, object]:
    return {
        "anchor": f"q:1:1:{no}",
        "surah": 1,
        "ayah": 1,
        "word": no,
        "pos": "N",
        "lemma_qac_ref": None,
        "root_letters_bw": None,
        "features": {"govde": []},
        "segment_sayisi": 1,
        "govde_sayisi": 1,
        "source_id": "qac-morfoloji",
        "data_version": surum,
    }


def test_kelime_satirlari_data_version_tutarli_okunur() -> None:
    veri = b"".join(satir_baytlari(_satir(n, "qac-morfoloji@0.4")) for n in (1, 2))
    assert len(kelime_satirlarini_oku(veri)) == 2


def test_kelime_satirlari_data_version_tutarsizsa_girdi_hatasi() -> None:
    veri = satir_baytlari(_satir(1, "qac-morfoloji@0.4")) + satir_baytlari(
        _satir(2, "qac-morfoloji@0.5")
    )
    with pytest.raises(GirdiHatasi) as hata:
        kelime_satirlarini_oku(veri)
    assert "data_version" in str(hata.value)
