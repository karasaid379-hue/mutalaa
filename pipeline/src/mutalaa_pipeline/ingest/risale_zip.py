"""Risale zip'inin bellekte guvenli okunmasi (A20.1, K-51 madde 2).

Indirilen zip guvenilmeyen veridir: diske ACILMAZ, hicbir uyesi calistirilmaz; uyeler yalniz bayt
olarak bellekte okunur. Acilista butun uye adlari ve boyutlari denetlenir:

* yol: bos, `\\` ya da NUL iceren, `/` ile baslayan (mutlak), surucu harfli ya da `:` iceren,
  `..` parcasi iceren adlar reddedilir; ayni ad iki kez bulunamaz;
* tur: sembolik baglanti ve sifreli uye reddedilir; yalniz depolanmis ve deflate sikistirmasi;
* sinirlar (`ZipSiniri`): uye sayisi, tek uye acik boyutu, toplam acik boyut ve uye basina
  sikistirma orani (zip bombasi).

Okuma sirasinda uye, bildirilen boyutu asamaz ve CRC denetimi `zipfile` tarafindan yapilir.
Iletiler yalniz sayi ve kisaltilmis ad tasir; uye icerigi asla.
"""

import io
import stat
import zipfile
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi

IZINLI_SIKISTIRMA: Final = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)


@dataclass(frozen=True)
class ZipSiniri:
    """Zip bombasi ve yol saldirisi sinirlari (gercek zip: 1.051 uye, 76 MB acik)."""

    en_cok_zip_bayt: int = 256 << 20
    en_cok_uye: int = 5000
    en_cok_uye_bayt: int = 64 << 20
    en_cok_toplam_bayt: int = 512 << 20
    en_cok_oran: int = 200  # acik boyut / sikisik boyut (uye basina)


VARSAYILAN_SINIR: Final = ZipSiniri()


def _ad_ozeti(ad: str) -> str:
    kesik = ad if len(ad) <= 60 else ad[:57] + "..."
    return kesik.encode("ascii", "backslashreplace").decode("ascii")


def uye_adi_guvenli_mi(ad: str) -> bool:
    """Zip uye adi guvenligi: mutlak yol, `..`, surucu harfi, ters bolu ve NUL reddedilir."""
    if ad == "" or "\\" in ad or "\x00" in ad or ":" in ad:
        return False
    govde = ad[:-1] if ad.endswith("/") else ad
    yol = PurePosixPath(govde)
    return not (yol.is_absolute() or ".." in yol.parts or govde == "")


def _uye_denetle(bilgi: zipfile.ZipInfo) -> None:
    ad = _ad_ozeti(bilgi.filename)
    if not uye_adi_guvenli_mi(bilgi.filename):
        raise GirdiHatasi(f"zip: guvensiz uye adi ({ad})")
    if bilgi.flag_bits & 0x1:
        raise GirdiHatasi(f"zip: sifreli uye ({ad})")
    if stat.S_ISLNK(bilgi.external_attr >> 16):
        raise GirdiHatasi(f"zip: sembolik baglanti uye ({ad})")
    if not bilgi.is_dir() and bilgi.compress_type not in IZINLI_SIKISTIRMA:
        raise GirdiHatasi(f"zip: desteklenmeyen sikistirma ({ad})")


class GuvenliZip:
    """Bellekteki zip baytlarini denetleyip uyeleri bayt olarak okur (diske yazmaz)."""

    def __init__(self, veri: bytes, sinir: ZipSiniri = VARSAYILAN_SINIR) -> None:
        if len(veri) > sinir.en_cok_zip_bayt:
            raise GirdiHatasi(f"zip: cok buyuk ({len(veri)} bayt)")
        try:
            self._zip = zipfile.ZipFile(io.BytesIO(veri))
        except (zipfile.BadZipFile, OSError, ValueError):
            raise GirdiHatasi("zip: gecerli bir zip degil") from None
        self._sinir = sinir
        bilgiler = self._zip.infolist()
        if len(bilgiler) > sinir.en_cok_uye:
            raise GirdiHatasi(f"zip: uye sayisi siniri asiyor ({len(bilgiler)})")
        self._uyeler: dict[str, zipfile.ZipInfo] = {}
        toplam = 0
        for bilgi in bilgiler:
            _uye_denetle(bilgi)
            if bilgi.filename in self._uyeler:
                raise GirdiHatasi(f"zip: yinelenen uye adi ({_ad_ozeti(bilgi.filename)})")
            if bilgi.file_size > sinir.en_cok_uye_bayt:
                raise GirdiHatasi(f"zip: uye cok buyuk ({_ad_ozeti(bilgi.filename)})")
            if bilgi.file_size > 0 and (
                bilgi.compress_size == 0
                or bilgi.file_size > bilgi.compress_size * sinir.en_cok_oran
            ):
                raise GirdiHatasi(
                    f"zip: sikistirma orani siniri asiyor ({_ad_ozeti(bilgi.filename)})"
                )
            toplam += bilgi.file_size
            if toplam > sinir.en_cok_toplam_bayt:
                raise GirdiHatasi("zip: toplam acik boyut siniri asiyor")
            self._uyeler[bilgi.filename] = bilgi
        self.toplam_acik_bayt = toplam

    def __len__(self) -> int:
        return len(self._uyeler)

    def adlar(self) -> list[str]:
        """Dizin olmayan uyelerin adlari (zip sirasinda)."""
        return [ad for ad, b in self._uyeler.items() if not b.is_dir()]

    def var_mi(self, ad: str) -> bool:
        bilgi = self._uyeler.get(ad)
        return bilgi is not None and not bilgi.is_dir()

    def boyut(self, ad: str) -> int:
        return self._bilgi(ad).file_size

    def _bilgi(self, ad: str) -> zipfile.ZipInfo:
        bilgi = self._uyeler.get(ad)
        if bilgi is None or bilgi.is_dir():
            raise GirdiHatasi(f"zip: uye yok ({_ad_ozeti(ad)})")
        return bilgi

    def oku(self, ad: str) -> bytes:
        """Uyenin baytlari; bildirilen boyutu asan ya da CRC'si tutmayan uye `GirdiHatasi`."""
        bilgi = self._bilgi(ad)
        try:
            with self._zip.open(bilgi) as akis:
                veri = akis.read(bilgi.file_size + 1)
        except (zipfile.BadZipFile, OSError, EOFError, RuntimeError, ValueError):
            raise GirdiHatasi(f"zip: uye okunamadi ({_ad_ozeti(ad)})") from None
        if len(veri) != bilgi.file_size:
            raise GirdiHatasi(f"zip: uye boyutu bildirilenle tutmuyor ({_ad_ozeti(ad)})")
        return veri
