"""Meal alimi ortak adimlari (A16.2): gelen dosyalar, kilit denetimi, ham kopya, komut.

Uc kaynagin (`elmalili-meal`, `elmalili-sade-meal`, `elmalili-meal-epub`) ortak kalibi:

1. `data/gelen/<kaynak>/<YYYY-AA-GG>/` altindaki dosyalar bayt olarak okunur ve kilitle
   (`elmalili_meal.lock.json`: boyut ve SHA-256) karsilastirilir. Tutmazsa HER DURUMDA cikis 2
   ve "kilit guncellenerek (/karar) alinir" uyarisi (K-49 madde 11); `data/raw`'a hicbir sey
   yazilmaz. Dosyalar yalniz VERI olarak okunur, hicbir sey calistirilmaz.
2. Kilitten sonra dosyalar `data/raw/<kaynak>/<tarih>/` altina `fetch.json` ile kopyalanir
   (`fsync`; klasor ya tam gorunur ya hic). Ayni baytlar `raw` altinda zaten varsa yeni kopya
   acilmaz; ayni tarih baska baytlarla doluysa cikis 2 (`data/raw` degismez).
3. Parmak izi, staged ve manifest `run_ingest` (birim ureten kaynaklar) ya da `tanik_ingest`
   (tanik: birimsiz `tanik.jsonl`) ile yazilir.

Hata iletileri yalniz kisaltilmis ozet, bayt sayisi ve goreli yol tasir; dosya icerigi asla.
A10 ve A11 yardimcilari (`_yaz_esitle`, `_klasoru_tasi`, `tarih_gecerli`) tasinmadan ice aktarilir.
"""

import shutil
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_kaynaklari as kayitlar
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest
from mutalaa_pipeline.ingest.meal_kilit import DosyaKilidi
from mutalaa_pipeline.ingest.tanzil import (
    FETCH_ADI,
    GELEN_KLASORU,
    INGEST_ADIMI,
    TARIH_DESENI,
    _klasoru_tasi,
    _yaz_esitle,
    tarih_gecerli,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import kisa_ozet
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz

EN_BUYUK_GELEN_BAYT: Final = 8 << 20  # gercek dosyalar en cok 1,5 MB'dir
UYARI: Final = "Yeni meal kaynagi kilit guncellenerek (/karar) alinir."


def gelen_dizini(veri_kok: Path, slug: str) -> Path:
    return veri_kok / GELEN_KLASORU / slug


def gelen_tarihi_coz(gelen: Path, istenen: str | None, slug: str) -> str:
    """`--gelen-tarih` ya da (verilmediyse) en yeni gecerli tarih klasoru."""
    if istenen is not None:
        if not tarih_gecerli(istenen):
            raise GirdiHatasi("--gelen-tarih YYYY-AA-GG biciminde gecerli bir tarih olmali")
        return istenen
    tarihler = (
        sorted(p.name for p in gelen.iterdir() if p.is_dir() and tarih_gecerli(p.name))
        if gelen.is_dir()
        else []
    )
    if not tarihler:
        raise GirdiHatasi(f"{GELEN_KLASORU}/{slug} altinda tarih klasoru yok")
    return tarihler[-1]


def gelen_oku(gelen: Path, tarih: str, slug: str, ad: str) -> bytes:
    """Gelen dosyanin baytlari; dosya yoksa, okunamiyorsa ya da cok buyukse `GirdiHatasi`."""
    goreli = f"{GELEN_KLASORU}/{slug}/{tarih}/{ad}"
    yol = gelen / tarih / ad
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{goreli} yok (--gelen-tarih ile baska bir klasor verilebilir)")
        if yol.stat().st_size > EN_BUYUK_GELEN_BAYT:
            raise GirdiHatasi(f"{goreli} cok buyuk (sinir {EN_BUYUK_GELEN_BAYT} bayt)")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{goreli} okunamadi") from None


def kilit_denetle(slug: str, kilit: DosyaKilidi, veri: bytes) -> None:
    """Dosya boyutu ve SHA-256'si kilitle tutmuyorsa `GirdiHatasi` (cikis 2)."""
    ozet = lineage.sha256_bayt(veri)
    if ozet != kilit.sha256 or len(veri) != kilit.boyut:
        raise GirdiHatasi(
            f"{slug}: {kilit.ad} ozeti kilitle tutmuyor (beklenen {kisa_ozet(kilit.sha256)},"
            f" bulunan {kisa_ozet(ozet)}; boyut {kilit.boyut}/{len(veri)}). {UYARI}"
        )


def gelenleri_oku(
    ctx: RunContext, slug: str, istenen_tarih: str | None, dosyalar: Sequence[DosyaKilidi]
) -> tuple[str, dict[str, bytes]]:
    """Kilitli dosyalarin hepsini gelen klasorunden okur ve kilitle karsilastirir."""
    gelen = gelen_dizini(ctx.veri_kok, slug)
    tarih = gelen_tarihi_coz(gelen, istenen_tarih, slug)
    icerik: dict[str, bytes] = {}
    for kilit in dosyalar:
        veri = gelen_oku(gelen, tarih, slug, kilit.ad)
        kilit_denetle(slug, kilit, veri)
        icerik[kilit.ad] = veri
    return tarih, icerik


# --- ham kopya -----------------------------------------------------------------------------


def _mevcut_ham(kok: Path, icerik: Mapping[str, bytes]) -> Path | None:
    """`raw/<kaynak>/` altinda ayni dosyalara sahip klasor varsa (en eski tarih) yolu."""
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
    ctx: RunContext,
    slug: str,
    tarih: str,
    icerik: Mapping[str, bytes],
    fetch_kaydi: Mapping[str, object],
) -> tuple[dict[str, Path], bool]:
    """Dosyalarin ham kopya yollari ve yeni klasor acilip acilmadigi.

    `--dry-run`da `data/raw`'a yazilmaz (yollar gelen klasorunu gosterir). Mevcut ayni baytlar
    yeniden kullanilir; ayni tarihli baska icerikli klasor `GirdiHatasi` verir.
    """
    kok = ctx.raw_dizin(slug)
    mevcut = _mevcut_ham(kok, icerik)
    if mevcut is not None:
        return {ad: mevcut / ad for ad in icerik}, False
    hedef = kok / tarih
    if hedef.exists():  # dry-run'da da denetlenir: gercek kosu ayni hatayla durur
        raise GirdiHatasi(
            f"raw/{slug}/{tarih} zaten var ve baska dosyalar tasiyor"
            " (data/raw degismez); yeni bir gelen tarih klasoru kullanin"
        )
    if ctx.dry_run:
        gelen = gelen_dizini(ctx.veri_kok, slug) / tarih
        return {ad: gelen / ad for ad in icerik}, False
    gecici = kok / f".{tarih}.gecici-{ctx.run_id}"
    try:
        gecici.mkdir(parents=True)
        for ad, veri in icerik.items():
            _yaz_esitle(gecici / ad, veri)
        _yaz_esitle(gecici / FETCH_ADI, json_baytlari(dict(fetch_kaydi)))
        _klasoru_tasi(gecici, hedef)  # klasor ya tam gorunur ya hic
    except OSError:
        esdeger = _mevcut_ham(kok, icerik)  # es zamanli kosu ayni baytlari almis olabilir
        if esdeger is not None:
            return {ad: esdeger / ad for ad in icerik}, False
        raise GirdiHatasi(f"raw/{slug}/{tarih} yazilamadi") from None
    finally:
        if gecici.exists():
            shutil.rmtree(gecici, ignore_errors=True)
    return {ad: hedef / ad for ad in icerik}, True


def fetch_kaydi(
    slug: str, tarih: str, url: str, kilit_sha256: str, dosyalar: Sequence[DosyaKilidi]
) -> dict[str, object]:
    return {
        "kaynak": slug,
        "alinma_tarihi": tarih,
        "url": url,
        "kilit_sha256": kilit_sha256,
        "dosyalar": [d.sozluk() for d in sorted(dosyalar, key=lambda d: d.ad)],
        "gelen_yol": f"{GELEN_KLASORU}/{slug}/{tarih}",
    }


# --- bagdastirici ortak govdesi ------------------------------------------------------------


class MealBagdastirici(Protocol):
    """Uc bagdastiricinin ortak yuzu (`SourceAdapter` + manifest kancasi)."""

    source_id: str

    def fetch(self, ctx: RunContext) -> list[RawFile]: ...

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]: ...

    def manifest_ayrintilari(self) -> dict[str, object]: ...


class TanikBagdastirici(Protocol):
    """Tanik bagdastiricisi: birim degil, `tanik.jsonl` satirlari uretir."""

    source_id: str

    def fetch(self, ctx: RunContext) -> list[RawFile]: ...

    def tanik_satirlari(self, ctx: RunContext, files: list[RawFile]) -> list[dict[str, object]]: ...

    def manifest_ayrintilari(self) -> dict[str, object]: ...


@dataclass(frozen=True)
class TanikSonucu:
    run_id: str
    atlandi: bool
    satir_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def raw_dosyalari(
    ctx: RunContext, yollar: Mapping[str, Path], icerik: Mapping[str, bytes]
) -> list[RawFile]:
    """`run_ingest` icin ham dosya listesi (ad sirasinda)."""
    return [RawFile(yollar[ad], lineage.sha256_bayt(icerik[ad])) for ad in sorted(icerik)]


def tanik_ingest(adapter: TanikBagdastirici, ctx: RunContext) -> TanikSonucu:
    """Tanik icin `run_ingest` kalibi: kayit, `fetch`, parmak izi, `tanik.jsonl`, manifest."""
    slug = adapter.source_id
    ctx.require_sources(slug)  # kayitsiz ya da gecersiz kayitta cikis 2
    ctx.gunluk.yaz("INFO", "ingest_basla", source_id=slug)
    dosyalar = adapter.fetch(ctx)
    girdiler: list[lineage.Girdi] = []
    for dosya in dosyalar:
        if lineage.sha256_dosya(dosya.path) != dosya.sha256:
            raise GirdiHatasi(f"ham dosya ozeti tutmuyor: sha256 {dosya.sha256}")
        girdiler.append(
            lineage.Girdi(yol=lineage.goreli_yol(ctx.veri_kok, dosya.path), sha256=dosya.sha256)
        )
    parmak = ctx.parmak_izi(girdiler)
    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(slug), ctx.adim)
    if lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "ingest_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return TanikSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    satirlar = adapter.tanik_satirlari(ctx, dosyalar)
    cikti = dosya_yaz(ctx, slug, lineage.TANIK_ADI, satirlar, anahtar=("sure", "ayet"))
    ctx.sayi("tanik", cikti.satir or 0)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "ingest_dry_run", source_id=slug, sayilar={"tanik": cikti.satir})
        return TanikSonucu(ctx.run_id, False, cikti.satir or 0, None)
    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar=adapter.manifest_ayrintilari(),
    )
    ctx.gunluk.yaz("INFO", "ingest_bitti", source_id=slug, sayilar={"tanik": cikti.satir})
    return TanikSonucu(ctx.run_id, False, cikti.satir or 0, klasor)


def bagdastirici_olustur(slug: str, gelen_tarih: str | None) -> object:
    """Kaynagin bagdastiricisi: modulun `bagdastirici_olustur(gelen_tarih=...)` fabrikasi."""
    modul = kayitlar.bagdastirici_modulu(slug)
    fabrika: Callable[..., object] | None = getattr(modul, "bagdastirici_olustur", None)
    if fabrika is None:
        raise GirdiHatasi("meal bagdastiricisi tanimli degil")
    return fabrika(gelen_tarih=gelen_tarih)


def komut_ingest_meal(
    *,
    source: str,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest meal --source <kimlik>` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        if not kayitlar.kayitli_mi(source):
            raise GirdiHatasi("ingest meal: bilinmeyen meal kaynagi (elmalili-meal, ...)")
        adapter = bagdastirici_olustur(source, gelen_tarih)
        if kayitlar.tanik_mi(source):
            sonuc_t = tanik_ingest(adapter, ctx)  # type: ignore[arg-type]
            if sonuc_t.atlandi:
                ozet = (
                    f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc_t.onceki_run_id})"
                )
            elif ctx.dry_run:
                ozet = f"{sonuc_t.satir_sayisi} tanik satiri (dry-run, hicbir sey yazilmadi)"
            else:
                ozet = f"{sonuc_t.satir_sayisi} tanik satiri, run {sonuc_t.run_id}"
            sys.stdout.write(f"ingest {source}: {ozet}\n")
            return cikis.BASARILI
        sonuc = run_ingest(adapter, ctx)  # type: ignore[arg-type]
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {source}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"ingest meal --source {source}",
        adim=INGEST_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )
