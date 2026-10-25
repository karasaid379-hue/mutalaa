"""Normalizasyon birim testleri (A05.5): ic kesme eslesmesi, vekiller, I/i, kaynak kurallari.

Kaynak yalniz ASCII'dir; ASCII disi karakterler `\\N{...}` ve `chr()` ile yazilir. Liste
dosyasinin bicim kurallari `test_export_ic_kesme.py` icindedir.
"""

import ast
import unicodedata
from pathlib import Path

import pytest

from mutalaa_pipeline import normalize as normalize_paketi
from mutalaa_pipeline.normalize import (
    NORMALIZER_VERSION,
    SearchKeys,
    lower_turkish,
    normalize_ar,
    normalize_tr,
    search_keys,
    split_scripts,
)
from mutalaa_pipeline.normalize import turkish as turkce
from mutalaa_pipeline.normalize import unicode as birim

NOKTASIZ_I = "\N{LATIN SMALL LETTER DOTLESS I}"
NOKTALI_BUYUK_I = "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}"
BA = "\N{ARABIC LETTER BEH}"
A_SAPKA = "\N{LATIN SMALL LETTER A WITH CIRCUMFLEX}"
U_UMLAUT = "\N{LATIN SMALL LETTER U WITH DIAERESIS}"
PAKET_KOKU = Path(normalize_paketi.__file__).parent


# --- Surum --------------------------------------------------------------------------------


def test_normalizer_version_1_0() -> None:
    assert NORMALIZER_VERSION == "1.0"
    assert isinstance(NORMALIZER_VERSION, str)


# --- Ic kesme: en uzun eslesme -------------------------------------------------------------


KISA_VE_UZUN = ("a'b", "a'bc'd")


def dar(metin: str, liste: tuple[str, ...]) -> str:
    return " ".join(turkce.dar_sozcukler(split_scripts(metin).tr, liste))


def test_en_uzun_eslesme_ortak_onekli_liste() -> None:
    # "a'bc'd" secilir: iki kesme silinir, ucuncu kesmeden sonrasi ek olarak atilir.
    assert dar("a'bc'de'f", KISA_VE_UZUN) == "abcde"
    # Yalniz kisa girdi olsaydi: bir kesme silinir, ikinci kesmeden sonrasi atilirdi.
    assert dar("a'bc'de'f", ("a'b",)) == "abc"


def test_en_uzun_eslesme_liste_sirasindan_bagimsiz() -> None:
    metin = "A'Bc'De'f"
    assert dar(metin, KISA_VE_UZUN) == dar(metin, tuple(reversed(KISA_VE_UZUN))) == "abcde"


def test_ic_kesme_saf_onektir_sinir_kosulu_yok() -> None:
    assert dar("a'bx", ("a'b",)) == "abx"  # girdiden sonra harf gelse de eslesir
    assert dar("a'b'x", ("a'b",)) == "ab"  # sonraki kesme ek baslatir


def test_ic_kesme_eslesmesi_genis_bicimle_yapilir() -> None:
    liste = ("i'caz",)
    c_sapka = "\N{LATIN SMALL LETTER A WITH CIRCUMFLEX}"
    sonuc = dar("\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}'c" + c_sapka + "z'da", liste)
    assert sonuc == "ic" + c_sapka + "z"  # dar anahtarda sapka kalir; kesme silinir
    # Buyuk I once noktasiz i olur; genis bicim "i'caz" ile basladigindan liste yine eslesir.
    assert dar("I'caz", liste) == NOKTASIZ_I + "caz"


def test_listede_olmayan_ic_kesme_ek_sayilir() -> None:
    assert dar("ab'cd", ("a'b",)) == "ab"
    assert dar("ab'cd", ()) == "ab"


def test_gercek_liste_onbellekli_ve_dosyayla_ayni() -> None:
    liste = turkce.ic_kesme_listesi()
    assert liste is turkce.ic_kesme_listesi()  # onbellek
    kok = turkce._kok_bul(Path(turkce.__file__))
    dosya = (kok / turkce.IC_KESME_YOLU).read_bytes().decode("utf-8")
    assert dosya == "".join(f"{girdi}\n" for girdi in liste)
    assert list(liste) == sorted(set(liste))


@pytest.mark.parametrize(
    "bozuk",
    [b"a'b", b"a'b\r\n", b"ab\n", b"a'b\n\n", b"A'b\n", b""],
    ids=["satir-sonu-yok", "crlf", "kesmesiz", "bos-satir", "buyuk-harf", "bos"],
)
def test_ic_kesme_coz_bozuk_listeyi_reddeder(bozuk: bytes) -> None:
    with pytest.raises(ValueError):
        turkce.ic_kesme_coz(bozuk.decode("utf-8"))


def test_ic_kesme_coz_gecerli() -> None:
    assert turkce.ic_kesme_coz("a'b\nc'd'e\n") == ("a'b", "c'd'e")


# --- Essiz vekil -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("a" + chr(0xD800) + "b", "a b"),  # yuksek vekil tek basina
        ("a" + chr(0xDBFF) + "b", "a b"),  # yuksek vekil son
        ("a" + chr(0xDC00) + "b", "a b"),  # alcak vekil tek basina
        ("a" + chr(0xDFFF) + "b", "a b"),  # alcak vekil son
        ("a" + chr(0xDC00) + chr(0xD800) + "b", "a b"),  # ters sira: ikisi de essiz
        ("a" + chr(0xD800) + chr(0xD800) + "b", "a b"),  # iki yuksek
        (chr(0xD800), ""),  # yalniz vekil
        ("a" + chr(0x1F600) + "b", "a b"),  # gecerli BMP disi simge: ayirici
        ("a" + chr(0xD7A3) + "b", "a" + chr(0xD7A3) + "b"),  # vekil araligi disi: Hangul harfi (Lo)
        ("a" + chr(0xE000) + "b", "a b"),  # ozel kullanim (Co): ayirici
    ],
    ids=[
        "yuksek",
        "yuksek-son",
        "alcak",
        "alcak-son",
        "ters-sira",
        "cift-yuksek",
        "yalniz",
        "gecerli-simge",
        "aralik-disi-hangul",
        "ozel-kullanim",
    ],
)
def test_essiz_vekil_bosluk_olur(girdi: str, beklenen: str) -> None:
    assert normalize_tr(girdi, "dar") == beklenen
    assert normalize_tr(girdi, "genis") == beklenen
    assert search_keys(girdi).tr_stem == turkce.tr_stem(girdi)


def test_essiz_vekil_arapca_anahtarda_da_bosluk() -> None:
    assert normalize_ar(BA + chr(0xD800) + BA) == BA + " " + BA
    assert split_scripts(chr(0xD800)).tr == " "
    assert split_scripts(chr(0xD800)).ar == " "


# --- On adim -----------------------------------------------------------------------------


def test_sifir_genislik_bosluk_bosluk_olur_diger_cf_silinir() -> None:
    assert normalize_tr("a\N{ZERO WIDTH SPACE}b", "dar") == "a b"
    assert normalize_tr("a\N{SOFT HYPHEN}b", "dar") == "ab"
    assert normalize_tr("a\N{ZERO WIDTH JOINER}b", "dar") == "ab"
    assert normalize_ar(BA + "\N{ZERO WIDTH SPACE}" + BA) == BA + " " + BA
    assert normalize_ar(BA + "\N{ARABIC LETTER MARK}" + BA) == BA + BA


def test_cf_silme_nfc_den_once_gelir() -> None:
    assert normalize_tr("e\N{LEFT-TO-RIGHT MARK}\N{COMBINING ACUTE ACCENT}", "dar") == "\xe9"


def test_split_scripts_konum_basina_bosluk() -> None:
    parcalar = split_scripts("ab" + BA + "\N{ARABIC FATHA}c")
    assert parcalar.tr == "ab  c"
    assert parcalar.ar == "  " + BA + "\N{ARABIC FATHA}" + " "
    assert split_scripts("") == ("", "")


def test_arapca_blok_sinirlari() -> None:
    for kod in (0x0600, 0x06FF, 0x0750, 0x077F, 0x08A0, 0x08FF, 0xFB50, 0xFDFF, 0xFE70, 0xFEFE):
        assert birim.arapca_mi(chr(kod)), hex(kod)
    for kod in (0x05FF, 0x0700, 0x074F, 0x0780, 0x089F, 0xFB4F, 0xFE6F, 0x0041):
        assert not birim.arapca_mi(chr(kod)), hex(kod)


# --- I/i ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "beklenen"),
    [
        ("I", NOKTASIZ_I),
        (NOKTALI_BUYUK_I, "i"),
        (NOKTASIZ_I, NOKTASIZ_I),
        ("i", "i"),
        ("ISIK", NOKTASIZ_I + "s" + NOKTASIZ_I + "k"),
        (NOKTALI_BUYUK_I + "MAN", "iman"),
        ("TITLE", "t" + "\N{LATIN SMALL LETTER DOTLESS I}" + "tle"),
        ("\N{LATIN CAPITAL LETTER S WITH CEDILLA}", "\N{LATIN SMALL LETTER S WITH CEDILLA}"),
        ("", ""),
    ],
)
def test_lower_turkish_i_tablosu(girdi: str, beklenen: str) -> None:
    assert lower_turkish(girdi) == beklenen


def test_python_dize_lower_hatasi_acik_eslemeyle_giderilir() -> None:
    # str.lower() noktali buyuk I'yi iki kod noktasina cevirir; lower_turkish tek `i` verir.
    assert len(NOKTALI_BUYUK_I.lower()) == 2
    assert lower_turkish(NOKTALI_BUYUK_I) == "i"
    assert "I".lower() == "i" != lower_turkish("I")


def test_son_sigma_baglami_uygulanmaz() -> None:
    sigma_buyuk = "\N{GREEK CAPITAL LETTER SIGMA}"
    sigma_kucuk = "\N{GREEK SMALL LETTER SIGMA}"
    son_sigma = "\N{GREEK SMALL LETTER FINAL SIGMA}"
    alfa = "\N{GREEK CAPITAL LETTER ALPHA}"
    assert (alfa + sigma_buyuk).lower().endswith(son_sigma)  # dize duzeyinde baglam var
    assert lower_turkish(alfa + sigma_buyuk).endswith(sigma_kucuk)
    assert not lower_turkish(alfa + sigma_buyuk).endswith(son_sigma)


def test_girdi_degismez_ve_yeni_dize_doner() -> None:
    liste = ["x'y"]
    kopya = list(liste)
    girdi = "Kur'an'" + NOKTASIZ_I + "n"
    for islem in (
        lambda t: lower_turkish(t),
        lambda t: normalize_tr(t, "dar"),
        lambda t: normalize_tr(t, "genis"),
        lambda t: normalize_ar(t),
        lambda t: search_keys(t),
        lambda t: split_scripts(t),
    ):
        islem(girdi)
        assert girdi == "Kur'an'" + NOKTASIZ_I + "n"
    turkce.dar_sozcukler("x'yz", liste)
    assert liste == kopya


def test_search_keys_alanlari_tek_tek_islevlerle_ayni() -> None:
    metin = (
        "Kur'"
        + A_SAPKA
        + "n'"
        + NOKTASIZ_I
        + "n m"
        + U_UMLAUT
        + "'min "
        + BA
        + "\N{ARABIC FATHA}"
        + BA
        + " \N{LATIN CAPITAL LETTER I WITH DOT ABOVE}man"
    )
    anahtarlar = search_keys(metin)
    assert isinstance(anahtarlar, SearchKeys)
    assert anahtarlar._fields == ("tr_narrow", "tr_wide", "tr_stem", "ar_norm")
    assert (
        anahtarlar.tr_narrow
        == normalize_tr(metin, "dar")
        == "kur" + A_SAPKA + "n m" + U_UMLAUT + "min iman"
    )
    assert anahtarlar.tr_wide == normalize_tr(metin, "genis") == "kuran mumin iman"
    assert anahtarlar.ar_norm == normalize_ar(metin) == BA + BA


def test_normalize_tr_gecersiz_anahtar() -> None:
    with pytest.raises(ValueError):
        normalize_tr("a", "stem")  # type: ignore[arg-type]


def test_fold_wide_sozcugu_katlar_kesmeye_dokunmaz() -> None:
    assert turkce.fold_wide(NOKTASIZ_I + "s" + NOKTASIZ_I + "k'" + A_SAPKA) == "isik'a"
    assert turkce.fold_wide("i\N{COMBINING DOT ABOVE}") == "i"
    assert turkce.fold_wide("a\N{COMBINING ENCLOSING CIRCLE}") == "a\N{COMBINING ENCLOSING CIRCLE}"


# --- Kategori kurali ---------------------------------------------------------------------


def test_sozcuk_kategorileri_on_bir_ve_harf_rakam_sekiz() -> None:
    assert len(birim.SOZCUK_KATEGORILERI) == 11
    assert len(birim.HARF_RAKAM_KATEGORILERI) == 8
    assert birim.HARF_RAKAM_KATEGORILERI < birim.SOZCUK_KATEGORILERI
    assert {"Mn", "Mc", "Me"} == birim.SOZCUK_KATEGORILERI - birim.HARF_RAKAM_KATEGORILERI


def test_isalnum_ile_ayrisan_karakterler() -> None:
    # Roma rakami (Nl) ve ust simge (No) isalnum dahil sozcuk karakteridir; alt cizgi (Pc) degil.
    assert unicodedata.category("\N{ROMAN NUMERAL TWELVE}") == "Nl"
    assert normalize_tr("a\N{ROMAN NUMERAL TWELVE}", "dar") == "a\N{SMALL ROMAN NUMERAL TWELVE}"
    assert normalize_tr("a_b", "dar") == "a b"


# --- Kaynak kurallari --------------------------------------------------------------------


def kaynaklar() -> list[Path]:
    return sorted(PAKET_KOKU.glob("*.py"))


def test_normalize_paketi_export_paketini_ice_aktarmaz() -> None:
    assert kaynaklar()
    for yol in kaynaklar():
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        for dugum in ast.walk(agac):
            adlar: list[str] = []
            if isinstance(dugum, ast.Import):
                adlar = [oge.name for oge in dugum.names]
            elif isinstance(dugum, ast.ImportFrom):
                modul = dugum.module or ""
                adlar = [modul, *(f"{modul}.{oge.name}" for oge in dugum.names)]
            for ad in adlar:
                parcalar = ad.split(".")
                assert "export" not in parcalar, f"{yol.name}: {ad}"
                assert "cli" not in parcalar, f"{yol.name}: {ad}"


def test_kaynakta_yerel_ayar_ve_yasak_islevler_yok() -> None:
    for yol in kaynaklar():
        kaynak = yol.read_text(encoding="utf-8")
        for yasak in (
            "isalnum(",
            "isalpha(",
            "isdigit(",
            "isnumeric(",
            "casefold(",
            ".upper(",
            "title(",
            "import locale",
            "\\d",
            "\\w",
            "open(",
            "splitlines",
        ):
            assert yasak not in kaynak, f"{yol.name}: {yasak}"


def test_nfkc_ve_nfkd_kullanilmaz() -> None:
    """Sunum bicimleri 1.0'da degismez: yalniz NFC ve NFD cagrilir."""
    kullanilan: set[str] = set()
    for yol in kaynaklar():
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        for dugum in ast.walk(agac):
            if (
                isinstance(dugum, ast.Call)
                and isinstance(dugum.func, ast.Attribute)
                and dugum.func.attr == "normalize"
                and dugum.args
                and isinstance(dugum.args[0], ast.Constant)
            ):
                kullanilan.add(str(dugum.args[0].value))
    assert kullanilan == {"NFC", "NFD"}


def test_dize_duzeyinde_lower_yok() -> None:
    """`.lower()` yalniz `lower_turkish` icinde, tek karakter degiskeninde cagrilir."""
    sayac = 0
    for yol in kaynaklar():
        agac = ast.parse(yol.read_text(encoding="utf-8"))
        for islev in ast.walk(agac):
            if not isinstance(islev, ast.FunctionDef):
                continue
            for dugum in ast.walk(islev):
                if (
                    isinstance(dugum, ast.Call)
                    and isinstance(dugum.func, ast.Attribute)
                    and dugum.func.attr == "lower"
                ):
                    sayac += 1
                    assert islev.name == "lower_turkish", f"{yol.name}:{islev.name}"
                    assert isinstance(dugum.func.value, ast.Name)
                    assert dugum.func.value.id == "karakter"
    assert sayac == 1


def test_duzenli_ifadeler_ascii_siniflari_kullanir() -> None:
    kaynak = (PAKET_KOKU / "turkish.py").read_text(encoding="utf-8")
    assert "[a-z]" in kaynak
    assert "re.compile" in kaynak


def test_kaynaklar_ascii_ve_lf() -> None:
    for yol in [*kaynaklar(), Path(__file__), Path(__file__).with_name("test_tr_stem.py")]:
        veri = yol.read_bytes()
        assert b"\r" not in veri, yol.name
        assert not veri.startswith(b"\xef\xbb\xbf"), yol.name
        assert all(b < 0x80 for b in veri), yol.name
