"""`mutalaa` komut satiri girisi."""

from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline import cikis, sources
from mutalaa_pipeline.export import ayet_sayilari, ic_kesme, test_vectors
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz

app = typer.Typer(
    name="mutalaa",
    help="Mutalaa icerik hatti.",
    no_args_is_help=True,
    add_completion=False,
)

export_app = typer.Typer(no_args_is_help=True, help="Disa aktarim: veri dosyalari ve vektorler.")
app.add_typer(export_app, name="export")

sources_app = typer.Typer(no_args_is_help=True, help="Kaynak kayitlari ve lisans durumlari.")
app.add_typer(sources_app, name="sources")

KokSecenegi = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]


@app.callback()
def main() -> None:
    """Mutalaa icerik hatti komutlari."""


class Bicim(StrEnum):
    JSON = "json"
    TABLO = "tablo"


def bugun() -> date:
    """Yeniden kontrol karsilastirmasinin bugunu (testlerde degistirilebilir)."""
    return datetime.now(UTC).date()


def _hata(hata: GirdiHatasi) -> typer.Exit:
    typer.echo(f"hata: {hata}", err=True)
    return typer.Exit(code=2)


@export_app.command("ayet-sayilari")
def export_ayet_sayilari(
    kaynak: Annotated[
        Path | None, typer.Option("--kaynak", help="Tanzil quran-data.xml dosyasi.")
    ] = None,
    url: Annotated[str | None, typer.Option("--url", help="Dosyanin indirildigi adres.")] = None,
    tarih: Annotated[str | None, typer.Option("--tarih", help="Alinma tarihi, YYYY-AA-GG.")] = None,
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    kok: KokSecenegi = None,
) -> None:
    """Sure basina ayet sayilarini (JSON) ve uc dildeki kopyalarini uretir."""
    try:
        depo = kok_coz(kok)
        if check:
            if kaynak is not None or url is not None or tarih is not None:
                raise GirdiHatasi("--check ile --kaynak, --url ve --tarih verilmez")
            farklar = ayet_sayilari.denetle(depo)
            if farklar:
                for yol in farklar:
                    typer.echo(f"fark: {yol}")
                raise typer.Exit(code=1)
            typer.echo("ayet-sayilari: fark yok")
            return
        if kaynak is None or url is None or tarih is None:
            raise GirdiHatasi("--kaynak, --url ve --tarih birlikte verilmeli (ya da --check)")
        yazilanlar = ayet_sayilari.uret(depo, kaynak, url, tarih)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("ayet-sayilari: degisiklik yok")


@export_app.command("test-vectors")
def export_test_vectors(
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    kok: KokSecenegi = None,
) -> None:
    """`shared/test-vectors` dosyalarinin hesaplanan alanlarini ve sinir satirlarini uretir."""
    try:
        depo = kok_coz(kok)
        if check:
            farklar = test_vectors.denetle(depo)
            if farklar:
                for fark in farklar:
                    typer.echo(f"fark: {fark}")
                raise typer.Exit(code=1)
            typer.echo("test-vectors: fark yok")
            return
        yazilanlar = test_vectors.uret(depo)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("test-vectors: degisiklik yok")


@export_app.command("ic-kesme")
def export_ic_kesme(
    check: Annotated[
        bool, typer.Option("--check", help="Yazmadan diskle karsilastirir; fark varsa 1.")
    ] = False,
    kok: KokSecenegi = None,
) -> None:
    """`shared/data/ic-kesme.txt` listesinden TypeScript ve C# kopyalarini uretir."""
    try:
        depo = kok_coz(kok)
        if check:
            farklar = ic_kesme.denetle(depo)
            if farklar:
                for yol in farklar:
                    typer.echo(f"fark: {yol}")
                raise typer.Exit(code=1)
            typer.echo("ic-kesme: fark yok")
            return
        yazilanlar = ic_kesme.uret(depo)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    for yol in yazilanlar:
        typer.echo(f"yazildi: {yol}")
    if not yazilanlar:
        typer.echo("ic-kesme: degisiklik yok")


@sources_app.command("list")
def sources_list(
    bicim: Annotated[
        Bicim, typer.Option("--format", help="Cikti bicimi: tablo ya da json.")
    ] = Bicim.TABLO,
    kok: KokSecenegi = None,
) -> None:
    """`pipeline/sources/*.toml` kayitlarini listeler; gecmis yeniden kontrol `!` ile isaretli."""
    try:
        sonuclar = sources.yukle(kok_coz(kok), lisans_dosyalari=False)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    bozuk = False
    for sonuc in sonuclar:
        for mesaj in sonuc.hatalar:
            typer.echo(f"hata: {sonuc.dosya}: {mesaj}", err=True)
            bozuk = True
    if bozuk:
        raise typer.Exit(code=cikis.GIRDI_HATASI)
    kayitlar = [s.kaynak for s in sonuclar if s.kaynak is not None]
    satirlar = sources.satirlar(kayitlar, bugun())
    if bicim is Bicim.JSON:
        typer.echo(sources.json_metni(satirlar))
    elif satirlar:
        typer.echo(sources.tablo_metni(satirlar))
    else:
        typer.echo("kayit yok")


@sources_app.command("check")
def sources_check(kok: KokSecenegi = None) -> None:
    """Kaynak kayitlarini, lisans kopyalarini ve SHA-256 ozetlerini denetler (G-LIS)."""
    try:
        sonuclar = sources.yukle(kok_coz(kok), lisans_dosyalari=True)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    hata_sayisi = 0
    uyari_sayisi = 0
    for sonuc in sonuclar:
        for mesaj in sonuc.hatalar:
            typer.echo(f"hata: {sonuc.dosya}: {mesaj}", err=True)
            hata_sayisi += 1
        for mesaj in sonuc.uyarilar:
            typer.echo(f"uyari: {sonuc.dosya}: {mesaj}", err=True)
            uyari_sayisi += 1
        if sonuc.kaynak is not None and sources.gecmis_mi(sonuc.kaynak, bugun()):
            typer.echo(
                f"uyari: {sonuc.dosya}: yeniden kontrol tarihi gecti: {sonuc.kaynak.slug}",
                err=True,
            )
            uyari_sayisi += 1
    for ad in sources.yetim_kopyalar(kok_coz(kok), sonuclar):
        typer.echo(f"uyari: licenses/{ad}: hicbir kayit bu lisans kopyasini gostermiyor", err=True)
        uyari_sayisi += 1
    if not sonuclar:
        typer.echo("kayit yok")
    else:
        typer.echo(
            f"sources check: {len(sonuclar)} kayit, {hata_sayisi} hata, {uyari_sayisi} uyari"
        )
    if hata_sayisi:
        raise typer.Exit(code=cikis.GIRDI_HATASI)
