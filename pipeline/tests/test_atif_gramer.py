"""Acik atif grameri (A20.7a): yalniz sentetik adlar ve metinler.

Sure adi tablosu SENTETIKTIR ("Deneme", "Ornek" ...): gercek sure adlari hafizadan yazilmaz.
Sure ve ayet numaralari serbesttir; gecerlilik `anchor.capa` ile denetlenir (sure 2: 286 ayet,
sure 3: 200 ayet, sure 24: 64 ayet).
"""

from itertools import pairwise

import pytest

from mutalaa_pipeline.enrich import atif_gramer
from mutalaa_pipeline.enrich.atif_gramer import SureAdTablosu


@pytest.fixture(scope="module")
def tablo() -> SureAdTablosu:
    return SureAdTablosu.kur(
        [(2, "Deneme"), (3, "Âl-i Örnek"), (24, "Parlak"), (24, "Parlak Deneme")],
        riskli_adlar=["Parlak"],
    )


def _tek(metin: str, tablo: SureAdTablosu | None) -> atif_gramer.Atif:
    sonuc = atif_gramer.ayristir(metin, tablo)
    assert len(sonuc.atiflar) == 1, sonuc
    return sonuc.atiflar[0]


def test_parantezli_ad_ve_sure_kelimesi(tablo: SureAdTablosu) -> None:
    metin = "Deneme paragrafi 1 (Deneme Sûresi, 255) devam."
    atif = _tek(metin, tablo)
    assert (atif.sure, atif.ayetler) == (2, (255,))
    assert atif.parantez
    assert atif.guven == atif_gramer.GUVEN_ANAHTAR_KELIMELI
    assert metin[atif.bas : atif.son] == "(Deneme Sûresi, 255)"
    assert atif.capalar() == ("q:2:255",)
    assert not atif.grup


def test_ciplak_ad_iki_nokta(tablo: SureAdTablosu) -> None:
    metin = "Deneme paragrafi 2: Deneme: 255 ve sonrasi."
    atif = _tek(metin, tablo)
    assert (atif.sure, atif.ayetler, atif.guven) == (2, (255,), atif_gramer.GUVEN_CIPLAK)
    assert metin[atif.bas : atif.son] == "Deneme: 255"
    assert atif.sinyal == "ad_ayrac_ayet"


def test_sapka_nokta_ve_buyuk_harf_farki_onemsiz(tablo: SureAdTablosu) -> None:
    for yazim in ("Âl-i Örnek: 7", "Al-i Ornek: 7", "ÂL-İ ÖRNEK: 7", "âl-i örnek, 7"):
        atif = _tek(f"Deneme paragrafi 3. {yazim}.", tablo)
        assert (atif.sure, atif.ayetler) == (3, (7,)), yazim


def test_sure_i_oneki_ve_aralik(tablo: SureAdTablosu) -> None:
    metin = "Deneme paragrafi 4. Sûre-i Deneme, 255-257 gibi."
    atif = _tek(metin, tablo)
    assert atif.ayetler == (255, 256, 257)
    assert atif.grup
    assert atif.guven == atif_gramer.GUVEN_ANAHTAR_KELIMELI
    assert metin[atif.bas : atif.son].startswith("Sûre-i Deneme")
    assert atif.capalar() == ("q:2:255", "q:2:256", "q:2:257")


def test_liste(tablo: SureAdTablosu) -> None:
    atif = _tek("Deneme paragrafi 5. Deneme, 255, 257-258.", tablo)
    assert atif.ayetler == (255, 257, 258)
    assert atif.grup


def test_sure_numarali_bicim_ve_tutarsizlik(tablo: SureAdTablosu) -> None:
    atif = _tek("Deneme paragrafi 6. Deneme 2/255.", tablo)
    assert (atif.sure, atif.ayetler, atif.sinyal) == (2, (255,), "ad_sure_ayet")
    sonuc = atif_gramer.ayristir("Deneme paragrafi 7. Deneme 3/255.", tablo)
    assert sonuc.atiflar == []
    assert sonuc.atilan == {"sure_no_tutarsiz": 1}


def test_sirali_bicim(tablo: SureAdTablosu) -> None:
    metin = "Deneme paragrafi 8. Deneme Sûresinin 255. âyeti şöyle."
    atif = _tek(metin, tablo)
    assert (atif.sure, atif.ayetler, atif.sinyal) == (2, (255,), "sirali")
    assert metin[atif.bas : atif.son] == "Deneme Sûresinin 255. âyeti"


def test_bosluk_ayracli_bicim_ipucu_ister(tablo: SureAdTablosu) -> None:
    sonuc = atif_gramer.ayristir("Deneme paragrafi 9. Deneme 255 yaziyor.", tablo)
    assert sonuc.atiflar == []
    assert sonuc.atilan == {"bosluk_ipucsuz": 1}
    assert _tek("Deneme paragrafi 9. (Deneme 255)", tablo).ayetler == (255,)
    assert _tek("Deneme paragrafi 9. Deneme Sûresi 255.", tablo).ayetler == (255,)


def test_riskli_ad_ipucsuz_atilir(tablo: SureAdTablosu) -> None:
    sonuc = atif_gramer.ayristir("Deneme paragrafi 10. Parlak: 35 yaziyor.", tablo)
    assert sonuc.atiflar == []
    assert sonuc.atilan == {"riskli_ipucsuz": 1}
    assert _tek("Deneme paragrafi 10. (Parlak, 35)", tablo).sure == 24
    assert _tek("Deneme paragrafi 10. Parlak Sûresi, 35.", tablo).guven == 0.95
    # Uzun yazim (riskli olmayan) tercih edilir.
    uzun = _tek("Deneme paragrafi 10. Parlak Deneme: 35.", tablo)
    assert (uzun.sure, uzun.ayetler, uzun.guven) == (24, (35,), atif_gramer.GUVEN_CIPLAK)


def test_adsiz_parantezli_sayisal_bicim_tablosuz_calisir() -> None:
    metin = "Deneme paragrafi 11 (2:255) ve [3/7]."
    atiflar = atif_gramer.ayristir(metin, None).atiflar
    assert [(a.sure, a.ayetler) for a in atiflar] == [(2, (255,)), (3, (7,))]
    assert all(a.sinyal == "adsiz_parantez" and a.parantez for a in atiflar)
    assert [metin[a.bas : a.son] for a in atiflar] == ["(2:255)", "[3/7]"]


def test_arapca_hint_rakamlar() -> None:
    atif = _tek("Deneme paragrafi 12 (٢:٢٥٥)", None)
    assert (atif.sure, atif.ayetler) == (2, (255,))


def test_aralik_disi_ve_ters_aralik_atilir(tablo: SureAdTablosu) -> None:
    for metin in ("(2:300)", "(115:1)", "(2:0)", "(2:257-255)"):
        sonuc = atif_gramer.ayristir(f"Deneme paragrafi 13 {metin}", tablo)
        assert sonuc.atiflar == [], metin
        assert sonuc.atilan == {"aralik_disi": 1}, metin
    ters = atif_gramer.ayristir("Deneme paragrafi 13. Deneme, 257-255.", tablo)
    assert ters.atiflar == []


def test_atif_olmayan_metin(tablo: SureAdTablosu) -> None:
    sonuc = atif_gramer.ayristir("Deneme paragrafi 14 ve 15; oran 3:1 yaziyor, (a) maddesi.", tablo)
    assert sonuc.atiflar == []
    assert sonuc.atilan == {}


def test_tablo_yoksa_adli_atif_yok() -> None:
    assert atif_gramer.ayristir("Deneme: 255", None).atiflar == []
    assert atif_gramer.ayristir("Deneme: 255", SureAdTablosu([])).atiflar == []


def test_birden_cok_atif_sirali_ve_cakismasiz(tablo: SureAdTablosu) -> None:
    metin = "Deneme paragrafi 16. (Deneme, 255) sonra (Âl-i Örnek: 7) sonra (2:1)."
    atiflar = atif_gramer.ayristir(metin, tablo).atiflar
    assert [(a.sure, a.ayetler) for a in atiflar] == [(2, (255,)), (3, (7,)), (2, (1,))]
    assert all(a.son <= b.bas for a, b in pairwise(atiflar))


def test_evidence_sinyalleri_metin_tasimaz(tablo: SureAdTablosu) -> None:
    atif = _tek("Deneme paragrafi 17 (Deneme, 255)", tablo)
    ev = atif_gramer.evidence_sinyalleri(atif)
    assert ev == {"sinyal": "ad_ayrac_ayet", "parantez": True}


def test_arapca_sentetik_ad_ve_arapca_hint_rakam() -> None:
    arapca = SureAdTablosu.kur([(3, "ابتث")])  # sentetik harf dizisi
    atif = _tek("Deneme paragrafi 18 ابتث: ٢٣", arapca)
    assert (atif.sure, atif.ayetler) == (3, (23,))
    assert atif.guven == atif_gramer.GUVEN_CIPLAK
