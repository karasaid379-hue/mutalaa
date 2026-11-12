"""QAC ayristirma, kilit ve morfoloji saf islevleri (A17.1, A17.3, A17.5; SENTETIK, dosyasiz).

Girdiler acikca sentetiktir: ASCII "Deneme" bildirimi ve Buckwalter tablosundaki harflerden
kurulan yer tutucu lemma/kok dizgileri; Kur'an kelimesi yoktur. Arapca beklentiler
`enrich.buckwalter` donusumunden hesaplanir.
"""

import unicodedata

import pytest

from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.enrich.buckwalter import TABLO, bw_arapca
from mutalaa_pipeline.enrich.morphology import (
    DALGA0_ETIKETLERI,
    DIGER_SAYFA_ETIKETLERI,
    HARF_ETIKETLERI,
    SAYFA_ETIKETLERI,
    ZAMIR_ETIKETLERI,
    Kelime,
    KokKaydi,
    LemmaKaydi,
    cuz_baslangici,
    dalgalari_hesapla,
    envanter_hesapla,
    idf_q,
    kelime_capasi,
    kelime_ozellikleri,
    kelimelere_topla,
    kimlik_ata,
    kok_harfleri,
    lemma_ayir,
    lemma_metni,
    uret,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import qac
from mutalaa_pipeline.ingest.qac import (
    UYARI,
    ayristir,
    bildirim_surumu,
    kilit_coz,
    kilit_denetle,
    kilit_metni,
    kilit_onerisi,
)
from mutalaa_pipeline.normalize import normalize_ar

BASLIK = "LOCATION\tFORM\tTAG\tFEATURES"
BILDIRIM = ["# DENEME BILDIRIM", "#  Quranic Arabic Corpus (morphology, version 9.9)", "#", ""]


def dosya(*satirlar: str, bildirim: list[str] | None = None) -> bytes:
    govde = [*(BILDIRIM if bildirim is None else bildirim), BASLIK, *satirlar]
    return ("\r\n".join(govde) + "\r\n").encode("ascii")


def segmentler(*satirlar: str) -> tuple[qac.Segment, ...]:
    return ayristir(dosya(*satirlar)).segmentler


# --- ayristirma --------------------------------------------------------------------------


def test_ayristir_alanlari_ve_bildirimi_okur() -> None:
    sonuc = ayristir(
        dosya(
            "(1:1:1:1)\tDeneme\tP\tPREFIX|bi+",
            "(1:1:1:2)\t\tN\tSUFFIX|PRON:3MS",  # FORM bos olabilir
            "(1:1:1:3)\tDeneme\tN\tSTEM|POS:N|LEM:bab|ROOT:bkt|MS|GEN",
        )
    )
    assert sonuc.bildirim == "\n".join(BILDIRIM[:3])  # LF'ye cevrildi, sondaki satir sonlari atildi
    assert bildirim_surumu(sonuc.bildirim) == "9.9"
    ilk, ikinci, ucuncu = sonuc.segmentler
    assert (ilk.sure, ilk.ayet, ilk.kelime, ilk.segment) == (1, 1, 1, 1)
    assert not ilk.govde and ilk.lem is None and ilk.kok is None
    assert ikinci.form == ""
    assert ucuncu.govde and ucuncu.lem == "bab" and ucuncu.kok == "bkt"
    assert ucuncu.ozellikler == ("STEM", "POS:N", "LEM:bab", "ROOT:bkt", "MS", "GEN")
    ozet = sonuc.bildirim_ozeti()
    assert ozet.satir == 3 and ozet.bayt == len(sonuc.bildirim.encode())


@pytest.mark.parametrize(
    "veri",
    [
        dosya("(1:1:1:1)\tDeneme\tN\tSTEM").replace(b"Deneme", "Denemeé".encode()),  # ASCII degil
        dosya("(1:1:1:1)\tD\tN\tSTEM").replace(b"\r\n", b"\n"),  # yalniz LF
        dosya("(1:1:1:1)\tD\tN\tSTEM")[:-2],  # son satir sonu yok
        dosya("(1:1:1:1)\tD\tN\tSTEM", bildirim=["# x"]).replace(BASLIK.encode(), b"BASLIK"),
        dosya(
            "(1:1:1:1)\tD\tN\tSTEM", bildirim=["x yorum degil"]
        ),  # bildirimde yorum olmayan satir
        dosya("(1:1:1:1)\tD\tN\tSTEM", bildirim=[""]),  # bildirim bos
        dosya("(1:1:1:1)\tD\tN"),  # uc sutun
        dosya("(1:1:1)\tD\tN\tSTEM"),  # konum bicimi
        dosya("(0:1:1:1)\tD\tN\tSTEM"),  # sifir numara
        dosya("(1:1:1:1)\tD\tN\tSTEM", "(1:1:1:1)\tD\tN\tSTEM"),  # yinelenen konum
        dosya("(1:1:1:1)\tD\tN\t"),  # bos FEATURES
        dosya("(1:1:1:1)\tD\tN\tSTEM|LEM:a|LEM:b"),  # LEM iki kez
        dosya("(1:1:1:1)\tD\tN\tSTEM|ROOT:"),  # bos ROOT
        dosya(),  # veri yok
    ],
)
def test_ayristir_bozuk_dosyayi_reddeder(veri: bytes) -> None:
    with pytest.raises(GirdiHatasi) as hata:
        ayristir(veri)
    assert "Deneme" not in str(hata.value)  # iletide icerik yok


def test_ayristir_baytlari_bellekte_ayirir_hicbir_dosya_yazmaz() -> None:
    veri = dosya("(2:3:4:1)\tD\tN\tSTEM|LEM:a")
    assert ayristir(veri).segmentler[0].lem == "a"
    assert veri.count(b"\r\n") == len(BILDIRIM) + 2  # girdi baytlari degismedi


# --- kilit -------------------------------------------------------------------------------


def test_kilit_onerisi_ve_denetim() -> None:
    veri = dosya("(1:1:1:1)\tD\tN\tSTEM")
    kilit = kilit_onerisi(veri, "2026-11-12", "https://deneme.invalid/x", "9.9")
    assert kilit_coz(kilit_metni(kilit).encode()) == kilit
    assert kilit_metni(kilit).endswith("}\n") and "\r" not in kilit_metni(kilit)
    kilit_denetle(kilit, veri)
    with pytest.raises(GirdiHatasi) as hata:
        kilit_denetle(kilit, veri + b"x")
    assert UYARI in str(hata.value)
    with pytest.raises(GirdiHatasi) as hata2:
        qac.bildirim_denetle(kilit, ayristir(dosya("(1:1:1:1)\tD\tN\tSTEM", bildirim=["# baska"])))
    assert UYARI in str(hata2.value)


@pytest.mark.parametrize(
    "degistir",
    [
        lambda s: s.replace('"url": "https://', '"url": "http://'),
        lambda s: s.replace('"surum": "9.9"', '"surum": "x"'),
        lambda s: s.replace("2026-11-12", "2026-13-12"),
        lambda s: s.replace(qac.DOSYA_ADI, "baska.txt"),
        lambda s: s.replace('"boyut"', '"boyutt"'),
        lambda s: s.replace("\n", "\r\n"),
        lambda s: "﻿" + s,
    ],
)
def test_kilit_bicim_hatasi(degistir: object) -> None:
    kilit = kilit_onerisi(
        dosya("(1:1:1:1)\tD\tN\tSTEM"), "2026-11-12", "https://d.invalid/x", "9.9"
    )
    metin = degistir(kilit_metni(kilit))  # type: ignore[operator]
    with pytest.raises(GirdiHatasi):
        kilit_coz(metin.encode("utf-8"))


# --- kelimeler ---------------------------------------------------------------------------


def test_kelimelere_topla_ilk_govdeyi_secer() -> None:
    kelimeler = kelimelere_topla(
        segmentler(
            "(1:1:1:1)\tD\tP\tPREFIX|bi+",
            "(1:1:1:2)\tD\tP\tSTEM|POS:P|LEM:aaa",
            "(1:1:1:3)\tD\tREL\tSTEM|POS:REL|LEM:bbb",
            "(1:1:2:1)\tD\tN\tSTEM|POS:N|LEM:ccc",
        )
    )
    assert [(k.sure, k.ayet, k.kelime) for k in kelimeler] == [(1, 1, 1), (1, 1, 2)]
    ilk = kelimeler[0]
    assert ilk.govde_indeksi == 1 and ilk.govde.lem == "aaa" and ilk.govde_sayisi == 2
    assert kelimeler[1].govde_sayisi == 1


def test_kelimelere_topla_bozuk_yapilari_reddeder() -> None:
    with pytest.raises(GirdiHatasi, match="govde"):
        kelimelere_topla(segmentler("(1:1:1:1)\tD\tP\tPREFIX|bi+"))
    with pytest.raises(GirdiHatasi, match="ardisik"):
        kelimelere_topla(
            segmentler(
                "(1:1:1:1)\tD\tN\tSTEM",
                "(1:1:2:1)\tD\tN\tSTEM",
                "(1:1:1:2)\tD\tN\tSTEM",
            )
        )
    with pytest.raises(GirdiHatasi, match="kesintisiz"):
        kelimelere_topla(segmentler("(1:1:1:2)\tD\tN\tSTEM"))


def test_kelime_capasi_yalniz_anchor_ile() -> None:
    assert kelime_capasi(2, 255, 3) == "q:2:255:3"
    for sure, ayet, kelime in ((115, 1, 1), (2, 287, 1), (1, 1, 1000), (0, 1, 1)):
        with pytest.raises(GirdiHatasi) as hata:
            kelime_capasi(sure, ayet, kelime)
        assert "gecersiz kelime konumu" in str(hata.value)


def test_kelime_ozellikleri_govde_onek_sonek() -> None:
    (kelime,) = kelimelere_topla(
        segmentler(
            "(1:1:1:1)\tD\tP\tPREFIX|bi+",
            "(1:1:1:2)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:bkt|MS|GEN",
            "(1:1:1:3)\tD\tPRON\tSUFFIX|PRON:3MS",
        )
    )
    assert kelime_ozellikleri(kelime) == {
        "govde": ["MS", "GEN"],
        "onek": [{"tag": "P", "ozellik": ["PREFIX", "bi+"]}],
        "sonek": [{"tag": "PRON", "ozellik": ["SUFFIX", "PRON:3MS"]}],
    }
    (yalin,) = kelimelere_topla(segmentler("(1:1:1:1)\tD\tN\tSTEM|POS:N"))
    assert kelime_ozellikleri(yalin) == {"govde": []}


# --- yazi --------------------------------------------------------------------------------


def test_lemma_ayir_ayirt_rakami() -> None:
    assert lemma_ayir("bab") == ("bab", None)
    assert lemma_ayir("bab2") == ("bab", 2)
    assert lemma_ayir("bab12") == ("bab", 12)
    assert lemma_ayir("2") == ("2", None)  # govdesiz rakam cevrilemez: lemma_metni hata verir


def test_lemma_metni_donusum_nfc_ve_text_clean() -> None:
    text, temiz, ayirt = lemma_metni("bab2", 7)
    assert text == kanonik_metin(bw_arapca("bab")) and ayirt == 2
    assert temiz == normalize_ar(text)
    # NFC yalniz burada ve bir kez: sedde (`~`) ile fetha (`a`) sirasi NFC'de degisir.
    ham = bw_arapca("b~a")
    text2, _, _ = lemma_metni("b~a", 1)
    assert text2 == unicodedata.normalize("NFC", ham) and text2 != ham
    assert lemma_metni("b~a", 1)[0] == kanonik_metin(text2)  # ikinci uygulama degistirmez
    for kotu in ("b?a", "2"):
        with pytest.raises(GirdiHatasi) as hata:
            lemma_metni(kotu, 5)
        assert str(hata.value) == "lemma 5: Buckwalter tablosunda olmayan karakter"


def test_kok_harfleri_bosluklu_ve_kotu_karakter() -> None:
    assert kok_harfleri("bkt", 1) == kanonik_metin(" ".join(bw_arapca(h) for h in "bkt"))
    assert kok_harfleri("bkt", 1).count(" ") == 2
    with pytest.raises(GirdiHatasi):
        kok_harfleri("b?t", 3)


# --- envanter ----------------------------------------------------------------------------


def _kelimeler() -> list[Kelime]:
    return kelimelere_topla(
        segmentler(
            "(1:1:1:1)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:bkt",
            "(1:1:2:1)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:bkt",
            "(1:2:1:1)\tD\tV\tSTEM|POS:V|LEM:bbb|ROOT:bkt",
            "(1:2:2:1)\tD\tPRON\tSTEM|POS:PRON",
            "(2:1:1:1)\tD\tP\tSTEM|POS:P|LEM:ccc",
            "(78:1:1:1)\tD\tN\tSTEM|POS:N|LEM:ddd|ROOT:kts",
            "(78:1:2:1)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:bkt",
        )
    )


def test_envanter_sayilari_ve_idf() -> None:
    env = envanter_hesapla(_kelimeler(), (78, 1))
    assert (env.kelime_sayisi, env.toplam_ayet) == (7, 4)
    assert (env.lemmasiz_kelime, env.koksuz_kelime, env.iki_govdeli_kelime) == (1, 2, 0)
    lemma = {lm.qac_ref: lm for lm in env.lemmalar}
    assert [lm.qac_ref for lm in env.lemmalar] == ["aaa", "bbb", "ccc", "ddd"]  # ilk gecis sirasi
    assert [lm.ilk_gecis for lm in env.lemmalar] == [1, 2, 3, 4]
    assert (lemma["aaa"].occurrences, lemma["aaa"].ayah_count) == (3, 2)  # 1:1 iki kelime
    assert lemma["aaa"].fatiha and lemma["aaa"].cuz30 and not lemma["ccc"].fatiha
    assert lemma["ddd"].cuz30 and not lemma["bbb"].cuz30
    assert lemma["ccc"].kok_bw is None
    kok = {k.letters_bw: k for k in env.kokler}
    assert (kok["bkt"].occurrences, kok["bkt"].ayah_count, kok["bkt"].ilk_gecis) == (4, 3, 1)
    assert kok["kts"].ilk_gecis == 2
    assert idf_q(1, 4) == "1.386294361"  # ln(4) dokuz ondalik
    assert idf_q(4, 4) == "0.000000000"
    for kotu in ((0, 4), (5, 4)):
        with pytest.raises(GirdiHatasi):
            idf_q(*kotu)


def test_lemma_birden_cok_kokle_gecerse_hata() -> None:
    kelimeler = kelimelere_topla(
        segmentler(
            "(1:1:1:1)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:bkt",
            "(1:1:2:1)\tD\tN\tSTEM|POS:N|LEM:aaa|ROOT:kts",
        )
    )
    with pytest.raises(GirdiHatasi, match="birden cok kokle"):
        envanter_hesapla(kelimeler, (999, 999))


def test_uret_belirlenimcidir_ve_satirlari_tutarlidir() -> None:
    kelimeler = segmentler(
        "(1:1:1:1)\tD\tN\tSTEM|POS:N|LEM:bab2|ROOT:bkt|MS",
        "(1:1:2:1)\tD\tN\tSTEM|POS:N|LEM:bab|ROOT:bkt|MS",
    )
    bir = uret(kelimeler, (999, 1), "9.9")
    iki = uret(kelimeler, (999, 1), "9.9")
    assert bir.kelime_satirlari == iki.kelime_satirlari
    assert bir.lemma_satirlari == iki.lemma_satirlari
    assert [r["anchor"] for r in bir.kelime_satirlari] == ["q:1:1:1", "q:1:1:2"]
    assert {r["qac_ref"]: r["ayirt_no"] for r in bir.lemma_satirlari} == {"bab2": 2, "bab": None}
    metinler = {r["text"] for r in bir.lemma_satirlari}
    assert len(metinler) == 1  # iki homograf ayni Arapca metin; kimlik qac_ref'e bagli
    assert all(r["data_version"] == "qac-morfoloji@9.9" for r in bir.kok_satirlari)
    assert all(isinstance(r["idf_q"], str) for r in bir.lemma_satirlari)  # JSON'da ondalik yok


# --- dalgalar ----------------------------------------------------------------------------


def _lemma(
    ad: str,
    sira: int,
    adet: int,
    kok: str | None,
    etiket: str = "N",
    *,
    fatiha: bool = False,
    cuz30: bool = False,
) -> LemmaKaydi:
    lm = LemmaKaydi(ad, sira, kok, occurrences=adet, fatiha=fatiha, cuz30=cuz30)
    lm.etiketler[etiket] = adet
    return lm


def test_dalga_yuzdeleri_dalga0_disarida_ve_zorla() -> None:
    kokler = [KokKaydi("x", 1, 0), KokKaydi("y", 2, 0)]
    adetler = [40, 20, 10, 10, 8, 5, 3, 2, 1, 1]  # toplam 100 (dalga 0 disarida)
    lemmalar = [_lemma(f"l{i}", i + 1, n, None) for i, n in enumerate(adetler)]
    lemmalar.append(_lemma("zamir", 11, 500, None, "PRON"))  # en sik ama dalga 0
    lemmalar.append(_lemma("harf", 12, 90, None, "P", fatiha=True))  # dalga 0'da kalir
    lemmalar[8].fatiha = True  # l8 (siklik dalgasi 4) -> 1'e alinir
    sonuc = {d.qac_ref: d for d in dalgalari_hesapla(lemmalar, kokler)}
    beklenen = {
        "l0": 1,  # birikim 0 < 50
        "l1": 1,  # 40 < 50
        "l2": 2,  # 60 < 80
        "l3": 2,  # 70 < 80
        "l4": 3,  # 80: %80 esigine ulasildi, 88 < 95
        "l5": 3,
        "l6": 3,  # 93 < 95
        "l7": 4,  # 96
        "l8": 1,  # 98 -> dalga 4 iken Fatiha ile 1'e alindi
        "l9": 4,
        "zamir": 0,
        "harf": 0,
    }
    assert {k: v.dalga for k, v in sonuc.items()} == beklenen
    assert sonuc["l8"].zorla and sonuc["l8"].fatiha and not sonuc["harf"].zorla
    assert not sonuc["l0"].zorla
    assert sonuc["zamir"].etiket == "PRON"


def test_dalga_sirasi_kok_toplamina_gore_koksuz_sonda() -> None:
    kokler = [KokKaydi("x", 1, 45), KokKaydi("y", 2, 60), KokKaydi("z", 3, 60)]
    lemmalar = [
        _lemma("a", 1, 40, "x"),
        _lemma("b", 2, 20, "y"),
        _lemma("c", 3, 15, "y"),  # y koku icinde b'den sonra
        _lemma("d", 4, 15, "z"),  # z, y ile ayni toplam: ilk gecisi buyuk -> y'den sonra
        _lemma("e", 5, 30, None),  # koksuz: sonda
        _lemma("f", 6, 5, "x"),  # x koku icinde a'dan sonra
    ]
    # Hepsi Fatiha lemmasi: dalga 1'e zorlanir; boylece tek dalgada kok sirasi sinanir.
    for lm in lemmalar:
        lm.fatiha = True
    sonuc = dalgalari_hesapla(lemmalar, kokler)
    dalga1 = [d for d in sonuc if d.dalga == 1]
    assert len(dalga1) == len(lemmalar)
    sirali = [d.qac_ref for d in sorted(dalga1, key=lambda d: d.sira)]
    assert [d.sira for d in sorted(dalga1, key=lambda d: d.sira)] == list(range(1, len(dalga1) + 1))
    # kok toplami azalan: y(60, ilk gecis 2), z(60, ilk gecis 3), x(45); sonra koksuz
    assert sirali == ["b", "c", "d", "a", "f", "e"]


def test_dalga_sirasi_esitlikte_ilk_gecis() -> None:
    kokler = [KokKaydi("x", 1, 10), KokKaydi("y", 2, 10)]
    lemmalar = [_lemma("a", 3, 4, "y"), _lemma("b", 1, 4, "x"), _lemma("c", 2, 4, "x")]
    for lm in lemmalar:
        lm.cuz30 = True
    sirali = [d.qac_ref for d in dalgalari_hesapla(lemmalar, kokler) if d.dalga == 1]
    assert sirali == ["b", "c", "a"]  # kok esit: x once (ilk gecis); kok icinde lemma ilk gecisi


def test_dalga0_etiket_kumeleri_sayfa_gruplamasiyla_tutarli() -> None:
    assert {"PRON", "DEM", "REL"} == ZAMIR_ETIKETLERI
    assert len(HARF_ETIKETLERI) == 33
    assert not (DALGA0_ETIKETLERI & DIGER_SAYFA_ETIKETLERI)
    assert len(SAYFA_ETIKETLERI) == 44  # sayfa 44 etiket listeler (DET sayfada yok)
    assert "DET" not in SAYFA_ETIKETLERI
    assert {"N", "PN", "ADJ", "IMPN", "T", "LOC", "V", "INL"} == DIGER_SAYFA_ETIKETLERI


# --- cuz sinirlari ve kimlik -------------------------------------------------------------


def test_cuz_baslangici_isaretlerden() -> None:
    isaretler = [
        {"kind": "cuz", "no": 29, "anchor": "q:67:1"},
        {"kind": "hizb", "no": 30, "anchor": "q:1:1"},
        {"kind": "cuz", "no": 30, "anchor": "q:78:1"},
    ]
    assert cuz_baslangici(isaretler) == (78, 1)
    assert cuz_baslangici(isaretler, 29) == (67, 1)
    for kotu in (
        [],
        [{"kind": "cuz", "no": 30, "anchor": "q:200:1"}],
        [{"kind": "cuz", "no": 30, "anchor": "q:78:1:2"}],
        [{"kind": "cuz", "no": 30}],
    ):
        with pytest.raises(GirdiHatasi):
            cuz_baslangici(kotu)


def test_kimlik_ata_kalici_ve_belirlenimci() -> None:
    anahtarlar = ["a", "b", "c", "d"]
    bos = kimlik_ata({}, anahtarlar)
    assert bos == {"a": 1, "b": 2, "c": 3, "d": 4}  # bos veritabani: ilk gecis sirasiyla
    assert kimlik_ata({}, anahtarlar) == bos  # ayni girdi ayni sonuc
    assert kimlik_ata(bos, anahtarlar) == bos  # ikinci calistirma: hicbir kimlik degismez
    karisik = kimlik_ata({"b": 2, "a": 5}, ["b", "c", "a", "d"])
    assert karisik == {"b": 2, "c": 6, "a": 5, "d": 7}  # var olan korunur, yeni max(id)+1'den
    assert kimlik_ata(karisik, ["b", "c", "a", "d", "e"])["e"] == 8
    assert kimlik_ata({"z": 9}, []) == {}
    with pytest.raises(ValueError, match="yinelenen"):
        kimlik_ata({}, ["a", "a"])


def test_tablo_harfleriyle_sentetik_lemma_cevrilebilir() -> None:
    """Yer tutucu dizgiler yalniz tablodaki karakterlerden olusur (test yardimcisi varsayimi)."""
    ornek = "".join(list(TABLO)[:5])
    assert lemma_metni(ornek, 1)[0] == kanonik_metin(bw_arapca(ornek))
