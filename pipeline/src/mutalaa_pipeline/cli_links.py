"""Kur'an ici baglanti komutu (A18.3): `enrich links` (`cli_qac.kaydet` ekler)."""

from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, Force, KokSecenegi

Tur = Annotated[
    str,
    typer.Option(
        "--type",
        help="Uretilecek tur: kok, lemma, benzer-ayet ya da hepsi (staged: xref-baglantilar).",
    ),
]
GelenTarih = Annotated[
    str | None,
    typer.Option(
        "--gelen-tarih",
        help="data/gelen/qursim altindaki tarih klasoru, YYYY-AA-GG; verilmezse en yenisi.",
    ),
]


def kaydet(enrich_app: typer.Typer) -> None:
    """`enrich links` komutunu ekler."""

    @enrich_app.command("links")
    def enrich_links(
        tur: Tur = "hepsi",
        gelen_tarih: GelenTarih = None,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Kur'an ici kok, lemma ve benzer_ayet baglantilari (A18.3). Cikis 0 ya da 2.

        Veritabanini yalniz okur; yukleme `export pg --source xref-baglantilar` ile yapilir.
        """
        from mutalaa_pipeline.adimlar import enrich_links as adim

        kod = adim.komut_enrich_links(
            tur=tur,
            gelen_tarih=gelen_tarih,
            dry_run=dry_run,
            force=force,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
