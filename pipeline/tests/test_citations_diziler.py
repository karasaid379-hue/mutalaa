# ruff: noqa: RUF001
"""Arapca dizi cikarma (Iktibas tespiti §3) ve esleme normalizasyonu (§4).

Normalizasyon ornekleri Iktibas tespiti §4 tablosundandir (dokumandaki ornekler); diger Arapca
metinler anlamsiz harf dizileridir (`links_yardimci.sozcuk`). Gercek Tanzil dizileri yalniz
`test_citations_gercek.py` icinde, veritabanindan betikle alinir.
"""

import pytest
from links_yardimci import sozcuk

from mutalaa_pipeline.enrich.citations.diziler import arapca_diziler
from mutalaa_pipeline.enrich.citations.normalizasyon import anahtar_dizisi, belirtecler

# Iktibas tespiti §4 tablosu (Uthmani yazim -> esleme anahtari)
ORNEKLER = [
    ("ٱلرَّحْمَـٰنِ", "الرحمن"),
    ("ٱلْكِتَـٰبُ", "الكتب"),
    ("ٱلصَّلَوٰةَ", "الصلوه"),
    ("شَىْءٍ", "شي"),
]


@pytest.mark.parametrize(("girdi", "beklenen"), ORNEKLER)
def test_normalizasyon_tablo_ornekleri(girdi: str, beklenen: str) -> None:
    assert anahtar_dizisi(girdi) == [beklenen]


def test_hemze_ve_rakam_kurallari() -> None:
    # yalin hemze silinir; vav/ye uzerindeki hemze duz harf; rakam ve noktalama bosluk
    assert anahtar_dizisi("ء") == []  # tek basina hemze: belirtec yok
    assert anahtar_dizisi("بؤب") == ["بوب"]
    assert anahtar_dizisi("بئب") == ["بيب"]
    assert anahtar_dizisi("بءب") == ["بب"]
    assert anahtar_dizisi("بب ٢٥ بج") == ["بب", "بج"]
    assert anahtar_dizisi("بب،بج") == ["بب", "بج"]


def test_belirtec_ofsetleri_ham_sozcuge_isaret_eder() -> None:
    metin = "بَب جْج ء دد"
    b = belirtecler(metin)
    assert [x.anahtar for x in b] == ["بب", "جج", "دد"]
    assert [metin[x.bas : x.son] for x in b] == [
        "بَب",
        "جْج",
        "دد",
    ]


def test_diziler_basit_cikarma_ve_ofset() -> None:
    ar = " ".join(sozcuk(i) for i in range(5))
    metin = f"Deneme paragrafi 1 {ar} Deneme paragrafi 2."
    d = arapca_diziler(metin)
    assert len(d) == 1 and d[0].metin == ar and metin[d[0].bas : d[0].son] == ar
    assert (d[0].position, d[0].suslu) == ("metin", False)


def test_diziler_latin_noktalama_ve_bosluk_ile_birlesir() -> None:
    a, b = sozcuk(1), sozcuk(2)
    assert len(arapca_diziler(f"x {a}, {b} y")) == 1  # virgul ve bosluk
    assert len(arapca_diziler(f"x {a}.  {b} y")) == 1  # nokta ve iki bosluk
    assert len(arapca_diziler(f"x {a} -  {b} y")) == 1  # tire ve bosluklar
    assert len(arapca_diziler(f"x {a}    {b} y")) == 2  # dort bosluk: ayrilir
    assert len(arapca_diziler(f"x {a}\n{b} y")) == 2  # satir sonu: ayrilir
    assert len(arapca_diziler(f"x {a} ve {b} y")) == 2  # Latin harf: ayrilir
    assert len(arapca_diziler(f"x {a} (2:255) {b} y")) == 2  # rakam: ayrilir


def test_diziler_sus_parantezi_isaretlenir_ve_araliga_girmez() -> None:
    ar = " ".join(sozcuk(i) for i in range(4))
    metin = f"x ﴿{ar}﴾ y"
    (d,) = arapca_diziler(metin)
    assert d.suslu and d.metin == ar
    assert metin[d.bas : d.son] == ar  # sus parantezi aralik disinda


def test_diziler_position_degeri() -> None:
    ar = sozcuk(1) + " " + sozcuk(2)
    for p in ("baslik", "dipnot", "metin"):
        assert arapca_diziler(ar, p)[0].position == p
    with pytest.raises(ValueError):
        arapca_diziler(ar, "baska")


def test_diziler_harf_icermeyen_dizi_atilir() -> None:
    assert arapca_diziler("x ،؟ y") == []


def test_diziler_zwnj_dizi_icinde_kalir() -> None:
    a = sozcuk(1) + "‌" + sozcuk(2)
    (d,) = arapca_diziler(f"x {a} y")
    assert d.metin == a


def test_diziler_bmp_disi_ofset() -> None:
    ar = sozcuk(1) + " " + sozcuk(2)
    metin = f"\U0001d400\U0001d401 {ar}"
    (d,) = arapca_diziler(metin)
    assert d.bas == 3 and metin[d.bas : d.son] == ar  # kod noktasi ofseti (UTF-16 degil)
