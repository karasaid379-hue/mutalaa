"""`mutalaa qa run --source <fikstur>`: zinciri yukler, dort kapiyi kosar, raporu yazar (A13.6).

Akis: kaynak kaydi (`require_sources`), son `anchor` calismasi (ya da `--run`), zincir
(`anchor -> normalize -> ingest fikstur`: her halkanin ciktilari saglam ve girdi ozeti ust halkanin
ciktisiyla ayni), G-CAP tabani (QA'dan gecmis en yeni onceki anchor calismasi); sonra G-KAY, G-BUT,
G-CAP, G-NOR (`qa/checks/fikstur.py`). Ham dosya ve kilit yoktur (veri koddan uretilir).

Rapor `data/reports/{run_id}.json` ve cikis kodlari `qa/run.py` ile ayni bicimdedir: `kaynak`,
`anchor_run_id`, `units_sha256`, `onceki_anchor_run_id`, `kapilar`, `kapi_bulgulari`,
`kapi_sayilari`, `zincir`. `export pg` bu raporla ve dort kapinin `gecti` olmasiyla arar.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.fikstur import birimler
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa import GECTI, KALDI, KAPILAR, QA_KOMUTU
from mutalaa_pipeline.qa.checks.fikstur import KAPI_ISLEVLERI, FiksturGirdisi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.qa.run import EN_COK_BULGU, QA_ADIMI, QaSonucu, kapilari_sec
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    calisma_bul,
    onceki_calisma,
    saglam_olmali,
    son_calisma,
    units_oku,
    ust_calismalar,
)


def _tek_ust(ctx: RunContext, calisma: Calisma, adim: str, slug: str) -> Calisma:
    """Halkanin tek ust calismasi: ayni kaynagin `adim` calismasi (ciktilari saglam)."""
    ustler = ust_calismalar(ctx, calisma)
    if len(ustler) != 1 or ustler[0].adim != adim or ustler[0].source_id != slug:
        raise GirdiHatasi(
            f"zincir bozuk: {calisma.adim} calistirmasi tek bir {slug} {adim} calistirmasina"
            f" bagli olmali; {len(ustler)} ust calisma"
        )
    saglam_olmali(ctx, ustler[0])
    return ustler[0]


def _onceki(ctx: RunContext, slug: str, once: str) -> Onceki | None:
    """G-CAP tabani: `once` kimliginden onceki, dort kapiyi da gecmis en yeni anchor calismasi."""
    raporlar = QaRaporlari(ctx.veri_kok)

    def onayli(calisma: Calisma) -> bool:
        ozet = calisma.cikti_ozeti()
        return ozet is not None and raporlar.onayli_mi(slug, calisma.run_id, ozet)

    onceki = onceki_calisma(ctx, slug, ANCHOR_ADIMI, once=once, kabul=onayli)
    if onceki is None:
        if onceki_calisma(ctx, slug, ANCHOR_ADIMI, once=once) is not None:
            ctx.uyar(
                "onceki anchor calistirmalari var ama dort kapisini da gecmis olan yok:"
                " onceki capa denetimi yapilamadi"
            )
        return None
    try:
        satirlar = units_oku(onceki, "onceki anchor units.jsonl")
        return Onceki(onceki.run_id, {s.metin("anchor"): s.metin("content_hash") for s in satirlar})
    except GirdiHatasi:
        ctx.uyar("onceki anchor calistirmasi okunamadi: onceki capa denetimi yapilamadi")
        return None


def yukle(
    ctx: RunContext, slug: str, *, run: str | None
) -> tuple[FiksturGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kayit = ctx.require_sources(slug)[slug]
    anchor = (
        calisma_bul(ctx, slug, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, slug, ANCHOR_ADIMI, ipucu=f"once: anchor --source {slug}")
    )
    # Rapor, sonraki adimlar hata verse de bu anchor calismasina baglanir (qa/run.py ile ayni).
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    ozet = anchor.cikti_ozeti()
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, anchor)
    normalize = _tek_ust(ctx, anchor, NORMALIZE_ADIMI, slug)
    ingest = _tek_ust(ctx, normalize, INGEST_ADIMI, slug)
    satirlar: list[Satir] = units_oku(anchor, f"anchor {slug} units.jsonl")
    girdi = FiksturGirdisi(
        slug=slug,
        kayit=kayit,
        anchor_satirlari=satirlar,
        beklenen=birimler(slug),
        depo_kok=ctx.depo_kok,
        onceki=_onceki(ctx, slug, anchor.run_id),
    )
    return girdi, anchor, {NORMALIZE_ADIMI: normalize, INGEST_ADIMI: ingest}


def run_qa(
    ctx: RunContext, slug: str, *, run: str | None = None, kapilar: Sequence[str] = KAPILAR
) -> QaSonucu:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonucu dondurur (kalan kapi: sonuc)."""
    ctx.rapor_ek["kaynak"] = slug
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=slug)
    girdi, anchor, halkalar = yukle(ctx, slug, run=run)
    units_sha = anchor.cikti_ozeti()
    if units_sha is None:
        raise GirdiHatasi(f"anchor manifestinde units.jsonl ozeti yok: {anchor.run_id}")
    ctx.rapor_ek.update(
        anchor_run_id=anchor.run_id,
        units_sha256=units_sha,
        onceki_anchor_run_id=girdi.onceki.run_id if girdi.onceki is not None else None,
        zincir={
            "anchor": anchor.run_id,
            "normalize": halkalar[NORMALIZE_ADIMI].run_id,
            "ingest": {slug: halkalar[INGEST_ADIMI].run_id},
        },
    )
    sonuclar: dict[str, KapiSonucu] = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
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
            source_id=slug,
            sayilar={"bulgu": len(sonuc.bulgular)},
            kapi=kapi,
        )
    ctx.sayi("birim", len(girdi.anchor_satirlari))
    return QaSonucu(anchor.run_id, units_sha, sonuclar)


def komut_qa_run_fikstur(
    *,
    source: str,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa run --source <fikstur>` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_qa(ctx, source, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuc.kapilar.items())
        sys.stdout.write(f"qa run {source}: {durumlar} (anchor run {sonuc.anchor_run_id})\n")
        for kapi, s in sonuc.kapilar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
        if sonuc.kalanlar:
            raise QaKaldi("QA kapisi kaldi: " + ", ".join(sonuc.kalanlar))
        return cikis.BASARILI

    parametreler: dict[str, object] = {"source": source}
    if run is not None:
        parametreler["run"] = run
    if gate:
        parametreler["gate"] = list(gate)
    return komutu_yurut(
        komut=QA_KOMUTU,
        adim=QA_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
