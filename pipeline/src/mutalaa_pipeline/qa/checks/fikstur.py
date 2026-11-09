# ruff: noqa: RUF001
"""Sentetik fikstur QA kapilari (A13.6): G-KAY, G-BUT, G-CAP, G-NOR.

Kapi islevleri bellekteki `FiksturGirdisi` uzerinde calisir; zinciri `qa/run_fikstur.py` yukler.
Bulgular ASCII ve kisadir: yalniz capa, sayi ve alan adi tasir, metin asla.

* G-KAY: kaynak kaydi gecerli, `atif_metni` sabit sentetik atif satiri, `tur` fiksture uygun,
  `surum` var.
* G-BUT: birim sayisi ve her birimin metni uretecin cikisiyla bayt bayt ayni (uretec belirlenimci);
  metin bos degil, kontrol karakteri yok, kendi metnimiz oldugu icin kanonik (`kanonik_metin`
  degismez: NFC dahil); kitapta `parent_path` bolum yolu.
* G-CAP: capa kanonik ve fiksturun ailesinden, tekil, sirali; `ord` 1..N; tefsirde `ayah_lo` /
  `ayah_hi` capadan turetilen yari acik aralik, kitapta ikisi de null; `content_hash` metnin
  SHA-256'si; sabit alanlar; onceki QA'dan gecmis anchor calismasinin her capasi durur ve
  `content_hash` degismez.
* G-NOR: normalizasyon vektorleri Python'da gecer; `tr_narrow`, `tr_wide`, `tr_stem` metinden
  `search_keys` ile yeniden uretilince ayni; `ar_norm` bos (null); `provenance.arama` surumu.
"""

import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline.adimlar.fikstur import (
    METIN_DURUMU,
    ROL,
    TR_ALANLARI,
    ayet_araligi,
    capa_ailesine_uyar,
)
from mutalaa_pipeline.anchor import content_hash, kanonik_metin, parse, sort_key
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.ingest.fikstur import KIND, KITAP, TEFSIR, FiksturBirimi
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, search_keys
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ATIF_METNI: Final = "Sentetik test verisi (Mütâlaa)."
KAYNAK_TURU: Final = {KITAP: SourceKind.KITAP, TEFSIR: SourceKind.TEFSIR}
ORNEK_CAPA: Final = 5
ISIK: Final = "Işık"  # Maestro arama akisi `isik` yazar (Test stratejisi §9)


@dataclass
class FiksturGirdisi:
    slug: str
    kayit: Kaynak
    anchor_satirlari: Sequence[Satir]
    beklenen: Sequence[FiksturBirimi]  # uretecin ayni surumdeki cikisi
    depo_kok: Path
    onceki: Onceki | None = None


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(ascii(c)[1:-1][:64] for c in capalar[:ORNEK_CAPA])
    fazla = len(capalar) - ORNEK_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def _bulgu(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")


def _kontrol_karakteri(metin: str) -> bool:
    """Kontrol (Cc) ya da bicim (Cf) karakteri var mi; U+000A paragraf ici satir sonu serbest."""
    return any(
        unicodedata.category(h) in ("Cc", "Cf", "Cs", "Co", "Cn") and h != "\n" for h in metin
    )


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: FiksturGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    if k.slug != g.slug or not g.slug.startswith("test-"):
        bulgular.append("kaynak kaydi: slug fikstur kimligiyle ayni degil ya da test- onekli degil")
    if k.tur is not KAYNAK_TURU[g.slug]:
        bulgular.append(f"kaynak kaydi: tur {KAYNAK_TURU[g.slug].value} olmali")
    if k.atif_metni != ATIF_METNI:
        bulgular.append("kaynak kaydi: atif_metni sabit sentetik atif satiri degil")
    if k.surum is None:
        bulgular.append("kaynak kaydi: surum yok")
    if k.notice_text is not None:
        bulgular.append("kaynak kaydi: sentetik fiksturde notice_text olmaz")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kayit": 1})


# --- G-BUT -------------------------------------------------------------------------------


def g_but(g: FiksturGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    satirlar = g.anchor_satirlari
    beklenen = {b.anchor: b for b in g.beklenen}
    var = {s.metin("anchor"): s for s in satirlar}
    if len(satirlar) != len(beklenen):
        bulgular.append(f"birim sayisi {len(satirlar)}, uretec {len(beklenen)} bekliyor")
    _bulgu(
        bulgular,
        "eksik birim",
        sorted(set(beklenen) - set(var)),
        "uretecin capasi satirlarda yok",
    )
    _bulgu(
        bulgular,
        "fazla birim",
        sorted(set(var) - set(beklenen)),
        "uretecin capalarindan biri degil",
    )
    farkli: list[str] = []
    bos: list[str] = []
    kontrol: list[str] = []
    kanonik_degil: list[str] = []
    yol_hatasi: list[str] = []
    isik = 0
    for capa, satir in var.items():
        metin = satir.metin("text")
        if metin == "" or all(h in " \t\n" for h in metin):
            bos.append(capa)
        if _kontrol_karakteri(metin):
            kontrol.append(capa)
        if kanonik_metin(metin) != metin:
            kanonik_degil.append(capa)
        if ISIK in metin:
            isik += 1
        b = beklenen.get(capa)
        if b is None:
            continue
        if b.text.encode("utf-8") != metin.encode("utf-8"):
            farkli.append(capa)
        yol = satir.veri.get("parent_path")
        if yol != b.parent_path:
            yol_hatasi.append(capa)
    for ad, liste, neden in (
        ("metin", farkli, "uretecin cikisiyla bayt bayt ayni degil"),
        ("bos metin", bos, "metin bos"),
        ("kontrol karakteri", kontrol, "metinde kontrol ya da bicim karakteri var"),
        ("kanonik olmayan metin", kanonik_degil, "kanonik_metin (NFC dahil) metni degistiriyor"),
        ("parent_path", yol_hatasi, "uretecin bolum yoluyla ayni degil"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    if g.slug == KITAP and isik != 1:
        bulgular.append(f"'{ISIK}' sozcugunu iceren paragraf sayisi {isik}, 1 bekleniyor")
    sayilar = {"birim": len(satirlar), "beklenen_birim": len(beklenen), "isik_paragraf": isik}
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: FiksturGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    gecersiz: list[str] = []
    tekrar: list[str] = []
    gorulen: set[str] = set()
    anahtarlar = []
    sira_hatasi: list[str] = []
    aralik_hatasi: list[str] = []
    ozet_hatasi: list[str] = []
    ozet_yanlis: list[str] = []
    sabit_hatasi: list[str] = []
    data_version = f"{g.slug}@{g.kayit.surum}"
    for no, satir in enumerate(g.anchor_satirlari, start=1):
        capa = satir.metin("anchor")
        if capa in gorulen:
            tekrar.append(capa)
        gorulen.add(capa)
        if not capa_ailesine_uyar(g.slug, capa):
            gecersiz.append(capa)
            continue
        anahtarlar.append((sort_key(parse(capa)), capa))
        if satir.veri.get("ord") != no:  # satirlar capa sirasinda, ord 1..N
            sira_hatasi.append(capa)
        aralik = ayet_araligi(capa)
        lo, hi = satir.veri.get("ayah_lo"), satir.veri.get("ayah_hi")
        if (lo, hi) != (aralik if aralik else (None, None)):
            aralik_hatasi.append(capa)
        ozet, metin = satir.metin("content_hash"), satir.metin("text")
        if OZET_DESENI.fullmatch(ozet) is None:
            ozet_hatasi.append(capa)
        elif ozet != content_hash(metin):
            ozet_yanlis.append(capa)
        if (
            satir.metin("kind") != KIND[g.slug]
            or satir.metin("source_id") != g.slug
            or satir.metin("metin_durumu") != METIN_DURUMU
            or satir.metin("role") != ROL
            or satir.metin("data_version") != data_version
        ):
            sabit_hatasi.append(capa)
    siralama = [c for (a, _), (b, c) in pairwise(anahtarlar) if not a < b]
    for ad, liste, neden in (
        ("gecersiz capa", gecersiz, "kanonik degil ya da fiksturun capa ailesinden degil"),
        ("yinelenen capa", tekrar, "capa birden fazla satirda"),
        ("okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor"),
        ("ord", sira_hatasi, "ord okuma sirasinin numarasi (1..N) degil"),
        ("ayah_lo/ayah_hi", aralik_hatasi, "capadan turetilen yari acik aralikla ayni degil"),
        ("content_hash biciminde", ozet_hatasi, "64 haneli kucuk harfli onaltilik degil"),
        ("content_hash", ozet_yanlis, "metnin SHA-256'siyla tutmuyor"),
        (
            "sabit alan",
            sabit_hatasi,
            "kind, source_id, metin_durumu, role ya da data_version yanlis",
        ),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {"capa": len(gorulen), "onceki_run": 0}
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        simdiki = {s.metin("anchor"): s.metin("content_hash") for s in g.anchor_satirlari}
        kayip = sorted(c for c in g.onceki.ozetler if c not in simdiki)
        degisen = sorted(
            c for c, ozet in g.onceki.ozetler.items() if c in simdiki and simdiki[c] != ozet
        )
        sayilar["onceki_capa"] = len(g.onceki.ozetler)
        _bulgu(bulgular, "onceki surumde olup kaybolan capa", kayip, "capa kullanim disi olamaz")
        _bulgu(bulgular, "onceki surumle content_hash farkli", degisen, "metin degismis")
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: FiksturGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(
            f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi:"
            f" {_capalar(vektor.kalan)}"
        )
    if vektor.hizasiz:
        bulgular.append(
            f"tr_wide/tr_stem sozcuk hizasi: {len(vektor.hizasiz)} vektor:"
            f" {_capalar(vektor.hizasiz)}"
        )
    farkli: list[str] = []
    ar_dolu: list[str] = []
    surum: list[str] = []
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        anahtarlar = search_keys(satir.metin("text"))
        beklenen = {
            "tr_narrow": anahtarlar.tr_narrow,
            "tr_wide": anahtarlar.tr_wide,
            "tr_stem": anahtarlar.tr_stem,
        }
        if any(satir.veri.get(alan) != beklenen[alan] for alan in TR_ALANLARI):
            farkli.append(capa)
        if satir.veri.get("ar_norm") is not None:
            ar_dolu.append(capa)
        arama = satir.nesne("provenance").get("arama")
        if not isinstance(arama, dict) or arama.get("normalizer_version") != NORMALIZER_VERSION:
            surum.append(capa)
    for ad, liste, neden in (
        ("arama anahtari", farkli, "metinden search_keys ile uretilen degerle ayni degil"),
        ("ar_norm", ar_dolu, "fiksturde ar_norm bos (null) olmali"),
        ("provenance.arama", surum, "normalizer_version yok ya da bu surumle ayni degil"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {
        "vektor": vektor.toplam,
        "vektor_kalan": len(vektor.kalan),
        "vektor_hizasiz": len(vektor.hizasiz),
        "anahtar_farki": len(farkli),
    }
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[dict[str, Callable[[FiksturGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}
