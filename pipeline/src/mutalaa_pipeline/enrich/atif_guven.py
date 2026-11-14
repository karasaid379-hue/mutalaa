"""Iktibas adayinin `score` ve `confidence` hesabi (A20.7b; Baglanti modeli §6, Iktibas §7-8).

Hesap araca degil bize aittir (K-51 madde 13): arac yalniz eslesmeyi ve kelime konumlarini
verir. Butun degerler "binde" tam sayidir (0..1000): staged JSON ondalik sayi tasimaz
(`export/ortak.kati_json`); veritabaninda `score` ve `confidence` `binde / 1000` olur.

Girdiler: `n` eslesen kelime, `toplam` eslesmenin degdigi ayetlerin kelime sayisi (QAC), `f`
eslesen dizinin Kur'an'da gectigi farkli yer sayisi (`tekrar`; kalip ifade cezasi).

    kapsama = min(1000, 1000 n / toplam)
    skor    = (0,5 + 0,5 n/toplam) . min(1, n/7) . 1/f          (Baglanti modeli §6; e = 0)
    guven   = (200 + 100 min(n, 7)) . (500 + kapsama/2) / 1000 . 1/f

`e` (duzenleme) sifirdir: arac kelime dizisi esler, hizalama yapmaz. `guven` kalibre degildir:
baslangic degeridir ve altin set (I-13) gelince lojistik regresyonla degisir (Iktibas tespiti §8).
Tamami tam sayi bolmesidir (kayan nokta yok): ayni girdi ayni baytlari verir.
"""

from dataclasses import dataclass
from typing import Final

BINDE: Final = 1000
UZUNLUK_DOYUMU: Final = 7  # min(1, n/7)
TABAN_KELIME_BASINA: Final = 100
TABAN_SABIT: Final = 200


def binde(oran: float) -> int:
    """0-1 arasi kesri binde tam sayiya cevirir (en yakina yuvarlar)."""
    return round(oran * BINDE)


@dataclass(frozen=True, slots=True)
class Puan:
    skor: int
    guven: int
    kapsama: int


def iktibas_puani(n: int, toplam: int, tekrar: int = 1) -> Puan:
    """`score`, `confidence` ve kapsama (binde). `n >= 1`, `toplam >= 1`, `tekrar >= 1`."""
    if n < 1 or toplam < 1 or tekrar < 1:
        raise ValueError("n, toplam ve tekrar en az 1 olmali")
    etkin = min(n, toplam)
    kapsama = etkin * BINDE // toplam
    pay = (toplam + etkin) * min(UZUNLUK_DOYUMU, n) * BINDE
    skor = pay // (2 * toplam * UZUNLUK_DOYUMU * tekrar)
    taban = TABAN_SABIT + TABAN_KELIME_BASINA * min(n, UZUNLUK_DOYUMU)
    guven = taban * (BINDE // 2 + kapsama // 2) // BINDE // tekrar
    return Puan(min(skor, BINDE), min(guven, BINDE), kapsama)
