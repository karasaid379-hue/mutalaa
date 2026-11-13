"""Baglam sinyalleri, puan ve guven (Iktibas tespiti §7-§8; Baglanti modeli §6): saf islevler.

Puan (Baglanti modeli §6): `score = (0,5 + 0,5 n/N) * min(1, n/7) * n/(n+e) * 1/f`.

Guven (baslangic degerleri; altin setle kalibre edilir):

* taban: `min(score, 0,90)`;
* komsu ayet +0,15 (ayni paragrafta ayni sureden en cok 3 ayet uzaklikta baska iktibas),
  meal benzerligi +0,15 (lemma ortusmesi >= 0,5), Kur'an ipucu +0,10, konum (baslik ya da sus
  parantezi) +0,10, ters ipucu -0,20; sonuc [0, 0,98];
* acik atif +-200 karakterde ayni ayete: `consistent_quote = true`, guven en az 0,99; baska ayete
  hizalaniyorsa `consistent_quote = false`, guven 0,30 (numaralandirma farki ya da OCR hatasi
  olabilir; kuyrugun basina gider).

`sinif_ipucu` sunucudaki `LinkCandidateClassifier` kuralinin aynasidir: tutarsiz, toplu, gri,
diger (editor kuyrugu sirasi).
"""

import struct
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.normalize import normalize_tr

IPUCLARI_YOLU: Final = Path(__file__).resolve().parent / "ipuclari.toml"
TABAN_UST: Final = 0.90
GUVEN_UST: Final = 0.98
GUVEN_TUTARLI: Final = 0.99
GUVEN_TUTARSIZ: Final = 0.30
ETKI_KOMSU: Final = 0.15
ETKI_MEAL: Final = 0.15
ETKI_KURAN: Final = 0.10
ETKI_KONUM: Final = 0.10
ETKI_TERS: Final = -0.20
ATIF_MESAFESI: Final = 200
KOMSU_UZAKLIK: Final = 3
IPUCU_PENCERESI: Final = 80
MEAL_PENCERESI: Final = 300
MEAL_ESIGI: Final = 0.5
MEAL_EN_AZ_ORTAK: Final = 2

SINIF_TUTARSIZ: Final = "tutarsiz"
SINIF_TOPLU: Final = "toplu"
SINIF_GRI: Final = "gri"
SINIF_DIGER: Final = "diger"


@dataclass(frozen=True)
class Ipuclari:
    kuran: tuple[tuple[str, ...], ...]
    ters: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Sinyaller:
    acik_atif: bool = False  # ayni ayete +-200 karakterde acik atif
    komsu: bool = False
    meal_benzerligi: float | None = None
    kuran_ipucu: bool = False
    ters_ipucu: bool = False
    konum: bool = False

    @property
    def olumlu(self) -> bool:
        """§7 "baglam sinyali var": olumlu herhangi bir sinyal."""
        return (
            self.acik_atif
            or self.komsu
            or self.meal_benzerligi is not None
            or self.kuran_ipucu
            or self.konum
        )


def _anahtar_kelimeleri(ifade: str) -> tuple[str, ...]:
    return tuple(normalize_tr(ifade, "genis").split())


def ipuclari_oku(yol: Path | None = None) -> Ipuclari:
    veri = tomllib.loads((yol or IPUCLARI_YOLU).read_text(encoding="utf-8"))

    def liste(ad: str) -> tuple[tuple[str, ...], ...]:
        ham = veri.get(ad, [])
        if not isinstance(ham, list) or not all(isinstance(x, str) for x in ham):
            raise ValueError(f"ipuclari: `{ad}` metin dizisi olmali")
        return tuple(k for k in map(_anahtar_kelimeleri, ham) if k)

    return Ipuclari(liste("kuran"), liste("ters"))


def ipucu_var(pencere: str, ifadeler: Sequence[Sequence[str]]) -> bool:
    """Pencere metninde ifadelerden biri kelime dizisi olarak gecer mi (genis anahtarla)."""
    kelimeler = normalize_tr(pencere, "genis").split()
    for ifade in ifadeler:
        n = len(ifade)
        if n and any(
            tuple(kelimeler[i : i + n]) == tuple(ifade) for i in range(len(kelimeler) - n + 1)
        ):
            return True
    return False


def lemma_kumesi(metin: str, sozluk: Mapping[str, frozenset[int]]) -> frozenset[int]:
    """Metnin dar anahtarlarinin `tr_form` sozlugundeki lemma kimlikleri."""
    sonuc: set[int] = set()
    for k in normalize_tr(metin, "dar").split():
        sonuc |= sozluk.get(k, frozenset())
    return frozenset(sonuc)


def meal_benzerligi(
    takip: str, meal: str | None, sozluk: Mapping[str, frozenset[int]]
) -> float | None:
    """Lemma ortusmesi (`|A n B| / min(|A|, |B|)`); esik ve en az 2 ortak lemma yoksa None."""
    if not sozluk or not meal:
        return None
    a, b = lemma_kumesi(takip, sozluk), lemma_kumesi(meal, sozluk)
    ortak = len(a & b)
    if not a or not b or ortak < MEAL_EN_AZ_ORTAK:
        return None
    oran = ortak / min(len(a), len(b))
    return oran if oran >= MEAL_ESIGI else None


def iktibas_puani(n: int, ayet_kelime: int, duzenleme: int, f: int) -> float:
    """Baglanti modeli §6: `(0,5 + 0,5 n/N) * min(1, n/7) * n/(n+e) * 1/f` ([0, 1] araliginda)."""
    if n <= 0 or ayet_kelime <= 0 or f <= 0:
        return 0.0
    kapsama = min(1.0, n / ayet_kelime)
    puan = (0.5 + 0.5 * kapsama) * min(1.0, n / 7) * (n / (n + duzenleme)) / f
    return max(0.0, min(1.0, puan))


def guven_hesapla(puan: float, sinyal: Sinyaller, *, tutarli: bool | None) -> float:
    """Baslangic guveni; `tutarli`: True ayni ayete atif, False baska ayete, None atif yok."""
    if tutarli is False:
        return GUVEN_TUTARSIZ
    guven = min(puan, TABAN_UST)
    guven += ETKI_KOMSU if sinyal.komsu else 0.0
    guven += ETKI_MEAL if sinyal.meal_benzerligi is not None else 0.0
    guven += ETKI_KURAN if sinyal.kuran_ipucu else 0.0
    guven += ETKI_KONUM if sinyal.konum else 0.0
    guven += ETKI_TERS if sinyal.ters_ipucu else 0.0
    guven = max(0.0, min(GUVEN_UST, guven))
    if tutarli is True:
        guven = max(guven, GUVEN_TUTARLI)
    return guven


def sinif_ipucu(
    tur: str,
    guven: float,
    *,
    matched_words: int | None,
    coverage: float | None,
    phrase_freq: int | None,
    consistent_quote: bool | None,
) -> str:
    """Sunucudaki `LinkCandidateClassifier.Classify` ile ayni sira ve esikler (float32)."""
    guven32 = _float32(guven)  # sunucu `real` (float32) ile kiyaslar
    if consistent_quote is False or (tur == "atif" and guven32 <= _float32(0.30)):
        return SINIF_TUTARSIZ
    if (
        tur in ("iktibas", "atif")
        and matched_words is not None
        and matched_words >= 7
        and coverage is not None
        and coverage >= 0.999999
        and phrase_freq == 1
        and (consistent_quote is True or guven32 >= _float32(0.95))
    ):
        return SINIF_TOPLU
    return SINIF_GRI if _float32(0.40) <= guven32 < _float32(0.80) else SINIF_DIGER


def _float32(deger: float) -> float:
    return float(struct.unpack("f", struct.pack("f", deger))[0])
