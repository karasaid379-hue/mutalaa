"""`qa/gold/kok_baglanti.py`: Kur'an ici `kok` xref satirlarinin QAC tutarliligi (A18.5; SENTETIK).

Butun veri uydurma ayet capalari ve anlamsiz kok harfleridir; Kur'an metni yoktur. Veritabani
gerekmez (olcum saf islevdir; SQL sorgulari gercek kosuda sinanir).
"""

import pytest

from mutalaa_pipeline.qa.gold import kok_baglanti, setler
from mutalaa_pipeline.qa.gold.kapi import CLI_GATE, TurSonucu

# ayet -> QAC kok harfleri ve veritabani root_id kumesi (ayni kokler iki yoldan)
HARFLER = {1: "k1x", 2: "k2x", 3: "k3x"}
QAC = {
    "q:1:1": ["k1x", "k2x"],
    "q:1:2": ["k1x", "k3x"],
    "q:1:3": ["k2x"],
}
DB = {
    "q:1:1": frozenset({1, 2}),
    "q:1:2": frozenset({1, 3}),
    "q:1:3": frozenset({2}),
}
Satirlar = list[tuple[str, str, list[int]]]


def _manifest() -> tuple[dict[str, object], list[dict[str, object]]]:
    ornekler = kok_baglanti.ornekleri_kur({c: ([], k) for c, k in QAC.items()}, "0.4")
    manifest, _ = setler.set_hazirla("kok-baglanti", kok_baglanti.taslak("0.4"), ornekler)
    return manifest, ornekler


def _olc(satirlar: Satirlar, db: dict[str, frozenset[int]] | None = None) -> TurSonucu:
    manifest, ornekler = _manifest()
    return kok_baglanti.kok_baglanti_olc(manifest, ornekler, db or DB, satirlar, HARFLER)


def test_manifest_altin_tutarlilik_ve_dongusellik_muaf() -> None:
    manifest, ornekler = _manifest()
    assert manifest["sinif"] == "altin" and manifest["olcum_turu"] == "tutarlilik"
    assert manifest["set"] == "kok-baglanti" and manifest["ornek_sayisi"] == 3
    assert all(o["sinif"] == "altin" for o in ornekler)
    # tutarlilik turu dongusellikten muaf: uretim kaynagi qac-morfoloji, set kaniti ayni
    setler.manifest_dongusellik_denetle(manifest, {"qac-morfoloji"})


def test_tum_satirlar_tutarliysa_gecti_ve_gate_kok_xref() -> None:
    s = _olc([("q:1:1", "q:1:2", [1]), ("q:1:1", "q:1:3", [2]), ("q:1:1", "q:1:2", [1])])
    assert s.olculer == {"tutarlilik": 1.0} and s.sonuc == "gecti"
    assert (s.gate_tur, s.alt_tur, s.set_sinifi) == ("kok", "xref", "altin")
    assert s.olculen_ornek == 3
    assert s.ayrintilar["xref"]["tutarli"] == 3  # type: ignore[index]
    assert CLI_GATE["kok-baglanti"] == ("kok", "xref")


def test_paylasilan_kok_hedef_ayette_yoksa_kaldi() -> None:
    # kok 3 (k3x) yalniz q:1:2'de var; q:1:3'te yok -> tutarsiz
    s = _olc([("q:1:1", "q:1:2", [1]), ("q:1:2", "q:1:3", [3])])
    assert s.sonuc == "kaldi" and s.olculer["tutarlilik"] == pytest.approx(0.5)
    x = s.ayrintilar["xref"]
    assert x["tutarsiz"] == 1 and x["db_root_id_kumesinde_degil"] == 1  # type: ignore[index]
    assert x["tutarsiz_ornekleri"] == ["q:1:2|q:1:3"]  # type: ignore[index]


def test_veritabani_kumesinde_olup_qac_kesisiminde_olmayan_kok_tutarsiz() -> None:
    """DB `root_id` kumesi QAC kumesinden saparsa (bozuk veri): ikisi de ayri sayilir."""
    bozuk = {**DB, "q:1:3": frozenset({1, 2})}  # DB q:1:3'te kok 1 var, QAC'te yok
    s = _olc([("q:1:1", "q:1:3", [1])], db=bozuk)
    assert s.sonuc == "kaldi"
    x = s.ayrintilar["xref"]
    assert x["db_root_id_kumesinde_degil"] == 0 and x["qac_kesisiminde_degil"] == 1  # type: ignore[index]


def test_bos_shared_ve_bilinmeyen_kok_tutarsiz() -> None:
    s = _olc([("q:1:1", "q:1:2", []), ("q:1:1", "q:1:2", [99])])
    assert s.sonuc == "kaldi" and s.olculer["tutarlilik"] == 0.0
    assert s.ayrintilar["xref"]["bos_shared"] == 1  # type: ignore[index]


def test_bir_satirin_tum_paylasilan_kokleri_tutmali() -> None:
    s = _olc([("q:1:1", "q:1:2", [1, 2])])  # kok 2 q:1:2'de yok
    assert s.sonuc == "kaldi"


def test_satir_yoksa_bos_kume_gecmez() -> None:
    s = _olc([])
    assert s.olculer == {"tutarlilik": 0.0} and s.sonuc == "kaldi" and s.olculen_ornek == 0


def test_tahmin_ozeti_satira_duyarli_ve_uretim_kaynagi_qac() -> None:
    a = _olc([("q:1:1", "q:1:2", [1])])
    b = _olc([("q:1:1", "q:1:3", [2])])
    assert a.tahmin_ozeti != b.tahmin_ozeti and len(a.tahmin_ozeti) == 64
    assert a.uretim_kaynaklari == ["qac-morfoloji"]
