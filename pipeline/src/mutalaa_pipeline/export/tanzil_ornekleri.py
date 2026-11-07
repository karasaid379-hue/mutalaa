"""Arama §1.5 Arapca tablosunun Tanzil Uthmani baytlariyla vektor satirlari (A10.7).

`mutalaa export test-vectors --tanzil-ornekleri`: `docs/03-veri/05-arama-fts5.md` icindeki
Arapca tablonun (Girdi, `ar`, Sinanan kural) her girdisini Tanzil Uthmani dosyasinda bulur ve
`shared/test-vectors/normalize/ar.jsonl` icin `ar-tz-NNNN` satirlari kurar:

    input     Tanzil'in baytlari (UTF-8 cozumu, hicbir donusum yok); birlesen isaretler
              dosyada `\\uXXXX` kacisiyla yazilir (test_vectors.dizgi_yaz)
    expected  tablonun `ar` sutunu (belgeden, aynen)
    note      `tanzil-uthmani q:{sure}:{ayet}`

Eslesme normallestiriciden BAGIMSIZ bir iskeletle yapilir: NFD'den sonra butun birlesen
isaretler (M*), U+0640 ve U+06D6-U+06ED atilir. Tablo girdisinin iskeleti, Uthmani ayetlerinin
bosluk (U+0020) ile ayrilan belirtec dizilerinin (k belirtec; k tablo girdisindeki belirtec
sayisi) iskeletiyle karsilastirilir; okuma sirasindaki ilk eslesme alinir. Tanik denetimi: tablo
girdisinin NFC bicimindeki, normallestiricinin sildigi ya da birlestirdigi (ve yalin hemze gibi
korudugu) her kod noktasi secilen dilimin NFC bicimde de bulunmalidir; bulunmuyorsa sonraki
eslesmeye gecilir. Boylece satir, sinadigi kurali Tanzil baytlarinda gercekten tasir.

Tanzil dosyasi `data/gelen/tanzil/<YYYY-AA-GG>/quran-uthmani.txt` altindan bayt olarak okunur ve
satir kurulmadan once `tanzil.lock.json` ile denetlenir (vektor girdisi yalniz kilitli baytlardan
gelir). Eslesme bulunamazsa ya da `normalize_ar` tablodaki degeri vermezse `GirdiHatasi` (cikis 2)
verilir ve DURULUR: beklenen deger uydurulmaz, Tanzil girdisi duzeltilmez; fark `/belge-esitle`
ya da `/karar` ile cozulur. Iletiler yalniz satir numarasi, capa, sayi ve kod noktasi tasir.

Bu modul `test_vectors.py`in disindadir: oradaki "normallestiriciyi ice aktarmaz" ilkesi
korunur (beklenen deger normallestiriciden uretilmez; burada normallestirici yalniz tablodaki
degeri dogrulamak icin cagrilir).
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi, utf8_oku
from mutalaa_pipeline.export.test_vectors import TANZIL_ONEKI, Satir
from mutalaa_pipeline.ingest import tanzil
from mutalaa_pipeline.ingest.tanzil_bicim import AyetSatiri, Ayrisma
from mutalaa_pipeline.normalize import normalize_ar

BELGE_YOLU: Final = "docs/03-veri/05-arama-fts5.md"
KAYNAK_ADI: Final = "tanzil-uthmani"
VARYANT: Final = "uthmani"
BOSLUK: Final = " "

TATVIL: Final = 0x0640
KUR_AN_ISARETLERI: Final = (0x06D6, 0x06ED)  # Arama §1.3 madde 1
# Tanik denetimi: normallestiricinin etkiledigi kod noktalari (Arama §1.3 madde 1-2). Bu liste
# normallestirici kodundan bagimsiz, belgenin yazdigi kuraldan alinmistir.
SILINENLER: Final = ((0x064B, 0x065F), (0x0670, 0x0670), KUR_AN_ISARETLERI, (TATVIL, TATVIL))
# Birlestirilen harfler: U+0623, U+0625, U+0622, U+0671 (elif), U+0649 (ye), U+0629 (he),
# U+0624 (vav) ve U+0626 (ye).
BIRLESENLER: Final = frozenset({0x0622, 0x0623, 0x0625, 0x0671, 0x0649, 0x0629, 0x0624, 0x0626})
KORUNANLAR: Final = frozenset({0x0621, 0x06C0})  # yalin hemze ve U+06C0 degismez

_TABLO_BASI: Final = re.compile(r"^\| Girdi \| `ar` \| ")
_TABLO_AYIRICISI: Final = re.compile(r"^\|(?: ?-+ ?\|)+$")
_TABLO_SATIRI: Final = re.compile(r"^\| `(?P<girdi>[^`]+)` \| `(?P<ar>[^`]+)` \| (?P<kural>.+) \|$")


@dataclass(frozen=True)
class TabloSatiri:
    """Belgedeki Arapca tablonun bir satiri (`girdi` yalniz arama anahtaridir, vektore yazilmaz)."""

    sira: int  # tablodaki 1 tabanli sira
    girdi: str
    ar: str  # beklenen deger
    belge_satiri: int  # belgedeki 1 tabanli satir numarasi


@dataclass(frozen=True)
class Eslesme:
    """Bir tablo satirinin Tanzil Uthmani'deki yeri."""

    tablo: TabloSatiri
    capa: str  # q:{sure}:{ayet}
    belirtec_bas: int  # 1 tabanli, kapali aralik
    belirtec_son: int
    dilim: str  # Tanzil baytlarinin UTF-8 cozumu, aynen
    tanik: tuple[int, ...]  # secilen dilimde bulunan, tablo girdisinin tanik kod noktalari
    atlanan: int  # tanik denetiminden gecemeyen daha erken iskelet eslesmesi sayisi

    @property
    def kimlik(self) -> str:
        return f"{TANZIL_ONEKI}{self.tablo.sira:04d}"

    def satir(self) -> Satir:
        return Satir(self.kimlik, self.dilim, self.tablo.ar, f"{KAYNAK_ADI} {self.capa}")

    def ozet(self) -> str:
        """Tek satirlik ASCII ozet (metin yok): kimlik, capa, belirtec yeri, tanik, atlanan."""
        tanik = " ".join(f"U+{kod:04X}" for kod in self.tanik)
        yer = (
            str(self.belirtec_bas)
            if self.belirtec_bas == self.belirtec_son
            else f"{self.belirtec_bas}-{self.belirtec_son}"
        )
        return (
            f"{self.kimlik} {self.capa} belirtec {yer} atlanan {self.atlanan} tanik {tanik}"
        ).rstrip()


@dataclass(frozen=True)
class Uretim:
    satirlar: list[Satir]
    eslesmeler: list[Eslesme]


# --- iskelet ve tanik ---------------------------------------------------------------------


def iskelet(metin: str) -> str:
    """NFD'den sonra birlesen isaretler (M*), U+0640 ve U+06D6-U+06ED atilmis hal.

    Normallestiriciden bagimsizdir: harf birlestirme (U+0649 -> U+064A vb.) yapmaz ve
    bosluklara dokunmaz.
    """
    cikti: list[str] = []
    for harf in unicodedata.normalize("NFD", metin):
        kod = ord(harf)
        if kod == TATVIL or KUR_AN_ISARETLERI[0] <= kod <= KUR_AN_ISARETLERI[1]:
            continue
        if unicodedata.category(harf).startswith("M"):
            continue
        cikti.append(harf)
    return "".join(cikti)


def _etkilenir(kod: int) -> bool:
    return (
        any(bas <= kod <= son for bas, son in SILINENLER) or kod in BIRLESENLER or kod in KORUNANLAR
    )


def tanik_kumesi(metin: str) -> frozenset[int]:
    """Metnin NFC bicimindeki, normallestiricinin etkiledigi kod noktalari."""
    return frozenset(ord(h) for h in unicodedata.normalize("NFC", metin) if _etkilenir(ord(h)))


def _kod_noktalari(metin: str) -> frozenset[int]:
    return frozenset(ord(h) for h in unicodedata.normalize("NFC", metin))


# --- belge tablosu ------------------------------------------------------------------------


def _arapca_hucre(metin: str) -> bool:
    """Bos olmayan, kenarlarda ve arada tekrarli bosluk icermeyen, yalniz Arapca harf/isaret."""
    if metin == "" or metin.startswith(BOSLUK) or metin.endswith(BOSLUK) or "  " in metin:
        return False
    for harf in metin:
        if harf == BOSLUK:
            continue
        try:
            if not unicodedata.name(harf).startswith("ARABIC"):
                return False
        except ValueError:
            return False
    return True


def tablo_oku(kok: Path) -> list[TabloSatiri]:
    """Arama §1.5 Arapca tablosunu okur; bicim bozuksa `GirdiHatasi`."""
    yol = kok / BELGE_YOLU
    if not yol.is_file():
        raise GirdiHatasi(f"{BELGE_YOLU} yok (Arapca tablo belgeden okunur)")
    satirlar = [s.removesuffix("\r") for s in utf8_oku(yol, BELGE_YOLU).split("\n")]
    basliklar = [i for i, s in enumerate(satirlar) if _TABLO_BASI.match(s)]
    if len(basliklar) != 1:
        raise GirdiHatasi(
            f"{BELGE_YOLU}: Arapca tablo basligi (Girdi, ar) tam bir kez bulunmali"
            f" (bulunan {len(basliklar)})"
        )
    bas = basliklar[0]
    if bas + 1 >= len(satirlar) or _TABLO_AYIRICISI.match(satirlar[bas + 1]) is None:
        raise GirdiHatasi(f"{BELGE_YOLU}: satir {bas + 2}: tablo ayirici satiri bekleniyordu")
    tablo: list[TabloSatiri] = []
    gorulen: set[str] = set()
    for i in range(bas + 2, len(satirlar)):
        satir = satirlar[i]
        if not satir.startswith("|"):
            break
        eslesme = _TABLO_SATIRI.match(satir)
        if eslesme is None:
            raise GirdiHatasi(f"{BELGE_YOLU}: satir {i + 1}: tablo satiri bicimi gecersiz")
        girdi, ar = eslesme.group("girdi"), eslesme.group("ar")
        if not _arapca_hucre(girdi) or not _arapca_hucre(ar):
            raise GirdiHatasi(
                f"{BELGE_YOLU}: satir {i + 1}: Girdi ve ar hucreleri yalniz Arapca harf ve"
                " isaret ile tek bosluk icermeli"
            )
        if girdi in gorulen:
            raise GirdiHatasi(f"{BELGE_YOLU}: satir {i + 1}: yinelenen girdi")
        gorulen.add(girdi)
        tablo.append(TabloSatiri(len(tablo) + 1, girdi, ar, i + 1))
    if not tablo:
        raise GirdiHatasi(f"{BELGE_YOLU}: Arapca tabloda satir yok")
    return tablo


# --- eslestirme ---------------------------------------------------------------------------


def eslestir(tablo: Sequence[TabloSatiri], ayetler: Sequence[AyetSatiri]) -> list[Eslesme]:
    """Her tablo satiri icin okuma sirasindaki ilk (tanik denetiminden gecen) eslesmeyi bulur.

    Bulunamayan satirda `GirdiHatasi` (cikis 2): beklenen deger uydurulmaz, girdi duzeltilmez.
    """
    belirtecler = [a.metin.split(BOSLUK) for a in ayetler]
    iskeletler = [[iskelet(b) for b in dizi] for dizi in belirtecler]
    sonuc: list[Eslesme] = []
    for satir in tablo:
        hedef = [iskelet(b) for b in satir.girdi.split(BOSLUK)]
        if "" in hedef:
            raise GirdiHatasi(f"tablo satiri {satir.sira}: iskelet bos belirtec iceriyor")
        k = len(hedef)
        tanik = tanik_kumesi(satir.girdi)
        atlanan = 0
        bulunan: Eslesme | None = None
        for ayet, dizi, isk in zip(ayetler, belirtecler, iskeletler, strict=True):
            for i in range(len(isk) - k + 1):
                if isk[i : i + k] != hedef:
                    continue
                dilim = BOSLUK.join(dizi[i : i + k])
                if tanik <= _kod_noktalari(dilim):
                    bulunan = Eslesme(
                        tablo=satir,
                        capa=ayet.capa,
                        belirtec_bas=i + 1,
                        belirtec_son=i + k,
                        dilim=dilim,
                        tanik=tuple(sorted(tanik)),
                        atlanan=atlanan,
                    )
                    break
                atlanan += 1
            if bulunan is not None:
                break
        if bulunan is None:
            ek = f" ({atlanan} iskelet eslesmesi tanik denetiminden gecemedi)" if atlanan else ""
            raise GirdiHatasi(
                f"tablo satiri {satir.sira} (belge satiri {satir.belge_satiri}):"
                f" Tanzil Uthmani'de eslesme yok{ek}; beklenen deger uydurulmaz, girdi"
                " duzeltilmez (/belge-esitle ya da /karar)"
            )
        sonuc.append(bulunan)
    return sonuc


def _fark(bulunan: str, beklenen: str) -> str:
    """Iki dizgi arasindaki ilk farkin yeri ve kod noktalari (metin yok)."""
    ortak = min(len(bulunan), len(beklenen))
    konum = next((i for i in range(ortak) if bulunan[i] != beklenen[i]), ortak)

    def kod(metin: str) -> str:
        return f"U+{ord(metin[konum]):04X}" if konum < len(metin) else "yok"

    return (
        f"uzunluk {len(bulunan)}/{len(beklenen)} (bulunan/beklenen),"
        f" ilk fark konum {konum}: {kod(bulunan)} / {kod(beklenen)}"
    )


def normalize_denetle(eslesmeler: Sequence[Eslesme]) -> None:
    """`normalize_ar(dilim)` tablodaki `ar` degerini vermiyorsa `GirdiHatasi` (cikis 2)."""
    for e in eslesmeler:
        bulunan = normalize_ar(e.dilim)
        if bulunan != e.tablo.ar:
            raise GirdiHatasi(
                f"tablo satiri {e.tablo.sira} ({e.capa}): normalize_ar tablodaki degeri"
                f" vermiyor ({_fark(bulunan, e.tablo.ar)}); beklenen deger uydurulmaz,"
                " Tanzil girdisi duzeltilmez (/belge-esitle ya da /karar)"
            )


# --- Tanzil dosyasi -----------------------------------------------------------------------


def tanzil_oku(veri_kok: Path) -> Ayrisma:
    """`data/gelen/tanzil` altindaki en yeni Uthmani dosyasi, kilitle denetlenmis ayrisma."""
    try:
        gelen = tanzil.gelen_kok(veri_kok)
        tarih = tanzil.gelen_tarihi_coz(gelen, None)
        veri = tanzil.gelen_oku(gelen, tarih, VARYANT)
        return tanzil.kilit_denetle(tanzil.kilit_yukle()[VARYANT], veri)
    except GirdiHatasi as hata:
        raise GirdiHatasi(
            f"--tanzil-ornekleri: Tanzil Uthmani dosyasi kullanilamadi ({hata});"
            " data/gelen/tanzil/<YYYY-AA-GG>/quran-uthmani.txt gerekir (A10.0)"
        ) from None


def uret(kok: Path, veri_kok: Path) -> Uretim:
    """Tabloyu belgeden okur, Tanzil'de bulur, normallestiriciyle dogrular, satirlari kurar."""
    tablo = tablo_oku(kok)
    ayrisma = tanzil_oku(veri_kok)
    eslesmeler = eslestir(tablo, ayrisma.ayetler)
    normalize_denetle(eslesmeler)
    return Uretim([e.satir() for e in eslesmeler], eslesmeler)
