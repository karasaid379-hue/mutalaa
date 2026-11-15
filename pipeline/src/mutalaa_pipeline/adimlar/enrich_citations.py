"""Risale ayet atif aday adimi (A20.7b; K-52 madde 13): `mutalaa enrich citations --source ...`.

Girdi `risale-rnk-metin` anchor calismasinin `units.jsonl` dosyasidir (satir satir akitilir,
413 MB'lik dosya bellege alinmaz) ve Tanzil Uthmani ile Simple Clean metni (`enrich/kuran_metni`:
`data/gelen/tanzil-*`, kilitle dogrulanir, bellekte). Cikti
`staged/risale-atif-dizini/{run_id}/xrefs.jsonl`: `xref` aday satirlari (`origin = 'hat'`,
`status = 'aday'`, tur `atif` ya da `iktibas`; ayrinti `enrich/citations.py`). Arac `quran-toolkit`
0.1.0'dir (`arac_sarmalayicilari`); acik atif grameri, Arapca dizi cikarimi ve `score` /
`confidence` hesabi bizdedir (`atif_gramer`, `arapca_dizi`, `atif_guven`).

Adim adi `anchor`dir (`zincir.ANCHOR_ADIMI`): `qa run --source risale-atif-dizini` ve
`export pg` bu calismayi bu adla arar; komut `enrich citations`tir (manifest `komut` alani).
Idempotent: ayni girdi (ayni units ozeti, ayni Tanzil dosyalari, ayni arac surumu) ayni
`xrefs.jsonl` baytlarini verir; `--force` yoksa parmak izi ayniysa adim atlanir.

Sure adi tablosu yoktur (`shared/data/sure-adlari.json` henuz uretilmedi): adli atiflar
("Bakara Suresi, 255") bulunmaz, yalniz adsiz parantezli sayisal bicimler ("(2:255)") bulunur;
bu, rapora `sure_adi_tablosu: yok` diye yazilir. Hata iletileri ve raporlar yalniz sayi, capa ve
ozet tasir; metin asla.
"""

import sys
import time
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.enrich import arac_sarmalayicilari, citations, kuran_metni
from mutalaa_pipeline.enrich.arac_olcumu import bellek_mb
from mutalaa_pipeline.enrich.citations import KAYNAK_ID, Tespit, XrefSatiri
from mutalaa_pipeline.enrich.rapor import yan_rapor_yaz
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import UNITS_ADI
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_akit
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
)

KAYNAK: Final = KAYNAK_ID
SRC_HASH_UZUNLUGU: Final = 16
KAPSAMA_BASAMAGI: Final = 100  # kapsama dagilimi: binde, yuzluk dilimler


@dataclass(frozen=True)
class AtifSonucu:
    run_id: str
    atlandi: bool
    satir: int
    klasor: Path | None
    onceki_run_id: str | None = None


def _kaynak_kontrol(source: str) -> None:
    if source != KAYNAK_RNK:
        raise GirdiHatasi(f"enrich citations yalniz --source {KAYNAK_RNK} icindir")


def veri_surumu(kaynak_surumu: str, units_sha256: str) -> str:
    """`data_version`: yalniz girdi degisince degisir (kaynak surumu + units ozeti)."""
    return f"{KAYNAK}@{kaynak_surumu}/{units_sha256[:12]}"


def _birimler(units: Path) -> Iterator[tuple[str, str, list[dict[str, object]], str, str]]:
    """`(capa, metin, marks, dil, content_hash)`; metni olmayan birim atlanir."""
    for satir in satirlari_akit(units, f"anchor {KAYNAK_RNK} units.jsonl"):
        metin = satir.veri.get("text")
        if not isinstance(metin, str) or metin == "":
            continue
        marks = satir.veri.get("marks")
        attrs = satir.veri.get("attrs")
        ozet = satir.veri.get("content_hash")
        if not isinstance(marks, list) or not isinstance(attrs, dict) or not isinstance(ozet, str):
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: marks, attrs ya da ozet yok")
        dil = attrs.get("dil")
        yield (
            satir.metin("anchor"),
            metin,
            [m for m in marks if isinstance(m, dict)],
            dil if isinstance(dil, str) else "",
            ozet,
        )


def tespitleri_uret(
    units: Path, kuran: kuran_metni.KuranMetni
) -> tuple[list[Tespit], dict[str, str], dict[str, int]]:
    """Butun birimlerden tespitler; `(tespitler, capa -> dil, sayaclar)`."""
    tespitci = arac_sarmalayicilari.ToolkitSarmalayici(kuran.ayetler)
    if arac_sarmalayicilari.paket_surumu() != arac_sarmalayicilari.ARAC_SURUMU:
        raise GirdiHatasi("quran-toolkit surumu 0.1.0 degil (uv.lock)")

    def ayet_kelime(sure: int, ayet: int) -> int | None:
        a = kuran.ayet(sure, ayet)
        return None if a is None else a.kelime

    tespitler: list[Tespit] = []
    dil_haritasi: dict[str, str] = {}
    sayac: Counter[str] = Counter()
    for capa, metin, marks, dil, ozet in _birimler(units):
        sayac["birim"] += 1
        sayac["ar_isareti"] += sum(1 for m in marks if m.get("t") == "ar")
        bulunan = citations.birimden_tespitler(
            capa,
            metin,
            marks,
            tespitci=tespitci,
            ayet_kelime=ayet_kelime,
            src_hash=ozet[:SRC_HASH_UZUNLUGU],
            dil=dil,
        )
        if bulunan:
            dil_haritasi[capa] = dil
            sayac["birim_tespitli"] += 1
            tespitler.extend(bulunan)
    return tespitler, dil_haritasi, dict(sayac)


def _dagilim(degerler: list[int], basamak: int) -> dict[str, int]:
    sayac: Counter[int] = Counter(v // basamak for v in degerler)
    return {str(k * basamak): sayac[k] for k in sorted(sayac)}


def rapor_govdesi(
    satirlar: list[XrefSatiri],
    tespit_sayisi: int,
    dil_haritasi: dict[str, str],
    sayaclar: dict[str, int],
    sure_sn: float,
    bellek_tepe_mb: float,
    kuran: kuran_metni.KuranMetni,
) -> dict[str, object]:
    """Yan rapor: yalniz sayi ve dagilim (metin yok)."""
    tur_dil: Counter[str] = Counter()
    kapsama: list[int] = []
    grup_boyutu: Counter[int] = Counter()
    guven: list[int] = []
    konum_yok = tekrarli = 0
    for s in satirlar:
        evidence = s["evidence"]
        assert isinstance(evidence, dict)
        src = s["src_anchor"]
        assert isinstance(src, str)
        tur_dil[f"{s['type']}|{dil_haritasi.get(src, '')}"] += 1
        if s["type"] == citations.TUR_IKTIBAS:
            k = evidence.get("kapsama")
            if isinstance(k, int):
                kapsama.append(k)
            grup = evidence.get("grup_boyutu")
            grup_boyutu[grup if isinstance(grup, int) else 1] += 1
            konum_yok += bool(evidence.get("kelime_konumu_yok"))
            tekrarli += int(isinstance(evidence.get("tekrar"), int))
        g = s["confidence_binde"]
        assert isinstance(g, int)
        guven.append(g)
    return {
        "kaynak": KAYNAK,
        "satir": len(satirlar),
        "tespit_ham": tespit_sayisi,
        "tur_dil": dict(sorted(tur_dil.items())),
        "ayet_sayisi_dagilimi": {str(k): v for k, v in sorted(grup_boyutu.items())},
        "kapsama_dagilimi_binde": _dagilim(kapsama, KAPSAMA_BASAMAGI),
        "guven_dagilimi_binde": _dagilim(guven, KAPSAMA_BASAMAGI),
        "kelime_konumu_yok": konum_yok,
        "tekrarli_dizi": tekrarli,
        "birim": sayaclar.get("birim", 0),
        "birim_tespitli": sayaclar.get("birim_tespitli", 0),
        "ar_isareti": sayaclar.get("ar_isareti", 0),
        "tanzil_hizasiz_ayet": kuran.hizasiz,
        "sure_adi_tablosu": "yok; yalniz adsiz parantezli sayisal bicimler",
        "arac": arac_sarmalayicilari.ARAC_ADI,
        "arac_surumu": arac_sarmalayicilari.ARAC_SURUMU,
        "sure_sn": round(sure_sn, 1),
        "bellek_tepe_mb": round(bellek_tepe_mb, 1),
    }


def run_enrich_citations(
    ctx: RunContext, source: str, gelen_tarih: str | None = None
) -> AtifSonucu:
    """Kaynak kayitlari, ust calisma, parmak izi, aday satirlari, manifest (en son)."""
    _kaynak_kontrol(source)
    kayitlar = ctx.require_sources((KAYNAK, KAYNAK_RNK))
    surum = kayitlar[KAYNAK].surum
    if surum is None:
        raise GirdiHatasi(f"{KAYNAK}: kaynak kaydinda surum yok")
    ctx.gunluk.yaz("INFO", "enrich_citations_basla", source_id=KAYNAK)
    anchor = son_calisma(ctx, KAYNAK_RNK, ANCHOR_ADIMI, ipucu=f"once: anchor --source {source}")
    saglam_olmali(ctx, anchor)
    units_girdi = girdi_olarak(anchor, UNITS_ADI)
    kuran = kuran_metni.yukle(ctx.veri_kok, gelen_tarih)
    girdiler = [units_girdi, *kuran.girdiler]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "enrich_citations_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AtifSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    t0 = time.perf_counter()
    tespitler, dil_haritasi, sayaclar = tespitleri_uret(anchor.klasor / UNITS_ADI, kuran)
    data_version = veri_surumu(surum, units_girdi.sha256)
    satirlar = citations.xrefleri_birlestir(tespitler, data_version)
    sure = time.perf_counter() - t0
    _, tepe = bellek_mb()
    if not satirlar:
        raise GirdiHatasi("hic aday uretilmedi (bos xrefs.jsonl yazilmaz)")
    sayilar = Counter(str(s["type"]) for s in satirlar)
    ctx.sayi("birim", sayaclar.get("birim", 0))
    ctx.sayi("tespit_ham", len(tespitler))
    ctx.sayi("xref", len(satirlar))
    ctx.sayi("xref_atif", sayilar[citations.TUR_ATIF])
    ctx.sayi("xref_iktibas", sayilar[citations.TUR_IKTIBAS])
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "enrich_citations_dry_run", source_id=KAYNAK)
        return AtifSonucu(ctx.run_id, False, len(satirlar), None)
    klasor = ctx.staged_dizin(KAYNAK)
    cikti = citations.xrefs_yaz_baglam(ctx, satirlar)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "taranan_kaynak": KAYNAK_RNK,
            "surum": surum,
            "data_version": data_version,
            "arac": arac_sarmalayicilari.ARAC_ADI,
            "arac_surumu": arac_sarmalayicilari.ARAC_SURUMU,
            "anchor_run": anchor.run_id,
            "tanzil_tarihleri": dict(sorted(kuran.tarihler.items())),
            "kaynak_qa_onayli": QaRaporlari(ctx.veri_kok).onayli_mi(
                KAYNAK_RNK, anchor.run_id, units_girdi.sha256
            ),
            "sayilar": {
                "birim": sayaclar.get("birim", 0),
                "xref": len(satirlar),
                "atif": sayilar[citations.TUR_ATIF],
                "iktibas": sayilar[citations.TUR_IKTIBAS],
            },
        },
    )
    yan_rapor_yaz(
        ctx,
        "atif",
        rapor_govdesi(satirlar, len(tespitler), dil_haritasi, sayaclar, sure, tepe, kuran),
    )
    ctx.gunluk.yaz("INFO", "enrich_citations_bitti", source_id=KAYNAK)
    return AtifSonucu(ctx.run_id, False, len(satirlar), klasor)


def komut_enrich_citations(
    *,
    source: str,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`enrich citations` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        sonuc = run_enrich_citations(ctx, source, gelen_tarih)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.satir} aday (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.satir} aday, run {sonuc.run_id}"
        sys.stdout.write(f"enrich citations {source}: {ozet}\n")
        return cikis.BASARILI

    parametreler: dict[str, object] = {"source": source}
    if gelen_tarih is not None:
        parametreler["gelen_tarih"] = gelen_tarih
    return komutu_yurut(
        komut="enrich citations",
        adim=ANCHOR_ADIMI,
        kaynaklar=[KAYNAK, KAYNAK_RNK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler=parametreler,
    )
