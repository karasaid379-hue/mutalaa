"""Tohum bulma (Iktibas tespiti §5) ve kelime duzeyinde Smith-Waterman hizalama (§6): saf islevler.

Tohum: dizinin 3 ve 4 kelimelik pencereleri indekste aranir; her isabet bir kose (`d` = kuresel
konum - dizideki konum) verir. 4-gramda tek isabet, 3-gramda ayni koseden en az iki isabet
tohumdur. Hizalama penceresi tohumun +-5 kelime genisletilmisidir.

Hizalama (kelime duzeyi; biopython denendi: `PairwiseAligner` kelime listelerini yalniz
esitlikle karsilastirir, bulanik eslesmeyi (`fuzz.ratio >= 80`) ancak her pencere icin V x V
benzerlik matrisi kurup kelimeleri tek karaktere eslemekle tasir; bu da kendi uygulamamizla ayni
O(m n) bulanik sayim maliyetidir ve C uzantisi bagimliligi getirirdi: kendi uygulama yazildi):
tam esleme +2, bulanik (`fuzz.ratio >= 80`) +1, uyusmazlik -2, bosluk -2. Geri izleme kosegen >
yukari > sol onceliklidir (belirleyici). Cikti: hizalanan `(i, j, tur)` ciftleri (`tur`: `tam`,
`bulanik`, `hatali`), baslangic/bitis ve duzenleme sayisi (`bulanik` + `hatali` + bosluk).
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from rapidfuzz import fuzz

from mutalaa_pipeline.enrich.quran_index import KuranIndeksi

ESLES: Final = 2
BULANIK: Final = 1
HATA: Final = -2
BOSLUK: Final = -2
BENZERLIK: Final = 80
PENCERE: Final = 5
EN_COK_KONUM: Final = 200  # bir n-gramin bu kadar konumdan fazlasi kalip sayilir, tohum olmaz
EN_COK_KOSE: Final = 400
TAM: Final = "tam"
BULANIK_TUR: Final = "bulanik"
HATALI: Final = "hatali"


@dataclass(frozen=True)
class Tohum:
    kose: int  # kuresel konum - dizideki konum
    ilk: int  # dizide ilk tohum isabeti
    son: int  # dizide son tohum isabetinin bitisi (yari acik)
    isabet: int


@dataclass
class TohumSonucu:
    tohumlar: list[Tohum] = field(default_factory=list)
    cok_sik_atlanan: int = 0
    kose_siniri_asan: int = 0


@dataclass(frozen=True)
class Hiza:
    ciftler: tuple[tuple[int, int, str], ...]  # (dizi konumu, kuresel konum, tur)
    skor: int
    duzenleme: int

    @property
    def dizi_araligi(self) -> tuple[int, int]:
        return self.ciftler[0][0], self.ciftler[-1][0] + 1

    @property
    def kuresel_aralik(self) -> tuple[int, int]:
        return self.ciftler[0][1], self.ciftler[-1][1] + 1


def tohumlari_bul(anahtarlar: Sequence[str], indeks: KuranIndeksi) -> TohumSonucu:
    """§5 `seeds`: koseye gore tohumlar (isabet azalan, kose artan siralidir)."""
    sonuc = TohumSonucu()
    birlesik: dict[int, tuple[int, int, set[int]]] = {}
    for n in (4, 3):
        kose_isabetleri: dict[int, set[int]] = defaultdict(set)
        for i in range(len(anahtarlar) - n + 1):
            konumlar = indeks.konumlar(anahtarlar[i : i + n])
            if len(konumlar) > EN_COK_KONUM:
                sonuc.cok_sik_atlanan += 1
                continue
            for g in konumlar:
                kose_isabetleri[g - i].add(i)
        for kose, isabetler in kose_isabetleri.items():
            if n == 3 and len(isabetler) < 2:
                continue
            ilk, son = min(isabetler), max(isabetler) + n
            onceki = birlesik.get(kose)
            if onceki is None:
                birlesik[kose] = (ilk, son, set(isabetler))
            else:
                birlesik[kose] = (min(onceki[0], ilk), max(onceki[1], son), onceki[2] | isabetler)
    sirali = sorted(birlesik.items(), key=lambda kv: (-len(kv[1][2]), kv[0]))
    if len(sirali) > EN_COK_KOSE:
        sonuc.kose_siniri_asan = len(sirali) - EN_COK_KOSE
        sirali = sirali[:EN_COK_KOSE]
    sonuc.tohumlar = [Tohum(k, v[0], v[1], len(v[2])) for k, v in sirali]
    return sonuc


def _puan(a: str, b: str, onbellek: dict[tuple[str, str], int]) -> int:
    if a == b:
        return ESLES
    anahtar = (a, b) if a < b else (b, a)
    deger = onbellek.get(anahtar)
    if deger is None:
        deger = BULANIK if fuzz.ratio(a, b) >= BENZERLIK else HATA
        onbellek[anahtar] = deger
    return deger


def smith_waterman(
    a: Sequence[str],
    b: Sequence[str],
    *,
    onbellek: dict[tuple[str, str], int] | None = None,
) -> Hiza | None:
    """Yerel hizalama; hizalanan cift yoksa None.

    Hiza konumlari `a` ve `b` icindeki indekslerdir (pencere kaydirmasini cagiran ekler).
    """
    onbellek = onbellek if onbellek is not None else {}
    m, n = len(a), len(b)
    h = [[0] * (n + 1) for _ in range(m + 1)]
    en_iyi = (0, 0, 0)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            p = _puan(a[i - 1], b[j - 1], onbellek)
            deger = max(0, h[i - 1][j - 1] + p, h[i - 1][j] + BOSLUK, h[i][j - 1] + BOSLUK)
            h[i][j] = deger
            if deger > en_iyi[0]:
                en_iyi = (deger, i, j)
    if en_iyi[0] == 0:
        return None
    skor, i, j = en_iyi
    ciftler: list[tuple[int, int, str]] = []
    duzenleme = 0
    while i > 0 and j > 0 and h[i][j] > 0:
        p = _puan(a[i - 1], b[j - 1], onbellek)
        if h[i][j] == h[i - 1][j - 1] + p:
            tur = TAM if p == ESLES else BULANIK_TUR if p == BULANIK else HATALI
            ciftler.append((i - 1, j - 1, tur))
            if tur != TAM:
                duzenleme += 1
            i, j = i - 1, j - 1
        elif h[i][j] == h[i - 1][j] + BOSLUK:
            duzenleme += 1
            i -= 1
        else:
            duzenleme += 1
            j -= 1
    ciftler.reverse()
    if not ciftler:
        return None
    return Hiza(tuple(ciftler), skor, duzenleme)


def hizala(
    anahtarlar: Sequence[str],
    indeks: KuranIndeksi,
    tohum: Tohum,
    *,
    onbellek: dict[tuple[str, str], int] | None = None,
) -> Hiza | None:
    """Tohum penceresinde (+-5 kelime) Smith-Waterman; konumlar dizi ve kuresel indekstir."""
    a0 = max(0, tohum.ilk - PENCERE)
    a1 = min(len(anahtarlar), tohum.son + PENCERE)
    b0 = max(0, tohum.kose + a0)
    b1 = min(len(indeks.kelimeler), tohum.kose + a1)
    if b0 >= b1 or a0 >= a1:
        return None
    hiza = smith_waterman(anahtarlar[a0:a1], indeks.kelimeler[b0:b1], onbellek=onbellek)
    if hiza is None:
        return None
    return Hiza(tuple((i + a0, j + b0, t) for i, j, t in hiza.ciftler), hiza.skor, hiza.duzenleme)
