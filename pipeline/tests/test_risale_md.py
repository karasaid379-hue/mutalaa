# ruff: noqa: RUF001
"""Diyanet markdown ayristirmasi (A20.1; SENTETIK metin: "Deneme paragrafi N" ve Arap harfleri)."""

from mutalaa_pipeline.ingest.risale_md import anahtar_uret, md_coz

AR = "ا ب ت"
AR2 = "ث ج ح"


def test_baslik_duzeyleri_ve_front_matter_atilir() -> None:
    md = md_coz(
        "---\nsource_name: Deneme\n---\n\n# Deneme 1\n\n### Deneme 3\n\nDeneme paragrafi 1\n"
    )
    assert [(s.tur, s.duzey, s.duz) for s in md.govde] == [
        ("baslik", 1, "Deneme 1"),
        ("baslik", 3, "Deneme 3"),
        ("paragraf", None, "Deneme paragrafi 1"),
    ]
    assert md.sayilar["baslik"] == 2


def test_yedi_diyez_baslik_degil_paragraftir() -> None:
    md = md_coz("####### Deneme\n\n#Deneme\n")
    assert [s.tur for s in md.govde] == ["paragraf", "paragraf"]


def test_ayirac_ve_cit_blogu_birim_uretmez() -> None:
    md = md_coz(
        "Deneme paragrafi 1\n\n***\n\n```mermaid\ngraph TD;\nA-->B;\n```\n\n* * *\n\nDeneme 2\n"
    )
    assert [s.duz for s in md.govde] == ["Deneme paragrafi 1", "Deneme 2"]
    assert md.sayilar["ayirac"] == 2 and md.sayilar["kod_blogu"] == 1


def test_kalin_yazi_ve_dipnot_atfi_duz_metinden_arinir() -> None:
    md = md_coz("***Deneme:*** paragrafi [^hâşiye1] **iki** ve [^2].\n")
    (satir,) = md.govde
    assert satir.duz == "Deneme: paragrafi  iki ve ."
    assert md.sayilar["dipnot_atfi"] == 2 and md.sayilar["dipnot_tanimi"] == 0


def test_dipnot_tanimi_devam_satirlari_ve_atif_sayimi() -> None:
    md = md_coz(
        "Deneme [^a1] paragrafi\n\n***\n\n[^a1]: Birinci dipnot\n\nDevam paragrafi\n\n"
        "[^a2]: Ikinci dipnot\n"
    )
    assert [s.duz for s in md.govde] == ["Deneme  paragrafi"]
    assert [d.etiket for d in md.dipnotlar] == ["a1", "a2"]
    assert [s.duz for s in md.dipnotlar[0].satirlar] == ["Birinci dipnot", "Devam paragrafi"]
    assert md.sayilar["dipnot_tanimi"] == 2 and md.sayilar["dipnot_atfi"] == 1


def test_bos_dipnot_tanimi_ilk_satiri_bos_birakir() -> None:
    md = md_coz("[^a1]:\n\nMetin satiri\n")
    (dipnot,) = md.dipnotlar
    assert [s.duz for s in dipnot.satirlar] == ["", "Metin satiri"]
    assert dipnot.satirlar[0].anahtar == ""


def test_arapca_satir_ici_aralik_kod_noktasi_ve_yari_acik() -> None:
    md = md_coz(f'Deneme <span class="arabic" dir="rtl">{AR}</span> paragrafi\n')
    (satir,) = md.govde
    assert satir.duz == f"Deneme {AR} paragrafi"
    assert satir.araplar == ((7, 7 + len(AR)),)
    assert satir.arapca_metinleri == (AR,)
    assert satir.duz[satir.araplar[0][0] : satir.araplar[0][1]] == AR
    assert not satir.tam_arapca
    assert md.sayilar["arapca_isareti"] == 1


def test_arapca_blok_br_ile_satirlara_bolunur_ve_grup_paylasir() -> None:
    md = md_coz(f'<p class="arabic" dir="rtl">{AR}<br/>{AR2}</p>\n\nDeneme paragrafi 1\n')
    a, b, c = md.govde
    assert (a.duz, b.duz) == (AR, AR2)
    assert a.tam_arapca and b.tam_arapca and not c.tam_arapca
    assert a.araplar == ((0, len(AR)),) and b.araplar == ((0, len(AR2)),)
    assert a.grup == b.grup != c.grup
    assert md.sayilar["arapca_isareti"] == 1  # tek etiket


def test_anahtar_hareke_noktalama_ve_bosluktan_bagimsizdir() -> None:
    assert anahtar_uret("Deneme: Paragrafı, 1.") == anahtar_uret("Deneme Paragrafı 1")
    # NFC sonrasi karsilastirma: sira farkli hareke dizileri ayni anahtari verir
    assert anahtar_uret("بَّ") == anahtar_uret("بَّ") == "ب"


def test_html_ozel_karakterleri_cozulur_ve_etiketler_atilir() -> None:
    md = md_coz("Deneme&nbsp;<b>paragrafi</b> &amp; 1\n")
    (satir,) = md.govde
    assert satir.duz == "Deneme\N{NO-BREAK SPACE}paragrafi & 1"


def test_crlf_ve_bos_girdi() -> None:
    assert md_coz("").govde == ()
    md = md_coz("# Deneme\r\n\r\nDeneme paragrafi 1\r\n")
    assert [s.duz for s in md.govde] == ["Deneme", "Deneme paragrafi 1"]
