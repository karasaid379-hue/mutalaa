"""`mutalaa qa run --source xref-atif-iktibas`: son `enrich citations` calismasini denetler (A18.4).

Akis: kaynak kayitlari (`tanzil-uthmani`, `tanzil-simple-clean` ve taranan mealler), son `enrich`
calismasi ya da `--run` (ciktilari saglam ve `xref_citations.jsonl` ozeti manifestle ayni),
staged satirlari; sonra G-KAY, G-BUT, G-CAP (`qa/checks/xref_atif.py`). G-NOR bu kaynakta yoktur.

`--db`: G-CAP'a veritabani uzantisi eklenir (meal ve ayet birimleri, ozetler ve araliklar,
`qa/checks/xref_atif.db_staged_hatalari`).

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id` (= enrich run), `units_sha256`
(= `xref_links.jsonl` ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`; `export pg`
bu alanlarla ve uc kapinin `gecti` olmasiyla arar (`qa/rapor.py`). Rapor icerik metni tasimaz.
Cikis kodlari: 0 uc kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar.enrich_citations import CITATIONS_ADIMI, CITATIONS_DOSYASI, KAYNAK
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.enrich.citations.uret import sayisal
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.meal_kaynaklari import MEAL_KAYNAKLARI
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.checks.xref_atif import (
    GEREKLI_KAYITLAR,
    KAPI_ISLEVLERI,
    AtifGirdisi,
    db_bulgulari,
    db_staged_hatalari,
)
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir
from mutalaa_pipeline.zincir import Calisma, calisma_bul, dosya_oku, saglam_olmali, son_calisma

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


def _manifest_alani(enrich: Calisma) -> tuple[list[str], dict[str, int], str]:
    """Manifestten taranan mealler, tur basina satir sayisi ve data_version."""
    hedefler = enrich.ayrinti("hedefler")
    surum = enrich.ayrinti("data_version")
    istatistik = enrich.ayrinti("istatistik")
    tur = istatistik.get("tur") if isinstance(istatistik, dict) else None
    if (
        not isinstance(hedefler, list)
        or not hedefler
        or not all(isinstance(t, str) for t in hedefler)
        or not isinstance(surum, str)
        or not isinstance(tur, dict)
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in tur.values())
    ):
        raise GirdiHatasi("enrich manifestinde hedefler, data_version ya da istatistik yok")
    return list(hedefler), {str(k): int(v) for k, v in tur.items()}, surum


def _sayisal(s: Satir) -> dict[str, object]:
    try:
        return sayisal(s.veri)
    except ValueError:
        raise GirdiHatasi(f"{s.etiket}: satir {s.no}: ondalik alan gecersiz") from None


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[AtifGirdisi, Calisma]:
    """Zinciri ve dosyayi yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    enrich = (
        calisma_bul(ctx, KAYNAK, run, CITATIONS_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, CITATIONS_ADIMI, ipucu="once: enrich citations")
    )
    ctx.rapor_ek["anchor_run_id"] = enrich.run_id
    ozet = enrich.cikti_ozeti(CITATIONS_DOSYASI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, enrich)
    hedefler, sayilar, surum = _manifest_alani(enrich)
    satirlar = [
        Satir(s.etiket, s.no, _sayisal(s))
        for s in dosya_oku(
            enrich, CITATIONS_DOSYASI, "enrich xref_citations.jsonl", bos_olabilir=True
        )
    ]
    eksik = [h for h in hedefler if h not in kayitlar]
    if eksik:
        raise GirdiHatasi("enrich manifestindeki meal kaynak kaydi yok")
    girdi = AtifGirdisi(
        kayitlar={slug: kayitlar[slug] for slug in (*GEREKLI_KAYITLAR, *hedefler)},
        satirlar=satirlar,
        hedefler=hedefler,
        manifest_sayilari=sayilar,
        data_version=surum,
    )
    return girdi, enrich


def run_qa(
    ctx: RunContext,
    *,
    run: str | None = None,
    kapilar: Sequence[str] = YAPI_KAPILARI,
    db: bool = False,
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((*GEREKLI_KAYITLAR, *MEAL_KAYNAKLARI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, enrich = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {"enrich": enrich.run_id}
    sonuclar = {kapi: KAPI_ISLEVLERI[kapi](girdi) for kapi in kapilar}
    if db and "G-CAP" in sonuclar:
        conn = baglan(ctx.ayarlar, autocommit=True)
        try:
            hatalar = db_staged_hatalari(conn, girdi.satirlar)
        finally:
            conn.close()
        dosya = sonuclar["G-CAP"]
        sonuclar["G-CAP"] = KapiSonucu(
            "G-CAP",
            (*dosya.bulgular, *db_bulgulari(hatalar, "staged-db")),
            {**dosya.sayilar, **{f"db_{k}": v for k, v in hatalar.items()}},
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
    ctx.sayi("satir", len(girdi.satirlar))
    return sonuclar


def komut_qa_run_xref_atif(
    *,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
    db: bool = False,
) -> int:
    """`qa run --source xref-atif-iktibas` komutu; cikis kodunu dondurur."""

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
        kaynaklar=[*GEREKLI_KAYITLAR, *MEAL_KAYNAKLARI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
