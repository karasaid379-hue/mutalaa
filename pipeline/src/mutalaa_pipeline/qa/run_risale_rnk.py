"""`risale-rnk-metin` QA girdisinin yuklenmesi ve kapilarin kosulmasi (A20.1b, A20.2b).

Zincir `anchor -> normalize -> ingest` (`qa/run.py` gibi): son `anchor` calismasini (ya da
`--run`) okur, her halkanin ciktilari saglam ve girdi ozeti ust halkanin ciktisiyla ayni olmali.
G-KAY ve G-BUT ingest birimlerini ve manifestteki `raw/risale-rnk-metin/...` ham dosyalarini
(ozetle dogrulanarak), G-CAP ve G-NOR anchor ciktisini (satir satir akitilir) kullanir; G-CAP
tabani kapilarini gecmis en yeni onceki anchor calismasidir. Rapor alanlari (`kaynak`,
`anchor_run_id`, `units_sha256`, `onceki_anchor_run_id`, `kapilar`, `kapi_bulgulari`,
`kapi_sayilari`, `zincir`, `ingest_run_id`) ve cikis kodlari `qa/run.py` ile ayni bicimdedir:
0 kapilar gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi. Rapor `data/reports/{run_id}.json`;
rapor ve bulgular metin tasimaz.
"""

import sys
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
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
from mutalaa_pipeline.lineage import OZET_DESENI, UNITS_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_rnk import KAPI_ISLEVLERI, RNK_KAPILARI, RnkGirdisi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import SLUG_DESENI
from mutalaa_pipeline.staged import Satir, satirlari_akit
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    RAW_ONEK,
    YOL_PARCASI,
    Calisma,
    calisma_bul,
    dosya_oku,
    girdiler,
    onceki_calisma,
    saglam_olmali,
    son_calisma,
    units_oku,
    ust_calismalar,
)

QA_ADIMI: Final = "qa"
EN_COK_BULGU: Final = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse dort kapi. Bilinmeyen kapi `GirdiHatasi`."""
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


@dataclass(frozen=True)
class Yuklenen:
    girdi: RnkGirdisi
    anchor: Calisma
    normalize: Calisma
    ingest: Calisma


def _ust(ctx: RunContext, calisma: Calisma, adim: str) -> Calisma:
    """Halkanin tek ust calismasi: `risale-rnk-metin`in `adim` calismasi, ciktilari saglam."""
    ustler = ust_calismalar(ctx, calisma)
    if len(ustler) != 1 or ustler[0].adim != adim or ustler[0].source_id != KAYNAK:
        raise GirdiHatasi(
            f"zincir bozuk: {calisma.adim} calistirmasi bir {adim} calistirmasina bagli olmali"
        )
    saglam_olmali(ctx, ustler[0])
    return ustler[0]


def _anchor_akisi(calisma: Calisma, etiket: str) -> Callable[[], Iterator[dict[str, object]]]:
    """Anchor ciktisinin her cagrida yeni satir akisi (ozet `saglam_olmali` ile dogrulanmistir)."""
    yol = calisma.klasor / UNITS_ADI

    def akis() -> Iterator[dict[str, object]]:
        satir: Satir
        for satir in satirlari_akit(yol, etiket):
            yield satir.veri

    return akis


def _onceki(ctx: RunContext, once: str) -> tuple[Onceki | None, str | None, str | None]:
    """G-CAP tabani: `once` kimliginden onceki, kapilarini gecmis en yeni anchor calismasi.

    Donus: capa ozetleri, o calismanin ingest'indeki kilit ozeti ve ayristirici surumu
    (okunamazsa `(None, None, None)`).
    """
    raporlar = QaRaporlari(ctx.veri_kok)

    def onayli(calisma: Calisma) -> bool:
        ozet = calisma.cikti_ozeti()
        return ozet is not None and raporlar.onayli_mi(KAYNAK, calisma.run_id, ozet)

    onceki = onceki_calisma(ctx, KAYNAK, ANCHOR_ADIMI, once=once, kabul=onayli)
    if onceki is None:
        if onceki_calisma(ctx, KAYNAK, ANCHOR_ADIMI, once=once) is not None:
            ctx.uyar(
                "onceki anchor calistirmalari var ama dort kapisini da gecmis olan yok:"
                " onceki capa denetimi yapilamadi"
            )
        return None, None, None
    try:
        ozetler = {
            s.metin("anchor"): s.metin("content_hash")
            for s in satirlari_akit(onceki.klasor / UNITS_ADI, "onceki anchor units.jsonl")
        }
        ingest = _ust(ctx, _ust(ctx, onceki, NORMALIZE_ADIMI), INGEST_ADIMI)
    except GirdiHatasi:
        ctx.uyar("onceki anchor calistirmasi okunamadi: onceki capa denetimi yapilamadi")
        return None, None, None
    kilit = ingest.ayrinti("kilit_sha256")
    surum = ingest.ayrinti("ayristirici_surumu")
    return (
        Onceki(onceki.run_id, ozetler),
        kilit if isinstance(kilit, str) else None,
        surum if isinstance(surum, str) else None,
    )


def yukle(ctx: RunContext, *, run: str | None = None) -> Yuklenen:
    """Son (ya da `--run`) anchor zincirini yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
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
    normalize = _ust(ctx, anchor, NORMALIZE_ADIMI)
    ingest = _ust(ctx, normalize, INGEST_ADIMI)
    ctx.rapor_ek["ingest_run_id"] = ingest.run_id
    kilit_ozeti_manifest = ingest.ayrinti("kilit_sha256")
    ayristirici = ingest.ayrinti("ayristirici_surumu")
    onceki, onceki_kilit, onceki_ayristirici = _onceki(ctx, anchor.run_id)
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
        anchor=_anchor_akisi(anchor, f"anchor {KAYNAK} units.jsonl"),
        onceki=onceki,
        onceki_kilit_ozeti=onceki_kilit,
        ayristirici_surumu=ayristirici if isinstance(ayristirici, str) else None,
        onceki_ayristirici_surumu=onceki_ayristirici,
    )
    return Yuklenen(girdi, anchor, normalize, ingest)


def kapilari_kos(girdi: RnkGirdisi, kapilar: Sequence[str]) -> dict[str, KapiSonucu]:
    """Secilen kapilari sirayla calistirir (`G-KAY`, `G-BUT`, `G-CAP`, `G-NOR`)."""
    return {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = RNK_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    y = yukle(ctx, run=run)  # kayitsiz ya da gecersiz kayit: cikis 2
    girdi = y.girdi
    ctx.rapor_ek["onceki_anchor_run_id"] = girdi.onceki.run_id if girdi.onceki is not None else None
    ctx.rapor_ek["zincir"] = {
        "anchor": y.anchor.run_id,
        "normalize": y.normalize.run_id,
        "ingest": y.ingest.run_id,
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
            f"qa run {KAYNAK}: {durumlar} (anchor run {ctx.rapor_ek['anchor_run_id']})\n"
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
