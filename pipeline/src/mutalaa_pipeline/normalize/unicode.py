"""Ortak Unicode adimlari: ortak on adim ve yazi sistemine gore bolme (K-36 madde 1).

Siralama: (a) essiz vekil -> U+0020; (b) U+200B -> U+0020, diger bicim karakterleri (Cf)
silinir; (c) NFC; (d) Arapca bloklardaki her kod noktasi Arapca parcaya, digerleri Turkce
parcaya gider, oburunda o konum tek U+0020 olur. Kategoriler `unicodedata.category`
ile okunur (`isalnum`, `isalpha`, regex w sinifi kullanilmaz). Islevler girdiyi degistirmez.
Bu modul yalniz kanonik olmayan arama sutunlari icindir; kanonik metne uygulanmaz (K-26).
"""

import unicodedata
from typing import Final, NamedTuple

BOSLUK: Final = " "
KESME: Final = "'"

# Arapca bloklari (K-36 madde 1d), kapali araliklar.
ARAPCA_BLOKLARI: Final = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
# Sozcuk karakteri: Lu Ll Lt Lm Lo Mn Mc Me Nd Nl No (K-36 madde 2 ve 4).
SOZCUK_KATEGORILERI: Final = frozenset(
    {"Lu", "Ll", "Lt", "Lm", "Lo", "Mn", "Mc", "Me", "Nd", "Nl", "No"}
)
# Harf ya da rakam: Lu Ll Lt Lm Lo Nd Nl No.
HARF_RAKAM_KATEGORILERI: Final = frozenset({"Lu", "Ll", "Lt", "Lm", "Lo", "Nd", "Nl", "No"})

_SIFIR_GENISLIK_BOSLUK: Final = 0x200B
_ESSIZ_VEKIL_BASI: Final = 0xD800
_ESSIZ_VEKIL_SONU: Final = 0xDFFF


class YaziParcalari(NamedTuple):
    """`split_scripts` sonucu: Turkce parca ve Arapca parca."""

    tr: str
    ar: str


def arapca_mi(karakter: str) -> bool:
    """Kod noktasi Arapca bloklardan birinde mi?"""
    kod = ord(karakter)
    return any(bas <= kod <= son for bas, son in ARAPCA_BLOKLARI)


def sozcuk_karakteri_mi(karakter: str) -> bool:
    """Kategorisi sozcuk kategorilerinden biri mi? (U+0027 ayrica ele alinir.)"""
    return unicodedata.category(karakter) in SOZCUK_KATEGORILERI


def harf_ya_da_rakam_var_mi(sozcuk: str) -> bool:
    """Sozcukte en az bir harf ya da rakam (L, N) kod noktasi var mi?"""
    return any(unicodedata.category(karakter) in HARF_RAKAM_KATEGORILERI for karakter in sozcuk)


def sozcuklere_bol(metin: str, *, kesme_dahil: bool) -> list[str]:
    """Sozcuk karakterlerinin en uzun dizilerini dondurur; digerleri ayiricidir.

    `kesme_dahil` ise U+0027 de sozcuk karakteridir (Turkce parca).
    """
    sozcukler: list[str] = []
    parcalar: list[str] = []
    for karakter in metin:
        if sozcuk_karakteri_mi(karakter) or (kesme_dahil and karakter == KESME):
            parcalar.append(karakter)
        elif parcalar:
            sozcukler.append("".join(parcalar))
            parcalar = []
    if parcalar:
        sozcukler.append("".join(parcalar))
    return sozcukler


def on_adim(metin: str) -> str:
    """Essiz vekil ve bicim karakteri adimlari, sonra NFC (K-36 madde 1 a-c)."""
    temiz: list[str] = []
    for karakter in metin:
        kod = ord(karakter)
        if _ESSIZ_VEKIL_BASI <= kod <= _ESSIZ_VEKIL_SONU or kod == _SIFIR_GENISLIK_BOSLUK:
            temiz.append(BOSLUK)
        elif unicodedata.category(karakter) != "Cf":
            temiz.append(karakter)
    return unicodedata.normalize("NFC", "".join(temiz))


def split_scripts(metin: str) -> YaziParcalari:
    """Ortak on adimi uygular ve metni Turkce ve Arapca parcalara boler (K-36 madde 1)."""
    tr: list[str] = []
    ar: list[str] = []
    for karakter in on_adim(metin):
        if arapca_mi(karakter):
            ar.append(karakter)
            tr.append(BOSLUK)
        else:
            tr.append(karakter)
            ar.append(BOSLUK)
    return YaziParcalari("".join(tr), "".join(ar))
