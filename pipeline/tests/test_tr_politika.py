"""Otomatik onay politikasi (A18.2, K-51 madde 9 (a)-(e)): her kosul ayri sinanir.

Butun veri SENTETIKTIR (uydurma Turkce sozcukler ve anlamsiz Arapca harf dizileri;
`tr_yardimci.py`). Lemmatizer sahtedir; zeyrek gerekmez.
"""

import pytest
from tr_yardimci import (
    ETIMON_BNR,
    ETIMON_MRT,
    ETIMON_SML,
    KOK_AMN_ELIFLI,
    KOK_BNR,
    KOK_SML,
    analiz,
    env_kur,
    etimon_kanit,
    indeks_kur,
    kok_kanit,
    ota_madde,
    tr_madde,
)

from mutalaa_pipeline.enrich.tr_roots.eslesme import QacEnvanteri
from mutalaa_pipeline.enrich.tr_roots.etimoloji import KaikkiIndeksi
from mutalaa_pipeline.enrich.tr_roots.politika import (
    ADAY,
    BELIRSIZ_LEMMA,
    BILINMEYEN_SOZCUK,
    COK_ADAYLI_QAC,
    HOMOGRAF_CELISKISI,
    KANIT_YOK,
    KAPALI_SINIF,
    KOK_CAKISMASI,
    KOK_YOK,
    MADDE_YOK,
    ONAYLI,
    POLITIKA_SURUMU,
    POS_UYUSMAZLIGI,
    QAC_ESLESMEDI,
    TR_OTA_KOK_CAKISMASI,
    YALNIZ_SERBEST_METIN,
    Karar,
    lemma_karari,
    yuzey_karari,
)
from mutalaa_pipeline.qa.checks.tr_roots import kanit_hatalari

ENV: QacEnvanteri = env_kur()


def karar(indeks: KaikkiIndeksi, lemma: str, *poslar: str) -> Karar:
    return lemma_karari(lemma, frozenset(poslar or ("Noun",)), indeks, ENV)


# --- onay: yapisal kanit + kesin ve tek QAC eslesmesi ----------------------------------------


def test_root_sablonu_ve_kesin_eslesme_onaylanir() -> None:
    k = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR))), "tavan")
    assert (k.karar, k.neden) == (ONAYLI, "kosullar_saglandi")
    assert k.kok is not None and k.kok.letters_bw == "bnr"
    assert k.yontem == "kok_harfleri"
    assert k.ar_lemma is None  # etimon yok: Arapca lemma eslesmesi yok


def test_etimon_lemma_eslesmesi_elif_katlamasiyla_onaylanir() -> None:
    """Etimon imlai elif yazar (`صَمَال`), QAC lemmasi elifsizdir (`صمل`)."""
    k = karar(indeks_kur(tr_madde("dolap", etimon_kanit(ETIMON_SML))), "dolap")
    assert (k.karar, k.yontem) == (ONAYLI, "etimon_lemma")
    assert k.kok is not None and k.kok.letters_bw == "Sml"
    assert k.ar_lemma is not None and k.ar_lemma.qac_ref == "samal"


def test_elifli_etimon_elifsiz_qac_lemmasiyla_tutar() -> None:
    k = karar(indeks_kur(tr_madde("tavan", etimon_kanit(ETIMON_BNR))), "tavan")
    assert k.karar == ONAYLI
    assert k.ar_lemma is not None and k.ar_lemma.qac_ref == "banar"


def test_iki_yol_ayni_koke_giderse_ikisi() -> None:
    k = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR), etimon_kanit(ETIMON_BNR))), "tavan")
    assert (k.karar, k.yontem) == (ONAYLI, "ikisi")


def test_hemze_katlamasi_kok_harfleriyle_tutar() -> None:
    """kaikki `أ م ن` (elif ustunde hemze), QAC `ء م ن`."""
    k = karar(indeks_kur(tr_madde("emin", kok_kanit(KOK_AMN_ELIFLI))), "emin")
    assert k.karar == ONAYLI and k.kok is not None and k.kok.letters_bw == "Amn"


def test_osmanlica_zinciri_yapisal_kanittir() -> None:
    indeks = indeks_kur(
        tr_madde("pelin", osmanlica=("ععع",)),
        ota_madde("ععع", kok_kanit(KOK_SML)),
    )
    k = karar(indeks, "pelin")
    assert (k.karar, k.yontem) == (ONAYLI, "kok_harfleri")
    assert {x["madde"] for x in k.kaynaklar} == {"ععع"}  # kanit Osmanlica maddeden gelir


def test_etymological_only_otomatik_eslemede_yok() -> None:
    """Karar nesnesi etymological_only tasimaz; yukleme her zaman false yazar (test_tr_roots_pg)."""
    k = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR))), "tavan")
    assert "etymological_only" not in k.kanit()
    assert not hasattr(k, "etymological_only")


# --- aday ------------------------------------------------------------------------------------


def test_iki_qac_adayi_aday_kalir() -> None:
    """Etimon anahtari `مرت` iki farkli kokten iki QAC lemmasina gider."""
    k = karar(indeks_kur(tr_madde("morta", etimon_kanit(ETIMON_MRT))), "morta")
    assert (k.karar, k.neden) == (ADAY, COK_ADAYLI_QAC)
    assert k.kok is None and {a.letters_bw for a in k.adaylar} == {"bnr", "Sml"}


def test_turkce_ve_osmanlica_farkli_kok_aday_kalir() -> None:
    indeks = indeks_kur(
        tr_madde("kelin", kok_kanit(KOK_BNR), osmanlica=("غغغ",)),
        ota_madde("غغغ", kok_kanit(KOK_SML)),
    )
    k = karar(indeks, "kelin")
    assert (k.karar, k.neden) == (ADAY, TR_OTA_KOK_CAKISMASI)
    assert len(k.adaylar) == 2


def test_yalniz_serbest_metin_arabic_aday_kalir_ve_kok_atanmaz() -> None:
    k = karar(indeks_kur(tr_madde("fisto", zayif=True)), "fisto")
    assert (k.karar, k.neden) == (ADAY, YALNIZ_SERBEST_METIN)
    assert k.kok is None and k.kaynaklar == ()


def test_serbest_metin_yapisal_kanitla_birlikte_kanit_sayilmaz() -> None:
    """Yapisal kanit varsa zayif bayrak karari degistirmez; yoksa yalniz aday yapar."""
    ikisi = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR), zayif=True)), "tavan")
    assert ikisi.karar == ONAYLI


def test_kanit_yok_kok_yok() -> None:
    assert karar(indeks_kur(tr_madde("yalin")), "yalin") == Karar(
        KOK_YOK, KANIT_YOK, kaikki_surum="2026-10-30"
    )
    k = karar(indeks_kur(), "yalin")
    assert (k.karar, k.neden) == (KOK_YOK, MADDE_YOK)


def test_kanit_var_ama_qac_koku_yok_kok_yok() -> None:
    k = karar(indeks_kur(tr_madde("yalin", kok_kanit("ز ز ز"))), "yalin")
    assert (k.karar, k.neden) == (KOK_YOK, QAC_ESLESMEDI)


def test_pos_uyusmazligi_aday_kalir_ve_oneri_tasir() -> None:
    k = karar(indeks_kur(tr_madde("kalem", kok_kanit(KOK_BNR))), "kalem", "Adj")
    assert (k.karar, k.neden) == (ADAY, POS_UYUSMAZLIGI)
    assert k.kok is not None and k.kok.letters_bw == "bnr"


def test_zeyrek_turu_kaikki_turuyle_eslesirse_onay() -> None:
    k = karar(indeks_kur(tr_madde("kalem", kok_kanit(KOK_BNR), pos="adj")), "kalem", "Adj")
    assert k.karar == ONAYLI


def test_ayni_lemma_ve_turde_madde_kanitsizsa_homograf_aday() -> None:
    k = karar(indeks_kur(tr_madde("bobin", kok_kanit(KOK_BNR)), tr_madde("bobin")), "bobin")
    assert (k.karar, k.neden) == (ADAY, HOMOGRAF_CELISKISI)
    assert k.kok is not None and k.kok.letters_bw == "bnr"  # oneri editore tasinir


def test_ayni_lemma_ve_turde_maddeler_farkli_kokse_aday() -> None:
    indeks = indeks_kur(
        tr_madde("zorba", kok_kanit(KOK_BNR)), tr_madde("zorba", kok_kanit(KOK_SML))
    )
    k = karar(indeks, "zorba")
    assert (k.karar, k.neden) == (ADAY, KOK_CAKISMASI)


def test_ayni_lemma_farkli_turdeki_madde_homograf_sayilmaz() -> None:
    indeks = indeks_kur(
        tr_madde("tavan", kok_kanit(KOK_BNR)),
        tr_madde("tavan", kok_kanit(KOK_SML), pos="verb"),
    )
    assert karar(indeks, "tavan", "Noun").karar == ONAYLI


def test_osmanlica_madde_tur_farkliysa_baglanti_sayilmaz() -> None:
    indeks = indeks_kur(
        tr_madde("pelin", osmanlica=("ععع",)), ota_madde("ععع", kok_kanit(KOK_SML), pos="verb")
    )
    k = karar(indeks, "pelin")
    assert (k.karar, k.neden) == (KOK_YOK, KANIT_YOK)


def test_ayni_lemmanin_butun_osmanlica_maddeleri_ayni_koke_gitmeli() -> None:
    indeks = indeks_kur(
        tr_madde("pelin", osmanlica=("ععع",)),
        ota_madde("ععع", kok_kanit(KOK_SML)),
        ota_madde("ععع", kok_kanit(KOK_BNR)),
    )
    assert karar(indeks, "pelin").karar == ADAY


# --- yuzey duzeyi: lemma tek olmali, kapali sinif disarida -----------------------------------


def yuzey(indeks: KaikkiIndeksi, *cozumler: tuple[str, str]) -> tuple[str, str]:
    k = yuzey_karari(analiz(*cozumler), indeks, ENV)
    return k.karar, k.neden


def test_bilinmeyen_sozcuk() -> None:
    assert yuzey(indeks_kur()) == (KOK_YOK, BILINMEYEN_SOZCUK)


@pytest.mark.parametrize("tur", ["Pron", "Conj", "Postp", "Det", "Ques"])
def test_kapali_sinif_kanit_olsa_da_dislanir(tur: str) -> None:
    indeks = indeks_kur(tr_madde("ve", kok_kanit(KOK_BNR), pos="conj"))
    assert yuzey(indeks, ("ve", tur)) == (KOK_YOK, KAPALI_SINIF)


def test_yardimci_fiil_dislanir() -> None:
    indeks = indeks_kur(tr_madde("olmak", kok_kanit(KOK_BNR), pos="verb"))
    assert yuzey(indeks, ("olmak", "Verb")) == (KOK_YOK, KAPALI_SINIF)


def test_kapali_cozumlerden_biri_yeter() -> None:
    indeks = indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR)))
    assert yuzey(indeks, ("tavan", "Noun"), ("tavan", "Pron")) == (KOK_YOK, KAPALI_SINIF)


def test_belirsiz_lemma_aday_kalir() -> None:
    indeks = indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR)))
    assert yuzey(indeks, ("tavan", "Noun"), ("tavanlamak", "Verb")) == (ADAY, BELIRSIZ_LEMMA)


def test_belirsiz_lemmalarin_hicbirinde_kanit_yoksa_kok_yok() -> None:
    assert yuzey(indeks_kur(), ("a", "Noun"), ("b", "Verb")) == (KOK_YOK, KANIT_YOK)


def test_tek_lemma_lemma_kararini_tasir() -> None:
    indeks = indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR)))
    k = yuzey_karari(analiz(("tavan", "Noun")), indeks, ENV)
    assert (k.karar, k.lemma) == (ONAYLI, "tavan") and k.lemma_karari is not None


def test_lemma_poslari_butun_bicimlerden_toplanir() -> None:
    """Lemmanin baska bir bicimde Verb olarak da cozulmesi turu birlestirir: Verb maddesi yok."""
    indeks = indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR)))
    k = yuzey_karari(
        analiz(("tavan", "Noun")),
        indeks,
        ENV,
        lemma_poslari={"tavan": frozenset({"Noun", "Verb"})},
    )
    assert (k.karar, k.neden) == (ADAY, POS_UYUSMAZLIGI)


# --- kanit nesnesi (K-51 biçimi) -------------------------------------------------------------


def test_kanit_k51_bicimindedir() -> None:
    k = karar(indeks_kur(tr_madde("dolap", etimon_kanit(ETIMON_SML))), "dolap")
    kanit = k.kanit()
    assert set(kanit) == {
        "politika",
        "politika_surumu",
        "yontem",
        "yontem_surumu",
        "kaynaklar",
        "qac",
        "karar",
        "neden",
    }
    assert kanit["politika_surumu"] == POLITIKA_SURUMU == "1"
    kaynak = kanit["kaynaklar"][0]  # type: ignore[index]
    assert set(kaynak) == {"source_id", "surum", "madde", "alan", "deger"}
    assert kaynak["source_id"] == "kaikki-tr" and kaynak["madde"] == "dolap"
    assert kaynak["deger"] == ETIMON_SML
    assert kanit["qac"]["eslesme"] == "etimon_lemma"  # type: ignore[index]
    assert kanit_hatalari(kanit, ONAYLI, "kosullar_saglandi") == []


@pytest.mark.parametrize(
    ("degisim", "hata"),
    [
        ({"kaynaklar": []}, "kanit_kaynak_yok"),
        ({"politika_surumu": "0"}, "kanit_politika_surumu"),
        ({"neden": "baska"}, "kanit_karar_tutmuyor"),
    ],
)
def test_gecersiz_kanit_onayli_satiri_reddeder(degisim: dict[str, object], hata: str) -> None:
    k = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR))), "tavan")
    kanit = {**k.kanit(), **degisim}
    assert hata in kanit_hatalari(kanit, ONAYLI, "kosullar_saglandi")


def test_kanit_qac_koku_olmayan_onayli_gecersiz() -> None:
    k = karar(indeks_kur(tr_madde("tavan", kok_kanit(KOK_BNR))), "tavan")
    kanit = k.kanit()
    kanit["qac"] = {"letters_bw": None, "letters": None, "eslesme": "yok"}
    hatalar = kanit_hatalari(kanit, ONAYLI, "kosullar_saglandi")
    assert "kanit_qac_kok_yok" in hatalar and "kanit_eslesme" in hatalar
    assert kanit_hatalari("kanit", ONAYLI, "x") == ["kanit_nesne_degil"]
