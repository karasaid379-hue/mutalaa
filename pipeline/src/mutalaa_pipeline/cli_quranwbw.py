"""QuranWBW komutlari (A17.6): `ingest quranwbw-tr` ve `enrich glosses` (`cli_qac.kaydet` ekler)."""

import sys
from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, Force, KokSecenegi
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz

GelenTarih = Annotated[
    str | None,
    typer.Option(
        "--gelen-tarih",
        help="data/gelen/quranwbw-tr altindaki tarih klasoru, YYYY-AA-GG; verilmezse en yenisi.",
    ),
]
Dalga = Annotated[
    int,
    typer.Option(
        "--wave",
        min=1,
        max=4,
        help=(
            "Islenecek dalga (lemma_dalga). --wave 1 dalga 0 ve 1'i BIRLIKTE acar; --wave N"
            " (N >= 2) yalniz N. dalgayi isler."
        ),
    ),
]


def kaydet(ingest_app: typer.Typer, enrich_app: typer.Typer) -> None:
    """`ingest quranwbw-tr` ve `enrich glosses` komutlarini ekler."""

    @ingest_app.command("quranwbw-tr")
    def ingest_quranwbw(
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
        """QuranWBW Turkce kelime anlamlarini kilitle karsilastirir, raw'a alir. Cikis 0 ya da 2."""
        from mutalaa_pipeline.config import ayarlar_yukle
        from mutalaa_pipeline.ingest import quranwbw

        if kilit_oner:
            try:
                if dry_run or force:
                    raise GirdiHatasi("--kilit-oner ile --dry-run ve --force verilmez")
                metin = quranwbw.kilit_oner_metni(
                    ayarlar_yukle(config).veri_kok, kok_coz(kok), gelen_tarih
                )
            except GirdiHatasi as hata:
                typer.echo(f"hata: {hata}", err=True)
                raise typer.Exit(code=cikis.GIRDI_HATASI) from hata
            sys.stdout.buffer.write(metin.encode("utf-8"))  # LF (Windows metin kipi CRLF yazar)
            sys.stdout.buffer.flush()
            return
        kod = quranwbw.komut_ingest_quranwbw(
            gelen_tarih=gelen_tarih, dry_run=dry_run, force=force, config=config, kok=kok
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)

    @enrich_app.command("glosses")
    def enrich_glosses(
        wave: Dalga,
        dry_run: DryRun = False,
        force: Force = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Hazir kaynaktan (QuranWBW) kelime anlami adaylarini uretir. Cikis 0 ya da 2.

        --wave 1 dalga 0 ve 1'i birlikte, --wave N (N >= 2) yalniz N. dalgayi isler.
        """
        from mutalaa_pipeline.adimlar import enrich_glosses as adim

        kod = adim.komut_enrich_glosses(
            wave=wave, dry_run=dry_run, force=force, config=config, kok=kok
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
