"""`qa/gold/alim.py`: alim kaynakli `benzer_ayet` satirlarinin kaynak butunlugu (A18.5; SENTETIK).

Uydurma ayet capalari ve cift listesi; QurSim dosyasi ya da ayet metni yoktur. Veritabani gerekmez.
"""

from collections.abc import Mapping

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import alim, setler
from mutalaa_pipeline.qa.gold.kapi import CLI_GATE, TurSonucu

SIRA = {"q:1:1": 1, "q:1:2": 2, "q:1:3": 3, "q:1:4": 4, "q:1:5": 5}
CAPA = {v: k for k, v in SIRA.items()}
KAYITLI = frozenset({"qursim", "tanzil-uthmani", "qac-morfoloji"})
QURSIM = {(1, 2): 1, (3, 4): 0, (2, 5): 2}  # (lo, hi) -> ham Label
Satir = tuple[str, str, Mapping[str, object]]


def _set() -> tuple[dict[str, object], list[dict[str, object]]]:
    ornekler = alim.ornekleri_kur(QURSIM, CAPA, "0.1")
    manifest, _ = setler.set_hazirla("benzer-ayet-alim", alim.taslak("0.1", {"ornek": 3}), ornekler)
    return manifest, ornekler


def _satir(src: str, dst: str, **ek: object) -> Satir:
    kanit: dict[str, object] = {"subtype": "alim", "source_id": "qursim", "label": 1}
    kanit.update(ek)
    return src, dst, kanit


def _olc(satirlar: list[Satir], kayitli: frozenset[str] = KAYITLI) -> TurSonucu:
    manifest, ornekler = _set()
    return alim.alim_olc(manifest, ornekler, satirlar, SIRA, kayitli)


def test_manifest_kaynak_turu_altin_ve_dongusellik_muaf() -> None:
    manifest, ornekler = _set()
    assert manifest["olcum_turu"] == "kaynak" and manifest["sinif"] == "altin"
    assert manifest["set"] == "benzer-ayet-alim"
    assert [o["id"] for o in ornekler] == ["q:1:1|q:1:2", "q:1:2|q:1:5", "q:1:3|q:1:4"]
    assert "olcum_turu = kaynak" in str(manifest["dongusellik_notu"])
    # set kaniti qursim = uretim kaynagi: `dogruluk` olsaydi hata verirdi; `kaynak` muaf
    setler.manifest_dongusellik_denetle(manifest, {"qursim"})
    degisik = {**manifest, "olcum_turu": "dogruluk"}
    with pytest.raises(GirdiHatasi, match="dongusellik"):
        setler.manifest_dongusellik_denetle(degisik, {"qursim"})


def test_tum_alim_satirlari_butunse_gecti() -> None:
    s = _olc([_satir("q:1:1", "q:1:2"), _satir("q:1:3", "q:1:4"), _satir("q:1:2", "q:1:5")])
    assert s.olculer == {"kaynak_butunlugu": 1.0} and s.sonuc == "gecti"
    assert s.olculen_ornek == 3
    assert (s.gate_tur, s.alt_tur, s.set_sinifi) == ("benzer_ayet", "alim", "altin")
    assert CLI_GATE["benzer-ayet-alim"] == ("benzer_ayet", "alim")
    assert s.ayrintilar["qursim_cifti_veritabaninda_olmayan"] == 0


def test_yon_normalize_ters_yazilmis_cift_da_tutar() -> None:
    s = _olc([_satir("q:1:2", "q:1:1")])  # kumede (1, 2): ters yon ayni cift
    assert s.sonuc == "gecti"


def test_bozuk_cift_kumede_yoksa_kaldi() -> None:
    s = _olc([_satir("q:1:1", "q:1:2"), _satir("q:1:1", "q:1:3")])  # (1, 3) QurSim'de yok
    assert s.sonuc == "kaldi" and s.olculer["kaynak_butunlugu"] == pytest.approx(0.5)
    assert s.ayrintilar["kusur_nedenleri"] == {"cift_qursim_de_yok": 1}
    assert s.ayrintilar["kusurlu_ornekleri"] == ["q:1:1|q:1:3"]


def test_kayitsiz_source_id_kaldi() -> None:
    s = _olc([_satir("q:1:1", "q:1:2")], kayitli=frozenset({"tanzil-uthmani"}))
    assert s.sonuc == "kaldi"
    assert s.ayrintilar["kusur_nedenleri"] == {"source_id_kayitli_degil": 1}


def test_qursim_nesneli_sozluksel_satir_alim_sayilir_ve_olculur() -> None:
    ortak: Satir = (
        "q:1:3",
        "q:1:4",
        {"subtype": "sozluksel", "source_id": "tanzil-uthmani", "qursim": {"label": 2}},
    )
    assert alim.alim_mi(ortak[2])
    s = _olc([ortak])
    assert s.sonuc == "gecti" and s.ayrintilar["kaynak_dagilimi"] == {"qursim,tanzil-uthmani": 1}
    # ayni satirda qursim kaynagi kayitli degilse kaldi (isaretin kaynagi da denetlenir)
    assert _olc([ortak], kayitli=frozenset({"tanzil-uthmani"})).sonuc == "kaldi"


def test_alim_mi_siniri() -> None:
    assert alim.alim_mi({"source_id": "qursim"})
    assert alim.alim_mi({"source_id": "tanzil-uthmani", "qursim": {"label": 0}})
    assert not alim.alim_mi({"source_id": "tanzil-uthmani", "subtype": "sozluksel"})
    assert not alim.alim_mi({"source_id": "tanzil-uthmani", "qursim": True})  # nesne degil
    assert not alim.alim_mi(None) and not alim.alim_mi("qursim")


def test_satir_yoksa_bos_kume_gecmez_ve_veritabaninda_olmayan_cift_sayilir() -> None:
    s = _olc([])
    assert s.olculer == {"kaynak_butunlugu": 0.0} and s.sonuc == "kaldi"
    assert s.ayrintilar["qursim_cifti_veritabaninda_olmayan"] == 3
    kismi = _olc([_satir("q:1:1", "q:1:2")])
    assert kismi.sonuc == "gecti" and kismi.ayrintilar["qursim_cifti_veritabaninda_olmayan"] == 2


def test_uretim_kaynaklari_ve_ozet_satirdan_gelir() -> None:
    a = _olc([_satir("q:1:1", "q:1:2")])
    b = _olc([_satir("q:1:3", "q:1:4")])
    assert a.uretim_kaynaklari == ["qursim"] and a.tahmin_ozeti != b.tahmin_ozeti
