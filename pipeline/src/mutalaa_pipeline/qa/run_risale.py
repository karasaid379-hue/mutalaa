"""`mutalaa qa run --source risale-asil-nusha`: zinciri yukler, kapilari kosar, rapor yazar.

Akis: kaynak kaydi (`risale-asil-nusha`), son `ingest` calismasi ya da `--run`, calismanin
ciktilari (saglam ve manifestteki ozetle ayni), ham zip (`data/raw`, manifestteki ozetle) ve
kilit; sonra G-KAY ve G-BUT (`qa/checks/risale.py`). G-CAP ve G-NOR bu adimda yoktur (G-CAP:
A20.2b; arama metni uretilmez). `export pg` bu kaynak icin YOKTUR: Diyanet metni karsilastirma
verisidir (K-51 madde 2), veritabanina yuklenmez.

Rapor `data/reports/{run_id}.json`: `kaynak`, `ingest_run_id`, `units_sha256`, `kapilar`,
`kapi_bulgulari`, `kapi_sayilari`, `olcumler`, `zincir`. Rapor ve bulgular metin tasimaz.
Cikis kodlari: 0 kapilar gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_diyanet
from mutalaa_pipeline.ingest.risale_diyanet import KAYNAK
from mutalaa_pipeline.ingest.risale_kaynaklari import RISALE_KAPILARI
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale import KAPI_ISLEVLERI, RisaleGirdisi, olcumler
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.zincir import (
    INGEST_ADIMI,
    Calisma,
    calisma_bul,
    ham_dosya,
    saglam_olmali,
    son_calisma,
    units_oku,
)

QA_ADIMI: Final = "qa"
EN_COK_BULGU: Final = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse iki kapi. G-CAP ve G-NOR bu kaynakta yoktur (hata)."""
    if not gate:
        return RISALE_KAPILARI
    bilinmeyen = [g for g in gate if g not in RISALE_KAPILARI]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(RISALE_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in RISALE_KAPILARI if k in gate)


def yukle(ctx: RunContext, kayit: Kaynak, *, run: str | None) -> tuple[RisaleGirdisi, Calisma]:
    """Ingest calismasini ve ham zip'i yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    ingest = (
        calisma_bul(ctx, KAYNAK, run, INGEST_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest risale --source " + KAYNAK)
    )
    ctx.rapor_ek["ingest_run_id"] = ingest.run_id
    ozet = ingest.cikti_ozeti()
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, ingest)
    _, ham_ozet, ham = ham_dosya(ctx, ingest)
    commit = ingest.ayrinti("commit")
    girdi = RisaleGirdisi(
        kayit=kayit,
        kilit=risale_diyanet.kilit_yukle(),
        kimlik=risale_diyanet.kimlik_yukle(),
        ham=ham,
        ham_sha256=ham_ozet,
        ingest_commit=commit if isinstance(commit, str) else None,
        birim_satirlari=units_oku(ingest, "ingest units.jsonl"),
    )
    return girdi, ingest


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = RISALE_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK,))  # kayitsiz ya da gecersiz: cikis 2
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, ingest = yukle(ctx, kayitlar[KAYNAK], run=run)
    ctx.rapor_ek["zincir"] = {"ingest": ingest.run_id}
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    ctx.rapor_ek["kapilar"] = {k: GECTI if s.gecti else KALDI for k, s in sonuclar.items()}
    ctx.rapor_ek["kapi_bulgulari"] = {
        k: list(s.bulgular[:EN_COK_BULGU]) for k, s in sonuclar.items()
    }
    ctx.rapor_ek["kapi_sayilari"] = {k: s.sayilar for k, s in sonuclar.items()}
    ctx.rapor_ek["olcumler"] = olcumler(girdi)
    for kapi, sonuc in sonuclar.items():
        ctx.sayi(f"bulgu_{kapi}", len(sonuc.bulgular))
        ctx.gunluk.yaz(
            "INFO" if sonuc.gecti else "ERROR",
            "qa_kapi",
            source_id=KAYNAK,
            sayilar={"bulgu": len(sonuc.bulgular)},
            kapi=kapi,
        )
    ctx.sayi("birim", len(girdi.birim_satirlari))
    return sonuclar


def komut_qa_run_risale(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source risale-asil-nusha` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (ingest run {ctx.rapor_ek['ingest_run_id']})\n"
        )
        for kapi, s in sonuclar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
            fazla = len(s.bulgular) - EN_COK_BULGU
            if fazla > 0:
                sys.stdout.write(f"  {kapi} kaldi: (+{fazla} bulgu daha)\n")
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
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
