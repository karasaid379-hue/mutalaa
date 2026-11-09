"""Ust veri QA dogrulama girdileri: QPC1 sayfa duzeni ve quran-meta listeleri (A11.1).

Iki girdi de `data/gelen/` altinda duran, guvenilmeyen VERIDIR: yalniz okunur, hicbir sey
calistirilmaz. QPC1 sayfa dosyalari JSON olarak, `quran-meta` tarball'u `tarfile` ile (diske
cikarmadan, uye boyutu sinirli) okunur; JS dosyasindaki dizi sabitleri duzenli ifadeyle
ayristirilir. Dosya yoksa ilgili okuyucu `None` doner (CI'da `data/` yoktur): olcum "atlandi"
olarak raporlanir. Dosya varsa ozetleri `SHA256SUMS` ile dogrulanir; uyusmazlik `GirdiHatasi`.

QPC1 ve `quran-meta` Kur'an metni degildir; yalniz sayfa/konum ve baslangic dogrulayicisidir.
"""

import json
import re
import tarfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil import TARIH_DESENI

GELEN: Final = "gelen"
QPC1_KAYNAGI: Final = "medine-604-duzen"
QPC1_ALT_YOL: Final = ("mushaf", "QPC1")
QURAN_META_KAYNAGI: Final = "quran-meta"
SHA256SUMS_ADI: Final = "SHA256SUMS"
SAYFA_DOSYASI: Final = re.compile(r"page-([0-9]{3})\.json")
KONUM: Final = re.compile(r"([0-9]{1,3}):([0-9]{1,3}):([0-9]{1,4})")
HAFS_UYESI: Final = re.compile(r"package/dist/HafsLists-[A-Za-z0-9_-]+\.js")
LISTE_ADLARI: Final = (
    "HizbQuarterList",
    "JuzList",
    "ManzilList",
    "PageList",
    "RukuList",
    "SajdaList",
)
EN_BUYUK_SAYFA_BAYT: Final = 1 << 20
EN_BUYUK_TGZ_BAYT: Final = 8 << 20
EN_BUYUK_UYE_BAYT: Final = 1 << 20
HINT_ILK, HINT_SON = 0x0660, 0x0669


@dataclass(frozen=True)
class Qpc1:
    """QPC1 duzeni: sayfa basina ilk ve son kelime konumu (`sure:ayet:kelime`)."""

    tarih: str
    ilk: dict[int, str]
    son: dict[int, str]
    sha256sums_ozeti: str  # SHA256SUMS dosyasinin SHA-256'si

    @property
    def sayfa_sayisi(self) -> int:
        return len(self.ilk)


@dataclass(frozen=True)
class QuranMeta:
    """`quran-meta` HafsLists: mutlak ayet numarali baslangic listeleri (sentinelsiz)."""

    tarih: str
    tgz_sha256: str
    listeler: dict[str, tuple[int, ...]]
    sentinel: int  # listelerin son elemani (toplam ayet + 1)


def _tarih_klasoru(kok: Path, ic: tuple[str, ...]) -> Path | None:
    """`kok` altindaki, `ic` alt yoluna sahip en yeni gecerli tarih klasoru."""
    if not kok.is_dir():
        return None
    adaylar = sorted(
        (p for p in kok.iterdir() if p.is_dir() and TARIH_DESENI.fullmatch(p.name)),
        key=lambda p: p.name,
    )
    for klasor in reversed(adaylar):
        hedef = klasor.joinpath(*ic)
        if hedef.exists() and (klasor / SHA256SUMS_ADI).is_file():
            return klasor
    return None


def _sha256sums(klasor: Path) -> dict[str, str]:
    """`sha256sum` bicimi: '<ozet> *<yol>' (yol klasore gore)."""
    sonuc: dict[str, str] = {}
    metin = (klasor / SHA256SUMS_ADI).read_bytes().decode("utf-8")
    for satir in metin.split("\n"):
        if not satir:
            continue
        if len(satir) < 67 or satir[64:66] not in (" *", "  "):
            raise GirdiHatasi(f"{klasor.name}/{SHA256SUMS_ADI}: satir bicimi gecersiz")
        sonuc[satir[66:]] = satir[:64]
    return sonuc


def _ozetleri_dogrula(klasor: Path, kimlik: str, yollar: list[Path]) -> None:
    """`yollar` `SHA256SUMS` icinde olmali ve ozetleri tutmali."""
    kayit = _sha256sums(klasor)
    for yol in yollar:
        goreli = yol.relative_to(klasor).as_posix()
        beklenen = kayit.get(goreli)
        if beklenen is None or lineage.sha256_dosya(yol) != beklenen:
            raise GirdiHatasi(f"{kimlik}: {goreli} ozeti {SHA256SUMS_ADI} ile tutmuyor")


def qpc1_oku(veri_kok: Path) -> Qpc1 | None:
    """En yeni QPC1 klasorunden her sayfanin ilk ve son kelime konumunu okur; yoksa `None`.

    Yalniz kelime konumu (`location`) okunur; kelime metni alinmaz. Yalniz rakamdan olusan
    (Arapca-Hint) 'ayet sonu' girdileri kelime sayilmaz.
    """
    klasor = _tarih_klasoru(veri_kok / GELEN / QPC1_KAYNAGI, QPC1_ALT_YOL)
    if klasor is None:
        return None
    sayfalar = sorted((klasor.joinpath(*QPC1_ALT_YOL)).glob("page-*.json"), key=lambda p: p.name)
    _ozetleri_dogrula(klasor, QPC1_KAYNAGI, sayfalar)
    ilk: dict[int, str] = {}
    son: dict[int, str] = {}
    for yol in sayfalar:
        eslesme = SAYFA_DOSYASI.fullmatch(yol.name)
        if eslesme is None or yol.stat().st_size > EN_BUYUK_SAYFA_BAYT:
            raise GirdiHatasi(f"{QPC1_KAYNAGI}: beklenmeyen dosya: {yol.name}")
        try:
            veri = json.loads(yol.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GirdiHatasi(f"{QPC1_KAYNAGI}: {yol.name} JSON degil") from None
        sayfa = int(eslesme.group(1))
        konumlar = _kelime_konumlari(veri, yol.name)
        if not konumlar:
            raise GirdiHatasi(f"{QPC1_KAYNAGI}: {yol.name} kelime icermiyor")
        ilk[sayfa], son[sayfa] = konumlar[0], konumlar[-1]
    sums = lineage.sha256_dosya(klasor / SHA256SUMS_ADI)
    return Qpc1(tarih=klasor.name, ilk=ilk, son=son, sha256sums_ozeti=sums)


def _kelime_konumlari(veri: object, ad: str) -> list[str]:
    if not isinstance(veri, dict) or not isinstance(veri.get("lines"), list):
        raise GirdiHatasi(f"{QPC1_KAYNAGI}: {ad} beklenen yapida degil")
    konumlar: list[str] = []
    for satir in veri["lines"]:
        kelimeler = satir.get("words", []) if isinstance(satir, dict) else []
        if not isinstance(kelimeler, list):
            raise GirdiHatasi(f"{QPC1_KAYNAGI}: {ad} words listesi degil")
        for kelime in kelimeler:
            if not isinstance(kelime, dict):
                raise GirdiHatasi(f"{QPC1_KAYNAGI}: {ad} kelime nesnesi degil")
            metin, konum = kelime.get("word"), kelime.get("location")
            if not isinstance(metin, str) or not isinstance(konum, str):
                raise GirdiHatasi(f"{QPC1_KAYNAGI}: {ad} word/location metin degil")
            if metin != "" and all(HINT_ILK <= ord(h) <= HINT_SON for h in metin):
                continue  # ayet sonu isareti
            if KONUM.fullmatch(konum) is None:
                raise GirdiHatasi(f"{QPC1_KAYNAGI}: {ad} location bicimi gecersiz")
            konumlar.append(konum)
    return konumlar


def quran_meta_oku(veri_kok: Path) -> QuranMeta | None:
    """En yeni `quran-meta-*.tgz` dosyasinin HafsLists dizilerini okur; yoksa `None`.

    Tarball `tarfile` ile bellekte okunur (cikarilmaz, JS calistirilmaz). Her dizi
    `Ad: [0, n1, n2, ..., 6237]` bicimindeki sayi dizisidir; baslangictaki 0 ve sondaki sentinel
    ayrilir (`SajdaList` sentinelsizdir).
    """
    klasor = _tarih_klasoru(veri_kok / GELEN / QURAN_META_KAYNAGI, ())
    if klasor is None:
        return None
    tgzler = sorted(klasor.glob("quran-meta-*.tgz"), key=lambda p: p.name)
    if not tgzler:
        return None
    tgz = tgzler[-1]
    if tgz.stat().st_size > EN_BUYUK_TGZ_BAYT:
        raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: {tgz.name} cok buyuk")
    _ozetleri_dogrula(klasor, QURAN_META_KAYNAGI, [tgz])
    try:
        with tarfile.open(tgz, "r:gz") as arsiv:
            uyeler = [m for m in arsiv.getmembers() if HAFS_UYESI.fullmatch(m.name) and m.isfile()]
            if len(uyeler) != 1 or uyeler[0].size > EN_BUYUK_UYE_BAYT:
                raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: HafsLists uyesi bulunamadi")
            dosya = arsiv.extractfile(uyeler[0])
            if dosya is None:
                raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: HafsLists uyesi okunamadi")
            kaynak = dosya.read().decode("utf-8")
    except (tarfile.TarError, OSError, UnicodeDecodeError):
        raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: {tgz.name} okunamadi") from None
    ham: dict[str, list[int]] = {}
    for ad in LISTE_ADLARI:
        eslesme = re.search(ad + r":\s*\[([0-9,\s]*)\]", kaynak)
        if eslesme is None:
            raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: {ad} dizisi bulunamadi (bicim degismis)")
        degerler = [int(x) for x in eslesme.group(1).split(",") if x.strip() != ""]
        ham[ad] = degerler
    listeler: dict[str, tuple[int, ...]] = {}
    sentinel = 0
    for ad, degerler in ham.items():
        if ad == "SajdaList":
            listeler[ad] = tuple(degerler)
            continue
        if len(degerler) < 3 or degerler[0] != 0:
            raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: {ad} beklenen bicimde degil")
        if sentinel not in (0, degerler[-1]):
            raise GirdiHatasi(f"{QURAN_META_KAYNAGI}: dizilerin sentinel degeri ayni degil")
        sentinel = degerler[-1]
        listeler[ad] = tuple(degerler[1:-1])
    return QuranMeta(
        tarih=klasor.name,
        tgz_sha256=lineage.sha256_dosya(tgz),
        listeler=listeler,
        sentinel=sentinel,
    )
