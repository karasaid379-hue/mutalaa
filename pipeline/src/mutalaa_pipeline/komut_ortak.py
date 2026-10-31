"""Komutlarin ortak iskeleti: baglam olusturma ve hata cikisi (cikis kodlari: cikis.py)."""

import sys
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.config import ayarlar_yukle
from mutalaa_pipeline.export.ortak import GirdiHatasi, kok_coz
from mutalaa_pipeline.logs import ileti_temizle
from mutalaa_pipeline.runctx import RunContext, komut_calistir


def komutu_yurut(
    *,
    komut: str,
    adim: str,
    kaynaklar: Iterable[str],
    config: Path | None,
    kok: Path | None,
    govde: Callable[[RunContext], int | None],
    force: bool = False,
    dry_run: bool = False,
    parametreler: Mapping[str, object] | None = None,
) -> int:
    """Baglami kurar ve govdeyi `komut_calistir` ile calistirir; cikis kodunu dondurur.

    Yapilandirma ya da depo koku hatasi baglam kurulamadan olur: ileti temizlenir, cikis 2.
    """
    try:
        ayarlar = ayarlar_yukle(config)
        ctx = RunContext.olustur(
            ayarlar,
            komut=komut,
            adim=adim,
            depo_kok=kok_coz(kok),
            kaynaklar=kaynaklar,
            parametreler=parametreler,
            force=force,
            dry_run=dry_run,
        )
    except GirdiHatasi as hata:
        sys.stderr.write(f"hata: {ileti_temizle(str(hata))}\n")
        return cikis.GIRDI_HATASI
    return komut_calistir(ctx, govde)
