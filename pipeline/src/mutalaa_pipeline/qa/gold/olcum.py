"""Olcum yardimcilari (A18.5): prf, aciklik esleme, kappa, gerileme kurali ve kapi esikleri.

Saf islevler; veritabani, dosya ve yapilandirma yok.

PRF: `prf(tahmin, referans)` kumeler uzerinde kesinlik, duyarlilik ve F1 verir; hesap
scikit-learn `precision_recall_fscore_support` ile yapilir (ikili etiket, `zero_division=1.0`).
Sifira bolme kurallari (Test stratejisi §4 kod parcasiyla ayni): tahmin kumesi bos ise kesinlik 1,0;
referans kumesi bos ise duyarlilik 1,0; ikisi de bos ise (1, 1, 1); F1 = 0 yalniz `p + r = 0` iken
(sklearn `2tp / (2tp + fp + fn)` ile ayni).

ACIKLIK ESLEME: aciklik `[bas, son)` yari acik kod noktasi araligidir. `iou` kesisim / birlesim.
Tahmin, referans bir ACIKLIGIN kabul edilen hedeflerinden birini tasiyorsa ve IoU >= 0,5 ise o
referansi bulmus sayilir (K-51; Iktibas tespiti §10: "ayni hedef ve ortusme >= 0,5"). Kesinlik
tahminler uzerinden (`en az bir referansla eslesen tahmin / tahmin`), duyarlilik referanslar
uzerinden (`en az bir tahminle eslesen referans / referans`) hesaplanir; bir referans birden cok
gecerli hedef tasiyabildigi icin (metinde ayni dizi birden cok ayette gecer) birebir eslesme
aranmaz.

KAPPA: `kappa_sklearn` scikit-learn `cohen_kappa_score` kullanir; `qa/uyum.cohen_kappa` (A17,
`Fraction`) ile ayni sonucu verir (test). Tek kategori durumunda sklearn nan verir: uyum.py gibi
1,0 doner ve `tek_kategori` isaretlenir.

GERILEME: onceki kabul edilmis kosuya (ayni tur, son `gecti` raporu) gore herhangi bir olcu 0,02'den
fazla duserse kosu kirilir (cikis 1; Test stratejisi §4 onerisi).
"""

from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from sklearn.metrics import (  # type: ignore[import-untyped]
    cohen_kappa_score,
    precision_recall_fscore_support,
)

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.uyum import cohen_kappa

IOU_ESIGI: Final = 0.5
GERILEME_ESIGI: Final = 0.02
GECTI: Final = "gecti"
KALDI: Final = "kaldi"


# --- prf ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class Prf:
    kesinlik: float
    duyarlilik: float
    f1: float
    tp: int
    fp: int
    fn: int

    def sozluk(self) -> dict[str, float | int]:
        return {
            "kesinlik": round(self.kesinlik, 6),
            "duyarlilik": round(self.duyarlilik, 6),
            "f1": round(self.f1, 6),
            "dp": self.tp,
            "yp": self.fp,
            "yn": self.fn,
        }


def prf(tahmin: Iterable[Hashable], referans: Iterable[Hashable]) -> Prf:
    """Kume duzeyinde kesinlik, duyarlilik, F1 (scikit-learn; sifira bolme kurallari modulde)."""
    t, r = set(tahmin), set(referans)
    tp, fp, fn = len(t & r), len(t - r), len(r - t)
    evren = sorted(t | r, key=repr)
    if not evren:
        return Prf(1.0, 1.0, 1.0, 0, 0, 0)
    y_gercek = [1 if x in r else 0 for x in evren]
    y_tahmin = [1 if x in t else 0 for x in evren]
    p, rc, f, _ = precision_recall_fscore_support(
        y_gercek, y_tahmin, average="binary", pos_label=1, zero_division=1.0
    )
    return Prf(float(p), float(rc), float(f), tp, fp, fn)


def prf_sayimdan(tp_tahmin: int, tahmin: int, tp_referans: int, referans: int) -> Prf:
    """Eslesme sayilarindan (aciklik esleme) PRF; sifira bolme: bos taraf 1,0.

    `tp_tahmin`: referansla eslesen tahmin sayisi; `tp_referans`: tahminle eslesen referans sayisi.
    F1 = 0 yalniz `p + r = 0` iken.
    """
    if not 0 <= tp_tahmin <= tahmin or not 0 <= tp_referans <= referans:
        raise GirdiHatasi("prf sayimlari tutarsiz")
    p = tp_tahmin / tahmin if tahmin else 1.0
    r = tp_referans / referans if referans else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return Prf(p, r, f, tp_tahmin, tahmin - tp_tahmin, referans - tp_referans)


# --- aciklik esleme ----------------------------------------------------------------------


@dataclass(frozen=True)
class TahminAciklik:
    hedef: str
    bas: int
    son: int


@dataclass(frozen=True)
class ReferansAciklik:
    hedefler: frozenset[str]  # kabul edilen hedefler (ayni dizinin gectigi butun ayetler)
    bas: int
    son: int


def iou(a_bas: int, a_son: int, b_bas: int, b_son: int) -> float:
    """Yari acik iki aralik icin kesisim / birlesim; gecersiz aralikta `GirdiHatasi`."""
    if not (0 <= a_bas < a_son and 0 <= b_bas < b_son):
        raise GirdiHatasi("aralik gecersiz: 0 <= bas < son olmali")
    kesisim = max(0, min(a_son, b_son) - max(a_bas, b_bas))
    birlesim = (a_son - a_bas) + (b_son - b_bas) - kesisim
    return kesisim / birlesim


def eslesir(t: TahminAciklik, r: ReferansAciklik, esik: float = IOU_ESIGI) -> bool:
    return t.hedef in r.hedefler and iou(t.bas, t.son, r.bas, r.son) >= esik


@dataclass(frozen=True)
class AciklikSonucu:
    tahmin: int
    referans: int
    tahmin_eslesen: tuple[bool, ...]  # tahmin sirasinda
    referans_eslesen: tuple[bool, ...]  # referans sirasinda

    def prf(
        self,
        tahmin_secim: Sequence[bool] | None = None,
        referans_secim: Sequence[bool] | None = None,
    ) -> Prf:
        """Tahminler ve referanslar icin ayri kesitler (ornegin uzun / kisa) secilebilir."""
        ts = tahmin_secim if tahmin_secim is not None else [True] * self.tahmin
        rs = referans_secim if referans_secim is not None else [True] * self.referans
        t_n = sum(1 for s in ts if s)
        r_n = sum(1 for s in rs if s)
        t_tp = sum(1 for s, e in zip(ts, self.tahmin_eslesen, strict=True) if s and e)
        r_tp = sum(1 for s, e in zip(rs, self.referans_eslesen, strict=True) if s and e)
        return prf_sayimdan(t_tp, t_n, r_tp, r_n)


def aciklik_esle(
    tahminler: Sequence[TahminAciklik],
    referanslar: Sequence[ReferansAciklik],
    esik: float = IOU_ESIGI,
) -> AciklikSonucu:
    """Tahmin ve referans aciklik listelerini eslestirir (modul belgesindeki kural)."""
    t_ok = [False] * len(tahminler)
    r_ok = [False] * len(referanslar)
    for i, t in enumerate(tahminler):
        for j, r in enumerate(referanslar):
            if eslesir(t, r, esik):
                t_ok[i] = True
                r_ok[j] = True
    return AciklikSonucu(len(tahminler), len(referanslar), tuple(t_ok), tuple(r_ok))


# --- kappa -------------------------------------------------------------------------------


@dataclass(frozen=True)
class KappaSonucu:
    n: int
    kappa: float
    kappa_uyum_py: float  # qa/uyum.cohen_kappa (Fraction) ile ayni olmali
    tek_kategori: bool


def kappa_sklearn(a: Sequence[str], b: Sequence[str]) -> KappaSonucu:
    """Cohen kappa (scikit-learn); bos ya da uzunluklari farkli listede `GirdiHatasi`."""
    if not a or len(a) != len(b):
        raise GirdiHatasi("kappa icin esit uzunlukta, bos olmayan iki liste gerekir")
    uyum_py = cohen_kappa(a, b)
    tek = len(set(a) | set(b)) == 1
    deger = 1.0 if tek else float(cohen_kappa_score(list(a), list(b)))
    return KappaSonucu(len(a), deger, uyum_py, tek)


# --- gerileme ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Gerileme:
    olcu: str
    onceki: float
    simdiki: float


def gerilemeleri_bul(
    onceki: Mapping[str, float] | None,
    simdiki: Mapping[str, float],
    esik: float = GERILEME_ESIGI,
) -> list[Gerileme]:
    """Her iki kosuda da bulunan olculerden `onceki - simdiki > esik` olanlar (sirali).

    `onceki` yoksa (ilk kosu) gerileme yoktur. Karsilastirma 1e-9 payla yapilir (kayan nokta).
    """
    if onceki is None:
        return []
    return [
        Gerileme(ad, onceki[ad], simdiki[ad])
        for ad in sorted(onceki.keys() & simdiki.keys())
        if onceki[ad] - simdiki[ad] > esik + 1e-9
    ]


# --- kapi esikleri -----------------------------------------------------------------------

# tur -> {olcu adi: alt sinir}; `>=` ile karsilastirilir (Test stratejisi §4 tablosu).
ESIKLER: Final[Mapping[str, Mapping[str, float]]] = {
    "kok": {"kesinlik": 0.95, "duyarlilik": 0.80},
    "lemma": {"tutarlilik": 1.0},
    "benzer_ayet": {"kesinlik": 0.90},
    "atif": {"kesinlik": 0.98, "duyarlilik": 0.90},
    "iktibas_uzun": {"kesinlik": 0.95, "duyarlilik": 0.85},
    "iktibas_kisa": {"kesinlik": 0.85},
}


def esik_degerlendir(esikler: Mapping[str, float], olculer: Mapping[str, float]) -> dict[str, bool]:
    """Her esik icin `olcu >= esik` (eksik olcu `GirdiHatasi`); kayan nokta icin 1e-12 payi."""
    sonuc: dict[str, bool] = {}
    for ad, alt in esikler.items():
        if ad not in olculer:
            raise GirdiHatasi(f"kapi olcusu eksik: {ad}")
        sonuc[ad] = olculer[ad] >= alt - 1e-12
    return sonuc


def kapi_karari(esikler: Mapping[str, float], olculer: Mapping[str, float]) -> str:
    """`gecti` yalniz her esik tutuyorsa; aksi halde `kaldi`."""
    return GECTI if all(esik_degerlendir(esikler, olculer).values()) else KALDI
