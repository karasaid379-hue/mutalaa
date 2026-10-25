"""Metin butunlugu yardimcilari: content_hash, ilk kayit kanonik hale getirme, snap_span.

Kaynaktan alinan metne (Tanzil vb.) `kanonik_metin` UYGULANMAZ; yalniz kendi urettigimiz
metne, ilk kayitta bir kez uygulanir (K-26, K-35 madde 7). Ofsetler Unicode kod noktasidir;
Python `str` zaten kod noktasiyla indeksler.
"""

import hashlib
import re
import unicodedata
from typing import Final

# K-35 madde 7 adim 1: U+FEFF, U+00AD, U+200E, U+200F, U+202A-U+202E, U+2066-U+2069, U+061C.
# U+200C ve U+200D korunur.
_SILINECEK: Final = frozenset(
    chr(kod)
    for kod in (
        0xFEFF,
        0x00AD,
        0x200E,
        0x200F,
        0x061C,
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
    )
)
_BOSLUK_DIZISI: Final = re.compile("[ \t]+")
_KIRPILACAK: Final = " \t\n"  # U+0020, U+0009, U+000A; U+00A0 korunur


def content_hash(text: str) -> str:
    """`sha256(utf-8).hexdigest()`; tek basina vekil `UnicodeEncodeError` verir."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def kanonik_metin(text: str) -> str:
    """Kendi urettigimiz metin icin ilk kayit kanonik hale getirme (K-35 madde 7).

    Sira: silinecek karakterler, NFC, satir sonu (CRLF ve CR -> LF), bosluk dizileri tek
    bosluk, bastan ve sondan yalniz U+0020, U+0009, U+000A kirpilir. `str.strip()`
    kullanilmaz: U+00A0'i da keser.
    """
    text.encode("utf-8")  # tek basina vekilde UnicodeEncodeError (sonuc atilir; C# ile ayni hata)
    silinmis = "".join(harf for harf in text if harf not in _SILINECEK)
    nfc = unicodedata.normalize("NFC", silinmis)
    satir = nfc.replace("\r\n", "\n").replace("\r", "\n")
    # Varsayilan strip() U+00A0'i da keser; bu yuzden acik karakter kumesi kullanilir.
    return _BOSLUK_DIZISI.sub(" ", satir).strip(_KIRPILACAK)


def _mn(harf: str) -> bool:
    return unicodedata.category(harf) == "Mn"


def snap_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Araligi birlesen isaret (Mn) sinirlarina hizalar (Capa semasi bolum 8).

    Baslangic Mn uzerine dusuyorsa geriye, bitis Mn oncesine dusuyorsa ileriye kayar.
    `0 <= start <= end <= len(text)` degilse `ValueError`.
    """
    if not 0 <= start <= end <= len(text):
        raise ValueError("gecersiz aralik")
    while 0 < start < len(text) and _mn(text[start]):
        start -= 1
    while end < len(text) and _mn(text[end]):
        end += 1
    return start, end
