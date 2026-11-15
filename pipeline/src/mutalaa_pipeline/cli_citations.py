"""Acik atif ve iktibas komutu (A18.4): `enrich citations` (`cli_qac.kaydet` ekler)."""

from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, Force, KokSecenegi

Hedef = Annotated[
    list[str],
    typer.Option(
        "--target",
        help=(
            "Taranacak meal (tekrarlanir): elmalili-meal, elmalili-sade-meal"
            " (staged: xref-atif-iktibas)."
        ),
    ),
]


def kaydet(enrich_app: typer.Typer) -> None:
    """`enrich citations` komutunu ekler."""

    @enrich_app.command("citations")
    def enrich_citations(
        target: Hedef,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Acik atif ve iktibas adaylari (A18.4). Cikis 0 ya da 2.

        Veritabanini yalniz okur; yukleme `export pg --source xref-atif-iktibas` ile yapilir.
        """
        from mutalaa_pipeline.adimlar import enrich_citations as adim

        kod = adim.komut_enrich_citations(
            hedefler=target, dry_run=dry_run, force=force, config=config, kok=kok
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
