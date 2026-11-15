"""Risale ayet atif dizini QA kapilari (A20.7b; K-52 madde 13): `risale-atif-dizini`.

Kapi islevleri bellekteki `AtifGirdisi` uzerinde calisir (`qa/run_risale_atif.py` yukler).
Bulgular ASCII ve kisadir: yalniz satir numarasi, capa, sayi ve alan adi tasir; metin asla.

* G-KAY: kaynak kaydi gecerli (`slug`, `tur = baglanti_verisi`, `surum`, `atif_metni` dolu);
  manifest araci `quran-toolkit` 0.1.0'dir; her satirin `data_version` ve `evidence.arac_surumu`
  manifest ve kayitla ayni; `data_version` kayit surumu ve units ozetinden uretilenle ayni.
* G-BUT: satir sayisi ve ozet manifestle ayni; alan kumesi `XREF_ALANLARI`; `origin = hat`,
  `status = aday`, tur `atif` ya da `iktibas`, `score_binde` ve `confidence_binde` 0..1000 tam
  sayi; `evidence` izinli anahtar ve metinsiz deger, `source_id = risale-atif-dizini`;
  `src_anchor` birimi anchor ciktisinda, `src_span` birim metnine sigar ve iki ucu birlesen
  isaretin ustune dusmez; `iktibas` araligi bir `ar` isaretinin icindedir (Osmanlica ve Arapca
  kitapta `alinti` isaretinin); `atif` satiri birim metninden ayni gramerle yeniden uretilir;
  `evidence.src_hash` birimin `content_hash` degerinin ilk 16 hanesidir; `dst_anchor` Tanzil'de
  var olan bir ayettir ve `dst_span` ayetin kelime sayisina sigar.
* G-CAP: `src_anchor` gramere uyan, kanonik Risale paragraf capasi; `dst_anchor` kanonik ayet
  capasi; `dst_span` kelime araligi olarak `to_unit_span` ile ayni birim ve araligi verir; dogal
  anahtar `(type, src_anchor, src_span, dst_anchor, dst_span)` tekil ve satirlar capa sirasinda
  (satirlardan yeniden kurulan kanonik baytlarin ozeti dosya ozetiyle ayni).
* G-NOR: arama metni uretilmez; kapi uygulanmaz, satirlarin metin tasimadigi sayilir.
"""

import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Q, Rn, format, parse, to_unit_span
from mutalaa_pipeline.enrich import arapca_dizi, atif_gramer, citations
from mutalaa_pipeline.enrich.arac_sarmalayicilari import ARAC_ADI, ARAC_SURUMU
from mutalaa_pipeline.enrich.kuran_metni import KuranMetni
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak

EN_COK_ORNEK: Final = 5
KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
EN_COK_ALAN_UZUNLUGU: Final = 256  # hicbir alan metin tasimaz; capa en uzun 256 karakter
SRC_HASH_UZUNLUGU: Final = 16
ISARET_YALNIZ_ALINTI: Final = citations.ISARET_YALNIZ_ALINTI

Satir = Mapping[str, object]


@dataclass(frozen=True)
class AtifBirimi:
    """Anchor ciktisindaki bir birimden yalniz denetim icin gereken alanlar (metin bellekte)."""

    metin: str
    marks: Sequence[Mapping[str, object]]
    dil: str
    content_hash: str


@dataclass
class AtifGirdisi:
    kayit: Kaynak
    manifest: Mapping[str, object]  # `ayrintilar` alani
    units_sha256: str  # taranan anchor ciktisinin ozeti
    xrefs_sha256: str  # xrefs.jsonl ozeti (manifestten)
    satirlar: Sequence[Satir]
    birimler: Mapping[str, AtifBirimi]  # yalniz satirlarda gecen src capalari
    kuran: KuranMetni
    ek: dict[str, object] = field(default_factory=dict)


def _bulgu(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        ornek = ", ".join(liste[:EN_COK_ORNEK])
        bulgular.append(f"{ad}: {len(liste)} {neden} (ornek: {ornek})")


def _tam(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def _aralik(deger: object) -> tuple[int, int] | None:
    if (
        isinstance(deger, list)
        and len(deger) == 2
        and (a := _tam(deger[0])) is not None
        and (b := _tam(deger[1])) is not None
    ):
        return a, b
    return None


def _no(i: int) -> str:
    return f"satir {i + 1}"


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: AtifGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    if k.slug != citations.KAYNAK_ID:
        bulgular.append("kaynak kaydi: slug kaynak kimligiyle ayni degil")
    if k.tur is not SourceKind.BAGLANTI_VERISI:
        bulgular.append("kaynak kaydi: tur baglanti_verisi olmali")
    if k.surum is None or k.surum == "":
        bulgular.append("kaynak kaydi: surum yok")
    if k.atif_metni.strip(" \t\n") == "":
        bulgular.append("kaynak kaydi: atif_metni bos")
    if g.manifest.get("arac") != ARAC_ADI or g.manifest.get("arac_surumu") != ARAC_SURUMU:
        bulgular.append(f"manifest: arac {ARAC_ADI} {ARAC_SURUMU} degil")
    beklenen = f"{citations.KAYNAK_ID}@{k.surum}/{g.units_sha256[:12]}" if k.surum else None
    if g.manifest.get("data_version") != beklenen:
        bulgular.append(
            "manifest: data_version kayit surumu ve units ozetinden uretilenle ayni degil"
        )
    surumsuz: list[str] = []
    for i, s in enumerate(g.satirlar):
        if s.get("data_version") != beklenen:
            surumsuz.append(_no(i))
    _bulgu(bulgular, "data_version", surumsuz, "satirda manifestteki degerle ayni degil")
    arac_farki: list[str] = []
    for i, s in enumerate(g.satirlar):
        ev = s.get("evidence")
        if (
            isinstance(ev, dict)
            and ev.get("yontem") == citations.YONTEM_ARAC
            and (ev.get("arac") != ARAC_ADI or ev.get("arac_surumu") != ARAC_SURUMU)
        ):
            arac_farki.append(_no(i))
    _bulgu(bulgular, "evidence", arac_farki, "satirda arac adi ya da surumu beklenen degil")
    return KapiSonucu("G-KAY", tuple(bulgular), {"satir": len(g.satirlar)})


# --- G-BUT -------------------------------------------------------------------------------


def _atif_anahtarlari(metin: str) -> set[tuple[int, int, int, int]]:
    """Birim metninden ayni gramerle uretilen `(bas, son, sure, ayet)` kumesi."""
    sonuc: set[tuple[int, int, int, int]] = set()
    for atif in atif_gramer.ayristir(metin, None).atiflar:
        for ayet in atif.ayetler:
            sonuc.add((atif.bas, atif.son, atif.sure, ayet))
    return sonuc


def _sinir_mn(metin: str, bas: int, son: int) -> bool:
    """Aralik birlesen isaretin (Mn) ustunden baslar ya da onun oncesinde biter mi."""
    if unicodedata.category(metin[bas]) == "Mn":
        return True
    return son < len(metin) and unicodedata.category(metin[son]) == "Mn"


def _dst_denetle(g: AtifGirdisi, i: int, s: Satir, bulgular: dict[str, list[str]]) -> None:
    dst = s.get("dst_anchor")
    ref = None
    if isinstance(dst, str):
        try:
            ref = parse(dst)
        except AnchorError:
            ref = None
    if ref is None or not isinstance(ref.anchor, Q) or ref.anchor.ilk is not None:
        bulgular["dst"].append(_no(i))
        return
    ayet = g.kuran.ayet(ref.anchor.sure, ref.anchor.ayet)
    if ayet is None:
        bulgular["dst"].append(_no(i))
        return
    aralik = s.get("dst_span")
    if aralik is None:
        return
    ab = _aralik(aralik)
    if ab is None or not 1 <= ab[0] < ab[1] <= ayet.kelime + 1:
        bulgular["dst_span"].append(_no(i))


def _src_denetle(
    g: AtifGirdisi,
    i: int,
    s: Satir,
    tur: object,
    bulgular: dict[str, list[str]],
    atif_onbellegi: dict[str, set[tuple[int, int, int, int]]],
    dizi_onbellegi: dict[str, list[arapca_dizi.ArapcaDizi]],
) -> None:
    src = s.get("src_anchor")
    birim = g.birimler.get(src) if isinstance(src, str) else None
    if birim is None:
        bulgular["src_birim"].append(_no(i))
        return
    ab = _aralik(s.get("src_span"))
    if ab is None or not 0 <= ab[0] < ab[1] <= len(birim.metin):
        bulgular["src_span"].append(_no(i))
        return
    bas, son = ab
    if _sinir_mn(birim.metin, bas, son):
        bulgular["mn"].append(_no(i))
    ev = s.get("evidence")
    if isinstance(ev, dict) and ev.get("src_hash") != birim.content_hash[:SRC_HASH_UZUNLUGU]:
        bulgular["src_hash"].append(_no(i))
    assert isinstance(src, str)
    if tur == citations.TUR_ATIF:
        kume = atif_onbellegi.get(src)
        if kume is None:
            kume = atif_onbellegi[src] = _atif_anahtarlari(birim.metin)
        ref = _ayet_cifti(s)
        if ref is None or (bas, son, *ref) not in kume:
            bulgular["atif"].append(_no(i))
    elif tur == citations.TUR_IKTIBAS:
        diziler = dizi_onbellegi.get(src)
        if diziler is None:
            diziler = dizi_onbellegi[src] = arapca_dizi.isaretlerden(birim.metin, birim.marks)
        icinde = [d for d in diziler if d.bas <= bas and son <= d.son]
        if not icinde:
            bulgular["ar_isareti"].append(_no(i))
        elif birim.dil in ISARET_YALNIZ_ALINTI and all(
            d.tur != arapca_dizi.TUR_ALINTI for d in icinde
        ):
            bulgular["blok"].append(_no(i))


def _ayet_cifti(s: Satir) -> tuple[int, int] | None:
    dst = s.get("dst_anchor")
    if not isinstance(dst, str):
        return None
    try:
        ref = parse(dst)
    except AnchorError:
        return None
    return (ref.anchor.sure, ref.anchor.ayet) if isinstance(ref.anchor, Q) else None


def g_but(g: AtifGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    beklenen_satir = g.manifest.get("sayilar")
    sayi = beklenen_satir.get("xref") if isinstance(beklenen_satir, dict) else None
    if sayi != len(g.satirlar):
        bulgular.append("satir sayisi manifestteki sayiyla ayni degil")
    if not g.satirlar:
        bulgular.append("xrefs.jsonl bos")
    kat: dict[str, list[str]] = {
        k: []
        for k in (
            "alan",
            "sabit",
            "tur",
            "puan",
            "evidence",
            "metin",
            "src_birim",
            "src_span",
            "mn",
            "src_hash",
            "atif",
            "ar_isareti",
            "blok",
            "dst",
            "dst_span",
        )
    }
    atif_onbellegi: dict[str, set[tuple[int, int, int, int]]] = {}
    dizi_onbellegi: dict[str, list[arapca_dizi.ArapcaDizi]] = {}
    for i, s in enumerate(g.satirlar):
        if set(s) != citations.XREF_ALANLARI:
            kat["alan"].append(_no(i))
            continue
        if s["origin"] != citations.ORIGIN or s["status"] != citations.STATUS:
            kat["sabit"].append(_no(i))
        tur = s["type"]
        if tur not in citations.TURLER:
            kat["tur"].append(_no(i))
        for ad in ("score_binde", "confidence_binde"):
            v = _tam(s[ad])
            if v is None or not 0 <= v <= citations.BINDE_USTU:
                kat["puan"].append(_no(i))
        ev = s["evidence"]
        try:
            if not isinstance(ev, dict):
                raise GirdiHatasi("evidence nesne degil")
            citations.evidence_denetle(ev)
            if ev.get("source_id") != citations.KAYNAK_ID:
                raise GirdiHatasi("source_id")
        except GirdiHatasi:
            kat["evidence"].append(_no(i))
        if any(isinstance(v, str) and len(v) > EN_COK_ALAN_UZUNLUGU for v in s.values()):
            kat["metin"].append(_no(i))
        _src_denetle(g, i, s, tur, kat, atif_onbellegi, dizi_onbellegi)
        _dst_denetle(g, i, s, kat)
    aciklama = {
        "alan": "satirda alan kumesi XREF_ALANLARI degil",
        "sabit": "satirda origin hat ya da status aday degil",
        "tur": "satirda tur atif ya da iktibas degil",
        "puan": "satirda score_binde/confidence_binde 0..1000 tam sayi degil",
        "evidence": "satirda evidence izinli anahtar/metinsiz deger degil ya da source_id yanlis",
        "metin": "satirda capadan uzun metin alani var",
        "src_birim": "satirin src_anchor birimi anchor ciktisinda yok",
        "src_span": "satirin src_span araligi birim metnine sigmiyor",
        "mn": "satirin src_span siniri birlesen isaretin ustune dusuyor",
        "src_hash": "satirda evidence.src_hash birim ozetinin ilk 16 hanesiyle ayni degil",
        "atif": "atif satiri birim metninden ayni gramerle uretilemiyor",
        "ar_isareti": "iktibas araligi bir ar isaretinin icinde degil",
        "blok": "iktibas araligi Osmanlica/Arapca kitapta alinti isaretinin icinde degil",
        "dst": "satirin dst_anchor ayeti Tanzil'de yok ya da ayet capasi degil",
        "dst_span": "satirin dst_span araligi ayetin kelime sayisina sigmiyor",
    }
    for ad, neden in aciklama.items():
        _bulgu(bulgular, ad, kat[ad], neden)
    sayilar = {
        "satir": len(g.satirlar),
        "birim": len(g.birimler),
        "atif": sum(1 for s in g.satirlar if s.get("type") == citations.TUR_ATIF),
        "iktibas": sum(1 for s in g.satirlar if s.get("type") == citations.TUR_IKTIBAS),
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: AtifGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    src_kotu: list[str] = []
    dst_kotu: list[str] = []
    span_kotu: list[str] = []
    for i, s in enumerate(g.satirlar):
        src = s.get("src_anchor")
        try:
            if not isinstance(src, str):
                raise AnchorError("BICIM", "src")
            ref = parse(src)
            if (
                not isinstance(ref.anchor, Rn)
                or ref.anchor.s is not None
                or ref.span is not None
                or format(ref) != src
            ):
                raise AnchorError("KANONIK_DEGIL", "src")
        except AnchorError:
            src_kotu.append(_no(i))
        dst = s.get("dst_anchor")
        try:
            if not isinstance(dst, str):
                raise AnchorError("BICIM", "dst")
            dref = parse(dst)
            if not isinstance(dref.anchor, Q) or dref.anchor.ilk is not None or format(dref) != dst:
                raise AnchorError("KANONIK_DEGIL", "dst")
            aralik = _aralik(s.get("dst_span"))
            if s.get("dst_span") is not None:
                if aralik is None or aralik[1] - 1 < aralik[0]:
                    raise AnchorError("TERS_ARALIK", "span")
                ilk, son = aralik[0], aralik[1] - 1
                kelime = AnchorRef(
                    Q(dref.anchor.sure, dref.anchor.ayet, ilk, None if son == ilk else son)
                )
                if to_unit_span(parse(format(kelime))) != to_unit_span(kelime):
                    raise AnchorError("KANONIK_DEGIL", "span")
                birim = to_unit_span(kelime)
                if birim.unit != dst or birim.span != aralik:
                    raise AnchorError("KANONIK_DEGIL", "span")
        except AnchorError:
            dst_kotu.append(_no(i))
            continue
        except ValueError:
            span_kotu.append(_no(i))
    _bulgu(
        bulgular,
        "src_anchor",
        src_kotu,
        "satirda Risale paragraf capasi gecersiz ya da kanonik degil",
    )
    _bulgu(bulgular, "dst_anchor", dst_kotu, "satirda ayet capasi ya da dst_span gecersiz")
    _bulgu(bulgular, "dst_span", span_kotu, "satirda dst_span birim araligina cevrilemiyor")
    try:
        satirlar = [dict(s) for s in g.satirlar]
        if satirlar != sorted(satirlar, key=citations.siralama_anahtari):
            bulgular.append("satirlar capa sirasinda degil")
        veri, _ = citations.xrefs_baytlari(satirlar)
    except GirdiHatasi as hata:
        bulgular.append(f"dogal anahtar: {hata}")
    except (AnchorError, KeyError, TypeError):
        bulgular.append("dogal anahtar: satirlardan okunamadi")
    else:
        if lineage.sha256_bayt(veri) != g.xrefs_sha256:
            bulgular.append("satirlar capa sirasinda degil ya da kanonik baytlarla ayni degil")
    return KapiSonucu("G-CAP", tuple(bulgular), {"satir": len(g.satirlar)})


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: AtifGirdisi) -> KapiSonucu:
    """Arama metni uretilmez: kapi uygulanmaz; satirlarin metin tasimadigini dogrular."""
    bulgular: list[str] = []
    fazla = [
        _no(i)
        for i, s in enumerate(g.satirlar)
        if any(isinstance(v, str) and len(v) > EN_COK_ALAN_UZUNLUGU for v in s.values())
    ]
    _bulgu(bulgular, "metin", fazla, "satirda capadan uzun metin alani var")
    return KapiSonucu("G-NOR", tuple(bulgular), {"uygulanmaz": 1, "satir": len(g.satirlar)})


KAPI_ISLEVLERI: Final[dict[str, Callable[[AtifGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}

__all__ = ["KAPILAR", "KAPI_ISLEVLERI", "AtifBirimi", "AtifGirdisi"]
