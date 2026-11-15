"""Atif araci sarmalayicisi: `quran-toolkit` 0.1.0 (K-52 madde 13; A20.7a olcumu sonrasi).

`ijaza` 2.0.0 ve `quran-detector` 0.0.2 elendi; sarmalayicilari ve import'lari silindi. Arac
Kur'an verisini kendi paketinden degil Tanzil Simple Clean metninden alir (`kuran_metni`): her
ayetin kelimesi QAC siralamasiyla (besmele onegi ve durak isaretleri haric) bir `QuranToken` olur.
Ayetin simple-clean kelime sayisi QAC sayisiyla ayni degilse konum 0 verilir (konum bilinmiyor;
hedef ayet duzeyinde kalir). Dosya yazilmaz: araclarin `find_ayat` islevi dogrudan bellekteki
jeton listesiyle cagrilir.

Sarmalayici bir diziyi (Arapca metin) alir ve `DiziEslesmesi` listesi dondurur; ofsetler dizi
metninde kod noktasi, `[bas, son)`. Arac en az `min_words` (4) kelimelik diziler bulur; daha
kisa dizi arac tarafindan bulunmaz. `tekrar`, eslesen kelime dizisinin Kur'an'da kac farkli
yerde gectigidir (kalip ifade cezasi icin); aracin kendi ciktisi degildir, jeton listesinden
hesaplanir. Metin hicbir yerde saklanmaz ya da yazilmaz.
"""

import importlib
import importlib.metadata
from collections.abc import Sequence
from typing import Any, Final

from mutalaa_pipeline.enrich.citations import DiziEslesmesi, Parca
from mutalaa_pipeline.enrich.kuran_metni import Ayet, basit_kelimeler

ARAC_ADI: Final = "quran-toolkit"
ARAC_MODULU: Final = "quran_toolkit"
ARAC_SURUMU: Final = "0.1.0"
EN_AZ_KELIME: Final = 4  # aracin varsayilan en kucuk dizi uzunlugu (Iktibas tespiti §7)
KONUM_YOK: Final = 0
WAW: Final = "\N{ARABIC LETTER WAW}"


def paket_surumu(paket: str = ARAC_ADI) -> str:
    """Yuklu paketin dagitim surumu."""
    return importlib.metadata.version(paket)


class ToolkitSarmalayici:
    """quran-toolkit 0.1.0: `find_ayat` (kelime dizisi eslesmesi; Tanzil Simple Clean)."""

    ad: str = ARAC_ADI
    surum: str = ARAC_SURUMU

    def __init__(self, ayetler: Sequence[Ayet], *, min_words: int = EN_AZ_KELIME) -> None:
        self._paket: Any = importlib.import_module(ARAC_MODULU)
        paket = self._paket
        self._min_words = min_words
        jetonlar: list[Any] = []
        for a in ayetler:
            if a.basit_kelimeler is not None:
                kelimeler = a.basit_kelimeler
                konumlar = range(1, len(kelimeler) + 1)
            else:  # hizasiz ayet: konum bilinmiyor; kelimeler yine eslesmeye girer
                kelimeler = _hizasiz_kelimeler(a)
                konumlar = range(len(kelimeler))
            for sira, kelime in zip(konumlar, kelimeler, strict=True):
                bicimler = frozenset(x for x in (paket.normalize_arabic(kelime),) if x)
                if not bicimler:
                    continue  # aracin yukleyicisi gibi: bos kalan jeton atilir
                jetonlar.append(
                    paket.QuranToken(a.sure, a.ayet, sira if a.hizali else KONUM_YOK, bicimler)
                )
        self._jetonlar: list[Any] = jetonlar
        self._indeks: Any = paket.build_index(jetonlar)

    def _tekrar(self, eslesme: Any) -> int:
        """Eslesen normalize kelime dizisinin Kur'an'daki baslangic sayisi (en az 1)."""
        paket = self._paket
        dizi = [
            "".join(paket.normalize_arabic(paket.clean_token(t)) for t in w.text.split())
            for w in eslesme.words
        ]
        if not dizi:
            return 1
        adaylar = set(self._indeks.get(dizi[0], ())) | set(self._indeks.get(WAW + dizi[0], ()))
        sayi = 0
        for c in adaylar:
            if c + len(dizi) > len(self._jetonlar):
                continue
            ilk = self._jetonlar[c].forms
            if dizi[0] not in ilk and WAW + dizi[0] not in ilk:
                continue
            if all(dizi[k] in self._jetonlar[c + k].forms for k in range(1, len(dizi))):
                sayi += 1
        return max(1, sayi)

    def tespit_et(self, dizi_metni: str) -> list[DiziEslesmesi]:
        sonuc: list[DiziEslesmesi] = []
        eslesmeler = self._paket.find_ayat(
            dizi_metni, self._jetonlar, self._indeks, min_words=self._min_words
        )
        for e in eslesmeler:
            parcalar: list[Parca] = []
            for k, w in enumerate(e.words):
                sure = self._jetonlar[e.word_start + k].surah
                if parcalar and (parcalar[-1].sure, parcalar[-1].ayet) == (sure, w.ayah):
                    onceki = parcalar[-1]
                    parcalar[-1] = Parca(sure, w.ayah, onceki.ilk, w.position, onceki.sayi + 1)
                else:
                    parcalar.append(Parca(sure, w.ayah, w.position, w.position, 1))
            ayetler = tuple((p.sure, p.ayet) for p in parcalar)
            sonuc.append(
                DiziEslesmesi(
                    e.char_start,
                    e.char_end,
                    ayetler,
                    None,
                    len(e.words),
                    tuple(parcalar),
                    self._tekrar(e),
                )
            )
        return sonuc


def _hizasiz_kelimeler(ayet: Ayet) -> tuple[str, ...]:
    """Hizasiz ayetin eslesmeye girecek kelimeleri: Simple Clean belirtecleri (besmele atilir)."""
    return basit_kelimeler(ayet.sure, ayet.ayet, ayet.basit)
