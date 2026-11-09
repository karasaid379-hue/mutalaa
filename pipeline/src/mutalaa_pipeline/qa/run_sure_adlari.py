"""`mutalaa qa run --source sure-adlari-vikipedi`: zinciri yukler, kapilari kosar, raporu yazar.

Akis: kaynak kayitlari (`sure-adlari-vikipedi`, `quran-meta`, `tanzil-ust-veri`), son `anchor`
calismasi (ya da `--run`), zincir (`anchor -> ingest sure-adlari` ve `ingest tanzil-ust-veri`:
her halkanin ciktilari saglam ve girdi ozeti ust halkanin ciktisiyla ayni), ham dosyalar
(`data/raw`, manifestteki ozetle), kilit; sonra G-KAY ve G-BUT (`qa/checks/sure_adlari.py`).
G-CAP ve G-NOR bu kaynakta yoktur (gerekce o modulun basinda).

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id`, `units_sha256` (= `aliases.jsonl`
ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `olcumler`, `zincir`. `export pg` raporu bu
alanlarla ve iki kapinin `gecti` olmasiyla arar (`qa/rapor.py`). Cikis kodlari: 0 iki kapi gecti,
1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.anchor_sure_adlari import (
    satirlari_coz,
    tanzil_sureleri,
)
from mutalaa_pipeline.adimlar.sure_adlari_adaylar import riskli_adlari_oku
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import sure_adlari
from mutalaa_pipeline.ingest.sure_adlari import (
    KAYNAK,
    QURAN_META,
    QURAN_META_ADI,
    TABLO_ADI,
    YONLENDIRME_ADI,
    MetaSatiri,
    TabloSatiri,
    Yonlendirme,
)
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import ALIASLAR_ADI
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, SURE_ADI_KAPILARI
from mutalaa_pipeline.qa.checks.sure_adlari import (
    KAPI_ISLEVLERI,
    SureAdlariGirdisi,
    olcumler,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
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
UST_VERI = "tanzil-ust-veri"


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse iki kapi. G-CAP ve G-NOR bu kaynakta yoktur (hata)."""
    if not gate:
        return SURE_ADI_KAPILARI
    bilinmeyen = [g for g in gate if g not in SURE_ADI_KAPILARI]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(SURE_ADI_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in SURE_ADI_KAPILARI if k in gate)


def _halkalar(ctx: RunContext, anchor: Calisma) -> tuple[Calisma, Calisma]:
    ustler = ust_calismalar(ctx, anchor)
    bulunan = {(u.adim, u.source_id): u for u in ustler}
    beklenen = {(INGEST_ADIMI, KAYNAK), (INGEST_ADIMI, UST_VERI)}
    if len(ustler) != len(beklenen) or set(bulunan) != beklenen:
        raise GirdiHatasi(
            "zincir bozuk: anchor sure-adlari-vikipedi calistirmasi ingest sure-adlari ve"
            f" ingest {UST_VERI} calistirmalarina bagli olmali; {len(ustler)} ust calisma"
        )
    for ust in ustler:
        saglam_olmali(ctx, ust)
    return bulunan[(INGEST_ADIMI, KAYNAK)], bulunan[(INGEST_ADIMI, UST_VERI)]


def _ham_dosyalar(ctx: RunContext, ingest: Calisma) -> dict[str, dict[str, bytes]]:
    """Ingest manifestindeki ham girdiler (`raw/{slug}/{tarih}/{ad}`), ozet dogrulanarak."""
    sonuc: dict[str, dict[str, bytes]] = {}
    for yol, ozet in girdiler(ingest.manifest):
        parcalar = yol.split("/")
        if len(parcalar) != 4 or parcalar[0] != "raw" or ozet is None:
            raise GirdiHatasi("ingest manifestinde ham girdi yolu gecersiz")
        try:
            veri = (ctx.veri_kok / yol).read_bytes()
        except OSError:
            raise GirdiHatasi(f"ham dosya okunamadi: {yol}") from None
        if lineage.sha256_bayt(veri) != ozet:
            raise GirdiHatasi(f"ham dosya ozeti manifestle tutmuyor: {yol}")
        sonuc.setdefault(parcalar[1], {})[parcalar[3]] = veri
    return sonuc


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[SureAdlariGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    anchor = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu="once: anchor --source " + KAYNAK)
    )
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    ozet = anchor.cikti_ozeti(ALIASLAR_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, anchor)
    ingest, ust_veri = _halkalar(ctx, anchor)
    girdi = SureAdlariGirdisi(
        kayit=kayitlar[KAYNAK],
        diger_kayitlar={k: v for k, v in kayitlar.items() if k != KAYNAK},
        kilit=sure_adlari.kilit_yukle(),
        ham=_ham_dosyalar(ctx, ingest),
        tablo=satirlari_coz(ingest, TABLO_ADI, TabloSatiri),
        yonlendirmeler=satirlari_coz(ingest, YONLENDIRME_ADI, Yonlendirme),
        meta=satirlari_coz(ingest, QURAN_META_ADI, MetaSatiri),
        tanzil=tanzil_sureleri(ust_veri),
        adaylar=dosya_oku(anchor, ALIASLAR_ADI, "anchor aliases.jsonl"),
        riskli_adlar=riskli_adlari_oku(),
        depo_kok=ctx.depo_kok,
    )
    return girdi, anchor, {"sure_adlari_ingest": ingest, "ust_veri_ingest": ust_veri}


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = SURE_ADI_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, QURAN_META, UST_VERI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, anchor, halkalar = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {
        "anchor": anchor.run_id,
        "sure_adlari_ingest": halkalar["sure_adlari_ingest"].run_id,
        "ust_veri_ingest": halkalar["ust_veri_ingest"].run_id,
    }
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    elenen = halkalar["sure_adlari_ingest"].ayrinti("sayilar")
    olcum = olcumler(
        girdi,
        elenen.get("yonlendirme_elenen") if isinstance(elenen, dict) else None,
    )
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
            kapi=kapi,
        )
    ctx.sayi("aday", len(girdi.adaylar))
    capraz = olcum["capraz_sure_anahtar"]
    if isinstance(capraz, dict) and capraz:
        ctx.uyar(f"{len(capraz)} alias_key birden fazla surede ayni (A05 kesme isareti davranisi)")
    fark = olcum["tanzil_fark_sure"]
    if isinstance(fark, list) and fark:
        ctx.uyar(f"{len(fark)} surede Vikipedi ile Tanzil arasinda fark var (adaylar isaretli)")
    return sonuclar


def komut_qa_run_sure_adlari(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source sure-adlari-vikipedi` komutu; cikis kodunu dondurur."""

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
        kaynaklar=[KAYNAK, QURAN_META, UST_VERI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
