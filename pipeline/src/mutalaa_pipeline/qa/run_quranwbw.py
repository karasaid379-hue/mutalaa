"""`mutalaa qa run --source quranwbw-tr`: zinciri yukler, kapilari kosar, raporu yazar (A17.6).

Akis: kaynak kayitlari (`quranwbw-tr`, `qac-morfoloji`), son `anchor` (`enrich glosses --wave N`)
calismasi ya da `--run`, zincir (anchor quranwbw-tr -> ingest quranwbw-tr ve anchor
qac-morfoloji: her halkanin ciktilari saglam ve girdi ozeti ust halkanin ciktisiyla ayni), ham
dosya (`data/raw`, manifestteki ozetle) ve kilit; sonra G-KAY, G-BUT, G-CAP
(`qa/checks/quranwbw.py`). G-NOR bu kaynakta yoktur.

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id`, `units_sha256` (= `glosses.jsonl`
ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `olcumler`, `zincir`; `export pg` raporu bu
alanlarla ve uc kapinin `gecti` olmasiyla arar (`qa/rapor.py`). Rapor ve bulgular anlam metni
tasimaz. Cikis kodlari: 0 uc kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.enrich.glosses import GLOSSES_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import quranwbw
from mutalaa_pipeline.ingest.qac import KAYNAK as QAC_KAYNAGI
from mutalaa_pipeline.ingest.quranwbw import ANLAMLAR_ADI, KAYNAK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import DALGALAR_ADI, KELIMELER_ADI, LEMMALAR_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.quranwbw import KAPI_ISLEVLERI, QuranwbwGirdisi, olcumler
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    Calisma,
    calisma_bul,
    dosya_oku,
    ham_dosya,
    saglam_olmali,
    son_calisma,
    ust_calismalar,
)

QA_ADIMI = "qa"
EN_COK_BULGU = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse uc kapi. G-NOR bu kaynakta yoktur (hata)."""
    if not gate:
        return YAPI_KAPILARI
    bilinmeyen = [g for g in gate if g not in YAPI_KAPILARI]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(YAPI_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in YAPI_KAPILARI if k in gate)


def _halkalar(ctx: RunContext, anchor: Calisma) -> tuple[Calisma, Calisma]:
    """Zincir: (ingest quranwbw-tr, anchor qac-morfoloji); ozetler tutar."""
    ustler = ust_calismalar(ctx, anchor)
    bulunan = {(u.adim, u.source_id): u for u in ustler}
    beklenen = {(INGEST_ADIMI, KAYNAK), (ANCHOR_ADIMI, QAC_KAYNAGI)}
    if len(ustler) != len(beklenen) or set(bulunan) != beklenen:
        raise GirdiHatasi(
            f"zincir bozuk: anchor {KAYNAK} calistirmasi ingest {KAYNAK} ve anchor"
            f" {QAC_KAYNAGI} calistirmalarina bagli olmali; {len(ustler)} ust calisma"
        )
    for ust in ustler:
        saglam_olmali(ctx, ust)
    return bulunan[(INGEST_ADIMI, KAYNAK)], bulunan[(ANCHOR_ADIMI, QAC_KAYNAGI)]


def _wave(anchor: Calisma) -> int:
    deger = anchor.ayrinti("wave")
    if not isinstance(deger, int) or isinstance(deger, bool):
        raise GirdiHatasi(f"anchor manifestinde wave yok: {anchor.run_id}")
    return deger


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[QuranwbwGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    anchor = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu="once: enrich glosses --wave N")
    )
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    ozet = anchor.cikti_ozeti(GLOSSES_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, anchor)
    ingest, qac = _halkalar(ctx, anchor)
    kilit = quranwbw.kilit_yukle()
    _, ham_ozet, ham = ham_dosya(ctx, ingest)
    surum = ingest.ayrinti("surum")
    girdi = QuranwbwGirdisi(
        kayit=kayitlar[KAYNAK],
        kilit=kilit,
        ham=ham,
        ham_sha256=ham_ozet,
        ingest_surum=surum if isinstance(surum, str) else None,
        wave=_wave(anchor),
        anlam_satirlari=dosya_oku(ingest, ANLAMLAR_ADI, "ingest meanings.jsonl"),
        gloss_satirlari=dosya_oku(anchor, GLOSSES_ADI, "enrich glosses.jsonl"),
        qac_kelime_satirlari=dosya_oku(qac, KELIMELER_ADI, "qac words.jsonl"),
        qac_lemma_satirlari=dosya_oku(qac, LEMMALAR_ADI, "qac lemmas.jsonl"),
        qac_dalga_satirlari=dosya_oku(qac, DALGALAR_ADI, "qac waves.jsonl"),
    )
    return girdi, anchor, {"ingest": ingest, "qac_anchor": qac}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = YAPI_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, QAC_KAYNAGI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, anchor, halkalar = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {
        "anchor": anchor.run_id,
        "ingest": halkalar["ingest"].run_id,
        "qac_anchor": halkalar["qac_anchor"].run_id,
    }
    ctx.rapor_ek["wave"] = girdi.wave
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
    ctx.sayi("girdi", len(girdi.anlam_satirlari))
    ctx.sayi("aday", len(girdi.gloss_satirlari))
    return sonuclar


def komut_qa_run_quranwbw(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source quranwbw-tr` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (anchor run {ctx.rapor_ek['anchor_run_id']})\n"
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
        kaynaklar=[KAYNAK, QAC_KAYNAGI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
