"""Hazir kaynaktan kelime anlami aday adimi (A17.6; K-50): `mutalaa enrich glosses --wave N`.

Iki ust calismayi zincirler:

* `ingest quranwbw-tr` calismasi (`staged/quranwbw-tr/{run_id}/meanings.jsonl`);
* `enrich morphology` calismasi (`staged/qac-morfoloji/{run_id}/words.jsonl` ve `waves.jsonl`).

QuranWBW anlamlarini QAC konumuyla (`q:s:a:k`) govde lemmasina eslestirir, `normalize_tr` genis
anahtariyla kumeler ve `staged/quranwbw-tr/{run_id}/glosses.jsonl` dosyasini yazar (lemma basina
bir satir; ayrintisi `enrich/glosses.py`). Yalniz `lemma_dalga` dalgasi secilenler islenir:
`--wave 1` dalga 0 ve 1'i birlikte, `--wave N` (N >= 2) yalniz N'yi. Yapay zeka yoktur (K-50).

Adim adi `anchor`dir (`zincir.ANCHOR_ADIMI`): `qa run --source quranwbw-tr` ve `export pg` bu
calismayi bu adla arar. Komut `enrich glosses`tir (manifest `komut` alani). `--wave` parmak
izine girer (`parametreler`); farkli dalga yeni calisma uretir. Kapsama raporu
`data/reports/{run_id}-kapsama.json` dosyasina YALNIZ sayi olarak yazilir.

Hata iletileri yalniz sayi, sira ve ozet tasir; anlam metni asla.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.enrich.glosses import (
    ESIK_PAY,
    ESIK_PAYDA,
    GLOSSES_ADI,
    kapsama_raporu,
    secilen_dalgalar,
    uret,
)
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.qac import KAYNAK as QAC_KAYNAGI
from mutalaa_pipeline.ingest.quranwbw import ANLAMLAR_ADI, KAYNAK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import DALGALAR_ADI, KELIMELER_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    dosya_oku,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
)

ANAHTAR: Final = ("qac_ref",)


@dataclass(frozen=True)
class GlossSonucu:
    run_id: str
    atlandi: bool
    lemma_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def run_enrich_glosses(ctx: RunContext, wave: int) -> GlossSonucu:
    """Kaynak kayitlari, iki ust calisma, parmak izi, aday satirlari, manifest (en son)."""
    secilen = secilen_dalgalar(wave)
    kayitlar = ctx.require_sources((KAYNAK, QAC_KAYNAGI))
    surum = kayitlar[KAYNAK].surum
    if surum is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda surum yok")
    ctx.gunluk.yaz("INFO", "enrich_glosses_basla", source_id=KAYNAK, sayilar={"wave": wave})
    ingest = son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest quranwbw-tr")
    qac = son_calisma(ctx, QAC_KAYNAGI, ANCHOR_ADIMI, ipucu="once: enrich morphology")
    saglam_olmali(ctx, ingest)
    saglam_olmali(ctx, qac)
    girdiler = [
        girdi_olarak(ingest, ANLAMLAR_ADI),
        girdi_olarak(qac, KELIMELER_ADI),
        girdi_olarak(qac, DALGALAR_ADI),
    ]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "enrich_glosses_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return GlossSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    anlamlar = [s.veri for s in dosya_oku(ingest, ANLAMLAR_ADI, "ingest meanings.jsonl")]
    kelimeler = [s.veri for s in dosya_oku(qac, KELIMELER_ADI, "enrich words.jsonl")]
    dalgalar = [s.veri for s in dosya_oku(qac, DALGALAR_ADI, "enrich waves.jsonl")]
    uretim = uret(kelimeler, anlamlar, dalgalar, wave, surum)
    if not uretim.adaylar:
        raise GirdiHatasi(
            f"--wave {wave}: secilen dalgalarda lemma yok (bos aday dosyasi yazilmaz)"
        )
    ctx.sayi("wave", wave)
    ctx.sayi("lemma", len(uretim.adaylar))
    ctx.sayi("tutarli", sum(1 for a in uretim.adaylar if a.tutarli))
    ctx.sayi("tutarsiz", sum(1 for a in uretim.adaylar if not a.tutarli))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_glosses_dry_run", source_id=KAYNAK)
        return GlossSonucu(ctx.run_id, False, len(uretim.adaylar), None)
    klasor = ctx.staged_dizin(KAYNAK)
    cikti = dosya_yaz(ctx, KAYNAK, GLOSSES_ADI, uretim.satirlar, ANAHTAR)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "surum": surum,
            "wave": wave,
            "secilen_dalgalar": sorted(secilen),
            "ingest_run": ingest.run_id,
            "morfoloji_run": qac.run_id,
            "esik": f"baskin_sayi*{ESIK_PAYDA}>=toplam*{ESIK_PAY}",
            "sayilar": {
                "lemma": len(uretim.adaylar),
                "tutarli": sum(1 for a in uretim.adaylar if a.tutarli),
                "tutarsiz": sum(1 for a in uretim.adaylar if not a.tutarli),
                "kelime": uretim.secilen_kelime,
                "lemmasiz_kelime": uretim.lemmasiz_kelime,
            },
        },
    )
    yan_rapor_yaz(ctx, "kapsama", kapsama_raporu(uretim, wave, len(kelimeler), surum))
    ctx.gunluk.yaz("INFO", "enrich_glosses_bitti", source_id=KAYNAK)
    return GlossSonucu(ctx.run_id, False, len(uretim.adaylar), klasor)


def komut_enrich_glosses(
    *, wave: int, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`enrich glosses` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_enrich_glosses(ctx, wave)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.lemma_sayisi} lemma (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.lemma_sayisi} lemma, run {sonuc.run_id}"
        sys.stdout.write(f"enrich glosses {KAYNAK} --wave {wave}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut="enrich glosses",
        adim=ANCHOR_ADIMI,
        kaynaklar=[KAYNAK, QAC_KAYNAGI],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK, "wave": wave},
    )
