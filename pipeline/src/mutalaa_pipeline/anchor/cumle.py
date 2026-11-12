# ruff: noqa: RUF001
"""Kural tabanli cumle ayirici (K-51 madde 8, BC-48).

Bir paragraf metnini cumlelere boler ve her cumle icin Unicode kod noktasi araligi
`[bas, son)` verir (yari acik; Capa semasi bolum 8). Aralik cumlenin ilk bosluk olmayan
karakterinden son noktalama ve kapanis isaretine kadardir; cumleler arasindaki bosluk hicbir
cumleye girmez. Metin degistirilmez; yalniz konum hesaplanir.

Kurallar (surum `CUMLE_SURUMU`):
  * Bitis isaretleri: `.`, `?`, `!`, U+2026 (uc nokta) ve U+061F (Arapca soru isareti); art arda
    gelen isaretler tek kume sayilir; kumeyi izleyen kapanis isaretleri (tirnak, parantez)
    cumleye dahildir.
  * Bitis ancak kumenin (ve kapanislarin) ardindan bosluk ya da metin sonu geliyorsa gecerlidir
    ("3.5" ve "a.b" boluk degildir).
  * Sonraki sozcuk kucuk harfle basliyorsa bolunmez (acilis tirnagi ve tirelere bakilmaz;
    kucuk harf `str.islower` ile, Arap harfleri harf buyuklugu tasimadigi icin bolunur).
  * Tek `.` icin istisnalar: cumlenin ilk sozcugu olan 1-3 haneli sayi (numaralandirma), tek
    harf (bas harf), bilinen kisaltma listesi ve noktali bas harf dizisi (`a.s`, `s.a.v`);
    bunlardan sonra bolunmez.
  * `ar_araliklari` (marks `t: "ar"` araliklari) icindeki bitis isaretleri bolmez.

`str.lower()` kullanilmaz; Turkce harf esleme tablolari acik yazilidir (dosya basindaki noqa:
ruff RUF001 dotless i'yi belirsiz sayar). Gorunmeyen ve belirsiz isaretler kod noktasiyla verilir.
"""

from collections.abc import Mapping, Sequence
from typing import Final

CUMLE_SURUMU: Final = "1.0"


def _harfler(duz: str, *kodlar: int) -> frozenset[str]:
    """`duz` karakterleri ve verilen kod noktalari (gorunmeyen ya da belirsiz karakterler)."""
    return frozenset(duz) | frozenset(map(chr, kodlar))


# Bosluk: U+0020, U+0009, U+000A ve U+00A0 (K-35 madde 7: U+00A0 kenarda da korunur ama bosluktur).
_BOSLUK: Final = _harfler(" \t\n", 0x00A0)
# Bitis isaretleri: . ? ! ve U+2026 (uc nokta), U+061F (Arapca soru isareti).
_BITIS: Final = _harfler(".?!", 0x2026, 0x061F)
# Kapanis (cumleye dahil): " ' ) ] } ve U+00BB, U+2019, U+201D, U+203A (kapanis tirnaklari).
_KAPANIS: Final = _harfler("\"')]}", 0x00BB, 0x2019, 0x201D, 0x203A)
# Sonraki sozcuge bakarken atlanan acilislar ve tireler: " ' ( [ { - ve U+00AB, U+2018, U+201C,
# U+2039 (acilis tirnaklari), U+2013, U+2014 (tireler).
_ACILIS: Final = _harfler("\"'([{-", 0x00AB, 0x2018, 0x201C, 0x2039, 0x2013, 0x2014)

# Kisaltmalar (nokta oncesi sozcuk, Turkce kucuk harfe indirilmis, ASCII).
KISALTMALAR: Final = frozenset(
    (
        "hz",
        "dr",
        "prof",
        "doc",
        "yrd",
        "sn",
        "bkz",
        "krs",
        "vs",
        "vb",
        "vd",
        "orn",
        "no",
        "bk",
        "yy",
        "ibid",
        "bs",
    )
)

# Acik Turkce kucuk harf esleme (buyuk -> kucuk); `str.lower()` yerine.
_KUCUK: Final[dict[int, str]] = {
    **{ord(chr(k)): chr(k + 32) for k in range(ord("A"), ord("Z") + 1)},
    ord("İ"): "i",  # dotted capital I
    ord("I"): "ı",  # ASCII I -> dotless i (Turkish)
    ord("Ç"): "ç",
    ord("Ğ"): "ğ",
    ord("Ö"): "ö",
    ord("Ş"): "ş",
    ord("Ü"): "ü",
    ord("Â"): "â",
    ord("Î"): "î",
    ord("Û"): "û",
}
# Kisaltma karsilastirmasi icin ASCII'ye katlama (kucuk Turkce harf -> ASCII).
_ASCII: Final[dict[int, str]] = {
    ord("ı"): "i",
    ord("ç"): "c",
    ord("ğ"): "g",
    ord("ö"): "o",
    ord("ş"): "s",
    ord("ü"): "u",
    ord("â"): "a",
    ord("î"): "i",
    ord("û"): "u",
}
_RAKAM: Final = _harfler("0123456789", *range(0x0660, 0x066A))  # ASCII ve Arap-Hint rakamlari


def _kisaltma_anahtari(sozcuk: str) -> str:
    """Acik esleme ile kucuk harf ve ASCII'ye katlanmis sozcuk (karsilastirma icin)."""
    return sozcuk.translate(_KUCUK).translate(_ASCII)


def _harf_mi(ch: str) -> bool:
    return ch.isalpha()


def _noktali_bas_harfler(sozcuk: str) -> bool:
    """`a.s`, `r.a`, `s.a.v` gibi: nokta ile ayrilmis 1-2 harflik en az iki parca."""
    parcalar = sozcuk.split(".")
    return len(parcalar) >= 2 and all(
        1 <= len(p) <= 2 and all(_harf_mi(c) for c in p) for p in parcalar
    )


def _nokta_sonrasi_bolunmez(sozcuk: str, cumle_basinda: bool) -> bool:
    """Tek noktadan sonra cumle bitmez mi? (numaralandirma, bas harf, kisaltma).

    `cumle_basinda`: sozcuk cumlenin ilk sozcugu mu (madde numarasi yalniz orada sayilir;
    "Deneme 1." gibi sayiyla biten cumle bolunur).
    """
    if sozcuk == "":
        return False
    if all(c in _RAKAM for c in sozcuk):
        return cumle_basinda and len(sozcuk) <= 3  # 1-3 hane: madde numarasi; yil bolebilir
    if len(sozcuk) == 1 and _harf_mi(sozcuk):
        return True
    if all(_harf_mi(c) for c in sozcuk):
        return _kisaltma_anahtari(sozcuk) in KISALTMALAR
    return _noktali_bas_harfler(sozcuk)


def _arapca_icinde(i: int, araliklar: Sequence[tuple[int, int]]) -> bool:
    return any(bas <= i < son for bas, son in araliklar)


def _gecerli_arapca(metin: str, araliklar: Sequence[tuple[int, int]]) -> None:
    onceki = 0
    for bas, son in araliklar:
        if not 0 <= bas < son <= len(metin):
            raise ValueError("gecersiz Arapca araligi")
        if bas < onceki:
            raise ValueError("Arapca araliklari artan ve ayrik olmali")
        onceki = son


def arapca_araliklari(marks: Sequence[Mapping[str, object]]) -> list[tuple[int, int]]:
    """`marks` listesinden `t == "ar"` araliklarini `(s, e)` olarak, baslangica gore siralar."""
    sonuc: list[tuple[int, int]] = []
    for isaret in marks:
        if isaret.get("t") != "ar":
            continue
        bas, son = isaret.get("s"), isaret.get("e")
        if not isinstance(bas, int) or not isinstance(son, int):
            raise ValueError("ar isareti s ve e tam sayilari tasimali")
        sonuc.append((bas, son))
    return sorted(sonuc)


def _sonraki_sozcuk_kucuk_mu(metin: str, konum: int) -> bool:
    """`konum`dan itibaren bosluk ve acilislar atlanir; ilk karakter kucuk harf mi?"""
    n = len(metin)
    while konum < n and (metin[konum] in _BOSLUK or metin[konum] in _ACILIS):
        konum += 1
    return konum < n and metin[konum].islower()


def _onceki_sozcuk(metin: str, alt: int, bitis_isareti: int) -> tuple[str, bool]:
    """Bitis isaretinden onceki sozcuk (`alt` ile bosluk arasi), bastaki acilislar atilmis.

    Ikinci deger: sozcuk cumlenin ilk sozcugu mu (`alt` konumunda mi basliyor).
    """
    bas = bitis_isareti
    while bas > alt and metin[bas - 1] not in _BOSLUK:
        bas -= 1
    cumle_basinda = bas == alt
    while bas < bitis_isareti and metin[bas] in _ACILIS:
        bas += 1
    return metin[bas:bitis_isareti], cumle_basinda


def cumleleri_ayir(
    metin: str, ar_araliklari: Sequence[tuple[int, int]] = ()
) -> list[tuple[int, int]]:
    """Cumle araliklari `[(bas, son), ...]` (kod noktasi, yari acik, artan, ayrik).

    `ar_araliklari`: marks `t: "ar"` araliklari `(s, e)`; icinde cumle bolunmez. Bos ya da yalniz
    bosluktan olusan metinde sonuc bostur. Metin hic degistirilmez.
    """
    araliklar = sorted(ar_araliklari)
    _gecerli_arapca(metin, araliklar)
    n = len(metin)
    sonuc: list[tuple[int, int]] = []
    bas: int | None = None
    i = 0
    while i < n:
        ch = metin[i]
        if bas is None:
            if ch in _BOSLUK:
                i += 1
                continue
            bas = i
        if ch not in _BITIS or _arapca_icinde(i, araliklar):
            i += 1
            continue
        kume_sonu = i
        while (
            kume_sonu < n
            and metin[kume_sonu] in _BITIS
            and not _arapca_icinde(kume_sonu, araliklar)
        ):
            kume_sonu += 1
        son = kume_sonu
        while son < n and metin[son] in _KAPANIS and not _arapca_icinde(son, araliklar):
            son += 1
        kume = metin[i:kume_sonu]
        if _bolunur(metin, bas, i, kume, son):
            sonuc.append((bas, son))
            bas = None
            i = son
        else:
            i = kume_sonu
    if bas is not None:
        son = n
        while son > bas and metin[son - 1] in _BOSLUK:
            son -= 1
        sonuc.append((bas, son))
    return sonuc


def _bolunur(metin: str, alt: int, kume_basi: int, kume: str, son: int) -> bool:
    """Bitis kumesinden (ve kapanislarindan) sonra cumle biter mi?"""
    if son >= len(metin):
        return True
    if metin[son] not in _BOSLUK:
        return False
    if _sonraki_sozcuk_kucuk_mu(metin, son):
        return False
    if kume != ".":
        return True
    sozcuk, cumle_basinda = _onceki_sozcuk(metin, alt, kume_basi)
    return not _nokta_sonrasi_bolunmez(sozcuk, cumle_basinda)
