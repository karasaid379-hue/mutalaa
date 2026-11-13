"""Arapca dizi cikarimi, `ar_norm` kelimeleri ve baglam penceresi (A20.7a; Iktibas tespiti §3-§4).

Arac secimine bagli degildir: hangi arac kazanirsa kazansin dizi cikarimi, normalizasyon ve baglam
katmanlari bizde kalir (K-51 guncellemesi). Girdi bir Risale biriminin metni ve `marks` dizisidir
(`t: "ar"` araliklari, `tur`: `blok` ya da `alinti`; K-51 madde 2). Butun ofsetler birim metninde
Unicode kod noktasidir ve aralik yari aciktir `[bas, son)` (K-26).

Osmanli ve Arapca kitaplarda butun metin Arap harflidir; bu yuzden `ham` dizi cikarimi (Arap harfli
en uzun diziler) yalniz Turkce (Latin) metin icin anlamlidir. Osmanli ve Arapca kitapta girdi
yalnizca `ar` isaretli araliklardir.

Metin buradan disari yalnizca fonksiyon donus degerleriyle cikar; gunluge ya da rapora yazilmaz.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize.arabic import ar_anahtari
from mutalaa_pipeline.normalize.unicode import ARAPCA_BLOKLARI

TUR_BLOK: Final = "blok"
TUR_ALINTI: Final = "alinti"
TUR_HAM: Final = "ham"
ISARET_TURLERI: Final = (TUR_BLOK, TUR_ALINTI)

BAGLAM_YARICAPI: Final = 200  # Iktibas tespiti §2 madde 2 ve §8: +-200 kod noktasi
YALIN_HEMZE: Final = "\N{ARABIC LETTER HAMZA}"

_AR_SINIF: Final = "".join(f"\\u{bas:04x}-\\u{son:04x}" for bas, son in ARAPCA_BLOKLARI)
# Dizi: Arap harfiyle baslar ve biter; arada bosluk, sekme, U+00A0, U+200C ve U+200D olabilir.
_ORTA_BOSLUK: Final = " \t\N{NO-BREAK SPACE}\N{ZERO WIDTH NON-JOINER}\N{ZERO WIDTH JOINER}"
_AR_DIZI: Final = re.compile(rf"[{_AR_SINIF}](?:[{_AR_SINIF}{_ORTA_BOSLUK}]*[{_AR_SINIF}])?")
_SOZCUK: Final = re.compile(r"\S+")


@dataclass(frozen=True, slots=True)
class ArapcaDizi:
    """Birim metninde bir Arapca dizi: `[bas, son)` kod noktasi, `tur`, `metin`."""

    bas: int
    son: int
    tur: str
    metin: str

    @property
    def uzunluk(self) -> int:
        return self.son - self.bas


@dataclass(frozen=True, slots=True)
class Kelime:
    """Bir dizinin normalize kelimesi ve birim metnindeki kaynak aralik `[bas, son)`."""

    norm: str
    bas: int
    son: int


def _isaret_sayisi(deger: object, alan: str) -> int:
    if not isinstance(deger, int) or isinstance(deger, bool):
        raise GirdiHatasi(f"ar isareti: '{alan}' tam sayi degil ya da yok")
    return deger


def isaretlerden(metin: str, marks: Iterable[Mapping[str, object]]) -> list[ArapcaDizi]:
    """`marks` icindeki `t: "ar"` araliklarindan dizileri kurar; `(bas, son)` sirali.

    Bos aralik (`bas == son`) atlanir; gecersiz aralik (`bas < son <= len(metin)` degil) ya da
    bilinmeyen `tur` `GirdiHatasi`
    (cikis 2) verir; iletide yalniz alan adi ve sayi bulunur.
    """
    diziler: list[ArapcaDizi] = []
    for isaret in marks:
        if isaret.get("t") != "ar":
            continue
        bas = _isaret_sayisi(isaret.get("s"), "s")
        son = _isaret_sayisi(isaret.get("e"), "e")
        tur = isaret.get("tur")
        if tur not in ISARET_TURLERI:
            raise GirdiHatasi("ar isareti: 'tur' blok ya da alinti degil")
        if bas == son and 0 <= bas <= len(metin):
            continue  # bos aralik (kaynakta bos alinti cifti): dizi degil, atlanir
        if not 0 <= bas < son <= len(metin):
            raise GirdiHatasi(f"ar isareti: gecersiz aralik [{bas}, {son}) (uzunluk {len(metin)})")
        diziler.append(ArapcaDizi(bas, son, str(tur), metin[bas:son]))
    diziler.sort(key=lambda d: (d.bas, d.son))
    return diziler


def ar_harf_dizileri(metin: str) -> list[ArapcaDizi]:
    """Arap harfli en uzun dizileri toplar (`tur = "ham"`; Iktibas tespiti §3).

    Osmanli ve Arapca kitapta butun metin tek dizi olur; bu islev yalniz Latin yazili metin ve
    isaret kapsami denetimi icindir.
    """
    return [ArapcaDizi(m.start(), m.end(), TUR_HAM, m.group()) for m in _AR_DIZI.finditer(metin)]


def isaret_disi_diziler(metin: str, marks: Iterable[Mapping[str, object]]) -> list[ArapcaDizi]:
    """`ham` dizilerden hicbir `ar` isaretiyle kesismeyenler (isaret kapsami denetimi)."""
    isaretli = isaretlerden(metin, marks)
    return [
        d
        for d in ar_harf_dizileri(metin)
        if not any(d.bas < i.son and i.bas < d.son for i in isaretli)
    ]


def kelimeler(dizi: ArapcaDizi) -> list[Kelime]:
    """Dizinin `ar_norm` kelimeleri, her biri kaynak aralikla (birim metni ofseti).

    Bosluklarla ayrilan her parca `ar_anahtari` ile normalize edilir (hareke, tatvil ve Kur'an
    isaretleri silinir; elif, ye, te ve hemze birlestirilir); bos kalan parca ve tek basina yalin
    hemze atilir (Iktibas tespiti §4). Bir parca birden fazla kelimeye bolunurse kelimeler ayni
    kaynak araligi paylasir.
    """
    sonuc: list[Kelime] = []
    for m in _SOZCUK.finditer(dizi.metin):
        for norm in ar_anahtari(m.group()).split():
            if norm == YALIN_HEMZE:
                continue
            sonuc.append(Kelime(norm, dizi.bas + m.start(), dizi.bas + m.end()))
    return sonuc


def norm_dizi(dizi: ArapcaDizi) -> str:
    """Dizinin eslestirme anahtari: normalize kelimeler tek bosluk ile birlestirilir."""
    return " ".join(k.norm for k in kelimeler(dizi))


def kelime_araligi(kelime_listesi: Sequence[Kelime], ilk: int, son: int) -> tuple[int, int]:
    """Kelime indeksi araligi `[ilk, son)` icin birim metni araligi `[bas, son)`.

    Gecersiz aralikta (`0 <= ilk < son <= len`) `ValueError`.
    """
    if not 0 <= ilk < son <= len(kelime_listesi):
        raise ValueError("kelime araligi gecersiz")
    return kelime_listesi[ilk].bas, kelime_listesi[son - 1].son


def baglam_penceresi(
    metin_uzunlugu: int, bas: int, son: int, yaricap: int = BAGLAM_YARICAPI
) -> tuple[int, int]:
    """`[bas, son)` aralikli dizinin +-`yaricap` kod noktalik baglam penceresi `[bas, son)`."""
    if not 0 <= bas < son <= metin_uzunlugu:
        raise ValueError("aralik gecersiz")
    if yaricap < 0:
        raise ValueError("yaricap negatif olamaz")
    return max(0, bas - yaricap), min(metin_uzunlugu, son + yaricap)


def baglam(metin: str, dizi: ArapcaDizi, yaricap: int = BAGLAM_YARICAPI) -> str:
    """Dizinin baglam penceresinin metni (dizi dahil)."""
    bas, son = baglam_penceresi(len(metin), dizi.bas, dizi.son, yaricap)
    return metin[bas:son]
