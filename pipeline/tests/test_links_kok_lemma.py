"""`kok` ve `lemma` komsulugu (A18.3): IDF esigi, N siniri, esitlik sirasi, skor formulu.

SENTETIK dunya: kimlikler tam sayidir, kelime capalari `q:2:{ayet}:{kelime}`; Arapca metin yok.
"""

import math

import pytest

from mutalaa_pipeline.enrich.baglantilar.girdi import Kelime
from mutalaa_pipeline.enrich.baglantilar.kok_lemma import (
    IDF_ESIGI,
    df_uyumsuzluklari,
    idf_n,
    komsular,
    kumeleri_kur,
    yuvarla,
)


def kelime(sira: int, no: int, kok: int | None, lemma: int | None = None) -> Kelime:
    return Kelime(sira, no, f"q:2:{sira + 1}:{no}", "w", kok, lemma)


def dunya(ayetler: list[list[int | None]]) -> list[Kelime]:
    """`ayetler[i]`: i. ayetin kelimelerinin kok kimlikleri (None: koksuz)."""
    return [kelime(i, k + 1, r) for i, kokler in enumerate(ayetler) for k, r in enumerate(kokler)]


def test_idf_n_formulu_ve_sinirlari() -> None:
    assert idf_n(1) == 1.0
    assert idf_n(6236) == 0.0
    assert idf_n(100) == pytest.approx(math.log(6236 / 100) / math.log(6236))
    assert idf_n(3, 10) == pytest.approx(math.log(10 / 3) / math.log(10))
    for gecersiz in (0, 6237):
        with pytest.raises(ValueError, match="df"):
            idf_n(gecersiz)


def test_idf_esigi_alti_kokler_kumeden_cikarilir() -> None:
    # toplam 10 ayet: idf_n(5) = 0,301 (kalir), idf_n(6) = 0,222 (cikar)
    assert idf_n(5, 10) > IDF_ESIGI > idf_n(6, 10)
    ayetler: list[list[int | None]] = [
        [1, 2],
        [1, 2],
        [1, 2],
        [1, 2],
        [1, 2],
        [2],
        [2],
        [9],
        [8],
        [7],
    ]
    k = kumeleri_kur(dunya(ayetler), "root_id", 10)
    assert k.df == {1: 5, 2: 7, 9: 1, 8: 1, 7: 1}
    assert sorted(k.idf) == [1, 7, 8, 9]  # 2 (df 7) cikarildi
    assert k.cikarilan == 1
    assert k.ilk_kelime[0] == {1: "q:2:1:1"}
    assert k.ilk_kelime[5] == {}  # yalniz yaygin kok: kume bos
    assert k.ters[1] == [0, 1, 2, 3, 4]


def test_yaygin_koklu_birim_satir_uretmez() -> None:
    ayetler: list[list[int | None]] = [[2], [2], [2], [2], [2], [2], [2], [1], [1], [None]]
    k = kumeleri_kur(dunya(ayetler), "root_id", 10)
    satirlar = list(komsular(k))
    assert {s.src for s in satirlar} == {7, 8}  # 0..6 yalniz yaygin kok tasir
    assert all(s.dst in (7, 8) for s in satirlar)


def test_skor_formulu_ortak_idf_toplami_bolu_kaynak_kume_toplami() -> None:
    # toplam 10: r1 df 2, r2 df 3, r3 df 1
    ayetler: list[list[int | None]] = [[1, 2, 3], [1, 2], [2], [4], [4], [4], [4], [4], [5], [5]]
    kelimeler = dunya(ayetler)
    k = kumeleri_kur(kelimeler, "root_id", 10)
    sonuc = {(s.src, s.dst): s for s in komsular(k)}
    a_b = sonuc[(0, 1)]
    payda = idf_n(2, 10) + idf_n(3, 10) + idf_n(1, 10)
    assert a_b.skor == yuvarla((idf_n(2, 10) + idf_n(3, 10)) / payda)
    # yon: B -> A paydasi B'nin kumesidir (iki kok), skor 1,0
    assert sonuc[(1, 0)].skor == 1.0
    assert [o.kimlik for o in a_b.ortaklar] == [1, 2]  # idf azalan (r1 df 2 > r2 df 3)
    assert a_b.ortaklar[0].src_kelime == "q:2:1:1"
    assert a_b.ortaklar[0].dst_kelime == "q:2:2:1"
    assert a_b.ortaklar[1].src_kelime == "q:2:1:2"
    assert (0, 3) not in sonuc  # ortak kok yok


def test_en_cok_bes_komsu_ve_esitlikte_ayet_sirasi() -> None:
    # 0. ayet ile ortak koku olan 9 ayet; hepsi ayni skorda -> en kucuk ayet sirali 5 tanesi
    ayetler: list[list[int | None]] = [[1]] + [[1]] * 3 + [[1]] * 6
    toplam = 40  # df 10 -> idf_n yuksek, esigin ustunde
    k = kumeleri_kur(dunya(ayetler), "root_id", len(ayetler), toplam=toplam)
    kaynak0 = [s for s in komsular(k) if s.src == 0]
    assert [s.dst for s in kaynak0] == [1, 2, 3, 4, 5]
    assert len({s.skor for s in kaynak0}) == 1
    assert all(s.dst != s.src for s in komsular(k))
    uc = [s for s in komsular(k, en_cok=3) if s.src == 9]
    assert [s.dst for s in uc] == [0, 1, 2]


def test_skor_sirasi_yuvarlanmis_degere_gore_ve_azalan() -> None:
    # A'nin iki koku var; B ikisini, C yalniz r1'i paylasir; B once gelir
    ayetler: list[list[int | None]] = [[1, 2], [2, 1], [1], [3], [3], [3], [3], [3], [3], [3]]
    k = kumeleri_kur(dunya(ayetler), "root_id", 10, toplam=100)
    s = [x for x in komsular(k) if x.src == 0]
    assert [x.dst for x in s] == [1, 2]
    assert s[0].skor == 1.0 and 0 < s[1].skor < 1.0


def test_lemma_ayni_formulu_lemma_sutunuyla_kullanir() -> None:
    kelimeler = [
        kelime(0, 1, 1, 10),
        kelime(0, 2, 2, 11),
        kelime(1, 1, 1, 12),  # ayni kok, farkli lemma
        kelime(1, 2, 3, 11),  # ayni lemma
    ]
    kok = {(s.src, s.dst) for s in komsular(kumeleri_kur(kelimeler, "root_id", 2, toplam=50))}
    lemma = list(komsular(kumeleri_kur(kelimeler, "lemma_id", 2, toplam=50)))
    assert kok == {(0, 1), (1, 0)}
    assert [(s.src, s.dst) for s in lemma] == [(0, 1), (1, 0)]
    assert [o.kimlik for o in lemma[0].ortaklar] == [11]
    assert lemma[0].ortaklar[0].src_kelime == "q:2:1:2"
    assert lemma[0].ortaklar[0].dst_kelime == "q:2:2:2"


def test_ayah_count_uyumsuzlugu() -> None:
    assert df_uyumsuzluklari({1: 3, 2: 4}, {1: 3, 2: 4, 7: 0}) == []
    assert df_uyumsuzluklari({1: 3, 2: 4}, {1: 3, 2: 5}) == [2]
    assert df_uyumsuzluklari({1: 3}, {}) == [1]
    assert df_uyumsuzluklari({}, {5: 2}) == [5]


def test_skor_bir_i_asmaz() -> None:
    assert yuvarla(1.0000000004) == 1.0
    assert yuvarla(0.12345678) == 0.123457
