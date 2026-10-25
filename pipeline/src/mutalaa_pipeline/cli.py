"""`mutalaa` komut satiri girisi."""

from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline.export import ayet_sayilari, test_vectors
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz

app = typer.Typer(
    name="mutalaa",
    help="Mutalaa icerik hatti.",
    no_args_is_help=True,
    add_completion=False,
)

export_app = typer.Typer(no_args_is_help=True, help="Disa aktarim: veri dosyalari ve vektorler.")
app.add_typer(export_app, name="export")

KokSecenegi = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]


@app.callback()
def main() -> None:
    """Mutalaa icerik hatti komutlari."""


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
