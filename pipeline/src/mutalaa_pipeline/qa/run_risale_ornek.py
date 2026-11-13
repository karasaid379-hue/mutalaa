"""`mutalaa qa run --source test-risale-ornek`: zinciri yukler, dort kapiyi kosar (A20.5a).

`qa/run_fikstur.py` ile ayni akis ve ayni rapor bicimi (`kaynak`, `anchor_run_id`, `units_sha256`,
`onceki_anchor_run_id`, `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`); `export pg` bu
raporu dort kapinin `gecti` olmasiyla arar (`qa/__init__.py` varsayilan dort kapi).

Fark: anchor calismasinin IKI ust halkasi vardir (`normalize` ve `ingest`; ingest `sayfalar.jsonl`
dosyasini verir) ve anchor `units.jsonl` yaninda `page_map.jsonl` ile `xref.jsonl` yazar
(`adimlar/risale_ornek.py`); hepsi manifest ozetiyle dogrulanarak okunur. Ham dosya ve kilit yoktur
(veri koddan uretilir). Hata iletileri metin tasimaz.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar.risale_ornek import SAYFA_ESLEME_ADI, XREF_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_ornek import KAYNAK, SAYFALAR_ADI, birimler
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa import GECTI, KALDI, KAPILAR, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_ornek import KAPI_ISLEVLERI, OrnekGirdisi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.run import EN_COK_BULGU, QA_ADIMI, QaSonucu, kapilari_sec
from mutalaa_pipeline.qa.run_fikstur import _onceki
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    calisma_bul,
    dosya_oku,
    saglam_olmali,
    son_calisma,
    units_oku,
    ust_calismalar,
)


def _halkalar(ctx: RunContext, anchor: Calisma) -> tuple[Calisma, Calisma]:
    """Anchor'un iki ust halkasi: `(normalize, ingest)`; normalize'in ust halkasi ayni ingest."""
    ustler = {c.adim: c for c in ust_calismalar(ctx, anchor)}
    if (
        len(ustler) != 2
        or set(ustler) != {NORMALIZE_ADIMI, INGEST_ADIMI}
        or any(c.source_id != KAYNAK for c in ustler.values())
    ):
        raise GirdiHatasi(
            f"zincir bozuk: anchor calistirmasi {KAYNAK} normalize ve ingest calistirmalarina"
            " bagli olmali"
        )
    normalize, ingest = ustler[NORMALIZE_ADIMI], ustler[INGEST_ADIMI]
    saglam_olmali(ctx, normalize)
    saglam_olmali(ctx, ingest)
    normalize_ust = ust_calismalar(ctx, normalize)
    if [c.run_id for c in normalize_ust] != [ingest.run_id]:
        raise GirdiHatasi(
            "zincir bozuk: normalize ve anchor ayni ingest calistirmasina bagli degil"
        )
    return normalize, ingest


def yukle(ctx: RunContext, *, run: str | None) -> tuple[OrnekGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    anchor = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu=f"once: anchor --source {KAYNAK}")
    )
    # Rapor, sonraki adimlar hata verse de bu anchor calismasina baglanir (qa/run.py ile ayni).
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    ozet = anchor.cikti_ozeti()
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, anchor)
    normalize, ingest = _halkalar(ctx, anchor)
    girdi = OrnekGirdisi(
        kayit=kayit,
        anchor_satirlari=units_oku(anchor, f"anchor {KAYNAK} units.jsonl"),
        sayfalar=dosya_oku(ingest, SAYFALAR_ADI, f"ingest {KAYNAK} {SAYFALAR_ADI}"),
        page_map=dosya_oku(anchor, SAYFA_ESLEME_ADI, f"anchor {KAYNAK} {SAYFA_ESLEME_ADI}"),
        xref=dosya_oku(anchor, XREF_ADI, f"anchor {KAYNAK} {XREF_ADI}"),
        beklenen=birimler(),
        depo_kok=ctx.depo_kok,
        onceki=_onceki(ctx, KAYNAK, anchor.run_id),
    )
    return girdi, anchor, {NORMALIZE_ADIMI: normalize, INGEST_ADIMI: ingest}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = KAPILAR
) -> QaSonucu:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonucu dondurur (kalan kapi: sonuc)."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, anchor, halkalar = yukle(ctx, run=run)
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
            "ingest": {KAYNAK: halkalar[INGEST_ADIMI].run_id},
        },
    )
    sonuclar: dict[str, KapiSonucu] = {k: KAPI_ISLEVLERI[k](girdi) for k in kapilar}
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
    ctx.sayi("birim", len(girdi.anchor_satirlari))
    return QaSonucu(anchor.run_id, units_sha, sonuclar)


def kapilari_kos(girdi: OrnekGirdisi, kapilar: Sequence[str] = KAPILAR) -> dict[str, KapiSonucu]:
    """Bellekteki girdi uzerinde kapilari kosar (testler ve araclar icin)."""
    return {k: KAPI_ISLEVLERI[k](girdi) for k in kapilar}


def komut_qa_run_ornek(
    *,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa run --source test-risale-ornek` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuc.kapilar.items())
        sys.stdout.write(f"qa run {KAYNAK}: {durumlar} (anchor run {sonuc.anchor_run_id})\n")
        for kapi, s in sonuc.kapilar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
        if sonuc.kalanlar:
            raise QaKaldi("QA kapisi kaldi: " + ", ".join(sonuc.kalanlar))
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
