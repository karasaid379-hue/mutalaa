"""`tr_stem` testleri (A05.5, K-36 madde 6).

Degismez kural: `tr_wide` ve `tr_stem` ayni sayida sozcuk tasir ve sozcuk sirasi aynidir.
Govdeleyici `snowballstemmer` 3.1.1 saf Python `TurkishStemmer` sinifidir. Kaynak yalniz
ASCII'dir; ASCII disi karakterler `\\N{...}` ve `chr()` ile yazilir. Beklenen govdeler
calistirilip dogrulanmistir; her birinin nedeni yaninda yazilidir.
"""

import importlib.metadata
import random
from pathlib import Path

import pytest
import snowballstemmer.turkish_stemmer as tr_modulu
from test_normalize_vectors import TR

from mutalaa_pipeline.normalize import normalize_tr, search_keys, tr_stem
from mutalaa_pipeline.normalize import turkish as turkce

A_SAPKA = "\N{LATIN SMALL LETTER A WITH CIRCUMFLEX}"
I_SAPKA = "\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}"
U_SAPKA = "\N{LATIN SMALL LETTER U WITH CIRCUMFLEX}"
NOKTASIZ_I = "\N{LATIN SMALL LETTER DOTLESS I}"
NOKTALI_BUYUK_I = "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}"
CENGELLI_S = "\N{LATIN SMALL LETTER S WITH CEDILLA}"
UMLAUTLU_U = "\N{LATIN SMALL LETTER U WITH DIAERESIS}"


def sozcukler(anahtar: str) -> list[str]:
    return anahtar.split(" ") if anahtar else []


# --- Degismez kural ----------------------------------------------------------------------


@pytest.mark.parametrize("vektor", TR, ids=[v["id"] for v in TR])
def test_vektor_girdilerinde_wide_ve_stem_ayni_sayida_ve_sirada(vektor: dict[str, object]) -> None:
    girdi = vektor["input"]
    assert isinstance(girdi, str)
    anahtarlar = search_keys(girdi)
    genis = sozcukler(anahtarlar.tr_wide)
    govde = sozcukler(anahtarlar.tr_stem)
    dar = sozcukler(anahtarlar.tr_narrow)
    assert len(genis) == len(govde) == len(dar)
    assert [turkce.govde_sozcuk(s) for s in dar] == govde  # sira sozcuk sozcuk ayni
    assert anahtarlar.tr_stem == tr_stem(girdi)
    assert "  " not in anahtarlar.tr_stem
    assert anahtarlar.tr_stem == anahtarlar.tr_stem.strip(" ")


ALFABE = [
    *"abcdeIiklmnorstuyz0123456789",
    NOKTASIZ_I,
    NOKTALI_BUYUK_I,
    CENGELLI_S,
    UMLAUTLU_U,
    A_SAPKA,
    I_SAPKA,
    U_SAPKA,
    "'",
    "\N{RIGHT SINGLE QUOTATION MARK}",
    "-",
    ",",
    " ",
    "\t",
    "\n",
    "\N{COMBINING CIRCUMFLEX ACCENT}",
    "\N{COMBINING ACUTE ACCENT}",
    "\N{SOFT HYPHEN}",
    "\N{ZERO WIDTH SPACE}",
    "\N{ARABIC LETTER BEH}",
    "\N{ARABIC FATHA}",
    "\N{ARABIC COMMA}",
    chr(0xD800),
    chr(0x1F600),
    "\N{SUPERSCRIPT TWO}",
]


def rastgele_metin(rng: random.Random) -> str:
    uzunluk = rng.randint(0, 40)
    return "".join(rng.choice(ALFABE) for _ in range(uzunluk))


def test_rastgele_metinlerde_degismez_kural() -> None:
    rng = random.Random(20261025)  # sabit tohum: deterministik
    for _ in range(3000):
        metin = rastgele_metin(rng)
        anahtarlar = search_keys(metin)
        genis = sozcukler(anahtarlar.tr_wide)
        govde = sozcukler(anahtarlar.tr_stem)
        assert len(genis) == len(govde), repr(metin)
        assert len(govde) == len(sozcukler(anahtarlar.tr_narrow)), repr(metin)
        assert "" not in govde, repr(metin)
        assert tr_stem(metin) == anahtarlar.tr_stem
        assert normalize_tr(metin, "genis") == anahtarlar.tr_wide


def test_rastgele_sozcuklerde_govde_bos_degil_ve_harf_tasir() -> None:
    rng = random.Random(7)
    harfler = "abcdeghiklmnoprstuvyz" + NOKTASIZ_I + CENGELLI_S + UMLAUTLU_U
    for _ in range(2000):
        sozcuk = "".join(rng.choice(harfler) for _ in range(rng.randint(1, 14)))
        govde = turkce.govde_sozcuk(sozcuk)
        assert govde
        assert any(k.isalpha() for k in govde)


# --- On katlama (K-36 madde 6) ---------------------------------------------------------


def test_duzeltme_isaretli_sozcuk_govdelenir() -> None:
    ham = tr_modulu.TurkishStemmer()
    # Snowball sesli harf tanimi yalniz a e i o u (ve noktasiz i, o, u umlaut) harflerini kapsar;
    # sapkali harfler sesli sayilmaz, bu yuzden onkatlama olmadan ek atilmaz.
    assert ham.stemWord("kur" + A_SAPKA + "n") == "kur" + A_SAPKA + "n"
    assert tr_stem("kur" + A_SAPKA + "n") == "kura"  # onkatlama: kuran -> kura
    assert tr_stem("kuran") == "kura"
    assert tr_stem("kur" + A_SAPKA + "n") == tr_stem("kuran")


def test_sapkali_sozcuk_ek_alirsa_govdelenir() -> None:
    ham = tr_modulu.TurkishStemmer()
    sozcuk = I_SAPKA + "m" + A_SAPKA + "nlar"
    assert ham.stemWord(sozcuk) == sozcuk  # ham: sapka sesli sayilmadigindan degismez
    assert tr_stem(sozcuk) == "iman"  # iman + lar -> iman (ek atildi)
    assert tr_stem("h" + A_SAPKA + "l" + A_SAPKA) == "hal"  # hala -> hal


def test_yalniz_uc_harf_katlanir() -> None:
    kati = turkce._DUZELTME_KATLAMA
    cikti = (A_SAPKA + I_SAPKA + U_SAPKA).translate(kati)
    assert cikti == "aiu"
    korunanlar = NOKTASIZ_I + CENGELLI_S + UMLAUTLU_U + "\N{LATIN SMALL LETTER G WITH BREVE}"
    assert korunanlar.translate(kati) == korunanlar
    assert "\N{LATIN SMALL LETTER O WITH DIAERESIS}\N{LATIN SMALL LETTER C WITH CEDILLA}".translate(
        kati
    ) == ("\N{LATIN SMALL LETTER O WITH DIAERESIS}\N{LATIN SMALL LETTER C WITH CEDILLA}")


# --- Belirli govdeler (calistirilarak dogrulandi) ------------------------------------------


@pytest.mark.parametrize(
    ("girdi", "beklenen", "neden"),
    [
        ("kitaplar", "kitap", "cogul eki -lar atilir"),
        ("kitaplar" + NOKTASIZ_I + "m" + NOKTASIZ_I + "zdan", "kitap", "iyelik ve ayrilma eki"),
        ("evlerinden", "ev", "cogul, iyelik ve ayrilma eki"),
        ("okullar", "okul", "cogul eki"),
        ("ilm", "ilm", "ek yok: sozcuk degismez"),
        ("ok", "ok", "kisa sozcuk korunur"),
        ("a", "a", "tek harf korunur"),
        ("1", "1", "rakam sozcugu govdelenmez"),
        ("kur" + A_SAPKA + "n", "kura", "onkatlama sonrasi kuran -> kura (son n atilir)"),
        ("h" + A_SAPKA + "l" + A_SAPKA, "hal", "onkatlama: hala -> hal"),
        (NOKTASIZ_I + CENGELLI_S + NOKTASIZ_I + "klar", "isik", "sonuc genis katlanir"),
        ("k" + A_SAPKA + "tipler", "katip", "onkatlama + cogul eki"),
    ],
)
def test_belirli_govdeler(girdi: str, beklenen: str, neden: str) -> None:
    assert tr_stem(girdi) == beklenen, neden


def test_ayni_sozcuk_ayni_govde_onbellek_tutarli() -> None:
    once = turkce.govde_sozcuk("kitaplar")
    sonra = turkce.govde_sozcuk("kitaplar")
    assert once == sonra == "kitap"
    bilgi = turkce.govde_sozcuk.cache_info()
    assert bilgi.hits >= 1


# --- Bos govde yedegi --------------------------------------------------------------------


class _BosGovdeleyici:
    def stemWord(self, sozcuk: str) -> str:
        return ""


class _HarfsizGovdeleyici:
    def stemWord(self, sozcuk: str) -> str:
        return "'-"


@pytest.mark.parametrize(
    "sahte", [_BosGovdeleyici(), _HarfsizGovdeleyici()], ids=["bos", "harfsiz"]
)
def test_bos_ya_da_harfsiz_govde_yedegi_genis_bicimdir(
    monkeypatch: pytest.MonkeyPatch, sahte: object
) -> None:
    monkeypatch.setattr(turkce, "_GOVDELEYICI", sahte)
    turkce.govde_sozcuk.cache_clear()
    try:
        sozcuk = NOKTASIZ_I + CENGELLI_S + NOKTASIZ_I + "k"
        assert turkce.govde_sozcuk(sozcuk) == "isik"  # sozcugun genis bicimi
        assert tr_stem(sozcuk + " " + NOKTALI_BUYUK_I + "man") == "isik iman"
        # yedek de sayi ve sirayi korur
        anahtarlar = search_keys("Kitaplar " + sozcuk)
        assert len(sozcukler(anahtarlar.tr_stem)) == len(sozcukler(anahtarlar.tr_wide)) == 2
    finally:
        turkce.govde_sozcuk.cache_clear()


# --- Surum sabitlemesi -------------------------------------------------------------------


def test_govdeleyici_saf_python_turkish_stemmer_ve_surum_3_1_1() -> None:
    assert importlib.metadata.version("snowballstemmer") == "3.1.1"
    ornek = turkce._GOVDELEYICI
    assert type(ornek) is tr_modulu.TurkishStemmer
    assert type(ornek).__module__ == "snowballstemmer.turkish_stemmer"
    kaynak = Path(tr_modulu.__file__)
    assert kaynak.suffix == ".py"  # C uzantisi (PyStemmer) degil, saf Python


def test_pyproject_tam_surumu_sabitler() -> None:
    kok = Path(__file__).resolve().parents[1]
    metin = (kok / "pyproject.toml").read_text(encoding="utf-8")
    assert '"snowballstemmer==3.1.1"' in metin


def test_kaynak_ust_duzey_stemmer_kullanmaz() -> None:
    kaynak = Path(turkce.__file__).read_text(encoding="utf-8")
    assert "from snowballstemmer.turkish_stemmer import TurkishStemmer" in kaynak
    assert "snowballstemmer.stemmer" not in kaynak
    assert "import snowballstemmer\n" not in kaynak
