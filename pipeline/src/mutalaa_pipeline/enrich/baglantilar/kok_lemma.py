"""`kok` ve `lemma` baglantilari: IDF ve birim-birim komsuluk (Baglanti modeli §6, K-51 madde 6).

```text
idf_n(r)   = ln(toplam / df(r)) / ln(toplam)       df: r'yi tasiyan AYET sayisi, toplam: 6.236
K(A)       = A'nin idf_n >= 0,3 olan kok (lemma) kumesi; idf_n < 0,3 olanlar kumeden CIKARILIR
score(A,B) = sum idf_n(r in K(A) ve K(B)) / sum idf_n(r in K(A))
```

Her A icin en yuksek `en_cok` (5) komsu B (B != A); sira (score azalan, ayet sirasi artan):
score, sira icin de depolama icin de 6 haneye yuvarlanir, esitlik yuvarlanmis degerle bozulur.
`K(A)` bos ise A satir uretmez. Ters indeks (kimlik -> ayetler) yalniz ortak kimlikli adaylari
tarar. Yon kaynak A -> hedef B'dir; simetri aranmaz (Baglanti modeli §4 madde 4).
"""

import heapq
import math
from collections import defaultdict
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from mutalaa_pipeline.enrich.baglantilar.girdi import Kelime

IDF_ESIGI: Final = 0.3
EN_COK_KOMSU: Final = 5
SKOR_BASAMAGI: Final = 6
TOPLAM_AYET: Final = 6236

Alan = Literal["root_id", "lemma_id"]


@dataclass(frozen=True)
class OrtakKimlik:
    kimlik: int
    idf: float
    src_kelime: str  # kaynak ayette kimligi tasiyan ilk kelimenin capasi (q:s:a:k)
    dst_kelime: str


@dataclass(frozen=True)
class Komsu:
    src: int  # ayet sirasi
    dst: int
    skor: float
    ortaklar: tuple[OrtakKimlik, ...]  # idf azalan, kimlik artan


def idf_n(df: int, toplam: int = TOPLAM_AYET) -> float:
    """`ln(toplam/df) / ln(toplam)`; `df` 1..toplam."""
    if not 1 <= df <= toplam or toplam < 2:
        raise ValueError("df 1..toplam araliginda, toplam en az 2 olmali")
    return math.log(toplam / df) / math.log(toplam)


@dataclass(frozen=True)
class Kumeler:
    """Bir alanin (kok ya da lemma) ayet kumeleri ve ters indeksi."""

    df: dict[int, int]  # kimlik -> ayet sayisi (tum kimlikler)
    idf: dict[int, float]  # kimlik -> idf_n (yalniz kumeye girenler: idf_n >= esik)
    ilk_kelime: list[dict[int, str]]  # ayet sirasi -> {kimlik: ilk kelime capasi} (kumeye girenler)
    ters: dict[int, list[int]]  # kimlik -> ayet sirasi (artan; yalniz kumeye girenler)
    cikarilan: int  # idf_n < esik oldugu icin kumeden cikarilan kimlik sayisi


def kumeleri_kur(
    kelimeler: Sequence[Kelime],
    alan: Alan,
    ayet_sayisi: int,
    *,
    toplam: int | None = None,
    esik: float = IDF_ESIGI,
) -> Kumeler:
    """`alan` kimliklerinin df, idf_n, ayet kumeleri ve ters indeksi.

    `kelimeler` (ayet sirasi, kelime numarasi) sirasindadir; ilk kelime en kucuk numaradir.
    `toplam` verilmezse `ayet_sayisi` kullanilir (gercek veride 6.236).
    """
    n = toplam if toplam is not None else ayet_sayisi
    ilk: list[dict[int, str]] = [{} for _ in range(ayet_sayisi)]
    for k in kelimeler:
        kimlik = k.root_id if alan == "root_id" else k.lemma_id
        if kimlik is not None and kimlik not in ilk[k.sira]:
            ilk[k.sira][kimlik] = k.capa
    df: dict[int, int] = defaultdict(int)
    for kume in ilk:
        for kimlik in kume:
            df[kimlik] += 1
    idf: dict[int, float] = {}
    for kimlik, sayi in df.items():
        deger = idf_n(sayi, n)
        if deger >= esik:
            idf[kimlik] = deger
    kumeler: list[dict[int, str]] = [
        {kimlik: capa for kimlik, capa in sorted(kume.items()) if kimlik in idf} for kume in ilk
    ]
    ters: dict[int, list[int]] = defaultdict(list)
    for sira, kume in enumerate(kumeler):
        for kimlik in kume:
            ters[kimlik].append(sira)
    return Kumeler(dict(df), idf, kumeler, dict(ters), len(df) - len(idf))


def df_uyumsuzluklari(df: Mapping[int, int], kayitli: Mapping[int, int]) -> list[int]:
    """`root.ayah_count` ile hesaplanan df'in tutmadigi kok kimlikleri (artan).

    Kayitli sayaci olmayan ya da hesapta bulunmayan kimlik de uyumsuzluktur; sayac 0 olan ve
    hesapta gecmeyen kok (QAC'de kelimesi olmayan) uyumsuzluk degildir.
    """
    kimlikler = set(df) | {k for k, v in kayitli.items() if v != 0}
    return sorted(k for k in kimlikler if df.get(k, 0) != kayitli.get(k, 0))


def yuvarla(skor: float) -> float:
    """Depolanan skor: 6 hane, en cok 1,0."""
    return min(1.0, round(skor, SKOR_BASAMAGI))


def komsular(
    kumeler: Kumeler, *, en_cok: int = EN_COK_KOMSU, kaynaklar: Sequence[int] | None = None
) -> Iterator[Komsu]:
    """Her kaynak ayet icin en yuksek `en_cok` komsu (ayet sirasi artan, sonra siralama sirasi)."""
    idf = kumeler.idf
    for a in kaynaklar if kaynaklar is not None else range(len(kumeler.ilk_kelime)):
        kume_a = kumeler.ilk_kelime[a]
        if not kume_a:
            continue
        payda = sum(idf[r] for r in kume_a)
        pay: dict[int, float] = defaultdict(float)
        ortak: dict[int, list[int]] = defaultdict(list)
        for r in kume_a:  # kimlik artan: toplama sirasi sabit
            deger = idf[r]
            for b in kumeler.ters[r]:
                if b != a:
                    pay[b] += deger
                    ortak[b].append(r)
        if not pay:
            continue
        puanlar = {b: yuvarla(p / payda) for b, p in pay.items()}
        for b in heapq.nsmallest(en_cok, puanlar, key=lambda b: (-puanlar[b], b)):
            ortaklar = tuple(
                OrtakKimlik(r, idf[r], kume_a[r], kumeler.ilk_kelime[b][r])
                for r in sorted(ortak[b], key=lambda r: (-idf[r], r))
            )
            yield Komsu(a, b, puanlar[b], ortaklar)
