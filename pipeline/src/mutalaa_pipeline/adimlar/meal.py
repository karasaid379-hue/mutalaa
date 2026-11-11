"""Meal normalize ve capa adimlari (A16.3): `elmalili-meal` ve `elmalili-sade-meal`.

Iki meal ayni kodla kosar; kaynak kimligi parametredir (`ingest/meal_kaynaklari.py`; sablon:
`adimlar/fikstur.py`). Tanik kaynagi (`elmalili-meal-epub`) bu adimlara girmez.

`mutalaa normalize --source <meal>`: son `ingest meal` calismasini okur ve her birime Turkce arama
anahtarlarini (`tr_narrow`, `tr_wide`, `tr_stem`; K-36 `search_keys`) ekler. `ar_norm` bos
kalir (`null`): meal Arapca metin tasimaz. Kanonik metin (`text`) hicbir donusumden gecmez
(`kanonik_metin` ingest'te bir kez uygulanmistir; K-49 madde 7).

`mutalaa anchor --source <meal>`: son normalize calismasina `export pg` icin gereken alanlari ekler:

    kind          "meal"
    role          "govde"
    ord           kuresel ayet sirasi 1..6236 (okuma sirasiyla ayni; izleyen birimler dahil)
    ayah_lo/hi    yari acik kuresel aralik [lo, hi + 1): tek ayet; birlesik bas birimde
                  `attrs.kapsam` araligi (K-49 madde 8: "ayah_range kapsami orter")
    content_hash  UTF-8 baytlarin SHA-256'si (birlesik izleyen birimde bos metnin ozeti)
    metin_durumu  "taslak" (K-49 madde 4)
    data_version  "{slug}@{surum}" (surum kaynak kaydindan)
    tanik         null ya da `{skor, kapsam, yontem, yontem_surumu, kaynak}` (asagida)

Tanik skoru (yalniz `elmalili-meal`; girdi: `elmalili-meal-epub` staged `tanik.jsonl`): her tanik
parcasi icin, parcanin kapsadigi ayetlerin `tr_narrow` metinleri tek U+0020 ile birlestirilir ve
tanigin `tr_narrow` metniyle `rapidfuzz.fuzz.ratio` (`processor=None`, 0..100) hesaplanir; sonuc en
yakin tam sayiya yuvarlanir (staged JSON'da ondalik sayi yoktur) ve kapsanan her ayete yazilir.
Numara boslugu olan yerde parca birden fazla ayeti kapsar (`kapsam = [lo, hi]`). Skor, iki ayri
derlemenin metin yakinligidir; ozgun baskiya sadakat degildir ve ortak kokenden etkilenebilir
(K-49). Yontem degisirse `TANIK_YONTEM_SURUMU` artar.

Capa elle bicimlenmez: ayristirma ve bicimleme `mutalaa_pipeline.anchor` ile yapilir. Onceki
calismayla capa karsilastirmasi `qa run` G-CAP'indedir.
"""

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

from rapidfuzz import fuzz

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.anchor_tanzil import AnchorSonucu, kuresel_sira
from mutalaa_pipeline.adimlar.normalize_tanzil import INGEST_ALANLARI, NormalizeSonucu
from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Meal, Qa, content_hash, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_kaynaklari as kayitlar
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.lineage import TANIK_ADI
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, search_keys
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, units_yaz
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    dosya_oku,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
    units_oku,
)

KIND: Final = kayitlar.KIND
ROL: Final = kayitlar.ROL_METIN
METIN_DURUMU: Final = kayitlar.METIN_DURUMU
TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")
NORMALIZE_ALANLARI: Final = INGEST_ALANLARI | {"ar_norm", *TR_ALANLARI}
ANCHOR_ALANLARI: Final = (
    NORMALIZE_ALANLARI
    | {"kind", "role", "ord", "ayah_lo", "ayah_hi", "content_hash", "metin_durumu"}
    | {"data_version", "tanik"}
)
ATTRS_ANAHTARLARI: Final = frozenset({"kapsam", "birlesik_ile", "besmele_meali"})
TANIK_YONTEMI: Final = "rapidfuzz.fuzz.ratio/tr_narrow"
TANIK_YONTEM_SURUMU: Final = "1"
TOPLAM_AYET: Final = sum(AYET_SAYILARI)


def kaynak_denetle(source: str) -> None:
    if not kayitlar.meal_mi(source):
        raise GirdiHatasi(f"bu adim meal kaynaklari icindir: {', '.join(kayitlar.MEAL_KAYNAKLARI)}")


def meal_capasi(slug: str, capa: str) -> tuple[int, int] | None:
    """Kanonik `meal:{eser}:{sure}:{ayet}` capasinin `(sure, ayet)` degeri; degilse None.

    Capa kaynagin KENDI eserinden olmali (`elmalili` ve `elmalili-sade` birbirinin yerine gecmez;
    K-26). Aralik (`@`) kabul edilmez. Sure ve ayet Tanzil sayilarinin icinde olmali.
    """
    try:
        ref = parse(capa)
        kanonik = anchor_format(ref) == capa
    except AnchorError:
        return None
    cozulen = ref.anchor
    if (
        not kanonik
        or ref.span is not None
        or not isinstance(cozulen, Meal)
        or cozulen.meal != kayitlar.capa_eseri(slug)
        or not 1 <= cozulen.sure <= 114
        or not 1 <= cozulen.ayet <= AYET_SAYILARI[cozulen.sure - 1]
    ):
        return None
    return cozulen.sure, cozulen.ayet


def kapsam_coz(sure: int, ayet: int, kapsam: object) -> tuple[int, int] | None:
    """`attrs.kapsam` (`q:{s}:{ilk}-{son}`) -> `(ilk, son)`; yok ya da gecersizse None.

    Kapsam ayni surede olmali ve bu ayetle baslamali (bas birim).
    """
    if not isinstance(kapsam, str):
        return None
    try:
        ref = parse(kapsam)
    except AnchorError:
        return None
    k = ref.anchor
    if (
        anchor_format(ref) != kapsam
        or not isinstance(k, Qa)
        or (k.sure, k.ilk) != (sure, ayet)
        or k.son > AYET_SAYILARI[sure - 1]
    ):
        return None
    return k.ilk, k.son


def ayet_araligi(sure: int, ayet: int, attrs: Mapping[str, object]) -> tuple[int, int]:
    """Yari acik kuresel aralik `[lo, hi)`; birlesik bas birimde kapsami orter."""
    if "kapsam" in attrs:
        k = kapsam_coz(sure, ayet, attrs["kapsam"])
        if k is None:
            raise GirdiHatasi("attrs.kapsam gecersiz")
        return kuresel_sira(sure, k[0]), kuresel_sira(sure, k[1]) + 1
    sira = kuresel_sira(sure, ayet)
    return sira, sira + 1


# --- normalize ---------------------------------------------------------------------------


def normalize_satirlari(slug: str, satirlar: Sequence[Satir]) -> list[dict[str, object]]:
    """Ingest satirlarina arama anahtarlarini ekler (satirlar degismez, kopyalanir)."""
    sonuc: list[dict[str, object]] = []
    for satir in satirlar:
        yer = f"ingest {slug} units.jsonl: satir {satir.no}"
        if set(satir.veri) != INGEST_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi ingest cikisi degil")
        if satir.metin("source_id") != slug:
            raise GirdiHatasi(f"{yer}: source_id {slug} degil")
        if meal_capasi(slug, satir.metin("anchor")) is None:
            raise GirdiHatasi(f"{yer}: capa bu mealin capa ailesine ait degil")
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


def _ingest_ipucu(slug: str) -> str:
    return f"once: ingest meal --source {slug}"


def run_normalize(ctx: RunContext, slug: str) -> NormalizeSonucu:
    """Kaynak kaydi, son ingest, parmak izi, arama anahtarlari, `staged`, manifest (en son)."""
    ctx.require_sources(slug)  # kayitsiz ya da gecersiz kayitta cikis 2
    ctx.gunluk.yaz("INFO", "normalize_basla", source_id=slug)
    ingest = son_calisma(ctx, slug, INGEST_ADIMI, ipucu=_ingest_ipucu(slug))
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
            "birim": birim,
        },
    )
    ctx.gunluk.yaz("INFO", "normalize_bitti", source_id=slug, sayilar={"birim": birim})
    return NormalizeSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def komut_normalize(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`normalize --source <meal>` komutu; cikis kodunu dondurur."""

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


# --- tanik skoru -------------------------------------------------------------------------


def tanik_skoru(birim_metni: str, tanik_metni: str) -> int:
    """`tr_narrow` metinleri arasinda `rapidfuzz.fuzz.ratio` (0..100), en yakin tam sayi.

    `processor=None` acik verilir (varsayilan sozcuk on isleme kullanilmaz). Iki metin de bos
    ise 100, yalniz biri bos ise 0.
    """
    if birim_metni == "" and tanik_metni == "":
        return 100
    return int(fuzz.ratio(birim_metni, tanik_metni, processor=None) + 0.5)


def tanik_satirlari(calisma: Calisma, etiket: str) -> list[Satir]:
    """Tanik ingest calismasinin `tanik.jsonl` satirlari (manifest ozetiyle dogrulanarak)."""
    return dosya_oku(calisma, TANIK_ADI, etiket)


def _birlestir(araliklar: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Ayet araliklarini ortak ayet paylasanlari birlestirerek (ayrik) araliklara indirger."""
    sonuc: list[tuple[int, int]] = []
    for lo, hi in sorted(araliklar):
        if sonuc and lo <= sonuc[-1][1]:
            sonuc[-1] = (sonuc[-1][0], max(sonuc[-1][1], hi))
        else:
            sonuc.append((lo, hi))
    return sonuc


def tanik_hesapla(
    slug: str,
    satirlar: Sequence[Mapping[str, object]],
    tanik: Sequence[Satir],
) -> dict[str, dict[str, object]]:
    """`capa -> tanik nesnesi`; tanik parcasi olmayan ayet sonuca girmez.

    `satirlar`: `tr_narrow`, `attrs` ve `anchor` alanli normalize satirlari. Karsilastirma
    birimi, ortak ayet paylasan tanik parcalarinin ve birlesik meal kapsamlarinin birlesimidir:
    bir ayet (ornegin birlesik izleyen birim) kendi bos metniyle degil, ait oldugu kumenin
    butun metniyle ve tanigin ayni kumeyi kapsayan parcalariyla karsilastirilir.
    """
    eser = kayitlar.capa_eseri(slug)
    narrow: dict[tuple[int, int], str] = {}
    kapsamlar: dict[int, list[tuple[int, int]]] = {}
    for s in satirlar:
        cozulen = meal_capasi(slug, str(s["anchor"]))
        if cozulen is None:
            continue
        narrow[cozulen] = str(s["tr_narrow"])
        attrs = s.get("attrs")
        if isinstance(attrs, dict) and "kapsam" in attrs:
            k = kapsam_coz(cozulen[0], cozulen[1], attrs["kapsam"])
            if k is not None:
                kapsamlar.setdefault(cozulen[0], []).append(k)
    parcalar: dict[int, list[tuple[int, int, str]]] = {}
    for t in tanik:
        yer = f"tanik {slug}: satir {t.no}"
        sure = t.sayi("sure")
        kapsam = t.veri.get("kapsam")
        if (
            not isinstance(kapsam, list)
            or len(kapsam) != 2
            or not all(type(k) is int for k in kapsam)
            or not 1 <= sure <= 114
        ):
            raise GirdiHatasi(f"{yer}: sure ya da kapsam gecersiz")
        lo, hi = int(kapsam[0]), int(kapsam[1])
        if not 1 <= lo <= hi <= AYET_SAYILARI[sure - 1]:
            raise GirdiHatasi(f"{yer}: kapsam sure ayet sayisinin disinda")
        parcalar.setdefault(sure, []).append((lo, hi, search_keys(t.metin("metin")).tr_narrow))
    sonuc: dict[str, dict[str, object]] = {}
    for sure, liste in parcalar.items():
        araliklar = [(lo, hi) for lo, hi, _ in liste] + kapsamlar.get(sure, [])
        for lo, hi in _birlestir(araliklar):
            tanik_metni = " ".join(
                m for plo, phi, m in sorted(liste) if lo <= plo and phi <= hi and m != ""
            )
            if not any(lo <= plo and phi <= hi for plo, phi, _ in liste):
                continue  # kumeyi kapsayan tanik parcasi yok
            birim_metni = " ".join(
                m for a in range(lo, hi + 1) if (m := narrow.get((sure, a), "")) != ""
            )
            nesne: dict[str, object] = {
                "skor": tanik_skoru(birim_metni, tanik_metni),
                "kapsam": [lo, hi] if lo < hi else None,
                "yontem": TANIK_YONTEMI,
                "yontem_surumu": TANIK_YONTEM_SURUMU,
                "kaynak": kayitlar.kaynak(slug).tanik,
            }
            for a in range(lo, hi + 1):
                sonuc[anchor_format_meal(eser, sure, a)] = dict(nesne)
    return sonuc


def anchor_format_meal(eser: str, sure: int, ayet: int) -> str:
    return anchor_format(AnchorRef(Meal(eser, sure, ayet)))


# --- anchor ------------------------------------------------------------------------------


def anchor_satirlari(
    slug: str,
    satirlar: Sequence[Satir],
    surum: str,
    tanik: Mapping[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    """Normalize satirlarina capa alanlarini ekler; `ord` kuresel ayet sirasidir."""
    hazir: list[dict[str, object]] = []
    for satir in satirlar:
        yer = f"normalize {slug} units.jsonl: satir {satir.no}"
        if set(satir.veri) != NORMALIZE_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi normalize cikisi degil")
        if satir.metin("source_id") != slug:
            raise GirdiHatasi(f"{yer}: source_id {slug} degil")
        capa = satir.metin("anchor")
        cozulen = meal_capasi(slug, capa)
        if cozulen is None:
            raise GirdiHatasi(f"{yer}: capa bu mealin capa ailesine ait degil")
        sure, ayet = cozulen
        attrs = dict(satir.nesne("attrs"))
        if not set(attrs) <= ATTRS_ANAHTARLARI:
            raise GirdiHatasi(f"{yer}: attrs bilinmeyen anahtar tasiyor")
        lo, hi = ayet_araligi(sure, ayet, attrs)
        metin = satir.metin("text")
        cikti = dict(satir.veri)
        cikti.update(
            kind=KIND,
            role=ROL,
            ord=kuresel_sira(sure, ayet),
            ayah_lo=lo,
            ayah_hi=hi,
            content_hash=content_hash(metin),
            metin_durumu=METIN_DURUMU,
            data_version=f"{slug}@{surum}",
            tanik=tanik.get(capa) if tanik is not None else None,
        )
        hazir.append(cikti)
    hazir.sort(key=lambda s: sort_key(parse(str(s["anchor"]))))
    return hazir


def _tanik_calismasi(ctx: RunContext, slug: str) -> Calisma | None:
    tanik = kayitlar.kaynak(slug).tanik
    if tanik is None:
        return None
    ctx.require_sources(tanik)  # tanik kaydi da gecerli olmali
    calisma = son_calisma(ctx, tanik, INGEST_ADIMI, ipucu=_ingest_ipucu(tanik))
    saglam_olmali(ctx, calisma)
    return calisma


def run_anchor(ctx: RunContext, slug: str) -> AnchorSonucu:
    """Kaynak kaydi, son normalize (+ tanik), parmak izi, capa alanlari, `staged`, manifest."""
    kayit = ctx.require_sources(slug)[slug]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {slug}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "anchor_basla", source_id=slug)
    normalize = son_calisma(ctx, slug, NORMALIZE_ADIMI, ipucu=f"once: normalize --source {slug}")
    saglam_olmali(ctx, normalize)
    tanik_calismasi = _tanik_calismasi(ctx, slug)
    girdiler = [girdi_olarak(normalize)]
    if tanik_calismasi is not None:
        girdiler.append(girdi_olarak(tanik_calismasi, TANIK_ADI))
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

    norm_satirlari = units_oku(normalize, f"normalize {slug} units.jsonl")
    tanik: dict[str, dict[str, object]] | None = None
    if tanik_calismasi is not None:
        tanik = tanik_hesapla(
            slug,
            [s.veri for s in norm_satirlari],
            tanik_satirlari(tanik_calismasi, f"tanik {tanik_calismasi.source_id} tanik.jsonl"),
        )
    satirlar = anchor_satirlari(slug, norm_satirlari, kayit.surum, tanik)
    cikti = units_yaz(ctx, slug, satirlar)
    birim = cikti.satir or 0
    ctx.sayi("birim", birim)
    if tanik is not None:
        ctx.sayi("tanikli", len(tanik))
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "anchor_dry_run", source_id=slug, sayilar={"birim": birim})
        return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=None)

    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti],
        parmak=parmak,
        ayrintilar=_ayrintilar(slug, kayit.surum, normalize.run_id, birim, tanik),
    )
    ctx.gunluk.yaz("INFO", "anchor_bitti", source_id=slug, sayilar={"birim": birim})
    return AnchorSonucu(run_id=ctx.run_id, atlandi=False, birim_sayisi=birim, klasor=klasor)


def _ayrintilar(
    slug: str,
    surum: str,
    normalize_run: str,
    birim: int,
    tanik: Mapping[str, dict[str, object]] | None,
) -> Mapping[str, object]:
    ayrinti: dict[str, object] = {
        "kaynak": slug,
        "normalize_run": normalize_run,
        "data_version": f"{slug}@{surum}",
        "birim": birim,
        "ord_araligi": [1, TOPLAM_AYET],
    }
    if tanik is not None:
        skorlar = [int(str(v["skor"])) for v in tanik.values()]
        ayrinti["tanik"] = {
            "yontem": TANIK_YONTEMI,
            "yontem_surumu": TANIK_YONTEM_SURUMU,
            "tanikli_birim": len(skorlar),
            "taniksiz_birim": birim - len(skorlar),
            "skor_10_alti": sum(1 for x in skorlar if x < 10),
            "skor_50_alti": sum(1 for x in skorlar if x < 50),
        }
    return ayrinti


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source <meal>` komutu; cikis kodunu dondurur."""

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
