"""`mutalaa qa run --source kaikki-tr`: zinciri yukler, kapilari kosar, raporu yazar (A18.2).

Akis: kaynak kayitlari (`kaikki-tr`, `qac-morfoloji`), son `enrich` (`enrich tr-roots`) calismasi
ya da `--run`, zincir (enrich -> anchor meal x N ve anchor qac-morfoloji: her halkanin ciktilari
saglam ve girdi ozeti ust halkanin ciktisiyla ayni), kaikki dokum ozetleri (`SHA256SUMS`); sonra
G-KAY, G-BUT, G-CAP (`qa/checks/tr_roots.py`). G-NOR bu kaynakta yoktur.

`--db`: G-CAP'a veritabani uzantisi eklenir (`tr_root_index` icin yari acik aralik, metin
uzunlugu ve guncel `unit_hash`); bu bulgular G-CAP sonucuna katilir.

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id` (= enrich run), `units_sha256`
(= `tr_lemmas.jsonl` ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`; `export pg`
raporu bu alanlarla ve uc kapinin `gecti` olmasiyla arar (`qa/rapor.py`). Rapor ve bulgular sozluk
metni tasimaz. Cikis kodlari: 0 uc kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar.enrich_tr_roots import (
    KAYNAK,
    OTA_DOSYASI,
    QAC_KAYNAGI,
    TR_DOSYASI,
    TR_ROOTS_ADIMI,
    ozetler_oku,
)
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.tr_roots.uret import FORMLAR_ADI, LEMMALAR_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import KOKLER_ADI
from mutalaa_pipeline.lineage import LEMMALAR_ADI as QAC_LEMMALAR_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.checks.tr_roots import KAPI_ISLEVLERI, TrRootsGirdisi, db_g_cap
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
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


def _qac_halkasi(ctx: RunContext, enrich: Calisma) -> Calisma:
    ustler = ust_calismalar(ctx, enrich)
    qac = [u for u in ustler if u.source_id == QAC_KAYNAGI and u.adim == ANCHOR_ADIMI]
    if len(qac) != 1:
        raise GirdiHatasi(
            f"zincir bozuk: enrich {KAYNAK} calistirmasi tek {QAC_KAYNAGI} anchor calistirmasina"
            " bagli olmali"
        )
    for ust in ustler:
        saglam_olmali(ctx, ust)
    return qac[0]


def _dokum_ozetleri(ctx: RunContext, enrich: Calisma) -> tuple[dict[str, str], dict[str, str]]:
    """(manifestteki, SHA256SUMS'taki) dokum ozetleri: dosya adi -> SHA-256."""
    manifestteki: dict[str, str] = {}
    klasor: Path | None = None
    for yol, ozet in girdiler(enrich.manifest):
        ad = yol.rsplit("/", 1)[-1]
        if ad in (TR_DOSYASI, OTA_DOSYASI) and ozet is not None:
            manifestteki[ad] = ozet
            klasor = (ctx.veri_kok / yol).parent
    if klasor is None:
        raise GirdiHatasi("enrich manifestinde kaikki dokum girdileri yok")
    kayitli = {ad: o for ad, o in ozetler_oku(klasor).items() if ad in manifestteki}
    return manifestteki, kayitli


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[TrRootsGirdisi, Calisma, Calisma]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    enrich = (
        calisma_bul(ctx, KAYNAK, run, TR_ROOTS_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, TR_ROOTS_ADIMI, ipucu="once: enrich tr-roots")
    )
    ctx.rapor_ek["anchor_run_id"] = enrich.run_id
    ozet = enrich.cikti_ozeti(LEMMALAR_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, enrich)
    qac = _qac_halkasi(ctx, enrich)
    manifestteki, kayitli = _dokum_ozetleri(ctx, enrich)
    sayilar = enrich.ayrinti("sayilar")
    token = sayilar.get("token") if isinstance(sayilar, dict) else None
    surum = enrich.ayrinti("surum")
    girdi = TrRootsGirdisi(
        kayit=kayitlar[KAYNAK],
        manifest_surum=surum if isinstance(surum, str) else None,
        manifest_token=token if isinstance(token, int) and not isinstance(token, bool) else None,
        dokum_ozetleri=manifestteki,
        kayitli_ozetler=kayitli,
        lemma_satirlari=dosya_oku(enrich, LEMMALAR_ADI, "enrich tr_lemmas.jsonl"),
        form_satirlari=dosya_oku(enrich, FORMLAR_ADI, "enrich tr_forms.jsonl"),
        qac_kok_satirlari=dosya_oku(qac, KOKLER_ADI, "qac roots.jsonl"),
        qac_lemma_satirlari=dosya_oku(qac, QAC_LEMMALAR_ADI, "qac lemmas.jsonl"),
    )
    return girdi, enrich, qac


def run_qa(
    ctx: RunContext,
    *,
    run: str | None = None,
    kapilar: Sequence[str] = YAPI_KAPILARI,
    db: bool = False,
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, QAC_KAYNAGI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, enrich, qac = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {"enrich": enrich.run_id, "qac_anchor": qac.run_id}
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    if db and "G-CAP" in sonuclar:
        conn = baglan(ctx.ayarlar, autocommit=True)
        try:
            ek = db_g_cap(conn)
        finally:
            conn.close()
        dosya = sonuclar["G-CAP"]
        sonuclar["G-CAP"] = KapiSonucu(
            "G-CAP", (*dosya.bulgular, *ek.bulgular), {**dosya.sayilar, **ek.sayilar}
        )
    ctx.rapor_ek["kapilar"] = {k: GECTI if s.gecti else KALDI for k, s in sonuclar.items()}
    ctx.rapor_ek["kapi_bulgulari"] = {
        k: list(s.bulgular[:EN_COK_BULGU]) for k, s in sonuclar.items()
    }
    ctx.rapor_ek["kapi_sayilari"] = {k: s.sayilar for k, s in sonuclar.items()}
    ctx.rapor_ek["db_uzantisi"] = db
    for kapi, sonuc in sonuclar.items():
        ctx.sayi(f"bulgu_{kapi}", len(sonuc.bulgular))
        ctx.gunluk.yaz(
            "INFO" if sonuc.gecti else "ERROR",
            "qa_kapi",
            source_id=KAYNAK,
            sayilar={"bulgu": len(sonuc.bulgular)},
            kapi=kapi,
        )
    ctx.sayi("lemma", len(girdi.lemma_satirlari))
    ctx.sayi("form", len(girdi.form_satirlari))
    return sonuclar


def komut_qa_run_tr_roots(
    *,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
    db: bool = False,
) -> int:
    """`qa run --source kaikki-tr` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate), db=db)
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (enrich run {ctx.rapor_ek['anchor_run_id']})\n"
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
    if db:
        parametreler["db"] = True
    return komutu_yurut(
        komut=QA_KOMUTU,
        adim=QA_ADIMI,
        kaynaklar=[KAYNAK, QAC_KAYNAGI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
