"""Risale ayet atif komutu (A20.7b): `enrich citations` (`cli_qac.kaydet` ekler)."""

from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, Force, KokSecenegi

Kaynak = Annotated[
    str,
    typer.Option(
        "--source",
        help="Taranacak Risale metin kaynagi (risale-rnk-metin).",
    ),
]
GelenTarih = Annotated[
    str | None,
    typer.Option(
        "--gelen-tarih",
        help=(
            "data/gelen/tanzil-uthmani ve tanzil-simple-clean altindaki tarih klasoru,"
            " YYYY-AA-GG; verilmezse her birinin en yenisi."
        ),
    ),
]


def kaydet(enrich_app: typer.Typer) -> None:
    """`enrich citations` komutunu ekler."""

    @enrich_app.command("citations")
    def enrich_citations(
        source: Kaynak,
        gelen_tarih: GelenTarih = None,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Risale ayet atif ve iktibas adaylarini uretir (xrefs.jsonl). Cikis 0 ya da 2."""
        from mutalaa_pipeline.adimlar import enrich_citations as adim

        kod = adim.komut_enrich_citations(
            source=source,
            gelen_tarih=gelen_tarih,
            dry_run=dry_run,
            force=force,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
