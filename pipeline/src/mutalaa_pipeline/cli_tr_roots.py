"""Turkce kelime -> Arapca kok komutu (A18.2): `enrich tr-roots` (`cli_qac.kaydet` ekler)."""

from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, Force, KokSecenegi

Kaynak = Annotated[
    list[str],
    typer.Option(
        "--source",
        help="Islenecek meal (tekrarlanir): elmalili-meal, elmalili-sade-meal. Ikisi tek kosuda.",
    ),
]
EnAzSiklik = Annotated[
    int,
    typer.Option(
        "--min-freq",
        min=1,
        help="Aday lemma icin review onerilecek en az toplam siklik (varsayilan 3).",
    ),
]
GelenTarih = Annotated[
    str | None,
    typer.Option(
        "--gelen-tarih",
        help="data/gelen/kaikki-tr altindaki tarih klasoru, YYYY-AA-GG; verilmezse en yenisi.",
    ),
]


def kaydet(enrich_app: typer.Typer) -> None:
    """`enrich tr-roots` komutunu ekler."""

    @enrich_app.command("tr-roots")
    def enrich_tr_roots(
        source: Kaynak,
        min_freq: EnAzSiklik = 3,
        gelen_tarih: GelenTarih = None,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Turkce kelime -> Arapca kok eslemesi (K-51 madde 9). Cikis 0 ya da 2.

        Iki meal tek kosuda birlesir; zeyrek icin `--extra turkce` gerekir.
        """
        from mutalaa_pipeline.adimlar import enrich_tr_roots as adim

        kod = adim.komut_enrich_tr_roots(
            kaynaklar=source,
            min_sik=min_freq,
            gelen_tarih=gelen_tarih,
            dry_run=dry_run,
            force=force,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
