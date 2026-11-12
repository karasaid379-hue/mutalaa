"""`mutalaa qa run --source qac-morfoloji`: zinciri yukler, kapilari kosar, raporu yazar (A17.3).

Akis: kaynak kayitlari (`qac-morfoloji`, `tanzil-ust-veri`, `mustafa0x-morfoloji`), son `anchor`
(`enrich morphology`) calismasi ya da `--run`, zincir (`anchor qac-morfoloji` -> `ingest qac` ve
`anchor tanzil-ust-veri` -> `anchor tanzil-uthmani`: her halkanin ciktilari saglam ve girdi ozeti
ust halkanin ciktisiyla ayni), ham dosya (`data/raw`, manifestteki ozetle), kilit, Tanzil kelime
bolmesi ve (varsa) `mustafa0x` kopyasi; sonra G-KAY, G-BUT, G-CAP (`qa/checks/qac.py`).
G-NOR bu kaynakta yoktur.

Rapor `data/reports/{run_id}.json`: `kaynak`, `anchor_run_id`, `units_sha256` (= `words.jsonl`
ozeti), `kapilar`, `kapi_bulgulari`, `kapi_sayilari`, `olcumler`, `zincir`. `export pg` raporu bu
alanlarla ve uc kapinin `gecti` olmasiyla arar (`qa/rapor.py`). `mustafa0x` kopyasi varsa lemma ve
kok yazim farklari AYRICA `data/reports/{run_id}-capraz.json` dosyasina yalniz `qac_ref`,
`letters_bw`, kelime capasi ve sayi olarak yazilir (metin yok; `komut` alani olmadigindan
`qa/rapor.py` onu rapor saymaz). Cikis kodlari: 0 uc kapi gecti, 1 bir kapi kaldi, 2 girdi ya da
zincir hatasi.
"""

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.enrich_morphology import UST_VERI
from mutalaa_pipeline.enrich.morphology import cuz_baslangici
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import qac
from mutalaa_pipeline.ingest.qac import KAYNAK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import ISARETLER_ADI, KELIMELER_ADI, NOTICE_ADI
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.qa import GECTI, KALDI, QA_KOMUTU, YAPI_KAPILARI
from mutalaa_pipeline.qa.checks.qac import KAPI_ISLEVLERI, QacGirdisi, olcumler
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.qac_capraz import KAYNAK as CAPRAZ_KAYNAGI
from mutalaa_pipeline.qa.qac_capraz import mustafa0x_oku
from mutalaa_pipeline.runctx import RAPOR_KLASORU, QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
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


def _halkalar(ctx: RunContext, enrich: Calisma) -> tuple[Calisma, Calisma, Calisma]:
    """Zincir: (ingest qac, anchor tanzil-ust-veri, anchor tanzil-uthmani); ozetler tutar."""
    ustler = ust_calismalar(ctx, enrich)
    bulunan = {(u.adim, u.source_id): u for u in ustler}
    beklenen = {(INGEST_ADIMI, KAYNAK), (ANCHOR_ADIMI, UST_VERI)}
    if len(ustler) != len(beklenen) or set(bulunan) != beklenen:
        raise GirdiHatasi(
            "zincir bozuk: anchor qac-morfoloji calistirmasi ingest qac-morfoloji ve"
            f" anchor {UST_VERI} calistirmalarina bagli olmali; {len(ustler)} ust calisma"
        )
    ust_veri = bulunan[(ANCHOR_ADIMI, UST_VERI)]
    for ust in ustler:
        saglam_olmali(ctx, ust)
    ikinci = ust_calismalar(ctx, ust_veri)
    kelime = [u for u in ikinci if (u.adim, u.source_id) == (ANCHOR_ADIMI, KELIME_KAYNAGI)]
    if len(kelime) != 1:
        raise GirdiHatasi(f"zincir bozuk: anchor {UST_VERI} anchor {KELIME_KAYNAGI}'a bagli olmali")
    saglam_olmali(ctx, kelime[0])
    return bulunan[(INGEST_ADIMI, KAYNAK)], ust_veri, kelime[0]


def yukle(
    ctx: RunContext, kayitlar: dict[str, Kaynak], *, run: str | None
) -> tuple[QacGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri ve dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    enrich = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu="once: enrich morphology")
    )
    ctx.rapor_ek["anchor_run_id"] = enrich.run_id
    ozet = enrich.cikti_ozeti(KELIMELER_ADI)
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, enrich)
    ingest, ust_veri, kelime = _halkalar(ctx, enrich)
    kilit = qac.kilit_yukle()
    _, ham_ozet, ham = ham_dosya(ctx, ingest)
    bildirim = ingest.klasor / NOTICE_ADI
    surum = ingest.ayrinti("surum")
    girdi = QacGirdisi(
        kayit=kayitlar[KAYNAK],
        kilit=kilit,
        ham=ham,
        ham_sha256=ham_ozet,
        dosya=qac.ayristir(ham),
        bildirim_dosyasi=bildirim.read_bytes() if bildirim.is_file() else None,
        ingest_surum=surum if isinstance(surum, str) else None,
        cuz_basi=cuz_baslangici(
            [s.veri for s in dosya_oku(ust_veri, ISARETLER_ADI, "anchor markers.jsonl")]
        ),
        kelime_satirlari=dosya_oku(enrich, KELIMELER_ADI, "enrich words.jsonl"),
        lemma_satirlari=dosya_oku(enrich, lineage.LEMMALAR_ADI, "enrich lemmas.jsonl"),
        kok_satirlari=dosya_oku(enrich, lineage.KOKLER_ADI, "enrich roots.jsonl"),
        dalga_satirlari=dosya_oku(enrich, lineage.DALGALAR_ADI, "enrich waves.jsonl"),
        tanzil_kelime_satirlari=kelimeler_oku(kelime, "anchor words.jsonl"),
        depo_kok=ctx.depo_kok,
        capraz=mustafa0x_oku(ctx.veri_kok),
    )
    return girdi, enrich, {"ingest": ingest, "ust_veri_anchor": ust_veri, "kelime_anchor": kelime}


def _capraz_dosyasi(ctx: RunContext, girdi: QacGirdisi) -> None:
    """Lemma ve kok yazim farklarini (yalniz kimlik ve sayi) ayri rapor dosyasina yazar."""
    kars = girdi.karsilastirma
    if kars is None or girdi.capraz is None:
        return
    govde: dict[str, object] = {
        "run_id": ctx.run_id,
        "kaynak": KAYNAK,
        "kopya": CAPRAZ_KAYNAGI,
        "kopya_tarih": girdi.capraz.tarih,
        "sayilar": kars.sayilar(),
        "lemma_farkli_qac_ref": list(kars.lemma_farkli_qac_ref),
        "kok_farkli_letters_bw": list(kars.kok_farkli_letters_bw),
        "ornek_capalar": list(kars.ornek_capalar),
    }
    klasor = ctx.veri_kok / RAPOR_KLASORU
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / f"{ctx.run_id}-capraz.json"
    gecici = klasor / f"{ctx.run_id}-capraz.json.tmp"
    with gecici.open("wb") as dosya:
        dosya.write(json_baytlari(govde))
        dosya.flush()
        os.fsync(dosya.fileno())
    lineage.atomik_degistir(gecici, hedef)


def run_qa(
    ctx: RunContext, *, run: str | None = None, kapilar: Sequence[str] = YAPI_KAPILARI
) -> dict[str, KapiSonucu]:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonuclari dondurur."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, UST_VERI, CAPRAZ_KAYNAGI))
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, enrich, halkalar = yukle(ctx, kayitlar, run=run)
    ctx.rapor_ek["zincir"] = {
        "anchor": enrich.run_id,
        "ingest": halkalar["ingest"].run_id,
        "ust_veri_anchor": halkalar["ust_veri_anchor"].run_id,
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
            kapi=kapi,
        )
    ctx.sayi("kelime", len(girdi.kelime_satirlari))
    ctx.sayi("lemma", len(girdi.lemma_satirlari))
    if girdi.capraz is None:
        ctx.uyar(f"{CAPRAZ_KAYNAGI} kopyasi yok: capraz sayim atlandi")
    else:
        _capraz_dosyasi(ctx, girdi)
    return sonuclar


def komut_qa_run_qac(
    *, run: str | None, gate: Sequence[str] | None, config: Path | None, kok: Path | None
) -> int:
    """`qa run --source qac-morfoloji` komutu; cikis kodunu dondurur."""

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
        kaynaklar=[KAYNAK, UST_VERI, CAPRAZ_KAYNAGI],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
