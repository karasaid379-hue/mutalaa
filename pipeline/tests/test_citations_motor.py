# ruff: noqa: RUF001
"""Atif ve iktibas motoru (A18.4): kisa ve kalip kurallari, sinyaller, guven, skor, evidence.

SENTETIK dunya (`citations_yardimci`): Arapca "kelimeler" anlamsiz harf dizileri, Turkce metin
"Deneme paragrafi ...". Veritabani gerekmez (indeks bellekte kurulur).
"""

from collections import Counter

import pytest
from citations_yardimci import (
    AYET_TOKENLERI,
    CAPALAR,
    KALIP,
    ayet_ozeti,
    indeksler,
    paragraf,
)
from links_yardimci import sozcuk

from mutalaa_pipeline.enrich.citations import iktibas as ik
from mutalaa_pipeline.enrich.citations.gramer import AdSozlugu
from mutalaa_pipeline.enrich.citations.kalip import kalip_mi
from mutalaa_pipeline.enrich.citations.kurallar import (
    Ipuclari,
    Sinyaller,
    guven_hesapla,
    iktibas_puani,
    ipuclari_oku,
    ipucu_var,
    meal_benzerligi,
    sinif_ipucu,
)
from mutalaa_pipeline.enrich.citations.normalizasyon import anahtar_dizisi

U, IMLAI = indeksler()
IPUCLARI = ipuclari_oku()


def ar(capa: str, bas: int = 0, son: int | None = None) -> str:
    return " ".join(AYET_TOKENLERI[capa][bas:son])


def girdi(
    kalip: frozenset[str] = frozenset(),
    *,
    ipuclari: Ipuclari = IPUCLARI,
    sozluk: AdSozlugu | None = None,
    meal: dict[int, str] | None = None,
    lemma: dict[str, frozenset[int]] | None = None,
) -> ik.MotorGirdisi:
    return ik.MotorGirdisi(
        indeksler=[U, IMLAI],
        ayet_capalari=CAPALAR,
        ayet_ozetleri=[ayet_ozeti(c) for c in CAPALAR],
        kalip=kalip,
        ipuclari=ipuclari,
        sozluk=sozluk,
        meal_metni=(meal or {}).get,
        lemma_sozlugu=lemma or {},
    )


def isle(
    metin: str, g: ik.MotorGirdisi | None = None, role: str = "govde"
) -> tuple[list[ik.AdayHat], Counter[str]]:
    sayac: Counter[str] = Counter()
    sonuc = ik.birim_isle(g or girdi(), ik.Birim("meal:elmalili:2:1", metin, "a" * 16, role), sayac)
    return sonuc, sayac


def iktibaslar(satirlar: list[ik.AdayHat]) -> dict[str, ik.AdayHat]:
    return {CAPALAR[h.dst_sira]: h for h in satirlar if h.tur == "iktibas"}


# --- tam, kismi, duzenleme, ardisik --------------------------------------------------------------


def test_tam_ayet_alintisi_ve_evidence_sozlesmesi() -> None:
    metin = paragraf(ar("q:2:1"), "Deneme paragrafi 2.")
    satirlar, _ = isle(metin)
    (h,) = satirlar
    assert h.tur == "iktibas" and CAPALAR[h.dst_sira] == "q:2:1"
    assert metin[h.src_span[0] : h.src_span[1]] == ar("q:2:1")  # kod noktasi, yari acik
    assert h.dst_span == (1, 11)  # QAC kelime konumu [ilk, son + 1)
    e = h.evidence
    assert set(e) == {
        "matched_words",
        "ayah_words",
        "coverage",
        "identity",
        "edits",
        "index",
        "phrase_freq",
        "position",
        "phrase_key",
        "src_hash",
        "dst_hash",
        "source_id",
        "src_span",
    }
    assert (e["matched_words"], e["ayah_words"], e["coverage"], e["identity"], e["edits"]) == (
        10,
        10,
        1.0,
        1.0,
        0,
    )
    assert (e["index"], e["phrase_freq"], e["position"]) == ("uthmani", 1, "metin")
    assert e["source_id"] == "tanzil-uthmani"
    assert e["phrase_key"] == " ".join(anahtar_dizisi(ar("q:2:1")))
    assert e["src_hash"] == "a" * 16 and e["dst_hash"] == ayet_ozeti("q:2:1")
    assert e["src_span"] == list(h.src_span)
    assert h.score == pytest.approx(1.0) and h.confidence == pytest.approx(0.90)


def test_kismi_alinti_skor_ve_kapsama() -> None:
    (h,) = isle(paragraf(ar("q:2:2", 3, 9)))[0]
    e = h.evidence
    assert (e["matched_words"], e["coverage"]) == (6, 0.6)
    assert h.dst_span == (4, 10)
    assert h.score == pytest.approx((0.5 + 0.5 * 0.6) * (6 / 7))


def test_bir_iki_duzenleme_identity_ve_edits() -> None:
    tokenler = list(AYET_TOKENLERI["q:3:2"])
    tokenler[1] = tokenler[1][:-1]
    tokenler[6] = tokenler[6][:-1]
    (h,) = isle(paragraf(" ".join(tokenler)))[0]
    e = h.evidence
    assert (e["matched_words"], e["edits"], e["identity"]) == (8, 2, 0.8)
    assert h.score == pytest.approx(1.0 * 1.0 * 0.8)


def test_ardisik_ayet_her_ayete_ayri_satir_ve_group() -> None:
    metin = paragraf(ar("q:2:1", 6) + " " + ar("q:2:2", 0, 5))
    h = iktibaslar(isle(metin)[0])
    assert set(h) == {"q:2:1", "q:2:2"}
    assert h["q:2:1"].dst_span == (7, 11) and h["q:2:2"].dst_span == (1, 6)
    assert h["q:2:1"].evidence["group"] == h["q:2:2"].evidence["group"]
    assert h["q:2:1"].src_span[1] < h["q:2:2"].src_span[0]  # kaynak araliklari ayri
    assert all(metin[a.src_span[0] : a.src_span[1]] for a in h.values())
    assert h["q:2:1"].evidence["matched_words"] == 4 and h["q:2:2"].evidence["matched_words"] == 5


def test_imlai_indeks_ve_konum_belirsiz() -> None:
    from citations_yardimci import besmele_kirp, simple_metni

    imlai = " ".join(besmele_kirp("q:3:1", simple_metni("q:3:1").split()))
    (h,) = isle(paragraf(imlai))[0]
    assert h.evidence["index"] == "imlai" and h.evidence["source_id"] == "tanzil-simple-clean"
    assert h.evidence["konum_belirsiz"] is True and h.dst_span == (1, 11)
    assert h.evidence["matched_words"] == 9


def test_arapca_olmayan_birim_satir_uretmez() -> None:
    satirlar, sayac = isle("Deneme paragrafi 1. Hicbir Arapca dizi yok.")
    assert satirlar == [] and sayac["arapca_dizi"] == 0


def test_cok_kisa_dizi_ayet_degilse_satir_yok() -> None:
    satirlar, sayac = isle(paragraf(ar("q:2:1", 0, 3)))  # ayetin yalniz bir parcasi
    assert satirlar == [] and sayac["dizi_kisa_tam_ayet_yok"] == 1


def test_tam_ayet_karmasi_kisa_ayet_baglamsiz_satir_yok() -> None:
    satirlar, sayac = isle(paragraf(ar("q:3:4")))
    assert satirlar == [] and sayac["tam_ayet_kisa_dizi"] == 1
    assert sayac["kisa_baglamsiz_satir_yok"] == 2  # f = 2 (q:3:4 ve q:3:5)


def test_tam_ayet_karmasi_kisa_ayet_baglamli_aday() -> None:
    h = iktibaslar(isle(paragraf("Bu âyet-i kerîme:", ar("q:3:4")))[0])
    assert set(h) == {"q:3:4", "q:3:5"}
    for x in h.values():
        assert x.evidence["matched_words"] == 3 and x.evidence["coverage"] == 1.0
        assert x.evidence["phrase_freq"] == 2 and x.dst_span == (1, 4)
        assert x.score == pytest.approx(iktibas_puani(3, 3, 0, 2))
        assert x.confidence < 0.5


def test_bilinmeyen_dizi_eslesmesiz() -> None:
    dizi = " ".join(sozcuk(i) for i in range(900, 906))
    satirlar, sayac = isle(paragraf(dizi))
    assert satirlar == [] and sayac["dizi_eslesmesiz"] == 1


# --- kisa ve kalip kurallari (§7) -----------------------------------------------------------


def kisa_bolunmus(ayet_a: str = "q:2:1", ayet_b: str = "q:2:2") -> str:
    """2 + 2 kelime: iki ayetin sinirinda dort kelimelik dizi (her parca n = 2)."""
    return ar(ayet_a, 8) + " " + ar(ayet_b, 0, 2)


def test_kisa_n_baglamsiz_satir_yok() -> None:
    satirlar, sayac = isle(paragraf(kisa_bolunmus()))
    assert satirlar == [] and sayac["kisa_baglamsiz_satir_yok"] == 2


def test_kisa_n_baglamli_dusuk_guvenli_aday() -> None:
    metin = paragraf("Bu bir âyet-i kerîme:", kisa_bolunmus())  # Kur'an ipucu: bagam sinyali
    satirlar, sayac = isle(metin)
    h = iktibaslar(satirlar)
    assert set(h) == {"q:2:1", "q:2:2"} and sayac["kisa_baglamli_aday"] == 2
    for x in h.values():
        assert x.evidence["matched_words"] == 2
        assert x.evidence["context"] == {"kuran_ipucu": True}  # type: ignore[comparison-overlap]
        assert x.confidence < 0.5  # dusuk guven


def test_kalip_listesindeki_dizi_otomatik_satir_yok() -> None:
    kalip = " ".join(anahtar_dizisi(" ".join(sozcuk(i) for i in KALIP)))
    metin = paragraf(" ".join(sozcuk(i) for i in KALIP))
    satirlar, sayac = isle(metin, girdi(frozenset({kalip})))
    assert satirlar == [] and sayac["kalip_listesinde_kume"] == 1
    assert isle(metin)[0]  # liste bossa satirlar uretilir


def test_kalip_mi_alt_dizi_sayilir() -> None:
    assert kalip_mi("b c", frozenset({"a b c d"})) and not kalip_mi(
        "a b c d e", frozenset({"a b c d"})
    )
    assert kalip_mi("a b", frozenset({"a b"})) and not kalip_mi("a", frozenset())


def test_f1_degil_baglam_yok_en_cok_uc_hedef_her_biri_1_f() -> None:
    metin = paragraf(" ".join(sozcuk(i) for i in KALIP))
    satirlar, sayac = isle(metin)
    h = iktibaslar(satirlar)
    assert len(h) == 3 and sayac["f_baglamsiz_en_cok_3"] == 1  # f = 4, en cok 3 hedef
    assert set(h) <= {"q:2:4", "q:2:5", "q:2:6", "q:3:3"}
    for x in h.values():
        assert x.evidence["phrase_freq"] == 4
        # n = N' ise kapsama = 6/N; skor 1/f ile bolunur (f = 4)
        n, big_n = x.evidence["matched_words"], x.evidence["ayah_words"]
        assert x.score == pytest.approx(iktibas_puani(int(n), int(big_n), 0, 4))  # type: ignore[arg-type]
        assert x.confidence < 0.3
        assert isinstance(x.evidence["alternatives"], list) and x.evidence["alternatives"]


def test_f1_degil_acik_atif_tek_hedef_secer() -> None:
    metin = paragraf(" ".join(sozcuk(i) for i in KALIP), "(2:5)")
    satirlar, sayac = isle(metin)
    h = iktibaslar(satirlar)
    assert set(h) == {"q:2:5"} and sayac["f_baglam_tek_hedef"] == 1
    x = h["q:2:5"]
    assert x.score == pytest.approx(iktibas_puani(6, 9, 0, 1))  # baglam tek hedef: f = 1
    assert x.evidence["phrase_freq"] == 4  # gozlenen f yine kanitta
    assert x.evidence["consistent_quote"] is True and x.confidence == pytest.approx(0.99)
    dst = {a["dst_anchor"] for a in x.evidence["alternatives"]}  # type: ignore[union-attr]
    assert {"q:2:4", "q:2:6", "q:3:3"} <= dst


def test_f1_degil_komsu_ayet_tek_hedef_secer() -> None:
    # q:2:1 benzersiz iktibas; q:2:4 yalniz ona 3 ayet uzakta (2:5: 4, 2:6: 5, 3:3: baska sure)
    metin = paragraf(ar("q:2:1"), "ve", " ".join(sozcuk(i) for i in KALIP))
    h = iktibaslar(isle(metin)[0])
    assert set(h) == {"q:2:1", "q:2:4"}
    assert h["q:2:4"].evidence["context"] == {"komsu_ayet": True}  # type: ignore[comparison-overlap]
    assert h["q:2:4"].evidence["phrase_freq"] == 4
    assert h["q:2:1"].evidence["context"] == {"komsu_ayet": True}  # type: ignore[comparison-overlap]


def test_f1_degil_meal_benzerligi_tek_hedef_secer() -> None:
    g = girdi(
        meal={CAPALAR.index("q:2:6"): "uc dort bes alti yedi", CAPALAR.index("q:2:4"): "bir iki"},
        lemma={
            k: frozenset({i})
            for i, k in enumerate(["bir", "iki", "uc", "dort", "bes", "alti", "yedi"])
        },
    )
    metin = paragraf(" ".join(sozcuk(i) for i in KALIP), "Deneme uc dort bes alti sekiz.")
    h = iktibaslar(isle(metin, g)[0])
    assert set(h) == {"q:2:6"}
    assert h["q:2:6"].evidence["context"] == {
        "meal_benzerligi": h["q:2:6"].evidence["context"]["meal_benzerligi"]
    }  # type: ignore[index]


# --- baglam sinyalleri ve guven (§8) -----------------------------------------------------


def test_acik_atif_ayni_ayet_tutarli_guven_099() -> None:
    metin = paragraf(ar("q:2:2", 0, 5), "(2:2)")
    satirlar, _ = isle(metin)
    atif = next(h for h in satirlar if h.tur == "atif")
    (ik_satir,) = (h for h in satirlar if h.tur == "iktibas")
    for h in (atif, ik_satir):
        assert h.evidence["consistent_quote"] is True and h.confidence == pytest.approx(0.99)
    assert atif.score == 1.0 and atif.dst_span is None and atif.evidence["bicim"] == "sayisal"
    assert metin[atif.src_span[0] : atif.src_span[1]] == "(2:2)"


def test_acik_atif_baska_ayete_tutarsiz_guven_030() -> None:
    metin = paragraf(ar("q:2:2", 0, 5), "(2:3)")
    satirlar, _ = isle(metin)
    for h in satirlar:
        assert h.evidence["consistent_quote"] is False and h.confidence == pytest.approx(0.30)


def test_atif_200_karakterden_uzaksa_baglam_yok() -> None:
    metin = paragraf(ar("q:2:2", 0, 5), "Deneme " * 40, "(2:3)")
    satirlar, _ = isle(metin)
    for h in satirlar:
        assert "consistent_quote" not in h.evidence
    atif = next(h for h in satirlar if h.tur == "atif")
    assert atif.confidence == 0.90  # yalniz sayisal parantez bicimi


def test_atif_grubunda_bir_ayet_tutarliysa_digerleri_isaretsiz() -> None:
    metin = paragraf(ar("q:2:2"), "(2:1-3)")
    satirlar, _ = isle(metin)
    atif = {CAPALAR[h.dst_sira]: h for h in satirlar if h.tur == "atif"}
    assert atif["q:2:2"].evidence["consistent_quote"] is True
    assert "consistent_quote" not in atif["q:2:1"].evidence
    assert (
        atif["q:2:1"].confidence == 0.90
        and atif["q:2:1"].evidence["group"] == atif["q:2:3"].evidence["group"]
    )


def test_komsu_ayet_etkisi() -> None:
    ayri = isle(paragraf(ar("q:2:2", 0, 5)))[0][0]
    cift = iktibaslar(isle(paragraf(ar("q:2:2", 0, 5), "ve", ar("q:2:3", 0, 7)))[0])
    assert cift["q:2:2"].confidence == pytest.approx(ayri.confidence + 0.15)
    assert cift["q:2:2"].evidence["context"] == {"komsu_ayet": True}  # type: ignore[comparison-overlap]


def test_ipucu_konum_ve_ters_ipucu_etkileri() -> None:
    taban = isle(paragraf(ar("q:2:2", 0, 5)))[0][0].confidence
    kuran = isle(paragraf("sırrınca", ar("q:2:2", 0, 5)))[0][0]
    ters = isle(paragraf("hadîs-i şerif", ar("q:2:2", 0, 5)))[0][0]
    baslik = isle(paragraf(ar("q:2:2", 0, 5)), role="baslik")[0][0]
    suslu = isle(paragraf("﴿" + ar("q:2:2", 0, 5) + "﴾"))[0][0]
    assert kuran.confidence == pytest.approx(taban + 0.10)
    assert ters.confidence == pytest.approx(taban - 0.20)
    assert (
        baslik.confidence == pytest.approx(taban + 0.10) and baslik.evidence["position"] == "baslik"
    )
    assert suslu.confidence == pytest.approx(taban + 0.10)
    assert suslu.evidence["context"] == {"konum": True, "suslu_parantez": True}  # type: ignore[comparison-overlap]
    assert ters.evidence["context"] == {"ters_ipucu": True}  # type: ignore[comparison-overlap]


def test_meal_benzerligi_etkisi_ve_sinyal_yok_hali() -> None:
    capa_sira = CAPALAR.index("q:2:2")
    lemma = {k: frozenset({i}) for i, k in enumerate(["bir", "iki", "uc", "dort"])}
    takip = "Deneme bir iki uc."
    taban = isle(paragraf(ar("q:2:2", 0, 5), takip))[0][0].confidence
    g = girdi(meal={capa_sira: "bir iki uc dort"}, lemma=lemma)
    h = isle(paragraf(ar("q:2:2", 0, 5), takip), g)[0][0]
    assert h.confidence == pytest.approx(taban + 0.15)
    # lemma sozlugu bos (tr_form yok): sinyal yok
    assert (
        isle(paragraf(ar("q:2:2", 0, 5), takip), girdi(meal={capa_sira: "bir iki"}))[0][
            0
        ].confidence
        == taban
    )


def test_meal_benzerligi_esik_ve_en_az_iki_ortak() -> None:
    lemma = {k: frozenset({i}) for i, k in enumerate(["a", "b", "c", "d", "e"])}
    assert meal_benzerligi("a b c", "a b", lemma) == 1.0
    assert meal_benzerligi("a x y", "a b", lemma) is None  # tek ortak lemma
    assert meal_benzerligi("a b c d", "a b e", lemma) == pytest.approx(2 / 3)
    assert meal_benzerligi("a b", None, lemma) is None and meal_benzerligi("a b", "a b", {}) is None


def test_guven_tavani_ve_sinirlari() -> None:
    s = Sinyaller(komsu=True, meal_benzerligi=0.8, kuran_ipucu=True, konum=True)
    assert guven_hesapla(1.0, s, tutarli=None) == 0.98
    assert guven_hesapla(0.1, Sinyaller(ters_ipucu=True), tutarli=None) == 0.0
    assert guven_hesapla(0.5, s, tutarli=False) == 0.30
    assert guven_hesapla(0.5, Sinyaller(), tutarli=True) == 0.99


# --- skor, sinif, ipucu listeleri ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("n", "n_buyuk", "e", "f", "beklenen"),
    [
        (7, 7, 0, 1, 1.0),
        (7, 14, 0, 1, 0.75),  # (0,5 + 0,5 * 7/14) * 1
        (4, 8, 0, 1, (0.5 + 0.25) * 4 / 7),
        (8, 8, 2, 1, 0.8),
        (6, 6, 0, 4, 6 / 7 / 4),
        (0, 5, 0, 1, 0.0),
    ],
)
def test_skor_formulu(n: int, n_buyuk: int, e: int, f: int, beklenen: float) -> None:
    assert iktibas_puani(n, n_buyuk, e, f) == pytest.approx(beklenen)


def test_sinif_ipucu_sunucu_kurallarinin_aynasi() -> None:
    kw = {"matched_words": 8, "coverage": 1.0, "phrase_freq": 1, "consistent_quote": None}
    assert sinif_ipucu("iktibas", 0.96, **kw) == "toplu"  # type: ignore[arg-type]
    assert sinif_ipucu("iktibas", 0.90, **kw) == "diger"  # type: ignore[arg-type]
    assert sinif_ipucu("iktibas", 0.90, **{**kw, "consistent_quote": True}) == "toplu"  # type: ignore[arg-type]
    assert sinif_ipucu("iktibas", 0.99, **{**kw, "consistent_quote": False}) == "tutarsiz"  # type: ignore[arg-type]
    assert (
        sinif_ipucu(
            "atif", 0.30, matched_words=None, coverage=None, phrase_freq=None, consistent_quote=None
        )
        == "tutarsiz"
    )
    assert sinif_ipucu("iktibas", 0.60, **{**kw, "matched_words": 5}) == "gri"  # type: ignore[arg-type]
    assert sinif_ipucu("iktibas", 0.80, **{**kw, "matched_words": 5}) == "diger"  # type: ignore[arg-type]


def test_ipuclari_dosyasi_ve_eslesme() -> None:
    assert IPUCLARI.kuran and IPUCLARI.ters
    assert ipucu_var("Bu ÂYET-i Kerîme dir", IPUCLARI.kuran)
    assert ipucu_var("hadîs-i şerif", IPUCLARI.ters) and not ipucu_var(
        "hadis degil", IPUCLARI.kuran
    )
    assert not ipucu_var("", IPUCLARI.kuran)
