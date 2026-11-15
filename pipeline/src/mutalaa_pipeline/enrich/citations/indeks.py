"""Iktibas esleme indeksi: `KuranIndeksi` (3-4 gram, ayet siniri asar) + kelime konumu eslemesi.

Iki indeks kurulur (Iktibas tespiti §5): Tanzil Uthmani (`quran_word.norm`; kelime numarasi QAC/QPC1
konumudur) ve Tanzil Simple Clean (imlai). Kelimeler mushaf sirasiyla kuresel konuma sahiptir ve
n-gramlar ayet sinirini asabilir (ardisik ayet alintilari tek kosegende kalir).

Her belirtecin bir QAC kelime numarasi vardir (`dst_span` kelime konumu `[ilk, son + 1)`):

* Uthmani: belirtec, geldigi QAC kelimesinin numarasini tasir (bosluklu `norm` degeri birden cok
  belirtec verir; yalin hemzeden ibaret kelime belirtec vermez).
* Imlai -> Uthmani (`imlai_word_map`): ayetteki belirtec sayilari esitse birebir konum; degilse
  ayet ici hizalama (`difflib.SequenceMatcher`, eslesen belirtec kesin, kalanlar orantili konum ve
  `belirsiz = True`). Hizalanamayan konum `evidence.konum_belirsiz = true` olarak isaretlenir.

Normalize metin yalniz bellektedir; hicbir yere yazilmaz.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from mutalaa_pipeline.enrich.baglantilar.girdi import Kelime
from mutalaa_pipeline.enrich.citations.normalizasyon import anahtarlar
from mutalaa_pipeline.enrich.quran_index import KuranIndeksi


@dataclass
class EslestirmeIndeksi:
    """`ad`: `uthmani` ya da `imlai`; `indeks`: ayet siniri asan 3-4 gram indeksi."""

    ad: str
    indeks: KuranIndeksi
    ayet_belirtec: list[list[str]]
    kelime_no: list[list[int]]  # belirtec -> QAC kelime numarasi (1 tabanli)
    belirsiz: list[list[bool]]  # belirtec -> konum eslemesi belirsiz mi
    ayet_kelime_sayisi: list[int]  # N: QAC kelime sayisi
    _tek_iki: dict[tuple[str, ...], frozenset[int]] = field(default_factory=dict)

    @property
    def ayet_sayisi(self) -> int:
        return len(self.ayet_belirtec)

    def ayet_ve_yerel(self, konum: int) -> tuple[int, int]:
        """Kuresel konum -> `(ayet sirasi, ayet ici belirtec sirasi)`."""
        ayet = self.indeks.ayet_of[konum]
        return ayet, konum - self.indeks.ayet_baslangic[ayet]

    def kelime_araligi(self, ayet: int, ilk: int, son: int) -> tuple[int, int, bool]:
        """Belirtec araligi `[ilk, son]` (dahil) -> `(ilk_kelime, son_kelime + 1, belirsiz)`."""
        nolar = self.kelime_no[ayet][ilk : son + 1]
        belirsiz = any(self.belirsiz[ayet][ilk : son + 1])
        return min(nolar), max(nolar) + 1, belirsiz

    def dizi_ayetleri(self, dizi: Sequence[str]) -> frozenset[int]:
        """Belirtec dizisinin AYNI ayet icinde ardisik gectigi ayetler (`phrase_freq` = sayisi)."""
        n = len(dizi)
        if n == 0:
            return frozenset()
        anahtar = tuple(dizi)
        if n < 3:
            onbellek = self._tek_iki.get(anahtar)
            if onbellek is None:
                tum = self.indeks.kelimeler
                bulunan = {
                    self.indeks.ayet_of[p]
                    for p in range(len(tum) - n + 1)
                    if tuple(tum[p : p + n]) == anahtar
                    and self.indeks.ayet_of[p] == self.indeks.ayet_of[p + n - 1]
                }
                onbellek = frozenset(bulunan)
                self._tek_iki[anahtar] = onbellek
            return onbellek
        kok = anahtar[:4] if n >= 4 else anahtar
        sonuc: set[int] = set()
        for p in self.indeks.konumlar(kok):
            if p + n > len(self.indeks.kelimeler):
                continue
            if tuple(self.indeks.kelimeler[p : p + n]) != anahtar:
                continue
            if self.indeks.ayet_of[p] == self.indeks.ayet_of[p + n - 1]:
                sonuc.add(self.indeks.ayet_of[p])
        return frozenset(sonuc)


def _kur(
    ad: str,
    ayetler: list[list[str]],
    nolar: list[list[int]],
    bel: list[list[bool]],
    sayilar: list[int],
) -> EslestirmeIndeksi:
    return EslestirmeIndeksi(
        ad, KuranIndeksi(ayetler, ayet_siniri_asar=True), ayetler, nolar, bel, sayilar
    )


def uthmani_indeksi(kelimeler: Sequence[Kelime], ayet_sayisi: int) -> EslestirmeIndeksi:
    """`quran_word` satirlarindan (ayet sirasi, kelime numarasi sirali) Uthmani esleme indeksi."""
    ayetler: list[list[str]] = [[] for _ in range(ayet_sayisi)]
    nolar: list[list[int]] = [[] for _ in range(ayet_sayisi)]
    sayilar = [0] * ayet_sayisi
    for k in kelimeler:
        sayilar[k.sira] += 1
        for a in anahtarlar(k.norm):
            ayetler[k.sira].append(a)
            nolar[k.sira].append(k.no)
    bel = [[False] * len(a) for a in ayetler]
    return _kur("uthmani", ayetler, nolar, bel, sayilar)


def imlai_kelime_haritasi(
    imlai: Sequence[str], uthmani: Sequence[str], uthmani_nolari: Sequence[int]
) -> tuple[list[int], list[bool]]:
    """Bir ayetin imlai belirteclerini Uthmani kelime numaralarina esler: `(nolar, belirsiz)`."""
    if not uthmani:
        return [1] * len(imlai), [True] * len(imlai)
    if len(imlai) == len(uthmani):
        return list(uthmani_nolari), [False] * len(imlai)
    nolar = [0] * len(imlai)
    belirsiz = [True] * len(imlai)
    for blok in SequenceMatcher(
        None, list(imlai), list(uthmani), autojunk=False
    ).get_matching_blocks():
        for k in range(blok.size):
            nolar[blok.a + k] = uthmani_nolari[blok.b + k]
            belirsiz[blok.a + k] = False
    son = len(uthmani) - 1
    for k in range(len(nolar)):
        if belirsiz[k]:
            oran = k * son // max(1, len(imlai) - 1) if len(imlai) > 1 else 0
            nolar[k] = uthmani_nolari[min(son, oran)]
    return nolar, belirsiz


def imlai_indeksi(
    imlai_ayetleri: Sequence[Sequence[str]], uthmani: EslestirmeIndeksi
) -> EslestirmeIndeksi:
    """Simple Clean ayet belirteclerinden (ayet basina, besmele kirpilmis) imlai esleme indeksi."""
    if len(imlai_ayetleri) != uthmani.ayet_sayisi:
        raise ValueError("imlai ve Uthmani ayet sayilari esit degil")
    ayetler: list[list[str]] = []
    nolar: list[list[int]] = []
    bel: list[list[bool]] = []
    for sira, ham in enumerate(imlai_ayetleri):
        belirtec = [a for h in ham for a in anahtarlar(h)]
        haritalanan, belirsiz = imlai_kelime_haritasi(
            belirtec, uthmani.ayet_belirtec[sira], uthmani.kelime_no[sira]
        )
        ayetler.append(belirtec)
        nolar.append(haritalanan)
        bel.append(belirsiz)
    return _kur("imlai", ayetler, nolar, bel, list(uthmani.ayet_kelime_sayisi))
