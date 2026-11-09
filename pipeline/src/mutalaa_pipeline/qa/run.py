"""`mutalaa qa run --source tanzil-uthmani`: zinciri yukler, kapilari kosar, raporu yazar.

Akis: kaynak kayitlari (`require_sources`, iki Tanzil kaynagi), son `anchor` calismasi (ya da
`--run`), zincir (`anchor -> normalize -> ingest x2`: her halkanin ciktilari saglam ve girdi
ozeti ust halkanin ciktisiyla ayni), ham dosyalar (`data/raw`, manifestteki ozetle), kilit,
G-CAP tabani (dort kapiyi da gecmis en yeni onceki anchor calismasi, `_onceki`); sonra G-KAY,
G-BUT, G-CAP, G-NOR (`qa/checks/tanzil.py`).

Cikis kodlari: 0 dort kapi gecti, 1 bir kapi kaldi, 2 girdi ya da zincir hatasi (kayitsiz ya da
gecersiz kaynak kaydi, bozuk zincir, okunamayan dosya dahil). Rapor `data/reports/{run_id}.json`
dosyasidir: temel alanlarin yanina `kaynak`, `anchor_run_id`, `units_sha256`,
`onceki_anchor_run_id` (G-CAP tabani; yoksa null), `kapilar` (`gecti` ya da `kaldi`),
`kapi_bulgulari`, `kapi_sayilari`, `olcumler` ve `zincir` eklenir. `export pg` raporu `komut`,
`kaynak`, `anchor_run_id`, `units_sha256` ve dort kapinin `gecti` olmasiyla arar
(`qa/rapor.py`); karar o calisma icin EN YENI kararlayici rapordadir: `--gate` ile kosulan eksik
rapor bu aramayi karsilamaz, kalan ya da tamamlanamayan sonraki kosu eski bir `gecti` raporunu
gecersiz kilar. Rapor ve iletiler icerik tasimaz (capa, sayi, ozet).
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from mutalaa_pipeline import cikis
from mutalaa_pipeline.adimlar.anchor_tanzil import capa_ozetleri
from mutalaa_pipeline.adimlar.normalize_tanzil import EK_KAYNAK, KAYNAK
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import fikstur, tanzil, tanzil_bicim
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import NOTICE_ADI
from mutalaa_pipeline.qa import (
    GECTI,
    KALDI,
    KAPILAR,
    QA_KOMUTU,
    SURE_ADI_KAYNAGI,
    UST_VERI_KAYNAGI,
)
from mutalaa_pipeline.qa.checks.tanzil import (
    KAPI_ISLEVLERI,
    KapiSonucu,
    Onceki,
    QaGirdisi,
    Varyant,
    olcumler,
)
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    calisma_bul,
    ham_dosya,
    kelimeler_oku,
    onceki_calisma,
    saglam_olmali,
    son_calisma,
    units_oku,
    ust_calismalar,
)

QA_ADIMI = "qa"
EN_COK_BULGU = 20  # rapora yazilan bulgu sayisi (kapi basina)


@dataclass(frozen=True)
class QaSonucu:
    anchor_run_id: str
    units_sha256: str
    kapilar: dict[str, KapiSonucu]

    @property
    def kalanlar(self) -> list[str]:
        return [ad for ad, sonuc in self.kapilar.items() if not sonuc.gecti]


def kapilari_sec(gate: Sequence[str] | None) -> tuple[str, ...]:
    """`--gate` degerleri (tekrarli olabilir); verilmezse dort kapi. Bilinmeyen kapi: hata."""
    if not gate:
        return KAPILAR
    bilinmeyen = [g for g in gate if g not in KAPILAR]
    if bilinmeyen:
        raise GirdiHatasi(f"--gate {', '.join(KAPILAR)} degerlerinden biri olmali")
    return tuple(k for k in KAPILAR if k in gate)


def _ust_halkalar(
    ctx: RunContext, calisma: Calisma, adim: str, kaynaklar: Sequence[str]
) -> dict[str, Calisma]:
    """Zincir halkasinin ust calismalari tam olarak `kaynaklar` icin `adim` calismalaridir."""
    ustler = ust_calismalar(ctx, calisma)
    bulunan = {u.source_id: u for u in ustler if u.adim == adim}
    if len(ustler) != len(kaynaklar) or set(bulunan) != set(kaynaklar):
        raise GirdiHatasi(
            f"zincir bozuk: {calisma.adim} calistirmasi {adim} calistirmasina bagli olmali"
            f" ({', '.join(kaynaklar)}); bulunan {len(ustler)} ust calisma"
        )
    for ust in ustler:
        saglam_olmali(ctx, ust)
    return bulunan


def _varyant(
    ctx: RunContext,
    kaynak: str,
    ingest: Calisma,
    kayit: Kaynak,
    kilit: tanzil.KilitGirdisi,
    sure_tablosu: Sequence[int],
) -> Varyant:
    _, ozet, ham = ham_dosya(ctx, ingest)
    notice = ingest.klasor / NOTICE_ADI
    surum = ingest.ayrinti("surum")
    return Varyant(
        kaynak=kaynak,
        kayit=kayit,
        kilit=kilit,
        ham=ham,
        ham_sha256=ozet,
        ayrisma=tanzil_bicim.ayristir(ham, sure_tablosu),
        bildirim_dosyasi=notice.read_bytes() if notice.is_file() else None,
        ingest_surum=surum if isinstance(surum, str) else None,
    )


def _onceki(ctx: RunContext, once: str) -> Onceki | None:
    """G-CAP tabani: `once` kimliginden onceki, dort kapiyi da gecmis en yeni anchor calismasi.

    Taban hemen onceki calisma DEGILDIR: QA'dan gecmemis ya da kalmis bir ara calisma tabani
    degistirmez; bozuk bir girdiden `anchor`i yeniden kosmak G-CAP'i kendiliginden kaldirmaz.
    Kabul, `export pg`nin arayacagi rapordan okunur (`qa/rapor.py`: en yeni kosu karar verir).
    Tabani olusturan calisma okunamazsa ya da hic yoksa None doner.
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
        return None
    try:
        return Onceki(onceki.run_id, capa_ozetleri(units_oku(onceki, "onceki anchor units.jsonl")))
    except GirdiHatasi:
        ctx.uyar("onceki anchor calistirmasi okunamadi: onceki capa denetimi yapilamadi")
        return None


def yukle(
    ctx: RunContext,
    kayitlar: Mapping[str, Kaynak],
    *,
    run: str | None,
    sure_tablosu: Sequence[int],
) -> tuple[QaGirdisi, Calisma, dict[str, Calisma]]:
    """Zinciri ve ham dosyalari yukler; bozuk zincir `GirdiHatasi` (cikis 2)."""
    anchor = (
        calisma_bul(ctx, KAYNAK, run, ANCHOR_ADIMI)
        if run is not None
        else son_calisma(ctx, KAYNAK, ANCHOR_ADIMI, ipucu="once: anchor --source tanzil-uthmani")
    )
    # Rapor, sonraki adimlar (zincir, kilit, dosyalar) hata verse de bu anchor calismasina
    # baglanir: baglanamayan bir rapor `export pg`de eski `gecti` raporunu gecersiz kilamaz.
    ctx.rapor_ek["anchor_run_id"] = anchor.run_id
    ozet = anchor.cikti_ozeti()
    if ozet is not None:
        ctx.rapor_ek["units_sha256"] = ozet
    saglam_olmali(ctx, anchor)
    normalize = _ust_halkalar(ctx, anchor, NORMALIZE_ADIMI, [KAYNAK])[KAYNAK]
    ingestler = _ust_halkalar(ctx, normalize, INGEST_ADIMI, [KAYNAK, EK_KAYNAK])
    kilitler = tanzil.kilit_yukle()
    girdi = QaGirdisi(
        anchor_satirlari=units_oku(anchor, "anchor units.jsonl"),
        kelime_satirlari=kelimeler_oku(anchor, "anchor words.jsonl"),
        uthmani=_varyant(
            ctx, KAYNAK, ingestler[KAYNAK], kayitlar[KAYNAK], kilitler["uthmani"], sure_tablosu
        ),
        simple=_varyant(
            ctx,
            EK_KAYNAK,
            ingestler[EK_KAYNAK],
            kayitlar[EK_KAYNAK],
            kilitler["simple-clean"],
            sure_tablosu,
        ),
        depo_kok=ctx.depo_kok,
        onceki=_onceki(ctx, anchor.run_id),
        sure_tablosu=sure_tablosu,
    )
    return girdi, anchor, {NORMALIZE_ADIMI: normalize, **ingestler}


def run_qa(
    ctx: RunContext,
    *,
    run: str | None = None,
    kapilar: Sequence[str] = KAPILAR,
    sure_tablosu: Sequence[int] = AYET_SAYILARI,
) -> QaSonucu:
    """Kapilari kosar, `ctx.rapor_ek` alanlarini doldurur; sonucu dondurur (kalan kapi: sonuc)."""
    ctx.rapor_ek["kaynak"] = KAYNAK
    kayitlar = ctx.require_sources((KAYNAK, EK_KAYNAK))  # kayitsiz ya da gecersiz: cikis 2
    ctx.gunluk.yaz("INFO", "qa_basla", source_id=KAYNAK)
    girdi, anchor, halkalar = yukle(ctx, kayitlar, run=run, sure_tablosu=sure_tablosu)
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
            "ingest": {k: halkalar[k].run_id for k in (KAYNAK, EK_KAYNAK)},
        },
    )
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
    ctx.sayi("birim", len(girdi.anchor_satirlari))
    if olcum["ar8_gorulen"]:
        ctx.uyar("AR-8: Farsca ye/kef ya da Arapca-Hint rakam goruldu (Arama 1.3 madde 4: /karar)")
    if olcum["mn_kalan_gorulen"]:
        ctx.uyar("normalizasyondan sonra Arapca bloklarinda birlesen isaret (Mn) kaldi")
    return QaSonucu(anchor.run_id, units_sha, sonuclar)


def _ozet_yaz(sonuc: QaSonucu) -> None:
    durumlar = ", ".join(f"{k} {GECTI if s.gecti else KALDI}" for k, s in sonuc.kapilar.items())
    sys.stdout.write(f"qa run {KAYNAK}: {durumlar} (anchor run {sonuc.anchor_run_id})\n")
    for kapi, s in sonuc.kapilar.items():
        for bulgu in s.bulgular[:EN_COK_BULGU]:
            sys.stdout.write(f"  {kapi} kaldi: {bulgu}\n")
        fazla = len(s.bulgular) - EN_COK_BULGU
        if fazla > 0:
            sys.stdout.write(f"  {kapi} kaldi: (+{fazla} bulgu daha)\n")


def komut_qa_run(
    *,
    source: str,
    run: str | None,
    gate: Sequence[str] | None,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`qa run` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`)."""
    if source == UST_VERI_KAYNAGI:  # isaret ve sayfa satirlari: G-KAY, G-BUT, G-CAP (A11.6)
        from mutalaa_pipeline.qa.run_ust_veri import komut_qa_run_ust_veri

        return komut_qa_run_ust_veri(run=run, gate=gate, config=config, kok=kok)
    if source == SURE_ADI_KAYNAGI:  # sure adi adaylari: G-KAY, G-BUT (A11.3)
        from mutalaa_pipeline.qa.run_sure_adlari import komut_qa_run_sure_adlari

        return komut_qa_run_sure_adlari(run=run, gate=gate, config=config, kok=kok)
    if source in fikstur.KAYNAKLAR:  # sentetik fikstur: dort kapi (A13.6)
        from mutalaa_pipeline.qa.run_fikstur import komut_qa_run_fikstur

        return komut_qa_run_fikstur(source=source, run=run, gate=gate, config=config, kok=kok)
    desteklenen = source == KAYNAK

    def govde(ctx: RunContext) -> int:
        if not desteklenen:
            raise GirdiHatasi(f"qa run bu kaynak icin tanimli degil (yalniz {KAYNAK})")
        sonuc = run_qa(ctx, run=run, kapilar=kapilari_sec(gate))
        _ozet_yaz(sonuc)
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
        kaynaklar=[KAYNAK, EK_KAYNAK] if desteklenen else [source],
        config=config,
        kok=kok,
        govde=govde,
        parametreler=parametreler,
    )
