# ruff: noqa: RUF001, RUF002
"""Vikikaynak cikarici cekirdegi (A16.2; SENTETIK wikitext): kural tablosu ve sinir kurallari.

Her sinir kurali (K-49 madde 8) ayri sinanir. Vektor (`extract/meal.jsonl`) ayni cekirdegi
girdi-cikti ciftleriyle sinar; burada konum aralıklari, kenar karakterleri ve hata turleri var.
"""

import pytest

from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import elmalili_vikikaynak as ev
from mutalaa_pipeline.ingest.elmalili_vikikaynak import SayfaCikti, sayfa_cikar


def k(n: object, metin: str) -> str:
    return "{{kısım||" + str(n) + "}}" + metin + "\n"


def cikar(wikitext: str, sayi: int, sure: int = 2) -> SayfaCikti:
    return sayfa_cikar(wikitext, sure=sure, ayet_sayisi=sayi, eser="elmalili")


def metinler(c: SayfaCikti) -> list[str]:
    return [a.metin for a in c.ayetler]


def test_kural_tablosu_aciktir() -> None:
    assert set(ev.SABLON_KURALLARI) == {"eser başlığı", "ortalı ve hizalı", "kısım"}
    assert set(ev.ETIKET_KURALLARI) == {"ref", "br", "nowiki", "i", "b"}
    assert ev.ad_anahtari(" Eser_Başlığı ") == "eser başlığı"  # Turkce kucuk harf, bosluk ve _
    assert ev.ad_anahtari("KISIM") == "kısım"  # Turkce kucuk harf: I -> noktasiz i (acik esleme)


def test_satir_sonu_kurali() -> None:
    assert ev.satir_sonlari("a\nb") == "a b"
    assert ev.satir_sonlari("a\n\nb") == "a\nb"
    assert ev.satir_sonlari("a\n \n\t\nb") == "a\nb"
    assert ev.satir_sonlari("a\r\nb\rc") == "a b c"
    assert ev.satir_sonlari("a \n b") == "a b"


def test_kirpma_yalniz_u0020_u0009_u000a_u00a0_korunur() -> None:
    nbsp = "\u00a0"
    assert ev.kirp(" \t\n" + nbsp + "x" + nbsp + " \n") == nbsp + "x" + nbsp
    assert cikar(k(1, nbsp + "Deneme" + nbsp), 1).ayetler[0].metin == nbsp + "Deneme" + nbsp


def test_isaret_metnin_onunde_ve_metin_sonraki_isarete_kadar() -> None:
    c = cikar(k(1, "Deneme 1") + k(2, "Deneme 2"), 2)
    assert metinler(c) == ["Deneme 1", "Deneme 2"]
    assert c.isaret_sayisi == 2


def test_ilk_kayit_nfc_ve_bosluklar_bir_kez() -> None:
    c = cikar(k(1, "Deneâme   metin‌"), 1)
    assert metinler(c) == ["Deneâme metin‌"]  # NFC, bosluk dizisi tek, U+200C korunur


def test_nowiki_ref_br_entity_biçim_etiketleri() -> None:
    c = cikar(
        k(1, "A<ref>x</ref>B<br>C<br/>D &nbsp;E <nowiki>''F''</nowiki> ''G'' '''H'''"),
        1,
    )
    assert metinler(c) == ["AB C D \u00a0E ''F'' G H"]


def test_numarasiz_parca_onceki_ayete_tek_bosluk() -> None:
    c = cikar(k(1, "A") + k(",", "B") + k(2, "C"), 2)
    assert metinler(c) == ["A B", "C"]
    assert c.ayetler[0].uyari == ("numarasiz_parca",)
    assert len(c.ayetler[0].araliklar) == 2


def test_numarasiz_parca_ilk_ayetten_once_hata() -> None:
    with pytest.raises(GirdiHatasi):
        cikar(k(",", "A") + k(1, "B"), 1)


def test_aralikli_isaret_birlesik_meal() -> None:
    c = cikar(k(1, "A") + k("2-4", "B") + k(5, "C"), 5)
    assert metinler(c) == ["A", "B", "", "", "C"]
    assert c.ayetler[1].attrs == {"kapsam": "q:2:2-4"}
    for n in (2, 3):  # izleyenler: 3 ve 4 (indeks 2, 3)
        assert c.ayetler[n].attrs == {"birlesik_ile": "meal:elmalili:2:2"}
    assert all("birlesik_meal" in c.ayetler[i].uyari for i in (1, 2, 3))


def test_aralik_artan_degilse_hata() -> None:
    for bozuk in ("3-2", "3-3"):
        with pytest.raises(GirdiHatasi):
            cikar(k(1, "A") + k(bozuk, "B"), 3)


def test_yinelenen_numara_sirayla_birlestirilir() -> None:
    c = cikar(k(1, "A") + k(2, "B") + k(3, "C") + k(2, "D"), 3)
    assert metinler(c) == ["A", "B D", "C"]
    assert "yinelenen_numara" in c.ayetler[1].uyari
    assert "sira_disi" in c.ayetler[1].uyari  # 3'ten sonra 2: sira bozuk


def test_aralikli_isaretin_numarasi_yinelenemez() -> None:
    with pytest.raises(GirdiHatasi):
        cikar(k(1, "A") + k("2-3", "B") + k(3, "C"), 3)


def test_ardisik_isaretler_birlesik_ve_ortak_metin() -> None:
    bitisik = cikar(k(1, "A") + "{{kısım||2}}{{kısım||3}}B\n", 3)
    assert metinler(bitisik) == ["A", "B", ""]
    assert bitisik.ayetler[1].attrs == {"kapsam": "q:2:2-3"}
    ortak = cikar("{{kısım||1}}{{kısım||3}}X\n" + k(2, "Y"), 3)
    assert metinler(ortak) == ["X", "Y", "X"]
    assert ortak.ayetler[0].attrs == {} and ortak.ayetler[2].attrs == {}
    assert "ortak_metin" in ortak.ayetler[0].uyari and "ortak_metin" in ortak.ayetler[2].uyari


def test_ardisik_isaretlerde_numarasiz_isaret_atlanir_ve_uyarilir() -> None:
    c = cikar(k(1, "A") + "{{kısım||2}}{{kısım||,}}{{kısım||3}}B\n", 3)
    assert metinler(c) == ["A", "B", ""]
    assert "numarasiz_parca" in c.ayetler[1].uyari


def test_besmele_yalniz_acik_isaretle_ve_sure_kurali() -> None:
    c = cikar(k("besmele", "Deneme besmele") + k(1, "A"), 1, sure=2)
    meal = c.ayetler[0].attrs["besmele_meali"]
    assert meal == {"metin": "Deneme besmele", "content_hash": content_hash("Deneme besmele")}
    assert c.ayetler[0].uyari == ("besmele_meali",)
    for sure in (1, 9):  # sure 1'de besmele ayettir; sure 9'da besmele yoktur
        with pytest.raises(GirdiHatasi):
            cikar(k("besmele", "B") + k(1, "A"), 1, sure=sure)
    with pytest.raises(GirdiHatasi):  # besmele yalniz ilk isaretten once
        cikar(k(1, "A") + k("besmele", "B"), 1)
    with pytest.raises(GirdiHatasi):  # iki besmele
        cikar(k("besmele", "B") + k("besmele", "C") + k(1, "A"), 1)


def test_isaretsiz_besmele_metni_alinmaz_yalniz_bolge_ozeti() -> None:
    c = cikar("Deneme besmele metni\n" + k(1, "A"), 1)
    assert metinler(c) == ["A"]
    assert c.on_bolge is not None and set(c.on_bolge) == {"uzunluk", "sha256"}
    assert c.on_bolge["uzunluk"] == len("Deneme besmele metni")


def test_son_bolge_kapanis_etiketi_ve_bos_satir() -> None:
    c = cikar(k(1, "A") + "{{kısım||2}}B\n</div>", 2)
    assert metinler(c) == ["A", "B"] and c.son_bolge is not None
    c = cikar(k(1, "A") + "{{kısım||2}}B\n\nNot satiri\n", 2)
    assert metinler(c) == ["A", "B"] and c.son_bolge is not None
    assert c.son_bolge["uzunluk"] == len("Not satiri")
    assert cikar(k(1, "A") + k(2, "B"), 2).son_bolge is None


def test_konum_araligi_wikitext_dilimidir() -> None:
    wt = "{{Eser başlığı|başlık=x}}\n" + k(1, "Deneme A") + k(2, "Deneme B  ")
    c = cikar(wt, 2)
    for ayet, beklenen in zip(c.ayetler, ("Deneme A", "Deneme B"), strict=True):
        ((bas, son),) = ayet.araliklar
        assert wt[bas:son].strip(" \n") == beklenen
    sarili = "{{Ortalı ve hizalı|\n" + k(1, "Deneme A") + k(2, "Deneme B") + "}}"
    c = cikar(sarili, 2)
    for ayet, beklenen in zip(c.ayetler, ("Deneme A", "Deneme B"), strict=True):
        ((bas, son),) = ayet.araliklar
        assert sarili[bas:son].strip(" \n") == beklenen


def test_wikitext_ayristirmasi_geri_uretir() -> None:
    import mwparserfromhell

    wt = "{{Eser başlığı|başlık=x}}\n" + k(1, "Deneme A") + "''x''<ref>y</ref>"
    assert str(mwparserfromhell.parse(wt, context=0, skip_style_tags=False)) == wt


@pytest.mark.parametrize(
    "wikitext",
    [
        k(1, "A") + "{{Bilinmeyen|x}}",
        k(1, "A <span>x</span>"),
        k(1, "A [[x]]"),
        k(1, "A [http://x y]"),
        k(1, "A {{{arg}}}"),
        k(1, "A {{ acik"),
        k(1, "A }}"),
        k(1, "A <b>"),
        "Deneme",
        k("x", "A"),
        k("01", "A"),
        "{{kısım|1|2}}A",
        "{{kısım||1|x=2}}A",
        "{{Ortalı ve hizalı|a=1|\n" + k(1, "A") + "}}",
        "{{Ortalı ve hizalı|" + k(1, "<i>{{kısım||2}}A</i>") + "}}",
    ],
)
def test_bilinmeyen_ya_da_bozuk_girdi_hata(wikitext: str) -> None:
    with pytest.raises(GirdiHatasi):
        cikar(wikitext, 1)


def test_ayet_kumesi_tanzil_sayisiyla_esit_olmali() -> None:
    with pytest.raises(GirdiHatasi, match="kume"):
        cikar(k(1, "A") + k(2, "B"), 3)  # eksik ayet
    with pytest.raises(GirdiHatasi):
        cikar(k(1, "A") + k(2, "B"), 1)  # fazla ayet (sayi disinda)


def test_hata_iletileri_ascii_ve_metin_icermez() -> None:
    for wt in (k(1, "Deneme gizli {{ acik"), k(1, "A") + "{{Bilinmeyen|gizli}}"):
        with pytest.raises(GirdiHatasi) as hata:
            cikar(wt, 1)
        assert str(hata.value).isascii()
        assert "gizli" not in str(hata.value)


def test_birlesik_degismezi_ayristiricida_zorlanir() -> None:
    """Izleyen olmayan birimin metni bos olamaz; kapsam tasiyan bas birim de bos olamaz."""
    with pytest.raises(GirdiHatasi, match="bos"):
        cikar(k(1, "Deneme A") + "{{kısım||2}}\n", 2)  # son isaret bos
    with pytest.raises(GirdiHatasi, match="bos"):
        cikar("{{kısım||1-2}}\n", 2)  # kapsam tasiyan bas birim bos
    with pytest.raises(GirdiHatasi, match="bos"):
        cikar(k(1, "Deneme A") + k(2, "﻿"), 2)  # yalniz silinen karakter
    # izleyen birim bos metin + birlesik_ile ile gecerlidir
    c = cikar(k(1, "Deneme A") + k("2-3", "Deneme B"), 3)
    assert [a.metin for a in c.ayetler] == ["Deneme A", "Deneme B", ""]


def test_silinecek_cf_karakterleri_satir_sonundan_once_silinir() -> None:
    # U+FEFF iki satir sonunu ayirir gibi gorunur; once silinince bos satir olur (tek LF)
    c = cikar(k(1, "Deneme\n﻿\nmeal"), 1)
    assert c.ayetler[0].metin == "Deneme\nmeal"
    # silinen karakter satir sonu kuralini sasirtmaz: yalniz tek LF bosluk olur
    c = cikar(k(1, "Deneme­\nmeal"), 1)
    assert c.ayetler[0].metin == "Deneme meal"
    cf = "­‎‏‪‫‬‭‮⁦⁧⁨⁩؜﻿"
    c = cikar(k(1, "Deneme" + cf + " meal‌ parca‍"), 1)
    assert c.ayetler[0].metin == "Deneme meal‌ parca‍"  # U+200C ve U+200D korunur


def test_metin_ortasindaki_u0009_tek_bosluk_olur() -> None:
    assert cikar(k(1, "Deneme\tmeal\t\t parca"), 1).ayetler[0].metin == "Deneme meal parca"
