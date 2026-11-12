"""`qa/uyum.py`: Cohen kappa, Wilson ust siniri, ikinci okuma ozeti (A17.6; saf, SENTETIK etiket).

Beklenen degerler elle hesaplanmistir (hesap yorumda). Veritabani ve dosya yok.
"""

import math
import random
from fractions import Fraction
from statistics import NormalDist

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa import uyum

# --- Cohen kappa -------------------------------------------------------------------------------


def test_kappa_iki_kategori_elle_hesap() -> None:
    # 50 madde: 20 evet-evet, 5 evet-hayir, 10 hayir-evet, 15 hayir-hayir.
    # p_o = 35 / 50 = 0,7; A evet 25, B evet 30 -> p_e = 0,5 * 0,6 + 0,5 * 0,4 = 0,5
    # kappa = (0,7 - 0,5) / (1 - 0,5) = 0,4
    a = ["evet"] * 25 + ["hayir"] * 25
    b = ["evet"] * 20 + ["hayir"] * 5 + ["evet"] * 10 + ["hayir"] * 15
    assert uyum.cohen_kappa(a, b) == pytest.approx(0.4, abs=1e-12)
    ozet = uyum.kappa_ozet(a, b)
    assert (ozet.n, ozet.uyum_sayisi) == (50, 35)
    assert ozet.p_o == pytest.approx(0.7) and ozet.p_e == pytest.approx(0.5)
    assert ozet.gecti is False  # 0,4 < 0,60


def test_kappa_uc_kategori_elle_hesap() -> None:
    # a = k k d r; b = k d d r -> uyum 3/4; a: k2 d1 r1; b: k1 d2 r1
    # p_e = (2*1 + 1*2 + 1*1) / 16 = 5/16; kappa = (3/4 - 5/16) / (11/16) = 7/11
    a = ["kabul", "kabul", "duzelt", "red"]
    b = ["kabul", "duzelt", "duzelt", "red"]
    assert uyum.cohen_kappa(a, b) == pytest.approx(7 / 11, abs=1e-12)
    ozet = uyum.kappa_ozet(a, b)
    assert ozet.gecti is True  # 7/11 = 0,636... >= 0,60
    assert ozet.a_sayilari == {"duzelt": 1, "kabul": 2, "red": 1}
    assert ozet.b_sayilari == {"duzelt": 2, "kabul": 1, "red": 1}


def test_kappa_sinir_durumlari() -> None:
    assert uyum.cohen_kappa(["x", "y"], ["x", "y"]) == 1.0  # tam uyum
    assert uyum.cohen_kappa(["x", "y"], ["y", "x"]) == -1.0  # p_o = 0, p_e = 1/2
    assert uyum.cohen_kappa(["x", "x", "y", "y"], ["x", "y", "x", "y"]) == 0.0  # sans duzeyi


def test_kappa_tek_kategori_payda_sifir_belgelenmis_davranis() -> None:
    # iki degerlendirici de hep ayni tek etiket: p_e = 1, payda 0 -> kappa 1,0 ama hedef gecmez.
    assert uyum.cohen_kappa(["kabul"] * 5, ["kabul"] * 5) == 1.0
    ozet = uyum.kappa_ozet(["kabul"] * 5, ["kabul"] * 5)
    assert ozet.tek_kategori is True and ozet.gecti is False


def test_kappa_birinin_tek_kategorisi_payda_sifir_degil() -> None:
    # A hep kabul, B karisik: p_e < 1; kappa 0 (A degisken degil, uyum sans duzeyinde).
    a = ["kabul"] * 4
    b = ["kabul", "kabul", "red", "red"]
    ozet = uyum.kappa_ozet(a, b)
    assert ozet.tek_kategori is False
    assert ozet.kappa == 0.0  # p_o = 1/2, p_e = 1/2


def test_kappa_hedef_tam_sinirda_kayan_nokta_gurultusu_yok() -> None:
    # n = 10; p_o = 8/10, p_e = 1/2 -> kappa = 3/5 tam; hedef >= 3/5 gecer.
    a = ["x"] * 5 + ["y"] * 5
    b = ["x"] * 4 + ["y"] + ["y"] * 4 + ["x"]
    ozet = uyum.kappa_ozet(a, b)
    assert ozet.uyum_sayisi == 8
    assert Fraction(ozet.kappa).limit_denominator(1000) == Fraction(3, 5)
    assert ozet.gecti is True
    # bir madde daha ayrisinca 0,4 olur
    b2 = ["x"] * 3 + ["y", "y"] + ["y"] * 3 + ["x", "x"]
    assert uyum.kappa_ozet(a, b2).gecti is False


def test_kappa_girdi_hatalari() -> None:
    with pytest.raises(GirdiHatasi):
        uyum.cohen_kappa([], [])
    with pytest.raises(GirdiHatasi):
        uyum.cohen_kappa(["a"], ["a", "b"])


def test_kappa_ozellik_aralik_ve_simetri() -> None:
    rng = random.Random(17)
    etiketler = ("kabul", "duzelt", "red")
    for _ in range(300):
        n = rng.randint(1, 60)
        a = [rng.choice(etiketler) for _ in range(n)]
        b = [rng.choice(etiketler) for _ in range(n)]
        k = uyum.cohen_kappa(a, b)
        assert -1.0 <= k <= 1.0
        assert k == uyum.cohen_kappa(b, a)  # iki degerlendirici yer degistirebilir


def test_kappa_etiket_adlari_yerel_ayardan_bagimsiz() -> None:
    # Etiketler oldugu gibi karsilastirilir (Turkce I/i buyuk-kucuk harf eslemesi yok).
    assert uyum.cohen_kappa(["I", "i"], ["i", "I"]) == -1.0
    dotted, dotless = chr(0x130), chr(0x131)  # Turkce I
    assert uyum.cohen_kappa([dotted, dotless], [dotted, dotless]) == 1.0


# --- Wilson ------------------------------------------------------------------------------------


def test_z_sabiti_hesaplanir() -> None:
    assert NormalDist().inv_cdf(0.975) == uyum.Z_95
    assert pytest.approx(1.959964, abs=1e-6) == uyum.Z_95


def test_wilson_bilinen_degerler() -> None:
    z2 = uyum.Z_95**2
    # hata = 0: ust sinir = z^2 / (n + z^2); 0/10 icin 0,2775 (Brown, Cai, DasGupta 2001 tablosu)
    assert uyum.wilson_ust_sinir(0, 10) == pytest.approx(z2 / (10 + z2), abs=1e-15)
    assert uyum.wilson_ust_sinir(0, 10) == pytest.approx(0.2775, abs=1e-4)
    assert uyum.wilson_ust_sinir(0, 300) == pytest.approx(z2 / (300 + z2), abs=1e-15)
    # 5/10: simetrik aralik [0,2366; 0,7634]
    assert uyum.wilson_alt_sinir(5, 10) == pytest.approx(0.2366, abs=1e-4)
    assert uyum.wilson_ust_sinir(5, 10) == pytest.approx(0.7634, abs=1e-4)
    assert uyum.wilson_ust_sinir(1, 10) == pytest.approx(0.4042, abs=1e-4)
    assert uyum.wilson_alt_sinir(1, 10) == pytest.approx(0.0179, abs=1e-4)


def test_wilson_sinir_durumlari() -> None:
    assert uyum.wilson_ust_sinir(0, 0) == 1.0  # bilgi yok
    assert uyum.wilson_alt_sinir(0, 0) == 0.0
    for n in (1, 2, 10, 300, 10_000_000):
        assert uyum.wilson_ust_sinir(n, n) == 1.0  # hata = n
        assert 0.0 < uyum.wilson_ust_sinir(0, n) < 1.0
        assert uyum.wilson_alt_sinir(0, n) == pytest.approx(0.0, abs=1e-12)
    with pytest.raises(GirdiHatasi):
        uyum.wilson_ust_sinir(-1, 10)
    with pytest.raises(GirdiHatasi):
        uyum.wilson_ust_sinir(11, 10)
    with pytest.raises(GirdiHatasi):
        uyum.wilson_ust_sinir(1, -1)


def test_wilson_ozellik_ust_sinir_gozlenenden_kucuk_degil() -> None:
    for n in (1, 2, 5, 30, 300, 1000):
        onceki = -1.0
        for hata in range(n + 1):
            ust = uyum.wilson_ust_sinir(hata, n)
            alt = uyum.wilson_alt_sinir(hata, n)
            assert 0.0 <= alt <= hata / n <= ust <= 1.0
            assert ust >= onceki  # hata arttikca ust sinir azalmaz
            onceki = ust


def test_wilson_ozellik_n_buyudukce_daralir() -> None:
    for oran_pay, oran_payda in ((0, 1), (1, 10), (1, 2), (1, 50)):
        onceki = math.inf
        for n in (10, 100, 1000, 10_000):
            hata = n * oran_pay // oran_payda
            genislik = uyum.wilson_ust_sinir(hata, n) - uyum.wilson_alt_sinir(hata, n)
            assert genislik < onceki
            onceki = genislik
    # sabit gozlenen oran: ust sinir gozlenen orana yaklasir
    assert uyum.wilson_ust_sinir(10, 1000) < uyum.wilson_ust_sinir(1, 100)  # ayni oran %1


# --- ikinci okuma boyu ve ozeti ---------------------------------------------------------------


def test_ikinci_okuma_boyu_kural() -> None:
    assert uyum.ikinci_okuma_boyu(0) == 0
    assert uyum.ikinci_okuma_boyu(1) == 1  # evren kucukse tamami
    assert uyum.ikinci_okuma_boyu(299) == 299
    assert uyum.ikinci_okuma_boyu(300) == 300
    assert uyum.ikinci_okuma_boyu(2999) == 300
    assert uyum.ikinci_okuma_boyu(3000) == 300
    assert uyum.ikinci_okuma_boyu(3001) == 301  # ceil(300,1)
    assert uyum.ikinci_okuma_boyu(12345) == 1235
    with pytest.raises(GirdiHatasi):
        uyum.ikinci_okuma_boyu(-1)


def test_ikinci_okuma_boyu_tam_sayi_tavan_kesirle_ayni() -> None:
    assert uyum.ikinci_okuma_boyu(3010) == 301
    for n in range(0, 20_001):
        beklenen = min(n, max(300, math.ceil(Fraction(n, 10))))
        assert uyum.ikinci_okuma_boyu(n) == beklenen


def test_ikinci_okuma_ozet_hata_yok() -> None:
    ozet = uyum.ikinci_okuma_ozet(["dogru"] * 300, 1000)
    assert (ozet.gereken, ozet.okunan, ozet.yanlis) == (300, 300, 0)
    assert ozet.wilson_ust_95 == pytest.approx(uyum.Z_95**2 / (300 + uyum.Z_95**2), abs=1e-15)
    assert ozet.wilson_ust_95 == pytest.approx(0.01264, abs=1e-5)
    assert ozet.yeterli_orneklem and ozet.hedef_saglandi and ozet.gecti


def test_ikinci_okuma_ozet_esik_yaninda() -> None:
    bir = uyum.ikinci_okuma_ozet(["dogru"] * 299 + ["yanlis"], 1000)
    assert bir.wilson_ust_95 == pytest.approx(0.01864, abs=1e-5)  # <= %2
    assert bir.gecti is True
    iki = uyum.ikinci_okuma_ozet(["dogru"] * 298 + ["yanlis"] * 2, 1000)
    assert iki.wilson_ust_95 == pytest.approx(0.02398, abs=1e-5)  # > %2
    assert iki.hedef_saglandi is False and iki.gecti is False
    assert iki.yanlis_orani == pytest.approx(2 / 300)


def test_ikinci_okuma_kucuk_hata_wilson_a_girmez() -> None:
    ozet = uyum.ikinci_okuma_ozet(["dogru"] * 290 + ["kucuk_hata"] * 10, 1000)
    assert (ozet.kucuk_hata, ozet.yanlis) == (10, 0)
    assert ozet.gecti is True


def test_ikinci_okuma_yetersiz_orneklem_gecmez() -> None:
    ozet = uyum.ikinci_okuma_ozet(["dogru"] * 299, 2000)  # 300 gerekir
    assert ozet.hedef_saglandi is True and ozet.yeterli_orneklem is False
    assert ozet.gecti is False
    buyuk = uyum.ikinci_okuma_ozet(["dogru"] * 300, 4000)  # %10 = 400 gerekir
    assert buyuk.gereken == 400 and buyuk.gecti is False


def test_ikinci_okuma_kucuk_evren_tamami_okunursa_yeterli() -> None:
    ozet = uyum.ikinci_okuma_ozet(["dogru"] * 120, 120)
    assert ozet.gereken == 120 and ozet.yeterli_orneklem
    assert ozet.wilson_ust_95 > uyum.WILSON_HEDEF  # 120 okumada hedef ust sinir tutmaz
    assert ozet.gecti is False


def test_ikinci_okuma_bos_ve_hatali_girdi() -> None:
    bos = uyum.ikinci_okuma_ozet([], 1000)
    assert bos.okunan == 0 and bos.wilson_ust_95 == 1.0 and bos.gecti is False
    assert bos.yanlis_orani == 0.0
    tum_yanlis = uyum.ikinci_okuma_ozet(["yanlis"] * 300, 300)
    assert tum_yanlis.wilson_ust_95 == 1.0 and tum_yanlis.gecti is False
    with pytest.raises(GirdiHatasi):
        uyum.ikinci_okuma_ozet(["dogru", "hata"], 10)  # tanimsiz etiket
    with pytest.raises(GirdiHatasi):
        uyum.ikinci_okuma_ozet(["dogru"] * 11, 10)  # evrenden fazla


def test_sozluk_yalniz_sayi_ve_sonuc() -> None:
    for sozluk in (
        uyum.kappa_ozet(["kabul", "red"], ["kabul", "red"]).sozluk(),
        uyum.ikinci_okuma_ozet(["dogru"] * 300, 300).sozluk(),
    ):
        for deger in sozluk.values():
            assert isinstance(deger, bool | int | float | dict)
