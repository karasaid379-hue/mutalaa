"""QAC komutlari (A17.3): `ingest qac` ve `enrich morphology`; `cli.py` yalniz `kaydet` cagirir."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz

KokSecenegi = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]
GelenTarih = Annotated[
    str | None,
    typer.Option(
        "--gelen-tarih",
        help="data/gelen/qac-morfoloji altindaki tarih klasoru, YYYY-AA-GG; verilmezse en yenisi.",
    ),
]
DryRun = Annotated[
    bool, typer.Option("--dry-run", help="raw ve staged'e yazmaz; kilit yine denetlenir.")
]
Force = Annotated[bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")]
Config = Annotated[Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")]


def kaydet(app: typer.Typer, ingest_app: typer.Typer) -> None:
    """`ingest qac` komutunu ve `enrich` grubunu (`enrich morphology`) uygulamaya ekler."""
    enrich_app = typer.Typer(no_args_is_help=True, help="Zenginlestirme: QAC morfolojisi.")
    app.add_typer(enrich_app, name="enrich")
    from mutalaa_pipeline import cli_quranwbw  # dairesel ice aktarma olmasin: islev icinde

    cli_quranwbw.kaydet(ingest_app, enrich_app)  # A17.6: ingest quranwbw-tr, enrich glosses

    @ingest_app.command("qac")
    def ingest_qac(
        gelen_tarih: GelenTarih = None,
        kilit_oner: Annotated[
            bool,
            typer.Option(
                "--kilit-oner",
                help="Kilidin ilk degerlerini gelen dosyadan yazdirir; hicbir sey yazmaz.",
            ),
        ] = False,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """QAC morfoloji dosyasini kilitle karsilastirir, raw'a alir. Cikis 0 ya da 2."""
        from mutalaa_pipeline.config import ayarlar_yukle
        from mutalaa_pipeline.ingest import qac

        if kilit_oner:
            try:
                if dry_run or force:
                    raise GirdiHatasi("--kilit-oner ile --dry-run ve --force verilmez")
                metin = qac.kilit_oner_metni(
                    ayarlar_yukle(config).veri_kok, kok_coz(kok), gelen_tarih
                )
            except GirdiHatasi as hata:
                typer.echo(f"hata: {hata}", err=True)
                raise typer.Exit(code=cikis.GIRDI_HATASI) from hata
            sys.stdout.buffer.write(metin.encode("utf-8"))  # LF (Windows metin kipi CRLF yazar)
            sys.stdout.buffer.flush()
            return
        kod = qac.komut_ingest_qac(
            gelen_tarih=gelen_tarih, dry_run=dry_run, force=force, config=config, kok=kok
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)

    @enrich_app.command("morphology")
    def enrich_morphology(
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """QAC kelime, lemma, kok ve dalga satirlarini uretir. Cikis 0 ya da 2."""
        from mutalaa_pipeline.adimlar import enrich_morphology as adim

        kod = adim.komut_enrich_morphology(dry_run=dry_run, force=force, config=config, kok=kok)
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
