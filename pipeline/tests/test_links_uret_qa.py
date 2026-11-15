"""Baglanti uretimi (bellekte) ve QA kapilari (A18.3): SENTETIK dunya, veritabani yok.

`links_yardimci` dunyasi bellekteki `DbGirdisi` olarak kurulur; satirlar staged biciminde uretilir
(ondalik dizgeler), `sayisal` ile sayiya cevrilir ve G-KAY, G-BUT, G-CAP kapilarindan gecirilir.
Bozuk satirlar kapilari dusurmelidir.
"""

import copy
from pathlib import Path

import pytest
from links_yardimci import (
    AYETLER,
    QURSIM,
    QURSIM_SATIRLARI,
    ayet_ozeti,
    csv_yaz,
    morf_kimlikleri,
    simple_metni,
    sozcuk,
)

from mutalaa_pipeline.enrich.baglantilar.girdi import Ayet, DbGirdisi, Kelime
from mutalaa_pipeline.enrich.baglantilar.qursim import qursim_oku
from mutalaa_pipeline.enrich.baglantilar.uret import (
    Girdi,
    ondalik,
    sayisal,
    simple_kelimeleri,
    uret,
)
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.qa.checks.xref import (
    GEREKLI_KAYITLAR,
    KAPI_ISLEVLERI,
    XrefGirdisi,
    satir_hatalari,
)
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

SURUMLER = {
    "kok": "links-kok@1/qac-morfoloji@0.4",
    "lemma": "links-lemma@1/qac-morfoloji@0.4",
    "benzer_ayet": "links-benzer@1/tanzil-uthmani@1.1/qursim@abc12345",
}


def db_girdisi() -> DbGirdisi:
    ayetler = [Ayet(i, ay.capa, ayet_ozeti(ay)[:16]) for i, ay in enumerate(AYETLER)]
    kelimeler = [
        Kelime(i, no, f"{ay.capa}:{no}", sozcuk(tok), kok, lemma)
        for i, ay in enumerate(AYETLER)
        for no, (tok, (kok, lemma)) in enumerate(zip(ay.tokenler, ay.morf, strict=True), start=1)
    ]
    return DbGirdisi(ayetler, kelimeler, morf_kimlikleri()[0])


def uretim(tmp_path: Path, *, qursim: bool = True) -> list[dict[str, object]]:
    db = db_girdisi()
    simple = simple_kelimeleri({ay.capa: simple_metni(ay) for ay in AYETLER}, db.ayetler)
    sonuc = None
    if qursim:
        csv_yaz(tmp_path / "g", QURSIM_SATIRLARI)
        sonuc = qursim_oku(tmp_path / "g" / "QurSim_filtered.csv", db.ayet_sirasi())
    return uret(Girdi(db, simple, sonuc), ("kok", "lemma", "benzer_ayet"), SURUMLER).satirlar


def girdi_kur(satirlar: list[dict[str, object]], **degisim: object) -> XrefGirdisi:
    kayitlar = {
        slug: Kaynak(
            slug=slug,
            tur=SourceKind.MORFOLOJI,
            baslik="Deneme",
            atif_metni="Deneme atif",
            surum="1",
        )
        for slug in GEREKLI_KAYITLAR
    }
    sayilar: dict[str, int] = {}
    for s in satirlar:
        sayilar[str(s["type"])] = sayilar.get(str(s["type"]), 0) + 1
    g = XrefGirdisi(
        kayitlar=kayitlar,
        satirlar=[Satir("t", i, sayisal(s)) for i, s in enumerate(satirlar, start=1)],
        turler=("kok", "lemma", "benzer_ayet"),
        manifest_sayilari=sayilar,
        data_version=SURUMLER,
    )
    for ad, deger in degisim.items():
        setattr(g, ad, deger)
    return g


def bulgular(g: XrefGirdisi, kapi: str) -> tuple[str, ...]:
    return KAPI_ISLEVLERI[kapi](g).bulgular


# --- uretim -----------------------------------------------------------------------------------


def test_uretim_satir_sayilari_ve_sira(tmp_path: Path) -> None:
    satirlar = uretim(tmp_path)
    tur = [str(s["type"]) for s in satirlar]
    assert (tur.count("kok"), tur.count("lemma"), tur.count("benzer_ayet")) == (6, 4, 4)
    sira = [(s["tur_no"], s["src_no"], s["dst_no"]) for s in satirlar]
    assert sira == sorted(sira)  # tur, kaynak ayet, hedef ayet sirasinda
    assert all(s["src_span"] is None and s["dst_span"] is None for s in satirlar)
    assert all(s["score"] == s["confidence"] for s in satirlar)


def test_ondalik_dizgeler_alti_hane_ve_sayiya_donusur(tmp_path: Path) -> None:
    assert ondalik(0.5) == "0.500000" and ondalik(1.0) == "1.000000"
    s = uretim(tmp_path)[0]
    assert isinstance(s["score"], str)
    sayi = sayisal(s)
    assert isinstance(sayi["score"], float) and isinstance(
        sayi["evidence"]["shared"][0]["idf"], float
    )  # type: ignore[index]
    for bozuk in ({**s, "score": 0.5}, {**s, "score": "0.5"}, {**s, "evidence": []}):
        with pytest.raises(ValueError, match=r"ondalik|nesne"):
            sayisal(bozuk)


def test_benzer_ayet_alanlari_ve_qursim_isareti(tmp_path: Path) -> None:
    benzer = {
        (s["src_anchor"], s["dst_anchor"]): s
        for s in uretim(tmp_path)
        if s["type"] == "benzer_ayet"
    }
    assert set(benzer) == {
        ("q:2:4", "q:2:5"),
        ("q:2:7", "q:2:8"),
        ("q:2:1", "q:2:3"),
        ("q:2:2", "q:2:9"),
    }
    sozluksel = benzer[("q:2:4", "q:2:5")]["evidence"]
    assert sozluksel["subtype"] == "sozluksel" and "qursim" not in sozluksel  # type: ignore[operator]
    assert (sozluksel["matched_words"], sozluksel["ayah_words"]) == (4, 5)  # type: ignore[index]
    assert sozluksel["kapsayan"] == "src" and sozluksel["index"] == "uthmani"  # type: ignore[index]
    assert benzer[("q:2:4", "q:2:5")]["score"] == "0.514286"  # 4/7 * (0,5 + 0,5 * 4/5)
    ortak = benzer[("q:2:7", "q:2:8")]["evidence"]
    assert ortak["qursim"] == {"label": 2} and ortak["dongusel"] is True  # type: ignore[index]
    assert benzer[("q:2:7", "q:2:8")]["score"] == "0.571429"  # QurSim label'i puani degistirmez
    for cift, label in ((("q:2:1", "q:2:3"), 0), (("q:2:2", "q:2:9"), 1)):
        satir = benzer[cift]
        assert satir["score"] == satir["confidence"] == "0.500000"
        assert satir["evidence"]["label"] == label and satir["evidence"]["subtype"] == "alim"  # type: ignore[index]
        assert satir["evidence"]["source_id"] == QURSIM  # type: ignore[index]


def test_qursim_olmadan_yalniz_sozluksel_satir(tmp_path: Path) -> None:
    benzer = [s for s in uretim(tmp_path, qursim=False) if s["type"] == "benzer_ayet"]
    assert len(benzer) == 2
    assert all(s["evidence"]["subtype"] == "sozluksel" for s in benzer)  # type: ignore[index]


def test_simple_clean_besmele_onegi_yalniz_bellekte_kirpilir() -> None:
    db = db_girdisi()
    metinler = {ay.capa: simple_metni(ay) for ay in AYETLER}
    s = simple_kelimeleri(metinler, db.ayetler)
    assert s.besmele_kirpilan == 1 and s.besmele_bulunmayan == 0
    assert len(s.kelimeler[1]) == len(AYETLER[1].tokenler)  # q:2:1: besmele atildi
    assert len(s.kelimeler[0]) == 4  # q:1:1 besmelenin kendisidir: kirpilmaz
    # sure basi ayet besmeleyle baslamiyorsa kirpilmaz ve sayilir
    metinler["q:2:1"] = " ".join(sozcuk(t) for t in AYETLER[1].tokenler)
    assert simple_kelimeleri(metinler, db.ayetler).besmele_bulunmayan == 1
    with pytest.raises(Exception, match="ayet kumesi"):
        simple_kelimeleri({"q:1:1": "x"}, db.ayetler)


# --- kapilar ----------------------------------------------------------------------------------


def test_temiz_satirlar_uc_kapidan_gecer(tmp_path: Path) -> None:
    g = girdi_kur(uretim(tmp_path))
    for kapi in ("G-KAY", "G-BUT", "G-CAP"):
        assert bulgular(g, kapi) == (), kapi


def _degistir(
    satirlar: list[dict[str, object]], sira: int, yama: dict[str, object]
) -> list[dict[str, object]]:
    kopya = copy.deepcopy(satirlar)
    for anahtar, deger in yama.items():
        hedef: dict[str, object] = kopya[sira]
        *yol, son = anahtar.split(".")
        for p in yol:
            hedef = hedef[p]  # type: ignore[assignment]
        hedef[son] = deger
    return kopya


def test_g_kay_kayitsiz_ya_da_tura_uygun_olmayan_source_id(tmp_path: Path) -> None:
    satirlar = uretim(tmp_path)
    kok = next(i for i, s in enumerate(satirlar) if s["type"] == "kok")
    kayitsiz = girdi_kur(_degistir(satirlar, kok, {"evidence.source_id": "kaydi-yok"}))
    assert any("kayitsiz" in b for b in bulgular(kayitsiz, "G-KAY"))
    uygunsuz = girdi_kur(_degistir(satirlar, kok, {"evidence.source_id": "qursim"}))
    assert any("tura uygun degil" in b for b in bulgular(uygunsuz, "G-KAY"))
    bos_atif = girdi_kur(satirlar)
    bos_atif.kayitlar = {
        **bos_atif.kayitlar,
        "qursim": Kaynak(slug="qursim", tur=SourceKind.BAGLANTI_VERISI, baslik="x", atif_metni=" "),
    }
    assert any("atif_metni bos" in b for b in bulgular(bos_atif, "G-KAY"))
    eksik = girdi_kur(satirlar)
    eksik.kayitlar = {k: v for k, v in eksik.kayitlar.items() if k != "qursim"}
    assert any("qursim: kaynak kaydi yok" in b for b in bulgular(eksik, "G-KAY"))


def test_g_but_ihlalleri(tmp_path: Path) -> None:
    satirlar = uretim(tmp_path)
    kok = next(i for i, s in enumerate(satirlar) if s["type"] == "kok")
    sozluksel = next(
        i
        for i, s in enumerate(satirlar)
        if s["type"] == "benzer_ayet" and s["evidence"]["subtype"] == "sozluksel"  # type: ignore[index]
    )
    alim = next(
        i
        for i, s in enumerate(satirlar)
        if s["type"] == "benzer_ayet" and s["evidence"]["subtype"] == "alim"  # type: ignore[index]
    )
    senaryolar = {
        "skor_guven_ayni_degil": (kok, {"confidence": "0.100000"}),
        "idf_araligi": (
            kok,
            {
                "evidence.shared": [
                    {"root": 1, "idf": "0.100000", "src_word": "q:2:1:1", "dst_word": "q:2:2:1"}
                ]
            },
        ),
        "shared_bos": (kok, {"evidence.shared": []}),
        "skor_formulu": (sozluksel, {"score": "0.900000", "confidence": "0.900000"}),
        "qursim_skoru_sabit_degil": (alim, {"score": "0.800000", "confidence": "0.800000"}),
        "src_hash": (kok, {"evidence.src_hash": "xyz"}),
        "aralik_dolu": (kok, {"src_span": [1, 2]}),
        "tur": (kok, {"type": "anlamsal"}),
    }
    for beklenen, (sira, yama) in senaryolar.items():
        g = girdi_kur(_degistir(satirlar, sira, yama))
        hatalar = satir_hatalari(g.satirlar[sira])
        assert beklenen in hatalar, (beklenen, hatalar)
        assert bulgular(g, "G-BUT"), beklenen
    # Label'a bagli puan yok: label degisse de skor sabit kalir, farkli skor reddedilir
    g = girdi_kur(_degistir(satirlar, alim, {"evidence.label": 2}))
    assert satir_hatalari(g.satirlar[alim]) == []


def test_g_but_birim_basina_en_cok_bes_ve_manifest_tutarliligi(tmp_path: Path) -> None:
    satirlar = uretim(tmp_path)
    g = girdi_kur(satirlar, manifest_sayilari={"kok": 6, "lemma": 5, "benzer_ayet": 4})
    assert any("manifestle tutmuyor" in b for b in bulgular(g, "G-BUT"))
    kok = [s for s in satirlar if s["type"] == "kok"]
    fazla = [copy.deepcopy(kok[0]) for _ in range(6)]
    for i, s in enumerate(fazla):
        s["dst_anchor"] = f"q:2:{i + 2}"
    g2 = girdi_kur(fazla, turler=("kok",), manifest_sayilari={"kok": 6}, data_version=SURUMLER)
    assert any("en cok 5" in b for b in bulgular(g2, "G-BUT"))
    g3 = girdi_kur(satirlar, data_version={**SURUMLER, "kok": "baska"})
    assert any("data_version" in b for b in bulgular(g3, "G-BUT"))


def test_g_cap_ihlalleri(tmp_path: Path) -> None:
    satirlar = uretim(tmp_path)
    kok = next(i for i, s in enumerate(satirlar) if s["type"] == "kok")
    benzer = next(i for i, s in enumerate(satirlar) if s["type"] == "benzer_ayet")
    for yama, sira in (
        ({"src_anchor": "q:2:300"}, kok),  # 2. surede 300. ayet yok
        ({"dst_anchor": "q:2:1:3"}, kok),  # kelime capasi: ayet degil
        ({"dst_anchor": "q:2:1"}, kok),  # src == dst (ilk kok satiri q:2:1 -> q:2:2)
        ({"dst_anchor": "meal:elmalili:2:1"}, kok),
    ):
        g = girdi_kur(_degistir(satirlar, sira, yama))
        assert bulgular(g, "G-CAP"), yama
    # benzer_ayet yonu: src < dst olmali
    ters = _degistir(satirlar, benzer, {})
    ters[benzer]["src_anchor"], ters[benzer]["dst_anchor"] = (
        satirlar[benzer]["dst_anchor"],
        satirlar[benzer]["src_anchor"],
    )
    assert any("src_kucuk_degil" in b for b in bulgular(girdi_kur(ters), "G-CAP"))
    # paylasilan kelime capasi ilgili ayete ait olmali
    g = girdi_kur(
        _degistir(
            satirlar,
            kok,
            {
                "evidence.shared": [
                    {"root": 1, "idf": "0.500000", "src_word": "q:2:9:1", "dst_word": "q:2:2:1"}
                ]
            },
        )
    )
    assert any("kelime_capasi" in b for b in bulgular(g, "G-CAP"))
    # yinelenen dogal anahtar
    yinelenen = [*satirlar, copy.deepcopy(satirlar[kok])]
    assert any("yinelenen" in b for b in bulgular(girdi_kur(yinelenen), "G-CAP"))
