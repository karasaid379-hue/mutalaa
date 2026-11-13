"""Kur'an kelime n-gram indeksi (A18.3, A18.4): SENTETIK kelimeler (`w1`, `w2` ...)."""

import pytest

from mutalaa_pipeline.enrich.quran_index import KuranIndeksi


def ayet(*kelimeler: str) -> list[str]:
    return list(kelimeler)


def test_konumlar_kuresel_ve_ayet_siniri_asmaz() -> None:
    ix = KuranIndeksi([ayet("a", "b", "c", "d"), ayet("a", "b", "c", "d", "e"), ayet("x", "a")])
    assert ix.ayet_sayisi == 3
    assert ix.konum(1, 0) == 4
    assert ix.konumlar(["a", "b", "c"]) == [0, 4]
    assert ix.konumlar(["b", "c", "d", "e"]) == [5]
    # `d` (ayet 0) ile `a` (ayet 1) bitisik degildir: pencere ayet sinirini asmaz
    assert ix.konumlar(["d", "a", "b"]) == []
    assert ix.konumlar(["x", "a", "b"]) == []


def test_yalniz_uc_ve_dort_kelimelik_diziler_indekslenir() -> None:
    ix = KuranIndeksi([ayet("a", "b", "c")])
    with pytest.raises(ValueError, match="3 ve 4"):
        ix.konumlar(["a", "b"])
    with pytest.raises(IndexError):
        ix.konum(0, 3)


def test_ayet_siniri_asan_pencereler_istege_baglidir() -> None:
    ix = KuranIndeksi([ayet("a", "b", "c"), ayet("d", "e")], ayet_siniri_asar=True)
    assert ix.konumlar(["b", "c", "d"]) == [1]  # penceresi 0. ayette baslar
    assert ix.ayet_of[1] == 0
    assert ix.konumlar(["c", "d", "e"]) == [2]


def test_komsular_ortak_4gram_sarti_ve_kapsama_birlesimi() -> None:
    a = ayet("w1", "w2", "w3", "w4", "w5", "x1", "x2", "x3")
    b = ayet("y", "w1", "w2", "w3", "w4", "z", "x1", "x2", "x3")  # 4-gram + ayri 3 kelime
    c = ayet("w1", "w2", "w3", "q")  # yalniz ortak 3-gram: aday degil
    ix = KuranIndeksi([a, b, c])
    k = ix.komsular(0)
    assert set(k) == {1}
    # w1..w4 (4 kelime) + x1..x3 (3 kelime); w5 ortak degil
    assert k[1] == 7
    assert ix.komsular(2) == {}  # c'nin ortak 4-grami yok
    assert ix.komsular(1)[0] == 7  # b'nin ayni kelimeleri: w1..w4 + x1..x3


def test_ayni_ayet_ve_tekrarlayan_dizi_kendini_eslemez() -> None:
    ix = KuranIndeksi([ayet("a", "b", "c", "d", "a", "b", "c", "d"), ayet("a", "b", "c", "d")])
    assert set(ix.komsular(0)) == {1}
    assert ix.komsular(0)[1] == 8  # iki tekrar da ortak dizi kapsiyor
    assert ix.komsular(1)[0] == 4


def test_tam_ayet_karmasi_kisa_ayetleri_yakalar() -> None:
    ix = KuranIndeksi([ayet("a", "b"), ayet("c", "d", "e"), ayet("a", "b")])
    assert ix.tam_ayetler(["a", "b"]) == [0, 2]
    assert ix.tam_ayetler(["c"]) == []
