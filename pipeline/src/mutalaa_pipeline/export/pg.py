"""`export pg`: staged birimleri PostgreSQL'e yukler (Icerik hatti §6, K-39).

Akis: (1) dosya onkosullari (kaynak kaydi, anchor calistirmasi, zincir, QA raporu, satirlar,
bildirim), (2) tek veritabani islemi: advisory kilit, `pipeline_run`, `source` satirlari,
`staging_unit` gecici tablosu, denetimler, iki ifadeli yazim.

G-KAY (dosya tarafi): kaynak kaydi gecerli ve `atif_metni` dolu (`require_sources`); kanonik
kaynakta TOML'daki `notice_text`, dosyadaki bildirim blogu (`notice.txt`) ile bayt bayt ayni
(K-39 madde 6). Uc denetim de cikis 2 verir.

Tanzil (K-39): birimler `onayli` girer; hat var olan satirda yalniz turetilmis sutunlari
(`ar_norm`, `provenance`, `data_version`, `ord`, `ayah_range`, `run_id`, `updated_at`) gunceller.
`metin`, `content_hash`, `metin_durumu`, `status`, `successors`, `rev`, `marks` ve `source_id`
SET listesine girmez. `export pg` parmak izi atlamasi yapmaz (`--force` kabul edilir, etkisizdir).

Kelimeler (A11.2, K-43 madde 3): `tanzil-uthmani` icin anchor calismasinin `words.jsonl`
dosyasi ayni islemde `icerik.quran_word` tablosuna yuklenir. Yukleme upsert'tir ve satir silmez:
var olmayan kelime eklenir; var olan satirin Tanzil sutunlarindan (`surah`, `ayah`, `word`,
`ayah_index`, `text_uthmani`, `norm`, `char_start`, `char_end`, `source_id`, `data_version`) biri
degismisse ya da veritabaninda olup staged'de olmayan bir `source_id` kelimesi varsa islem geri
alinir (cikis 1). QAC sutunlarina (`root_id`, `lemma_id`, `pos`, `features`, `morph_source`)
INSERT'te bile yazilmaz; onlar A17'nindir.

Sentetik fiksturler (A13.6, `export/pg_fikstur.py`): `test-kucuk` ve `test-tefsir-ornek` birimleri
`metin_durumu = 'taslak'` girer (kanonik basvuru degil, K-38 madde 4) ve `tr_narrow`, `tr_wide`,
`tr_stem` ile birlikte yuklenir; `test-ses` birim tasimaz, yalniz `source` satiri yuklenir.

Meal (A16.4, K-49): `elmalili-meal` ve `elmalili-sade-meal` birimleri `taslak` girer; hat meal
biriminin metnine hic yazmaz ve her birim icin bir inceleme kaydi acar (`export/pg_meal.py`).
Tanik kaynagi yuklenmez.

Cikis kodlari: 0 basarili, 1 QA kapisi/ozet farki/eksik capa, 2 girdi ve yapilandirma (kayitsiz
ya da gecersiz kaynak kaydi dahil). Iletilere satir icerigi ve baglanti dizesi yazilmaz; yalniz
capa, sayi, ozet ve alan adi.
"""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Final

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, Q
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse as anchor_parse
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import VeritabaniHatasi, baglan
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export import pg_kelime
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import fikstur as fikstur_uretec
from mutalaa_pipeline.ingest.meal_kaynaklari import MEAL_KAYNAKLARI, meal_mi
from mutalaa_pipeline.lineage import (
    KELIMELER_ADI,
    NOTICE_ADI,
    OZET_DESENI,
    RUN_ID_DESENI,
    UNITS_ADI,
)
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi, RunContext, komut_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import satirlari_oku as staged_satirlari_oku

ANCHOR_ADIMI: Final = "anchor"
INGEST_ADIMI: Final = "ingest"
EXPORT_ADIMI: Final = "export"
ZINCIR_DERINLIGI: Final = 8
ILK_N_CAPA: Final = 5
TARIH_DESENI: Final = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

# `--source` ile birlikte yuklenen birimsiz kaynaklar (K-39 madde 1).
EK_KAYNAKLAR: Final[Mapping[str, tuple[str, ...]]] = {
    "tanzil-uthmani": ("tanzil-simple-clean",),
    "tanzil-ust-veri": (),  # yapi verisi: quran_marker ve page_map (export/pg_yapi.py)
    "sure-adlari-vikipedi": (),  # sure adi adaylari: surah_alias ve review (pg_sure_adlari.py)
    "qac-morfoloji": (),  # A17.3: root, lemma, lemma_dalga, quran_word QAC sutunlari (pg_qac.py)
    "quranwbw-tr": (),  # A17.6: lemma_gloss adaylari ve review (pg_glosses.py)
    "test-kucuk": (),  # sentetik kitap fiksturu (A13.6; pg_fikstur.py)
    "test-tefsir-ornek": (),  # sentetik tefsir fiksturu (A13.6; pg_fikstur.py)
    "test-ses": (),  # sentetik ses fiksturu: yalniz source satiri (A13.6)
    # Iki meal (A16.4; pg_meal.py). Tanik `elmalili-meal-epub` yuklenmez: tabloda yoktur.
    **{slug: () for slug in MEAL_KAYNAKLARI},
}
# Birim degil yapi satiri yukleyen kaynaklar (K-43 madde 3): units.jsonl yerine markers/pages.
YAPI_KAYNAKLARI: Final = frozenset({"tanzil-ust-veri"})
# Sure adi aday satiri yukleyen kaynaklar (K-43 madde 4-5): surah_alias + review, units yok.
SURE_ADI_KAYNAKLARI: Final = frozenset({"sure-adlari-vikipedi"})
# Sentetik fikstur birimleri: `taslak` girer, tr_* arama sutunlariyla (A13.6, pg_fikstur.py).
FIKSTUR_KAYNAKLARI: Final = frozenset(fikstur_uretec.KAYNAKLAR)
# Birimsiz kaynaklar: zincir ve QA raporu aranmaz, yalniz `source` satiri yuklenir (A13.6).
YALNIZ_KAYNAK_KAYNAKLARI: Final = frozenset(fikstur_uretec.YALNIZ_KAYNAK)

# `words.jsonl` zorunlu olan kaynaklar: anchor calismasi kelime dosyasini listelemelidir.
KELIME_KAYNAKLARI: Final = frozenset({"tanzil-uthmani"})
# `quran_word` Tanzil sutunlari (K-43 madde 3); QAC sutunlarina hat hic yazmaz.
KELIME_SUTUNLARI: Final = (
    "anchor",
    "surah",
    "ayah",
    "word",
    "ayah_index",
    "text_uthmani",
    "norm",
    "char_start",
    "char_end",
    "source_id",
    "data_version",
)

UNIT_TURLERI: Final = frozenset(
    {"ayet", "meal", "tefsir", "risale", "hadis", "hadis_ceviri", "kitap"}
)
GEREKLI_ALANLAR: Final = (
    "anchor",
    "kind",
    "ord",
    "ayah_lo",
    "ayah_hi",
    "text",
    "content_hash",
    "metin_durumu",
    "ar_norm",
    "data_version",
    "provenance",
    "source_id",
)
# K-39 madde 3: satir varsa yalniz betimleyici alanlar guncellenir.
BETIMLEYICI_ALANLAR: Final = (
    "baslik",
    "surum",
    "kaynak_url",
    "atif_metni",
    "atif_url",
    "notice_text",
    "alinma_tarihi",
    "dosya_sha256",
)
TURETILMIS_ALANLAR: Final = ("ar_norm", "provenance", "data_version", "ord", "ayah_range")
# K-39 madde 3: satir yoksa TOML'daki butun alanlarla eklenir (alinma ve ozet ham dosyadan).
INSERT_SOURCE: Final = (
    "INSERT INTO icerik.source (slug, tur, baslik, yazar, surum, provider, kaynak_url,"
    " alinma_tarihi, dosya_sha256, baski_bilgisi, atif_metni, atif_url, notice_text, notlar)"
    " VALUES (%(slug)s, %(tur)s::icerik.source_kind, %(baslik)s, %(yazar)s, %(surum)s,"
    " %(provider)s, %(kaynak_url)s, %(alinma_tarihi)s, %(dosya_sha256)s, %(baski_bilgisi)s,"
    " %(atif_metni)s, %(atif_url)s, %(notice_text)s, %(notlar)s)"
)
SELECT_SOURCE: Final = sql.SQL("SELECT {} FROM icerik.source WHERE slug = %s FOR UPDATE").format(
    sql.SQL(", ").join(sql.Identifier(alan) for alan in BETIMLEYICI_ALANLAR)
)

BAGLANTI = Callable[[], psycopg.Connection]


@dataclass(frozen=True)
class Satir:
    """`units.jsonl` satiri; metin yalniz veritabanina gider, iletilere girmez."""

    anchor: str
    kind: str
    ord: int
    ayah_lo: int
    ayah_hi: int
    metin: str
    content_hash: str
    metin_durumu: str
    ar_norm: str | None
    data_version: str
    provenance: dict[str, object]
    source_id: str


@dataclass(frozen=True)
class KelimeSatiri:
    """`words.jsonl` satiri (`quran_word` Tanzil sutunlari); metin yalniz veritabanina gider."""

    anchor: str
    surah: int
    ayah: int
    word: int
    ayah_index: int
    text_uthmani: str
    norm: str
    char_start: int
    char_end: int
    source_id: str
    data_version: str


@dataclass(frozen=True)
class IsaretSatiri:
    """`markers.jsonl` satiri (`quran_marker`)."""

    kind: str
    no: int
    anchor: str
    secde_turu: str | None
    source_id: str
    data_version: str


@dataclass(frozen=True)
class SayfaSatiri:
    """`pages.jsonl` satiri (`page_map`; volume, line ... NULL, centered false)."""

    page: int
    start_anchor: str
    end_anchor: str
    source_id: str
    data_version: str


@dataclass(frozen=True)
class AdaySatiri:
    """`aliases.jsonl` satiri (`surah_alias` adayi); `onerilen` `review.onerilen` alanidir."""

    surah_no: int
    alias: str
    alias_key: str
    kind: str
    risky: bool
    onerilen: dict[str, object]


@dataclass(frozen=True)
class FiksturSatiri:
    """Fikstur `units.jsonl` satiri; `ayah_lo`/`ayah_hi` kitapta None. Metin iletilere girmez."""

    anchor: str
    kind: str
    role: str
    parent_path: str | None
    ord: int
    ayah_lo: int | None
    ayah_hi: int | None
    metin: str
    content_hash: str
    metin_durumu: str
    attrs: dict[str, object]
    tr_narrow: str
    tr_wide: str
    tr_stem: str
    ar_norm: str | None
    data_version: str
    provenance: dict[str, object]
    source_id: str


@dataclass(frozen=True)
class MealSatiri:
    """Meal `units.jsonl` satiri (A16.4); `metin` yalniz veritabanina gider, iletilere girmez.

    `tanik`: capraz tanik skoru nesnesi ya da None; `uyari`: sinir durumu kodlari
    (`provenance.uyari`); ikisi de yalniz `review.onerilen` icindir (unit tablosuna yazilmaz).
    """

    anchor: str
    kind: str
    role: str
    ord: int
    ayah_lo: int
    ayah_hi: int
    metin: str
    content_hash: str
    metin_durumu: str
    attrs: dict[str, object]
    tr_narrow: str
    tr_wide: str
    tr_stem: str
    data_version: str
    provenance: dict[str, object]
    source_id: str
    tanik: dict[str, object] | None
    uyari: tuple[str, ...]


@dataclass(frozen=True)
class ZincirRun:
    run_id: str
    adim: str
    source_id: str
    klasor: Path
    manifest: dict[str, object]


@dataclass
class Hazirlik:
    """Dosya onkosullarinin sonucu (veritabanina dokunmadan)."""

    source_id: str
    kaynak_idleri: tuple[str, ...]
    anchor_run_id: str
    units_yol: str
    units_sha256: str
    satirlar: list[Satir]
    zincir: list[ZincirRun]
    ingest: dict[str, ZincirRun]
    ham: dict[str, list[dict[str, str]]]
    qa_rapor_id: str
    kaynaklar: dict[str, Kaynak]
    bildirimler: dict[str, str | None]
    parmak: str
    manifest: dict[str, object] = field(default_factory=dict)
    kelimeler: list[KelimeSatiri] = field(default_factory=list)
    kelimeler_yol: str | None = None
    kelimeler_sha256: str | None = None
    yapi: bool = False  # True: isaretler ve sayfalar yuklenir (units/quran_word yok)
    isaretler: list[IsaretSatiri] = field(default_factory=list)
    sayfalar: list[SayfaSatiri] = field(default_factory=list)
    sure_adi: bool = False  # True: adaylar yuklenir (surah_alias + review; units yok)
    adaylar: list[AdaySatiri] = field(default_factory=list)
    fikstur: bool = False  # True: fikstur birimleri yuklenir (taslak + tr_*; pg_fikstur.py)
    fikstur_satirlari: list[FiksturSatiri] = field(default_factory=list)
    yalniz_kaynak: bool = False  # True: yalniz source satiri yuklenir (zincir ve birim yok)
    meal: bool = False  # True: taslak meal birimleri ve inceleme kuyrugu (pg_meal.py)
    meal_satirlari: list[MealSatiri] = field(default_factory=list)


# --- yardimcilar -------------------------------------------------------------------------


def _g(deger: str) -> str:
    """Konsol icin guvenli (ASCII) kisa gosterim."""
    return ascii(deger)[1:-1][:64]


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(_g(c) for c in capalar[:ILK_N_CAPA])
    fazla = len(capalar) - ILK_N_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def _manifest_ozet(manifest: Mapping[str, object], ad: str) -> str | None:
    ciktilar = manifest.get("ciktilar")
    if isinstance(ciktilar, list):
        for kayit in ciktilar:
            if isinstance(kayit, dict):
                yol, ozet = kayit.get("yol"), kayit.get("sha256")
                if isinstance(yol, str) and isinstance(ozet, str) and yol.endswith("/" + ad):
                    return ozet
    return None


def _girdi_yollari(manifest: Mapping[str, object]) -> list[tuple[str, str | None]]:
    """Manifestin `girdiler` listesi: (yol, sha256) ciftleri."""
    girdiler = manifest.get("girdiler")
    if not isinstance(girdiler, list):
        return []
    sonuc: list[tuple[str, str | None]] = []
    for kayit in girdiler:
        if isinstance(kayit, dict) and isinstance(kayit.get("yol"), str):
            ozet = kayit.get("sha256")
            sonuc.append((str(kayit["yol"]), ozet if isinstance(ozet, str) else None))
    return sonuc


# --- anchor calistirmasi ve zincir -------------------------------------------------------


def _anchor_calismasi(
    ctx: RunContext, source_id: str, run: str | None
) -> tuple[str, Path, dict[str, object]]:
    klasor = ctx.staged_kaynak_dizini(source_id)
    if run is not None:
        if RUN_ID_DESENI.fullmatch(run) is None:
            raise GirdiHatasi("--run bir UUID degil")
        for kayit in lineage.calismalar(klasor):
            if kayit[0] == run:
                if kayit[2].get("adim") != ANCHOR_ADIMI:
                    raise GirdiHatasi("--run bir anchor calistirmasi degil")
                return kayit
        raise GirdiHatasi("--run icin manifestli anchor calistirmasi yok")
    kayit_son = lineage.son_basarili(klasor, ANCHOR_ADIMI)
    if kayit_son is None:
        raise GirdiHatasi("manifestli anchor calistirmasi yok (once anchor komutu calismali)")
    return kayit_son


def _zincir(ctx: RunContext, anchor_manifest: Mapping[str, object]) -> list[ZincirRun]:
    """Anchor manifestinin `girdiler` yollarindan ust calistirmalari (staged/...) toplar."""
    gorulen: set[str] = set()
    sonuc: list[ZincirRun] = []
    siradaki: list[tuple[Mapping[str, object], int]] = [(anchor_manifest, 0)]
    while siradaki:
        manifest, derinlik = siradaki.pop()
        if derinlik >= ZINCIR_DERINLIGI:
            raise GirdiHatasi("calistirma zinciri cok derin")
        for yol, _ in _girdi_yollari(manifest):
            parcalar = yol.split("/")
            if len(parcalar) != 4 or parcalar[0] != "staged":
                continue
            _, source_id, run_id, _ad = parcalar
            if run_id in gorulen:
                continue
            gorulen.add(run_id)
            klasor = ctx.staged_kaynak_dizini(source_id) / run_id
            ust = lineage.manifest_oku(klasor)
            if ust is None or ust.get("run_id") != run_id:
                raise GirdiHatasi(f"zincirde manifesti olmayan calistirma: {_g(run_id)}")
            adim = ust.get("adim")
            if not isinstance(adim, str):
                raise GirdiHatasi(f"zincirdeki manifestte adim yok: {_g(run_id)}")
            sonuc.append(ZincirRun(run_id, adim, source_id, klasor, ust))
            siradaki.append((ust, derinlik + 1))
    return sorted(sonuc, key=lambda r: r.run_id)


def _zincir_denetle(
    ctx: RunContext, zincir: list[ZincirRun], gerekli: Sequence[str]
) -> tuple[dict[str, ZincirRun], dict[str, list[dict[str, str]]]]:
    """Ingest calistirmalari kaynagin en sonuncusu mu; ham dosyalar yerinde mi."""
    ingest: dict[str, ZincirRun] = {}
    for run in zincir:
        if not lineage.ciktilar_saglam(ctx.veri_kok, run.manifest):
            raise GirdiHatasi(f"zincirdeki calistirmanin ciktilari saglam degil: {_g(run.run_id)}")
        if run.adim != INGEST_ADIMI:
            continue
        if run.source_id in ingest:
            raise GirdiHatasi(f"zincirde {_g(run.source_id)} icin birden fazla ingest var")
        ingest[run.source_id] = run
        son = lineage.son_basarili(ctx.staged_kaynak_dizini(run.source_id), INGEST_ADIMI)
        if son is None or son[0] != run.run_id:
            raise QaKaldi(f"zincirdeki ingest {_g(run.source_id)} icin en son ingest degil")
    for slug in gerekli:
        if slug not in ingest:
            raise GirdiHatasi(f"zincirde {_g(slug)} icin ingest calistirmasi yok")
    ham: dict[str, list[dict[str, str]]] = {}
    for slug, run in ingest.items():
        dosyalar: list[dict[str, str]] = []
        for yol, ozet in _girdi_yollari(run.manifest):
            if not yol.startswith("raw/"):
                continue
            if ozet is None or OZET_DESENI.fullmatch(ozet) is None:
                raise GirdiHatasi(f"ham dosya ozeti gecersiz: {_g(yol)}")
            dosya = ctx.veri_kok / yol
            if not dosya.is_file() or lineage.sha256_dosya(dosya) != ozet:
                raise GirdiHatasi(f"ham dosya yok ya da ozeti tutmuyor: {_g(yol)}")
            dosyalar.append({"yol": yol, "sha256": ozet})
        ham[slug] = dosyalar
    return ingest, ham


# --- QA raporu ---------------------------------------------------------------------------


def _qa_denetle(
    ctx: RunContext,
    source_id: str,
    anchor_run_id: str,
    units_sha: str,
    ek_ozetler: Mapping[str, str] | None = None,
) -> str:
    """Ayni anchor calismasi ve ayni `units_sha256` icin dort kapida `gecti` diyen rapor ister.

    Karar o calismanin EN YENI kararlayici raporundadir (`qa/rapor.py`): kapisi kalan ya da
    tamamlanamayan sonraki bir kosu, daha eski bir `gecti` raporunu gecersiz kilar; basarili bir
    kismi (`--gate`) kosu karari degistirmez.
    """
    return QaRaporlari(ctx.veri_kok).onayla(source_id, anchor_run_id, units_sha, ek_ozetler)


# --- satirlar ----------------------------------------------------------------------------


def _int(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def _satirlari_oku(veri: bytes, source_id: str) -> list[Satir]:
    """`units.jsonl` baytlarini kati bicimde okur; hata iletisi yalniz satir numarasi/alan adi."""
    if not veri or not veri.endswith(b"\n"):
        raise GirdiHatasi("units.jsonl bos ya da son satir LF ile bitmiyor")
    satirlar: list[Satir] = []
    gorulen: set[str] = set()
    for no, ham in enumerate(veri[:-1].split(b"\n"), start=1):

        def hata(neden: str, no: int = no) -> GirdiHatasi:
            return GirdiHatasi(f"units.jsonl satir {no}: {neden}")

        try:
            nesne = kati_json(ham.decode("utf-8"))
        except UnicodeDecodeError:
            raise hata("UTF-8 degil") from None
        except GirdiHatasi:
            raise hata("JSON gecersiz") from None
        if not isinstance(nesne, dict):
            raise hata("nesne degil")
        for alan in GEREKLI_ALANLAR:
            if alan not in nesne:
                raise hata(f"alan eksik: {alan}")
        anchor, kind, text = nesne["anchor"], nesne["kind"], nesne["text"]
        ozet, durum, surum = nesne["content_hash"], nesne["metin_durumu"], nesne["data_version"]
        ar_norm, provenance, kaynak = nesne["ar_norm"], nesne["provenance"], nesne["source_id"]
        sira, lo, hi = _int(nesne["ord"]), _int(nesne["ayah_lo"]), _int(nesne["ayah_hi"])
        if not isinstance(anchor, str):
            raise hata("anchor metin degil")
        try:
            if anchor_format(anchor_parse(anchor)) != anchor:
                raise hata("anchor kanonik degil")
        except AnchorError:
            raise hata("anchor gecersiz") from None
        if anchor in gorulen:
            raise hata("yinelenen anchor")
        gorulen.add(anchor)
        if not isinstance(kind, str) or kind not in UNIT_TURLERI:
            raise hata("kind gecersiz")
        if kaynak != source_id:
            raise hata("source_id --source ile ayni degil")
        if durum != "onayli":
            raise hata("metin_durumu onayli degil")
        if not isinstance(text, str) or text == "" or "\x00" in text:
            raise hata("text bos ya da NUL iceriyor")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError:
            raise hata("text UTF-8 olarak yazilamaz") from None
        if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
            raise hata("content_hash 64 haneli kucuk harfli onaltilik degil")
        if ar_norm is not None and (not isinstance(ar_norm, str) or "\x00" in ar_norm):
            raise hata("ar_norm gecersiz")
        if not isinstance(surum, str) or surum == "":
            raise hata("data_version gecersiz")
        if not isinstance(provenance, dict):
            raise hata("provenance nesne degil")
        if sira is None or lo is None or hi is None or sira < 1 or lo >= hi:
            raise hata("ord ya da ayah_lo/ayah_hi gecersiz")
        satirlar.append(
            Satir(
                anchor=anchor,
                kind=kind,
                ord=sira,
                ayah_lo=lo,
                ayah_hi=hi,
                metin=text,
                content_hash=ozet,
                metin_durumu=durum,
                ar_norm=ar_norm,
                data_version=surum,
                provenance=provenance,
                source_id=source_id,
            )
        )
    return satirlar


def _icerik_ozeti_denetle(satirlar: list[Satir]) -> None:
    """Staged `content_hash` metnin SHA-256'si olmali (hat hatasi: cikis 1)."""
    bozuk = [
        s.anchor for s in satirlar if lineage.sha256_bayt(s.metin.encode("utf-8")) != s.content_hash
    ]
    if bozuk:
        raise QaKaldi(f"staged content_hash metinle tutmuyor ({len(bozuk)}): {_capalar(bozuk)}")


def _kelime_satirlari_oku(
    veri: bytes, source_id: str, birimler: Sequence[Satir]
) -> list[KelimeSatiri]:
    """`words.jsonl` baytlarini kati okur ve `units.jsonl` satirlariyla tutarliligini denetler.

    Bicim hatasi `GirdiHatasi` (cikis 2); birimlerle tutarsizlik hat hatasidir, `QaKaldi`
    (cikis 1). Iletiler yalniz satir numarasi, capa ve alan adi tasir.
    """
    kelimeler: list[KelimeSatiri] = []
    gorulen: set[str] = set()
    for satir in staged_satirlari_oku(veri, KELIMELER_ADI):
        yer = f"{KELIMELER_ADI} satir {satir.no}"
        if set(satir.veri) != set(KELIME_SUTUNLARI):
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        kelime = KelimeSatiri(
            anchor=satir.metin("anchor"),
            surah=satir.sayi("surah"),
            ayah=satir.sayi("ayah"),
            word=satir.sayi("word"),
            ayah_index=satir.sayi("ayah_index"),
            text_uthmani=satir.metin("text_uthmani"),
            norm=satir.metin("norm"),
            char_start=satir.sayi("char_start"),
            char_end=satir.sayi("char_end"),
            source_id=satir.metin("source_id"),
            data_version=satir.metin("data_version"),
        )
        try:
            ref = anchor_parse(kelime.anchor)
            kanonik = anchor_format(ref) == kelime.anchor
        except AnchorError:
            raise GirdiHatasi(f"{yer}: anchor gecersiz") from None
        konum = ref.anchor
        if not kanonik or not isinstance(konum, Q) or konum.ilk is None or konum.son is not None:
            raise GirdiHatasi(f"{yer}: anchor kelime capasi degil")
        if (konum.sure, konum.ayet, konum.ilk) != (kelime.surah, kelime.ayah, kelime.word):
            raise GirdiHatasi(f"{yer}: alanlar capayla tutmuyor")
        if kelime.anchor in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen anchor")
        gorulen.add(kelime.anchor)
        if kelime.source_id != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        for alan, deger in (
            ("text_uthmani", kelime.text_uthmani),
            ("norm", kelime.norm),
            ("data_version", kelime.data_version),
        ):
            if deger == "" or "\x00" in deger:
                raise GirdiHatasi(f"{yer}: {alan} bos ya da NUL iceriyor")
            try:
                deger.encode("utf-8")
            except UnicodeEncodeError:
                raise GirdiHatasi(f"{yer}: {alan} UTF-8 olarak yazilamaz") from None
        if not 0 <= kelime.char_start < kelime.char_end or kelime.ayah_index < 1:
            raise GirdiHatasi(f"{yer}: aralik ya da ayah_index gecersiz")
        kelimeler.append(kelime)
    _kelime_birim_tutarliligi(kelimeler, birimler)
    return kelimeler


def _kelime_birim_tutarliligi(kelimeler: Sequence[KelimeSatiri], birimler: Sequence[Satir]) -> None:
    """Her kelime ayet metninin dilimidir, `ayah_index` `ord`dur, numaralar kesintisizdir."""
    ayetler: dict[tuple[int, int], Satir] = {}
    for birim in birimler:
        konum = anchor_parse(birim.anchor).anchor
        if isinstance(konum, Q) and konum.ilk is None:
            ayetler[(konum.sure, konum.ayet)] = birim
    dilim: list[str] = []
    ayetsiz: list[str] = []
    numara: list[str] = []
    sayac: dict[tuple[int, int], int] = {}
    for kelime in kelimeler:
        ayet = (kelime.surah, kelime.ayah)
        birim_ = ayetler.get(ayet)
        if birim_ is None:
            ayetsiz.append(kelime.anchor)
            continue
        sayac[ayet] = sayac.get(ayet, 0) + 1
        if sayac[ayet] != kelime.word:
            numara.append(kelime.anchor)
        if (
            kelime.ayah_index != birim_.ord
            or birim_.metin[kelime.char_start : kelime.char_end] != kelime.text_uthmani
        ):
            dilim.append(kelime.anchor)
    kelimesiz = [f"q:{sure}:{ayet}" for sure, ayet in ayetler if (sure, ayet) not in sayac]
    for ad, liste in (
        ("kelimenin ayeti units icinde yok", ayetsiz),
        ("kelime ayet metninin dilimi ya da ayah_index degil", dilim),
        ("kelime numarasi ayet icinde kesintisiz degil", numara),
        ("ayetin hic kelimesi yok", kelimesiz),
    ):
        if liste:
            raise QaKaldi(f"{ad} ({len(liste)}): {_capalar(liste)}")


def _kelimeler_hazirla(
    ctx: RunContext,
    source_id: str,
    klasor: Path,
    manifest: Mapping[str, object],
    birimler: Sequence[Satir],
) -> tuple[list[KelimeSatiri], str | None, str | None]:
    """Kelime kaynaklarinda anchor calismasinin `words.jsonl` dosyasini okur (yoksa cikis 2)."""
    if source_id not in KELIME_KAYNAKLARI:
        return [], None, None
    beklenen = _manifest_ozet(manifest, KELIMELER_ADI)
    if beklenen is None:
        raise GirdiHatasi(f"anchor manifestinde {KELIMELER_ADI} yok (once anchor --force)")
    dosya = klasor / KELIMELER_ADI
    try:
        veri = dosya.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{KELIMELER_ADI} okunamadi") from None
    ozet = lineage.sha256_bayt(veri)
    if ozet != beklenen:
        raise GirdiHatasi(f"{KELIMELER_ADI} ozeti manifestle tutmuyor")
    return (
        _kelime_satirlari_oku(veri, source_id, birimler),
        lineage.goreli_yol(ctx.veri_kok, dosya),
        ozet,
    )


# --- hazirlik ----------------------------------------------------------------------------


def _bildirim(ingest: ZincirRun, kaynak: Kaynak) -> str | None:
    """G-KAY bildirim denetimi (K-39 madde 6): `notice.txt` baytlarinin kati UTF-8 cozumu.

    Dosya TOML'daki `notice_text` ile birebir ayni olmali (`rstrip` yok). Kanonik Kur'an
    metninde TOML bildirim tasiyorsa dosya zorunludur: dosya yoksa bayt denetimi sessizce
    atlanmaz. Oteki kaynaklarda ingest bildirim yazmadiysa TOML degeri kullanilir.
    """
    yol = ingest.klasor / NOTICE_ADI
    if not yol.is_file():
        if kaynak.tur is SourceKind.KURAN_METNI and kaynak.notice_text is not None:
            raise GirdiHatasi(f"{_g(kaynak.slug)}: TOML notice_text var ama notice.txt yok")
        return kaynak.notice_text
    try:
        metin = yol.read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{_g(kaynak.slug)}: notice.txt UTF-8 degil") from None
    if kaynak.notice_text != metin:
        raise GirdiHatasi(f"{_g(kaynak.slug)}: notice.txt ile TOML notice_text ayni degil")
    return metin


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler."""
    if (ozel := pg_kelime.hazirla(ctx, source_id, run, ek_kaynaklar)) is not None:  # A17
        return ozel
    if source_id in YAPI_KAYNAKLARI:
        from mutalaa_pipeline.export import pg_yapi

        return pg_yapi.hazirla(ctx, source_id, run, ek_kaynaklar)
    if source_id in SURE_ADI_KAYNAKLARI:
        from mutalaa_pipeline.export import pg_sure_adlari

        return pg_sure_adlari.hazirla(ctx, source_id, run, ek_kaynaklar)
    if meal_mi(source_id):
        from mutalaa_pipeline.export import pg_meal

        return pg_meal.hazirla(ctx, source_id, run, ek_kaynaklar)
    if source_id in FIKSTUR_KAYNAKLARI or source_id in YALNIZ_KAYNAK_KAYNAKLARI:
        from mutalaa_pipeline.export import pg_fikstur

        if source_id in YALNIZ_KAYNAK_KAYNAKLARI:
            return pg_fikstur.hazirla_yalniz_kaynak(ctx, source_id, run, ek_kaynaklar)
        return pg_fikstur.hazirla(ctx, source_id, run, ek_kaynaklar)
    kaynak_idleri = (source_id, *ek_kaynaklar)
    # G-KAY: kayit gecerli ve atif_metni dolu; kayitsiz ya da gecersiz kayitta cikis 2.
    kaynaklar = ctx.require_sources(kaynak_idleri)
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    units_dosya = klasor / UNITS_ADI
    units_bayt = units_dosya.read_bytes()
    units_sha = lineage.sha256_bayt(units_bayt)
    if _manifest_ozet(manifest, UNITS_ADI) != units_sha:
        raise GirdiHatasi("units.jsonl ozeti manifestle tutmuyor")
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, units_sha)
    satirlar = _satirlari_oku(units_bayt, source_id)
    _icerik_ozeti_denetle(satirlar)
    kelimeler, kelimeler_yol, kelimeler_sha = _kelimeler_hazirla(
        ctx, source_id, klasor, manifest, satirlar
    )
    # G-KAY: TOML notice_text dosyadaki bildirimle bayt bayt ayni; farkliysa cikis 2.
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    units_yol = lineage.goreli_yol(ctx.veri_kok, units_dosya)
    girdiler = [lineage.Girdi(units_yol, units_sha, anchor_run_id)]
    if kelimeler_yol is not None and kelimeler_sha is not None:
        girdiler.append(lineage.Girdi(kelimeler_yol, kelimeler_sha, anchor_run_id))
    for slug in kaynak_idleri:
        girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[slug]]
    parmak = ctx.parmak_izi(girdiler)
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=units_yol,
        units_sha256=units_sha,
        satirlar=satirlar,
        zincir=zincir,
        ingest=ingest,
        ham=ham,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=parmak,
        kelimeler=kelimeler,
        kelimeler_yol=kelimeler_yol,
        kelimeler_sha256=kelimeler_sha,
    )


def _manifest_kur(h: Hazirlik) -> dict[str, object]:
    if h.yalniz_kaynak:  # zincir, QA raporu ve ham dosya yok
        return {"source_id": h.source_id, "kaynaklar": list(h.kaynak_idleri), "yalniz_kaynak": True}
    kelime: dict[str, object] = (
        {"words_sha256": h.kelimeler_sha256} if h.kelimeler_sha256 is not None else {}
    )
    return {
        "source_id": h.source_id,
        "kaynaklar": list(h.kaynak_idleri),
        "anchor_run_id": h.anchor_run_id,
        "units_sha256": h.units_sha256,
        **kelime,
        "qa_rapor": h.qa_rapor_id,
        "zincir": [
            {
                "run_id": r.run_id,
                "adim": r.adim,
                "source_id": r.source_id,
                "units_sha256": _manifest_ozet(r.manifest, UNITS_ADI),
            }
            for r in h.zincir
        ],
        "ham_dosyalar": [
            {"source_id": slug, "yol": d["yol"], "sha256": d["sha256"]}
            for slug in h.kaynak_idleri
            for d in h.ham[slug]
        ],
    }


# --- veritabani --------------------------------------------------------------------------


def _alinma(ham: Sequence[Mapping[str, str]]) -> tuple[date | None, str | None]:
    """Tek ham dosyadan (alinma tarihi, dosya SHA-256); tarih `raw/{kaynak}/{YYYY-AA-GG}/`."""
    if len(ham) != 1:
        return None, None
    parcalar = ham[0]["yol"].split("/")
    tarih: date | None = None
    if len(parcalar) >= 4 and TARIH_DESENI.fullmatch(parcalar[2]):
        try:
            tarih = date.fromisoformat(parcalar[2])
        except ValueError:
            tarih = None
    return tarih, ham[0]["sha256"]


def _istenen(kaynak: Kaynak, h: Hazirlik) -> dict[str, object]:
    """Betimleyici alanlarin istenen degerleri (`BETIMLEYICI_ALANLAR` sirasinda)."""
    alinma, dosya_sha = _alinma(h.ham[kaynak.slug])
    return {
        "baslik": kaynak.baslik,
        "surum": kaynak.surum,
        "kaynak_url": kaynak.kaynak_url,
        "atif_metni": kaynak.atif_metni,
        "atif_url": kaynak.atif_url,
        "notice_text": h.bildirimler[kaynak.slug],
        "alinma_tarihi": alinma,
        "dosya_sha256": dosya_sha,
    }


def _ekleme_parametreleri(kaynak: Kaynak, istenen: Mapping[str, object]) -> dict[str, object]:
    """`INSERT_SOURCE` parametreleri: betimleyici alanlar ve yalniz ilk eklemede yazilanlar."""
    return {
        **istenen,
        "slug": kaynak.slug,
        "tur": kaynak.tur.value,
        "yazar": kaynak.yazar,
        "provider": kaynak.provider,
        "baski_bilgisi": (
            Jsonb(kaynak.baski_bilgisi) if kaynak.baski_bilgisi is not None else None
        ),
        "notlar": kaynak.notlar,
    }


def _source_satirlari(conn: psycopg.Connection, h: Hazirlik) -> dict[str, int]:
    """K-39 madde 3: yoksa butun TOML alanlariyla ekler, varsa betimleyici alanlari gunceller.

    Betimleyici alan yalniz farkliysa yazilir. Var olan satirda oteki sutunlara (`tur`, `yazar`,
    `provider`, `baski_bilgisi`, `notlar`) hat dokunmaz.
    """
    sayac = {"kaynak_eklenen": 0, "kaynak_guncellenen": 0, "kaynak_degismeyen": 0}
    mevcutlar: dict[str, dict[str, object] | None] = {}
    with conn.cursor(row_factory=dict_row) as imlec:
        for slug in h.kaynak_idleri:
            imlec.execute(SELECT_SOURCE, (slug,))
            mevcutlar[slug] = imlec.fetchone()
    for slug in h.kaynak_idleri:
        kaynak = h.kaynaklar[slug]
        istenen = _istenen(kaynak, h)
        if istenen["surum"] is None:
            raise GirdiHatasi(f"kaynak {_g(slug)}: surum cozulemedi (TOML surum alani yok)")
        mevcut = mevcutlar[slug]
        if mevcut is None:
            conn.execute(INSERT_SOURCE, _ekleme_parametreleri(kaynak, istenen))
            sayac["kaynak_eklenen"] += 1
            continue
        degisen: dict[str, object] = {}
        for alan in BETIMLEYICI_ALANLAR:
            deger = istenen[alan]
            if alan in ("alinma_tarihi", "dosya_sha256") and deger is None:
                continue  # ham dosyadan cozulemeyen turetilmis deger veritabanini silmez
            if mevcut[alan] != deger:
                degisen[alan] = deger
        if not degisen:
            sayac["kaynak_degismeyen"] += 1
            continue
        atamalar = sql.SQL(", ").join(
            sql.SQL("{} = {}").format(sql.Identifier(alan), sql.Placeholder(alan))
            for alan in degisen
        )
        conn.execute(
            sql.SQL("UPDATE icerik.source SET {}, updated_at = now() WHERE slug = {}").format(
                atamalar, sql.Placeholder("_slug")
            ),
            {**degisen, "_slug": slug},
        )
        sayac["kaynak_guncellenen"] += 1
    return sayac


STAGING_OLUSTUR: Final = (
    'CREATE TEMP TABLE staging_unit (anchor text COLLATE "C", kind icerik.unit_kind,'
    " ord bigint, ayah_range int4range, metin text, content_hash char(64),"
    " metin_durumu icerik.metin_durumu, ar_norm text, data_version text, provenance jsonb,"
    " source_id text) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_unit (anchor, kind, ord, ayah_range, metin, content_hash,"
    " metin_durumu, ar_norm, data_version, provenance, source_id) FROM STDIN"
)


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[Satir]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_unit")
    conn.execute(STAGING_OLUSTUR)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for s in satirlar:
            kopya.write_row(
                (
                    s.anchor,
                    s.kind,
                    s.ord,
                    Range(s.ayah_lo, s.ayah_hi, "[)"),
                    s.metin,
                    s.content_hash,
                    s.metin_durumu,
                    s.ar_norm,
                    s.data_version,
                    Jsonb(s.provenance),
                    s.source_id,
                )
            )


def _capa_listesi(
    conn: psycopg.Connection, sorgu: str, parametre: Sequence[object] = ()
) -> list[str]:
    return [str(satir[0]) for satir in conn.execute(sql.SQL(sorgu), parametre).fetchall()]


def _denetimler(conn: psycopg.Connection, source_id: str) -> None:
    """Isleme ozgu denetimler; her biri ilk capalari iletiye yazar."""
    baska = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_unit s ON s.anchor = u.anchor"
        " WHERE u.source_id <> s.source_id ORDER BY u.anchor",
    )
    if baska:
        raise GirdiHatasi(f"capa baska bir source_id altinda ({len(baska)}): {_capalar(baska)}")
    fark = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_unit s ON s.anchor = u.anchor"
        " WHERE u.content_hash <> s.content_hash OR u.metin IS DISTINCT FROM s.metin"
        " ORDER BY u.anchor",
    )
    if fark:
        raise QaKaldi(f"var olan capada content_hash/metin farki ({len(fark)}): {_capalar(fark)}")
    eksik = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u WHERE u.source_id = %s AND NOT EXISTS"
        " (SELECT 1 FROM pg_temp.staging_unit s WHERE s.anchor = u.anchor) ORDER BY u.anchor",
        (source_id,),
    )
    if eksik:
        raise QaKaldi(
            f"onceki yuklemedeki capa staged icinde yok ({len(eksik)}): {_capalar(eksik)}"
        )
    bozuk = _capa_listesi(
        conn,
        "SELECT anchor FROM pg_temp.staging_unit"
        " WHERE content_hash::text <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')"
        " ORDER BY anchor",
    )
    if bozuk:
        raise QaKaldi(f"content_hash metnin SHA-256'si degil ({len(bozuk)}): {_capalar(bozuk)}")


INSERT_UNIT: Final = (
    "INSERT INTO icerik.unit (anchor, kind, source_id, ord, ayah_range, metin, content_hash,"
    " metin_durumu, ar_norm, data_version, provenance, run_id)"
    " SELECT s.anchor, s.kind, s.source_id, s.ord, s.ayah_range, s.metin, s.content_hash,"
    " s.metin_durumu, s.ar_norm, s.data_version, s.provenance, %s::uuid"
    " FROM pg_temp.staging_unit s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.anchor)"
    " ORDER BY s.ord"
)
# metin, content_hash, metin_durumu, status, successors, rev, marks, source_id SET listesinde yok.
UPDATE_UNIT: Final = (
    "UPDATE icerik.unit u SET ar_norm = s.ar_norm, provenance = s.provenance,"
    " data_version = s.data_version, ord = s.ord, ayah_range = s.ayah_range,"
    " run_id = %s::uuid, updated_at = now()"
    " FROM pg_temp.staging_unit s"
    " WHERE u.anchor = s.anchor AND u.source_id = s.source_id AND u.content_hash = s.content_hash"
    " AND (u.ar_norm, u.provenance, u.data_version, u.ord, u.ayah_range)"
    " IS DISTINCT FROM (s.ar_norm, s.provenance, s.data_version, s.ord, s.ayah_range)"
)


KELIME_STAGING_OLUSTUR: Final = (
    'CREATE TEMP TABLE staging_word (anchor text COLLATE "C", surah smallint, ayah smallint,'
    " word smallint, ayah_index smallint, text_uthmani text, norm text, char_start integer,"
    " char_end integer, source_id text, data_version text) ON COMMIT DROP"
)
KELIME_STAGING_COPY: Final = (
    "COPY pg_temp.staging_word (" + ", ".join(KELIME_SUTUNLARI) + ") FROM STDIN"
)
# Yalniz Tanzil sutunlari adlandirilir; root_id, lemma_id, pos, features, morph_source yazilmaz.
INSERT_KELIME: Final = (
    "INSERT INTO icerik.quran_word ("
    + ", ".join(KELIME_SUTUNLARI)
    + ") SELECT "
    + ", ".join(f"s.{alan}" for alan in KELIME_SUTUNLARI)
    + " FROM pg_temp.staging_word s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.quran_word w WHERE w.anchor = s.anchor)"
    " ORDER BY s.ayah_index, s.word"
)
FARKLI_KELIME: Final = (
    "SELECT w.anchor FROM icerik.quran_word w JOIN pg_temp.staging_word s ON s.anchor = w.anchor"
    " WHERE ("
    + ", ".join(f"w.{alan}" for alan in KELIME_SUTUNLARI[1:])
    + ") IS DISTINCT FROM ("
    + ", ".join(f"s.{alan}" for alan in KELIME_SUTUNLARI[1:])
    + ") ORDER BY w.anchor"
)
EKSIK_KELIME: Final = (
    "SELECT w.anchor FROM icerik.quran_word w WHERE w.source_id = %s AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_word s WHERE s.anchor = w.anchor) ORDER BY w.anchor"
)


def _kelimeleri_yukle(conn: psycopg.Connection, h: Hazirlik) -> dict[str, int]:
    """`quran_word` upsert'i (K-43 madde 3): ekler; degisen ya da eksik satirda `QaKaldi`.

    Tanzil sutunlarindan biri degismis bir satir ya da staged'de olmayan bir `source_id` kelimesi
    islemi geri aldirir (cikis 1). Satir silinmez, QAC sutunlarina yazilmaz.
    """
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_word")
    conn.execute(KELIME_STAGING_OLUSTUR)
    with conn.cursor() as imlec, imlec.copy(KELIME_STAGING_COPY) as kopya:
        for k in h.kelimeler:
            kopya.write_row(
                (
                    k.anchor,
                    k.surah,
                    k.ayah,
                    k.word,
                    k.ayah_index,
                    k.text_uthmani,
                    k.norm,
                    k.char_start,
                    k.char_end,
                    k.source_id,
                    k.data_version,
                )
            )
    farkli = _capa_listesi(conn, FARKLI_KELIME)
    if farkli:
        raise QaKaldi(
            f"var olan kelimenin Tanzil sutunu degismis ({len(farkli)}): {_capalar(farkli)}"
        )
    eksik = _capa_listesi(conn, EKSIK_KELIME, (h.source_id,))
    if eksik:
        raise QaKaldi(f"veritabanindaki kelime staged icinde yok ({len(eksik)}): {_capalar(eksik)}")
    eklenen = conn.execute(INSERT_KELIME).rowcount
    return {
        "kelime_staging": len(h.kelimeler),
        "kelime_eklenen": eklenen,
        "kelime_degismeyen": len(h.kelimeler) - eklenen,
    }


def _pipeline_run_yaz(
    conn: psycopg.Connection,
    ctx: RunContext,
    h: Hazirlik,
    durum: str,
    manifest: Mapping[str, object],
) -> None:
    bitis = ctx.saat() if durum != "calisiyor" else None
    conn.execute(
        "INSERT INTO icerik.pipeline_run (run_id, komut, git_commit, parmak_izi, baslangic,"
        " bitis, durum, manifest) VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s)",
        (
            ctx.run_id,
            ctx.komut,
            ctx.git().commit or "bilinmiyor",
            h.parmak,
            ctx.baslangic,
            bitis,
            durum,
            Jsonb(manifest),
        ),
    )


def _yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Tek islemin govdesi (cagiran `conn.transaction()` icinde)."""
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('mutalaa:' || %s::text))", (h.source_id,))
    manifest = _manifest_kur(h)
    _pipeline_run_yaz(conn, ctx, h, "calisiyor", manifest)
    sayilar = _source_satirlari(conn, h)
    if pg_kelime.ozel_mi(h):  # A17: qac-morfoloji ve quranwbw-tr (kaynak satiri yukarida yazildi)
        sayilar.update(pg_kelime.yukle(conn, ctx, h))
    elif h.yapi:
        from mutalaa_pipeline.export import pg_yapi

        sayilar.update(pg_yapi.yukle(conn, h))
    elif h.sure_adi:
        from mutalaa_pipeline.export import pg_sure_adlari

        sayilar.update(pg_sure_adlari.yukle(conn, h))
    elif h.fikstur:
        from mutalaa_pipeline.export import pg_fikstur

        sayilar.update(pg_fikstur.yukle(conn, ctx, h))
    elif h.meal:
        from mutalaa_pipeline.export import pg_meal

        sayilar.update(pg_meal.yukle(conn, ctx, h))
    elif h.yalniz_kaynak:
        pass  # yalniz `source` satiri (yukarida yazildi): unit, review ve xref yok
    else:
        _staging_yukle(conn, h.satirlar)
        _denetimler(conn, h.source_id)
        eklenen = conn.execute(INSERT_UNIT, (ctx.run_id,)).rowcount
        guncellenen = conn.execute(UPDATE_UNIT, (ctx.run_id,)).rowcount
        sayilar.update(
            staging=len(h.satirlar),
            eklenen=eklenen,
            guncellenen=guncellenen,
            degismeyen=len(h.satirlar) - eklenen - guncellenen,
        )
        if h.kelimeler_sha256 is not None:
            sayilar.update(_kelimeleri_yukle(conn, h))
    conn.execute(
        "UPDATE icerik.pipeline_run SET durum = 'basarili', bitis = %s, manifest = %s"
        " WHERE run_id = %s::uuid",
        (ctx.saat(), Jsonb({**manifest, "sayilar": sayilar}), ctx.run_id),
    )
    return sayilar


def _basarisiz_yaz(
    conn: psycopg.Connection, ctx: RunContext, h: Hazirlik, hata: BaseException
) -> None:
    """Geri alinan isin yerine `basarisiz` satiri; dis islem yoksa kendi kisa islemini acar.

    `conn.transaction()` bos baglantida gercek islem, dis islem varsa savepoint olur. Yazim
    hatasi asil hatayi ortmez.
    """
    manifest = {**_manifest_kur(h), "hata_turu": type(hata).__name__}
    try:
        with conn.transaction():
            _pipeline_run_yaz(conn, ctx, h, "basarisiz", manifest)
    except Exception:
        ctx.uyar("basarisiz pipeline_run satiri yazilamadi")


def export_pg(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Ana is: `conn.transaction()` icinde yukleme; `--dry-run` `Rollback` ile hicbir sey yazmaz.

    Hata: ic blok geri alinir, `basarisiz` satiri yazilir, hata aynen yukari firlatilir
    (psycopg hatalari yalniz tur adiyla `VeritabaniHatasi` olur).
    """
    try:
        with conn.transaction():
            sayilar = _yukle(conn, ctx, h)
            if ctx.dry_run:
                raise psycopg.Rollback()
    except psycopg.Error as hata:
        _basarisiz_yaz(conn, ctx, h, hata)
        durum = getattr(hata, "sqlstate", None)
        raise VeritabaniHatasi(
            f"veritabani hatasi ({type(hata).__name__}, sqlstate {durum})"
        ) from None
    except Exception as hata:
        _basarisiz_yaz(conn, ctx, h, hata)
        raise
    return sayilar


# --- komut -------------------------------------------------------------------------------


def komut_export_pg(
    ayarlar: Ayarlar,
    *,
    depo_kok: Path,
    source: str,
    run: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    kayit: Mapping[str, tuple[str, ...]] | None = None,
    baglanti: BAGLANTI | None = None,
) -> int:
    """`export pg` komutu; cikis kodunu dondurur (rapor `data/reports/{run_id}.json`).

    `baglanti` testler icindir: verilirse baglanti disaridan gelir ve kapatilmaz.
    """
    tablo = kayit if kayit is not None else EK_KAYNAKLAR
    ek = tablo.get(source)
    ctx = RunContext.olustur(
        ayarlar,
        komut="export pg",
        adim=EXPORT_ADIMI,
        depo_kok=depo_kok,
        kaynaklar=(source, *(ek or ())),
        parametreler={"source": source},
        force=force,
        dry_run=dry_run,
    )

    def govde(c: RunContext) -> int:
        if ek is None:
            raise GirdiHatasi("tanimsiz kaynak: export pg icin kayit yok")
        if force:
            c.uyar("--force export pg icin etkisiz: parmak izi atlamasi yok (K-39 madde 8)")
        h = hazirla(c, source, run, ek)
        kapat = baglanti is None
        conn = baglanti() if baglanti is not None else baglan(ayarlar, autocommit=True)
        try:
            sayilar = export_pg(conn, c, h)
        finally:
            if kapat:
                conn.close()
        for ad, deger in sayilar.items():
            c.sayi(ad, deger)
        c.gunluk.bilgi("export_pg_bitti", **sayilar)
        return 0

    return komut_calistir(ctx, govde)
