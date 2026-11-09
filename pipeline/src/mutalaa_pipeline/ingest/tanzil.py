"""Tanzil bagdastiricisi (A10.2): `data/gelen` -> `data/raw` -> `data/staged` (K-39).

`mutalaa ingest tanzil --variant uthmani|simple-clean`:

1. `fetch` indirmez: `data/gelen/tanzil/<YYYY-AA-GG>/quran-<varyant>.txt` dosyasini bayt olarak
   okur ve `tanzil.lock.json` ile karsilastirir (dosya ozeti, boyut, bicim, parca ozetleri).
   Tutmazsa HER DURUMDA cikis 2: ileti farkin bildirim blogunda mi ayet satirlarinda mi
   oldugunu ayirir ve "yeni Tanzil surumu kilit guncellenerek (/karar) alinir" uyarisini tasir
   (K-39 madde 4); dosya icerigi iletide yer almaz. Ileti `ILETI_EN_UZUN` icinde kalir: konsol
   300 karakterde keser, bu yuzden degisken parca kisaltilir, uyari asla kesilmez. Ancak
   kilitten sonra `data/raw/<kaynak>/<YYYY-MM-DD>/` altina kopyalar ve `fetch.json` yazar
   (dosyalar `fsync` ile diske esitlenmeden klasor gorunur olmaz). Ayni baytlar `raw` altinda
   zaten varsa yeni kopya acilmaz (raw degismez, gece kosusu raw'u sisirmez).
2. `parse` ham dosyayi `tanzil_bicim.ayristir` ile okur (NFC, strip, splitlines ve satir sonu
   cevirisi yok, K-26). Her ayet bir birimdir; bildirim blogu `notice.txt` olarak staged klasorune
   bayt bayt yazilir (`export pg` bunu bekler, K-39 madde 6).

Manifest ve parmak izi `run_ingest` tarafindandir: parmak izi (dosya adi ve ozeti, parametreler,
yapilandirma, git commit, arac surumleri) onceki basarili calistirmayla ayniysa adim atlanir;
`--force` ve kirli calisma agaci atlamayi kapatir. Kilit denetimi atlansa da her kosuda yapilir.

Ust veri (A11, K-39 guncellemesi 8 Kasim 2026): `tanzil.lock.json` `varyantlar` kumesinin
yanina ayri bir `ust_veri` bolumu tasir (`url`, `surum`, `alinma_tarihi`, `boyut`, `sha256`);
metin satiri ve bildirim blogu olmadigi icin `metin_sha256` ve `bildirim_sha256` yoktur. Alim
`ingest/tanzil_ust_veri.py` icindedir (`--variant ust-veri`).

Hata iletileri yalniz sayi, ozet (kisaltilmis), alan adi ve goreli yol tasir; dosya icerigi asla.
"""

import json
import os
import re
import shutil
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import tanzil_bicim
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import NOTICE_ADI, OZET_DESENI, kisa_ozet
from mutalaa_pipeline.logs import ILETI_EN_UZUN, json_baytlari
from mutalaa_pipeline.runctx import RunContext

VARYANTLAR: Final = ("uthmani", "simple-clean")
BASLIK_TURU: Final = {"uthmani": "Uthmani", "simple-clean": "Simple Clean"}
# A10.0 alimi: Tanzil indirme formunun adresi ve acilistaki secenekleri (baytlari bunlar belirler).
FORM_ADRESI: Final = "https://tanzil.net/download/"
SECENEKLER: Final = {
    "marks": True,
    "sajdah": True,
    "tatweel": True,
    "rub": False,
    "stanween": False,
}
UST_VERI: Final = "ust-veri"  # `--variant` degeri; metin varyanti degil, kilitte ayri bolum
KILIT_YOLU: Final = Path(__file__).with_name("tanzil.lock.json")
GELEN_KLASORU: Final = "gelen"
GELEN_KAYNAK: Final = "tanzil"
FETCH_ADI: Final = "fetch.json"
INGEST_ADIMI: Final = "ingest"
EN_BUYUK_GELEN_BAYT: Final = 32 << 20  # gercek dosyalar 1,4 MB'dir; bunun ustu guvenilmez
# OneDrive ya da antivirus klasoru eszamanli tarayinca yeniden adlandirma gecici olarak
# PermissionError verebilir (windows-sorun: EPERM); sinirli sayida yeniden denenir.
YENIDEN_ADLANDIRMA_DENEMESI: Final = 5

TARIH_DESENI: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
SURUM_DESENI: Final = re.compile(r"[0-9]+(\.[0-9]+)*")
KILIT_ALANLARI: Final = (
    "url",
    "secenekler",
    "surum",
    "alinma_tarihi",
    "boyut",
    "sha256",
    "metin_sha256",
    "bildirim_sha256",
)
UST_VERI_KILIT_ALANLARI: Final = ("url", "surum", "alinma_tarihi", "boyut", "sha256")
UYARI: Final = "Yeni Tanzil surumu kilit guncellenerek (/karar) alinir."


def kaynak_kimligi(varyant: str) -> str:
    return f"tanzil-{_varyant(varyant)}"


def dosya_adi(varyant: str) -> str:
    return f"quran-{_varyant(varyant)}.txt"


def _varyant(varyant: str) -> str:
    if varyant not in VARYANTLAR:
        raise GirdiHatasi("varyant uthmani ya da simple-clean olmali")
    return varyant


# --- kilit -------------------------------------------------------------------------------


@dataclass(frozen=True)
class KilitGirdisi:
    """`tanzil.lock.json` icindeki bir varyantin kaydi (K-39 madde 4)."""

    varyant: str
    url: str  # indirme formunun adresi
    secenekler: dict[str, bool]  # marks, sajdah, tatweel, rub, stanween
    surum: str  # dosya basligindaki surum, or. "1.1"
    alinma_tarihi: str  # YYYY-AA-GG
    boyut: int
    sha256: str  # butun dosya
    metin_sha256: str  # ayet satirlarinin baytlari
    bildirim_sha256: str  # bildirim blogunun baytlari

    @property
    def kaynak(self) -> str:
        return kaynak_kimligi(self.varyant)

    def sozluk(self) -> dict[str, object]:
        """Kilit dosyasindaki alan sirasiyla."""
        return {
            "url": self.url,
            "secenekler": dict(self.secenekler),
            "surum": self.surum,
            "alinma_tarihi": self.alinma_tarihi,
            "boyut": self.boyut,
            "sha256": self.sha256,
            "metin_sha256": self.metin_sha256,
            "bildirim_sha256": self.bildirim_sha256,
        }


@dataclass(frozen=True)
class UstVeriKilidi:
    """`tanzil.lock.json` icindeki `ust_veri` bolumu (K-39 guncellemesi, 8 Kasim 2026)."""

    url: str  # dosyanin dogrudan adresi
    surum: str  # XML kok ogesinin `version` degeri, or. "1.0"
    alinma_tarihi: str  # YYYY-AA-GG
    boyut: int
    sha256: str  # butun dosya

    def sozluk(self) -> dict[str, object]:
        """Kilit dosyasindaki alan sirasiyla."""
        return {
            "url": self.url,
            "surum": self.surum,
            "alinma_tarihi": self.alinma_tarihi,
            "boyut": self.boyut,
            "sha256": self.sha256,
        }


def tarih_gecerli(metin: str) -> bool:
    """`YYYY-AA-GG` biciminde ve takvimde var olan bir tarih mi."""
    if TARIH_DESENI.fullmatch(metin) is None:
        return False
    try:
        date.fromisoformat(metin)
    except ValueError:
        return False
    return True


def _kilit_girdisi(varyant: str, nesne: object) -> KilitGirdisi:
    yer = f"tanzil.lock.json varyantlar.{varyant}"
    if not isinstance(nesne, dict):
        raise GirdiHatasi(f"{yer}: nesne olmali")
    eksik = [a for a in KILIT_ALANLARI if a not in nesne]
    if eksik:
        raise GirdiHatasi(f"{yer}: alan eksik: {eksik[0]}")
    fazla = sorted(str(a) for a in nesne if a not in KILIT_ALANLARI)
    if fazla:
        raise GirdiHatasi(f"{yer}: bilinmeyen alan (sayi {len(fazla)})")
    url, secenekler, surum = nesne["url"], nesne["secenekler"], nesne["surum"]
    tarih, boyut = nesne["alinma_tarihi"], nesne["boyut"]
    if not isinstance(url, str) or not url.startswith("https://"):
        raise GirdiHatasi(f"{yer}: url https:// ile baslayan metin olmali")
    if (
        not isinstance(secenekler, dict)
        or set(secenekler) != set(SECENEKLER)
        or not all(type(v) is bool for v in secenekler.values())
    ):
        raise GirdiHatasi(f"{yer}: secenekler {', '.join(SECENEKLER)} alanlarini (bool) tasimali")
    if not isinstance(surum, str) or SURUM_DESENI.fullmatch(surum) is None:
        raise GirdiHatasi(f"{yer}: surum sayilardan olusan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise GirdiHatasi(f"{yer}: alinma_tarihi YYYY-AA-GG olmali")
    if type(boyut) is not int or boyut <= 0:
        raise GirdiHatasi(f"{yer}: boyut pozitif tam sayi olmali")
    ozetler: dict[str, str] = {}
    for alan in ("sha256", "metin_sha256", "bildirim_sha256"):
        deger = nesne[alan]
        if not isinstance(deger, str) or OZET_DESENI.fullmatch(deger) is None:
            raise GirdiHatasi(f"{yer}: {alan} 64 haneli kucuk harfli onaltilik olmali")
        ozetler[alan] = deger
    return KilitGirdisi(
        varyant=varyant,
        url=url,
        secenekler={ad: bool(secenekler[ad]) for ad in SECENEKLER},
        surum=surum,
        alinma_tarihi=tarih,
        boyut=boyut,
        **ozetler,
    )


def _ust_veri_kilidi(nesne: object) -> UstVeriKilidi:
    yer = "tanzil.lock.json ust_veri"
    if not isinstance(nesne, dict):
        raise GirdiHatasi(f"{yer}: nesne olmali")
    eksik = [a for a in UST_VERI_KILIT_ALANLARI if a not in nesne]
    if eksik:
        raise GirdiHatasi(f"{yer}: alan eksik: {eksik[0]}")
    fazla = sorted(str(a) for a in nesne if a not in UST_VERI_KILIT_ALANLARI)
    if fazla:
        raise GirdiHatasi(f"{yer}: bilinmeyen alan (sayi {len(fazla)})")
    url, surum, tarih = nesne["url"], nesne["surum"], nesne["alinma_tarihi"]
    boyut, ozet = nesne["boyut"], nesne["sha256"]
    if not isinstance(url, str) or not url.startswith("https://"):
        raise GirdiHatasi(f"{yer}: url https:// ile baslayan metin olmali")
    if not isinstance(surum, str) or SURUM_DESENI.fullmatch(surum) is None:
        raise GirdiHatasi(f"{yer}: surum sayilardan olusan metin olmali")
    if not isinstance(tarih, str) or not tarih_gecerli(tarih):
        raise GirdiHatasi(f"{yer}: alinma_tarihi YYYY-AA-GG olmali")
    if type(boyut) is not int or boyut <= 0:
        raise GirdiHatasi(f"{yer}: boyut pozitif tam sayi olmali")
    if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi(f"{yer}: sha256 64 haneli kucuk harfli onaltilik olmali")
    return UstVeriKilidi(url=url, surum=surum, alinma_tarihi=tarih, boyut=boyut, sha256=ozet)


def kilit_coz_tam(ham: bytes) -> tuple[dict[str, KilitGirdisi], UstVeriKilidi | None]:
    """Kilit dosyasinin baytlarini kati bicimde cozer: `(varyantlar, ust_veri)`.

    Ust alanlar yalniz `varyantlar` (zorunlu) ve `ust_veri` (istege bagli) olabilir; baska ust
    alan, BOM, CR, UTF-8 olmayan bayt ve yinelenen anahtar hatadir. Bicim hatasi `GirdiHatasi`.
    """
    if ham.startswith(tanzil_bicim.BOM) or tanzil_bicim.CR in ham:
        raise GirdiHatasi("tanzil.lock.json: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        metin = ham.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi("tanzil.lock.json: UTF-8 degil") from None
    try:
        veri = kati_json(metin)
    except GirdiHatasi as hata:
        raise GirdiHatasi(f"tanzil.lock.json: {hata}") from None
    if not isinstance(veri, dict) or set(veri) not in ({"varyantlar"}, {"varyantlar", "ust_veri"}):
        raise GirdiHatasi("tanzil.lock.json: ust alanlar 'varyantlar' ve 'ust_veri' olmali")
    varyantlar = veri["varyantlar"]
    if not isinstance(varyantlar, dict) or set(varyantlar) != set(VARYANTLAR):
        raise GirdiHatasi(f"tanzil.lock.json: varyantlar {', '.join(VARYANTLAR)} olmali")
    girdiler = {ad: _kilit_girdisi(ad, varyantlar[ad]) for ad in VARYANTLAR}
    ust_veri = _ust_veri_kilidi(veri["ust_veri"]) if "ust_veri" in veri else None
    return girdiler, ust_veri


def kilit_coz(ham: bytes) -> dict[str, KilitGirdisi]:
    """Metin varyantlarinin kilidi (`varyantlar`); `ust_veri` bolumu de kati denetlenir."""
    return kilit_coz_tam(ham)[0]


def kilit_yukle(yol: Path | None = None) -> dict[str, KilitGirdisi]:
    """Kilit dosyasini okur (varsayilan: paketteki `tanzil.lock.json`)."""
    hedef = yol if yol is not None else KILIT_YOLU
    try:
        ham = hedef.read_bytes()
    except OSError:
        raise GirdiHatasi("tanzil.lock.json okunamadi") from None
    return kilit_coz(ham)


def ust_veri_kilidi_yukle(yol: Path | None = None) -> UstVeriKilidi:
    """Kilit dosyasindaki `ust_veri` bolumu; bolum yoksa `GirdiHatasi`."""
    hedef = yol if yol is not None else KILIT_YOLU
    try:
        ham = hedef.read_bytes()
    except OSError:
        raise GirdiHatasi("tanzil.lock.json okunamadi") from None
    kilit = kilit_coz_tam(ham)[1]
    if kilit is None:
        raise GirdiHatasi("tanzil.lock.json: ust_veri bolumu yok")
    return kilit


def kilit_metni(girdiler: dict[str, KilitGirdisi], ust_veri: UstVeriKilidi | None = None) -> str:
    """Kilit dosyasinin kanonik metni (varyantlar, varsa ust_veri; alan sirasi sabit, ASCII, LF)."""
    govde: dict[str, object] = {"varyantlar": {ad: girdiler[ad].sozluk() for ad in VARYANTLAR}}
    if ust_veri is not None:
        govde["ust_veri"] = ust_veri.sozluk()
    return json.dumps(govde, ensure_ascii=True, indent=2) + "\n"


def kilit_onerisi(varyant: str, veri: bytes, tarih: str) -> KilitGirdisi:
    """Gelen dosyasinin baytlarindan ilk kilit degerlerini hesaplar (hicbir sey yazmaz)."""
    ayrisma = tanzil_bicim.ayristir(veri)
    tur, surum = tanzil_bicim.bildirim_basligi(ayrisma.bildirim)
    if tur != BASLIK_TURU[_varyant(varyant)]:
        raise GirdiHatasi("dosya basligindaki tur varyantla uyusmuyor")
    return KilitGirdisi(
        varyant=varyant,
        url=FORM_ADRESI,
        secenekler=dict(SECENEKLER),
        surum=surum,
        alinma_tarihi=tarih,
        boyut=len(veri),
        sha256=lineage.sha256_bayt(veri),
        metin_sha256=ayrisma.metin_sha256,
        bildirim_sha256=ayrisma.bildirim_sha256,
    )


def uyusmazlik_iletisi(kilit: KilitGirdisi, ozet: str, boyut: int, fark: str) -> str:
    """Dosya ozeti kilitle tutmadiginda hata iletisi; `ILETI_EN_UZUN` icinde kalir.

    Konsola yazilan ileti `ILETI_EN_UZUN` karakterde kesilir (`logs.ileti_temizle`); UYARI en
    sonda durdugu icin uzun bir `fark` onu keserdi. Degisken parca (`fark`) sigacak kadar
    kisaltilir ("..." ile); sabit parcalar ve UYARI hicbir durumda kesilmez.
    """
    bas = (
        f"{kilit.kaynak}: dosya ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
        f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{boyut}): "
    )
    son = f". {UYARI}"
    pay = ILETI_EN_UZUN - len(bas) - len(son)
    if len(fark) > pay:
        fark = fark[: max(pay - 3, 0)] + "..."
    return bas + fark + son


def kilit_denetle(kilit: KilitGirdisi, veri: bytes, *, tam: bool = True) -> tanzil_bicim.Ayrisma:
    """Gelen dosyasini kilitle karsilastirir (`data/raw`a kopyalamadan ONCE).

    Dosya ozeti, boyut ve bicim kilitle tutarsa ayrismayi dondurur. Tutmazsa `GirdiHatasi`
    (cikis 2) verir ve farki tanilar: yalniz bildirim blogunda, yalniz ayet satirlarinda,
    her ikisinde ya da dosya bicimi bozuk. Iletide dosya icerigi yoktur; yalniz kisaltilmis
    ozetler ve bayt sayilari.
    """
    ozet = lineage.sha256_bayt(veri)
    if ozet == kilit.sha256 and len(veri) == kilit.boyut:
        try:
            ayrisma = tanzil_bicim.ayristir(veri, tam=tam)
        except GirdiHatasi as hata:
            raise GirdiHatasi(
                f"{kilit.kaynak}: kilitle tutan dosyanin bicimi gecersiz: {hata}"
            ) from None
        if (
            ayrisma.metin_sha256 != kilit.metin_sha256
            or ayrisma.bildirim_sha256 != kilit.bildirim_sha256
        ):
            raise GirdiHatasi(
                f"{kilit.kaynak}: kilit kaydi tutarsiz"
                " (dosya ozeti tutuyor, parca ozetleri tutmuyor)"
            )
        return ayrisma
    try:
        ayrisma = tanzil_bicim.ayristir(veri, tam=tam)
    except GirdiHatasi as hata:
        fark = f"dosya bicimi gecersiz ({hata})"
    else:
        metin_ayni = ayrisma.metin_sha256 == kilit.metin_sha256
        bildirim_ayni = ayrisma.bildirim_sha256 == kilit.bildirim_sha256
        if metin_ayni and not bildirim_ayni:
            fark = "fark yalniz bildirim blogunda (ayet satirlari kilitle ayni)"
        elif bildirim_ayni and not metin_ayni:
            fark = "fark ayet satirlarinda (bildirim blogu kilitle ayni)"
        elif not metin_ayni:
            fark = "fark hem ayet satirlarinda hem bildirim blogunda"
        else:
            fark = "kilit kaydi tutarsiz (parca ozetleri tutuyor, dosya ozeti tutmuyor)"
    raise GirdiHatasi(uyusmazlik_iletisi(kilit, ozet, len(veri), fark))


# --- gelen klasoru -----------------------------------------------------------------------


def gelen_kok(veri_kok: Path) -> Path:
    return veri_kok / GELEN_KLASORU / GELEN_KAYNAK


def gelen_tarihleri(gelen: Path) -> list[str]:
    """`gelen` altindaki gecerli tarih klasorlerinin adlari, eskiden yeniye."""
    if not gelen.is_dir():
        return []
    return sorted(yol.name for yol in gelen.iterdir() if yol.is_dir() and tarih_gecerli(yol.name))


def gelen_tarihi_coz(gelen: Path, istenen: str | None) -> str:
    """`--gelen-tarih` ya da (verilmediyse) en yeni tarih klasoru."""
    if istenen is not None:
        if not tarih_gecerli(istenen):
            raise GirdiHatasi("--gelen-tarih YYYY-AA-GG biciminde gecerli bir tarih olmali")
        return istenen
    tarihler = gelen_tarihleri(gelen)
    if not tarihler:
        raise GirdiHatasi(f"{GELEN_KLASORU}/{GELEN_KAYNAK} altinda tarih klasoru yok")
    return tarihler[-1]


def gelen_oku(gelen: Path, tarih: str, varyant: str) -> bytes:
    """Gelen dosyasinin baytlari; dosya yoksa, okunamiyorsa ya da cok buyukse `GirdiHatasi`."""
    ad = dosya_adi(varyant)
    goreli = f"{GELEN_KLASORU}/{GELEN_KAYNAK}/{tarih}/{ad}"
    yol = gelen / tarih / ad
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_GELEN_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_GELEN_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


# --- bagdastirici ------------------------------------------------------------------------


class TanzilBagdastirici:
    """`SourceAdapter`: bir Tanzil varyantini `data/gelen`den alir (K-39).

    `kilit` verilmezse paketteki kilit okunur; testler kendi kilidini verir. `tam=False` yalniz
    fiksturdeki dosya parcalari icindir (komut her zaman `tam=True` kullanir).
    """

    def __init__(
        self,
        varyant: str,
        *,
        gelen_tarih: str | None = None,
        kilit: KilitGirdisi | None = None,
        tam: bool = True,
    ) -> None:
        self.varyant = _varyant(varyant)
        self.source_id = kaynak_kimligi(varyant)
        self._istenen_tarih = gelen_tarih
        self._kilit = kilit if kilit is not None else kilit_yukle()[varyant]
        self._tam = tam
        self._tarih: str | None = None
        self._duzen: tanzil_bicim.Duzen | None = None

    @property
    def kilit(self) -> KilitGirdisi:
        return self._kilit

    # --- fetch ---

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        gelen = gelen_kok(ctx.veri_kok)
        tarih = gelen_tarihi_coz(gelen, self._istenen_tarih)
        self._tarih = tarih
        veri = gelen_oku(gelen, tarih, self.varyant)
        kilit_denetle(self._kilit, veri, tam=self._tam)  # tutmazsa raw'a hicbir sey yazilmaz
        yol, yeni = self._ham_yol(ctx, gelen / tarih / dosya_adi(self.varyant), tarih, veri)
        ctx.sayi("ham_boyut", len(veri))
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        ctx.gunluk.yaz(
            "INFO",
            "tanzil_fetch",
            source_id=self.source_id,
            sayilar={"boyut": len(veri), "ham_yeni": 1 if yeni else 0},
        )
        return [RawFile(yol, self._kilit.sha256, self._kilit.url)]

    def _ham_yol(
        self, ctx: RunContext, gelen_yol: Path, tarih: str, veri: bytes
    ) -> tuple[Path, bool]:
        """Ham kopyanin yolu ve yeni acilip acilmadigi. `--dry-run`da raw'a yazilmaz."""
        ad = dosya_adi(self.varyant)
        kok = ctx.raw_dizin(self.source_id)
        mevcut = _mevcut_ham(kok, ad, self._kilit)
        if mevcut is not None:
            return mevcut, False
        hedef = kok / tarih
        if hedef.exists():  # dry-run'da da denetlenir: gercek kosu ayni hatayla durur
            raise GirdiHatasi(
                f"raw/{self.source_id}/{tarih} zaten var ve baska bir dosya tasiyor"
                " (data/raw degismez); yeni bir gelen tarih klasoru kullanin"
            )
        if ctx.dry_run:
            return gelen_yol, False
        gecici = kok / f".{tarih}.gecici-{ctx.run_id}"
        try:
            gecici.mkdir(parents=True)
            # Dosyalar diske esitlenmeden klasor gorunur olmasin: guc kesilirse raw altinda
            # sifir uzunluklu dosya kalir ve sonraki kosu `data/raw degismez` ile durur.
            _yaz_esitle(gecici / ad, veri)
            _yaz_esitle(gecici / FETCH_ADI, json_baytlari(self._fetch_kaydi(tarih)))
            _klasoru_tasi(gecici, hedef)  # klasor ya tam gorunur ya hic
        except OSError:
            # Es zamanli baska bir kosu ayni baytlari az once raw'a almis olabilir.
            esdeger = _mevcut_ham(kok, ad, self._kilit)
            if esdeger is not None:
                return esdeger, False
            raise GirdiHatasi(f"raw/{self.source_id}/{tarih} yazilamadi") from None
        finally:
            if gecici.exists():
                shutil.rmtree(gecici, ignore_errors=True)
        return hedef / ad, True

    def _fetch_kaydi(self, tarih: str) -> dict[str, object]:
        k = self._kilit
        return {
            "kaynak": self.source_id,
            "varyant": self.varyant,
            "dosya": dosya_adi(self.varyant),
            "url": k.url,
            "secenekler": dict(k.secenekler),
            "surum": k.surum,
            "alinma_tarihi": tarih,
            "boyut": k.boyut,
            "sha256": k.sha256,
            "gelen_yol": f"{GELEN_KLASORU}/{GELEN_KAYNAK}/{tarih}/{dosya_adi(self.varyant)}",
        }

    # --- parse ---

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        if len(files) != 1:
            raise GirdiHatasi("tanzil: tek ham dosya bekleniyor")
        dosya = files[0]
        try:
            veri = dosya.path.read_bytes()
        except OSError:
            raise GirdiHatasi("ham dosya okunamadi") from None
        ayrisma = tanzil_bicim.ayristir(veri, tam=self._tam)
        if (
            ayrisma.metin_sha256 != self._kilit.metin_sha256
            or ayrisma.bildirim_sha256 != self._kilit.bildirim_sha256
        ):
            raise GirdiHatasi(f"{self.source_id}: ayristirilan ozetler kilitle tutmuyor")
        self._duzen = ayrisma.duzen
        if not ctx.dry_run:
            klasor = ctx.staged_dizin(self.source_id)
            klasor.mkdir(parents=True, exist_ok=True)
            (klasor / NOTICE_ADI).write_bytes(ayrisma.bildirim)  # bayt bayt (K-39 madde 6)
        ad = dosya_adi(self.varyant)
        for ay in ayrisma.ayetler:
            yield StagedUnit(
                anchor=ay.capa,
                text=ay.metin,
                attrs={},
                provenance={
                    "file": ad,
                    "sha256": dosya.sha256,
                    "line": ay.satir,
                    "bayt": [ay.bayt_bas, ay.bayt_son],
                    "steps": [],
                },
            )

    def manifest_ayrintilari(self) -> dict[str, object]:
        """Manifestin `ayrintilar` alani: varyant, kilit ozetleri ve dosyanin satir duzeni."""
        if self._duzen is None:
            return {}
        k = self._kilit
        return {
            "varyant": self.varyant,
            "surum": k.surum,
            "gelen_tarih": self._tarih,
            "kilit": {
                "boyut": k.boyut,
                "sha256": k.sha256,
                "metin_sha256": k.metin_sha256,
                "bildirim_sha256": k.bildirim_sha256,
            },
            "duzen": self._duzen.sozluk(),
        }


def _yaz_esitle(yol: Path, veri: bytes) -> None:
    """Dosyayi yazar, tamponlari bosaltir ve diske esitler (`lineage.manifest_yaz` gibi)."""
    with yol.open("wb") as dosya:
        dosya.write(veri)
        dosya.flush()
        os.fsync(dosya.fileno())


def _klasoru_tasi(kaynak: Path, hedef: Path) -> None:
    """`kaynak` klasorunu `hedef` adina tasir; gecici `PermissionError`da birkac kez dener."""
    for deneme in range(1, YENIDEN_ADLANDIRMA_DENEMESI + 1):
        try:
            kaynak.rename(hedef)
        except PermissionError:
            if deneme == YENIDEN_ADLANDIRMA_DENEMESI:
                raise
            time.sleep(0.2 * deneme)
        else:
            return


def _mevcut_ham(kok: Path, ad: str, kilit: KilitGirdisi) -> Path | None:
    """`raw/<kaynak>/` altinda ayni baytlara sahip kopya varsa (en eski tarih) yolu."""
    if not kok.is_dir():
        return None
    for klasor in sorted(kok.iterdir(), key=lambda yol: yol.name):
        if not klasor.is_dir() or TARIH_DESENI.fullmatch(klasor.name) is None:
            continue
        aday = klasor / ad
        if (
            aday.is_file()
            and aday.stat().st_size == kilit.boyut
            and lineage.sha256_dosya(aday) == kilit.sha256
        ):
            return aday
    return None


# --- komutlar ----------------------------------------------------------------------------


def kilit_oner_metni(depo_kok: Path, veri_kok: Path, varyant: str, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen dosyasindan hesaplanan kilit girdisi (JSON); hicbir sey yazilmaz."""
    slug = kaynak_kimligi(varyant)
    kayit = {s.dosya.removesuffix(".toml"): s for s in sources.yukle(depo_kok)}.get(slug)
    if kayit is None or kayit.kaynak is None:
        raise GirdiHatasi(f"kaynak kaydi: {slug}: kayitsiz ya da gecersiz (mutalaa sources check)")
    gelen = gelen_kok(veri_kok)
    tarih = gelen_tarihi_coz(gelen, gelen_tarih)
    kilit = kilit_onerisi(varyant, gelen_oku(gelen, tarih, varyant), tarih)
    return json.dumps({"varyantlar": {varyant: kilit.sozluk()}}, ensure_ascii=True, indent=2) + "\n"


def komut_ingest_tanzil(
    *,
    varyant: str,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest tanzil` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`)."""
    slug = kaynak_kimligi(varyant)

    def govde(ctx: RunContext) -> int:
        bagdastirici = TanzilBagdastirici(varyant, gelen_tarih=gelen_tarih)
        sonuc = run_ingest(bagdastirici, ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {slug}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest tanzil --variant {varyant}",
        adim=INGEST_ADIMI,
        kaynaklar=[slug],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"variant": varyant},
    )
