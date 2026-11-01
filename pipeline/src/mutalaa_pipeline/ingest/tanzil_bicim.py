"""Tanzil "Text (with aya numbers)" dosya bicimi: kati ayristirma ve yeniden kurma (K-39 madde 7).

VARSAYIM (olculecek: A10): dosya, okuma sirasinda `sure|ayet|metin` satirlarindan ve bunlara
bitisik tek bir bildirim blogundan olusur. Gercek dosya indirilene kadar belgede yazili bicim
yoktur; bu modul bicimin TEK tanimidir (satir deseni, bildirim blogunun yeri). Bildirim onekinin
ne oldugu bilinmez ve sabitlenmez: bildirim blogu, ilk ayet satiri olmayan satirdan dosya sonuna
kadar (bos satirlar dahil) olan baytlardir (`konum = "son"`); dosya bildirimle basliyorsa
(`konum = "bas"`) ilk ayet satirina kadar olan baytlardir. Blogu bulan mantik `bildirim_bul`.

Tanimsiz her durum `GirdiHatasi` (cikis 2) verir. Hata iletileri yalniz satir numarasi, bayt
konumu ve sayi tasir; satir icerigi asla (Icerik hatti §7).

Metin hicbir donusumden gecmez: yalniz `b"\\n"` ile bolunur, her satir kati UTF-8 ile cozulur.
NFC, strip ve splitlines yoktur (K-26). Birim metni dosyanin aynen bir dilimidir.
"""

import hashlib
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Q, format, parse
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi

# --- VARSAYIM (olculecek: A10): ayet satiri oneki -----------------------------------------------
AYET_ONEKI: Final = re.compile(rb"([1-9][0-9]{0,2})\|([1-9][0-9]{0,2})\|")
# Bastaki sifir ya da gecersiz numara tanisi: ayet satirina benzeyen, AYET_ONEKI'ne uymayan satir.
AYET_BENZERI: Final = re.compile(rb"[0-9]+\|[0-9]+\|")
# ------------------------------------------------------------------------------------------------

KONUM_SON: Final = "son"
KONUM_BAS: Final = "bas"
BOM: Final = b"\xef\xbb\xbf"
LF: Final = b"\n"
CR: Final = b"\r"


@dataclass(frozen=True)
class AyetSatiri:
    """Bir ayet satiri. Bayt konumlari dosya basindan; araliklar yari aciktir."""

    sure: int
    ayet: int
    satir: int  # 1 tabanli satir numarasi
    satir_bas: int  # satirin ilk bayti
    satir_son: int  # satirin son baytindan sonrasi (varsa LF dahil)
    bayt_bas: int  # metnin ilk bayti (`s|a|` oneki sonrasi)
    bayt_son: int  # metnin son baytindan sonrasi (LF haric)
    metin: str

    @property
    def capa(self) -> str:
        return format(AnchorRef(Q(self.sure, self.ayet)))


@dataclass(frozen=True)
class Duzen:
    """Dosyanin satir duzeni: sinif ve bayt araliklari, son LF durumu (manifeste yazilir)."""

    konum: str  # "son": ayetler, sonra bildirim; "bas": once bildirim
    son_lf: bool  # dosya LF ile bitiyor mu
    toplam_bayt: int
    ayet_satir: tuple[int, int]  # [ilk, son] 1 tabanli, kapali
    ayet_bayt: tuple[int, int]  # [b, e)
    bildirim_satir: tuple[int, int]
    bildirim_bayt: tuple[int, int]
    bildirim_bos_satir: int

    def sozluk(self) -> dict[str, object]:
        ayet: dict[str, object] = {
            "sinif": "ayet",
            "satir": list(self.ayet_satir),
            "bayt": list(self.ayet_bayt),
        }
        bildirim: dict[str, object] = {
            "sinif": "bildirim",
            "satir": list(self.bildirim_satir),
            "bayt": list(self.bildirim_bayt),
            "bos_satir": self.bildirim_bos_satir,
        }
        siniflar = [ayet, bildirim] if self.konum == KONUM_SON else [bildirim, ayet]
        return {
            "konum": self.konum,
            "son_lf": self.son_lf,
            "toplam_bayt": self.toplam_bayt,
            "siniflar": siniflar,
        }

    @classmethod
    def sozlukten(cls, veri: Mapping[str, object]) -> "Duzen":
        """`sozluk()` ciktisindan geri kurar (manifestten); bicim hatasi `GirdiHatasi`."""
        try:
            konum = veri["konum"]
            son_lf = veri["son_lf"]
            toplam = veri["toplam_bayt"]
            siniflar = veri["siniflar"]
            if (
                konum not in (KONUM_SON, KONUM_BAS)
                or not isinstance(son_lf, bool)
                or not isinstance(toplam, int)
                or not isinstance(siniflar, list)
            ):
                raise KeyError
            tablo: dict[str, Mapping[str, object]] = {}
            for kayit in siniflar:
                if not isinstance(kayit, dict):
                    raise KeyError
                tablo[str(kayit["sinif"])] = kayit
            ayet, bildirim = tablo["ayet"], tablo["bildirim"]
            bos = bildirim["bos_satir"]
            if not isinstance(bos, int):
                raise KeyError
            return cls(
                konum=str(konum),
                son_lf=son_lf,
                toplam_bayt=toplam,
                ayet_satir=_cift(ayet["satir"]),
                ayet_bayt=_cift(ayet["bayt"]),
                bildirim_satir=_cift(bildirim["satir"]),
                bildirim_bayt=_cift(bildirim["bayt"]),
                bildirim_bos_satir=bos,
            )
        except (KeyError, TypeError, ValueError):
            raise GirdiHatasi("satir duzeni kaydi gecersiz") from None


def _cift(deger: object) -> tuple[int, int]:
    if (
        isinstance(deger, list)
        and len(deger) == 2
        and all(isinstance(x, int) and not isinstance(x, bool) for x in deger)
    ):
        return (int(deger[0]), int(deger[1]))
    raise ValueError


@dataclass(frozen=True)
class Ayrisma:
    ayetler: tuple[AyetSatiri, ...]
    bildirim: bytes  # dosyadaki bildirim blogunun baytlari, aynen
    metin_baytlari: bytes  # ayet satirlarinin ham baytlari (her biri kendi LF'siyle)
    duzen: Duzen

    @property
    def metin_sha256(self) -> str:
        return hashlib.sha256(self.metin_baytlari).hexdigest()

    @property
    def bildirim_sha256(self) -> str:
        return hashlib.sha256(self.bildirim).hexdigest()


def sure_basina_toplam(sure_tablosu: Sequence[int]) -> int:
    return sum(sure_tablosu)


def sonraki(sure: int, ayet: int, sure_tablosu: Sequence[int]) -> tuple[int, int] | None:
    """Okuma sirasinda sonraki (sure, ayet); son ayetten sonra None."""
    if ayet < sure_tablosu[sure - 1]:
        return (sure, ayet + 1)
    if sure < len(sure_tablosu):
        return (sure + 1, 1)
    return None


def _satir_no(veri: bytes, konum: int) -> int:
    return veri.count(LF, 0, konum) + 1


def ayet_satiri_mi(satir: bytes) -> bool:
    return AYET_ONEKI.match(satir) is not None


def bildirim_bul(siniflar: Sequence[bool]) -> tuple[str, int, int]:
    """Bildirim blogunun yeri: (konum, ilk_satir_indeksi, son_satir_indeksi_dahil_degil).

    `siniflar[i]` i. satirin ayet satiri olup olmadigidir. Bildirim blogu, ilk ayet satiri
    olmayan satirdan dosya sonuna kadardir (`konum="son"`); ilk satir ayet satiri degilse blok
    dosya basindan ilk ayet satirina kadardir (`konum="bas"`). Bu, bicimin VARSAYIMIDIR
    (olculecek: A10); yalniz bu islev degisir.
    """
    sayi = len(siniflar)
    if sayi == 0:
        raise GirdiHatasi("dosya bos")
    if siniflar[0]:
        for i, ayet in enumerate(siniflar):
            if not ayet:
                return (KONUM_SON, i, sayi)
        return (KONUM_SON, sayi, sayi)  # bildirim yok
    for i, ayet in enumerate(siniflar):
        if ayet:
            return (KONUM_BAS, 0, i)
    return (KONUM_BAS, 0, sayi)  # ayet yok


def ayristir(
    veri: bytes,
    sure_tablosu: Sequence[int] = AYET_SAYILARI,
    *,
    tam: bool = True,
) -> Ayrisma:
    """Dosyayi kati bicimde ayristirir; tanimsiz her sey `GirdiHatasi` (cikis 2).

    `tam=False` okuma sirasinin `1|1`'den kesintisiz olmasini ister ama sure tablosunun sonuna
    kadar gitmeyi istemez (fikstur parcalari icin). Tanzil alimi her zaman `tam=True` kullanir.
    """
    if veri.startswith(BOM):
        raise GirdiHatasi("BOM var (bayt 0)")
    if CR in veri:
        ilk = veri.index(CR)
        raise GirdiHatasi(
            f"CR (0x0D) var: ilk bayt {ilk}, satir {_satir_no(veri, ilk)}, toplam {veri.count(CR)}"
        )
    satirlar = veri.split(LF)
    son_lf = veri.endswith(LF)
    if son_lf:
        satirlar.pop()
    if not satirlar:
        raise GirdiHatasi("dosya bos")

    baslangiclar: list[int] = []
    konum_bayt = 0
    for satir in satirlar:
        baslangiclar.append(konum_bayt)
        konum_bayt += len(satir) + 1

    siniflar = [ayet_satiri_mi(s) for s in satirlar]
    konum, bildirim_ilk, bildirim_son = bildirim_bul(siniflar)
    # Bildirim blogu disindaki her satir ayet satiri olmali; icindeki hicbiri ayete benzememeli.
    if konum == KONUM_SON:
        ayet_araligi = range(0, bildirim_ilk)
    else:
        ayet_araligi = range(bildirim_son, len(satirlar))
    for i in range(len(satirlar)):
        if i in ayet_araligi:
            if not siniflar[i]:
                raise GirdiHatasi(
                    f"satir {i + 1}: tanimsiz satir (ayet bolgesinde ayet satiri degil)"
                )
        elif AYET_BENZERI.match(satirlar[i]) is not None:
            raise GirdiHatasi(
                f"satir {i + 1}: tanimsiz satir (baslangic sifir, gecersiz numara ya da "
                "bildirim blogunda ayet benzeri satir)"
            )
    if len(ayet_araligi) == 0:
        raise GirdiHatasi("ayet satiri yok")

    sonda_lf_yok = konum == KONUM_BAS and not son_lf
    ayetler = _ayetleri_oku(veri, satirlar, baslangiclar, ayet_araligi, sonda_lf_yok, sure_tablosu)
    if tam and len(ayetler) != sure_basina_toplam(sure_tablosu):
        raise GirdiHatasi(
            f"ayet sayisi eksik: beklenen {sure_basina_toplam(sure_tablosu)},"
            f" bulunan {len(ayetler)}"
        )

    bildirim_bas = baslangiclar[bildirim_ilk] if bildirim_ilk < len(satirlar) else len(veri)
    bildirim_bitis = len(veri) if konum == KONUM_SON else baslangiclar[bildirim_son]
    bildirim = veri[bildirim_bas:bildirim_bitis]
    if not bildirim:
        raise GirdiHatasi("bildirim blogu yok")
    try:
        bildirim.decode("utf-8")
    except UnicodeDecodeError as hata:
        raise GirdiHatasi(
            f"bildirim blogu gecersiz UTF-8 (bayt {bildirim_bas + hata.start})"
        ) from None

    ayet_bas = ayetler[0].satir_bas
    ayet_bitis = ayetler[-1].satir_son
    bildirim_satirlari = range(bildirim_ilk, bildirim_son)
    duzen = Duzen(
        konum=konum,
        son_lf=son_lf,
        toplam_bayt=len(veri),
        ayet_satir=(ayetler[0].satir, ayetler[-1].satir),
        ayet_bayt=(ayet_bas, ayet_bitis),
        bildirim_satir=(bildirim_satirlari[0] + 1, bildirim_satirlari[-1] + 1),
        bildirim_bayt=(bildirim_bas, bildirim_bitis),
        bildirim_bos_satir=sum(1 for i in bildirim_satirlari if satirlar[i] == b""),
    )
    return Ayrisma(
        ayetler=tuple(ayetler),
        bildirim=bildirim,
        metin_baytlari=veri[ayet_bas:ayet_bitis],
        duzen=duzen,
    )


def _ayetleri_oku(
    veri: bytes,
    satirlar: Sequence[bytes],
    baslangiclar: Sequence[int],
    araligi: range,
    sonda_lf_yok: bool,
    sure_tablosu: Sequence[int],
) -> list[AyetSatiri]:
    beklenen: tuple[int, int] | None = (1, 1)
    sonuc: list[AyetSatiri] = []
    for i in araligi:
        satir = satirlar[i]
        eslesme = AYET_ONEKI.match(satir)
        if eslesme is None:  # ayristir() zaten eler; savunma
            raise GirdiHatasi(f"satir {i + 1}: tanimsiz satir")
        sure, ayet = int(eslesme.group(1)), int(eslesme.group(2))
        if beklenen is None or (sure, ayet) != beklenen:
            raise GirdiHatasi(f"satir {i + 1}: sira disi numara (okuma sirasi bozuk)")
        beklenen = sonraki(sure, ayet, sure_tablosu)
        bas = baslangiclar[i]
        metin_bas = bas + eslesme.end()
        metin_son = bas + len(satir)
        son_satir = i == araligi[-1]
        satir_son = metin_son + (0 if (son_satir and sonda_lf_yok) else 1)
        if metin_son == metin_bas:
            raise GirdiHatasi(f"satir {i + 1}: bos metin")
        try:
            metin = veri[metin_bas:metin_son].decode("utf-8")
        except UnicodeDecodeError as hata:
            raise GirdiHatasi(
                f"satir {i + 1}: gecersiz UTF-8 (bayt {metin_bas + hata.start})"
            ) from None
        sonuc.append(
            AyetSatiri(
                sure=sure,
                ayet=ayet,
                satir=i + 1,
                satir_bas=bas,
                satir_son=satir_son,
                bayt_bas=metin_bas,
                bayt_son=metin_son,
                metin=metin,
            )
        )
    return sonuc


def metin_baytlari(
    ham: bytes, sure_tablosu: Sequence[int] = AYET_SAYILARI, *, tam: bool = True
) -> bytes:
    """Ayet satirlarinin ham baytlari, her biri kendi LF'siyle. Ozeti kilitteki `metin_sha256`."""
    return ayristir(ham, sure_tablosu, tam=tam).metin_baytlari


def _ayet_baytlari(birimler: Iterable[tuple[str, str]], duzen: Duzen) -> bytes:
    parcalar: list[bytes] = []
    for capa, metin in birimler:
        try:
            ref = parse(capa)
        except AnchorError:
            raise GirdiHatasi("capa gecersiz (yeniden kurma)") from None
        if not isinstance(ref.anchor, Q) or ref.anchor.ilk is not None or ref.span is not None:
            raise GirdiHatasi("capa bir ayet capasi degil (yeniden kurma)")
        parcalar.append(
            f"{ref.anchor.sure}|{ref.anchor.ayet}|".encode("ascii") + metin.encode("utf-8") + LF
        )
    if parcalar and duzen.konum == KONUM_BAS and not duzen.son_lf:
        parcalar[-1] = parcalar[-1][:-1]
    return b"".join(parcalar)


def yeniden_kur(birimler: Iterable[tuple[str, str]], bildirim: bytes, duzen: Duzen) -> bytes:
    """Dosyanin tamamini kurar. `birimler` okuma sirasinda `(capa, metin)` ciftleridir.

    Ozeti kilitteki `sha256`'dir. Ayet satirlari `{sure}|{ayet}|{metin}` + LF'dir (baslangic
    sifir reddedildigi icin onek kanoniktir); bildirim aynen, `duzen.konum` yerine konur.
    """
    ayetler = _ayet_baytlari(birimler, duzen)
    return ayetler + bildirim if duzen.konum == KONUM_SON else bildirim + ayetler
