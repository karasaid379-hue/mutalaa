"""`mutalaa qa run --source risale-kelime-frekans`: zinciri yukler, kapilari kosar (A20.6).

Akis: kaynak kayitlari (`risale-kelime-frekans` ve uc lugat sozlugu), son `ingest lugat` calismasi
ya da `--run`, ciktilarin sagligi, manifestteki ham girdiler (`data/raw`; ozetle dogrulanir: ham
zip ve uc OCR dosyasi) ve kilit; sonra G-KAY, G-BUT, G-CAP, G-NOR (`qa/checks/risale_lugat.py`).

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id` (= ingest calismasi; ayri bir
anchor adimi yoktur), `units_sha256` (= `lugat.jsonl` ozeti), `kapilar`, `kapi_bulgulari`,
`kapi_sayilari`, `olcumler`, `zincir`; rapor ve bulgular baslik soz, anlam ya da OCR metni
tasimaz. Cikis kodlari: 0 dort kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi.
`--gate` kismi kosusu `export pg`ye yetmez (`qa/rapor.py`).
"""

import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import kelime_frekans, sozluk_ocr
from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK
from mutalaa_pipeline.ingest.lugat_madde import LUGAT_ADI
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.qa import GECTI, KALDI, KAPILAR, QA_KOMUTU
from mutalaa_pipeline.qa.checks.risale_lugat import KAPI_ISLEVLERI, LugatGirdisi, olcumler
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import SLUG_DESENI, Kaynak
from mutalaa_pipeline.zincir import (
    INGEST_ADIMI,
    RAW_ONEK,
    YOL_PARCASI,
    Calisma,
    calisma_bul,
    dosya_oku,
    girdiler,
    saglam_olmali,
    son_calisma,
)

QA_ADIMI = "qa"
EN_COK_BULGU = 20


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri; verilmezse dort kapi."""
    if not gate:
        return KAPILAR
    if any(g not in KAPILAR for g in gate):
        raise GirdiHatasi(f"--gate {', '.join(KAPILAR)} degerlerinden biri olmali")
    return tuple(k for k in KAPILAR if k in gate)


def _ham_girdiler(ctx: RunContext, ingest: Calisma) -> dict[str, bytes]:
    """Ingest manifestindeki ham girdiler: `{kaynak kimligi: bayt}`; ozet manifestle tutmali."""
    beklenen = {KAYNAK, *sozluk_ocr.SOZLUKLER}
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
            or parcalar[1] not in beklenen
            or parcalar[1] in sonuc
        ):
            raise GirdiHatasi(f"ham girdi yolu ya da ozeti gecersiz: {ingest.run_id}")
        try:
            veri = (ctx.veri_kok / yol).read_bytes()
        except OSError:
            raise GirdiHatasi(f"ham dosya okunamadi: {yol}") from None
        if lineage.sha256_bayt(veri) != ozet:
            raise GirdiHatasi(f"ham dosya ozeti manifestle tutmuyor: {yol}")
        sonuc[parcalar[1]] = veri
    if set(sonuc) != beklenen:
        raise GirdiHatasi(f"ingest manifestinde dort ham girdi bekleniyor: {ingest.run_id}")
    return sonuc


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[LugatGirdisi, Calisma]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    ingest = (
        calisma_bul(ctx, KAYNAK, run, INGEST_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest lugat")
    )
    ctx.rapor_ek["anchor_run_id"] = ingest.run_id
    ozet = ingest.cikti_ozeti(LUGAT_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, ingest)
    ham = _ham_girdiler(ctx, ingest)
    commit = ingest.ayrinti("commit")
    girdi = LugatGirdisi(
        kayit=kayitlar[KAYNAK],
        sozluk_kayitlari={s: kayitlar[s] for s in sozluk_ocr.SOZLUKLER},
        kilit=kelime_frekans.kilit_yukle(),
        zip_verisi=ham[KAYNAK],
        ocr_verileri={s: ham[s] for s in sozluk_ocr.SOZLUKLER},
        satirlar=dosya_oku(ingest, LUGAT_ADI, "ingest lugat.jsonl"),
        ingest_commit=commit if isinstance(commit, str) else None,
    )
    return girdi, ingest


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = KAPILAR
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, *sozluk_ocr.SOZLUKLER))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, ingest = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {"ingest": ingest.run_id}
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
    ctx.sayi("madde", len(girdi.satirlar))
    return sonuclar


def komut_qa_run_lugat(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source risale-kelime-frekans` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuclar = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuclar.items())
        sys.stdout.write(
            f"qa run {KAYNAK}: {durumlar} (ingest run {ctx.rapor_ek['anchor_run_id']})\n"
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
        kaynaklar=[KAYNAK, *sozluk_ocr.SOZLUKLER],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
