"""QAC morfoloji zenginlestirme adimi (A17.3, A17.5; K-50): `mutalaa enrich morphology`.

Iki ust calismayi zincirler:

* `ingest qac` calismasi (`staged/qac-morfoloji/{run_id}/notice.txt`; ham dosya manifestteki
  ozetle dogrulanarak `data/raw`'dan okunur ve bellekte ayristirilir);
* `anchor --source tanzil-ust-veri` calismasinin `markers.jsonl` dosyasi (30. cuz siniri).

ve `staged/qac-morfoloji/{run_id}/` altina dort dosya yazar (hepsi ASCII kacisli, sirali, LF):

* `words.jsonl`: QAC kelimeleri (`anchor` = `q:{sure}:{ayet}:{kelime}`, `surah`, `ayah`, `word`,
  `pos`, `lemma_qac_ref`, `root_letters_bw`, `features`, `segment_sayisi`, `govde_sayisi`,
  `source_id`, `data_version`);
* `lemmas.jsonl` (`qac_ref`, `ilk_gecis`, `text`, `text_clean`, `ayirt_no`, `root_letters_bw`,
  `occurrences`, `ayah_count`, `idf_q`) ve `roots.jsonl` (`letters_bw`, `ilk_gecis`, `letters`,
  `occurrences`, `ayah_count`, `idf_q`): KIMLIK TASIMAZ; `export pg` kimligi (`kimlik_ata`) verir;
* `waves.jsonl`: lemma basina `dalga` ve `sira` (K-50 madde 7).

Adim adi `anchor`dir (`zincir.ANCHOR_ADIMI`): cikti, kelime capasina bagli sirali satirlardir ve
`export pg` ile `qa run` anchor calismasini bu adla arar; ayri bir adim adi bu kancalarin
genellestirilmesini gerektirirdi. Komut `enrich morphology`dir (manifest `komut` alani).
Hata iletileri yalniz sayi, sira ve ozet tasir; icerik metni asla.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.enrich.dalga_raporu import dalga_raporu
from mutalaa_pipeline.enrich.morphology import (
    DALGA0_ETIKETLERI,
    cuz_baslangici,
    uret,
)
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil_ust_veri
from mutalaa_pipeline.ingest.qac import KAYNAK, ayristir
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import (
    DALGALAR_ADI,
    ISARETLER_ADI,
    KOKLER_ADI,
    LEMMALAR_ADI,
    NOTICE_ADI,
)
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz, kelimeler_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    dosya_oku,
    girdi_olarak,
    girdileri_ayni,
    ham_dosya,
    saglam_olmali,
    son_calisma,
)

UST_VERI: Final = tanzil_ust_veri.KAYNAK
LEMMA_ANAHTARI: Final = ("qac_ref",)
KOK_ANAHTARI: Final = ("letters_bw",)


@dataclass(frozen=True)
class EnrichSonucu:
    run_id: str
    atlandi: bool
    kelime_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def run_enrich_morphology(ctx: RunContext) -> EnrichSonucu:
    """Kaynak kayitlari, iki ust calisma, parmak izi, satirlar, manifest (en son)."""
    kayitlar = ctx.require_sources((KAYNAK, UST_VERI))
    surum = kayitlar[KAYNAK].surum
    if surum is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda surum yok")
    ctx.gunluk.yaz("INFO", "enrich_morphology_basla", source_id=KAYNAK)
    ingest = son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest qac")
    ust_veri = son_calisma(
        ctx, UST_VERI, ANCHOR_ADIMI, ipucu="once: anchor --source tanzil-ust-veri"
    )
    saglam_olmali(ctx, ingest)
    saglam_olmali(ctx, ust_veri)
    girdiler = [girdi_olarak(ingest, NOTICE_ADI), girdi_olarak(ust_veri, ISARETLER_ADI)]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "enrich_morphology_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return EnrichSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    _, _, ham = ham_dosya(ctx, ingest)
    isaretler = [s.veri for s in dosya_oku(ust_veri, ISARETLER_ADI, "ust veri markers.jsonl")]
    cuz_basi = cuz_baslangici(isaretler)
    uretim = uret(ayristir(ham).segmentler, cuz_basi, surum)
    envanter, dalgalar = uretim.envanter, uretim.dalgalar
    ciktilar = [
        kelimeler_yaz(ctx, KAYNAK, uretim.kelime_satirlari),
        dosya_yaz(ctx, KAYNAK, LEMMALAR_ADI, uretim.lemma_satirlari, LEMMA_ANAHTARI),
        dosya_yaz(ctx, KAYNAK, KOKLER_ADI, uretim.kok_satirlari, KOK_ANAHTARI),
        dosya_yaz(ctx, KAYNAK, DALGALAR_ADI, uretim.dalga_satirlari, LEMMA_ANAHTARI),
    ]
    dagilim = Counter(d.dalga for d in dalgalar)
    sayilar: dict[str, object] = {
        "kelime": envanter.kelime_sayisi,
        "ayet": envanter.toplam_ayet,
        "lemma": len(envanter.lemmalar),
        "kok": len(envanter.kokler),
        "lemmasiz_kelime": envanter.lemmasiz_kelime,
        "koksuz_kelime": envanter.koksuz_kelime,
        "iki_govdeli_kelime": envanter.iki_govdeli_kelime,
        "ayirt_rakamli_lemma": sum(1 for lm in envanter.lemmalar if lm.qac_ref[-1:].isdigit()),
        "dalga": {str(no): dagilim.get(no, 0) for no in range(5)},
        "dalga_zorla": sum(1 for d in dalgalar if d.zorla),
    }
    for ad in ("kelime", "ayet", "lemma", "kok", "lemmasiz_kelime", "iki_govdeli_kelime"):
        ctx.sayi(ad, int(str(sayilar[ad])))
    for no in range(5):
        ctx.sayi(f"dalga_{no}", dagilim.get(no, 0))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_morphology_dry_run", source_id=KAYNAK)
        return EnrichSonucu(ctx.run_id, False, envanter.kelime_sayisi, None)
    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=ciktilar,
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "surum": surum,
            "ingest_run": ingest.run_id,
            "ust_veri_run": ust_veri.run_id,
            "cuz30_baslangic": list(cuz_basi),
            "dalga0_etiket_sayisi": len(DALGA0_ETIKETLERI),
            "sayilar": sayilar,
        },
    )
    # A17.5: dalga tablosu raporu (yalniz sayi; data/reports/{run_id}-dalga.json)
    yan_rapor_yaz(ctx, "dalga", dalga_raporu(envanter, dalgalar, cuz_basi, KAYNAK, surum))
    ctx.gunluk.yaz("INFO", "enrich_morphology_bitti", source_id=KAYNAK)
    return EnrichSonucu(ctx.run_id, False, envanter.kelime_sayisi, klasor)


def komut_enrich_morphology(
    *, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`enrich morphology` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_enrich_morphology(ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.kelime_sayisi} kelime (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.kelime_sayisi} kelime, run {sonuc.run_id}"
        sys.stdout.write(f"enrich morphology {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut="enrich morphology",
        adim=ANCHOR_ADIMI,
        kaynaklar=[KAYNAK, UST_VERI],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": KAYNAK},
    )
