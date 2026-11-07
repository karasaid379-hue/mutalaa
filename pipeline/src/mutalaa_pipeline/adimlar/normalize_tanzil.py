"""Tanzil normalize adimi (A10.4): `ar_norm` ve AR-4 (K-39 madde 1 ve 5).

`mutalaa normalize --source tanzil-uthmani`: iki ingest calismasini (Uthmani ve Simple Clean)
okur, her ayetin `ar_norm` degerini uretir ve `staged/tanzil-uthmani/{run_id}/units.jsonl`
olarak yazar. Kanonik metin (`text`) hicbir donusumden gecmez; `ar_norm` ayri bir alandir
(K-26). Kur'an birimlerinde `tr_*` alanlari yoktur (bos kalir).

AR-4: `ar_norm = normalize_ar(simple_clean)`; ardina ayni ayetin `normalize_ar(uthmani)`
sozcuklerinden Simple Clean sozcuk kumesinde olmayanlar, Uthmani'deki ilk gorulme sirasiyla,
tekrarsiz, tek bosluklarla eklenir. Normallestirici islevi ve `NORMALIZER_VERSION` degismez;
kural hattin Kur'an `ar_norm` bilesimidir.

Baglilik makinenin okuyacagi yerde tutulur (K-39 madde 1): her satirin
`provenance.ar_norm = {kaynak, sha256, line, normalizer_version, ar4}` alani Simple Clean ham
dosyasinin ozetini ve satir numarasini tasir. Hata iletileri icerik tasimaz (yalniz capa, satir
numarasi, sayi ve alan adi).
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar
from mutalaa_pipeline.normalize.unicode import BOSLUK
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, units_yaz
from mutalaa_pipeline.zincir import (
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
    units_oku,
)

KAYNAK: Final = "tanzil-uthmani"  # q: birimlerinin kaynagi (kanonik metin)
EK_KAYNAK: Final = "tanzil-simple-clean"  # yalniz ar_norm kaynagi (K-39 madde 1)
INGEST_ALANLARI: Final = frozenset({"anchor", "attrs", "provenance", "source_id", "text"})
ORNEK_CAPA: Final = 5


@dataclass(frozen=True)
class NormalizeSonucu:
    run_id: str
    atlandi: bool
    birim_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None


def sozcuklere_ayir(ar_norm: str) -> list[str]:
    """`normalize_ar` ciktisinin sozcukleri (tek U+0020 ile ayrilmistir; bos metin: bos liste)."""
    return ar_norm.split(BOSLUK) if ar_norm else []


def ar4_birlestir(simple_norm: str, uthmani_norm: str) -> tuple[str, int]:
    """AR-4: `(ar_norm, eklenen sozcuk sayisi)`; girdiler `normalize_ar` ciktilaridir.

    Ek sozcukler Uthmani'de ilk gorulme sirasindadir ve tekrarsizdir; Simple Clean'in
    sozcuk kumesindekiler eklenmez. Simple Clean tarafi aynen korunur (tekrarlari dahil).
    """
    bilinen = set(sozcuklere_ayir(simple_norm))
    ekler: list[str] = []
    for sozcuk in sozcuklere_ayir(uthmani_norm):
        if sozcuk not in bilinen:
            bilinen.add(sozcuk)
            ekler.append(sozcuk)
    if not ekler:
        return simple_norm, 0
    ek_metin = BOSLUK.join(ekler)
    return (simple_norm + BOSLUK + ek_metin if simple_norm else ek_metin), len(ekler)


def ar_norm_uret(simple_clean: str, uthmani: str) -> str:
    """Bir ayetin `ar_norm` degeri: Simple Clean ve Uthmani ayet metinlerinden (AR-4)."""
    return ar4_birlestir(normalize_ar(simple_clean), normalize_ar(uthmani))[0]


def ar_norm_kaydi(simple: Satir) -> dict[str, object]:
    """`provenance.ar_norm` alani: baglilik Simple Clean ham dosyasindadir (K-39 madde 1)."""
    kok = simple.nesne("provenance")
    ozet, satir = kok.get("sha256"), kok.get("line")
    if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi(f"{simple.etiket}: satir {simple.no}: provenance.sha256 gecersiz")
    if not isinstance(satir, int) or isinstance(satir, bool) or satir < 1:
        raise GirdiHatasi(f"{simple.etiket}: satir {simple.no}: provenance.line gecersiz")
    return {
        "kaynak": EK_KAYNAK,
        "sha256": ozet,
        "line": satir,
        "normalizer_version": NORMALIZER_VERSION,
        "ar4": True,
    }


def _ingest_satirlari(calisma: Calisma, kaynak: str) -> dict[str, Satir]:
    """Ingest satirlari capaya gore; alan kumesi ve `source_id` kati denetlenir."""
    etiket = f"ingest {kaynak} units.jsonl"
    harita: dict[str, Satir] = {}
    for satir in units_oku(calisma, etiket):
        if set(satir.veri) != INGEST_ALANLARI:
            raise GirdiHatasi(f"{etiket}: satir {satir.no}: alan kumesi ingest cikisi degil")
        if satir.metin("source_id") != kaynak:
            raise GirdiHatasi(f"{etiket}: satir {satir.no}: source_id {kaynak} degil")
        satir.metin("text")
        satir.nesne("provenance")
        capa = satir.metin("anchor")
        if capa in harita:
            raise GirdiHatasi(f"{etiket}: yinelenen capa: {capa}")
        harita[capa] = satir
    return harita


def _capa_ornekleri(capalar: set[str]) -> str:
    return ", ".join(sorted(capalar)[:ORNEK_CAPA])


def normalize_satirlari(
    uthmani: dict[str, Satir], simple: dict[str, Satir]
) -> tuple[list[dict[str, object]], int, int]:
    """Uthmani satirlarina `ar_norm` ve `provenance.ar_norm` ekler.

    Donus: `(satirlar, ek sozcuklu ayet sayisi, toplam ek sozcuk sayisi)`. Iki ingest
    calismasinin capa kumeleri ayni olmalidir; aksi halde `GirdiHatasi`.
    """
    yalniz_uthmani = set(uthmani) - set(simple)
    yalniz_simple = set(simple) - set(uthmani)
    if yalniz_uthmani or yalniz_simple:
        raise GirdiHatasi(
            "iki ingest calismasinin capa kumeleri ayni degil:"
            f" yalniz uthmani {len(yalniz_uthmani)} ({_capa_ornekleri(yalniz_uthmani)}),"
            f" yalniz simple-clean {len(yalniz_simple)} ({_capa_ornekleri(yalniz_simple)})"
        )
    satirlar: list[dict[str, object]] = []
    ek_ayet = ek_sozcuk = 0
    for capa in uthmani:
        u, s = uthmani[capa], simple[capa]
        ar_norm, eklenen = ar4_birlestir(
            normalize_ar(s.metin("text")), normalize_ar(u.metin("text"))
        )
        cikti = dict(u.veri)
        cikti["ar_norm"] = ar_norm
        kok = dict(u.nesne("provenance"))
        kok["ar_norm"] = ar_norm_kaydi(s)
        cikti["provenance"] = kok
        satirlar.append(cikti)
        if eklenen:
            ek_ayet += 1
            ek_sozcuk += eklenen
    return satirlar, ek_ayet, ek_sozcuk


def run_normalize(ctx: RunContext) -> NormalizeSonucu:
    """Kaynak kayitlari, son iki ingest, parmak izi, `ar_norm`, `staged`, manifest (en son)."""
    ctx.require_sources((KAYNAK, EK_KAYNAK))  # kayitsiz ya da gecersiz kayitta cikis 2
    ctx.gunluk.yaz("INFO", "normalize_basla", source_id=KAYNAK)
    uthmani = son_calisma(ctx, KAYNAK, INGEST_ADIMI, ipucu="once: ingest tanzil --variant uthmani")
    simple = son_calisma(
        ctx, EK_KAYNAK, INGEST_ADIMI, ipucu="once: ingest tanzil --variant simple-clean"
    )
    saglam_olmali(ctx, uthmani)
    saglam_olmali(ctx, simple)
    girdiler = [girdi_olarak(uthmani), girdi_olarak(simple)]
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
        ctx.gunluk.yaz("INFO", "normalize_atlandi", source_id=KAYNAK)
        ctx.sayi("atlandi", 1)
        return NormalizeSonucu(
            run_id=ctx.run_id,
            atlandi=True,
            birim_sayisi=0,
            klasor=None,
            onceki_run_id=onceki[0] if onceki else None,
        )

    satirlar, ek_ayet, ek_sozcuk = normalize_satirlari(
        _ingest_satirlari(uthmani, KAYNAK), _ingest_satirlari(simple, EK_KAYNAK)
    )
    cikti = units_yaz(ctx, KAYNAK, satirlar)
    birim = cikti.satir or 0
    ctx.sayi("birim", birim)
    ctx.sayi("ar4_ek_ayet", ek_ayet)
    ctx.sayi("ar4_ek_sozcuk", ek_sozcuk)
    sayilar = {"birim": birim, "ar4_ek_ayet": ek_ayet, "ar4_ek_sozcuk": ek_sozcuk}
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "normalize_dry_run", source_id=KAYNAK, sayilar=sayilar)
        return NormalizeSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=None)

    klasor = ctx.staged_dizin(KAYNAK)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": KAYNAK,
            "ek_kaynak": EK_KAYNAK,
            "ingest": {KAYNAK: uthmani.run_id, EK_KAYNAK: simple.run_id},
            "normalizer_version": NORMALIZER_VERSION,
            "ar4": True,
            "birim": birim,
            "ar4_ek_ayet": ek_ayet,
            "ar4_ek_sozcuk": ek_sozcuk,
        },
    )
    ctx.gunluk.yaz("INFO", "normalize_bitti", source_id=KAYNAK, sayilar=sayilar)
    return NormalizeSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def komut_normalize(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`normalize --source` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`)."""
    desteklenen = source == KAYNAK

    def govde(ctx: RunContext) -> int:
        if not desteklenen:
            raise GirdiHatasi(f"normalize bu kaynak icin tanimli degil (yalniz {KAYNAK})")
        sonuc = run_normalize(ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"normalize {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"normalize --source {source}",
        adim=NORMALIZE_ADIMI,
        kaynaklar=[KAYNAK, EK_KAYNAK] if desteklenen else [source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )
