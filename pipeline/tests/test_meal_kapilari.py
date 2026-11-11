"""Meal QA kapilari islev duzeyinde (A16.3; SENTETIK veri): G-KAY, G-BUT, G-CAP, G-NOR, G-HIZ.

Sablon, `conftest.meal_sablon` (tam sentetik zincir) staged anchor satirlarindan kurulan
`MealGirdisi`dir; her test satirlari bir noktadan bozar ve ilgili kapinin kaldigini (ve yalniz
onun bulgu verdigini) sinar. Metin sentetiktir ("Deneme meal parcasi ...").
"""

import dataclasses
from collections.abc import Callable
from pathlib import Path

import pytest
from meal_yardimci import MealKoku

from mutalaa_pipeline import lineage, sources
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.export.ortak import depo_koku
from mutalaa_pipeline.ingest import meal_kaynaklari as mk
from mutalaa_pipeline.ingest import meal_kilit
from mutalaa_pipeline.ingest.meal_kilit import kilit_ozeti
from mutalaa_pipeline.qa.checks import meal as kapilar
from mutalaa_pipeline.qa.checks.meal import MealGirdisi, yasak_karakter
from mutalaa_pipeline.qa.checks.tanzil import Onceki
from mutalaa_pipeline.staged import Satir, satirlari_oku

ORIJINAL = "elmalili-meal"
SADE = "elmalili-sade-meal"


def _anchor_satirlari(kok: MealKoku, slug: str) -> list[Satir]:
    calismalar = [
        c for c in lineage.calismalar(kok.veri / "staged" / slug) if c[2].get("adim") == "anchor"
    ]
    return satirlari_oku((calismalar[-1][1] / "units.jsonl").read_bytes(), "anchor units.jsonl")


def _ham(kok: MealKoku, slug: str) -> dict[str, bytes]:
    klasor = kok.veri / "raw" / slug / "2026-11-11"
    return {p.name: p.read_bytes() for p in klasor.iterdir() if p.name != "fetch.json"}


@pytest.fixture
def girdi(meal_sablon: MealKoku, monkeypatch: pytest.MonkeyPatch) -> Callable[[str], MealGirdisi]:
    monkeypatch.setattr(meal_kilit, "KILIT_YOLU", meal_sablon.kilit_yolu)

    def kur(slug: str) -> MealGirdisi:
        kayit = {s.kaynak.slug: s.kaynak for s in sources.yukle(depo_koku()) if s.kaynak}[slug]
        kilit = meal_kilit.kilit_yukle()
        bolum = mk.kaynak(slug).kilit_bolumu
        modul = mk.bagdastirici_modulu(slug)
        return MealGirdisi(
            slug=slug,
            kayit=kayit,
            anchor_satirlari=_anchor_satirlari(meal_sablon, slug),
            yeniden=modul.yeniden_uret(_ham(meal_sablon, slug)),  # type: ignore[attr-defined]
            kilit_ozeti=kilit_ozeti(kilit.bolum_sozlugu(bolum)),
            kilit_guncel=kilit_ozeti(kilit.bolum_sozlugu(bolum)),
            depo_kok=depo_koku(),
        )

    return kur


def degistir(g: MealGirdisi, capa: str, **alanlar: object) -> MealGirdisi:
    yeni: list[Satir] = []
    for s in g.anchor_satirlari:
        if s.veri["anchor"] == capa:
            s = Satir(s.etiket, s.no, {**s.veri, **alanlar})
        yeni.append(s)
    return dataclasses.replace(g, anchor_satirlari=yeni)


def sil(g: MealGirdisi, capa: str) -> MealGirdisi:
    return dataclasses.replace(
        g, anchor_satirlari=[s for s in g.anchor_satirlari if s.veri["anchor"] != capa]
    )


def kalan(sonuc: object) -> list[str]:
    return list(sonuc.bulgular)  # type: ignore[attr-defined]


def tum_kapilar(g: MealGirdisi) -> dict[str, bool]:
    return {k: f(g).gecti for k, f in kapilar.KAPI_ISLEVLERI.items()}


# --- temel: sentetik zincir bes kapida da gecer -----------------------------------------------


@pytest.mark.parametrize("slug", [ORIJINAL, SADE])
def test_sentetik_zincir_bes_kapiyi_gecer(girdi: Callable[[str], MealGirdisi], slug: str) -> None:
    sonuclar = {k: f(girdi(slug)) for k, f in kapilar.KAPI_ISLEVLERI.items()}
    assert list(sonuclar) == ["G-KAY", "G-BUT", "G-CAP", "G-NOR", "G-HIZ"]
    for kapi, s in sonuclar.items():
        assert s.gecti, (kapi, s.bulgular)
    assert sonuclar["G-HIZ"].sayilar["eksik"] == 0
    assert sonuclar["G-BUT"].sayilar["birim"] == 6236


# --- G-HIZ (sert kapi) -----------------------------------------------------------------------


def test_g_hiz_eksik_ayet_kalir(girdi: Callable[[str], MealGirdisi]) -> None:
    g = sil(girdi(SADE), "meal:elmalili-sade:2:255")
    sonuc = kapilar.g_hiz(g)
    assert not sonuc.gecti
    assert sonuc.sayilar["eksik"] == 1
    assert "q:2:255" in sonuc.bulgular[0]


def test_g_hiz_fazla_ve_baska_eser_capasi_kalir(girdi: Callable[[str], MealGirdisi]) -> None:
    g = degistir(girdi(SADE), "meal:elmalili-sade:2:255", anchor="meal:elmalili:2:255")
    sonuc = kapilar.g_hiz(g)
    assert not sonuc.gecti
    assert any("fazla birim" in b for b in sonuc.bulgular)


def test_g_hiz_yinelenen_capa_kalir(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(SADE)
    kopya = Satir("x", 99999, dict(g.anchor_satirlari[0].veri))
    g = dataclasses.replace(g, anchor_satirlari=[*g.anchor_satirlari, kopya])
    assert not kapilar.g_hiz(g).gecti


def test_g_hiz_birlesik_izleyen_baglantisi_denetlenir(
    girdi: Callable[[str], MealGirdisi],
) -> None:
    g = girdi(ORIJINAL)
    izleyen = "meal:elmalili:3:11"
    # baglanti baska ayete
    yanlis = degistir(g, izleyen, attrs={"birlesik_ile": "meal:elmalili:3:9"})
    assert any("birlesik_ile" in b for b in kapilar.g_hiz(yanlis).bulgular)
    # baglanti baska sureye
    yanlis = degistir(g, izleyen, attrs={"birlesik_ile": "meal:elmalili:4:10"})
    assert not kapilar.g_hiz(yanlis).gecti
    # bas birimde kapsam var ama izleyende baglanti yok
    baglantisiz = degistir(g, izleyen, attrs={})
    assert any("birlesik izleyen" in b for b in kapilar.g_hiz(baglantisiz).bulgular)
    # bas birimin kapsami gecersiz
    bozuk = degistir(g, "meal:elmalili:3:10", attrs={"kapsam": "q:3:10-999"})
    assert any("birlesik kapsam" in b for b in kapilar.g_hiz(bozuk).bulgular)
    # kapsam tasiyan bas birimin metni bos
    bos = degistir(g, "meal:elmalili:3:10", text="")
    assert any("bas birim" in b for b in kapilar.g_hiz(bos).bulgular)


# --- G-BUT -----------------------------------------------------------------------------------


def test_g_but_birlesik_ile_degismezi_iki_yonludur(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(ORIJINAL)
    # birlesik_ile var ama metin dolu
    a = kapilar.g_but(degistir(g, "meal:elmalili:3:11", text="Deneme dolu"))
    assert any("birlesik_ile degismezi" in b for b in a.bulgular)
    # metin bos ama birlesik_ile yok (bos birim)
    b = kapilar.g_but(degistir(g, "meal:elmalili:2:5", text=""))
    assert any("bos birim" in x for x in b.bulgular)
    assert any("birlesik_ile degismezi" in x for x in b.bulgular)
    # dogru izleyen (bos metin + birlesik_ile) kabul
    assert kapilar.g_but(g).gecti


def test_g_but_birim_sayisi_ve_sure_basina_sayi(girdi: Callable[[str], MealGirdisi]) -> None:
    s = kapilar.g_but(sil(girdi(SADE), "meal:elmalili-sade:1:1"))
    assert not s.gecti
    assert any("birim sayisi" in b for b in s.bulgular)
    assert any("sure basina" in b for b in s.bulgular)


@pytest.mark.parametrize(
    ("karakter", "serbest"),
    [
        ("‌", True),  # U+200C serbest
        ("‍", True),  # U+200D serbest
        ("\n", True),  # paragraf ici satir sonu
        ("​", False),  # sifir genislik bosluk (Cf)
        ("‮", False),  # yon kontrolu (Cf)
        ("﻿", False),  # BOM (Cf)
        ("\u0007", False),  # Cc
        ("\u0085", False),  # Cc
        ("", False),  # Co
        ("͸", False),  # Cn
    ],
)
def test_g_but_yasak_karakter_kurali(
    girdi: Callable[[str], MealGirdisi], karakter: str, serbest: bool
) -> None:
    assert yasak_karakter("Deneme " + karakter + " parca") is (not serbest)
    metin = f"Deneme{karakter}parça"
    g = degistir(
        girdi(SADE), "meal:elmalili-sade:2:2", text=metin, content_hash=content_hash(metin)
    )
    sonuc = kapilar.g_but(g)
    kontrol = [b for b in sonuc.bulgular if "kontrol karakteri" in b]
    assert (not kontrol) is serbest


def test_u200c_ingest_ve_kapida_korunur() -> None:
    from mutalaa_pipeline.anchor import kanonik_metin

    assert "‌" in kanonik_metin("Deneme‌metin")  # ilk kayit U+200C'yi silmez
    assert "‍" in kanonik_metin("Deneme‍metin")
    assert "​" in kanonik_metin("Deneme​metin")  # U+200B de silinmez; G-BUT reddeder


def test_g_but_kanonik_olmayan_metin_ve_besmele_ozeti(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(SADE)
    nfc_degil = "Deneâme"
    s = kapilar.g_but(
        degistir(g, "meal:elmalili-sade:2:2", text=nfc_degil, content_hash=content_hash(nfc_degil))
    )
    assert any("kanonik olmayan" in b for b in s.bulgular)
    s = kapilar.g_but(
        degistir(
            g,
            "meal:elmalili-sade:2:2",
            attrs={"besmele_meali": {"metin": "Deneme", "content_hash": "0" * 64}},
        )
    )
    assert any("besmele_meali" in b for b in s.bulgular)


def test_g_but_yeniden_uretilebilirlik_ham_dosyadan(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(SADE)
    s = kapilar.g_but(degistir(g, "meal:elmalili-sade:2:2", text="Deneme baska"))
    assert any("yeniden uretilebilirlik" in b for b in s.bulgular)


# --- G-CAP -----------------------------------------------------------------------------------


def test_g_cap_alan_ord_aralik_ve_ozet_bozuklugu(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(ORIJINAL)
    capa = "meal:elmalili:3:10"
    assert any("ord" in b for b in kapilar.g_cap(degistir(g, capa, ord=5)).bulgular)
    assert any("ayah" in b for b in kapilar.g_cap(degistir(g, capa, ayah_hi=0)).bulgular)
    assert any(
        "content_hash" in b
        for b in kapilar.g_cap(degistir(g, capa, content_hash="0" * 64)).bulgular
    )
    assert any("sabit alan" in b for b in kapilar.g_cap(degistir(g, capa, kind="ayet")).bulgular)
    assert any("alan kumesi" in b for b in kapilar.g_cap(degistir(g, capa, fazla=1)).bulgular)


def test_g_cap_kapsam_ayah_range_orter(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(ORIJINAL)
    bas = next(s for s in g.anchor_satirlari if s.veri["anchor"] == "meal:elmalili:3:10")
    assert bas.veri["ayah_hi"] == int(str(bas.veri["ayah_lo"])) + 2  # q:3:10-11 -> iki ayet
    # kapsam tek ayet araligina cevrilirse aralik tutmaz
    yanlis = degistir(g, "meal:elmalili:3:10", ayah_hi=int(str(bas.veri["ayah_lo"])) + 1)
    assert not kapilar.g_cap(yanlis).gecti


def test_g_cap_onceki_kayip_capa_ve_hash_degisimi(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(SADE)
    simdiki = {s.metin("anchor"): s.metin("content_hash") for s in g.anchor_satirlari}
    # onceki: ayni ozetler -> gecer
    ayni = dataclasses.replace(
        g, onceki=Onceki("r0", dict(simdiki)), onceki_kilit_ozeti=g.kilit_ozeti
    )
    assert kapilar.g_cap(ayni).gecti
    # onceki'nde olup simdi olmayan capa: kilit degisse de kalir
    kayip = dict(simdiki, **{"meal:elmalili-sade:1:99": "0" * 64})
    s = kapilar.g_cap(
        dataclasses.replace(g, onceki=Onceki("r0", kayip), onceki_kilit_ozeti="b" * 64)
    )
    assert any("kaybolan" in b for b in s.bulgular)
    # content_hash degisti, kilit AYNI -> kalir
    farkli = dict(simdiki, **{"meal:elmalili-sade:1:1": "0" * 64})
    ayni_kilit = dataclasses.replace(
        g, onceki=Onceki("r0", farkli), onceki_kilit_ozeti=g.kilit_ozeti
    )
    s = kapilar.g_cap(ayni_kilit)
    assert any("content_hash farkli" in b for b in s.bulgular)
    assert s.sayilar["hash_degisen"] == 1 and s.sayilar["kilit_degisti"] == 0
    # content_hash degisti, kilit DEGISTI -> gecer ve rapora yazilir
    kilit_degisti = dataclasses.replace(g, onceki=Onceki("r0", farkli), onceki_kilit_ozeti="b" * 64)
    s = kapilar.g_cap(kilit_degisti)
    assert s.gecti
    assert s.sayilar["hash_degisen"] == 1 and s.sayilar["kilit_degisti"] == 1


# --- G-KAY -----------------------------------------------------------------------------------


def test_g_kay_atif_yer_tutucu_tur_ve_kilit(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(ORIJINAL)
    assert kapilar.g_kay(g).gecti
    ek = dataclasses.replace(g.kayit, atif_metni=g.kayit.atif_metni + mk.DENETLENDI_EKI)
    assert kapilar.g_kay(dataclasses.replace(g, kayit=ek)).gecti  # G-INC sonrasi ek kabul
    yer = dataclasses.replace(g.kayit, atif_metni="Meal: {sürüm}")
    assert not kapilar.g_kay(dataclasses.replace(g, kayit=yer)).gecti
    baska = dataclasses.replace(g.kayit, atif_metni="Baska bir atif.")
    assert any(
        "atif_metni" in b for b in kapilar.g_kay(dataclasses.replace(g, kayit=baska)).bulgular
    )
    surumsuz = dataclasses.replace(g.kayit, surum=None)
    assert not kapilar.g_kay(dataclasses.replace(g, kayit=surumsuz)).gecti
    assert not kapilar.g_kay(dataclasses.replace(g, kilit_ozeti="c" * 64)).gecti  # eski kilit
    assert not kapilar.g_kay(dataclasses.replace(g, kilit_ozeti=None)).gecti


# --- G-NOR -----------------------------------------------------------------------------------


def test_g_nor_anahtar_ar_norm_ve_surum(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(SADE)
    capa = "meal:elmalili-sade:2:2"
    assert kapilar.g_nor(g).gecti
    assert not kapilar.g_nor(degistir(g, capa, tr_narrow="baska")).gecti
    assert not kapilar.g_nor(degistir(g, capa, ar_norm="x")).gecti
    assert not kapilar.g_nor(degistir(g, capa, provenance={})).gecti


def test_hicbir_bulgu_metin_icermez(girdi: Callable[[str], MealGirdisi]) -> None:
    g = degistir(girdi(SADE), "meal:elmalili-sade:2:2", text="Deneme gizli metin", tr_narrow="x")
    for f in kapilar.KAPI_ISLEVLERI.values():
        for bulgu in f(g).bulgular:
            assert "gizli" not in bulgu
            assert "Deneme" not in bulgu


def test_rapor_dizin_testi_dosyalari_var(meal_sablon: MealKoku) -> None:
    assert isinstance(meal_sablon.veri, Path)
    assert (meal_sablon.veri / "reports").is_dir()


# --- sayfa basi/sonu bolgesi esigi ------------------------------------------------------------


def _bolge(sure: int, taraf: str, uzunluk: int) -> dict[str, object]:
    ozet = {"uzunluk": uzunluk, "sha256": "0" * 64}
    return {
        "sure": sure,
        "on": ozet if taraf == "on" else None,
        "son": ozet if taraf == "son" else None,
    }


def test_g_but_uzun_sayfa_bolgesi_kalir(girdi: Callable[[str], MealGirdisi]) -> None:
    g = girdi(ORIJINAL)
    kisa = dataclasses.replace(g, bolgeler=[_bolge(6, "son", 6)])
    assert kapilar.g_but(kisa).gecti
    assert kapilar.g_but(dataclasses.replace(g, bolgeler=[_bolge(6, "son", 100)])).gecti
    uzun = kapilar.g_but(dataclasses.replace(g, bolgeler=[_bolge(6, "son", 101)]))
    assert any("bolgesi 100" in b and "sure 6 son" in b for b in uzun.bulgular)
    uzun_on = kapilar.g_but(dataclasses.replace(g, bolgeler=[_bolge(7, "on", 500)]))
    assert any("sure 7 on" in b for b in uzun_on.bulgular)
    assert kapilar.g_but(kisa).sayilar["en_uzun_bolge"] == 6
