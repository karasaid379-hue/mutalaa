"""Sentetik Risale fiksturu: normalize ve anchor adimlari (A20.5a; `test-risale-ornek`).

`adimlar/risale.py` yalniz `risale-rnk-metin` icin `komut_*` sarmalayicilari sunar
(`kaynak_denetle`); `run_normalize` ve `run_anchor` ise kaynak kimligi aldigi icin fiksturle
AYNI KOD calisir. Bu modul:

* `komut_normalize`: `risale.run_normalize(ctx, "test-risale-ornek")` (arama anahtarlari, ayni
  `normalize_satiri`).
* `komut_anchor`: `risale.run_anchor` ile ayni capa alanlari (`anchor_satiri`, `ord_haritasi`;
  `ANCHOR_ALANLARI`; `risale.run_anchor(..., ek=OrnekEki())` kancasi) ve ek olarak ayni anchor
  calismasinin ciktisi olarak
    `page_map.jsonl`      sentetik sayfa esleme (`risale_sayfa.dosya_satirlari` ile hesaplanir,
                          `source_id = test-risale-ornek`, `volume` sentetik cilt;
                          `risale-baski-rnk` DEGIL),
    `page_map_rapor.jsonl` kitap raporu (yalniz sayilar),
    `xref.jsonl`          iki sentetik `xref` (`aday`, `origin = 'hat'`, `evidence.fikstur = true`).

Hata iletileri metin tasimaz. Manifest en son yazilir.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar import risale
from mutalaa_pipeline.adimlar.risale import AdimSonucu, run_normalize
from mutalaa_pipeline.adimlar.risale_sayfa import (
    BOLUM_BASI_EKI,
    SATIR_ALANLARI,
    baslangic_capalari,
    birimleri_grupla,
    sayfa_baslari_oku,
    sayfa_esleme_uret,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_ornek
from mutalaa_pipeline.ingest.risale_ornek import KAYNAK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, dosya_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    dosya_oku,
    girdi_olarak,
    saglam_olmali,
    son_calisma,
)

SAYFA_ESLEME_ADI: Final = "page_map.jsonl"
SAYFA_RAPOR_ADI: Final = "page_map_rapor.jsonl"
XREF_ADI: Final = "xref.jsonl"
SAYFA_ANAHTARI: Final = ("volume", "page")
RAPOR_ANAHTARI: Final = ("dosya",)
XREF_ANAHTARI: Final = ("type", "src_anchor", "dst_anchor")
SAYFA_VERSIYONU: Final = f"{KAYNAK}@"


def kaynak_denetle(source: str) -> None:
    if source != KAYNAK:
        raise GirdiHatasi(f"bu adim yalniz {KAYNAK} icindir")


def sayfa_satirlari(
    anchor_satirlari: list[Satir], sayfa_satirlari_: list[Satir], surum: str
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """`page_map` satirlari ve kitap raporu: gercek `dosya_satirlari` ile hesaplanir.

    `risale_sayfa` satirlara `risale-baski-rnk` kimligini yazar; burada fiksturun kendi
    kaynagina cevrilir (`source_id`, `data_version`). Sayfa baslari `sayfalar.jsonl`dir.
    """
    sayfalar = sayfa_baslari_oku(sayfa_satirlari_)
    birimler = birimleri_grupla(iter(anchor_satirlari), baslangic_capalari(sayfalar))
    satirlar, raporlar = sayfa_esleme_uret(
        birimler, sayfalar, {risale_ornek.DOSYA: risale_ornek.CILT}, surum
    )
    sonuc: list[dict[str, object]] = []
    for satir in satirlar:
        kopya = dict(satir)
        bolum_basi = str(kopya["data_version"]).endswith(BOLUM_BASI_EKI)
        kopya["source_id"] = KAYNAK
        kopya["data_version"] = f"{SAYFA_VERSIYONU}{surum}" + (BOLUM_BASI_EKI if bolum_basi else "")
        if set(kopya) != SATIR_ALANLARI:
            raise GirdiHatasi("page_map satiri beklenen alan kumesinde degil")
        sonuc.append(kopya)
    return sonuc, raporlar


class OrnekEki:
    """`risale.run_anchor` kancasi: `page_map.jsonl`, `page_map_rapor.jsonl` ve `xref.jsonl`.

    Girdi olarak ingest calismasinin `sayfalar.jsonl` dosyasi parmak izine ve manifeste girer.
    """

    def __init__(self) -> None:
        self._ingest: Calisma | None = None

    def girdiler(self, ctx: RunContext) -> list[lineage.Girdi]:
        ingest = son_calisma(
            ctx, KAYNAK, INGEST_ADIMI, ipucu=f"once: ingest risale --source {KAYNAK}"
        )
        saglam_olmali(ctx, ingest)
        self._ingest = ingest
        return [girdi_olarak(ingest, risale_ornek.SAYFALAR_ADI)]

    def ciktilar(
        self, ctx: RunContext, satirlar: Sequence[Satir], surum: str
    ) -> tuple[list[lineage.Cikti], Mapping[str, object]]:
        if self._ingest is None:
            raise GirdiHatasi("ek girdiler okunmadan ek ciktilar istendi")
        sayfa_girdisi = dosya_oku(
            self._ingest, risale_ornek.SAYFALAR_ADI, f"ingest {KAYNAK} sayfalar.jsonl"
        )
        page_map, raporlar = sayfa_satirlari(list(satirlar), sayfa_girdisi, surum)
        metinler = {str(s.veri["anchor"]): str(s.veri["text"]) for s in satirlar}
        xrefler = risale_ornek.xref_satirlari(metinler, surum)
        if len({risale_ornek.dogal_anahtar(x) for x in xrefler}) != len(xrefler):
            raise GirdiHatasi("xref dogal anahtari tekil degil")
        ciktilar = [
            dosya_yaz(ctx, KAYNAK, SAYFA_ESLEME_ADI, page_map, SAYFA_ANAHTARI),
            dosya_yaz(ctx, KAYNAK, SAYFA_RAPOR_ADI, raporlar, RAPOR_ANAHTARI),
            dosya_yaz(ctx, KAYNAK, XREF_ADI, xrefler, XREF_ANAHTARI),
        ]
        ctx.sayi("sayfa", len(page_map))
        ctx.sayi("xref", len(xrefler))
        return ciktilar, {
            "ingest_run": self._ingest.run_id,
            "sayfa": len(page_map),
            "xref": len(xrefler),
            "cilt": {risale_ornek.DOSYA: risale_ornek.CILT},
        }


def run_anchor(ctx: RunContext) -> AdimSonucu:
    """`risale.run_anchor` (ayni kod) ve ek ciktilar: `page_map` ile `xref` (`OrnekEki`)."""
    return risale.run_anchor(ctx, KAYNAK, ek=OrnekEki())


def _ozet(sonuc: AdimSonucu, dry_run: bool) -> str:
    if sonuc.atlandi:
        return f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
    if dry_run:
        return f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
    return f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"


def komut_normalize(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`normalize --source test-risale-ornek` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_normalize(ctx, source)
        sys.stdout.write(f"normalize {source}: {_ozet(sonuc, ctx.dry_run)}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"normalize --source {source}",
        adim=NORMALIZE_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source test-risale-ornek` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_anchor(ctx)
        sys.stdout.write(f"anchor {source}: {_ozet(sonuc, ctx.dry_run)}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"anchor --source {source}",
        adim=ANCHOR_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )


__all__ = [
    "SAYFA_ESLEME_ADI",
    "SAYFA_RAPOR_ADI",
    "XREF_ADI",
    "komut_anchor",
    "komut_normalize",
    "run_anchor",
    "sayfa_satirlari",
]
