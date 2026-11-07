"""Tanzil capa adimi (A10.4): `q:{sure}:{ayet}` capasi, `content_hash` ve kuresel ayet sirasi.

`mutalaa anchor --source tanzil-uthmani`: son `normalize` calismasinin satirlarina `export pg`
icin gereken alanlari ekler ve `staged/tanzil-uthmani/{run_id}/units.jsonl` olarak yazar:

    kind          "ayet"
    ord           kuresel ayet sirasi 1..6236 (2:255 icin 7 + 255 = 262)
    ayah_lo       ord (yari acik aralik [ayah_lo, ayah_hi) tek ayeti gosterir)
    ayah_hi       ord + 1
    content_hash  UTF-8 baytlarin SHA-256'si (64 kucuk harfli onaltilik, onek yok)
    metin_durumu  "onayli" (kanonik kaynak, K-38 madde 4)
    data_version  "tanzil-uthmani@{surum}" (surum kaynak kaydindan)

Capa elle bicimlenmez: ayristirma ve bicimleme `mutalaa_pipeline.anchor` ile yapilir (kanonik
degilse hata). Kanonik metin (`text`) oldugu gibi tasinir; `content_hash` normalize
edilmemis metnin ozetidir (K-26). Onceki anchor calismasiyla karsilastirma bilgi icindir
(manifest, rapor, uyari); kapi karari `qa run` G-CAP'indedir ve G-CAP'in tabani hemen onceki
degil, dort kapiyi da gecmis son anchor calismasidir (`qa/run.py`).
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import accumulate
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import KAYNAK
from mutalaa_pipeline.anchor import AnchorError, Q, content_hash, parse
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, units_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    girdi_olarak,
    girdileri_ayni,
    onceki_calisma,
    saglam_olmali,
    son_calisma,
    units_oku,
)

# BASLANGIC[s - 1] = 1..s-1. surelerdeki ayet toplami; kuresel sira = BASLANGIC[s - 1] + ayet
BASLANGIC: Final = tuple(accumulate(AYET_SAYILARI, initial=0))
KIND: Final = "ayet"
METIN_DURUMU: Final = "onayli"
NORMALIZE_ALANLARI: Final = frozenset(
    {"anchor", "attrs", "ar_norm", "provenance", "source_id", "text"}
)
ORNEK_CAPA: Final = 5


@dataclass(frozen=True)
class AnchorSonucu:
    run_id: str
    atlandi: bool
    birim_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


@dataclass(frozen=True)
class Karsilastirma:
    """Onceki anchor calismasi ile bu calisma arasindaki capa farki."""

    onceki_run_id: str | None
    ortak: int
    eklenen: int
    kaldirilan: tuple[str, ...]  # onceki calismada olup simdi olmayan capalar (sirali)
    degisen: tuple[str, ...]  # ayni capada content_hash farkli olanlar (sirali)

    def ayrinti(self) -> dict[str, object]:
        return {
            "run_id": self.onceki_run_id,
            "ortak": self.ortak,
            "eklenen": self.eklenen,
            "kaldirilan": len(self.kaldirilan),
            "degisen_hash": len(self.degisen),
        }


def kuresel_sira(sure: int, ayet: int) -> int:
    """Ayetin 1..6236 araligindaki kuresel sirasi (`sure` ve `ayet` gecerli olmalidir)."""
    return BASLANGIC[sure - 1] + ayet


def ayet_coz(capa: str) -> tuple[int, int] | None:
    """Kanonik bir `q:{sure}:{ayet}` capasinin `(sure, ayet)` degeri; degilse None.

    Kelime, kelime araligi, ayet araligi ve `@` araligi ayet capasi sayilmaz; ayristirilip
    yeniden bicimlenen dizgi girdiyle ayni olmalidir. `@` araligi `q:` capasinda ayristiricinin
    kendisinde reddedilir (`parse` BICIM verir, K-35 madde 6); bu yuzden ayrica `span`
    denetlenmez. Davranis tests/test_anchor_tanzil.py::test_ayet_coz ile sabitlenmistir.
    """
    try:
        ref = parse(capa)
        kanonik = anchor_format(ref) == capa
    except (AnchorError, ValueError):
        return None
    cozulen = ref.anchor
    if not kanonik or not isinstance(cozulen, Q) or cozulen.ilk is not None:
        return None
    return cozulen.sure, cozulen.ayet


def anchor_satirlari(satirlar: Sequence[Satir], surum: str) -> list[dict[str, object]]:
    """Normalize satirlarina capa alanlarini ekler (satirlar degismez, kopyalanir)."""
    sonuc: list[dict[str, object]] = []
    for satir in satirlar:
        if set(satir.veri) != NORMALIZE_ALANLARI:
            raise GirdiHatasi(
                f"{satir.etiket}: satir {satir.no}: alan kumesi normalize cikisi degil"
            )
        if satir.metin("source_id") != KAYNAK:
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: source_id {KAYNAK} degil")
        konum = ayet_coz(satir.metin("anchor"))
        if konum is None:
            raise GirdiHatasi(
                f"{satir.etiket}: satir {satir.no}: capa kanonik bir ayet capasi degil"
            )
        satir.metin("ar_norm")  # normalize cikisinda zorunlu (tip denetimi)
        satir.nesne("provenance")
        sira = kuresel_sira(*konum)
        cikti = dict(satir.veri)
        cikti.update(
            kind=KIND,
            ord=sira,
            ayah_lo=sira,
            ayah_hi=sira + 1,
            content_hash=content_hash(satir.metin("text")),
            metin_durumu=METIN_DURUMU,
            data_version=f"{KAYNAK}@{surum}",
        )
        sonuc.append(cikti)
    return sonuc


def capa_ozetleri(satirlar: Sequence[Satir]) -> dict[str, str]:
    """`anchor -> content_hash` (anchor calismasi satirlarindan)."""
    return {s.metin("anchor"): s.metin("content_hash") for s in satirlar}


def onceki_ile_karsilastir(
    onceki: Mapping[str, str] | None, simdiki: Mapping[str, str], onceki_run_id: str | None
) -> Karsilastirma:
    """Capa kumelerini ve ortak capalardaki `content_hash` degerlerini karsilastirir."""
    if onceki is None:
        return Karsilastirma(None, 0, len(simdiki), (), ())
    ortak = [c for c in onceki if c in simdiki]
    return Karsilastirma(
        onceki_run_id=onceki_run_id,
        ortak=len(ortak),
        eklenen=len(simdiki) - len(ortak),
        kaldirilan=tuple(sorted(c for c in onceki if c not in simdiki)),
        degisen=tuple(sorted(c for c in ortak if onceki[c] != simdiki[c])),
    )


def _ord_araligi(satirlar: Sequence[Mapping[str, object]]) -> list[int]:
    siralar = [s["ord"] for s in satirlar if isinstance(s["ord"], int)]
    return [min(siralar), max(siralar)] if siralar else [0, 0]


def _onceki_ozetleri(ctx: RunContext, onceki: Calisma | None) -> dict[str, str] | None:
    """Onceki anchor calismasinin `anchor -> content_hash` haritasi (okunamazsa None + uyari)."""
    if onceki is None:
        return None
    try:
        return capa_ozetleri(units_oku(onceki, "onceki anchor units.jsonl"))
    except GirdiHatasi:
        ctx.uyar("onceki anchor calistirmasi okunamadi: karsilastirma yapilamadi")
        return None


def run_anchor(ctx: RunContext) -> AnchorSonucu:
    """Kaynak kaydi, son normalize, parmak izi, capa alanlari, `staged`, manifest (en son)."""
    kayit = ctx.require_sources(KAYNAK)[KAYNAK]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {KAYNAK}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "anchor_basla", source_id=KAYNAK)
    normalize = son_calisma(ctx, KAYNAK, NORMALIZE_ADIMI, ipucu="once: normalize --source")
    saglam_olmali(ctx, normalize)
    girdiler = [girdi_olarak(normalize)]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(KAYNAK), ctx.adim)
    # Parmak izi run_id icermez: cikti ayrica en son ust calismalara bagli olmali, yoksa
    # ust adim yeniden kosulmus (ornegin --force) ve zincir eski bir calismada kalir.
    if girdileri_ayni(onceki[2] if onceki else None, girdiler) and lineage.atlanabilir(
        onceki=onceki[2] if onceki else None,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "anchor_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return AnchorSonucu(
            run_id=ctx.run_id,
            atlandi=True,
            birim_sayisi=0,
            klasor=None,
            onceki_run_id=onceki[0] if onceki else None,
        )

    satirlar = anchor_satirlari(units_oku(normalize, "normalize units.jsonl"), kayit.surum)
    onceki_anchor = onceki_calisma(ctx, KAYNAK, ANCHOR_ADIMI)
    fark = onceki_ile_karsilastir(
        _onceki_ozetleri(ctx, onceki_anchor),
        {str(s["anchor"]): str(s["content_hash"]) for s in satirlar},
        onceki_anchor.run_id if onceki_anchor else None,
    )
    cikti = units_yaz(ctx, KAYNAK, satirlar)
    birim = cikti.satir or 0
    ctx.sayi("birim", birim)
    ctx.sayi("onceki_ortak", fark.ortak)
    ctx.sayi("onceki_eklenen", fark.eklenen)
    ctx.sayi("onceki_kaldirilan", len(fark.kaldirilan))
    ctx.sayi("onceki_degisen_hash", len(fark.degisen))
    # Bilgi amaclidir: onceki anchor calismasiyla karsilastirma. Kapi karari `qa run` G-CAP'indedir
    # ve tabani QA'dan gecmis son calismadir (hemen onceki calisma olmayabilir).
    if fark.kaldirilan:
        ctx.uyar(f"onceki anchor calistirmasindan {len(fark.kaldirilan)} capa kayip (kapi: G-CAP)")
    if fark.degisen:
        ctx.uyar(f"{len(fark.degisen)} capada content_hash degisti (kapi: G-CAP)")
    sayilar = {"birim": birim, "onceki_ortak": fark.ortak, "onceki_eklenen": fark.eklenen}
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "anchor_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=None)

    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "normalize_run": normalize.run_id,
            "data_version": f"{KAYNAK}@{kayit.surum}",
            "birim": birim,
            "ord_araligi": _ord_araligi(satirlar),
            "onceki": fark.ayrinti(),
        },
    )
    ctx.gunluk.yaz("INFO", "anchor_bitti", source_id=KAYNAK, sayilar=sayilar)
    return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`)."""
    desteklenen = source == KAYNAK

    def govde(ctx: RunContext) -> int:
        if not desteklenen:
            raise GirdiHatasi(f"anchor bu kaynak icin tanimli degil (yalniz {KAYNAK})")
        sonuc = run_anchor(ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"anchor {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"anchor --source {source}",
        adim=ANCHOR_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )
