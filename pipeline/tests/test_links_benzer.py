"""`benzer_ayet` sozluksel skor, simetrik tekillestirme, sinir ve QurSim birlestirmesi (A18.3).

SENTETIK kelimeler (`w1`, `x1` ...); Arapca metin yok.
"""

import pytest

from mutalaa_pipeline.enrich.baglantilar.benzer import (
    EN_COK_BENZER,
    QURSIM_SKORU,
    SozlukselCift,
    adaylari_bul,
    birlestir,
    sinirla,
    skor_hesapla,
)
from mutalaa_pipeline.enrich.quran_index import KuranIndeksi


def kelimeler(onek: str, n: int) -> list[str]:
    return [f"{onek}{i}" for i in range(1, n + 1)]


def test_skor_formulu() -> None:
    assert skor_hesapla(7, 14) == pytest.approx(1.0 * (0.5 + 0.5 * 0.5))
    assert skor_hesapla(4, 4) == pytest.approx(4 / 7)
    assert skor_hesapla(4, 8) == pytest.approx((4 / 7) * 0.75)
    assert skor_hesapla(20, 20) == 1.0  # doyum: min(1, ortak/7)
    for ortak, uzunluk in ((1, 0), (5, 4), (-1, 4)):
        with pytest.raises(ValueError, match="ortak"):
            skor_hesapla(ortak, uzunluk)


def test_aday_sarti_ortak_4gram_ve_iki_yonun_buyugu() -> None:
    kisa = kelimeler("w", 5)  # 5 kelime
    uzun = [*kelimeler("w", 5), *kelimeler("y", 15)]  # 20 kelime, kisanin hepsini icerir
    yalniz_uc = ["w1", "w2", "w3", "q1", "q2"]
    ix = KuranIndeksi([kisa, uzun, yalniz_uc])
    adaylar = adaylari_bul({"uthmani": ix})
    assert set(adaylar) == {(0, 1)}  # yalniz ortak 3-gram olan ayet aday degil
    c = adaylar[(0, 1)]
    # kisa ayet icin: ortak 5/5 -> skor 5/7 * 1,0; uzun icin 5/20 -> daha kucuk
    assert c.skor == pytest.approx(round(5 / 7, 6))
    assert (c.lo, c.hi, c.ortak, c.ayet_kelime, c.kapsayan) == (0, 1, 5, 5, "src")
    assert c.kapsama == 1.0 and c.indeks == "uthmani"


def test_kapsayan_ayet_hedefse_yon_dst_olur() -> None:
    uzun = [*kelimeler("y", 15), *kelimeler("w", 5)]
    kisa = kelimeler("w", 5)
    adaylar = adaylari_bul({"uthmani": KuranIndeksi([uzun, kisa])})
    c = adaylar[(0, 1)]
    assert c.kapsayan == "dst" and c.ayet_kelime == 5 and c.ortak == 5


def test_iki_indeksten_yuksek_skor_ve_esitlikte_uthmani() -> None:
    a = kelimeler("w", 6)
    b_uth = [*kelimeler("w", 4), "u1", "u2"]  # uthmani'de 4 ortak
    b_iml = [*kelimeler("w", 6)]  # imlai'de 6 ortak
    uth = KuranIndeksi([a, b_uth])
    iml = KuranIndeksi([a, b_iml])
    c = adaylari_bul({"uthmani": uth, "imlai": iml})[(0, 1)]
    assert c.indeks == "imlai" and c.ortak == 6
    ayni = adaylari_bul({"uthmani": iml, "imlai": iml})[(0, 1)]
    assert ayni.indeks == "uthmani"


def test_sinir_her_ayet_icin_en_iyi_on_komsu_birlesim() -> None:
    # merkez ayet (0) ile 12 ayet ortak 4-gram paylasir; skorlar ortak sayisiyla artar
    merkez = kelimeler("m", 24)
    ayetler = [merkez]
    for j in range(12):
        ayetler.append([*merkez[: 4 + j], *kelimeler(f"z{j}_", 3)])
    adaylar = adaylari_bul({"uthmani": KuranIndeksi(ayetler)})
    assert all(0 in cift for cift in adaylar if cift[0] == 0)
    secilen = sinirla(adaylar, EN_COK_BENZER)
    # her yaprak ayetin en iyi komsusu en cok ortagi olan yapraktir: sinir birlesimle tutulur
    assert len(secilen) >= EN_COK_BENZER
    assert secilen <= set(adaylar)
    dar = sinirla(adaylar, 1)
    assert dar <= secilen and dar


def test_sinir_iki_ucun_hicbirinde_ilk_n_degilse_eler() -> None:
    cift = {
        (i, j): SozlukselCift(
            i, j, round(0.9 - 0.01 * (i * 10 + j), 6), 4, 4, 1.0, "uthmani", "src"
        )
        for i in range(3)
        for j in range(3, 6)
    }
    secilen = sinirla(cift, 1)
    # 0, 1, 2'nin en iyisi 3; 3, 4, 5'in en iyisi 0 degil kendi lo ucudur: 3 -> 0, 4 -> 0, 5 -> 0
    assert secilen == {(0, 3), (1, 3), (2, 3), (0, 4), (0, 5)}
    assert (1, 4) not in secilen and (2, 5) not in secilen


def test_qursim_birlestirme_tek_satir_ve_label_puani_etkilemez() -> None:
    kendi = SozlukselCift(0, 1, 0.571429, 4, 4, 1.0, "uthmani", "src")
    adaylar = {(0, 1): kendi, (2, 3): SozlukselCift(2, 3, 0.6, 5, 5, 1.0, "imlai", "src")}
    secilen = {(2, 3)}  # (0,1) sinirdan elendi
    satirlar = birlestir(adaylar, secilen, {(0, 1): 2, (4, 5): 0, (6, 7): 1})
    sozluk = {(s.lo, s.hi): s for s in satirlar}
    assert sorted(sozluk) == [(0, 1), (2, 3), (4, 5), (6, 7)]
    # kendi indeksimizde aday olan QurSim cifti: sozluksel skor, subtype sozluksel, label ekli
    assert sozluk[(0, 1)].altyapi == "sozluksel" and sozluk[(0, 1)].qursim_label == 2
    assert sozluk[(0, 1)].skor == 0.571429
    assert sozluk[(2, 3)].qursim_label is None
    # saf QurSim: sabit skor, Label'dan bagimsiz
    assert sozluk[(4, 5)].altyapi == "alim" and sozluk[(6, 7)].altyapi == "alim"
    assert sozluk[(4, 5)].skor == sozluk[(6, 7)].skor == QURSIM_SKORU == 0.5
    assert [(s.lo, s.hi) for s in satirlar] == sorted(sozluk)
