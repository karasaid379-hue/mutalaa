"""`mutalaa qa gold` komutu (A18.5): degerlendirme setleri ve kapi olcumu (`cli.py` ekler)."""

from typing import Annotated

import typer

from mutalaa_pipeline import cikis
from mutalaa_pipeline.cli_qac import Config, DryRun, KokSecenegi

Tur = Annotated[
    str,
    typer.Option(
        "--type", help="Olculecek tur: kok, lemma, benzer-ayet, atif, iktibas ya da hepsi."
    ),
]
Build = Annotated[
    bool,
    typer.Option("--build", help="Seti (yeniden) uretir; yoksa var olan son set olculur."),
]


def kaydet(qa_app: typer.Typer) -> None:
    """`qa gold` komutunu ekler."""

    @qa_app.command("gold")
    def qa_gold(
        tur: Tur,
        build: Build = False,
        dry_run: DryRun = False,
        config: Config = None,
        kok: KokSecenegi = None,
    ) -> None:
        """Degerlendirme seti olcumu, kapi karari ve xref_gate yazimi (A18.5). Cikis 0, 1 ya da 2.

        Rapor data/reports/{data_version}-gold-{tur}.json; --dry-run hicbir sey yazmaz.
        """
        from mutalaa_pipeline.qa.gold import run

        kod = run.komut_qa_gold(tur=tur, build=build, dry_run=dry_run, config=config, kok=kok)
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
