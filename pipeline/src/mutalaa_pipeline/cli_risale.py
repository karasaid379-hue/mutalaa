"""Risale komutlari (A20.1): `ingest risale`; `cli.py` yalniz `kaydet` cagirir."""

import sys
from pathlib import Path
from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz
from mutalaa_pipeline.ingest import risale_kaynaklari

KokSecenegi = Annotated[
    Path | None,
    typer.Option("--kok", help="Depo koku (testler icin); verilmezse pnpm-workspace.yaml aranir."),
]


def kaydet(ingest_app: typer.Typer) -> None:
    """`ingest risale` komutunu uygulamaya ekler."""

    @ingest_app.command("risale")
    def ingest_risale(
        source: Annotated[
            str,
            typer.Option(
                "--source",
                help="Risale kaynagi: risale-asil-nusha (Diyanet, karsilastirma verisi).",
            ),
        ],
        gelen_tarih: Annotated[
            str | None,
            typer.Option(
                "--gelen-tarih",
                help="data/gelen/<kaynak> altindaki tarih klasoru (YYYY-AA-GG); yoksa en yenisi.",
            ),
        ] = None,
        kilit_oner: Annotated[
            bool,
            typer.Option(
                "--kilit-oner",
                help="Kilidin ilk degerlerini gelen zip'ten yazdirir; hicbir sey yazmaz.",
            ),
        ] = False,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="raw ve staged'e yazmaz; kilit yine denetlenir.")
        ] = False,
        force: Annotated[
            bool, typer.Option("--force", help="Parmak izi ayni olsa da calistirir.")
        ] = False,
        limit: Annotated[
            int | None,
            typer.Option("--limit", help="Reddedilir (kismi alim kilidi ve G-BUT'u bozar)."),
        ] = None,
        config: Annotated[
            Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")
        ] = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Gelen Diyanet zip'ini kilitle karsilastirir, raw'a alir, staged uretir (cikis 0, 2)."""
        from mutalaa_pipeline.config import ayarlar_yukle
        from mutalaa_pipeline.ingest import risale_diyanet

        try:
            if not risale_kaynaklari.risale_mi(source):
                raise GirdiHatasi("ingest risale: bilinmeyen Risale kaynagi (risale-asil-nusha)")
            if limit is not None:
                raise GirdiHatasi(
                    "--limit Risale alimi icin desteklenmez (kismi alim kilidi bozar)"
                )
            if kilit_oner:
                if dry_run or force:
                    raise GirdiHatasi("--kilit-oner ile --dry-run ve --force verilmez")
                metin = risale_diyanet.kilit_oner_metni(
                    ayarlar_yukle(config).veri_kok, kok_coz(kok), gelen_tarih
                )
                sys.stdout.buffer.write(metin.encode("utf-8"))  # LF (Windows CRLF yazar)
                sys.stdout.buffer.flush()
                return
        except GirdiHatasi as hata:
            typer.echo(f"hata: {hata}", err=True)
            raise typer.Exit(code=cikis.GIRDI_HATASI) from hata
        kod = risale_diyanet.komut_ingest_risale(
            gelen_tarih=gelen_tarih, dry_run=dry_run, force=force, config=config, kok=kok
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
