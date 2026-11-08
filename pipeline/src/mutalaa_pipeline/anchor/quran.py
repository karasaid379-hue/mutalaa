"""Kur'an ayet metnini kelimelere boler (K-43 madde 1): `q:{sure}:{ayet}:{kelime}` konumlari.

Kelime numarasi QAC ve QPC1 konumudur. Bolme yalniz ARALIK hesaplar: metni kopyalamaz, normalize
etmez, kirpmaz (K-26); kelime metni `ayet_metni[char_start:char_end]` dilimidir. Ofsetler Unicode
kod noktasidir ve aralik yari acik `[baslangic, bitis)`'tir.

Kural (Tanzil Uthmani ayet metni icin):

* Belirtecler yalniz U+0020 ile ayrilir. Bos belirtec (basta, sonda ya da cift bosluk) belirtec
  degildir: atlanir ve sayilmaz (gercek Tanzil metninde yoktur; ofsetler yine ayet metnine
  gorendir).
* Yalniz U+06D6-U+06ED karakterlerinden olusan belirtec (durak ve secde isaretleri) kelime degildir.
* Sure 2-114'un (9 haric) 1. ayetinde ilk dort belirtec besmeledir ve numara almaz. Sure 1'in
  1. ayeti besmeledir ve kelimeleri sayilir.
* Tanzil'de bitisik iki belirtecin QAC ve QPC1'de tek kelime oldugu dort ayet `BIRLESTIRME`
  listesiyle birlestirilir. Deger, kural uygulandiktan sonra (besmele ve durak isareti atilmis)
  kelime-belirteclerinde 1 tabanli siradir: `3` demek 3. ve 4. belirtec tek kelime olur. Birlesen
  kelimenin araligi iki belirteci ve aradaki bosluklari kapsar. Listedeki her degisiklik `/karar`
  ister.
"""

from typing import Final, NamedTuple

DURAK_ILK: Final = 0x06D6
DURAK_SON: Final = 0x06ED
BESMELE_BELIRTEC: Final = 4
BESMELESIZ_SURELER: Final = frozenset({1, 9})  # 1: ayet zaten besmele, 9: besmele yok
SURE_SAYISI: Final = 114
BOSLUK: Final = " "

# (sure, ayet) -> birlesecek ilk belirtecin 1 tabanli sirasi (K-43 madde 1).
BIRLESTIRME: Final[dict[tuple[int, int], int]] = {
    (2, 181): 3,
    (8, 6): 4,
    (13, 37): 8,
    (37, 130): 3,
}


class KelimeBolmeHatasi(ValueError):
    """Ayet metni kurala gore bolunemedi. Iletide metin yer almaz (yalniz sure, ayet, neden)."""


class Kelime(NamedTuple):
    """Bir kelimenin numarasi (1 tabanli) ve ayet metnindeki `[char_start, char_end)` araligi."""

    word: int
    char_start: int
    char_end: int


def durak_belirteci_mi(belirtec: str) -> bool:
    """Belirtec bos degil ve yalniz U+06D6-U+06ED karakterlerinden olusuyor mu."""
    return belirtec != "" and all(DURAK_ILK <= ord(harf) <= DURAK_SON for harf in belirtec)


def besmele_onekli_mi(sure: int, ayet: int) -> bool:
    """Ayetin ilk dort belirteci besmele midir (sure 2-114, 9 haric, 1. ayet)."""
    return ayet == 1 and sure not in BESMELESIZ_SURELER


def _belirtecler(metin: str) -> list[tuple[int, int]]:
    """Bos olmayan belirteclerin `(baslangic, bitis)` kod noktasi araliklari (U+0020 ayiricili)."""
    araliklar: list[tuple[int, int]] = []
    bas = 0
    for konum, harf in enumerate(metin):
        if harf == BOSLUK:
            araliklar.append((bas, konum))
            bas = konum + 1
    araliklar.append((bas, len(metin)))
    return [(bas, son) for bas, son in araliklar if bas < son]


def kelimelere_bol(metin: str, sure: int, ayet: int) -> list[Kelime]:
    """Ayet metnini K-43 kuralina gore kelimelere boler; numaralar 1'den kesintisizdir.

    `sure` 1..114 ve `ayet` >= 1 olmalidir. Besmele onekli ayette en az bir kelime kalmali,
    birlestirme listesindeki ayette birlesecek iki belirtec bulunmalidir; aksi halde
    `KelimeBolmeHatasi`. Sonuc bos olamaz.
    """
    if not 1 <= sure <= SURE_SAYISI or ayet < 1:
        raise KelimeBolmeHatasi(f"{sure}:{ayet}: sure ya da ayet gecersiz")
    belirtecler = _belirtecler(metin)
    if besmele_onekli_mi(sure, ayet):
        if len(belirtecler) < BESMELE_BELIRTEC:
            raise KelimeBolmeHatasi(f"{sure}:{ayet}: besmele icin {BESMELE_BELIRTEC} belirtec yok")
        belirtecler = belirtecler[BESMELE_BELIRTEC:]
    kelimeler = [(bas, son) for bas, son in belirtecler if not durak_belirteci_mi(metin[bas:son])]
    birlesecek = BIRLESTIRME.get((sure, ayet))
    if birlesecek is not None:
        if birlesecek < 1 or birlesecek >= len(kelimeler):
            raise KelimeBolmeHatasi(f"{sure}:{ayet}: birlestirilecek belirtec cifti yok")
        kelimeler[birlesecek - 1 : birlesecek + 1] = [
            (kelimeler[birlesecek - 1][0], kelimeler[birlesecek][1])
        ]
    if not kelimeler:
        raise KelimeBolmeHatasi(f"{sure}:{ayet}: ayette kelime yok")
    return [Kelime(sira, bas, son) for sira, (bas, son) in enumerate(kelimeler, start=1)]
