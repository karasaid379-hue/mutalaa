"""`risale-rnk-metin` kaynagi: RNK `txt` + `json` bagdastiricisi ve komutu (A20.1b, K-52 madde 2).

`mutalaa ingest risale --source risale-rnk-metin` icin hazir govde (CLI kaydi `cli_risale.py`'de
yapilir):

1. `data/gelen/risale-baski-rnk/<tarih>/` altindaki 85 kitabin `.txt` ve `.json` dosyalari ve
   `shelves.json` bayt olarak okunur; boyut, SHA-256 ve MD5 `risale_rnk.lock.json` ile
   karsilastirilir. Tutmazsa HER DURUMDA cikis 2 (`data/raw`'a hicbir sey yazilmaz). Dosyalar
   yalniz VERI olarak okunur, hicbir sey calistirilmaz.
2. Kilitten sonra dosyalar `data/raw/risale-rnk-metin/<tarih>/{raf}/{uid}.{txt,json}` altina
   kopyalanir (`fetch.json` ile; klasor ya tam gorunur ya hic). Ayni baytlar `raw` altinda zaten
   varsa yeni kopya acilmaz; ayni tarih baska baytlarla doluysa cikis 2.
3. Her kitap `risale_rnk_staged.kitap_donustur` ile capali birimlere cevrilir (`units.jsonl`);
   yan dosyalar: `sayfalar.jsonl` (sayfa kirilma konumlari, A20.3 `page_map` girdisi),
   `yapi.jsonl` (bos ve ayirac satirlari), `kitaplar.jsonl` (dosya duzeyi bilgi ve sayilar).

K-52 madde 2: bu kaynak 85 RNK dosyasinin (87 kitap) tamaminin birimlerini uretir; Diyanet
birim olarak yuklenmez. Hata iletileri metin tasimaz.
"""

import hashlib
import shutil
import sys
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor.risale import Kitap, kitaplar
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_ortak
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest
from mutalaa_pipeline.ingest.meal_kilit import DosyaKilidi
from mutalaa_pipeline.ingest.risale_rnk import AYRISTIRICI_SURUMU
from mutalaa_pipeline.ingest.risale_rnk_kilit import (
    GELEN_KAYNAK,
    KATALOG_ADI,
    KAYNAK,
    UYARI,
    KitapKilidi,
    RnkKilidi,
    kilit_metni,
    kilit_ozeti,
    kilit_uret,
    kilit_yukle,
)
from mutalaa_pipeline.ingest.risale_rnk_staged import kitap_donustur
from mutalaa_pipeline.ingest.tanzil import (
    FETCH_ADI,
    INGEST_ADIMI,
    TARIH_DESENI,
    _klasoru_tasi,
    _yaz_esitle,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz

KATALOG_URL: Final = "https://rnknesriyat.com/res/metinler/json_files/shelves.json"
SAYFALAR_ADI: Final = "sayfalar.jsonl"
YAPI_ADI: Final = "yapi.jsonl"
KITAPLAR_ADI: Final = "kitaplar.jsonl"


def rnk_dosyalari(tablo: tuple[Kitap, ...] | None = None) -> dict[tuple[str, str], list[Kitap]]:
    """`(raf, uid) -> o dosyaya bagli kitaplar` (tablo sirasi); sunuhat uc kitaba baglidir."""
    sonuc: dict[tuple[str, str], list[Kitap]] = {}
    for kitap in tablo if tablo is not None else kitaplar():
        if kitap.rnk is None:
            raise GirdiHatasi("RNK baglantisi olmayan kitap")
        sonuc.setdefault((kitap.rnk.raf, kitap.rnk.uid), []).append(kitap)
    return sonuc


def _dosya_kilidi(ad: str, boyut: int, sha256: str) -> DosyaKilidi:
    return DosyaKilidi(ad=ad, boyut=boyut, sha256=sha256)


def kilit_dosyalari(kilit: RnkKilidi) -> list[DosyaKilidi]:
    """Kilitteki butun dosyalar (katalog dahil), ad sirasinda."""
    dosyalar = [_dosya_kilidi(KATALOG_ADI, kilit.katalog_boyut, kilit.katalog_sha256)]
    for kitap in kilit.kitaplar.values():
        dosyalar.append(
            _dosya_kilidi(f"{kitap.ad}.txt", kitap.sayi("boyut_txt"), kitap.metin("sha256_txt"))
        )
        dosyalar.append(
            _dosya_kilidi(f"{kitap.ad}.json", kitap.sayi("boyut_json"), kitap.metin("sha256_json"))
        )
    return sorted(dosyalar, key=lambda d: d.ad)


def kilit_tablo_uyumu(kilit: RnkKilidi, tablo: tuple[Kitap, ...] | None = None) -> None:
    """Kilitteki dosyalar `risale-kitaplar.json` tablosundaki RNK dosyalariyla ayni olmali."""
    beklenen = {f"{raf}/{uid}" for raf, uid in rnk_dosyalari(tablo)}
    if set(kilit.kitaplar) != beklenen:
        raise GirdiHatasi("kilit dosya kumesi kitap tablosuyla uyusmuyor")


# --- ham kopya -------------------------------------------------------------------------------


def _mevcut_ham(kok: Path, icerik: dict[str, bytes]) -> Path | None:
    if not kok.is_dir():
        return None
    ozetler = {ad: lineage.sha256_bayt(v) for ad, v in icerik.items()}
    for klasor in sorted(kok.iterdir(), key=lambda yol: yol.name):
        if not klasor.is_dir() or TARIH_DESENI.fullmatch(klasor.name) is None:
            continue
        if all(
            (klasor / ad).is_file()
            and (klasor / ad).stat().st_size == len(icerik[ad])
            and lineage.sha256_dosya(klasor / ad) == ozet
            for ad, ozet in ozetler.items()
        ):
            return klasor
    return None


def ham_kopyala(
    ctx: RunContext, tarih: str, icerik: dict[str, bytes], kayit: dict[str, object]
) -> tuple[dict[str, Path], bool]:
    """Dosyalari `data/raw/risale-rnk-metin/<tarih>/` altina kopyalar (alt klasorlu adlar)."""
    kok = ctx.raw_dizin(KAYNAK)
    mevcut = _mevcut_ham(kok, icerik)
    if mevcut is not None:
        return {ad: mevcut / ad for ad in icerik}, False
    hedef = kok / tarih
    if hedef.exists():
        raise GirdiHatasi(
            f"raw/{KAYNAK}/{tarih} zaten var ve baska dosyalar tasiyor"
            " (data/raw degismez); yeni bir gelen tarih klasoru kullanin"
        )
    if ctx.dry_run:
        gelen = meal_ortak.gelen_dizini(ctx.veri_kok, GELEN_KAYNAK) / tarih
        return {ad: gelen / ad for ad in icerik}, False
    gecici = kok / f".{tarih}.gecici-{ctx.run_id}"
    try:
        gecici.mkdir(parents=True)
        for ad, veri in icerik.items():
            hedef_dosya = gecici / ad
            hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
            _yaz_esitle(hedef_dosya, veri)
        _yaz_esitle(gecici / FETCH_ADI, json_baytlari(dict(kayit)))
        _klasoru_tasi(gecici, hedef)
    except OSError:
        esdeger = _mevcut_ham(kok, icerik)
        if esdeger is not None:
            return {ad: esdeger / ad for ad in icerik}, False
        raise GirdiHatasi(f"raw/{KAYNAK}/{tarih} yazilamadi") from None
    finally:
        if gecici.exists():
            shutil.rmtree(gecici, ignore_errors=True)
    return {ad: hedef / ad for ad in icerik}, True


# --- bagdastirici ------------------------------------------------------------------------------


class RnkBagdastirici:
    """`SourceAdapter`: RNK `txt` + `json` dosyalarini `data/gelen`den alir ve ayristirir."""

    source_id = KAYNAK

    def __init__(
        self,
        *,
        gelen_tarih: str | None = None,
        kilit: RnkKilidi | None = None,
        tablo: tuple[Kitap, ...] | None = None,
    ) -> None:
        self._istenen_tarih = gelen_tarih
        self._kilit = kilit if kilit is not None else kilit_yukle()
        self._tablo = tablo if tablo is not None else kitaplar()
        self._icerik: dict[str, bytes] = {}
        self._tarih = ""
        self._kilit_sha = ""
        self._birim = 0
        self._uyarilar: Counter[str] = Counter()

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        kilit_tablo_uyumu(self._kilit, self._tablo)
        gelen = meal_ortak.gelen_dizini(ctx.veri_kok, GELEN_KAYNAK)
        # Tarih yola eklenir: `YYYY-AA-GG` degilse (`../`, mutlak yol, takvimde olmayan tarih)
        # dosya aranmadan `GirdiHatasi` (cikis 2). Kilitteki tarih `kilit_coz`da denetlenir.
        tarih = (
            meal_ortak.gelen_tarihi_coz(gelen, self._istenen_tarih, GELEN_KAYNAK)
            if self._istenen_tarih is not None
            else self._kilit.gelen_tarih
        )
        dosyalar = kilit_dosyalari(self._kilit)
        icerik: dict[str, bytes] = {}
        for dosya in dosyalar:
            veri = meal_ortak.gelen_oku(gelen, tarih, GELEN_KAYNAK, dosya.ad)
            meal_ortak.kilit_denetle(dosya.ad, dosya, veri)
            icerik[dosya.ad] = veri
        for kitap in self._kilit.kitaplar.values():
            self._md5_denetle(kitap, icerik)
        ozet = kilit_ozeti(self._kilit)
        kayit: dict[str, object] = {
            "kaynak": KAYNAK,
            "alinma_tarihi": tarih,
            "url": KATALOG_URL,
            "kilit_sha256": ozet,
            "dosya_sayisi": len(dosyalar),
            "gelen_yol": f"gelen/{GELEN_KAYNAK}/{tarih}",
            "dosyalar": [d.sozluk() for d in dosyalar],
        }
        yollar, yeni = ham_kopyala(ctx, tarih, icerik, kayit)
        self._icerik = icerik
        self._tarih = tarih
        self._kilit_sha = ozet
        ctx.sayi("ham_dosya", len(icerik))
        ctx.sayi("ham_yeni", 1 if yeni else 0)
        return meal_ortak.raw_dosyalari(ctx, yollar, icerik)

    @staticmethod
    def _md5_denetle(kitap: KitapKilidi, icerik: dict[str, bytes]) -> None:
        for uzanti, alan in (("txt", "md5_txt"), ("json", "md5_json")):
            ozet = hashlib.md5(icerik[f"{kitap.ad}.{uzanti}"], usedforsecurity=False).hexdigest()
            if ozet != kitap.metin(alan):
                raise GirdiHatasi(f"{kitap.ad}.{uzanti}: MD5 kilitle tutmuyor. {UYARI}")

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        if not self._icerik:
            raise GirdiHatasi("fetch cagrilmadan parse")
        dosyalar = rnk_dosyalari(self._tablo)
        sayfalar: list[dict[str, object]] = []
        yapi: list[dict[str, object]] = []
        kitap_satirlari: list[dict[str, object]] = []
        for ad, kilit in self._kilit.kitaplar.items():
            sonuc = kitap_donustur(
                raf=kilit.raf,
                uid=kilit.uid,
                txt=self._icerik[f"{ad}.txt"],
                json_veri=self._icerik[f"{ad}.json"],
                txt_sha256=kilit.metin("sha256_txt"),
                kitaplar=dosyalar[(kilit.raf, kilit.uid)],
            )
            self._birim += len(sonuc.birimler)
            self._uyarilar.update(sonuc.uyarilar)
            sayfalar.extend(sonuc.sayfalar)
            yapi.extend(sonuc.yapi)
            kitap_satirlari.append(sonuc.kitap)
            yield from sonuc.birimler
        dosya_yaz(ctx, KAYNAK, SAYFALAR_ADI, sayfalar, anahtar=("dosya", "n"))
        dosya_yaz(ctx, KAYNAK, YAPI_ADI, yapi, anahtar=("dosya", "no"))
        dosya_yaz(ctx, KAYNAK, KITAPLAR_ADI, kitap_satirlari, anahtar=("dosya",))
        for ad_, sayi in self._uyarilar.items():
            ctx.sayi(f"uyari_{ad_}", sayi)

    def manifest_ayrintilari(self) -> dict[str, object]:
        return {
            "kaynak": KAYNAK,
            "gelen_kaynak": GELEN_KAYNAK,
            "gelen_tarih": self._tarih,
            "kilit_sha256": self._kilit_sha,
            "ayristirici_surumu": AYRISTIRICI_SURUMU,
            "kitap_dosyasi": len(self._kilit.kitaplar),
            "birim": self._birim,
            "uyarilar": dict(sorted(self._uyarilar.items())),
        }


def bagdastirici_olustur(*, gelen_tarih: str | None = None) -> RnkBagdastirici:
    return RnkBagdastirici(gelen_tarih=gelen_tarih)


# --- komutlar ----------------------------------------------------------------------------------


def komut_ingest_rnk(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest risale --source risale-rnk-metin` govdesi; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_ingest(bagdastirici_olustur(gelen_tarih=gelen_tarih), ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest risale --source {KAYNAK}",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )


def kilit_oner_metni(veri_kok: Path, gelen_tarih: str | None) -> str:
    """`--kilit-oner`: gelen klasorunden hesaplanan kilit (JSON); hicbir sey yazmaz."""
    gelen = meal_ortak.gelen_dizini(veri_kok, GELEN_KAYNAK)
    tarih = meal_ortak.gelen_tarihi_coz(gelen, gelen_tarih, GELEN_KAYNAK)
    return kilit_metni(kilit_uret(gelen=gelen, tarih=tarih, dosyalar=sorted(rnk_dosyalari())))


__all__ = [
    "KAYNAK",
    "RnkBagdastirici",
    "bagdastirici_olustur",
    "kilit_oner_metni",
    "komut_ingest_rnk",
]
