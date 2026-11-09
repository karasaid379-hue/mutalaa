"""`mutalaa qa run --source tanzil-ust-veri`: zinciri yukler, kapilari kosar, raporu yazar (A11.6).

Akis: kaynak kayitlari (`tanzil-ust-veri`, `medine-604-duzen`, `quran-meta`), son `anchor`
calismasi (ya da `--run`), zincir (`anchor tanzil-ust-veri` -> `ingest tanzil-ust-veri` ve
`anchor tanzil-uthmani`: her halkanin ciktilari saglam ve girdi ozeti ust halkanin ciktisiyla
ayni), ham XML (`data/raw`, manifestteki ozetle), kilit, dogrulama girdileri (QPC1 ve
quran-meta; yoksa "atlandi"); sonra G-KAY, G-BUT, G-CAP (`qa/checks/ust_veri.py`). G-NOR bu
kaynakta yoktur (gerekce o modulun basinda).

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id`, `units_sha256` (= `markers.jsonl`
ozeti), `sayfalar_sha256` (= `pages.jsonl` ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`,
`olcumler`, `zincir`. `export pg` raporu bu alanlarla ve uc kapinin `gecti` olmasiyla arar
(`qa/rapor.py`). Cikis kodlari: 0 uc kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK, YAPI_DOSYALARI, yapi_ayristir
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import ISARETLER_ADI, SAYFALAR_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.checks.ust_veri import (
    KAPI_ISLEVLERI,
    UstVeriGirdisi,
    olcumler,
)
from mutalaa_pipeline.qa.dogrulama import QPC1_KAYNAGI, QURAN_META_KAYNAGI, qpc1_oku, quran_meta_oku
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import satirlari_oku
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    Calisma,
    calisma_bul,
    dosya_oku,
    ham_dosya,
    kelimeler_oku,
    saglam_olmali,
    son_calisma,
    units_oku,
    ust_calismalar,
)

QA_ADIMI = "qa"
EN_COK_BULGU = 20
KELIME_KAYNAGI = "tanzil-uthmani"


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse uc kapi. G-NOR bu kaynakta yoktur (hata)."""
    if not gate:
        return YAPI_KAPILARI
    bilinmeyen = [g for g in gate if g not in YAPI_KAPILARI]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(YAPI_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in YAPI_KAPILARI if k in gate)


def _halkalar(ctx: RunContext, anchor: Calisma) -> tuple[Calisma, Calisma]:
    """Zincirin tam iki halkasi: ust veri ingest ve tanzil-uthmani anchor (girdi ozetleri tutar)."""
    ustler = ust_calismalar(ctx, anchor)
    bulunan = {(u.adim, u.source_id): u for u in ustler}
    beklenen = {(INGEST_ADIMI, KAYNAK), (ANCHOR_ADIMI, KELIME_KAYNAGI)}
    if len(ustler) != len(beklenen) or set(bulunan) != beklenen:
        raise GirdiHatasi(
            "zincir bozuk: anchor tanzil-ust-veri calistirmasi ingest tanzil-ust-veri ve"
            f" anchor {KELIME_KAYNAGI} calistirmalarina bagli olmali; {len(ustler)} ust calisma"
        )
    for ust in ustler:
        saglam_olmali(ctx, ust)
    return bulunan[(INGEST_ADIMI, KAYNAK)], bulunan[(ANCHOR_ADIMI, KELIME_KAYNAGI)]


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[UstVeriGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    anchor = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu="once: anchor --source tanzil-ust-veri")
    )
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    isaret_ozeti, sayfa_ozeti = anchor.cikti_ozeti(ISARETLER_ADI), anchor.cikti_ozeti(SAYFALAR_ADI)
    if isaret_ozeti is not None:
        ctx.rapor_ek["units_sha256"] = isaret_ozeti
    if sayfa_ozeti is not None:
        ctx.rapor_ek["sayfalar_sha256"] = sayfa_ozeti
    saglam_olmali(ctx, anchor)
    ingest, kelime = _halkalar(ctx, anchor)
    kilit = tanzil.ust_veri_kilidi_yukle()
    _, ham_ozet, ham = ham_dosya(ctx, ingest)
    yapi = yapi_ayristir(ham, kilit.surum)
    ingest_yapi = {
        tur: [s.veri for s in satirlari_oku((ingest.klasor / ad).read_bytes(), f"ust veri {ad}")]
        for tur, ad in YAPI_DOSYALARI.items()
    }
    girdi = UstVeriGirdisi(
        kayit=kayitlar[KAYNAK],
        diger_kayitlar={k: v for k, v in kayitlar.items() if k != KAYNAK},
        kilit=kilit,
        ham=ham,
        ham_sha256=ham_ozet,
        yapi=yapi,
        ingest_yapi=ingest_yapi,
        isaret_satirlari=dosya_oku(anchor, ISARETLER_ADI, "anchor markers.jsonl"),
        sayfa_satirlari=dosya_oku(anchor, SAYFALAR_ADI, "anchor pages.jsonl"),
        kelime_satirlari=kelimeler_oku(kelime, "anchor words.jsonl"),
        birim_satirlari=units_oku(kelime, "anchor units.jsonl"),
        depo_kok=ctx.depo_kok,
        qpc1=qpc1_oku(ctx.veri_kok),
        quran_meta=quran_meta_oku(ctx.veri_kok),
    )
    return girdi, anchor, {"ust_veri_ingest": ingest, "kelime_anchor": kelime}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = YAPI_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, QPC1_KAYNAGI, QURAN_META_KAYNAGI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, anchor, halkalar = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {
        "anchor": anchor.run_id,
        "ingest": halkalar["ust_veri_ingest"].run_id,
        "kelime_anchor": halkalar["kelime_anchor"].run_id,
    }
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    olcum = olcumler(girdi)
    ctx.rapor_ek["kapilar"] = {k: GECTI if s.gecti else KALDI for k, s in sonuclar.items()}
    ctx.rapor_ek["kapi_bulgulari"] = {
        k: list(s.bulgular[:EN_COK_BULGU]) for k, s in sonuclar.items()
    }
    ctx.rapor_ek["kapi_sayilari"] = {k: s.sayilar for k, s in sonuclar.items()}
    ctx.rapor_ek["olcumler"] = olcum
    for kapi, sonuc in sonuclar.items():
        ctx.sayi(f"bulgu_{kapi}", len(sonuc.bulgular))
        ctx.gunluk.yaz(
            "INFO" if sonuc.gecti else "ERROR",
            "qa_kapi",
            source_id=KAYNAK,
            sayilar={"bulgu": len(sonuc.bulgular)},
        )
    ctx.sayi("isaret", len(girdi.isaret_satirlari))
    ctx.sayi("sayfa", len(girdi.sayfa_satirlari))
    for ad in ("qpc1", "quran_meta"):
        deger = olcum.get(ad)
        if isinstance(deger, dict) and deger.get("durum") == "atlandi":
            ctx.uyar(f"{ad} dogrulama girdisi yok: olcum atlandi")
    return sonuclar


def komut_qa_run_ust_veri(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source tanzil-ust-veri` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (anchor run {ctx.rapor_ek['anchor_run_id']})\n"
        )
        kalanlar = [k for k, s in sonuclar.items() if not s.gecti]
        for kapi, s in sonuclar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
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
        kaynaklar=[KAYNAK, QPC1_KAYNAGI, QURAN_META_KAYNAGI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
