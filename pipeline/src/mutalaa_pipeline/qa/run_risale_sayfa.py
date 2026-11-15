"""`risale-baski-rnk` QA girdisinin yuklenmesi ve kapilarin kosulmasi (A20.3, K-52 madde 6-7).

Zincir: `anchor --source risale-baski-rnk` calismasi (`page_map.jsonl`), onun girdisi olan
`risale-rnk-metin` anchor ve ingest calismalari (`units.jsonl`, `sayfalar.jsonl`, `kitaplar.jsonl`).
Satirlar bu iki dosyadan yeniden uretilir ve bayt bayt karsilastirilir (G-BUT). G-CAP tabani
kapilarini gecmis en yeni onceki sayfa esleme calismasidir. Rapor alanlari (`kaynak`,
`anchor_run_id`, `units_sha256` = `page_map.jsonl` ozeti, `onceki_anchor_run_id`, `kapilar`,
`kapi_bulgulari`, `kapi_sayilari`, `zincir`) ve cikis kodlari `qa/run.py` ile ayni bicimdedir:
0 kapilar gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi. Rapor `data/reports/{run_id}.json`;
rapor ve bulgular metin tasimaz.
"""

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar import risale_sayfa
from mutalaa_pipeline.adimlar.risale_sayfa import (
    KAYNAK,
    SAYFA_ESLEME_ADI,
    SAYFA_RAPOR_ADI,
    SayfaZinciri,
)
from mutalaa_pipeline.anchor.risale import kitaplar
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK
from mutalaa_pipeline.ingest.risale_rnk_kaynaklari import KITAPLAR_ADI
from mutalaa_pipeline.ingest.risale_rnk_kilit import kilit_yukle
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_sayfa import (
    KAPI_ISLEVLERI,
    SAYFA_KAPILARI,
    SayfaGirdisi,
    SayfaOnceki,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    Calisma,
    calisma_bul,
    dosya_oku,
    onceki_calisma,
    saglam_olmali,
    son_calisma,
    ust_calismalar,
)

QA_ADIMI: Final = "qa"
EN_COK_BULGU: Final = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse dort kapi. Bilinmeyen kapi `GirdiHatasi`."""
    if not gate:
        return SAYFA_KAPILARI
    if any(g not in SAYFA_KAPILARI for g in gate):
        raise GirdiHatasi(f"--gate {', '.join(SAYFA_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in SAYFA_KAPILARI if k in gate)


def _onceki(ctx: RunContext, once: str) -> SayfaOnceki | None:
    """G-CAP tabani: `once` kimliginden onceki, kapilarini gecmis en yeni sayfa esleme calismasi."""
    raporlar = QaRaporlari(ctx.veri_kok)

    def onayli(calisma: Calisma) -> bool:
        ozet = calisma.cikti_ozeti(SAYFA_ESLEME_ADI)
        return ozet is not None and raporlar.onayli_mi(KAYNAK, calisma.run_id, ozet)

    onceki = onceki_calisma(ctx, KAYNAK, ANCHOR_ADIMI, once=once, kabul=onayli)
    if onceki is None:
        if onceki_calisma(ctx, KAYNAK, ANCHOR_ADIMI, once=once) is not None:
            ctx.uyar(
                "onceki sayfa esleme calistirmalari var ama dort kapisini da gecmis olan yok:"
                " onceki satir denetimi yapilamadi"
            )
        return None
    try:
        satirlar = {
            (s.sayi("volume"), s.sayi("page")): (s.metin("start_anchor"), s.metin("end_anchor"))
            for s in dosya_oku(onceki, SAYFA_ESLEME_ADI, f"onceki {KAYNAK} {SAYFA_ESLEME_ADI}")
        }
    except GirdiHatasi:
        ctx.uyar("onceki sayfa esleme calistirmasi okunamadi: onceki satir denetimi yapilamadi")
        return None
    return SayfaOnceki(onceki.run_id, satirlar)


def _zincir(ctx: RunContext, mine: Calisma) -> SayfaZinciri:
    """Sayfa esleme calismasinin girdileri: tek `risale-rnk-metin` anchor ve ayni ingest."""
    ustler = ust_calismalar(ctx, mine)
    anchorlar = [u for u in ustler if u.adim == ANCHOR_ADIMI and u.source_id == KAYNAK_RNK]
    ingestler = [u for u in ustler if u.adim == INGEST_ADIMI and u.source_id == KAYNAK_RNK]
    if len(ustler) != 2 or len(anchorlar) != 1 or len(ingestler) != 1:
        raise GirdiHatasi(
            f"zincir bozuk: {KAYNAK} calistirmasi bir {KAYNAK_RNK} anchor ve bir ingest"
            " calistirmasina bagli olmali"
        )
    zincir = risale_sayfa.zincir_coz(ctx, anchorlar[0])
    if zincir.ingest.run_id != ingestler[0].run_id:
        raise GirdiHatasi(f"zincir bozuk: {KAYNAK} ingest girdisi anchor zincirindeki ingest degil")
    saglam_olmali(ctx, ingestler[0])
    return zincir


def yukle(ctx: RunContext, *, run: str | None = None) -> tuple[SayfaGirdisi, Calisma, SayfaZinciri]:
    """Son (ya da `--run`) sayfa esleme zincirini yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    mine = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu=f"once: anchor --source {KAYNAK}")
    )
    # Rapor, sonraki adimlar hata verse de bu calismaya baglanir (qa/run.py ile ayni).
    ctx.rapor_ek["anchor_run_id"] = mine.run_id
    ozet = mine.cikti_ozeti(SAYFA_ESLEME_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, mine)
    zincir = _zincir(ctx, mine)
    surum = kayit.surum
    if surum is None:
        raise GirdiHatasi(f"kaynak {KAYNAK}: surum cozulemedi (TOML surum alani yok)")
    cilt = risale_sayfa.cilt_tablosu()
    sayfalar, birimler = risale_sayfa.girdileri_oku(zincir)
    beklenen_satirlar, beklenen_raporlar = risale_sayfa.sayfa_esleme_uret(
        birimler, sayfalar, cilt, surum
    )
    manifest_surumu = mine.ayrinti("data_version")
    girdi = SayfaGirdisi(
        kayit=kayit,
        kilit=kilit_yukle(),
        manifest_data_version=manifest_surumu if isinstance(manifest_surumu, str) else None,
        satirlar=[
            s.veri for s in dosya_oku(mine, SAYFA_ESLEME_ADI, f"{KAYNAK} {SAYFA_ESLEME_ADI}")
        ],
        raporlar=[s.veri for s in dosya_oku(mine, SAYFA_RAPOR_ADI, f"{KAYNAK} {SAYFA_RAPOR_ADI}")],
        beklenen_satirlar=beklenen_satirlar,
        beklenen_raporlar=beklenen_raporlar,
        birimler=birimler,
        sayfalar=sayfalar,
        kitaplar=[
            s.veri for s in dosya_oku(zincir.ingest, KITAPLAR_ADI, f"{KAYNAK_RNK} {KITAPLAR_ADI}")
        ],
        cilt=cilt,
        tablo=kitaplar(),
        depo_kok=ctx.depo_kok,
        onceki=_onceki(ctx, mine.run_id),
    )
    return girdi, mine, zincir


def kapilari_kos(girdi: SayfaGirdisi, kapilar: Sequence[str]) -> dict[str, KapiSonucu]:
    """Secilen kapilari sirayla calistirir (`G-KAY`, `G-BUT`, `G-CAP`, `G-NOR`)."""
    return {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = SAYFA_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, mine, zincir = yukle(ctx, run=run)  # kayitsiz ya da gecersiz kayit: cikis 2
    ctx.rapor_ek["onceki_anchor_run_id"] = girdi.onceki.run_id if girdi.onceki is not None else None
    ctx.rapor_ek["zincir"] = {
        "sayfa_esleme": mine.run_id,
        "anchor": zincir.anchor.run_id,
        "ingest": zincir.ingest.run_id,
    }
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
    ctx.sayi("satir", len(girdi.satirlar))
    return sonuclar


def komut_qa_run_risale_sayfa(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source risale-baski-rnk` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (sayfa esleme run {ctx.rapor_ek['anchor_run_id']})\n"
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
