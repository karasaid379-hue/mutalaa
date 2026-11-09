"""Fikstur normalize ve capa adimlari (A13.6): `test-kucuk` ve `test-tefsir-ornek`.

`mutalaa normalize --source <fikstur>`: son `ingest fikstur` calismasini okur ve her birime Turkce
arama anahtarlarini (`tr_narrow`, `tr_wide`, `tr_stem`; A05, K-36 `search_keys`) ekler. `ar_norm`
bos kalir (`null`): sentetik fikstur Arapca metin tasimaz. Kanonik metin (`text`) hicbir donusumden
gecmez (`kanonik_metin` ingest'te bir kez uygulanmistir).

`mutalaa anchor --source <fikstur>`: son normalize calismasina `export pg` icin gereken alanlari
ekler ve `units.jsonl` yazar:

    kind          "kitap" (test-kucuk) ya da "tefsir" (test-tefsir-ornek); ingest `attrs.kind`
    parent_path   kitapta bolum yolu (`attrs.parent_path`); tefsirde null
    role          "govde"
    ord           okuma sirasi 1..N (`sort_key` sirasiyla; kaynak icinde)
    ayah_lo/hi    tefsirde capadan turetilir: kuresel ayet sirasi, yari acik [lo, hi + 1);
                  kitapta ikisi de null
    content_hash  UTF-8 baytlarin SHA-256'si
    metin_durumu  "taslak": sentetik fikstur kanonik basvuru degildir (K-38 madde 4)
    data_version  "{slug}@{surum}" (surum kaynak kaydindan)

Capa elle bicimlenmez: ayristirma ve bicimleme `mutalaa_pipeline.anchor` ile yapilir. Onceki
calismayla capa karsilastirmasi `qa run` G-CAP'indedir.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.anchor_tanzil import AnchorSonucu, kuresel_sira
from mutalaa_pipeline.adimlar.normalize_tanzil import INGEST_ALANLARI, NormalizeSonucu
from mutalaa_pipeline.anchor import AnchorError, K, Tf, content_hash, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.fikstur import KAYNAKLAR, KIND, TEFSIR_ESER, URETEC_SURUMU
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, search_keys
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, units_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
    units_oku,
)

METIN_DURUMU: Final = "taslak"
ROL: Final = "govde"
TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")
NORMALIZE_ALANLARI: Final = INGEST_ALANLARI | {"ar_norm", *TR_ALANLARI}
# Capa onekleri: her fikstur yalniz kendi capa ailesini tasir.
CAPA_AILESI: Final = {"test-kucuk": ("k", "test-kucuk"), "test-tefsir-ornek": ("tf", TEFSIR_ESER)}


def kaynak_denetle(source: str) -> None:
    if source not in KAYNAKLAR:
        raise GirdiHatasi(f"bu adim fikstur kaynaklari icindir: {', '.join(KAYNAKLAR)}")


def capa_ailesine_uyar(slug: str, capa: str) -> bool:
    """Capa kanonik mi ve kaynagin kendi ailesinden mi (kitapta `test-kucuk`, tefsirde eser)."""
    try:
        ref = parse(capa)
        kanonik = anchor_format(ref) == capa
    except AnchorError:
        return False
    cozulen = ref.anchor
    if not kanonik or ref.span is not None:
        return False
    if slug == "test-kucuk":
        return isinstance(cozulen, K) and cozulen.yol[0] == CAPA_AILESI[slug][1]
    return isinstance(cozulen, Tf) and cozulen.eser == CAPA_AILESI[slug][1]


def ayet_araligi(capa: str) -> tuple[int, int] | None:
    """Tefsir capasinin yari acik kuresel ayet araligi `[lo, hi)`; tefsir degilse None."""
    cozulen = parse(capa).anchor
    if not isinstance(cozulen, Tf):
        return None
    return (
        kuresel_sira(cozulen.sure, cozulen.ilk),
        kuresel_sira(cozulen.sure, cozulen.son) + 1,
    )


# --- normalize ---------------------------------------------------------------------------


def normalize_satirlari(slug: str, satirlar: Sequence[Satir]) -> list[dict[str, object]]:
    """Ingest satirlarina arama anahtarlarini ekler (satirlar degismez, kopyalanir)."""
    sonuc: list[dict[str, object]] = []
    for satir in satirlar:
        if set(satir.veri) != INGEST_ALANLARI:
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: alan kumesi ingest cikisi degil")
        if satir.metin("source_id") != slug:
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: source_id {slug} degil")
        if not capa_ailesine_uyar(slug, satir.metin("anchor")):
            raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: capa bu fikstura ait degil")
        anahtarlar = search_keys(satir.metin("text"))
        cikti = dict(satir.veri)
        cikti.update(
            ar_norm=None,
            tr_narrow=anahtarlar.tr_narrow,
            tr_wide=anahtarlar.tr_wide,
            tr_stem=anahtarlar.tr_stem,
        )
        kok = dict(satir.nesne("provenance"))
        kok["arama"] = {"normalizer_version": NORMALIZER_VERSION}
        cikti["provenance"] = kok
        sonuc.append(cikti)
    return sonuc


def run_normalize(ctx: RunContext, slug: str) -> NormalizeSonucu:
    """Kaynak kaydi, son ingest, parmak izi, arama anahtarlari, `staged`, manifest (en son)."""
    ctx.require_sources(slug)  # kayitsiz ya da gecersiz kayitta cikis 2
    ctx.gunluk.yaz("INFO", "normalize_basla", source_id=slug)
    ingest = son_calisma(ctx, slug, INGEST_ADIMI, ipucu=f"once: ingest fikstur --source {slug}")
    saglam_olmali(ctx, ingest)
    girdiler = [girdi_olarak(ingest)]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(slug), ctx.adim)
    onceki_manifest = onceki[2] if onceki else None
    if girdileri_ayni(onceki_manifest, girdiler) and lineage.atlanabilir(
        onceki=onceki_manifest,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "normalize_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return NormalizeSonucu(
            run_id=ctx.run_id,
            atlandi=True,
            birim_sayisi=0,
            klasor=None,
            onceki_run_id=onceki[0] if onceki else None,
        )

    satirlar = normalize_satirlari(slug, units_oku(ingest, f"ingest {slug} units.jsonl"))
    cikti = units_yaz(ctx, slug, satirlar)
    birim = cikti.satir or 0
    ctx.sayi("birim", birim)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "normalize_dry_run", source_id=slug, sayilar={"birim": birim})
        return NormalizeSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=None)

    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar={
            "kaynak": slug,
            "ingest": {slug: ingest.run_id},
            "normalizer_version": NORMALIZER_VERSION,
            "uretec_surumu": URETEC_SURUMU,
            "birim": birim,
        },
    )
    ctx.gunluk.yaz("INFO", "normalize_bitti", source_id=slug, sayilar={"birim": birim})
    return NormalizeSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def komut_normalize(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`normalize --source <fikstur>` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_normalize(ctx, source)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"normalize {source}: {ozet}\n")
        return cikis.BASARILI

    return komutu_yurut(
        komut=f"normalize --source {source}",
        adim=NORMALIZE_ADIMI,
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler={"source": source},
    )


# --- anchor ------------------------------------------------------------------------------


def anchor_satirlari(slug: str, satirlar: Sequence[Satir], surum: str) -> list[dict[str, object]]:
    """Normalize satirlarina capa alanlarini ekler; `ord` `sort_key` sirasidir."""
    hazir: list[tuple[Satir, dict[str, object]]] = []
    for satir in satirlar:
        yer = f"{satir.etiket}: satir {satir.no}"
        if set(satir.veri) != NORMALIZE_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi normalize cikisi degil")
        if satir.metin("source_id") != slug:
            raise GirdiHatasi(f"{yer}: source_id {slug} degil")
        capa = satir.metin("anchor")
        if not capa_ailesine_uyar(slug, capa):
            raise GirdiHatasi(f"{yer}: capa bu fikstura ait degil")
        attrs = dict(satir.nesne("attrs"))
        kind = attrs.pop("kind", None)
        yol = attrs.pop("parent_path", None)
        if kind != KIND[slug]:
            raise GirdiHatasi(f"{yer}: attrs.kind {KIND[slug]} degil")
        if yol is not None and not isinstance(yol, str):
            raise GirdiHatasi(f"{yer}: attrs.parent_path metin degil")
        aralik = ayet_araligi(capa)
        metin = satir.metin("text")
        cikti = dict(satir.veri)
        cikti.update(
            kind=kind,
            parent_path=yol,
            role=ROL,
            attrs=attrs,
            ayah_lo=aralik[0] if aralik else None,
            ayah_hi=aralik[1] if aralik else None,
            content_hash=content_hash(metin),
            metin_durumu=METIN_DURUMU,
            data_version=f"{slug}@{surum}",
        )
        hazir.append((satir, cikti))
    hazir.sort(key=lambda cift: sort_key(parse(str(cift[1]["anchor"]))))
    sonuc: list[dict[str, object]] = []
    for sira, (_, cikti) in enumerate(hazir, start=1):
        cikti["ord"] = sira
        sonuc.append(cikti)
    return sonuc


def run_anchor(ctx: RunContext, slug: str) -> AnchorSonucu:
    """Kaynak kaydi, son normalize, parmak izi, capa alanlari, `staged`, manifest (en son)."""
    kayit = ctx.require_sources(slug)[slug]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {slug}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "anchor_basla", source_id=slug)
    normalize = son_calisma(ctx, slug, NORMALIZE_ADIMI, ipucu=f"once: normalize --source {slug}")
    saglam_olmali(ctx, normalize)
    girdiler = [girdi_olarak(normalize)]
    parmak = ctx.parmak_izi(girdiler)

    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(slug), ctx.adim)
    onceki_manifest = onceki[2] if onceki else None
    if girdileri_ayni(onceki_manifest, girdiler) and lineage.atlanabilir(
        onceki=onceki_manifest,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    ):
        ctx.gunluk.yaz("INFO", "anchor_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return AnchorSonucu(
            run_id=ctx.run_id,
            atlandi=True,
            birim_sayisi=0,
            klasor=None,
            onceki_run_id=onceki[0] if onceki else None,
        )

    satirlar = anchor_satirlari(
        slug, units_oku(normalize, f"normalize {slug} units.jsonl"), kayit.surum
    )
    cikti = units_yaz(ctx, slug, satirlar)
    birim = cikti.satir or 0
    ctx.sayi("birim", birim)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "anchor_dry_run", source_id=slug, sayilar={"birim": birim})
        return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=None)

    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar=_ayrintilar(slug, kayit.surum, normalize.run_id, birim),
    )
    ctx.gunluk.yaz("INFO", "anchor_bitti", source_id=slug, sayilar={"birim": birim})
    return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def _ayrintilar(slug: str, surum: str, normalize_run: str, birim: int) -> Mapping[str, object]:
    return {
        "kaynak": slug,
        "normalize_run": normalize_run,
        "data_version": f"{slug}@{surum}",
        "birim": birim,
        "ord_araligi": [1, birim],
    }


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source <fikstur>` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_anchor(ctx, source)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"anchor {source}: {ozet}\n")
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
