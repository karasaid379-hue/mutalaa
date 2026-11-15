"""`qa risale-rapor`: Risale karsilastirma raporlari (A20.1, A20.2b); `cli.py` yalniz `kaydet`
cagirir.

* `icindekiler`: RNK `json` icindekileri <-> eRisale `toc-tr.json` ve staged RNK basliklari
  (`qa/risale_raporlari.py`) -> `data/reports/a20/icindekiler-karsilastirma.json`.
* `diyanet`: Diyanet <-> RNK kelime dizisi karsilastirmasi (`ingest/risale_karsilastirma.py`)
  -> `data/reports/a20/diyanet-rnk-karsilastirma.json`.

Girdi yalniz `data/staged` ve `data/gelen` altindan okunur; veritabani yoktur. Raporlar METIN
ICERMEZ. `shared/data/risale-kitaplar.json` degismez (`dogrulandi` onerisi insan adimidir, I-24).
Cikis kodu 0 ya da 2.
"""

import sys
from pathlib import Path
from typing import Annotated, Final

import typer

from mutalaa_pipeline import cikis, lineage, zincir
from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_karsilastirma
from mutalaa_pipeline.ingest.risale_rnk_staged import JsonBilgisi, json_oku
from mutalaa_pipeline.ingest.tanzil import INGEST_ADIMI, tarih_gecerli
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.qa import risale_raporlari
from mutalaa_pipeline.runctx import RunContext

KOMUT: Final = "qa risale-rapor"
RAPOR_KLASORU: Final = ("reports", "a20")
ICINDEKILER_DOSYASI: Final = "icindekiler-karsilastirma.json"
DIYANET_DOSYASI: Final = "diyanet-rnk-karsilastirma.json"
TURLER: Final = ("icindekiler", "diyanet", "hepsi")
RNK_METIN: Final = "risale-rnk-metin"
DIYANET_METIN: Final = "risale-asil-nusha"
RNK_BASKI: Final = "risale-baski-rnk"
ERISALE: Final = "erisale-icindekiler"
ERISALE_DOSYA: Final = "toc-tr.json"


def _yaz(ctx: RunContext, ad: str, veri: bytes) -> str:
    klasor = ctx.veri_kok.joinpath(*RAPOR_KLASORU)
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / ad
    gecici = klasor / (ad + ".tmp")
    gecici.write_bytes(veri)
    lineage.atomik_degistir(gecici, hedef)
    return lineage.goreli_yol(ctx.veri_kok, hedef)


def _calisma(ctx: RunContext, kaynak: str, calisma: str | None) -> Path:
    klasor = ctx.veri_kok / "staged" / kaynak
    if not klasor.is_dir():
        raise GirdiHatasi(f"{kaynak}: staged klasoru yok (once ingest)")
    if calisma is None:
        return risale_karsilastirma.son_calisma(klasor)
    # Acik `--*-run`: kimlik UUID olmali (yola eklenir), calisma manifestli ve adimi `ingest`
    # (karsilastirma ham ayristirma ciktisini okur) ve ciktilari saglam olmali.
    secilen = zincir.calisma_bul(ctx, kaynak, calisma, INGEST_ADIMI)
    zincir.saglam_olmali(ctx, secilen)
    if not (secilen.klasor / "units.jsonl").is_file():
        raise GirdiHatasi(f"{kaynak}: staged calisma bulunamadi")
    return secilen.klasor


def _gelen(ctx: RunContext, kaynak: str, tarih: str | None) -> Path:
    klasor = ctx.veri_kok / "gelen" / kaynak
    if not klasor.is_dir():
        raise GirdiHatasi(f"{kaynak}: gelen klasoru yok")
    if tarih is not None and not tarih_gecerli(tarih):  # yola eklenir: `../` ve yol ayiraci yok
        raise GirdiHatasi("tarih YYYY-AA-GG biciminde gecerli bir tarih olmali")
    ad = tarih if tarih is not None else risale_raporlari.son_tarih(klasor)
    if not (klasor / ad).is_dir():
        raise GirdiHatasi(f"{kaynak}: tarih klasoru yok")
    return klasor / ad


def icindekiler_raporu(
    ctx: RunContext, rnk_run: str | None, rnk_tarih: str | None, erisale_tarih: str | None
) -> dict[str, object]:
    tablo = risale.kitaplar()
    calisma = _calisma(ctx, RNK_METIN, rnk_run)
    baski = _gelen(ctx, RNK_BASKI, rnk_tarih)
    erisale_klasoru = _gelen(ctx, ERISALE, erisale_tarih)
    rnk_json: dict[str, JsonBilgisi] = {}
    for k in tablo:
        if k.rnk is None:
            raise GirdiHatasi(f"{k.slug}: RNK baglantisi yok")
        anahtar = f"{k.rnk.raf}/{k.rnk.uid}"
        if anahtar in rnk_json:
            continue
        yol = baski / k.rnk.raf / f"{k.rnk.uid}.json"
        if not yol.is_file():
            raise GirdiHatasi(f"{anahtar}: RNK json yok")
        rnk_json[anahtar] = json_oku(yol.read_bytes())
    staged = risale_raporlari.staged_basliklari(calisma / "units.jsonl", [k.slug for k in tablo])
    erisale = risale_raporlari.erisale_oku(erisale_klasoru / ERISALE_DOSYA)
    return risale_raporlari.rapor_uret(
        tablo,
        rnk_json,
        staged,
        erisale,
        {
            "rnk_json": f"{RNK_BASKI}/{baski.name}",
            "erisale_toc": f"{ERISALE}/{erisale_klasoru.name}/{ERISALE_DOSYA}",
            "staged_rnk": f"{RNK_METIN}/{calisma.name}",
        },
    )


def diyanet_raporu(
    ctx: RunContext, rnk_run: str | None, diyanet_run: str | None
) -> dict[str, object]:
    tablo = risale.kitaplar()
    rnk = _calisma(ctx, RNK_METIN, rnk_run)
    diyanet = _calisma(ctx, DIYANET_METIN, diyanet_run)
    rapor = risale_karsilastirma.rapor_uret(tablo, diyanet / "units.jsonl", rnk / "units.jsonl")
    rapor["kaynaklar"] = {
        "staged_rnk": f"{RNK_METIN}/{rnk.name}",
        "staged_diyanet": f"{DIYANET_METIN}/{diyanet.name}",
    }
    return rapor


def komut_risale_rapor(
    *,
    rapor: str,
    rnk_run: str | None,
    diyanet_run: str | None,
    rnk_tarih: str | None,
    erisale_tarih: str | None,
    dry_run: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa risale-rapor`; cikis kodu 0 ya da 2."""

    def govde(ctx: RunContext) -> int:
        if rapor not in TURLER:
            raise GirdiHatasi("--rapor icindekiler, diyanet ya da hepsi olmali")
        if rapor in ("icindekiler", "hepsi"):
            r = icindekiler_raporu(ctx, rnk_run, rnk_tarih, erisale_tarih)
            if not dry_run:
                ctx.rapor_ek["icindekiler"] = _yaz(ctx, ICINDEKILER_DOSYASI, json_baytlari(r))
            ozet = r["ozet"]
            sys.stdout.write(f"qa risale-rapor icindekiler: {ozet}\n")
        if rapor in ("diyanet", "hepsi"):
            d = diyanet_raporu(ctx, rnk_run, diyanet_run)
            if not dry_run:
                ctx.rapor_ek["diyanet"] = _yaz(ctx, DIYANET_DOSYASI, json_baytlari(d))
            sys.stdout.write(f"qa risale-rapor diyanet: {d['toplam']}\n")
        if dry_run:
            sys.stdout.write("[dry-run: dosya yazilmadi]\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=KOMUT,
        adim="qa",
        kaynaklar=[],
        config=config,
        kok=kok,
        govde=govde,
        dry_run=dry_run,
        parametreler={"rapor": rapor},
    )


def kaydet(qa_app: typer.Typer) -> None:
    """`qa risale-rapor` komutunu `qa` grubuna ekler."""

    @qa_app.command("risale-rapor")
    def risale_rapor(
        rapor: Annotated[
            str, typer.Option("--rapor", help="icindekiler, diyanet ya da hepsi.")
        ] = "hepsi",
        rnk_run: Annotated[
            str | None, typer.Option("--rnk-run", help="Staged RNK run_id; yoksa en yenisi.")
        ] = None,
        diyanet_run: Annotated[
            str | None,
            typer.Option("--diyanet-run", help="Staged Diyanet run_id; yoksa en yenisi."),
        ] = None,
        rnk_tarih: Annotated[
            str | None,
            typer.Option("--rnk-tarih", help="data/gelen/risale-baski-rnk tarih klasoru."),
        ] = None,
        erisale_tarih: Annotated[
            str | None,
            typer.Option("--erisale-tarih", help="data/gelen/erisale-icindekiler tarih klasoru."),
        ] = None,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Dosya yazmaz; ozeti yazdirir.")
        ] = False,
        config: Annotated[
            Path | None, typer.Option("--config", help="Baska bir mutalaa.toml.")
        ] = None,
        kok: Annotated[
            Path | None,
            typer.Option(
                "--kok", help="Depo koku (testler icin); yoksa pnpm-workspace.yaml aranir."
            ),
        ] = None,
    ) -> None:
        """Risale karsilastirma raporlari (icindekiler, Diyanet-RNK). Cikis 0 ya da 2."""
        kod = komut_risale_rapor(
            rapor=rapor,
            rnk_run=rnk_run,
            diyanet_run=diyanet_run,
            rnk_tarih=rnk_tarih,
            erisale_tarih=erisale_tarih,
            dry_run=dry_run,
            config=config,
            kok=kok,
        )
        if kod != cikis.BASARILI:
            raise typer.Exit(code=kod)
