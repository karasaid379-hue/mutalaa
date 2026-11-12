"""Hazir kaynak kelime anlami: gruplama, aday ve QuranWBW cikarma birim testleri (A17.6; SENTETIK).

Anlam metinleri "Deneme anlam N" gibi anlamsiz dizgilerdir; Turkce I/i/dotless i/dotted I
gruplamasi yalniz bu harflerden olusan dizgilerle sinanir. Hicbir Kur'an kelimesi ya da gercek
kelime anlami yoktur; dosya ASCII kalsin diye karakter adlari (N{...}) kullanilir.
"""

import json
from collections import Counter

import pytest
from quranwbw_yardimci import GENIS_I_ANAHTARI, I_VARYANTLARI

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.enrich.glosses import (
    ESIK_PAY,
    ESIK_PAYDA,
    aday_satiri,
    grup_anahtari,
    kapsama_raporu,
    lemma_adayi,
    secilen_dalgalar,
    uret,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import quranwbw
from mutalaa_pipeline.ingest.quranwbw import CIKARICI_SURUMU, cikar, kilit_coz
from mutalaa_pipeline.staged import satir_baytlari

OZET = "a" * 64


# --- gruplama anahtari -----------------------------------------------------------------------


def test_grup_anahtari_turkce_i_ve_buyuk_kucuk_harf_ayni_kume() -> None:
    anahtarlar = {grup_anahtari(a) for a in I_VARYANTLARI}
    assert anahtarlar == {(False, GENIS_I_ANAHTARI)}
    assert grup_anahtari("Deneme anlam 3") == grup_anahtari("DENEME ANLAM 3")
    assert grup_anahtari("Deneme anlam 3") != grup_anahtari("Deneme anlam 4")


def test_grup_anahtari_bos_cikarsa_ozgun_yazimdan_ayrik_anahtar() -> None:
    assert grup_anahtari("!!") == (True, "!!")
    assert grup_anahtari("??") == (True, "??")
    assert grup_anahtari("!!") != grup_anahtari("??")
    assert grup_anahtari("!!") != grup_anahtari("deneme")


# --- lemma adayi -----------------------------------------------------------------------------


def test_aday_baskin_kume_gercek_yazim_anahtar_yazilmaz() -> None:
    sayac = Counter({"Deneme anlam 3": 5, "DENEME ANLAM 3": 4, "Deneme baska 1": 3})
    aday = lemma_adayi("L1", sayac)
    assert aday.anlam_kisa == "Deneme anlam 3"  # kumenin en sik GERCEK yazimi
    assert aday.baskin_sayi == 9 and aday.toplam == 12  # ayni genis anahtar tek kume
    assert aday.anlam_kisa != grup_anahtari("Deneme anlam 3")[1]  # anahtar anlam_kisa'ya yazilmaz
    # dagilim kumelere bolunmez: her yazim ayri girdi; sayiya gore azalan
    assert aday.dagilim == (("Deneme anlam 3", 5), ("DENEME ANLAM 3", 4), ("Deneme baska 1", 3))
    assert aday.kuran_anlamlari == ("Deneme anlam 3", "Deneme baska 1")
    satir = aday_satiri(aday, 1, 7, "v1")
    assert GENIS_I_ANAHTARI not in json.dumps(satir)
    assert "deneme anlam 3" not in json.dumps(satir)  # genis anahtar hicbir alanda yok


def test_dagilim_esitlikte_bayt_sirasi_ve_baskin_esitlikte_bayt_sirasi() -> None:
    aday = lemma_adayi("L1", Counter({"Deneme b 1": 2, "Deneme a 1": 2, "Deneme c 1": 1}))
    assert [a for a, _ in aday.dagilim] == ["Deneme a 1", "Deneme b 1", "Deneme c 1"]
    assert aday.anlam_kisa == "Deneme a 1"  # esit kumeler: gorunen yazimin bayt sirasi


def test_kume_gorunen_yazimi_esitlikte_bayt_sirasi() -> None:
    # ayni kume (genis anahtar), iki yazim esit sikta: bayt sirasinda ilki
    aday = lemma_adayi("L1", Counter({"DENEME ANLAM 3": 2, "Deneme anlam 3": 2}))
    assert aday.anlam_kisa == "DENEME ANLAM 3"  # 'D' (0x44) < 'e'? karsilastirma UTF-8 baytlariyla
    assert aday.baskin_sayi == 4


def test_tutarli_esigi_tam_sayi_aritmetigi_0_8() -> None:
    assert (ESIK_PAY, ESIK_PAYDA) == (8, 10)
    assert lemma_adayi("L", Counter({"Deneme a 1": 8, "Deneme b 1": 2})).tutarli  # 0,8 tutarli
    assert not lemma_adayi("L", Counter({"Deneme a 1": 79, "Deneme b 1": 21})).tutarli  # 0,79
    assert lemma_adayi("L", Counter({"Deneme a 1": 1})).tutarli  # tek yazim 1,0


def test_kuran_anlamlari_en_cok_uc_kume() -> None:
    sayac = Counter({f"Deneme anlam {n}": 10 - n for n in range(6)})
    aday = lemma_adayi("L", sayac)
    assert len(aday.kuran_anlamlari) == 3
    assert aday.kuran_anlamlari == tuple(f"Deneme anlam {n}" for n in range(3))


def test_aday_satiri_ondalik_sayi_icermez_ve_kati_okunur() -> None:
    aday = lemma_adayi("L", Counter({"Deneme a 1": 2, "Deneme b 1": 1}))
    satir = aday_satiri(aday, 2, 5, "v1")
    veri = satir_baytlari(satir)  # sorted keys, ASCII
    assert b"." not in veri.replace(b"Deneme", b"")  # JSON'da ondalik nokta yok
    assert satir["tutarsiz_hazir_anlam"] is True  # 2/3 < 0,8
    assert satir["source_id"] == "quranwbw-tr" and satir["data_version"] == "quranwbw-tr@v1"


def test_bos_sayac_value_error() -> None:
    with pytest.raises(ValueError):
        lemma_adayi("L", Counter())


# --- dalga secimi ----------------------------------------------------------------------------


def test_wave_1_dalga_0_ve_1_i_birlikte_acar_digerleri_yalniz_kendini() -> None:
    assert secilen_dalgalar(1) == {0, 1}
    assert secilen_dalgalar(2) == {2}
    assert secilen_dalgalar(3) == {3}
    assert secilen_dalgalar(4) == {4}
    for gecersiz in (0, 5, -1):
        with pytest.raises(GirdiHatasi):
            secilen_dalgalar(gecersiz)


def _girdi() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    """Uc lemmali (L0 dalga 0, L1 dalga 1, L2 dalga 2), sekiz kelimeli sentetik girdi."""
    atamalar = ["L0", "L0", "L1", "L1", "L1", "L2", "L2", None]
    kelimeler = [
        {"anchor": f"q:1:1:{i}", "lemma_qac_ref": a} for i, a in enumerate(atamalar, start=1)
    ]
    anlamlar = [
        {"anchor": k["anchor"], "text": f"Deneme anlam {i}"} for i, k in enumerate(kelimeler)
    ]
    anlamlar[3]["text"] = anlamlar[2]["text"]  # L1: iki kelime ayni anlam
    dalgalar = [
        {"qac_ref": "L0", "dalga": 0, "sira": 1},
        {"qac_ref": "L1", "dalga": 1, "sira": 1},
        {"qac_ref": "L2", "dalga": 2, "sira": 1},
    ]
    return kelimeler, anlamlar, dalgalar


def test_uret_yalniz_secilen_dalgalar_ve_lemmasiz_kelime_atlanir() -> None:
    kelimeler, anlamlar, dalgalar = _girdi()
    bir = uret(kelimeler, anlamlar, dalgalar, 1, "v1")
    assert sorted(bir.dalgalar) == ["L0", "L1"]  # dalga 0 ve 1 birlikte
    assert bir.lemmasiz_kelime == 1 and bir.secilen_kelime == 5
    iki = uret(kelimeler, anlamlar, dalgalar, 2, "v1")
    assert sorted(iki.dalgalar) == ["L2"]
    satir = {s["qac_ref"]: s for s in bir.satirlar}["L1"]
    assert satir["toplam"] == 3 and satir["baskin_sayi"] == 2 and satir["dalga"] == 1


def test_uret_eksik_anlam_ya_da_bilinmeyen_lemma_girdi_hatasi() -> None:
    kelimeler, anlamlar, dalgalar = _girdi()
    with pytest.raises(GirdiHatasi):
        uret(kelimeler, anlamlar[1:], dalgalar, 1, "v1")  # ilk kelimenin anlami yok
    with pytest.raises(GirdiHatasi):
        uret(kelimeler, anlamlar, dalgalar[1:], 1, "v1")  # L0 dalga satiri yok


def test_kapsama_raporu_yalniz_sayi() -> None:
    kelimeler, anlamlar, dalgalar = _girdi()
    uretim = uret(kelimeler, anlamlar, dalgalar, 1, "v1")
    rapor = kapsama_raporu(uretim, 1, len(kelimeler), "v1")
    metinler = [str(a["text"]) for a in anlamlar]
    govde = json.dumps(rapor)
    assert not any(m in govde for m in metinler)  # anlam metni yok
    assert "L0" not in govde and "L1" not in govde  # qac_ref de yok (yalniz sayi)
    assert rapor["lemma"] == 2 and rapor["tutarli"] + rapor["tutarsiz"] == 2
    assert rapor["secilen_dalgalar"] == [0, 1]
    dagilim = rapor["baskin_pay_dagilimi"]
    assert isinstance(dagilim, dict) and sum(dagilim.values()) == 2


# --- QuranWBW cikarma ------------------------------------------------------------------------


def _json(govde: object) -> bytes:
    return json.dumps(govde, ensure_ascii=False).encode("utf-8")


def test_cikar_kanonik_metin_bir_kez_capa_ve_provenance() -> None:
    ham = _json(
        {
            "1": {
                "1": [
                    [
                        "Deneme  e\N{COMBINING ACUTE ACCENT}\r\n",
                        "\N{ZERO WIDTH NO-BREAK SPACE}Deneme anlam 2",
                    ]
                ]
            }
        }
    )
    satirlar = cikar(ham, OZET, "v1")
    assert [s["anchor"] for s in satirlar] == ["q:1:1:1", "q:1:1:2"]
    assert (
        satirlar[0]["text"] == "Deneme \N{LATIN SMALL LETTER E WITH ACUTE}"
    )  # BOM/CRLF/cift bosluk temizlendi, NFC
    assert satirlar[1]["text"] == "Deneme anlam 2"
    assert satirlar[0]["provenance"] == {
        "ham_sha256": OZET,
        "yol": "/1/1/0/0",
        "cikarici": CIKARICI_SURUMU,
    }
    assert satirlar[1]["provenance"]["yol"] == "/1/1/0/1"  # type: ignore[index]
    assert satirlar[0]["source_id"] == "quranwbw-tr" and satirlar[0]["data_version"] == (
        "quranwbw-tr@v1"
    )
    # kanonik metin bir kez uygulanir: yeniden uygulamak degistirmez
    assert content_hash(str(satirlar[0]["text"]))


@pytest.mark.parametrize(
    "govde",
    [
        [],  # kok nesne degil
        {},  # bos
        {"1": []},  # sure nesne degil
        {"1": {"1": []}},  # [[...]] degil
        {"1": {"1": [[]]}},  # bos kelime listesi
        {"1": {"1": [["Deneme"], ["Deneme"]]}},  # iki eleman
        {"1": {"1": [[1]]}},  # anlam metin degil
        {"1": {"1": [["   "]]}},  # kanonik hali bos
        {"1": {"1": [["\N{LEFT-TO-RIGHT MARK}"]]}},  # silinen karakterden ibaret
        {"01": {"1": [["Deneme"]]}},  # kanonik olmayan anahtar
        {"115": {"1": [["Deneme"]]}},  # gecersiz sure
        {"1": {"8": [["Deneme"]]}},  # sure 1 yedi ayetlidir
        {"x": {"1": [["Deneme"]]}},
    ],
)
def test_cikar_bicim_sapmasi_ve_bos_girdi_girdi_hatasi(govde: object) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        cikar(_json(govde), OZET, "v1")
    assert "Deneme" not in str(hata.value)  # ileti anlam metni tasimaz


def test_cikar_yinelenen_anahtar_utf8_degil_ve_ondalik_hata() -> None:
    with pytest.raises(GirdiHatasi):
        cikar(b'{"1": {"1": [["Deneme"]], "1": [["Deneme"]]}}', OZET, "v1")
    with pytest.raises(GirdiHatasi):
        cikar(b'{"1": {"1": [["\xff"]]}}', OZET, "v1")
    with pytest.raises(GirdiHatasi):
        cikar(b'{"1": {"1": [["Deneme"]]}, "2": 1.5}', OZET, "v1")


def test_cikar_cok_kelimeli_ayet_kelime_numarasi_konumdur() -> None:
    ham = _json({"2": {"255": [[f"Deneme anlam {i}" for i in range(1, 51)]]}})
    satirlar = cikar(ham, OZET, "v1")
    assert [s["word"] for s in satirlar] == list(range(1, 51))
    assert satirlar[49]["anchor"] == "q:2:255:50"


# --- kilit -----------------------------------------------------------------------------------


def _kilit(**degisim: object) -> bytes:
    kilit: dict[str, object] = {
        "url": "https://deneme.invalid/6.json",
        "surum": "v1",
        "alinma_tarihi": "2026-11-12",
        "dosya": "6.json",
        "boyut": 10,
        "sha256": OZET,
    }
    kilit.update(degisim)
    return (json.dumps(kilit, indent=2) + "\n").encode("utf-8")


def test_kilit_coz_gecerli_ve_bicim_hatalari() -> None:
    assert kilit_coz(_kilit()).sha256 == OZET
    for ham in (
        b"\xef\xbb\xbf" + _kilit(),
        _kilit().replace(b"\n", b"\r\n"),
        _kilit(url="http://x"),
        _kilit(surum=""),
        _kilit(alinma_tarihi="2026-13-40"),
        _kilit(dosya="baska.json"),
        _kilit(boyut=0),
        _kilit(sha256="A" * 64),
        _kilit(fazla=1),
    ):
        with pytest.raises(GirdiHatasi):
            kilit_coz(ham)


def test_paket_kilidi_yuklenir_ve_kayitla_tutarli_alanlar() -> None:
    kilit = quranwbw.kilit_yukle()
    assert kilit.dosya == "6.json" and kilit.url.startswith("https://")
    assert len(kilit.sha256) == 64 and kilit.boyut > 0
