"""Medine 604 sayfa <-> capa sorgulari (A11.5): saf islevler, tablo ARGUMANDIR.

Sayfa tablosu bu modulde uretilmis bir kopya olarak tutulmaz; `page_map` satirlarindan
(`page`, `start_anchor`, `end_anchor`) kurulur. Kaynak Tanzil `pages` grubudur (QPC1 duzeni yalniz
dogrulayicidir); tablonun nasil uretildigi `adimlar/anchor_ust_veri.py`dedir.

Bir sayfa iki kelime capasi arasidir: `start_anchor` ve `end_anchor` `q:{sure}:{ayet}:{kelime}`
(her ikisi de DAHIL). Tablo kurulurken sayfa numaralari 1'den kesintisiz, baslangiclar okuma
sirasinda artan, her sayfa kendi icinde sirali ve sayfalar birbiriyle ortusmeyen olmalidir; aksi
halde `SayfaHatasi`. Gecerli sayfa araligi `1..len(tablo)`'dir: 0 ve 605 hatadir.

`sayfa_bul`: kelime capasi kendi sayfasini verir; ayet capasi ayetin ILK kelimesinin sayfasini
verir (bir ayet iki sayfaya yayilabilir). Kelime araligi, ayet araligi ve baska turler hatadir.
"""

from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.anchor.capa import AnchorError, Q, format, parse

__all__ = ["SayfaHatasi", "SayfaTablosu", "sayfa_araligi", "sayfa_bul"]

Konum = tuple[int, int, int]  # (sure, ayet, kelime)
ILK_KELIME: Final = 1


class SayfaHatasi(ValueError):
    """Sayfa tablosu bicimi, sayfa numarasi ya da capa sorgusu gecersiz."""


def _kelime_konumu(capa: str, yer: str) -> Konum:
    try:
        ref = parse(capa)
        kanonik = format(ref) == capa
    except AnchorError:
        raise SayfaHatasi(f"{yer}: capa gecersiz") from None
    kok = ref.anchor
    if not kanonik or ref.span is not None or not isinstance(kok, Q):
        raise SayfaHatasi(f"{yer}: kanonik bir q: capasi degil")
    if kok.ilk is None or kok.son is not None:
        raise SayfaHatasi(f"{yer}: tekil kelime capasi (q:s:a:k) degil")
    return (kok.sure, kok.ayet, kok.ilk)


@dataclass(frozen=True)
class SayfaTablosu:
    """Dogrulanmis sayfa tablosu; `sayfa_araligi` ve `sayfa_bul` bunu kullanir."""

    baslangiclar: tuple[Konum, ...]
    bitisler: tuple[Konum, ...]

    @classmethod
    def kur(cls, satirlar: Iterable[tuple[int, str, str]]) -> "SayfaTablosu":
        """`(sayfa, start_anchor, end_anchor)` satirlarindan tablo kurar (sirasi onemsiz)."""
        sirali = sorted(satirlar, key=lambda s: s[0])
        if not sirali:
            raise SayfaHatasi("sayfa tablosu bos")
        baslangiclar: list[Konum] = []
        bitisler: list[Konum] = []
        for beklenen, (sayfa, ilk, son) in enumerate(sirali, start=1):
            if sayfa != beklenen:
                raise SayfaHatasi(f"sayfa {sayfa}: numaralar 1'den kesintisiz degil")
            bas = _kelime_konumu(ilk, f"sayfa {sayfa} start_anchor")
            bit = _kelime_konumu(son, f"sayfa {sayfa} end_anchor")
            if bit < bas:
                raise SayfaHatasi(f"sayfa {sayfa}: end_anchor start_anchor'dan once")
            if bitisler and bas <= bitisler[-1]:
                raise SayfaHatasi(f"sayfa {sayfa}: onceki sayfayla ortusuyor ya da sirasiz")
            baslangiclar.append(bas)
            bitisler.append(bit)
        return cls(tuple(baslangiclar), tuple(bitisler))

    def __len__(self) -> int:
        return len(self.baslangiclar)


def _capa(konum: Konum) -> str:
    sure, ayet, kelime = konum
    return format(parse(f"q:{sure}:{ayet}:{kelime}"))


def sayfa_araligi(tablo: SayfaTablosu, sayfa: int) -> tuple[str, str]:
    """Sayfanin `(start_anchor, end_anchor)` kelime capalari; sayfa `1..len(tablo)` disinda hata."""
    if type(sayfa) is not int or not 1 <= sayfa <= len(tablo):
        raise SayfaHatasi(f"sayfa 1..{len(tablo)} araliginda olmali")
    return _capa(tablo.baslangiclar[sayfa - 1]), _capa(tablo.bitisler[sayfa - 1])


def sayfa_bul(tablo: SayfaTablosu, capa: str) -> int:
    """Ayet (`q:s:a`, ilk kelimesi) ya da kelime (`q:s:a:k`) capasinin sayfasi.

    Capa hicbir sayfanin araligina dusmuyorsa (tablo eksik ya da kelime numarasi asiyor) hata.
    """
    try:
        ref = parse(capa)
    except AnchorError:
        raise SayfaHatasi("capa gecersiz") from None
    kok = ref.anchor
    if ref.span is not None or not isinstance(kok, Q) or kok.son is not None:
        raise SayfaHatasi("capa bir ayet ya da tekil kelime capasi (q:) olmali")
    konum: Konum = (kok.sure, kok.ayet, kok.ilk if kok.ilk is not None else ILK_KELIME)
    sira = bisect_right(tablo.baslangiclar, konum) - 1
    if sira < 0 or konum > tablo.bitisler[sira]:
        raise SayfaHatasi("capa sayfa tablosunda yok")
    return sira + 1
