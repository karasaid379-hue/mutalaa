"""RNK Risale normalize ve capa adimlari (A20.2b, K-52 madde 2, 4 ve 8): `risale-rnk-metin`.

Iskelet `adimlar/fikstur.py` ile aynidir; birimler cok buyuk oldugu icin dosyalar satir satir
akitilir (`staged.satirlari_akit`) ve bellekte yalniz tek satirin nesnesi ile siralanacak satir
baytlari tutulur. Ingest capalari zaten verir (`ingest/risale_rnk_staged.py`: sayili bolum
kaliplari, `p{n}`, `hasiye-{n}`); bu adimlar capayi DEGISTIRMEZ, yalniz dogrular ve turetilmis
alanlari ekler. Kanonik metin (`text`) hicbir donusumden gecmez (K-26: ucuncu taraf, bayt bayt).

`mutalaa normalize --source risale-rnk-metin`: son ingest calismasini okur, arama anahtarlarini
ekler. Turkce (`dil = tr`) kitapta `tr_narrow`, `tr_wide`, `tr_stem` ve `ar_norm` (Arapca bloklar,
yoksa `null`); Osmanlica (`ota`) ve Arapca (`ar`) kitapta YALNIZ `ar_norm` (`tr_*` `null`;
K-52 madde 4). Anahtarlar `search_keys` ve `normalize_ar` ile uretilir.

`mutalaa anchor --source risale-rnk-metin`: son normalize calismasina `export pg` icin alanlari
ekler ve `units.jsonl` yazar:

    kind          "risale"
    role          "baslik" (baslik birimi), "dipnot" (hasiye/dipnot birimi), "govde"
    parent_path   "rn:" + bolum yolu (capanin `:p{n}` oncesi; hasiye birimde `…:hasiye-{n}`)
    ord           kitap icinde okuma sirasi 1..N (dosya, ilk satir, hasiye sirasi, capa)
    ayah_lo/hi    null
    marks         `ar`, `hasiye`, `rnk` isaretleri (kod noktasi, yari acik); birlestirme bosluk
                  isareti (`satir`) atilir: kaynak `provenance.konum.segmentler`den kurulur
    sentences     [[bas, son], ...] kod noktasi, yari acik (`anchor/cumle.py`; `ar` isaretli
                  araliklarda bolmez; baslik biriminde bos); surum `provenance.cumle.surum`
    content_hash  UTF-8 baytlarin SHA-256'si (NFC yok)
    metin_durumu  "taslak"
    data_version  "{slug}@{surum}" (surum kaynak kaydindan)

`attrs`: `kind`, `marks`, `bolum_yolu` ve `slug` ust alanlara tasinir; `baslik_yolu` (bolumun
gorunen baslik zinciri), `dil`, `yon`, `p`, `sayfa` ... kalir.

Capa elle bicimlenmez: ayristirma ve dogrulama `mutalaa_pipeline.anchor` ile yapilir. Onceki
calismayla capa ve `content_hash` karsilastirmasi `qa run` G-CAP'indedir.
"""

import hashlib
import sys
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.adimlar.normalize_tanzil import INGEST_ALANLARI
from mutalaa_pipeline.anchor import AnchorError, Rn, SortKey, content_hash, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.cumle import CUMLE_SURUMU, cumleleri_ayir
from mutalaa_pipeline.anchor.risale import (
    RisaleHatasi,
    bolum_kalibi,
    rn_capa,
    yol_denetle,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_rnk_kilit import KAYNAK
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, normalize_ar, search_keys
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import Satir, satir_baytlari, satirlari_akit
from mutalaa_pipeline.zincir import (
    ANCHOR_ADIMI,
    INGEST_ADIMI,
    NORMALIZE_ADIMI,
    Calisma,
    girdi_olarak,
    girdileri_ayni,
    saglam_olmali,
    son_calisma,
)

KIND: Final = "risale"
METIN_DURUMU: Final = "taslak"
ROL_GOVDE: Final = "govde"
ROL_BASLIK: Final = "baslik"
ROL_DIPNOT: Final = "dipnot"
DILLER: Final = ("tr", "ota", "ar")
TR_ALANLARI: Final = ("tr_narrow", "tr_wide", "tr_stem")
NORMALIZE_ALANLARI: Final = INGEST_ALANLARI | {"ar_norm", *TR_ALANLARI}
ANCHOR_ALANLARI: Final = NORMALIZE_ALANLARI | {
    "kind",
    "role",
    "parent_path",
    "ord",
    "ayah_lo",
    "ayah_hi",
    "marks",
    "sentences",
    "content_hash",
    "metin_durumu",
    "data_version",
}
# `attrs` anahtarlari ust alanlara tasinir (anchor adimi).
TASINAN_ATTRS: Final = ("kind", "marks", "bolum_yolu", "slug")
ISARET_TURLERI: Final = frozenset({"ar", "hasiye", "rnk", "satir"})
BIRLESTIRME_ISARETI: Final = "satir"
HASIYE_TURU: Final = "hasiye"
BASLIK_TURU: Final = "baslik"
PARAGRAF_TURU: Final = "paragraf"
BIRIM_TURLERI: Final = (BASLIK_TURU, PARAGRAF_TURU, HASIYE_TURU)
ROLLER: Final = {BASLIK_TURU: ROL_BASLIK, PARAGRAF_TURU: ROL_GOVDE, HASIYE_TURU: ROL_DIPNOT}
Satirlar = Iterable[Satir]


# --- capa ------------------------------------------------------------------------------------


def rn_yolu(capa: str) -> tuple[str, ...]:
    """Kanonik, araliksiz, paragraf duzeyinde `rn:` capasinin yolu (`yol[0]` kitap).

    Capa gramerden gecer (`parse`), `anchor.risale` adlarini ve derinligi dogrular ve yeniden
    bicimlenince ayni dizgeyi verir; cumle (`:s{n}`) ve `@` araligi birim capasi degildir.
    Gecersizse `GirdiHatasi` (iletide yalniz capa).
    """
    try:
        ref = parse(capa)
        cozulen = ref.anchor
        if (
            not isinstance(cozulen, Rn)
            or ref.span is not None
            or cozulen.s is not None
            or anchor_format(ref) != capa
        ):
            raise GirdiHatasi(f"{capa}: Risale birim capasi (rn:...:p{{n}}) degil")
        yol_denetle(cozulen.yol)
        if rn_capa(cozulen.yol, cozulen.p) != capa:
            raise GirdiHatasi(f"{capa}: capa kanonik degil")
    except (AnchorError, RisaleHatasi):
        raise GirdiHatasi(f"{capa}: capa gecersiz") from None
    return cozulen.yol


def parent_yolu(yol: Sequence[str]) -> str:
    """`parent_path`: `rn:` ve bolum yolu (kitap dahil)."""
    return "rn:" + ":".join(yol)


def hasiye_bolumu_mu(yol: Sequence[str]) -> bool:
    """Yolun son parcasi `hasiye-{n}` kalibi mi (dipnot bolumu)."""
    son = bolum_kalibi(yol[-1]) if len(yol) > 1 else None
    return son is not None and son.tur == "hasiye"


def _dil(satir: Satir, attrs: Mapping[str, object]) -> str:
    dil = attrs.get("dil")
    if dil not in DILLER or not isinstance(dil, str):
        raise GirdiHatasi(f"{satir.etiket}: satir {satir.no}: attrs.dil tr, ota ya da ar degil")
    return dil


def _birim_turu(satir: Satir, attrs: Mapping[str, object]) -> str:
    tur = attrs.get("kind")
    if tur not in BIRIM_TURLERI or not isinstance(tur, str):
        raise GirdiHatasi(
            f"{satir.etiket}: satir {satir.no}: attrs.kind baslik/paragraf/hasiye degil"
        )
    return tur


# --- normalize -------------------------------------------------------------------------------


def normalize_satiri(slug: str, satir: Satir) -> dict[str, object]:
    """Ingest satirina arama anahtarlarini ekler (satir degismez, kopyalanir)."""
    yer = f"{satir.etiket}: satir {satir.no}"
    if set(satir.veri) != INGEST_ALANLARI:
        raise GirdiHatasi(f"{yer}: alan kumesi ingest cikisi degil")
    if satir.metin("source_id") != slug:
        raise GirdiHatasi(f"{yer}: source_id {slug} degil")
    rn_yolu(satir.metin("anchor"))
    dil = _dil(satir, satir.nesne("attrs"))
    metin = satir.metin("text")
    cikti = dict(satir.veri)
    if dil == "tr":
        anahtarlar = search_keys(metin)
        cikti.update(
            tr_narrow=anahtarlar.tr_narrow,
            tr_wide=anahtarlar.tr_wide,
            tr_stem=anahtarlar.tr_stem,
            ar_norm=anahtarlar.ar_norm or None,
        )
    else:  # Osmanlica ve Arapca: yalniz ar_norm (K-52 madde 4)
        cikti.update(
            tr_narrow=None,
            tr_wide=None,
            tr_stem=None,
            ar_norm=normalize_ar(metin) or None,
        )
    kok = dict(satir.nesne("provenance"))
    kok["arama"] = {"normalizer_version": NORMALIZER_VERSION}
    cikti["provenance"] = kok
    return cikti


# --- anchor ----------------------------------------------------------------------------------


def ar_araliklari(
    capa: str, marks: Sequence[Mapping[str, object]], uzunluk: int
) -> list[tuple[int, int]]:
    """`ar` isaretli araliklar: bos olanlar atilir, ust uste binenler birlesir, metne sigmali.

    `cumleleri_ayir` artan ve ayrik araliklar ister; ingest isaretleri ic ice gelebilir.
    """
    ham: list[tuple[int, int]] = []
    for isaret in marks:
        if isaret.get("t") != "ar":
            continue
        bas, son = isaret.get("s"), isaret.get("e")
        if (
            isinstance(bas, bool)
            or isinstance(son, bool)
            or not isinstance(bas, int)
            or not isinstance(son, int)
            or not 0 <= bas <= son <= uzunluk
        ):
            raise GirdiHatasi(f"{capa}: ar isareti gecersiz")
        if bas < son:
            ham.append((bas, son))
    birlesik: list[tuple[int, int]] = []
    for bas, son in sorted(ham):
        if birlesik and bas < birlesik[-1][1]:
            birlesik[-1] = (birlesik[-1][0], max(birlesik[-1][1], son))
        else:
            birlesik.append((bas, son))
    return birlesik


def isaretleri_dogrula(capa: str, marks: object, uzunluk: int) -> list[dict[str, object]]:
    """Ingest `marks` listesi: bilinen turler, yari acik aralik metne sigar. Liste kopyalanir."""
    if not isinstance(marks, list):
        raise GirdiHatasi(f"{capa}: attrs.marks liste degil")
    sonuc: list[dict[str, object]] = []
    for isaret in marks:
        if not isinstance(isaret, dict) or isaret.get("t") not in ISARET_TURLERI:
            raise GirdiHatasi(f"{capa}: bilinmeyen isaret turu")
        bas = isaret.get("s")
        son = isaret.get("e", bas)
        if (
            isinstance(bas, bool)
            or isinstance(son, bool)
            or not isinstance(bas, int)
            or not isinstance(son, int)
            or not 0 <= bas <= son <= uzunluk
        ):
            raise GirdiHatasi(f"{capa}: isaret araligi gecersiz")
        sonuc.append(isaret)
    return sonuc


def cumle_araliklari(
    capa: str, metin: str, marks: Sequence[Mapping[str, object]]
) -> list[list[int]]:
    """Cumle sinirlari `[[bas, son], ...]` (kod noktasi, yari acik; `ar` isaretlerinde bolmez)."""
    try:
        araliklar = cumleleri_ayir(metin, ar_araliklari(capa, marks, len(metin)))
    except ValueError:
        raise GirdiHatasi(f"{capa}: cumle ayirici gecersiz isaretle durdu") from None
    return [[bas, son] for bas, son in araliklar]


def anchor_satiri(slug: str, satir: Satir, surum: str) -> dict[str, object]:
    """Normalize satirina capa alanlarini ekler (`ord` haric; `ord_haritasi` ile eklenir)."""
    yer = f"{satir.etiket}: satir {satir.no}"
    if set(satir.veri) != NORMALIZE_ALANLARI:
        raise GirdiHatasi(f"{yer}: alan kumesi normalize cikisi degil")
    if satir.metin("source_id") != slug:
        raise GirdiHatasi(f"{yer}: source_id {slug} degil")
    capa = satir.metin("anchor")
    yol = rn_yolu(capa)
    attrs = dict(satir.nesne("attrs"))
    tur = _birim_turu(satir, attrs)
    _dil(satir, attrs)
    bolum_yolu = attrs.get("bolum_yolu")
    beklenen = list(yol[1:-1]) if tur == HASIYE_TURU else list(yol[1:])
    if (
        attrs.get("slug") != yol[0]
        or bolum_yolu != beklenen
        or (tur == HASIYE_TURU) != hasiye_bolumu_mu(yol)
        or not isinstance(attrs.get("baslik_yolu"), list)
        or len(attrs["baslik_yolu"]) != len(beklenen)  # type: ignore[arg-type]
    ):
        raise GirdiHatasi(f"{yer}: attrs capayla tutarsiz ({capa})")
    metin = satir.metin("text")
    marks = isaretleri_dogrula(capa, attrs.get("marks"), len(metin))
    for ad in TASINAN_ATTRS:
        attrs.pop(ad, None)
    sonuclar = [] if tur == BASLIK_TURU else cumle_araliklari(capa, metin, marks)
    kok = dict(satir.nesne("provenance"))
    kok["cumle"] = {"surum": CUMLE_SURUMU}
    cikti = dict(satir.veri)
    cikti.update(
        kind=KIND,
        role=ROLLER[tur],
        parent_path=parent_yolu(yol),
        attrs=attrs,
        provenance=kok,
        ayah_lo=None,
        ayah_hi=None,
        marks=[m for m in marks if m.get("t") != BIRLESTIRME_ISARETI],
        sentences=sonuclar,
        content_hash=content_hash(metin),
        metin_durumu=METIN_DURUMU,
        data_version=f"{slug}@{surum}",
    )
    return cikti


def ord_anahtari_degerleri(
    capa: str, saglayici: Mapping[str, object]
) -> tuple[str, str, int, int, SortKey]:
    """Okuma sirasi anahtari: (kitap, dosya, ilk satir, dipnot sirasi, capa sirasi).

    Dipnot (`hasiye-{n}` bolumu) ayni satirdaki ana paragrafin ardindan gelir.
    """
    yol = rn_yolu(capa)
    dosya = saglayici.get("file")
    konum = saglayici.get("konum")
    satirlar = konum.get("satir") if isinstance(konum, dict) else None
    if (
        not isinstance(dosya, str)
        or not isinstance(satirlar, list)
        or not satirlar
        or not isinstance(satirlar[0], int)
        or isinstance(satirlar[0], bool)
    ):
        raise GirdiHatasi(f"{capa}: provenance.konum.satir yok")
    return (yol[0], dosya, satirlar[0], 1 if hasiye_bolumu_mu(yol) else 0, sort_key(parse(capa)))


def ord_anahtari(satir: Satir) -> tuple[str, str, int, int, SortKey]:
    """`ord_anahtari_degerleri`, `Satir` uzerinden."""
    return ord_anahtari_degerleri(satir.metin("anchor"), satir.nesne("provenance"))


def ord_haritasi(satirlar: Satirlar) -> dict[str, int]:
    """Capa -> kitap icinde okuma sirasi (1..N). Anahtar sirasi `ord_anahtari`dir."""
    anahtarlar = [(ord_anahtari(s), s.metin("anchor")) for s in satirlar]
    anahtarlar.sort(key=lambda cift: cift[0])
    sayac: Counter[str] = Counter()
    harita: dict[str, int] = {}
    for (kitap, *_), capa in anahtarlar:
        sayac[kitap] += 1
        harita[capa] = sayac[kitap]
    return harita


# --- dosya yazimi ------------------------------------------------------------------------------


def _siralayip_yaz(
    ctx: RunContext, hedef: Path, kayitlar: list[tuple[SortKey, str, bytes]]
) -> lineage.Cikti:
    """Satir baytlarini capaya gore (okuma sirasi) siralar, tekilligi denetler ve yazar."""
    kayitlar.sort(key=lambda k: k[0])
    ozet = hashlib.sha256()
    onceki: str | None = None
    for _, capa, _ in kayitlar:
        if capa == onceki:
            raise GirdiHatasi(f"yinelenen capa: {capa}")
        onceki = capa
    if ctx.dry_run:
        for _, _, veri in kayitlar:
            ozet.update(veri)
    else:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        with hedef.open("wb") as dosya:
            for _, _, veri in kayitlar:
                dosya.write(veri)
                ozet.update(veri)
    return lineage.Cikti(
        yol=lineage.goreli_yol(ctx.veri_kok, hedef), sha256=ozet.hexdigest(), satir=len(kayitlar)
    )


def _calisma_dosyasi(calisma: Calisma, ad: str = lineage.UNITS_ADI) -> Path:
    return calisma.klasor / ad


# --- adimlar ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class AdimSonucu:
    run_id: str
    atlandi: bool
    birim_sayisi: int
    klasor: Path | None
    onceki_run_id: str | None = None
    diller: Mapping[str, int] | None = None


def kaynak_denetle(source: str) -> None:
    if source != KAYNAK:
        raise GirdiHatasi(f"bu adim yalniz {KAYNAK} icindir")


def _atla(
    ctx: RunContext, slug: str, girdiler: list[lineage.Girdi]
) -> tuple[str, tuple[str, Path, dict[str, object]] | None, bool]:
    """Parmak izi ve onceki calisma; ayniysa atlanir (`--force` ve kirli agac atlamaz)."""
    parmak = ctx.parmak_izi(girdiler)
    onceki = lineage.son_basarili(ctx.staged_kaynak_dizini(slug), ctx.adim)
    onceki_manifest = onceki[2] if onceki else None
    atla = girdileri_ayni(onceki_manifest, girdiler) and lineage.atlanabilir(
        onceki=onceki_manifest,
        parmak=parmak,
        git_kirli=ctx.git().kirli,
        force=ctx.force,
        veri_kok=ctx.veri_kok,
    )
    return parmak, onceki, atla


def run_normalize(ctx: RunContext, slug: str = KAYNAK) -> AdimSonucu:
    """Kaynak kaydi, son ingest, parmak izi, arama anahtarlari, `staged`, manifest (en son)."""
    ctx.require_sources(slug)  # kayitsiz ya da gecersiz kayitta cikis 2
    ctx.gunluk.yaz("INFO", "normalize_basla", source_id=slug)
    ingest = son_calisma(ctx, slug, INGEST_ADIMI, ipucu=f"once: ingest risale --source {slug}")
    saglam_olmali(ctx, ingest)
    girdiler = [girdi_olarak(ingest)]
    parmak, onceki, atla = _atla(ctx, slug, girdiler)
    if atla:
        ctx.gunluk.yaz("INFO", "normalize_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return AdimSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    kayitlar: list[tuple[SortKey, str, bytes]] = []
    diller: Counter[str] = Counter()
    for satir in satirlari_akit(_calisma_dosyasi(ingest), f"ingest {slug} units.jsonl"):
        cikti = normalize_satiri(slug, satir)
        capa = str(cikti["anchor"])
        diller[str(satir.nesne("attrs")["dil"])] += 1
        kayitlar.append((sort_key(parse(capa)), capa, satir_baytlari(cikti)))
    cikti_dosyasi = _siralayip_yaz(ctx, ctx.staged_dizin(slug) / lineage.UNITS_ADI, kayitlar)
    birim = cikti_dosyasi.satir or 0
    ctx.sayi("birim", birim)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "normalize_dry_run", source_id=slug, sayilar={"birim": birim})
        return AdimSonucu(ctx.run_id, False, birim, None, diller=dict(diller))

    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti_dosyasi],
        parmak=parmak,
        ayrintilar={
            "kaynak": slug,
            "ingest": {slug: ingest.run_id},
            "normalizer_version": NORMALIZER_VERSION,
            "birim": birim,
            "diller": dict(sorted(diller.items())),
        },
    )
    ctx.gunluk.yaz("INFO", "normalize_bitti", source_id=slug, sayilar={"birim": birim})
    return AdimSonucu(ctx.run_id, False, birim, klasor, diller=dict(diller))


class AnchorEki(Protocol):
    """`run_anchor` kancasi: ek girdi ve ek ciktilar (sentetik fikstur: `page_map`, `xref`; A20.5a).

    `girdiler` parmak izine ve manifeste, `ciktilar` manifeste girer. `ciktilar` anchor satirlarini
    (yazilan `units.jsonl` satirlari, capa sirasinda degil okunma sirasinda) alir; dosyalarini
    `staged.dosya_yaz` ile yazar (`--dry-run`'da yazmaz) ve manifest `ayrintilar`ina eklenecek
    alanlari dondurur.
    """

    def girdiler(self, ctx: RunContext) -> list[lineage.Girdi]: ...

    def ciktilar(
        self, ctx: RunContext, satirlar: Sequence[Satir], surum: str
    ) -> tuple[list[lineage.Cikti], Mapping[str, object]]: ...


def run_anchor(ctx: RunContext, slug: str = KAYNAK, *, ek: AnchorEki | None = None) -> AdimSonucu:
    """Kaynak kaydi, son normalize, parmak izi, capa alanlari, `staged`, manifest (en son).

    `ek` verilirse ek girdiler parmak izine, ek ciktilar manifeste girer (varsayilan: yok;
    davranis degismez).
    """
    kayit = ctx.require_sources(slug)[slug]
    if kayit.surum is None:
        raise GirdiHatasi(f"kaynak {slug}: surum cozulemedi (TOML surum alani yok)")
    ctx.gunluk.yaz("INFO", "anchor_basla", source_id=slug)
    normalize = son_calisma(ctx, slug, NORMALIZE_ADIMI, ipucu=f"once: normalize --source {slug}")
    saglam_olmali(ctx, normalize)
    girdiler = [girdi_olarak(normalize)]
    if ek is not None:
        girdiler += ek.girdiler(ctx)
    parmak, onceki, atla = _atla(ctx, slug, girdiler)
    if atla:
        ctx.gunluk.yaz("INFO", "anchor_atlandi", source_id=slug)
        ctx.sayi("atlandi", 1)
        return AdimSonucu(ctx.run_id, True, 0, None, onceki[0] if onceki else None)

    dosya = _calisma_dosyasi(normalize)
    etiket = f"normalize {slug} units.jsonl"
    siralar = ord_haritasi(satirlari_akit(dosya, etiket))  # 1. gecis: yalniz okuma sirasi
    kayitlar: list[tuple[SortKey, str, bytes]] = []
    ek_satirlar: list[Satir] = []  # yalniz `ek` varken doldurulur
    sayilar: Counter[str] = Counter()
    for satir in satirlari_akit(dosya, etiket):  # 2. gecis: alanlar
        cikti = anchor_satiri(slug, satir, kayit.surum)
        capa = str(cikti["anchor"])
        cikti["ord"] = siralar[capa]
        if ek is not None:
            ek_satirlar.append(Satir("anchor", len(ek_satirlar) + 1, cikti))
        sayilar[f"rol_{cikti['role']}"] += 1
        sayilar["cumle"] += len(cikti["sentences"])  # type: ignore[arg-type]
        sayilar["isaret"] += len(cikti["marks"])  # type: ignore[arg-type]
        kayitlar.append((sort_key(parse(capa)), capa, satir_baytlari(cikti)))
    cikti_dosyasi = _siralayip_yaz(ctx, ctx.staged_dizin(slug) / lineage.UNITS_ADI, kayitlar)
    ek_ciktilar: list[lineage.Cikti] = []
    ek_ayrintilar: Mapping[str, object] = {}
    if ek is not None:
        ek_ciktilar, ek_ayrintilar = ek.ciktilar(ctx, ek_satirlar, kayit.surum)
    birim = cikti_dosyasi.satir or 0
    ctx.sayi("birim", birim)
    if ctx.dry_run:
        ctx.gunluk.yaz("INFO", "anchor_dry_run", source_id=slug, sayilar={"birim": birim})
        return AdimSonucu(ctx.run_id, False, birim, None)

    klasor = ctx.staged_dizin(slug)
    ctx.manifest_yaz(
        klasor,
        girdiler=girdiler,
        ciktilar=[cikti_dosyasi, *ek_ciktilar],
        parmak=parmak,
        ayrintilar={
            "kaynak": slug,
            "normalize_run": normalize.run_id,
            "data_version": f"{slug}@{kayit.surum}",
            "cumle_surumu": CUMLE_SURUMU,
            "birim": birim,
            "kitap": len({c.split(":")[1] for _, c, _ in kayitlar}),
            "sayilar": dict(sorted(sayilar.items())),
            **ek_ayrintilar,
        },
    )
    ctx.gunluk.yaz("INFO", "anchor_bitti", source_id=slug, sayilar={"birim": birim})
    return AdimSonucu(ctx.run_id, False, birim, klasor)


def _ozet(sonuc: AdimSonucu, dry_run: bool) -> str:
    if sonuc.atlandi:
        return f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
    if dry_run:
        return f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
    return f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"


def komut_normalize(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`normalize --source risale-rnk-metin` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_normalize(ctx, source)
        sys.stdout.write(f"normalize {source}: {_ozet(sonuc, ctx.dry_run)}\n")
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


def komut_anchor(
    *, source: str, dry_run: bool, force: bool, config: Path | None, kok: Path | None
) -> int:
    """`anchor --source risale-rnk-metin` komutu; cikis kodunu dondurur."""

    def govde(ctx: RunContext) -> int:
        kaynak_denetle(source)
        sonuc = run_anchor(ctx, source)
        sys.stdout.write(f"anchor {source}: {_ozet(sonuc, ctx.dry_run)}\n")
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


__all__ = [
    "ANCHOR_ALANLARI",
    "NORMALIZE_ALANLARI",
    "AdimSonucu",
    "AnchorEki",
    "anchor_satiri",
    "komut_anchor",
    "komut_normalize",
    "normalize_satiri",
    "ord_anahtari",
    "ord_anahtari_degerleri",
    "ord_haritasi",
    "rn_yolu",
    "run_anchor",
    "run_normalize",
]
