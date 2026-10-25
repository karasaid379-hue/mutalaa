"""Turkce arama anahtarlari: dar, genis ve govde (K-36 madde 2, 3, 5, 6; Arama 1.2).

Dar anahtar Turkce harfleri ve duzeltme isaretlerini korur; genis anahtar dar anahtardan
turetilir (noktasiz i -> i, NFD, U+0300-U+036F silme, NFC). Kucuk harf asla dize duzeyinde
`lower()` ile yapilmaz: once `I -> noktasiz i`, `noktali I -> i` acik eslemesi, sonra kod
noktasi basina basit kucuk harf (son sigma baglami uygulanmaz). Ic kesme listesi
`shared/data/ic-kesme.txt` dosyasindan `encoding="utf-8"` ile okunur; bu modul
`mutalaa_pipeline.export` paketine bagli degildir.
"""

import re
import threading
import unicodedata
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

from snowballstemmer.turkish_stemmer import TurkishStemmer

from mutalaa_pipeline.normalize.unicode import (
    BOSLUK,
    KESME,
    harf_ya_da_rakam_var_mi,
    sozcuklere_bol,
    split_scripts,
)

AnahtarTuru = Literal["dar", "genis"]

IC_KESME_YOLU: Final = "shared/data/ic-kesme.txt"
_KOK_ISARETI: Final = "pnpm-workspace.yaml"
_GIRDI: Final = re.compile(r"[a-z]+('[a-z]+)+")

_BUYUK_I: Final = "I"
_NOKTALI_BUYUK_I: Final = "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}"
_NOKTASIZ_I: Final = "\N{LATIN SMALL LETTER DOTLESS I}"
# Yedi kesme bicimi (K-36 madde 2): U+2019, U+2018, U+02BC, U+02BE, U+02BF, U+00B4, U+0060.
_KESME_BICIMLERI: Final = dict.fromkeys(
    (0x2019, 0x2018, 0x02BC, 0x02BE, 0x02BF, 0x00B4, 0x0060), KESME
)
_ISARET_BASI: Final = 0x0300
_ISARET_SONU: Final = 0x036F
# Govde oncesi katlama (K-36 madde 6): yalniz a/i/u uzerindeki sapka.
_DUZELTME_KATLAMA: Final = str.maketrans({0x00E2: "a", 0x00EE: "i", 0x00FB: "u"})


def lower_turkish(metin: str) -> str:
    """Turkce kucuk harf: `I -> noktasiz i`, `noktali I -> i`, digerleri kod noktasi basina."""
    sonuc: list[str] = []
    for karakter in metin:
        if karakter == _BUYUK_I:
            sonuc.append(_NOKTASIZ_I)
        elif karakter == _NOKTALI_BUYUK_I:
            sonuc.append("i")
        else:
            sonuc.append(karakter.lower())  # tek kod noktasi: son sigma baglami yok
    return "".join(sonuc)


def fold_wide(sozcuk: str) -> str:
    """Genis katlama: noktasiz i -> i, NFD, U+0300-U+036F sil, NFC. Kesmelere dokunmaz."""
    ayrik = unicodedata.normalize("NFD", sozcuk.replace(_NOKTASIZ_I, "i"))
    kalan = "".join(k for k in ayrik if not _ISARET_BASI <= ord(k) <= _ISARET_SONU)
    return unicodedata.normalize("NFC", kalan)


# --- Ic kesme listesi -------------------------------------------------------------------


def _kok_bul(baslangic: Path) -> Path:
    yol = baslangic.resolve()
    for aday in (yol, *yol.parents):
        if (aday / _KOK_ISARETI).is_file():
            return aday
    raise FileNotFoundError(f"depo koku bulunamadi ({_KOK_ISARETI} yok)")


def ic_kesme_coz(metin: str) -> tuple[str, ...]:
    """Liste metnini ayristirir; `[a-z]+('[a-z]+)+` desenine uymayan satirda ValueError."""
    if "\r" in metin or not metin.endswith("\n"):
        raise ValueError(f"{IC_KESME_YOLU}: LF satir sonlari ve sonda satir sonu bekleniyor")
    girdiler = tuple(metin[:-1].split("\n"))
    for sira, girdi in enumerate(girdiler, start=1):
        if _GIRDI.fullmatch(girdi) is None:
            raise ValueError(f"{IC_KESME_YOLU}:{sira}: girdi desene uymuyor")
    return girdiler


@lru_cache(maxsize=1)
def ic_kesme_listesi() -> tuple[str, ...]:
    """`shared/data/ic-kesme.txt` girdileri; ilk cagrida okunur ve onbellege alinir."""
    yol = _kok_bul(Path(__file__)) / IC_KESME_YOLU
    return ic_kesme_coz(yol.read_text(encoding="utf-8", newline=""))


def _ic_kesme_sil(sozcuk: str, liste: Sequence[str]) -> str:
    """Genis bicim bir girdiyle basliyorsa en uzun girdinin kesme sayisi kadar ilk kesmeyi siler."""
    genis = fold_wide(sozcuk)
    secilen: str | None = None
    for girdi in liste:
        if genis.startswith(girdi) and (secilen is None or len(girdi) > len(secilen)):
            secilen = girdi
    if secilen is None:
        return sozcuk
    kalan = secilen.count(KESME)
    cikti: list[str] = []
    for karakter in sozcuk:
        if karakter == KESME and kalan > 0:
            kalan -= 1
        else:
            cikti.append(karakter)
    return "".join(cikti)


# --- Dar sozcukler ------------------------------------------------------------------------


def _dar_sozcuk(sozcuk: str, liste: Sequence[str]) -> str | None:
    sozcuk = sozcuk.strip(KESME)  # bas ve sondaki kesme dizileri (4a)
    if not sozcuk:
        return None
    sozcuk = _ic_kesme_sil(sozcuk, liste)  # 4b
    ek_basi = sozcuk.find(KESME)  # 4c: kalan ilk kesmeden sonrasi ek
    if ek_basi >= 0:
        sozcuk = sozcuk[:ek_basi]
    sozcuk = unicodedata.normalize("NFC", sozcuk)  # 4d
    return sozcuk if harf_ya_da_rakam_var_mi(sozcuk) else None  # 4e


def dar_sozcukler(tr_parca: str, liste: Sequence[str]) -> list[str]:
    """Turkce parcadan dar anahtar sozcukleri (listeyi parametre alan ic islev)."""
    kucuk = lower_turkish(tr_parca).translate(_KESME_BICIMLERI)
    sonuc: list[str] = []
    for ham in sozcuklere_bol(kucuk, kesme_dahil=True):
        sozcuk = _dar_sozcuk(ham, liste)
        if sozcuk is not None:
            sonuc.append(sozcuk)
    return sonuc


def normalize_tr(metin: str, anahtar: AnahtarTuru) -> str:
    """Turkce anahtar: `"dar"` ya da `"genis"`."""
    if anahtar not in ("dar", "genis"):
        raise ValueError("anahtar 'dar' ya da 'genis' olmali")
    sozcukler = dar_sozcukler(split_scripts(metin).tr, ic_kesme_listesi())
    if anahtar == "dar":
        return BOSLUK.join(sozcukler)
    return BOSLUK.join(fold_wide(s) for s in sozcukler)


# --- Govde --------------------------------------------------------------------------------

_GOVDELEYICI: Final = TurkishStemmer()  # saf Python; ust duzey stemmer() kullanilmaz
_GOVDE_KILIDI: Final = threading.Lock()  # Snowball ornegi durumludur


@lru_cache(maxsize=65536)
def govde_sozcuk(dar_sozcuk: str) -> str:
    """Dar bir sozcugun govdesi (genis katlanmis); bos ya da harfsiz ise sozcugun genis bicimi."""
    with _GOVDE_KILIDI:
        govde = _GOVDELEYICI.stemWord(dar_sozcuk.translate(_DUZELTME_KATLAMA))
    katlanmis = fold_wide(govde)
    if not katlanmis or not harf_ya_da_rakam_var_mi(katlanmis):
        return fold_wide(dar_sozcuk)
    return katlanmis


def tr_stem_sozcukler(sozcukler: Sequence[str]) -> str:
    """Dar sozcuklerin govdelerini tek bosluk ile birlestirir."""
    return BOSLUK.join(govde_sozcuk(s) for s in sozcukler)


def tr_stem(metin: str) -> str:
    """Govde anahtari `tr_stem`; sozcuk sayisi ve sirasi `genis` ile ayni."""
    return tr_stem_sozcukler(dar_sozcukler(split_scripts(metin).tr, ic_kesme_listesi()))
