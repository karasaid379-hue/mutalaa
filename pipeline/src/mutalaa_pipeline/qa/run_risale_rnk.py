"""`risale-rnk-metin` QA girdisinin yuklenmesi ve kapilarin kosulmasi (A20.1b).

Ingest asamasinda kosar (normalize ve anchor adimlari A20.2b'ye aittir): son `ingest`
calismasini (ya da `--run`) zincir denetimiyle okur, manifestteki `raw/risale-rnk-metin/...`
girdilerini ozetle dogrulayarak yukler ve `qa/checks/risale_rnk.py` kapilarini calistirir.
`qa run` yonlendirmesi, rapor alanlari (`kaynak`, `kapilar`, `kapi_bulgulari` ...) ve cikis
kodlari `qa/run.py` ile ayni bicimdedir: 0 kapilar gecti, 1 bir kapi kaldi, 2 girdi ya da
zincir hatasi. Rapor `data/reports/{run_id}.json`: `kaynak`, `ingest_run_id`, `units_sha256`,
`kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`; rapor ve bulgular metin tasimaz.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor.risale import kitaplar
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_rnk_kaynaklari import (
    KITAPLAR_ADI,
    SAYFALAR_ADI,
    YAPI_ADI,
)
from mutalaa_pipeline.ingest.risale_rnk_kilit import KAYNAK, kilit_yukle
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_rnk import KAPI_ISLEVLERI, RNK_KAPILARI, RnkGirdisi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import SLUG_DESENI
from mutalaa_pipeline.zincir import (
    INGEST_ADIMI,
    RAW_ONEK,
    YOL_PARCASI,
    Calisma,
    calisma_bul,
    dosya_oku,
    girdiler,
    saglam_olmali,
    son_calisma,
    units_oku,
)

QA_ADIMI: Final = "qa"
EN_COK_BULGU: Final = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse uc kapi. Bilinmeyen kapi `GirdiHatasi`."""
    if not gate:
        return RNK_KAPILARI
    if any(g not in RNK_KAPILARI for g in gate):
        raise GirdiHatasi(f"--gate {', '.join(RNK_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in RNK_KAPILARI if k in gate)


def _ham_dosyalar(ctx: RunContext, ingest: Calisma) -> dict[str, bytes]:
    """Ingest girdileri: `raw/risale-rnk-metin/<tarih>/<ad>` -> `ad` (`tr/sozler.txt`, ...)."""
    sonuc: dict[str, bytes] = {}
    for yol, ozet in girdiler(ingest.manifest):
        if not yol.startswith(RAW_ONEK):
            continue
        parcalar = yol.split("/")
        if (
            len(parcalar) not in (4, 5)
            or SLUG_DESENI.fullmatch(parcalar[1]) is None
            or any(YOL_PARCASI.fullmatch(p) is None for p in parcalar[2:])
            or ozet is None
            or OZET_DESENI.fullmatch(ozet) is None
        ):
            raise GirdiHatasi(f"ham girdi yolu ya da ozeti gecersiz: {ingest.run_id}")
        try:
            veri = (ctx.veri_kok / yol).read_bytes()
        except OSError:
            raise GirdiHatasi(f"ham dosya okunamadi: {yol}") from None
        if lineage.sha256_bayt(veri) != ozet:
            raise GirdiHatasi(f"ham dosya ozeti manifestle tutmuyor: {yol}")
        sonuc["/".join(parcalar[3:])] = veri
    if not sonuc:
        raise GirdiHatasi(f"ingest manifestinde ham girdi yok: {ingest.run_id}")
    return sonuc


def yukle(ctx: RunContext, *, run: str | None = None) -> tuple[RnkGirdisi, Calisma]:
    """Son (ya da `--run`) ingest calismasini yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    ingest = (
        calisma_bul(ctx, KAYNAK, run, INGEST_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu=f"once: ingest risale --source {KAYNAK}")
    )
    ozet = ingest.cikti_ozeti()
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    ctx.rapor_ek["ingest_run_id"] = ingest.run_id
    saglam_olmali(ctx, ingest)
    kilit_ozeti_manifest = ingest.ayrinti("kilit_sha256")
    girdi = RnkGirdisi(
        kayit=kayit,
        kilit=kilit_yukle(),
        kilit_ozeti_manifest=kilit_ozeti_manifest
        if isinstance(kilit_ozeti_manifest, str)
        else None,
        ham=_ham_dosyalar(ctx, ingest),
        birimler=[s.veri for s in units_oku(ingest, f"{KAYNAK} units.jsonl")],
        sayfalar=[s.veri for s in dosya_oku(ingest, SAYFALAR_ADI, f"{KAYNAK} {SAYFALAR_ADI}")],
        yapi=[s.veri for s in dosya_oku(ingest, YAPI_ADI, f"{KAYNAK} {YAPI_ADI}")],
        kitaplar=[s.veri for s in dosya_oku(ingest, KITAPLAR_ADI, f"{KAYNAK} {KITAPLAR_ADI}")],
        tablo=kitaplar(),
        depo_kok=ctx.depo_kok,
    )
    return girdi, ingest


def kapilari_kos(girdi: RnkGirdisi, kapilar: Sequence[str]) -> dict[str, KapiSonucu]:
    """Secilen kapilari sirayla calistirir (`G-KAY`, `G-BUT`, `G-NOR`)."""
    return {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = RNK_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, ingest = yukle(ctx, run=run)  # kayitsiz ya da gecersiz kayit: cikis 2
    ctx.rapor_ek["zincir"] = {"ingest": ingest.run_id}
    sonuclar = kapilari_kos(girdi, kapilar)
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
    ctx.sayi("birim", len(girdi.birimler))
    return sonuclar


def komut_qa_run_risale_rnk(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source risale-rnk-metin` komutu; cikis kodunu dondurur."""

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
