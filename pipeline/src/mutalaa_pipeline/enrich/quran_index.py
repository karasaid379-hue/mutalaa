"""Kur'an kelime n-gram indeksi (Iktibas tespiti §5; A18.3 `benzer_ayet`, A18.4 iktibas motoru).

Girdi: ayet basina NORMALIZE kelime listeleri (Tanzil Uthmani `quran_word.norm` ya da Simple Clean
`normalize_ar`); ayet sirasi mushaf sirasidir (0 tabanli ayet numarasi = liste sirasi). Kelimeler
mushaf sirasiyla KURESEL konuma sahiptir (0 tabanli). Indeks `n = 3` ve `n = 4` icin n-gram ->
baslangic konumlari tablosudur.

* `ayet_siniri_asar = False` (varsayilan, `benzer_ayet`): n-gramlar yalniz bir ayetin icinde
  kurulur; ayet sinirini asan pencere yoktur.
* `ayet_siniri_asar = True` (A18.4, ardisik ayet alintilari): pencereler ayet sinirini asabilir;
  bir pencerenin ayeti BASLADIGI ayettir. Ayet bazli kapsama sayimi (`komsular`) yalniz sorgu
  ayetinin kendi kelime konumlarini sayar.

Bu modul veritabani, dosya ve hat modullerini ice aktarmaz (saf hesap); metin yalniz bellekte
durur ve hicbir yere yazilmaz ya da kaydedilmez.
"""

from collections import defaultdict
from collections.abc import Sequence
from typing import Final

N_DEGERLERI: Final = (3, 4)
KAPI_N: Final = 4  # iki ayet arasinda adayligin sarti: en az bir ortak 4-gram
KAPSAMA_N: Final = 3  # kapsama sayimi: ortak 3-gram pencerelerinin birlesimi


class KuranIndeksi:
    """Normalize ayet kelime listelerinden 3 ve 4 gram indeksi."""

    def __init__(self, ayetler: Sequence[Sequence[str]], *, ayet_siniri_asar: bool = False) -> None:
        self.ayet_siniri_asar = ayet_siniri_asar
        self.kelimeler: list[str] = []
        self.ayet_of: list[int] = []
        self.ayet_baslangic: list[int] = []
        for sira, ayet in enumerate(ayetler):
            self.ayet_baslangic.append(len(self.kelimeler))
            self.kelimeler.extend(ayet)
            self.ayet_of.extend([sira] * len(ayet))
        self.ayet_baslangic.append(len(self.kelimeler))
        self._ngram: dict[int, dict[tuple[str, ...], list[int]]] = {
            n: self._kur(n) for n in N_DEGERLERI
        }
        self._tam_ayet: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for sira, ayet in enumerate(ayetler):
            if ayet:
                self._tam_ayet[tuple(ayet)].append(sira)

    @property
    def ayet_sayisi(self) -> int:
        return len(self.ayet_baslangic) - 1

    def ayet_uzunlugu(self, ayet: int) -> int:
        return self.ayet_baslangic[ayet + 1] - self.ayet_baslangic[ayet]

    def konum(self, ayet: int, kelime: int) -> int:
        """Ayet icindeki 0 tabanli kelime sirasinin kuresel konumu."""
        if not 0 <= kelime < self.ayet_uzunlugu(ayet):
            raise IndexError("kelime sirasi ayet disinda")
        return self.ayet_baslangic[ayet] + kelime

    def _baslangiclar(self, ayet: int, n: int) -> range:
        """Bir ayette baslayan n-gram pencerelerinin kuresel baslangic konumlari."""
        bas, son = self.ayet_baslangic[ayet], self.ayet_baslangic[ayet + 1]
        if self.ayet_siniri_asar:
            return range(bas, min(son, len(self.kelimeler) - n + 1))
        return range(bas, son - n + 1)

    def _anahtar(self, konum: int, n: int) -> tuple[str, ...]:
        return tuple(self.kelimeler[konum : konum + n])

    def _kur(self, n: int) -> dict[tuple[str, ...], list[int]]:
        tablo: dict[tuple[str, ...], list[int]] = defaultdict(list)
        for ayet in range(self.ayet_sayisi):
            for konum in self._baslangiclar(ayet, n):
                tablo[self._anahtar(konum, n)].append(konum)
        return tablo

    def konumlar(self, kelimeler: Sequence[str]) -> list[int]:
        """3 ya da 4 kelimelik bir dizinin indeksteki baslangic konumlari (kuresel, artan)."""
        n = len(kelimeler)
        if n not in self._ngram:
            raise ValueError("yalniz 3 ve 4 kelimelik diziler indekslenir")
        return list(self._ngram[n].get(tuple(kelimeler), ()))

    def tam_ayetler(self, kelimeler: Sequence[str]) -> list[int]:
        """Normalize ayet metni birebir ayni olan ayetler (n'den kisa ayetlerin tam alintisi)."""
        return list(self._tam_ayet.get(tuple(kelimeler), ()))

    def komsular(self, ayet: int) -> dict[int, int]:
        """`ayet` ile en az bir ortak 4-gram paylasan ayetler ve ortak kelime sayilari.

        Deger: sorgu ayetinin, o ayetle paylasilan 3-gram pencerelerinin kapsadigi kelime sayisi
        (pencere birlesimi; bir 4-gram eslesmesi iki 3-gram penceresidir). Sorgu ayetinin kendisi
        sonuca girmez.
        """
        kapi: set[int] = set()
        tablo4 = self._ngram[KAPI_N]
        for konum in self._baslangiclar(ayet, KAPI_N):
            for q in tablo4[self._anahtar(konum, KAPI_N)]:
                diger = self.ayet_of[q]
                if diger != ayet:
                    kapi.add(diger)
        if not kapi:
            return {}
        bas, son = self.ayet_baslangic[ayet], self.ayet_baslangic[ayet + 1]
        kapsanan: dict[int, set[int]] = {diger: set() for diger in kapi}
        tablo3 = self._ngram[KAPSAMA_N]
        for konum in self._baslangiclar(ayet, KAPSAMA_N):
            for q in tablo3[self._anahtar(konum, KAPSAMA_N)]:
                kume = kapsanan.get(self.ayet_of[q])
                if kume is not None:
                    kume.update(p for p in range(konum, konum + KAPSAMA_N) if bas <= p < son)
        return {diger: len(kume) for diger, kume in kapsanan.items()}
