# ruff: noqa: RUF001, RUF002, RUF003
"""Belirtec ve on bolme (Kok ve lemma §5 adim 1-2; K-36 ic kesme listesi).

Bir Turkce metinden lemmatizasyona girecek sozcuk parcalarini ve KOD NOKTASI konumlarini (`[bas,
son)`, yari acik) cikarir. Metin degismez; konumlar verilen dizginin kod noktasi indeksleridir.

Kurallar (her biri `shared/test-vectors/enrich/tr-bolme.jsonl` vektoruyle sinanir):

* sozcuk: harf ve birlesen isaret (L*, M*) dizisi; araya `-` (ya da U+2010, U+2011) ve kesme
  bicimleri girebilir (`rahmet-i`, `Kur'an'in`);
* kesme: kesmeden sonrasi GERCEKTEN Turkce ek zinciri ise ektir (govde `Kur'an`, ek `in`); degilse
  kesme sozcugun icindedir ve sozcuk butun kalir. Ic kesmeli sozcukler `shared/data/ic-kesme.txt`
  listesiyle korunur (genis bicim bir girdiyle basliyorsa o girdideki kesme sayisi kadar ilk kesme
  govdeye aittir); listede olmayan ic kesmeli sozcukler (Arapca kokenli) ek zinciri sinamasiyla
  korunur (`ek_zinciri_mi`: asagida);
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


# --- Turkce ek zinciri sinamasi ------------------------------------------------------------
#
# Kesmeden sonrasi ancak su kucuk, belgeli dilbilgisiyle TAMAMEN tuketilebiliyorsa ek zinciridir.
# Sira (her bolum bos olabilir): cogul `lAr`; iyelik `(I)m, (I)n, (s)I, (I)mIz, (I)nIz`; hal
# (belirtme `(y|n)I`, yonelme `(y|n)A`, bulunma `(n)DA`, ayrilma `(n)DAn`, tamlayan `(n)In`,
# vasita `(y)lA`); bildirme (`DIr`, `(y)DI`, `(y)mIş`, `(y)ken`, `(y)sA`); ilgi `ki`.
# `A` e/a, `I` i/ı/u/ü (unlu uyumu SON unluye gore, her ekten sonra yeniden hesaplanir); `D` d/t
# (sert unsuz uyumu aranmaz). Kaynasma harfi `y`/`n`/`s` yalniz unluyle biten govdeden sonra gelir,
# 3. kisi iyeliginden sonra hal eki `n` alir. Kesmeden sonrasinda en az bir unlu bulunmalidir
# (`'m`, `'n` gibi tek unsuzlu parcalar ek sayilmaz). Sapkali unluler (`â`, `û`) iki uyumdan
# birine uyabilir, `î` ince sayilir. Ek sonrasindaki baska kesmeler yok sayilir (`'lar'ın`).

_UNLULER: Final = frozenset("aeıioöuüâîû")
_UNLU_UYUMU: Final[dict[str, tuple[str, ...]]] = {
    "a": ("a",),
    "ı": ("ı",),
    "o": ("o",),
    "u": ("u",),
    "e": ("e",),
    "i": ("i",),
    "ö": ("ö",),
    "ü": ("ü",),
    "â": ("a", "e"),
    "î": ("i",),
    "û": ("u", "ü"),
}
_DUZ_UNLU: Final = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}
_ARKA_UNLULER: Final = frozenset("aıou")
_EK_SIRALARI: Final = 5  # cogul, iyelik, hal, bildirme, ilgi


def _ek_yuzeyleri(
    sira: int, son_unlu: str, unluyle_bitiyor: bool, ucuncu_iyelik: bool
) -> list[tuple[str, bool]]:
    """`(yuzey, ucuncu_kisi_iyeligi_mi)` ciftleri; bir bolumun olasi yuzey bicimleri."""
    a = "a" if son_unlu in _ARKA_UNLULER else "e"
    i = _DUZ_UNLU[son_unlu]
    ek: list[tuple[str, bool]] = []
    if sira == 0:
        ek.append(("l" + a + "r", False))
    elif sira == 1:
        if unluyle_bitiyor:
            ek += [("m", False), ("n", False), ("s" + i, True)]
            ek += [("m" + i + "z", False), ("n" + i + "z", False)]
        else:
            ek += [(i + "m", False), (i + "n", False), (i, True)]
            ek += [(i + "m" + i + "z", False), (i + "n" + i + "z", False)]
    elif sira == 2:
        tampon = "n" if ucuncu_iyelik else ("y" if unluyle_bitiyor else "")
        ek += [(tampon + i, False), (tampon + a, False)]
        n_tamponu = "n" if ucuncu_iyelik else ""
        for d in ("d", "t"):
            ek += [(n_tamponu + d + a, False), (n_tamponu + d + a + "n", False)]
        ek.append((("n" + i + "n") if ucuncu_iyelik or unluyle_bitiyor else (i + "n"), False))
        ek.append((("y" if ucuncu_iyelik or unluyle_bitiyor else "") + "l" + a, False))
    elif sira == 3:
        tampon = "y" if unluyle_bitiyor else ""
        for d in ("d", "t"):
            ek += [(d + i + "r", False), (tampon + d + i, False)]
        ek += [(tampon + "m" + i + "ş", False), (tampon + "ken", False), (tampon + "s" + a, False)]
    else:
        ek.append(("ki", False))
    return ek


def _zincir_tuketir(
    ek: str, konum: int, sira: int, son_unlu: str, unluyle_bitiyor: bool, ucuncu_iyelik: bool
) -> bool:
    if konum == len(ek):
        return True
    for s in range(sira, _EK_SIRALARI):
        for yuzey, ucuncu in _ek_yuzeyleri(s, son_unlu, unluyle_bitiyor, ucuncu_iyelik):
            if not ek.startswith(yuzey, konum):
                continue
            unluler = [k for k in yuzey if k in _UNLULER]
            yeni_unlu = unluler[-1] if unluler else son_unlu
            if _zincir_tuketir(
                ek, konum + len(yuzey), s + 1, yeni_unlu, yuzey[-1] in _UNLULER, ucuncu
            ):
                return True
    return False


def ek_zinciri_mi(govde: str, kalan: str) -> bool:
    """`kalan` (kesmeden sonrasi), `govde` ile birlikte Turkce ek zinciri mi? Bkz. bolumun basi."""
    g = lower_turkish(kesme_tekle(govde)).replace(KESME, "")
    ek = lower_turkish(kesme_tekle(kalan)).replace(KESME, "")
    if not any(k in _UNLULER for k in ek):
        return False
    unluler = [k for k in g if k in _UNLULER]
    adaylar = _UNLU_UYUMU[unluler[-1]] if unluler else ("a", "e", "o", "ö")
    bitis_unlu = bool(g) and g[-1] in _UNLULER
    return any(_zincir_tuketir(ek, 0, 0, u, bitis_unlu, False) for u in adaylar)


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


def _tarif_l_mi(metin: str, bas: int, kesme: int, e: int, son: int) -> bool:
    """`Ayetü'l-Kürsi` bicimi: unlu ile biten govde, kesme, yalniz `l`, arkasindan tire gelir."""
    return (
        e < son
        and kesme - bas > 1
        and lower_turkish(metin[kesme + 1 : e]) == "l"
        and lower_turkish(metin[kesme - 1]) in TARIF_UNLULERI
    )


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
                elif _tarif_l_mi(metin, b, i, e, son) or ek_zinciri_mi(
                    metin[b:i], metin[i + 1 : e]
                ):
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
