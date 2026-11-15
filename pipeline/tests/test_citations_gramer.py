"""Acik atif grameri (A18.4; Iktibas tespiti §2, K-51 madde 4): SENTETIK adlar ve metinler.

Sure adlari `Alfa`, `Beta` gibi uydurmadir; hicbir Kur'an ya da meal metni yoktur. Onayli alias
tablosu testte kurulur (gercekte `status = 'onayli'` satirlari; bugun yok: İ-23).
"""

from pathlib import Path

import pytest

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.enrich.citations import gramer
from mutalaa_pipeline.enrich.citations.gramer import (
    AdlandirilmisAyet,
    AdSozlugu,
    Alias,
    Sonuc,
    atiflari_bul,
)
from mutalaa_pipeline.normalize import normalize_ar, normalize_tr


def alias(no: int, ad: str, tur: str = "kanonik", *, riskli: bool = False) -> Alias:
    arapca = any("؀" <= h <= "ۿ" for h in ad)
    anahtar = normalize_ar(ad) if arapca else normalize_tr(ad, "genis")
    return Alias(no, ad, anahtar, tur, riskli)


ARAPCA_AD = "ببججد"  # anlamsiz harf dizisi
SOZLUK = AdSozlugu(
    [
        alias(2, "Alfa"),
        alias(3, "Âl-i Beta"),
        alias(3, "Sûre-i Âl-i Beta", "yazim"),
        alias(24, "Gece", riskli=True),
        alias(11, "Hûd"),
        alias(71, "Hud"),
        alias(2, ARAPCA_AD, "arapca"),
        alias(9, "Delta"),
    ]
)


def bul(metin: str, sozluk: AdSozlugu | None = SOZLUK) -> Sonuc:
    return atiflari_bul(metin, sozluk=sozluk)


def ozet(metin: str, sozluk: AdSozlugu | None = SOZLUK) -> list[tuple[str, float, str]]:
    return [(a.capa, a.guven, a.bicim) for a in bul(metin, sozluk).atiflar]


# --- sayisal bicimler: her zaman etkin -------------------------------------------------------


def test_sayisal_parantez_ad_olmadan_etkin() -> None:
    for metin in ("Deneme (2:255) bitti", "Deneme [2/255] bitti"):
        s = atiflari_bul(metin)
        assert [(a.capa, a.guven, a.bicim) for a in s.atiflar] == [("q:2:255", 0.90, "sayisal")]
        assert s.sayac["ad_tabanli_kapali"] == 1
        a = s.atiflar[0]
        assert metin[a.bas : a.son] in ("(2:255)", "[2/255]")  # parantezler dahil, yari acik


def test_sayisal_arapca_hint_rakam() -> None:
    s = atiflari_bul("Deneme (٢:٢٥٥) bitti")
    assert [a.capa for a in s.atiflar] == ["q:2:255"]


def test_sayisal_yalniz_parantez_icinde() -> None:
    assert atiflari_bul("Deneme 2:255 bitti").atiflar == []
    assert atiflari_bul("Deneme (2:255] bitti").atiflar == []  # eslesmeyen parantez


def test_aralik_ve_liste_ayet_basina_satir_ve_grup() -> None:
    s = atiflari_bul("Deneme (2:255-257) ve (2:255, 257)")
    aralik = s.atiflar[:3]
    assert [a.capa for a in aralik] == ["q:2:255", "q:2:256", "q:2:257"]
    assert aralik[0].grup is not None and len({a.grup for a in aralik}) == 1
    liste = s.atiflar[3:]
    assert [a.capa for a in liste] == ["q:2:255", "q:2:257"]
    assert liste[0].grup == liste[1].grup is not None and liste[0].grup != aralik[0].grup


def test_tek_ayette_grup_yok() -> None:
    assert atiflari_bul("(2:255)").atiflar[0].grup is None


def test_sinir_disi_atilir_ve_sayilir() -> None:
    s = atiflari_bul("a (2:999) b (115:1) c (2:200-300) d (2:286) e (0:1)")
    assert [a.capa for a in s.atiflar] == ["q:2:286"]
    assert s.sayac["ayet_disi"] == 1  # 2:999
    assert s.sayac["sure_disi"] == 2  # 115, 0
    assert s.sayac["aralik_disi"] == 1  # 200-300 (286'yi asiyor)
    assert all(isinstance(k, str) and " " not in k for k in s.sayac)  # sayac adlari, metin yok


def test_dort_haneli_sayi_kismen_okunmaz() -> None:
    assert atiflari_bul("(2:2555)").atiflar == []
    assert atiflari_bul("(12345:1)").atiflar == []
    assert bul("Alfa 12345").atiflar == []


def test_cok_uzun_aralik_atilir() -> None:
    s = atiflari_bul("(2:1-100)")
    assert s.atiflar == [] and s.sayac["aralik_cok_uzun"] == 1


def test_ayet_sayisi_dizisi_sinir() -> None:
    assert AYET_SAYILARI[1] == 286
    assert [a.capa for a in atiflari_bul("(2:286)").atiflar] == ["q:2:286"]
    assert atiflari_bul("(2:287)").atiflar == []


# --- ad tabanli bicimler -------------------------------------------------------------------------


def test_ad_tabanli_onayli_alias_yokken_kapali() -> None:
    for sozluk in (None, AdSozlugu([])):
        s = atiflari_bul("Deneme (Alfa Sûresi, 255) ve Alfa: 255", sozluk=sozluk)
        assert s.atiflar == []
        assert s.sayac["ad_tabanli_kapali"] == 1


def test_parantezli_ad_virgul_numara() -> None:
    assert ozet("Deneme (Alfa Sûresi, 255) bitti") == [("q:2:255", 0.95, "ad")]


def test_ad_iki_nokta_numara_ciplak() -> None:
    assert ozet("Deneme Âl-i Beta: 7 bitti") == [("q:3:7", 0.85, "ad")]


def test_sure_i_oneki_ve_alias_yazimi() -> None:
    assert ozet("Sûre-i Alfa, 255") == [("q:2:255", 0.95, "ad")]
    assert ozet("Sûre-i Âl-i Beta, 7") == [("q:3:7", 0.95, "ad")]


def test_ad_sure_numara_slash() -> None:
    assert ozet("Deneme Alfa 2/255 bitti") == [("q:2:255", 0.85, "ad")]
    s = bul("Deneme Alfa 3/255 bitti")  # numara adla uyusmuyor
    assert s.atiflar == [] and s.sayac["ad_no_uyumsuz"] == 1


def test_sira_sayisiyla() -> None:
    assert ozet("Alfa Sûresinin 255. âyeti") == [("q:2:255", 0.95, "ad_sira")]
    assert ozet("Alfa Sûresi'nin 255. âyet-i kerîmesi") == [("q:2:255", 0.95, "ad_sira")]


def test_ad_aralik_ve_liste() -> None:
    s = bul("Alfa, 255-257 ve Alfa, 255, 257.")
    assert [a.capa for a in s.atiflar] == ["q:2:255", "q:2:256", "q:2:257", "q:2:255", "q:2:257"]
    assert s.atiflar[0].grup == s.atiflar[1].grup != s.atiflar[3].grup


def test_arapca_ad_ve_arapca_rakam() -> None:
    s = bul(f"Deneme {ARAPCA_AD}: ٢٥٥ bitti")
    assert [(a.capa, a.guven) for a in s.atiflar] == [("q:2:255", 0.85)]


def test_riskli_ad_ipucsuz_atilir_ipucuyla_kabul() -> None:
    s = bul("Risale-i Gece, 5 kisi")
    assert s.atiflar == [] and s.sayac["riskli_ipucsuz"] == 1
    assert ozet("Deneme (Gece, 5) bitti") == [("q:24:5", 0.85, "ad")]  # parantez
    assert ozet("Deneme Gece Sûresi 5") == [("q:24:5", 0.85, "ad")]  # sure kelimesi
    assert ozet("Deneme Gece 5. âyeti") == [("q:24:5", 0.85, "ad_sira")]  # ayet kelimesi


def test_riskli_adlar_dosyasindan_da_riskli_olur() -> None:
    riskli = gramer.riskli_anahtarlar()
    assert riskli  # riskli_adlar.txt dolu
    ad = sorted(riskli)[0]
    s = AdSozlugu([alias(5, ad)], riskli)  # alias.risky false; dosya riskli sayar
    assert atiflari_bul(f"x {ad}, 3 y", sozluk=s).atiflar == []


def test_cakisan_alias_iki_surede_satir_yok() -> None:
    # genis anahtar ayni ('hud'): Hûd (11) ve Hud (71); yuzey bicim Hüd her ikisine de uymuyor
    s = bul("Deneme Hüd: 3 bitti")
    assert s.atiflar == [] and s.sayac["ad_cakisan_birden_cok_sure"] == 1


def test_dar_anahtar_genis_anahtardan_once() -> None:
    assert ozet("Hûd: 3") == [("q:11:3", 0.85, "ad")]  # dar tek surede (11)
    assert ozet("Hud: 3") == [("q:71:3", 0.85, "ad")]  # dar tek surede (71)


def test_genis_anahtar_tek_sureye_cikiyorsa_kullanilir() -> None:
    s = bul("Deneme Âlfa, 5 bitti")  # sapka farki: dar yok, genis 'alfa' tek sure
    assert [(a.capa, a.guven) for a in s.atiflar] == [("q:2:5", 0.85)]
    assert s.sayac["ad_genis_anahtarla"] == 1


def test_ad_aralik_sinir_disi() -> None:
    s = bul("Alfa, 255-999")
    assert s.atiflar == [] and s.sayac["aralik_disi"] == 1


def test_atif_ofsetleri_kod_noktasi_ve_yari_acik() -> None:
    metin = "\U0001d400 (Alfa Sûresi, 255) bitti"  # BMP disi karakter: 1 kod noktasi
    a = bul(metin).atiflar[0]
    assert metin[a.bas : a.son] == "(Alfa Sûresi, 255)"
    assert a.bas == 2


def test_ayni_bolgede_tek_satir() -> None:
    assert len(bul("(Alfa, 255)").atiflar) == 1


# --- adlandirilmis ayet ---------------------------------------------------------------------------


def test_adlandirilmis_ayet_listesi_ve_guven(tmp_path: Path) -> None:
    yol = tmp_path / "liste.toml"
    yol.write_text(
        '[[ayet]]\nad = "Deneme Ayeti"\nhedefler = ["q:2:255"]\n'
        '[[ayet]]\nad = "Cift Ayet"\nhedefler = ["q:2:1", "q:2:2"]\n',
        encoding="utf-8",
    )
    liste = gramer.adlandirilmis_oku(yol)
    assert liste == [
        AdlandirilmisAyet("Deneme Ayeti", ((2, 255),)),
        AdlandirilmisAyet("Cift Ayet", ((2, 1), (2, 2))),
    ]
    s = atiflari_bul("x deneme ayeti y ve Çift Âyet z", adlandirilmis=liste)
    assert [(a.capa, a.guven, a.bicim) for a in s.atiflar] == [
        ("q:2:255", 0.90, "adlandirilmis"),
        ("q:2:1", 0.90, "adlandirilmis"),
        ("q:2:2", 0.90, "adlandirilmis"),
    ]
    assert s.atiflar[1].grup == s.atiflar[2].grup is not None


def test_depodaki_adlandirilmis_liste_bos_iskelet() -> None:
    assert gramer.adlandirilmis_oku() == []


@pytest.mark.parametrize(
    "icerik",
    [
        '[[ayet]]\nad = "X"\nhedefler = ["q:2:255:3"]\n',  # kelime capasi
        '[[ayet]]\nad = "X"\nhedefler = ["q:999:1"]\n',  # gecersiz
        '[[ayet]]\nhedefler = ["q:2:1"]\n',  # ad yok
    ],
)
def test_adlandirilmis_liste_gecersiz_girdi_reddedilir(tmp_path: Path, icerik: str) -> None:
    yol = tmp_path / "l.toml"
    yol.write_text(icerik, encoding="utf-8")
    with pytest.raises(ValueError):
        gramer.adlandirilmis_oku(yol)
