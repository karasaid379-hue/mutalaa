"""`benzer_ayet` sozluksel kanit ve QurSim birlestirmesi (K-51 madde 10 ve 12; Baglanti §6).

Sozluksel: iki ayetin normalize kelime dizileri uzerinde 3 ve 4 gram indeksi (`quran_index`).
Iki ayet arasinda en az bir ORTAK 4-gram sarttir (adaylik); `ortak`, kaynak ayetin ortak
ardisik dizilerle (3-gram pencere birlesimi) kapsanan kelime sayisidir.

```text
kapsama = ortak / len(A)           score = min(1, ortak/7) * (0,5 + 0,5 * kapsama)
```

Simetrik cift (A, B) tek satirdir: `lo < hi` (kuresel ayet sirasi) ve skor iki yonun ve iki
indeksin (Uthmani, imlai) BUYUGUDUR (esitlikte Uthmani, sonra `lo` yonu). Her ayet icin en cok
`en_cok` (10) komsu secilir: cift, iki ucundan en az birinin en iyi `en_cok` komsusu icindeyse
tutulur. QurSim ciftleri bu sinira tabi degildir (`qursim` modulu); kendi indeksimizde de
adaylik sartini saglayan bir QurSim cifti TEK satir olur (`birlestir`).
"""

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal

from mutalaa_pipeline.enrich.baglantilar.kok_lemma import yuvarla
from mutalaa_pipeline.enrich.quran_index import KuranIndeksi

EN_COK_BENZER: Final = 10
ORTAK_DOYUM: Final = 7
QURSIM_SKORU: Final = 0.50  # sabit: Label anlami dogrulanamadi (K-51 madde 12)
INDEKS_SIRASI: Final = ("uthmani", "imlai")  # esitlikte ilk sirada olan kazanir

Yon = Literal["src", "dst"]  # kapsama sayilan ayet: `lo` (src) ya da `hi` (dst)


@dataclass(frozen=True)
class SozlukselCift:
    lo: int  # kuresel ayet sirasi, lo < hi
    hi: int
    skor: float
    ortak: int  # kapsayan ayette ortak dizilerle kapsanan kelime sayisi
    ayet_kelime: int  # kapsayan ayetin kelime sayisi (o indekste)
    kapsama: float
    indeks: str
    kapsayan: Yon


def skor_hesapla(ortak: int, ayet_kelime: int) -> float:
    """`min(1, ortak/7) * (0,5 + 0,5 * ortak/ayet_kelime)`; yuvarlanmamis."""
    if ayet_kelime <= 0 or not 0 <= ortak <= ayet_kelime:
        raise ValueError("ortak 0..ayet_kelime araliginda, ayet_kelime pozitif olmali")
    return min(1.0, ortak / ORTAK_DOYUM) * (0.5 + 0.5 * ortak / ayet_kelime)


def _daha_iyi(yeni: tuple[float, int, int], eski: tuple[float, int, int]) -> bool:
    """(skor, -indeks sirasi, -yon sirasi) karsilastirmasi."""
    return yeni > eski


def adaylari_bul(indeksler: Mapping[str, KuranIndeksi]) -> dict[tuple[int, int], SozlukselCift]:
    """Tum sozluksel adaylar: `(lo, hi)` -> en iyi yon ve indeks (sinir uygulanmaz)."""
    sirali = [(ad, indeksler[ad]) for ad in INDEKS_SIRASI if ad in indeksler]
    if not sirali:
        raise ValueError("en az bir indeks gerekir")
    adaylar: dict[tuple[int, int], tuple[tuple[float, int, int], SozlukselCift]] = {}
    for sira_no, (ad, ix) in enumerate(sirali):
        for a in range(ix.ayet_sayisi):
            uzunluk = ix.ayet_uzunlugu(a)
            for b, ortak in ix.komsular(a).items():
                lo, hi = (a, b) if a < b else (b, a)
                yon: Yon = "src" if a == lo else "dst"
                skor = yuvarla(skor_hesapla(ortak, uzunluk))
                anahtar = (skor, -sira_no, 0 if yon == "dst" else 1)
                cift = SozlukselCift(
                    lo, hi, skor, ortak, uzunluk, round(ortak / uzunluk, 6), ad, yon
                )
                eski = adaylar.get((lo, hi))
                if eski is None or _daha_iyi(anahtar, eski[0]):
                    adaylar[(lo, hi)] = (anahtar, cift)
    return {anahtar: cift for anahtar, (_, cift) in adaylar.items()}


def sinirla(
    adaylar: Mapping[tuple[int, int], SozlukselCift], en_cok: int = EN_COK_BENZER
) -> set[tuple[int, int]]:
    """Her ayetin en iyi `en_cok` komsusunu secer; secilen ciftlerin birlesimi."""
    uclar: dict[int, list[tuple[float, int, tuple[int, int]]]] = defaultdict(list)
    for (lo, hi), c in adaylar.items():
        uclar[lo].append((-c.skor, hi, (lo, hi)))
        uclar[hi].append((-c.skor, lo, (lo, hi)))
    secilen: set[tuple[int, int]] = set()
    for liste in uclar.values():
        liste.sort()
        secilen.update(cift for _, _, cift in liste[:en_cok])
    return secilen


@dataclass(frozen=True)
class BenzerSatir:
    """Bir `benzer_ayet` satiri (lo < hi); `sozluksel` None ise saf QurSim satiri."""

    lo: int
    hi: int
    sozluksel: SozlukselCift | None
    qursim_label: int | None

    @property
    def altyapi(self) -> str:
        return "sozluksel" if self.sozluksel is not None else "alim"

    @property
    def skor(self) -> float:
        return self.sozluksel.skor if self.sozluksel is not None else QURSIM_SKORU


def birlestir(
    adaylar: Mapping[tuple[int, int], SozlukselCift],
    secilen: set[tuple[int, int]],
    qursim: Mapping[tuple[int, int], int],
) -> list[BenzerSatir]:
    """Sozluksel (sinirli) ve QurSim ciftlerini tek satira indirger; `(lo, hi)` sirasinda.

    QurSim cifti kendi indeksimizde aday ise (sinirdan bagimsiz) sozluksel skorla ve
    `qursim_label` ile tek satir olur; degilse saf QurSim satiridir (skor sabit 0,50).
    """
    satirlar: dict[tuple[int, int], BenzerSatir] = {}
    for cift in sorted(secilen):
        satirlar[cift] = BenzerSatir(cift[0], cift[1], adaylar[cift], None)
    for cift, label in sorted(qursim.items()):
        kendi = adaylar.get(cift)
        satirlar[cift] = BenzerSatir(cift[0], cift[1], kendi, label)
    return [satirlar[k] for k in sorted(satirlar)]
