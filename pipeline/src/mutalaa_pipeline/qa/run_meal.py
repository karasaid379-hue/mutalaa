"""`mutalaa qa run --source <meal>`: zinciri yukler, bes kapiyi kosar, raporlari yazar (A16.3).

Akis: kaynak kayitlari (`require_sources`: meal ve varsa tanigi), son `anchor` calismasi (ya da
`--run`), zincir (`anchor -> normalize -> ingest`; `elmalili-meal` icin anchor ayrica tanigin
ingest'ine baglidir; her halkanin ciktilari saglam ve girdi ozeti ust halkanin ciktisiyla ayni),
ham dosyalar (`data/raw`, manifestteki ozetle) ve YENIDEN URETIM (ham dosyadan ayni kodla
cikarim; G-BUT), G-CAP tabani (dort degil bes kapiyi da gecmis en yeni onceki anchor calismasi);
sonra G-KAY, G-BUT, G-CAP, G-NOR, G-HIZ (`qa/checks/meal.py`). G-MET uygulanmaz (K-49 madde 12).

Cikis kodlari ve rapor `qa/run.py` ile ayni bicimdedir: `kaynak`, `anchor_run_id`, `units_sha256`,
`onceki_anchor_run_id`, `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `zincir`. `export pg` bu
raporla ve bes kapinin `gecti` olmasiyla arar (`qa/rapor.py`); G-HIZ kalirsa yukleme yapilmaz.

Ek olarak `data/reports/{run_id}-meal-raporlari.json` yazilir (kapsam, kod noktasi envanteri,
capraz tanik, sadelestirme taramasi; `qa/meal_raporlari.py`): metin ve sozcuk icermez.
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_kaynaklari as kayitlar
from mutalaa_pipeline.ingest.meal_kilit import kilit_ozeti, kilit_yukle
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI, TANIK_ADI, goreli_yol
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU
from mutalaa_pipeline.qa.checks.meal import KAPI_ISLEVLERI, MealGirdisi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.meal_raporlari import (
    capraz_tanik_raporu,
    kapsam_raporu,
    kod_noktasi_envanteri,
    sadelestirme_taramasi,
)
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.qa.run import EN_COK_BULGU, QA_ADIMI, QaSonucu
from mutalaa_pipeline.runctx import RAPOR_KLASORU, QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import SLUG_DESENI
from mutalaa_pipeline.staged import Satir
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

RAPOR_SONEKI = "-meal-raporlari"


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri (tekrarli olabilir); verilmezse bes kapi. Bilinmeyen kapi: hata."""
    if not gate:
        return kayitlar.MEAL_KAPILARI
    bilinmeyen = [g for g in gate if g not in kayitlar.MEAL_KAPILARI]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(kayitlar.MEAL_KAPILARI)} degerlerinden biri olmali")
    return tuple(k for k in kayitlar.MEAL_KAPILARI if k in gate)


def _ham_dosyalar(ctx: RunContext, ingest: Calisma) -> dict[str, bytes]:
    """Ingest calismasinin butun ham girdileri (`ad -> bayt`); ozetler manifestle tutmali."""
    sonuc: dict[str, bytes] = {}
    for yol, ozet in girdiler(ingest.manifest):
        if not yol.startswith(RAW_ONEK):
            continue
        parcalar = yol.split("/")
        if (
            len(parcalar) != 4
            or SLUG_DESENI.fullmatch(parcalar[1]) is None
            or YOL_PARCASI.fullmatch(parcalar[2]) is None
            or YOL_PARCASI.fullmatch(parcalar[3]) is None
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
        sonuc[parcalar[3]] = veri
    if not sonuc:
        raise GirdiHatasi(f"ingest manifestinde ham girdi yok: {ingest.run_id}")
    return sonuc


def _ust(
    ctx: RunContext, calisma: Calisma, adim: str, kaynak: str, *, tanik: str | None = None
) -> tuple[Calisma, Calisma | None]:
    """Halkanin ust calismalari: `kaynak`in `adim` calismasi (+ varsa tanigin ingest'i)."""
    ustler = ust_calismalar(ctx, calisma)
    ana = [u for u in ustler if u.adim == adim and u.source_id == kaynak]
    tanik_ust = [u for u in ustler if tanik is not None and u.source_id == tanik]
    beklenen = 1 + (1 if tanik is not None else 0)
    if len(ana) != 1 or len(ustler) != beklenen or (tanik is not None and len(tanik_ust) != 1):
        raise GirdiHatasi(
            f"zincir bozuk: {calisma.adim} calistirmasi {kaynak} {adim}"
            f"{' ve ' + tanik + ' ingest' if tanik else ''} calistirmalarina bagli olmali;"
            f" {len(ustler)} ust calisma"
        )
    for u in ustler:
        saglam_olmali(ctx, u)
    return ana[0], tanik_ust[0] if tanik_ust else None


def _bolgeler(ingest: Calisma) -> list[dict[str, object]]:
    """Ingest manifestinin `bolgeler` listesi (yoksa bos)."""
    liste = ingest.ayrinti("bolgeler")
    return [b for b in liste if isinstance(b, dict)] if isinstance(liste, list) else []


def _kilit_ozeti_ingest(ingest: Calisma) -> str | None:
    deger = ingest.ayrinti("kilit_sha256")
    return deger if isinstance(deger, str) else None


def _onceki(ctx: RunContext, slug: str, once: str) -> tuple[Onceki | None, str | None]:
    """G-CAP tabani: `once` kimliginden onceki, bes kapiyi da gecmis en yeni anchor calismasi.

    Donus: capa ozetleri ve o calismanin ingest'indeki kilit ozeti (ikisi de okunamazsa None).
    """
    raporlar = QaRaporlari(ctx.veri_kok)

    def onayli(calisma: Calisma) -> bool:
        ozet = calisma.cikti_ozeti()
        return ozet is not None and raporlar.onayli_mi(slug, calisma.run_id, ozet)

    onceki = onceki_calisma(ctx, slug, ANCHOR_ADIMI, once=once, kabul=onayli)
    if onceki is None:
        if onceki_calisma(ctx, slug, ANCHOR_ADIMI, once=once) is not None:
            ctx.uyar(
                "onceki anchor calistirmalari var ama bes kapisini da gecmis olan yok:"
                " onceki capa denetimi yapilamadi"
            )
        return None, None
    try:
        satirlar = units_oku(onceki, "onceki anchor units.jsonl")
        normalize, _ = _ust(ctx, onceki, NORMALIZE_ADIMI, slug, tanik=kayitlar.kaynak(slug).tanik)
        ingest, _ = _ust(ctx, normalize, INGEST_ADIMI, slug)
        return (
            Onceki(onceki.run_id, {s.metin("anchor"): s.metin("content_hash") for s in satirlar}),
            _kilit_ozeti_ingest(ingest),
        )
    except GirdiHatasi:
        ctx.uyar("onceki anchor calistirmasi okunamadi: onceki capa denetimi yapilamadi")
        return None, None


@dataclass(frozen=True)
class Yuklenen:
    girdi: MealGirdisi
    anchor: Calisma
    normalize: Calisma
    ingest: Calisma
    tanik_ingest: Calisma | None


def yukle(ctx: RunContext, slug: str, *, run: str | None) -> Yuklenen:
    """Zinciri ve ham dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    kaynak = kayitlar.kaynak(slug)
    kapsam = [slug] if kaynak.tanik is None else [slug, kaynak.tanik]
    kayit = ctx.require_sources(kapsam)[slug]
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
    normalize, tanik_ingest = _ust(ctx, anchor, NORMALIZE_ADIMI, slug, tanik=kaynak.tanik)
    ingest, _ = _ust(ctx, normalize, INGEST_ADIMI, slug)
    ham = _ham_dosyalar(ctx, ingest)
    uret = getattr(kayitlar.bagdastirici_modulu(slug), "yeniden_uret", None)
    if uret is None:
        raise GirdiHatasi("meal bagdastiricisi yeniden uretimi tanimlamiyor")
    kilit = kilit_yukle()
    onceki, onceki_kilit = _onceki(ctx, slug, anchor.run_id)
    girdi = MealGirdisi(
        slug=slug,
        kayit=kayit,
        anchor_satirlari=units_oku(anchor, f"anchor {slug} units.jsonl"),
        yeniden=uret(ham),
        kilit_ozeti=_kilit_ozeti_ingest(ingest),
        kilit_guncel=kilit_ozeti(kilit.bolum_sozlugu(kaynak.kilit_bolumu)),
        depo_kok=ctx.depo_kok,
        onceki=onceki,
        onceki_kilit_ozeti=onceki_kilit,
        bolgeler=_bolgeler(ingest),
    )
    return Yuklenen(girdi, anchor, normalize, ingest, tanik_ingest)


def _sade_narrow(ctx: RunContext) -> dict[tuple[int, int], str] | None:
    """Guncel mealin `(sure, ayet) -> tr_narrow` haritasi; anchor calismasi yoksa None."""
    from mutalaa_pipeline.adimlar.meal import meal_capasi

    calismalar = [
        c
        for c in lineage.calismalar(ctx.staged_kaynak_dizini(kayitlar.KAYNAK_SADE))
        if c[2].get("adim") == ANCHOR_ADIMI
    ]
    if not calismalar:
        return None
    run_id, klasor, manifest = calismalar[-1]
    calisma = Calisma(run_id, ANCHOR_ADIMI, kayitlar.KAYNAK_SADE, klasor, manifest)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        return None
    harita: dict[tuple[int, int], str] = {}
    for satir in units_oku(calisma, "sade anchor units.jsonl"):
        cozulen = meal_capasi(kayitlar.KAYNAK_SADE, satir.metin("anchor"))
        if cozulen is not None:
            harita[cozulen] = satir.metin("tr_narrow")
    return harita


def raporlari_kur(
    ctx: RunContext,
    slug: str,
    girdi: MealGirdisi,
    ingest: Calisma,
    tanik_ingest: Calisma | None,
) -> dict[str, object]:
    """Dort raporu kurar (metin ve sozcuk icermez)."""
    ayrintilar = ingest.manifest.get("ayrintilar")
    rapor: dict[str, object] = {
        "kaynak": slug,
        "anchor_run_id": ctx.rapor_ek.get("anchor_run_id"),
        "kapsam": kapsam_raporu(
            slug, girdi.anchor_satirlari, ayrintilar if isinstance(ayrintilar, dict) else {}
        ),
        "kod_noktasi": kod_noktasi_envanteri([s.metin("text") for s in girdi.anchor_satirlari]),
        "capraz_tanik": capraz_tanik_raporu(slug, girdi.anchor_satirlari),
        "sadelestirme_taramasi": None,
    }
    if tanik_ingest is not None:
        sade = _sade_narrow(ctx)
        if sade is None:
            ctx.uyar("sadelestirme taramasi atlandi: elmalili-sade-meal anchor calismasi yok")
        else:
            tanik_satirlari: list[Satir] = dosya_oku(
                tanik_ingest, TANIK_ADI, f"tanik {tanik_ingest.source_id} {TANIK_ADI}"
            )
            rapor["sadelestirme_taramasi"] = sadelestirme_taramasi(
                slug, girdi.anchor_satirlari, sade, tanik_satirlari
            )
    return rapor


def rapor_dosyasi_yaz(ctx: RunContext, rapor: Mapping[str, object]) -> str:
    """`data/reports/{run_id}-meal-raporlari.json` (kanonik JSON, ASCII, atomik)."""
    klasor = ctx.veri_kok / RAPOR_KLASORU
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / f"{ctx.run_id}{RAPOR_SONEKI}.json"
    gecici = klasor / f"{ctx.run_id}{RAPOR_SONEKI}.json.tmp"
    gecici.write_bytes(json_baytlari(dict(rapor)))
    lineage.atomik_degistir(gecici, hedef)
    return goreli_yol(ctx.veri_kok, hedef)


def run_qa(
    ctx: RunContext,
    slug: str,
    *,
    run: str | None = None,
    kapilar: Sequence[str] = kayitlar.MEAL_KAPILARI,
) -> QaSonucu:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonucu dondurur (kalan kapi: sonuc)."""
    ctx.rapor_ek["kaynak"] = slug
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=slug)
    y = yukle(ctx, slug, run=run)
    girdi, anchor, ingest, tanik = y.girdi, y.anchor, y.ingest, y.tanik_ingest
    units_sha = anchor.cikti_ozeti()
    if units_sha is None:
        raise GirdiHatasi(f"anchor manifestinde units.jsonl ozeti yok: {anchor.run_id}")
    zincir: dict[str, object] = {
        "anchor": anchor.run_id,
        "normalize": y.normalize.run_id,
        "ingest": {slug: ingest.run_id},
    }
    if tanik is not None:
        zincir["tanik_ingest"] = {tanik.source_id: tanik.run_id}
    ctx.rapor_ek.update(
        anchor_run_id=anchor.run_id,
        units_sha256=units_sha,
        onceki_anchor_run_id=girdi.onceki.run_id if girdi.onceki is not None else None,
        zincir=zincir,
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
    rapor = raporlari_kur(ctx, slug, girdi, ingest, tanik)
    ctx.rapor_ek["meal_raporlari"] = rapor_dosyasi_yaz(ctx, rapor)
    return QaSonucu(anchor.run_id, units_sha, sonuclar)


def komut_qa_run_meal(
    *,
    source: str,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa run --source <meal>` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        if not kayitlar.meal_mi(source):
            raise GirdiHatasi("qa run meal icin: tanik kaynaklari QA kapisi tasimaz")
        sonuc = run_qa(ctx, source, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuc.kapilar.items())
        sys.stdout.write(f"qa run {source}: {durumlar} (anchor run {sonuc.anchor_run_id})\n")
        for kapi, s in sonuc.kapilar.items():
            for bulgu in s.bulgular[:EN_COK_BULGU]:
                sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
            fazla = len(s.bulgular) - EN_COK_BULGU
            if fazla > 0:
                sys.stdout.write(f"  {kapi} kaldi: (+{fazla} bulgu daha)\n")
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
