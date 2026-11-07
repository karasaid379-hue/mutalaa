"""Tanzil "Text (with aya numbers)" dosya bicimi: kati ayristirma ve yeniden kurma (K-39 madde 7).

Olculen duzen (2 Kasim 2026; Uthmani ve Simple Clean, ikisi de "Version 1.1"; form: marks, sajdah
ve tatweel acik, rub ve stanween kapali). Dosya 6.266 satirdir, her satir LF ile biter, CR ve BOM
yoktur:

    <sure>|<ayet>|<metin> LF     6.236 ayet satiri (1-6.236. satirlar), okuma sirasinda 1|1'den
                                 114|6'ya kesintisiz; sure ve ayet numarasi 1-3 hane, bastaki
                                 sifir yok
    LF LF                        2 bos satir (6.237-6.238. satirlar)
    # ... LF                     28 '#' satiri (6.239-6.266. satirlar)

Bildirim blogu, ayet bolgesinin hemen ardindan dosya sonuna kadar olan baytlardir (6.237-6.266.
satirlar, `konum = "son"`); icinde yalniz bos ve '#' ile baslayan satirlar bulunur. Dosyayi bu
kosullarin disinda kalan her sey (CR, BOM, sonda LF yok, ayet bolgesinde bos ya da tanimsiz
satir, numara atlamasi ya da tekrari, bildirimsiz dosya) `GirdiHatasi` (cikis 2) verir. Bu modul
bicimin TEK tanimidir (satir deseni, bildirim blogunun yeri); kilit (`tanzil.lock.json`) ayet
satirlarinin (`metin_sha256`) ve bildirim blogunun (`bildirim_sha256`) ozetini ayri tutar.

Hata iletileri yalniz satir numarasi, bayt konumu ve sayi tasir; satir icerigi asla (Icerik
hatti §7).

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

# Ayet satiri oneki: bastaki sifir kabul edilmez (kanonik cikis `{sure}|{ayet}|` yeniden kurulur).
AYET_ONEKI: Final = re.compile(rb"([1-9][0-9]{0,2})\|([1-9][0-9]{0,2})\|")
# Bastaki sifir ya da gecersiz numara tanisi: ayet satirina benzeyen, AYET_ONEKI'ne uymayan satir.
AYET_BENZERI: Final = re.compile(rb"[0-9]+\|[0-9]+\|")
# Bildirim blogundaki baslik satiri: `#  Tanzil Quran Text (Uthmani, Version 1.1)`.
BASLIK_DESENI: Final = re.compile(
    rb"^#[ ]+Tanzil Quran Text \((?P<tur>[A-Za-z]+(?: [A-Za-z]+)*), "
    rb"Version (?P<surum>[0-9]+(?:\.[0-9]+)*)\)[ ]*$",
    re.MULTILINE,
)

KONUM_SON: Final = "son"
BOM: Final = b"\xef\xbb\xbf"
LF: Final = b"\n"
CR: Final = b"\r"
DIYEZ: Final = b"#"


@dataclass(frozen=True)
class AyetSatiri:
    """Bir ayet satiri. Bayt konumlari dosya basindan; araliklar yari aciktir."""

    sure: int
    ayet: int
    satir: int  # 1 tabanli satir numarasi
    satir_bas: int  # satirin ilk bayti
    satir_son: int  # satirin son baytindan sonrasi (LF dahil)
    bayt_bas: int  # metnin ilk bayti (`s|a|` oneki sonrasi)
    bayt_son: int  # metnin son baytindan sonrasi (LF haric)
    metin: str

    @property
    def capa(self) -> str:
        return format(AnchorRef(Q(self.sure, self.ayet)))


@dataclass(frozen=True)
class Duzen:
    """Dosyanin satir duzeni: sinif ve bayt araliklari, son LF durumu (manifeste yazilir).

    Olculen bicimde `konum` her zaman "son" (ayetler, sonra bildirim) ve `son_lf` her zaman
    dogrudur; alanlar manifestin kendini betimlemesi icin tutulur.
    """

    konum: str
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
        return {
            "konum": self.konum,
            "son_lf": self.son_lf,
            "toplam_bayt": self.toplam_bayt,
            "siniflar": [ayet, bildirim],
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
                konum != KONUM_SON
                or son_lf is not True
                or not isinstance(toplam, int)
                or isinstance(toplam, bool)
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
            if not isinstance(bos, int) or isinstance(bos, bool):
                raise KeyError
            return cls(
                konum=KONUM_SON,
                son_lf=True,
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


def bildirim_bul(siniflar: Sequence[bool]) -> int:
    """Bildirim blogunun ilk satirinin 0 tabanli indeksi.

    `siniflar[i]` i. satirin ayet satiri olup olmadigidir. Ayet bolgesi dosya basindan itibaren
    kesintisiz ayet satirlaridir; bildirim blogu, ilk ayet satiri olmayan satirdan dosya sonuna
    kadardir (`konum = "son"`). Ayet olmayan satir yoksa `len(siniflar)` doner (bildirim yok).
    """
    for i, ayet in enumerate(siniflar):
        if not ayet:
            return i
    return len(siniflar)


def bildirim_basligi(bildirim: bytes) -> tuple[str, str]:
    """Bildirim blogundaki baslik satirindan `(tur, surum)`: `("Uthmani", "1.1")`.

    Baslik satiri tam bir kez bulunmalidir; aksi halde `GirdiHatasi`.
    """
    bulunan = BASLIK_DESENI.findall(bildirim)
    if len(bulunan) != 1:
        raise GirdiHatasi(f"bildirim basligi cozulemedi (eslesme sayisi {len(bulunan)})")
    tur, surum = bulunan[0]
    return tur.decode("ascii"), surum.decode("ascii")


def _bildirim_denetle(satirlar: Sequence[bytes], ilk: int) -> None:
    """`ilk` indeksinden sonuna kadar yalniz bos ve '#' satirlari; en az bir '#' satiri."""
    diyez = 0
    for i in range(ilk, len(satirlar)):
        satir = satirlar[i]
        if AYET_BENZERI.match(satir) is not None:
            if i == ilk:
                raise GirdiHatasi(
                    f"satir {i + 1}: tanimsiz satir (ayet numarasi gecersiz: baslangic sifir"
                    " ya da uc haneden uzun)"
                )
            raise GirdiHatasi(
                f"satir {i + 1}: ayet bolgesi kesildi (ilk ayet olmayan satir {ilk + 1}),"
                " ardindan ayet satiri geldi"
            )
        if satir == b"":
            continue
        if satir.startswith(DIYEZ):
            diyez += 1
            continue
        raise GirdiHatasi(
            f"satir {i + 1}: tanimsiz satir (ayet bolgesinde ayet satiri degil, bildirim"
            " blogunda bos ya da '#' satiri degil)"
        )
    if diyez == 0:
        raise GirdiHatasi("bildirim blogu yok (ayet bolgesinden sonra '#' satiri yok)")


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
    if not veri:
        raise GirdiHatasi("dosya bos")
    if not veri.endswith(LF):
        raise GirdiHatasi(f"dosya LF ile bitmiyor (son bayt {len(veri) - 1})")
    satirlar = veri.split(LF)
    satirlar.pop()  # son LF'den sonraki bos parca

    baslangiclar: list[int] = []
    konum_bayt = 0
    for satir in satirlar:
        baslangiclar.append(konum_bayt)
        konum_bayt += len(satir) + 1

    ayet_sayisi = bildirim_bul([ayet_satiri_mi(s) for s in satirlar])
    if ayet_sayisi == 0:
        raise GirdiHatasi("ayet satiri yok (dosya ayet satiriyla baslamiyor)")
    if ayet_sayisi == len(satirlar):
        raise GirdiHatasi("bildirim blogu yok (ayet satirlarindan sonra satir yok)")
    _bildirim_denetle(satirlar, ayet_sayisi)

    ayetler = _ayetleri_oku(veri, satirlar, baslangiclar, ayet_sayisi, sure_tablosu)
    if tam and len(ayetler) != sure_basina_toplam(sure_tablosu):
        raise GirdiHatasi(
            f"ayet sayisi eksik: beklenen {sure_basina_toplam(sure_tablosu)},"
            f" bulunan {len(ayetler)}"
        )

    bildirim_bas = baslangiclar[ayet_sayisi]
    bildirim = veri[bildirim_bas:]
    try:
        bildirim.decode("utf-8")
    except UnicodeDecodeError as hata:
        raise GirdiHatasi(
            f"bildirim blogu gecersiz UTF-8 (bayt {bildirim_bas + hata.start})"
        ) from None

    ayet_bitis = ayetler[-1].satir_son
    duzen = Duzen(
        konum=KONUM_SON,
        son_lf=True,
        toplam_bayt=len(veri),
        ayet_satir=(ayetler[0].satir, ayetler[-1].satir),
        ayet_bayt=(0, ayet_bitis),
        bildirim_satir=(ayet_sayisi + 1, len(satirlar)),
        bildirim_bayt=(bildirim_bas, len(veri)),
        bildirim_bos_satir=sum(1 for s in satirlar[ayet_sayisi:] if s == b""),
    )
    return Ayrisma(
        ayetler=tuple(ayetler),
        bildirim=bildirim,
        metin_baytlari=veri[:ayet_bitis],
        duzen=duzen,
    )


def _ayetleri_oku(
    veri: bytes,
    satirlar: Sequence[bytes],
    baslangiclar: Sequence[int],
    ayet_sayisi: int,
    sure_tablosu: Sequence[int],
) -> list[AyetSatiri]:
    beklenen: tuple[int, int] | None = (1, 1)
    sonuc: list[AyetSatiri] = []
    for i in range(ayet_sayisi):
        satir = satirlar[i]
        eslesme = AYET_ONEKI.match(satir)
        if eslesme is None:  # bildirim_bul zaten eler; savunma
            raise GirdiHatasi(f"satir {i + 1}: tanimsiz satir")
        sure, ayet = int(eslesme.group(1)), int(eslesme.group(2))
        if beklenen is None or (sure, ayet) != beklenen:
            raise GirdiHatasi(f"satir {i + 1}: sira disi numara (okuma sirasi bozuk)")
        beklenen = sonraki(sure, ayet, sure_tablosu)
        bas = baslangiclar[i]
        metin_bas = bas + eslesme.end()
        metin_son = bas + len(satir)
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
                satir_son=metin_son + 1,
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


def _ayet_baytlari(birimler: Iterable[tuple[str, str]]) -> bytes:
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
    return b"".join(parcalar)


def yeniden_kur(birimler: Iterable[tuple[str, str]], bildirim: bytes, duzen: Duzen) -> bytes:
    """Dosyanin tamamini kurar. `birimler` okuma sirasinda `(capa, metin)` ciftleridir.

    Ozeti kilitteki `sha256`'dir. Ayet satirlari `{sure}|{ayet}|{metin}` + LF'dir (baslangic
    sifir reddedildigi icin onek kanoniktir); bildirim aynen, ayet satirlarindan sonra konur
    (`konum = "son"`).
    """
    if duzen.konum != KONUM_SON or not duzen.son_lf:
        raise GirdiHatasi("satir duzeni bu bicimle uyumsuz (konum son, son LF olmali)")
    return _ayet_baytlari(birimler) + bildirim
