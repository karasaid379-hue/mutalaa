# ruff: noqa: RUF001, RUF002
"""Belirtec ve on bolme (Kok ve lemma §5 adim 1-2; K-36 ic kesme listesi).

Bir Turkce metinden lemmatizasyona girecek sozcuk parcalarini ve KOD NOKTASI konumlarini (`[bas,
son)`, yari acik) cikarir. Metin degismez; konumlar verilen dizginin kod noktasi indeksleridir.

Kurallar (her biri `shared/test-vectors/enrich/tr-bolme.jsonl` vektoruyle sinanir):

* sozcuk: harf ve birlesen isaret (L*, M*) dizisi; araya `-` (ya da U+2010, U+2011) ve kesme
  bicimleri girebilir (`rahmet-i`, `Kur'an'in`);
* kesme: sondaki kesmeden sonrasi Turkce ektir (govde `Kur'an`, ek `in`). Ic kesmeli sozcukler
  `shared/data/ic-kesme.txt` listesiyle korunur (genis bicim bir girdiyle basliyorsa o girdideki
  kesme sayisi kadar ilk kesme govdeye aittir);
* izafet: `-i`, `-ı`, `-u`, `-ü`, `-yi`, `-yı`, `-yu`, `-yü` eki onceki sozcuge baglidir ve
  ayrilir (`rahmet-i Ilahiye` -> `rahmet`);
* harf-i tarif: `el-`, `er-`, `es-`, `eş-`, `en-`, `et-`, `ed-`, `ez-` on eki (gunes harfi uyumu
  aranir: `er-` ancak `r` ile baslayan sozcukten once, `el-` her harfle); `-ül` son eki ve
  `ü'l-` bicimi (`Ayetü'l-Kürsi` -> `Ayet` + `Kürsi`);
* ayrilan parcalar (ek, izafet, tarif) sozcuk degildir: lemmatizasyona girmez ve indekse yazilmaz.
"""

import unicodedata
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.normalize.turkish import fold_wide, ic_kesme_listesi, lower_turkish

KESME: Final = "'"
KESME_BICIMLERI: Final = frozenset("'’‘ʼʾʿ´`")
TIRE_BICIMLERI: Final = frozenset("-‐‑")
IZAFET_EKLERI: Final = frozenset({"i", "ı", "u", "ü", "yi", "yı", "yu", "yü"})
# Harf-i tarif on eki -> bir sonraki sozcugun ilk harfi (gunes harfi uyumu); `el` her harfle gelir.
TARIF_ONEKLERI: Final[dict[str, str | None]] = {
    "el": None,
    "er": "r",
    "es": "s",
    "eş": "ş",
    "en": "n",
    "et": "t",
    "ed": "d",
    "ez": "z",
}
TARIF_SONEKLERI: Final = frozenset({"ül", "ûl"})
TARIF_UNLULERI: Final = frozenset({"ü", "u", "i", "ı"})

ROL_EK: Final = "ek"
ROL_IZAFET: Final = "izafet"
ROL_TARIF: Final = "tarif"


@dataclass(frozen=True)
class Parca:
    """Lemmatizasyona girecek sozcuk parcasi; `[bas, son)` kod noktasi araligidir."""

    yuzey: str
    bas: int
    son: int

    @property
    def anahtar(self) -> str:
        """Tur anahtari: Turkce kucuk harf (acik eslemeyle), kesme bicimleri tek `'`."""
        return lower_turkish(kesme_tekle(self.yuzey))

    @property
    def lemmatizer_girdisi(self) -> str:
        """Lemmatizerin gordugu bicim: kesmesiz anahtar (`kur'an` -> `kuran`)."""
        return self.anahtar.replace(KESME, "")


@dataclass(frozen=True)
class Atlanan:
    """Ayrilan, sozcuk olmayan parca (ek, izafet ya da harf-i tarif)."""

    metin: str
    bas: int
    son: int
    rol: str


@dataclass(frozen=True)
class BolmeSonucu:
    parcalar: tuple[Parca, ...]
    atlananlar: tuple[Atlanan, ...]


def kesme_tekle(metin: str) -> str:
    """Yedi kesme bicimini U+0027'ye cevirir (baska hicbir karakter degismez)."""
    return "".join(KESME if k in KESME_BICIMLERI else k for k in metin)


def _sozcuk_karakteri(k: str) -> bool:
    return unicodedata.category(k)[0] in ("L", "M")


def _birlestirici(k: str) -> bool:
    return k in KESME_BICIMLERI or k in TIRE_BICIMLERI


def _kume_sonu(metin: str, bas: int) -> int:
    """`bas`ta baslayan sozcuk kumesinin (harf dizisi + tire/kesme birlestiricileri) sonu."""
    i = bas
    n = len(metin)
    while i < n and (
        _sozcuk_karakteri(metin[i])
        or (_birlestirici(metin[i]) and i + 1 < n and _sozcuk_karakteri(metin[i + 1]))
    ):
        i += 1
    return i


def _ic_kesme_sayisi(segment: str) -> int:
    """Segmentin basindaki ic kesmeli girdinin (en uzun) kesme sayisi; yoksa 0."""
    genis = fold_wide(lower_turkish(kesme_tekle(segment)))
    secilen = ""
    for girdi in ic_kesme_listesi():
        if genis.startswith(girdi) and len(girdi) > len(secilen):
            secilen = girdi
    return secilen.count(KESME)


@dataclass(frozen=True)
class _Segment:
    """Tireler arasi bir parca: govde `[bas, govde_son)`, varsa ek `[govde_son, son)`."""

    bas: int
    govde_son: int
    son: int


def _segmentler(metin: str, bas: int, son: int) -> list[_Segment]:
    sinirlar: list[tuple[int, int]] = []
    ilk = bas
    for i in range(bas, son):
        if metin[i] in TIRE_BICIMLERI:
            sinirlar.append((ilk, i))
            ilk = i + 1
    sinirlar.append((ilk, son))
    sonuc: list[_Segment] = []
    for b, e in sinirlar:
        korunan = _ic_kesme_sayisi(metin[b:e])
        govde_son = e
        for i in range(b, e):
            if metin[i] in KESME_BICIMLERI:
                if korunan > 0:
                    korunan -= 1
                else:
                    govde_son = i
                    break
        sonuc.append(_Segment(b, govde_son, e))
    return sonuc


def _kume_bol(
    metin: str, bas: int, son: int, parcalar: list[Parca], atlananlar: list[Atlanan]
) -> None:
    segmentler = _segmentler(metin, bas, son)
    son_sira = len(segmentler) - 1
    for sira, s in enumerate(segmentler):
        govde = metin[s.bas : s.govde_son]
        kucuk = lower_turkish(govde)
        ek = metin[s.govde_son : s.son]
        sonraki = ""
        if sira < son_sira:
            komsu = segmentler[sira + 1]
            sonraki = lower_turkish(metin[komsu.bas : komsu.govde_son])
        # harf-i tarif on eki: `el-Xxx`, `er-Rxx` (ek yok, arkasindan sozcuk gelir)
        if sira < son_sira and not ek and kucuk in TARIF_ONEKLERI:
            uyum = TARIF_ONEKLERI[kucuk]
            if sonraki and (uyum is None or sonraki.startswith(uyum)):
                atlananlar.append(Atlanan(govde, s.bas, s.govde_son, ROL_TARIF))
                continue
        # izafet eki: `rahmet-i` (onceki sozcuge bagli, tek basina sozcuk degil)
        if sira > 0 and not ek and kucuk in IZAFET_EKLERI:
            atlananlar.append(Atlanan(govde, s.bas, s.govde_son, ROL_IZAFET))
            continue
        # `-ül` son eki: `Beyt-ül-Haram`
        if 0 < sira < son_sira and not ek and kucuk in TARIF_SONEKLERI:
            atlananlar.append(Atlanan(govde, s.bas, s.govde_son, ROL_TARIF))
            continue
        # `Ayetü'l-Kürsi`: govde unlu ile biter, ek yalniz `l`, arkasindan sozcuk gelir
        if (
            sira < son_sira
            and len(govde) > 1
            and lower_turkish(ek[1:]) == "l"
            and kucuk[-1] in TARIF_UNLULERI
        ):
            parcalar.append(Parca(govde[:-1], s.bas, s.govde_son - 1))
            atlananlar.append(
                Atlanan(metin[s.govde_son - 1 : s.son], s.govde_son - 1, s.son, ROL_TARIF)
            )
            continue
        if govde:
            parcalar.append(Parca(govde, s.bas, s.govde_son))
        if ek:
            atlananlar.append(Atlanan(ek, s.govde_son, s.son, ROL_EK))


def bol(metin: str) -> BolmeSonucu:
    """Metnin tum sozcuk parcalarini ve ayrilan parcalari kod noktasi konumlariyla dondurur."""
    parcalar: list[Parca] = []
    atlananlar: list[Atlanan] = []
    i = 0
    n = len(metin)
    while i < n:
        if _sozcuk_karakteri(metin[i]):
            son = _kume_sonu(metin, i)
            _kume_bol(metin, i, son, parcalar, atlananlar)
            i = son
        else:
            i += 1
    return BolmeSonucu(tuple(parcalar), tuple(atlananlar))


def parcalar(metin: str) -> tuple[Parca, ...]:
    """Yalniz lemmatizasyona girecek parcalar (okuma sirasinda)."""
    return bol(metin).parcalar
