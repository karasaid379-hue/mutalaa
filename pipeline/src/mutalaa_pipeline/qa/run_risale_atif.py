"""`mutalaa qa run --source risale-atif-dizini`: zinciri yukler, kapilari kosar (A20.7b).

Zincir: son `enrich citations` calismasi (`anchor` adimi; ya da `--run`) -> taranan
`risale-rnk-metin` anchor calismasi (manifest `girdiler`, ozet ust calismanin ciktisiyla ayni
olmali) ve Tanzil dosyalari (`data/gelen/tanzil-*`; manifestteki ozet ve kilitle dogrulanir).
G-KAY, G-BUT, G-CAP, G-NOR `qa/checks/risale_atif.py`'dedir. Taranan `units.jsonl` satir satir
akitilir; yalniz xref'te gecen birimler bellekte tutulur.

Rapor alanlari (`kaynak`, `anchor_run_id` = atif calismasi, `units_sha256` = `xrefs.jsonl`
ozeti, `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`) ve cikis kodlari `qa/run.py` ile
ayni bicimdedir: 0 kapilar gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi. Rapor ve
bulgular metin tasimaz. `--gate` kismi kosusu `export pg`ye yetmez (`qa/rapor.py`).
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis
from mutalaa_pipeline.enrich import kuran_metni
from mutalaa_pipeline.enrich.citations import KAYNAK_ID, XREFS_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import UNITS_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_atif import (
    KAPI_ISLEVLERI,
    KAPILAR,
    AtifBirimi,
    AtifGirdisi,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_akit
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    Calisma,
    calisma_bul,
    dosya_oku,
    girdiler,
    saglam_olmali,
    son_calisma,
    ust_calismalar,
)

KAYNAK: Final = KAYNAK_ID
QA_ADIMI: Final = "qa"
EN_COK_BULGU: Final = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse dort kapi. Bilinmeyen kapi `GirdiHatasi`."""
    if not gate:
        return KAPILAR
    if any(g not in KAPILAR for g in gate):
        raise GirdiHatasi(f"--gate {', '.join(KAPILAR)} degerlerinden biri olmali")
    return tuple(k for k in KAPILAR if k in gate)


def _tarananlar(calisma: Calisma, ctx: RunContext) -> Calisma:
    ustler = ust_calismalar(ctx, calisma)
    if len(ustler) != 1 or ustler[0].adim != ANCHOR_ADIMI or ustler[0].source_id != KAYNAK_RNK:
        raise GirdiHatasi(f"zincir bozuk: atif calismasi bir {KAYNAK_RNK} anchor calismasina bagli")
    saglam_olmali(ctx, ustler[0])
    return ustler[0]


def _birimleri_topla(anchor: Calisma, istenen: set[str]) -> dict[str, AtifBirimi]:
    sonuc: dict[str, AtifBirimi] = {}
    satir: Satir
    for satir in satirlari_akit(anchor.klasor / UNITS_ADI, f"anchor {KAYNAK_RNK} units.jsonl"):
        capa = satir.veri.get("anchor")
        if not isinstance(capa, str) or capa not in istenen:
            continue
        metin, marks, attrs, ozet = (
            satir.veri.get("text"),
            satir.veri.get("marks"),
            satir.veri.get("attrs"),
            satir.veri.get("content_hash"),
        )
        if (
            not isinstance(metin, str)
            or not isinstance(marks, list)
            or not isinstance(attrs, dict)
            or not isinstance(ozet, str)
        ):
            raise GirdiHatasi(
                f"{satir.etiket}: satir {satir.no}: metin, marks, attrs ya da ozet yok"
            )
        dil = attrs.get("dil")
        sonuc[capa] = AtifBirimi(
            metin,
            [m for m in marks if isinstance(m, dict)],
            dil if isinstance(dil, str) else "",
            ozet,
        )
    return sonuc


def _kuran(ctx: RunContext, calisma: Calisma) -> kuran_metni.KuranMetni:
    tarihler = calisma.ayrinti("tanzil_tarihleri")
    if not isinstance(tarihler, dict) or set(tarihler) != set(kuran_metni.VARYANTLAR):
        raise GirdiHatasi("atif manifestinde tanzil_tarihleri yok")
    kuran = kuran_metni.yukle(ctx.veri_kok, {str(k): str(v) for k, v in tarihler.items()})
    manifestteki = {
        (yol, ozet) for yol, ozet in girdiler(calisma.manifest) if yol.startswith("gelen/")
    }
    okunan = {(g.yol, g.sha256) for g in kuran.girdiler}
    if manifestteki != okunan:
        raise GirdiHatasi("Tanzil dosyalari atif calismasindaki ozetlerle ayni degil")
    return kuran


def yukle(ctx: RunContext, *, run: str | None) -> tuple[AtifGirdisi, Calisma, Calisma]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kayit = ctx.require_sources((KAYNAK, KAYNAK_RNK))[KAYNAK]
    calisma = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(
            ctx, KAYNAK, ANCHOR_ADIMI, ipucu=f"once: enrich citations --source {KAYNAK_RNK}"
        )
    )
    ctx.rapor_ek["anchor_run_id"] = calisma.run_id
    ozet = calisma.cikti_ozeti(XREFS_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, calisma)
    taranan = _tarananlar(calisma, ctx)
    units_ozeti = taranan.cikti_ozeti(UNITS_ADI)
    if ozet is None or units_ozeti is None:
        raise GirdiHatasi("manifestte xrefs.jsonl ya da units.jsonl ozeti yok")
    satirlar = [s.veri for s in dosya_oku(calisma, XREFS_ADI, f"atif {XREFS_ADI}")]
    istenen = {str(s["src_anchor"]) for s in satirlar if isinstance(s.get("src_anchor"), str)}
    ayrintilar = calisma.manifest.get("ayrintilar")
    if not isinstance(ayrintilar, dict):
        raise GirdiHatasi("atif manifestinde ayrintilar yok")
    girdi = AtifGirdisi(
        kayit=kayit,
        manifest=ayrintilar,
        units_sha256=units_ozeti,
        xrefs_sha256=ozet,
        satirlar=satirlar,
        birimler=_birimleri_topla(taranan, istenen),
        kuran=_kuran(ctx, calisma),
    )
    return girdi, calisma, taranan


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = KAPILAR
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, calisma, taranan = yukle(ctx, run=run)  # kayitsiz ya da gecersiz kayit: cikis 2
    ctx.rapor_ek["zincir"] = {"atif": calisma.run_id, "anchor": taranan.run_id}
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    ctx.rapor_ek["kapilar"] = {k: GECTI if s.gecti else KALDI for k, s in sonuclar.items()}
    ctx.rapor_ek["kapi_bulgulari"] = {
        k: list(s.bulgular[:EN_COK_BULGU]) for k, s in sonuclar.items()
    }
    ctx.rapor_ek["kapi_sayilari"] = {k: s.sayilar for k, s in sonuclar.items()}
    for kapi, sonuc in sonuclar.items():
        ctx.sayi(f"bulgu_{kapi}", len(sonuc.bulgular))
        ctx.gunluk.yaz(
            "INFO" if sonuc.gecti else "ERROR",
            "qa_kapi",
            source_id=KAYNAK,
            sayilar={"bulgu": len(sonuc.bulgular)},
            kapi=kapi,
        )
    ctx.sayi("satir", len(girdi.satirlar))
    return sonuclar


def komut_qa_run_risale_atif(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source risale-atif-dizini` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (atif run {ctx.rapor_ek['anchor_run_id']})\n"
        )
        for kapi, s in sonuclar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
        kalanlar = [k for k, s in sonuclar.items() if not s.gecti]
        if kalanlar:
            raise QaKaldi("QA kapisi kaldi: " + ", ".join(kalanlar))
        return cikis.BASARILI

    parametreler: dict[str, object] = {"source": KAYNAK}
    if run is not None:
        parametreler["run"] = run
    if gate:
        parametreler["gate"] = list(gate)
    return komutu_yurut(
        komut=QA_KOMUTU,
        adim=QA_ADIMI,
        kaynaklar=[KAYNAK, KAYNAK_RNK],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
