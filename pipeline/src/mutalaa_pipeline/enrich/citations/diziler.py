# ruff: noqa: RUF001
"""Turkce ana metindeki Arapca dizilerin cikarilmasi (Iktibas tespiti §3).

Ofsetler kanonik metindeki kod noktasi ofsetidir (Python `str` indeksi) ve aralik yari acik
`[bas, son)`'tir; metin degistirilmez. Arapca bloklardaki en uzun diziler toplanir
(ZWNJ/ZWJ dizi icinde kalir); iki dizi arasindaki bosluk yalniz Latin noktalama ve en cok 3
bosluktan (satir sonu yok) olusuyorsa diziler birlestirilir. Kenardaki harf olmayan karakterler
(sus parantezi, Arapca noktalama) `[bas, son)` araligina dahil edilmez; sus parantezi ayrica
isaretlenir (`suslu`).
"""

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Final

SUS_PARANTEZLERI: Final = "﴾﴿"
ZW: Final = "‌‍"
EN_COK_BOSLUK: Final = 3
ARAPCA_ARALIKLARI: Final = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)
POZISYONLAR: Final = ("baslik", "dipnot", "metin")


@dataclass(frozen=True)
class ArapcaDizi:
    bas: int
    son: int
    metin: str
    position: str  # baslik | dipnot | metin
    suslu: bool  # sus parantezi (U+FD3E, U+FD3F) bu dizide ya da hemen kenarinda


def arapca_mi(harf: str) -> bool:
    kod = ord(harf)
    return any(bas <= kod <= son for bas, son in ARAPCA_ARALIKLARI)


def _parcalar(metin: str) -> Iterator[tuple[int, int]]:
    """Arapca karakter (ve dizi icindeki ZWNJ/ZWJ) kesintisiz parcalari: `(bas, son)`."""
    bas = -1
    son = -1
    for i, h in enumerate(metin):
        if arapca_mi(h) or (h in ZW and bas >= 0):
            if bas < 0:
                bas = i
            son = i + 1
        elif bas >= 0:
            yield bas, son
            bas = -1
    if bas >= 0:
        yield bas, son


def _birlesir(bosluk: str) -> bool:
    """Iki parca arasi yalniz Latin noktalama ve en cok 3 bosluk mu (satir sonu yok)."""
    if bosluk == "":
        return True
    if "\n" in bosluk or "\r" in bosluk:
        return False
    sayac = 0
    for h in bosluk:
        if h.isspace():
            sayac += 1
        elif unicodedata.category(h)[0] != "P" or arapca_mi(h):
            return False
    return sayac <= EN_COK_BOSLUK


def _kirp(metin: str, bas: int, son: int) -> tuple[int, int]:
    """Kenardaki harf olmayan karakterleri (sus parantezi, noktalama) araliktan cikarir."""
    while bas < son and unicodedata.category(metin[bas])[0] != "L":
        bas += 1
    while son > bas and unicodedata.category(metin[son - 1])[0] not in ("L", "M"):
        son -= 1
    return bas, son


def arapca_diziler(metin: str, position: str = "metin") -> list[ArapcaDizi]:
    """Birimin Arapca dizileri (metin sirasinda); harf icermeyen dizi atilir."""
    if position not in POZISYONLAR:
        raise ValueError("position baslik, dipnot ya da metin olmali")
    birlesik: list[tuple[int, int]] = []
    for bas, son in _parcalar(metin):
        if birlesik and _birlesir(metin[birlesik[-1][1] : bas]):
            birlesik[-1] = (birlesik[-1][0], son)
        else:
            birlesik.append((bas, son))
    sonuc: list[ArapcaDizi] = []
    for bas, son in birlesik:
        kb, ks = _kirp(metin, bas, son)
        if kb >= ks:
            continue
        kenar = metin[max(0, bas - 1) : bas] + metin[son : son + 1]
        suslu = any(h in SUS_PARANTEZLERI for h in (*metin[bas:son], *kenar))
        sonuc.append(ArapcaDizi(kb, ks, metin[kb:ks], position, suslu))
    return sonuc
