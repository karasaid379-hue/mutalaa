"""`qa/gold/olcum.py`: prf, aciklik esleme, kappa, gerileme kurali, kapi esikleri (A18.5).

Saf islevler; SENTETIK etiketler; beklenen degerler elle hesaplanmistir.
"""

import pytest

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa import uyum
from mutalaa_pipeline.qa.gold import olcum
from mutalaa_pipeline.qa.gold.olcum import ReferansAciklik, TahminAciklik

# --- prf -----------------------------------------------------------------------------------------


def _belge_prf(pred: set[str], gold: set[str]) -> tuple[float, float, float]:
    """Test stratejisi §4 kod parcasi (belgedeki tanim)."""
    tp = len(pred & gold)
    p = tp / len(pred) if pred else 1.0
    r = tp / len(gold) if gold else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


@pytest.mark.parametrize(
    ("tahmin", "referans"),
    [
        ({"a", "b", "c"}, {"a", "b", "d", "e"}),  # karisik
        ({"a", "b"}, {"a", "b"}),  # tam
        (set(), {"a", "b"}),  # tahmin bos: kesinlik 1, duyarlilik 0
        ({"a", "b"}, set()),  # referans bos: kesinlik 0, duyarlilik 1
        (set(), set()),  # ikisi de bos
        ({"x"}, {"y"}),  # ayrik: p = r = 0
    ],
)
def test_prf_belgedeki_tanimla_ayni(tahmin: set[str], referans: set[str]) -> None:
    sonuc = olcum.prf(tahmin, referans)
    p, r, f = _belge_prf(tahmin, referans)
    assert (sonuc.kesinlik, sonuc.duyarlilik) == (pytest.approx(p), pytest.approx(r))
    assert sonuc.f1 == pytest.approx(f)
    assert (sonuc.tp, sonuc.fp, sonuc.fn) == (
        len(tahmin & referans),
        len(tahmin - referans),
        len(referans - tahmin),
    )


def test_prf_elle_hesap() -> None:
    # tp = 2 (a, b), fp = 1 (c), fn = 2 (d, e): p = 2/3, r = 1/2, f1 = 4/7
    sonuc = olcum.prf({"a", "b", "c"}, {"a", "b", "d", "e"})
    assert sonuc.kesinlik == pytest.approx(2 / 3)
    assert sonuc.duyarlilik == pytest.approx(1 / 2)
    assert sonuc.f1 == pytest.approx(4 / 7)


def test_prf_sifira_bolme_kurallari() -> None:
    assert olcum.prf(set(), {"a"}).kesinlik == 1.0
    assert olcum.prf(set(), {"a"}).f1 == 0.0
    assert olcum.prf({"a"}, set()).duyarlilik == 1.0
    assert olcum.prf({"a"}, set()).f1 == 0.0
    bos = olcum.prf(set(), set())
    assert (bos.kesinlik, bos.duyarlilik, bos.f1) == (1.0, 1.0, 1.0)


def test_prf_sayimdan_sifira_bolme_ve_tutarsizlik() -> None:
    assert olcum.prf_sayimdan(0, 0, 0, 0).f1 == 1.0  # ikisi de bos
    s = olcum.prf_sayimdan(3, 4, 3, 6)
    assert (s.kesinlik, s.duyarlilik) == (0.75, 0.5)
    assert s.f1 == pytest.approx(0.6)
    assert olcum.prf_sayimdan(0, 0, 0, 5).kesinlik == 1.0  # tahmin yok
    assert olcum.prf_sayimdan(0, 5, 0, 0).duyarlilik == 1.0  # referans yok
    assert olcum.prf_sayimdan(0, 5, 0, 5).f1 == 0.0  # p = r = 0
    with pytest.raises(GirdiHatasi):
        olcum.prf_sayimdan(5, 4, 0, 0)


# --- aciklik esleme ------------------------------------------------------------------------------


def test_iou_yari_acik_elle_hesap() -> None:
    assert olcum.iou(0, 10, 0, 10) == 1.0
    assert olcum.iou(0, 10, 5, 15) == pytest.approx(5 / 15)
    assert olcum.iou(0, 10, 10, 20) == 0.0  # yari acik: ortak kod noktasi yok
    assert olcum.iou(0, 10, 2, 6) == pytest.approx(4 / 10)  # iceren aralik


def test_iou_gecersiz_aralik_hata() -> None:
    for bas, son in ((5, 5), (6, 5), (-1, 3)):
        with pytest.raises(GirdiHatasi):
            olcum.iou(bas, son, 0, 10)


def test_aciklik_esle_esik_tam_sinirda() -> None:
    ref = [ReferansAciklik(frozenset({"q:2:1"}), 0, 10)]
    # IoU = 5/10 = 0,5 tam esik: eslesir
    assert olcum.aciklik_esle([TahminAciklik("q:2:1", 0, 5)], ref).tahmin_eslesen == (True,)
    # IoU = 4/10 < 0,5
    assert olcum.aciklik_esle([TahminAciklik("q:2:1", 0, 4)], ref).tahmin_eslesen == (False,)


def test_aciklik_esle_ayni_hedef_sarti_ve_cok_hedefli_referans() -> None:
    ref = [ReferansAciklik(frozenset({"q:2:1", "q:3:9"}), 0, 10)]
    tahminler = [
        TahminAciklik("q:2:1", 0, 10),  # dogru hedef
        TahminAciklik("q:3:9", 0, 10),  # ayni dizinin gectigi bir baska ayet: gecerli
        TahminAciklik("q:4:4", 0, 10),  # yanlis hedef
    ]
    s = olcum.aciklik_esle(tahminler, ref)
    assert s.tahmin_eslesen == (True, True, False)
    assert s.referans_eslesen == (True,)
    p = s.prf()
    assert (p.tp, p.fp, p.fn) == (2, 1, 0)  # kesinlik 2/3, duyarlilik 1
    assert p.duyarlilik == 1.0


def test_aciklik_sonucu_kesit_uzun_kisa() -> None:
    ref = [
        ReferansAciklik(frozenset({"a"}), 0, 10),  # uzun
        ReferansAciklik(frozenset({"b"}), 20, 25),  # kisa
    ]
    tah = [TahminAciklik("a", 0, 10), TahminAciklik("x", 20, 25)]
    s = olcum.aciklik_esle(tah, ref)
    uzun = s.prf([True, False], [True, False])
    kisa = s.prf([False, True], [False, True])
    assert (uzun.kesinlik, uzun.duyarlilik) == (1.0, 1.0)
    assert (kisa.kesinlik, kisa.duyarlilik) == (0.0, 0.0)


# --- kappa ---------------------------------------------------------------------------------------


def test_kappa_elle_hesaplanmis_kucuk_ornek() -> None:
    # n = 4, uyum 3 -> p_o = 0,75; A: x2 y2, B: x1 y3 -> p_e = (2*1 + 2*3) / 16 = 0,5
    # kappa = (0,75 - 0,5) / 0,5 = 0,5
    a = ["x", "x", "y", "y"]
    b = ["x", "y", "y", "y"]
    s = olcum.kappa_sklearn(a, b)
    assert s.kappa == pytest.approx(0.5, abs=1e-12)
    assert s.n == 4 and s.tek_kategori is False


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (["x", "x", "y", "y"], ["x", "y", "y", "y"]),
        (["kabul", "kabul", "duzelt", "red"], ["kabul", "duzelt", "duzelt", "red"]),
        (["x", "y"], ["y", "x"]),
        (["a"] * 25 + ["b"] * 25, ["a"] * 20 + ["b"] * 5 + ["a"] * 10 + ["b"] * 15),
    ],
)
def test_kappa_sklearn_uyum_py_ile_ayni(a: list[str], b: list[str]) -> None:
    s = olcum.kappa_sklearn(a, b)
    assert s.kappa == pytest.approx(uyum.cohen_kappa(a, b), abs=1e-12)
    assert s.kappa == pytest.approx(s.kappa_uyum_py, abs=1e-12)


def test_kappa_tek_kategori_ve_hatalar() -> None:
    s = olcum.kappa_sklearn(["x"] * 3, ["x"] * 3)
    assert s.kappa == 1.0 and s.tek_kategori is True  # uyum.py ile ayni belgelenmis davranis
    with pytest.raises(GirdiHatasi):
        olcum.kappa_sklearn([], [])
    with pytest.raises(GirdiHatasi):
        olcum.kappa_sklearn(["x"], ["x", "y"])


# --- gerileme ------------------------------------------------------------------------------------


def test_gerileme_ilk_kosuda_yok() -> None:
    assert olcum.gerilemeleri_bul(None, {"kesinlik": 0.1}) == []


def test_gerileme_esigi_0_02() -> None:
    onceki = {"kesinlik": 0.95, "duyarlilik": 0.90}
    # tam 0,02 dusus: kirmaz; 0,0201 dusus: kirar
    assert olcum.gerilemeleri_bul(onceki, {"kesinlik": 0.93, "duyarlilik": 0.90}) == []
    kirilan = olcum.gerilemeleri_bul(onceki, {"kesinlik": 0.9299, "duyarlilik": 0.91})
    assert [g.olcu for g in kirilan] == ["kesinlik"]
    assert kirilan[0].onceki == 0.95 and kirilan[0].simdiki == 0.9299


def test_gerileme_artis_ve_ortak_olmayan_olcu_kirmaz() -> None:
    assert olcum.gerilemeleri_bul({"a": 0.5}, {"a": 0.9}) == []
    assert olcum.gerilemeleri_bul({"a": 0.9}, {"b": 0.1}) == []


# --- kapi esikleri -------------------------------------------------------------------------------


def test_esik_tablosu_test_stratejisi_4() -> None:
    assert olcum.ESIKLER["kok"] == {"kesinlik": 0.95, "duyarlilik": 0.80}
    assert olcum.ESIKLER["lemma"] == {"tutarlilik": 1.0}
    assert olcum.ESIKLER["benzer_ayet"] == {"kesinlik": 0.90}
    assert olcum.ESIKLER["atif"] == {"kesinlik": 0.98, "duyarlilik": 0.90}
    assert olcum.ESIKLER["iktibas_uzun"] == {"kesinlik": 0.95, "duyarlilik": 0.85}
    assert olcum.ESIKLER["iktibas_kisa"] == {"kesinlik": 0.85}


def test_kapi_karari_esik_ve_sinir() -> None:
    esik = olcum.ESIKLER["kok"]
    assert olcum.kapi_karari(esik, {"kesinlik": 0.95, "duyarlilik": 0.80}) == "gecti"  # esit
    assert olcum.kapi_karari(esik, {"kesinlik": 0.9499, "duyarlilik": 0.99}) == "kaldi"
    assert olcum.kapi_karari(esik, {"kesinlik": 0.99, "duyarlilik": 0.7999}) == "kaldi"
    assert olcum.esik_degerlendir(esik, {"kesinlik": 0.99, "duyarlilik": 0.5}) == {
        "kesinlik": True,
        "duyarlilik": False,
    }


def test_kapi_karari_lemma_yuzde_yuz() -> None:
    esik = olcum.ESIKLER["lemma"]
    assert olcum.kapi_karari(esik, {"tutarlilik": 1.0}) == "gecti"
    assert olcum.kapi_karari(esik, {"tutarlilik": 0.99999}) == "kaldi"


def test_kapi_karari_eksik_olcu_hata() -> None:
    with pytest.raises(GirdiHatasi):
        olcum.kapi_karari({"kesinlik": 0.9}, {})
