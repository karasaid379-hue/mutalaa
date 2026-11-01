"""`mutalaa` komut satiri girisi (cikis kodlari: `cikis.py`)."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline import cikis, sources
from mutalaa_pipeline.export import ayet_sayilari, ic_kesme, test_vectors
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz

app = typer.Typer(
    name="mutalaa",
    help=(
        "Mutalaa icerik hatti. Cikis kodlari: 0 basarili, 1 QA kapisi kaldi,"
        " 2 girdi ya da yapilandirma hatasi (kayitsiz ya da gecersiz kaynak kaydi dahil)."
    ),
    no_args_is_help=True,
    add_completion=False,
    # Iz (traceback) yerel degiskenleri gosterirse baglanti dizesi sizabilir.
    pretty_exceptions_show_locals=False,
)

export_app = typer.Typer(no_args_is_help=True, help="Disa aktarim: veri dosyalari ve vektorler.")
app.add_typer(export_app, name="export")

sources_app = typer.Typer(
    no_args_is_help=True, help="Kaynak kayitlari (pipeline/sources/*.toml): liste ve denetim."
)
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


def _hata(hata: GirdiHatasi) -> typer.Exit:
    typer.echo(f"hata: {hata}", err=True)
    return typer.Exit(code=cikis.GIRDI_HATASI)


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


@export_app.command("pg")
def export_pg_komutu(
    source: Annotated[str, typer.Option("--source", help="Kaynak kimligi, or. tanzil-uthmani.")],
    run: Annotated[
        str | None,
        typer.Option("--run", help="anchor run_id; verilmezse manifestli en son anchor."),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Islemi geri alir; hicbir satir yazmaz.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Kabul edilir; export pg parmak izi atlamaz (K-39).")
    ] = False,
    config: Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")] = None,
    kok: KokSecenegi = None,
) -> None:
    """Staged birimleri PostgreSQL'e yukler (tek islem, idempotent; K-39). Cikis 0, 1 ya da 2."""
    # Ice aktarma: psycopg ve yapilandirma yalniz bu komutta yuklenir.
    from mutalaa_pipeline.config import ayarlar_yukle
    from mutalaa_pipeline.export import pg

    try:
        depo = kok_coz(kok)
        ayarlar = ayarlar_yukle(config)
    except GirdiHatasi as hata:
        raise _hata(hata) from hata
    kod = pg.komut_export_pg(
        ayarlar, depo_kok=depo, source=source, run=run, dry_run=dry_run, force=force
    )
    if kod != cikis.BASARILI:
        raise typer.Exit(code=kod)


@sources_app.command("list")
def sources_list(
    bicim: Annotated[
        Bicim, typer.Option("--format", help="Cikti bicimi: tablo ya da json.")
    ] = Bicim.TABLO,
    kok: KokSecenegi = None,
) -> None:
    """`pipeline/sources/*.toml` kayitlarini listeler: slug, tur, surum, kaynak_url."""
    try:
        sonuclar = sources.yukle(kok_coz(kok))
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
    satirlar = sources.satirlar(kayitlar)
    if bicim is Bicim.JSON:
        typer.echo(sources.json_metni(satirlar))
    elif satirlar:
        typer.echo(sources.tablo_metni(satirlar))
    else:
        typer.echo("kayit yok")


@sources_app.command("check")
def sources_check(kok: KokSecenegi = None) -> None:
    """Kaynak kayitlarinin bicimini ve zorunlu alanlarini denetler (G-KAY); cikis 0 ya da 2."""
    try:
        sonuclar = sources.yukle(kok_coz(kok))
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
    if not sonuclar:
        typer.echo("kayit yok")
    else:
        typer.echo(
            f"sources check: {len(sonuclar)} kayit, {hata_sayisi} hata, {uyari_sayisi} uyari"
        )
    if hata_sayisi:
        raise typer.Exit(code=cikis.GIRDI_HATASI)
