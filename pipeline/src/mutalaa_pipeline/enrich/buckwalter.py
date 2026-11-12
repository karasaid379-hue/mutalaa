"""Genisletilmis Buckwalter -> Arapca eslemesi (A17.1, K-50): tek yaprak modul.

QAC morfoloji dosyasinin FORM, LEM ve ROOT degerleri "extended Buckwalter" ASCII dizgisidir
(`corpus.quran.com/documentation/morphologicalfeatures.jsp`). Esleme tablosu ELLE YAZILMAZ ve
Arapca harf hafizadan eklenmez: `TABLO`, kaydedilmis QAC sayfasindan (`data/gelen/qac-belge/
2026-11-12/buckwalter.html`, Java API - Buckwalter Transliteration, Fig 1) uretilmistir. Sayfadaki
Decimal ve Hex sutunlari Arapca kod noktasini, ASCII sutunu Buckwalter karakterini verir; Glyph
(gorsel) sutunu kullanilmaz. Uretim betigi `.tmp/a17/bw-tablo-uret.py`'dir (`python -I`); sayfanin
tablo parcasi `tests/fixtures/qac/buckwalter-tablo.html` olarak depodadir ve CI testi
`tablo_ayristir` ile bu parcadan tabloyu yeniden turetip `TABLO` ile karsilastirir.

Kural: yalniz tablodaki karakterler cevrilir; tabloda olmayan karakter `BuckwalterHatasi` verir
(sessiz atlama ya da tahmin yok). Iletide yalniz konum ve kod noktasi yer alir.

Bu modul yapraktir: `mutalaa_pipeline` altindan hicbir sey ice aktarmaz (`tests/
test_qac_buckwalter.py` sinar). NFC bu modulde UYGULANMAZ: cevrilen metin QAC'den turetilen,
kendi urettigimiz metindir ve ilk kayitta `mutalaa_pipeline.anchor.metin.kanonik_metin` ile bir
kez kanonik hale getirilir (K-26).
"""

import html
import re
from typing import Final

SAYFA_TABLOSU: Final = "u1"  # Fig 1 tablosunun CSS sinifi (sayfada tek)

# ASCII (Buckwalter) -> Arapca; kod noktasina gore sirali; yorum sayfadaki Orthography adidir.
TABLO: Final[dict[str, str]] = {
    "'": "\u0621",  # Hamza
    ">": "\u0623",  # Alif + HamzaAbove
    "&": "\u0624",  # Waw + HamzaAbove
    "<": "\u0625",  # Alif + HamzaBelow
    "}": "\u0626",  # Ya + HamzaAbove
    "A": "\u0627",  # Alif
    "b": "\u0628",  # Ba
    "p": "\u0629",  # TaMarbuta
    "t": "\u062a",  # Ta
    "v": "\u062b",  # Tha
    "j": "\u062c",  # Jeem
    "H": "\u062d",  # HHa
    "x": "\u062e",  # Kha
    "d": "\u062f",  # Dal
    "*": "\u0630",  # Thal
    "r": "\u0631",  # Ra
    "z": "\u0632",  # Zain
    "s": "\u0633",  # Seen
    "$": "\u0634",  # Sheen
    "S": "\u0635",  # Sad
    "D": "\u0636",  # DDad
    "T": "\u0637",  # TTa
    "Z": "\u0638",  # DTha
    "E": "\u0639",  # Ain
    "g": "\u063a",  # Ghain
    "_": "\u0640",  # Tatweel
    "f": "\u0641",  # Fa
    "q": "\u0642",  # Qaf
    "k": "\u0643",  # Kaf
    "l": "\u0644",  # Lam
    "m": "\u0645",  # Meem
    "n": "\u0646",  # Noon
    "h": "\u0647",  # Ha
    "w": "\u0648",  # Waw
    "Y": "\u0649",  # AlifMaksura
    "y": "\u064a",  # Ya
    "F": "\u064b",  # Fathatan
    "N": "\u064c",  # Dammatan
    "K": "\u064d",  # Kasratan
    "a": "\u064e",  # Fatha
    "u": "\u064f",  # Damma
    "i": "\u0650",  # Kasra
    "~": "\u0651",  # Shadda
    "o": "\u0652",  # Sukun
    "^": "\u0653",  # Maddah
    "#": "\u0654",  # HamzaAbove
    "`": "\u0670",  # AlifKhanjareeya
    "{": "\u0671",  # Alif + HamzatWasl
    ":": "\u06dc",  # SmallHighSeen
    "@": "\u06df",  # SmallHighRoundedZero
    '"': "\u06e0",  # SmallHighUprightRectangularZero
    "[": "\u06e2",  # SmallHighMeemIsolatedForm
    ";": "\u06e3",  # SmallLowSeen
    ",": "\u06e5",  # SmallWaw
    ".": "\u06e6",  # SmallYa
    "!": "\u06e8",  # SmallHighNoon
    "-": "\u06ea",  # EmptyCentreLowStop
    "+": "\u06eb",  # EmptyCentreHighStop
    "%": "\u06ec",  # RoundedHighStopWithFilledCentre
    "]": "\u06ed",  # SmallLowMeem
}

_SATIR: Final = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
_HUCRE: Final = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_ONLUK: Final = re.compile(r"[0-9]+")
_ONALTILIK: Final = re.compile(r"U\+([0-9A-F]{4})")


class BuckwalterHatasi(ValueError):
    """Esleme tablosunda olmayan karakter ya da bozuk sayfa; iletide metin yoktur."""


def tablo_ayristir(sayfa: str) -> dict[str, str]:
    """Sayfanin Fig 1 tablosundan (`<table class="u1">`) ASCII -> Arapca esleme tablosu.

    Her veri satiri bes hucreli olmalidir (Decimal, Hex, Glyph, ASCII, Orthography); Decimal ve
    Hex ayni kod noktasini vermeli, ASCII hucresi (HTML varliklari cozulmus) tek ASCII karakter
    olmalidir; ASCII karakter ve kod noktasi tekil olmalidir. Aksi halde `BuckwalterHatasi`.
    """
    bas = sayfa.find(f'<table class="{SAYFA_TABLOSU}"')
    if bas < 0:
        raise BuckwalterHatasi("sayfada Buckwalter tablosu yok")
    son = sayfa.find("</table>", bas)
    if son < 0:
        raise BuckwalterHatasi("Buckwalter tablosu kapanmiyor")
    sonuc: dict[str, str] = {}
    kod_noktalari: set[int] = set()
    for satir in _SATIR.findall(sayfa[bas:son]):
        hucreler = _HUCRE.findall(satir)
        if len(hucreler) != 5 or _ONLUK.fullmatch(hucreler[0].strip()) is None:
            continue  # baslik satiri
        onluk = int(hucreler[0].strip())
        onaltilik = _ONALTILIK.fullmatch(hucreler[1].strip())
        if onaltilik is None or int(onaltilik.group(1), 16) != onluk:
            raise BuckwalterHatasi(f"Decimal ve Hex sutunlari tutmuyor: {onluk}")
        ascii_ = html.unescape(hucreler[3].strip())
        if len(ascii_) != 1 or not ascii_.isascii():
            raise BuckwalterHatasi(f"ASCII sutunu tek ASCII karakter degil: {onluk}")
        if ascii_ in sonuc or onluk in kod_noktalari:
            raise BuckwalterHatasi(f"yinelenen satir: {onluk}")
        kod_noktalari.add(onluk)
        sonuc[ascii_] = chr(onluk)
    if not sonuc:
        raise BuckwalterHatasi("Buckwalter tablosunda veri satiri yok")
    return dict(sorted(sonuc.items(), key=lambda oge: ord(oge[1])))


def eslenemeyenler(metin: str) -> set[str]:
    """`metin` icinde tabloda olmayan karakterler (kume; bos kume = tamami cevrilebilir)."""
    return {harf for harf in metin if harf not in TABLO}


def bw_arapca(metin: str) -> str:
    """Buckwalter dizgisini Arapca yapar; tabloda olmayan karakterde `BuckwalterHatasi`."""
    cikti: list[str] = []
    for konum, harf in enumerate(metin):
        arapca = TABLO.get(harf)
        if arapca is None:
            raise BuckwalterHatasi(f"tabloda olmayan karakter: konum {konum}, U+{ord(harf):04X}")
        cikti.append(arapca)
    return "".join(cikti)
