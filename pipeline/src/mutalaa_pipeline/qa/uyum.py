"""Degerlendirici uyumu ve ikinci okuma olcumleri (A17.6; Kelime anlamlari §7; K-50).

Saf islevler (yalniz standart kitaplik: `math`, `statistics`, `fractions`); veritabani, dosya ve
yapilandirma yok. Komut katmani `cli_gloss_ornek.py` dosyasindadir.

COHEN KAPPA (Cohen 1960, "A coefficient of agreement for nominal scales"; belge §7 madde 2):
`kappa = (p_o - p_e) / (1 - p_e)`; `p_o` gozlenen uyum, `p_e = sum_k (a_k / n) * (b_k / n)` iki
degerlendiricinin kategori paylarindan beklenen sans uyumu. Hesap tam sayi sayimlariyla
`Fraction` uzerinde yapilir: `kappa = (uyum * n - sum_k a_k * b_k) / (n * n - sum_k a_k * b_k)`.
Boylece `kappa >= 0,60` karsilastirmasi (3/5) kayan noktali gurultuden etkilenmez.
Sinir durumlari (belgelenmis davranis):
- `n = 0` ya da uzunluklar farkli: `GirdiHatasi` (olcum yok).
- Payda 0 (`p_e = 1`): iki degerlendirici de tek ve ayni kategoriyi kullandi, yani `p_o = 1`.
  `kappa = 1,0` doner (tam uyum), ama bu ayrim gucu olmayan bir olcumdur: `kappa_ozet`
  `tek_kategori = True` yazar ve hedefi GECMIS saymaz.

WILSON UST SINIRI (Wilson 1927, JASA 22(158); Agresti ve Coull 1998 ozeti): `n` okumada `hata`
hata icin gozlenen oran `p = hata / n`; Wilson puan araligi
`(p + z^2 / 2n +- z * sqrt(p (1 - p) / n + z^2 / 4n^2)) / (1 + z^2 / n)`. Belge §7 madde 3 "%95
Wilson araligi" der: iki yanli %95, `z = NormalDist().inv_cdf(0,975)` (~1,95996). `z` sabiti
belgede yoktur; hesaplanir, uydurulmaz. Sinirlar: `n = 0` icin bilgi yoktur, ust sinir 1,0 doner
(hata 0 olmali); `hata = 0` ust sinir `z^2 / (n + z^2)`; `hata = n` ust sinir 1,0 (kayan nokta
tasmasina karsi [0, 1] araligina kirpilir).

IKINCI OKUMA (belge §7 madde 3): her dalgada onayli maddelerden en az 300 ya da %10:
`gereken = min(N, max(300, ceil(N / 10)))`. Tavan tam sayi aritmetigiyle alinir (kayan nokta
yok; 0..200000 araliginda `math.ceil(0,1 * N)` ile ayni sonucu verdigi denenmistir). Evren
300'den kucukse tamami okunur. Hata sayilan etiket `yanlis`; `kucuk_hata` ayri sayilir ve
Wilson'a girmez. Hedef: ust sinir <= %2 (oneri esigi).
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from fractions import Fraction
from statistics import NormalDist
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi

KAPPA_HEDEF: Final = Fraction(3, 5)  # belge §7 madde 2: inceleyenler arasi kappa >= 0,60
GUVEN: Final = 0.95  # iki yanli Wilson araligi
Z_95: Final = NormalDist().inv_cdf(0.5 + GUVEN / 2)
WILSON_HEDEF: Final = 0.02  # belge §7 madde 3: ust sinir <= %2
EN_AZ_OKUNAN: Final = 300
ORAN_PAYDA: Final = 10  # %10 = N / 10

KAPPA_ETIKETLERI: Final = ("kabul", "duzelt", "red")
OKUMA_ETIKETLERI: Final = ("dogru", "kucuk_hata", "yanlis")
HATA_ETIKETI: Final = "yanlis"


# --- Cohen kappa ---------------------------------------------------------------------------


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Iki degerlendiricinin etiket listeleri (ayni sirada, ayni maddeler) icin Cohen kappa."""
    return float(_kappa_kesir(a, b)[0])


def _kappa_kesir(a: Sequence[str], b: Sequence[str]) -> tuple[Fraction, Fraction, Fraction]:
    """`(kappa, p_o, p_e)` tam kesir olarak; payda 0 ise kappa 1 (modul belgesine bak)."""
    n = len(a)
    if n == 0:
        raise GirdiHatasi("kappa icin en az bir madde gerekir")
    if len(b) != n:
        raise GirdiHatasi("kappa icin iki listenin uzunlugu esit olmali")
    uyum = sum(1 for x, y in zip(a, b, strict=True) if x == y)
    ca, cb = Counter(a), Counter(b)
    beklenen = sum(ca[k] * cb[k] for k in ca.keys() & cb.keys())
    p_o = Fraction(uyum, n)
    p_e = Fraction(beklenen, n * n)
    if p_e == 1:
        return Fraction(1), p_o, p_e
    return (p_o - p_e) / (1 - p_e), p_o, p_e


@dataclass(frozen=True)
class KappaOzeti:
    """Yalniz sayilar ve sonuc; etiket METNI ve anlam metni yoktur."""

    n: int
    uyum_sayisi: int
    p_o: float
    p_e: float
    kappa: float
    hedef: float
    tek_kategori: bool
    gecti: bool
    a_sayilari: dict[str, int]
    b_sayilari: dict[str, int]

    def sozluk(self) -> dict[str, object]:
        return asdict(self)


def kappa_ozet(a: Sequence[str], b: Sequence[str]) -> KappaOzeti:
    """Kappa, bilesenleri ve hedef (>= 0,60) karsilastirmasi. Tek kategori hedefi gecmez."""
    kappa, p_o, p_e = _kappa_kesir(a, b)
    tek = p_e == 1
    return KappaOzeti(
        n=len(a),
        uyum_sayisi=sum(1 for x, y in zip(a, b, strict=True) if x == y),
        p_o=float(p_o),
        p_e=float(p_e),
        kappa=float(kappa),
        hedef=float(KAPPA_HEDEF),
        tek_kategori=tek,
        gecti=(not tek) and kappa >= KAPPA_HEDEF,
        a_sayilari=dict(sorted(Counter(a).items())),
        b_sayilari=dict(sorted(Counter(b).items())),
    )


# --- Wilson --------------------------------------------------------------------------------


def wilson_ust_sinir(hata: int, n: int, z: float = Z_95) -> float:
    """`n` okumada `hata` hata icin Wilson puan araliginin ust siniri (modul belgesine bak)."""
    if n < 0 or not 0 <= hata <= n:
        raise GirdiHatasi("wilson icin 0 <= hata <= n olmali")
    if z < 0.0:
        raise GirdiHatasi("wilson icin z >= 0 olmali")
    if n == 0 or hata == n:
        return 1.0  # hata = n: oran 1, ust sinir tam 1 (kayan nokta 1 - 2e-16 vermesin)
    p = hata / n
    z2 = z * z
    kok = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n))
    ust = (p + z2 / (2.0 * n) + kok) / (1.0 + z2 / n)
    return min(1.0, max(0.0, ust))


def wilson_alt_sinir(hata: int, n: int, z: float = Z_95) -> float:
    """Wilson araliginin alt siniri (`wilson_ust_sinir`in simetrigi; `n = 0` icin 0,0)."""
    if n < 0 or not 0 <= hata <= n:
        raise GirdiHatasi("wilson icin 0 <= hata <= n olmali")
    if n == 0:
        return 0.0
    return 1.0 - wilson_ust_sinir(n - hata, n, z)


# --- ikinci okuma --------------------------------------------------------------------------


def ikinci_okuma_boyu(onayli_evren: int) -> int:
    """`min(N, max(300, ceil(N / 10)))`: bir dalgada okunacak onayli madde sayisi."""
    if onayli_evren < 0:
        raise GirdiHatasi("onayli evren 0 ya da daha buyuk olmali")
    yuzde_on = -(-onayli_evren // ORAN_PAYDA)  # tam sayi tavan
    return min(onayli_evren, max(EN_AZ_OKUNAN, yuzde_on))


@dataclass(frozen=True)
class IkinciOkumaOzeti:
    """Bir dalganin ikinci okuma sonucu; yalniz sayilar ve sonuc."""

    evren: int
    gereken: int
    okunan: int
    dogru: int
    kucuk_hata: int
    yanlis: int
    yanlis_orani: float
    wilson_alt_95: float
    wilson_ust_95: float
    hedef: float
    yeterli_orneklem: bool
    hedef_saglandi: bool
    gecti: bool

    def sozluk(self) -> dict[str, object]:
        return asdict(self)


def ikinci_okuma_ozet(
    etiketler: Sequence[str], onayli_evren: int, z: float = Z_95
) -> IkinciOkumaOzeti:
    """Okunan maddelerin etiketleri (`dogru`, `kucuk_hata`, `yanlis`) ve onayli evren boyu.

    `gecti`: orneklem yeterli (`okunan >= gereken`) VE Wilson ust siniri <= %2. Okunan hic yoksa
    ust sinir 1,0 olur ve hedef saglanmaz.
    """
    gecersiz = sorted(set(etiketler) - set(OKUMA_ETIKETLERI))
    if gecersiz:
        raise GirdiHatasi("ikinci okuma etiketi dogru, kucuk_hata ya da yanlis olmali")
    sayac = Counter(etiketler)
    okunan = len(etiketler)
    gereken = ikinci_okuma_boyu(onayli_evren)
    if okunan > onayli_evren:
        raise GirdiHatasi("okunan madde sayisi onayli evrenden buyuk olamaz")
    yanlis = sayac[HATA_ETIKETI]
    ust = wilson_ust_sinir(yanlis, okunan, z)
    yeterli = okunan >= gereken
    saglandi = ust <= WILSON_HEDEF
    return IkinciOkumaOzeti(
        evren=onayli_evren,
        gereken=gereken,
        okunan=okunan,
        dogru=sayac["dogru"],
        kucuk_hata=sayac["kucuk_hata"],
        yanlis=yanlis,
        yanlis_orani=(yanlis / okunan) if okunan else 0.0,
        wilson_alt_95=wilson_alt_sinir(yanlis, okunan, z),
        wilson_ust_95=ust,
        hedef=WILSON_HEDEF,
        yeterli_orneklem=yeterli,
        hedef_saglandi=saglandi,
        gecti=yeterli and saglandi,
    )
