"""Arapca dizi cikarimi, `ar_norm` kelimeleri ve baglam penceresi (A20.7a).

Girdiler acikca sentetiktir: "Deneme paragrafi ..." ve Arap alfabesi harfleri (gercek bir metin
degil). Kur'an, hadis ya da Risale metni kullanilmaz.
"""

import pytest

from mutalaa_pipeline.enrich import arapca_dizi
from mutalaa_pipeline.enrich.arapca_dizi import ArapcaDizi
from mutalaa_pipeline.export.ortak import GirdiHatasi

FATHA = "\N{ARABIC FATHA}"
SUKUN = "\N{ARABIC SUKUN}"
SHADDA = "\N{ARABIC SHADDA}"
TATWEEL = "\N{ARABIC TATWEEL}"

DIZI_1 = "ابت ثجح"  # sentetik harf dizisi
DIZI_2 = "خدذ"


def _metin() -> tuple[str, list[dict[str, object]]]:
    onek = "Deneme paragrafi 1 "
    metin = f"{onek}{DIZI_1} ara metin {DIZI_2} son."
    s1 = len(onek)
    e1 = s1 + len(DIZI_1)
    s2 = metin.index(DIZI_2)
    e2 = s2 + len(DIZI_2)
    marks: list[dict[str, object]] = [
        {"t": "ar", "s": s2, "e": e2, "tur": "alinti"},
        {"t": "rnk", "c": "~", "s": 0, "e": 0},
        {"t": "ar", "s": s1, "e": e1, "tur": "blok"},
    ]
    return metin, marks


def test_isaretlerden_sirali_ve_turlu() -> None:
    metin, marks = _metin()
    diziler = arapca_dizi.isaretlerden(metin, marks)
    assert [d.tur for d in diziler] == ["blok", "alinti"]
    assert [d.metin for d in diziler] == [DIZI_1, DIZI_2]
    assert diziler[0].bas < diziler[0].son <= diziler[1].bas
    assert metin[diziler[1].bas : diziler[1].son] == DIZI_2
    assert diziler[0].uzunluk == len(DIZI_1)


def test_bos_aralik_atlanir_gecersiz_aralik_hata() -> None:
    metin, _ = _metin()
    assert arapca_dizi.isaretlerden(metin, [{"t": "ar", "s": 3, "e": 3, "tur": "alinti"}]) == []
    for kotu in (
        {"t": "ar", "s": 5, "e": 4, "tur": "blok"},
        {"t": "ar", "s": 0, "e": len(metin) + 1, "tur": "blok"},
        {"t": "ar", "s": -1, "e": 2, "tur": "blok"},
        {"t": "ar", "s": "0", "e": 2, "tur": "blok"},
        {"t": "ar", "s": 0, "e": 2, "tur": "baska"},
        {"t": "ar", "s": 0, "e": 2},
    ):
        with pytest.raises(GirdiHatasi):
            arapca_dizi.isaretlerden(metin, [kotu])


def test_hata_iletisi_metin_tasimaz() -> None:
    metin, _ = _metin()
    with pytest.raises(GirdiHatasi) as hata:
        arapca_dizi.isaretlerden(metin, [{"t": "ar", "s": 0, "e": len(metin) + 5, "tur": "blok"}])
    assert "Deneme" not in str(hata.value)


def test_ar_harf_dizileri_latin_metinde() -> None:
    metin, _ = _metin()
    diziler = arapca_dizi.ar_harf_dizileri(metin)
    assert [d.metin for d in diziler] == [DIZI_1, DIZI_2]
    assert all(d.tur == "ham" for d in diziler)
    assert arapca_dizi.ar_harf_dizileri("Deneme paragrafi 2.") == []


def test_isaret_disi_diziler() -> None:
    metin, marks = _metin()
    assert arapca_dizi.isaret_disi_diziler(metin, marks) == []
    kalan = arapca_dizi.isaret_disi_diziler(metin, marks[:1])
    assert [d.metin for d in kalan] == [DIZI_1]


def test_kelimeler_normalize_ve_kaynak_ofset() -> None:
    kaynak = f"ب{FATHA}ت{SUKUN} أب{TATWEEL}ة {SHADDA}"  # hareke, tatvil, elif-hemze, te marbuta
    dizi = ArapcaDizi(10, 10 + len(kaynak), "blok", kaynak)
    sozcukler = arapca_dizi.kelimeler(dizi)
    assert [k.norm for k in sozcukler] == ["بت", "ابه"]
    # ofset: birim metninde kod noktasi, yari acik
    assert (sozcukler[0].bas, sozcukler[0].son) == (10, 10 + len(f"ب{FATHA}ت{SUKUN}"))
    assert sozcukler[1].bas == 10 + len(f"ب{FATHA}ت{SUKUN} ")
    assert arapca_dizi.norm_dizi(dizi) == "بت ابه"


def test_yalin_hemze_ve_bos_kelime_atilir() -> None:
    dizi = ArapcaDizi(0, 9, "ham", f"ابت ء {FATHA} ثج")
    assert [k.norm for k in arapca_dizi.kelimeler(dizi)] == ["ابت", "ثج"]


def test_kelime_araligi() -> None:
    dizi = ArapcaDizi(5, 5 + len("ابت ثجح خدذ"), "blok", "ابت ثجح خدذ")
    sozcukler = arapca_dizi.kelimeler(dizi)
    assert len(sozcukler) == 3
    assert arapca_dizi.kelime_araligi(sozcukler, 1, 3) == (sozcukler[1].bas, sozcukler[2].son)
    assert dizi.metin[sozcukler[1].bas - 5 : sozcukler[2].son - 5] == "ثجح خدذ"
    for ilk, son in ((0, 0), (2, 1), (0, 4), (-1, 1)):
        with pytest.raises(ValueError, match="gecersiz"):
            arapca_dizi.kelime_araligi(sozcukler, ilk, son)


def test_baglam_penceresi_sinirlari() -> None:
    assert arapca_dizi.baglam_penceresi(1000, 500, 510) == (300, 710)
    assert arapca_dizi.baglam_penceresi(1000, 5, 10) == (0, 210)
    assert arapca_dizi.baglam_penceresi(1000, 990, 1000, 50) == (940, 1000)
    with pytest.raises(ValueError, match="aralik"):
        arapca_dizi.baglam_penceresi(10, 5, 11)
    with pytest.raises(ValueError, match="yaricap"):
        arapca_dizi.baglam_penceresi(10, 1, 2, -1)


def test_baglam_metni_diziyi_icerir() -> None:
    metin, marks = _metin()
    dizi = arapca_dizi.isaretlerden(metin, marks)[0]
    pencere = arapca_dizi.baglam(metin, dizi, 3)
    assert DIZI_1 in pencere
    assert len(pencere) == len(DIZI_1) + 6
