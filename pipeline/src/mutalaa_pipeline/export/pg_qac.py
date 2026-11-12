"""`export pg --source qac-morfoloji`: `root`, `lemma`, `lemma_dalga` ve `quran_word` QAC sutunlari
(A17.3, K-50 madde 3 ve 4).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit); dosya
tarafi: kaynak kaydi (G-KAY), son `anchor` (`enrich morphology`) calismasi (`words.jsonl`,
`lemmas.jsonl`, `roots.jsonl`, `waves.jsonl`), zincir (anchor -> ingest qac ve anchor
tanzil-ust-veri -> ...), QA raporu (G-KAY, G-BUT, G-CAP; `units_sha256` = `words.jsonl` ozeti) ve
satirlarin kati okunmasi. Tek islemde sirasiyla: `source` satiri (`export/pg.py` ortak kodu;
`dosya_sha256` ve `alinma_tarihi` tek dosyali kaynak kuraliyla), `root`, `lemma`, `lemma_dalga`,
sonra `quran_word` QAC sutunlarinin UPDATE'i.

YAZMA KURALLARI

* Kimlik kalicidir (`enrich.morphology.kimlik_ata`): var olan `(lang = 'ar', qac_ref)` ya da
  `letters_bw` satirinin kimligi korunur; yeni satira tablodaki en buyuk kimligin ustunden, staged
  `ilk_gecis` sirasiyla verilir. Bos veritabaninda kimlikler ilk gecis sirasiyla 1'den baslar.
* `lemma`: `status = 'onayli'`, `origin = 'qac'`, `source_id = 'qac-morfoloji'`; `root`: durum ve
  koken sutunu yoktur, `source_id = 'qac-morfoloji'`. `review` ACILMAZ (K-50 madde 4).
* Sonraki yuklemelerde YALNIZ turetilmis sutunlar guncellenir: `root`ta `occurrences`,
  `ayah_count`, `idf_q`, `data_version`; `lemma`da `occurrences` ve `data_version` (`lemma`da
  `ayah_count`, `idf_q` ve ARAPCA satirda `freq` sutunu yoktur / bos kalir). `text`, `text_clean`,
  `qac_ref`, `letters`, `letters_bw`, `status`, `origin`, `source_id` ve bagli kok degismisse ya da
  QAC satiri staged'de yoksa islem geri alinir (`QaKaldi`, cikis 1).
* `lemma_dalga`: dalga staged `waves.jsonl`'dan, `sira` VERITABANI KIMLIKLERIYLE hesaplanir (dalga
  icinde kokun toplam gecisine gore azalan, esitlikte `root.id`; koksuzler sonda; kok icinde lemma
  gecisine gore azalan, esitlikte `lemma.id`). Bos veritabaninda sonuc staged `sira` ile aynidir.
* `quran_word`: satir eklenmez ve silinmez; staged kelimesi veritabaninda yoksa, veritabanindaki
  kelime staged'de yoksa, `(surah, ayah, word)` farkliysa ya da `morph_source` baska bir kaynaga
  aitse islem geri alinir (cikis 1). Yalniz `root_id`, `lemma_id`, `pos`, `features` ve
  `morph_source` yazilir; Tanzil sutunlarina, `source_id` ve `data_version`a dokunulmaz.
* Yukleme sonrasi (ayni islem) iki degismez sorgulanir: her `quran_word.lemma_id` ve `root_id`
  staged govde LEM ve ROOT'una karsilik gelir (%100) ve Fatiha ile 30. cuz lemmalarinin hepsi
  `dalga IN (0, 1)`'dedir; aksi halde islem geri alinir.
* `--dry-run` hicbir sey yazmaz (islem geri alinir). Ikinci kosu 0 degisiklik verir.

Iletiler yalniz sayi, kimlik ve capa (`qac_ref`, `letters_bw`) tasir; Arapca metin yazilmaz.
Sayaclar: `kok_*`, `lemma_*`, `dalga_*`, `kelime_*` (`staging`, `eklenen`, `guncellenen`,
`degismeyen`).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, Q
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse as anchor_parse
from mutalaa_pipeline.enrich.morphology import kimlik_ata
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    _anchor_calismasi,
    _bildirim,
    _capa_listesi,
    _capalar,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.ingest.qac import KAYNAK
from mutalaa_pipeline.lineage import DALGALAR_ADI, KELIMELER_ADI, KOKLER_ADI, LEMMALAR_ADI
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_oku

KELIME_KAYNAGI: Final = "tanzil-uthmani"
LEMMA_ORIGIN: Final = "qac"
LEMMA_STATUS: Final = "onayli"
SON_DALGA: Final = 4
IDF_DESENI: Final = re.compile(r"[0-9]+\.[0-9]{9}")
KELIME_ALANLARI: Final = frozenset(
    {
        "anchor",
        "surah",
        "ayah",
        "word",
        "pos",
        "lemma_qac_ref",
        "root_letters_bw",
        "features",
        "segment_sayisi",
        "govde_sayisi",
        "source_id",
        "data_version",
    }
)
LEMMA_ALANLARI: Final = frozenset(
    {
        "qac_ref",
        "ilk_gecis",
        "text",
        "text_clean",
        "ayirt_no",
        "root_letters_bw",
        "occurrences",
        "ayah_count",
        "idf_q",
        "source_id",
        "data_version",
    }
)
KOK_ALANLARI: Final = frozenset(
    {
        "letters_bw",
        "ilk_gecis",
        "letters",
        "occurrences",
        "ayah_count",
        "idf_q",
        "source_id",
        "data_version",
    }
)
DALGA_ALANLARI: Final = frozenset(
    {"qac_ref", "dalga", "sira", "etiket", "fatiha", "cuz30", "zorla", "source_id", "data_version"}
)


# --- satir tipleri ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KokSatiri:
    letters_bw: str
    ilk_gecis: int
    letters: str
    occurrences: int
    ayah_count: int
    idf_q: float
    data_version: str


@dataclass(frozen=True)
class LemmaSatiri:
    qac_ref: str
    ilk_gecis: int
    text: str
    text_clean: str
    root_letters_bw: str | None
    occurrences: int
    data_version: str


@dataclass(frozen=True)
class DalgaSatiri:
    qac_ref: str
    dalga: int
    data_version: str


@dataclass(frozen=True)
class QacKelimesi:
    anchor: str
    surah: int
    ayah: int
    word: int
    pos: str
    lemma_qac_ref: str | None
    root_letters_bw: str | None
    features: dict[str, object]


@dataclass
class QacHazirlik(Hazirlik):
    """`Hazirlik` + QAC staged satirlari (veritabanina yazilacak olanlar)."""

    kokler: list[KokSatiri] = field(default_factory=list)
    lemmalar: list[LemmaSatiri] = field(default_factory=list)
    dalgalar: list[DalgaSatiri] = field(default_factory=list)
    qac_kelimeler: list[QacKelimesi] = field(default_factory=list)
    cuz30: tuple[int, int] = (0, 0)  # 30. cuzun baslangic ayeti (sure, ayet)
    data_version: str = ""


# --- satirlari okuma (kati) ------------------------------------------------------------------


def _alan_kumesi(satir: Satir, beklenen: frozenset[str]) -> None:
    if set(satir.veri) != beklenen:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: alan kumesi beklenen degil")


def _bos_degil(satir: Satir, alan: str) -> str:
    deger = satir.metin(alan)
    if deger == "" or "\x00" in deger:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: {alan} bos ya da NUL iceriyor")
    return deger


def _bos_ya_da_metin(satir: Satir, alan: str) -> str | None:
    deger = satir.veri.get(alan)
    if deger is None:
        return None
    return _bos_degil(satir, alan)


def _pozitif(satir: Satir, alan: str) -> int:
    deger = satir.sayi(alan)
    if deger < 1:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: {alan} 1'den kucuk")
    return deger


def _sabitler(satir: Satir, surum: str) -> str:
    if satir.metin("source_id") != KAYNAK:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: source_id {KAYNAK} degil")
    veri_surumu = _bos_degil(satir, "data_version")
    if surum and veri_surumu != surum:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: data_version satirlar arasinda farkli")
    return veri_surumu


def _idf(satir: Satir) -> float:
    deger = satir.metin("idf_q")
    if IDF_DESENI.fullmatch(deger) is None:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: idf_q dokuz ondalikli metin degil")
    return float(deger)


def kok_satirlarini_oku(veri: bytes) -> list[KokSatiri]:
    satirlar: list[KokSatiri] = []
    gorulen: set[str] = set()
    letters: set[str] = set()
    surum = ""
    for s in satirlari_oku(veri, KOKLER_ADI):
        _alan_kumesi(s, KOK_ALANLARI)
        surum = _sabitler(s, surum)
        bw, harfler = _bos_degil(s, "letters_bw"), _bos_degil(s, "letters")
        if bw in gorulen or harfler in letters:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: yinelenen letters_bw ya da letters")
        gorulen.add(bw)
        letters.add(harfler)
        sayi, ayet = _pozitif(s, "occurrences"), _pozitif(s, "ayah_count")
        satirlar.append(
            KokSatiri(bw, _pozitif(s, "ilk_gecis"), harfler, sayi, ayet, _idf(s), surum)
        )
    if not satirlar:
        raise GirdiHatasi(f"{KOKLER_ADI} bos")
    _ilk_gecisler([k.ilk_gecis for k in satirlar], KOKLER_ADI)
    return satirlar


def lemma_satirlarini_oku(veri: bytes) -> list[LemmaSatiri]:
    satirlar: list[LemmaSatiri] = []
    gorulen: set[str] = set()
    surum = ""
    for s in satirlari_oku(veri, LEMMALAR_ADI):
        _alan_kumesi(s, LEMMA_ALANLARI)
        surum = _sabitler(s, surum)
        ref = _bos_degil(s, "qac_ref")
        if ref in gorulen:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: yinelenen qac_ref")
        gorulen.add(ref)
        _pozitif(s, "ayah_count")
        _idf(s)
        satirlar.append(
            LemmaSatiri(
                ref,
                _pozitif(s, "ilk_gecis"),
                _bos_degil(s, "text"),
                _bos_degil(s, "text_clean"),
                _bos_ya_da_metin(s, "root_letters_bw"),
                _pozitif(s, "occurrences"),
                surum,
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{LEMMALAR_ADI} bos")
    _ilk_gecisler([k.ilk_gecis for k in satirlar], LEMMALAR_ADI)
    return satirlar


def _ilk_gecisler(degerler: Sequence[int], ad: str) -> None:
    if len(set(degerler)) != len(degerler):
        raise GirdiHatasi(f"{ad}: ilk_gecis tekil degil")


def dalga_satirlarini_oku(veri: bytes) -> list[DalgaSatiri]:
    satirlar: list[DalgaSatiri] = []
    gorulen: set[str] = set()
    surum = ""
    for s in satirlari_oku(veri, DALGALAR_ADI):
        _alan_kumesi(s, DALGA_ALANLARI)
        surum = _sabitler(s, surum)
        ref = _bos_degil(s, "qac_ref")
        if ref in gorulen:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: yinelenen qac_ref")
        gorulen.add(ref)
        dalga = s.sayi("dalga")
        if not 0 <= dalga <= SON_DALGA:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: dalga 0..{SON_DALGA} disinda")
        _pozitif(s, "sira")
        satirlar.append(DalgaSatiri(ref, dalga, surum))
    if not satirlar:
        raise GirdiHatasi(f"{DALGALAR_ADI} bos")
    return satirlar


def kelime_satirlarini_oku(veri: bytes) -> list[QacKelimesi]:
    satirlar: list[QacKelimesi] = []
    gorulen: set[str] = set()
    for s in satirlari_oku(veri, KELIMELER_ADI):
        _alan_kumesi(s, KELIME_ALANLARI)
        _sabitler(s, "")
        capa = s.metin("anchor")
        try:
            ref = anchor_parse(capa)
            kanonik = anchor_format(ref) == capa
        except AnchorError:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: anchor gecersiz") from None
        kok = ref.anchor
        if (
            not kanonik
            or ref.span is not None
            or not isinstance(kok, Q)
            or kok.ilk is None
            or kok.son is not None
        ):
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: anchor kanonik kelime capasi degil")
        sure, ayet, kelime = s.sayi("surah"), s.sayi("ayah"), s.sayi("word")
        if (sure, ayet, kelime) != (kok.sure, kok.ayet, kok.ilk):
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: surah/ayah/word capayla tutarsiz")
        if capa in gorulen:
            raise GirdiHatasi(f"{s.etiket} satir {s.no}: yinelenen anchor")
        gorulen.add(capa)
        satirlar.append(
            QacKelimesi(
                capa,
                sure,
                ayet,
                kelime,
                _bos_degil(s, "pos"),
                _bos_ya_da_metin(s, "lemma_qac_ref"),
                _bos_ya_da_metin(s, "root_letters_bw"),
                dict(s.nesne("features")),
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{KELIMELER_ADI} bos")
    return satirlar


def tutarlilik_denetle(
    kokler: Sequence[KokSatiri],
    lemmalar: Sequence[LemmaSatiri],
    dalgalar: Sequence[DalgaSatiri],
    kelimeler: Sequence[QacKelimesi],
) -> None:
    """Dosyalar arasi tutarlilik: kok/lemma basvurulari, dalga kumesi (cikis 2)."""
    kok_kumesi = {k.letters_bw for k in kokler}
    lemma_kumesi = {lm.qac_ref for lm in lemmalar}
    if any(
        lm.root_letters_bw is not None and lm.root_letters_bw not in kok_kumesi for lm in lemmalar
    ):
        raise GirdiHatasi(f"{LEMMALAR_ADI}: kokler dosyasinda olmayan kok basvurusu")
    if {d.qac_ref for d in dalgalar} != lemma_kumesi:
        raise GirdiHatasi(f"{DALGALAR_ADI}: dalga kumesi lemma kumesiyle ayni degil")
    for k in kelimeler:
        if k.lemma_qac_ref is not None and k.lemma_qac_ref not in lemma_kumesi:
            raise GirdiHatasi("words.jsonl: lemmalar dosyasinda olmayan lemma basvurusu")
        if k.root_letters_bw is not None and k.root_letters_bw not in kok_kumesi:
            raise GirdiHatasi("words.jsonl: kokler dosyasinda olmayan kok basvurusu")


def _cuz30(manifest: Mapping[str, object]) -> tuple[int, int]:
    ayrintilar = manifest.get("ayrintilar")
    deger = ayrintilar.get("cuz30_baslangic") if isinstance(ayrintilar, dict) else None
    if (
        not isinstance(deger, list)
        or len(deger) != 2
        or not all(isinstance(x, int) and not isinstance(x, bool) and x >= 1 for x in deger)
    ):
        raise GirdiHatasi("anchor manifestinde cuz30_baslangic yok ya da gecersiz")
    return int(deger[0]), int(deger[1])


# --- hazirlik --------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (QAC kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    kelime_bayt, kelime_sha = _dosya_oku(klasor, manifest, KELIMELER_ADI)
    lemma_bayt, lemma_sha = _dosya_oku(klasor, manifest, LEMMALAR_ADI)
    kok_bayt, kok_sha = _dosya_oku(klasor, manifest, KOKLER_ADI)
    dalga_bayt, dalga_sha = _dosya_oku(klasor, manifest, DALGALAR_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, kelime_sha)
    kelimeler = kelime_satirlarini_oku(kelime_bayt)
    lemmalar = lemma_satirlarini_oku(lemma_bayt)
    kokler = kok_satirlarini_oku(kok_bayt)
    dalgalar = dalga_satirlarini_oku(dalga_bayt)
    tutarlilik_denetle(kokler, lemmalar, dalgalar, kelimeler)
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / KELIMELER_ADI)
    girdiler = [lineage.Girdi(yol, kelime_sha, anchor_run_id)]
    for ad, sha in ((LEMMALAR_ADI, lemma_sha), (KOKLER_ADI, kok_sha), (DALGALAR_ADI, dalga_sha)):
        girdiler.append(
            lineage.Girdi(lineage.goreli_yol(ctx.veri_kok, klasor / ad), sha, anchor_run_id)
        )
    for slug in kaynak_idleri:
        girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[slug]]
    return QacHazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=yol,
        units_sha256=kelime_sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham=ham,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        kokler=kokler,
        lemmalar=lemmalar,
        dalgalar=dalgalar,
        qac_kelimeler=kelimeler,
        cuz30=_cuz30(manifest),
        data_version=lemmalar[0].data_version,
    )


# --- dalga sirasi (veritabani kimlikleriyle) --------------------------------------------------


def dalga_sirasi(
    lemmalar: Sequence[LemmaSatiri],
    kokler: Sequence[KokSatiri],
    dalgalar: Mapping[str, int],
    lemma_id: Mapping[str, int],
    kok_id: Mapping[str, int],
) -> dict[str, tuple[int, int]]:
    """`{qac_ref: (dalga, sira)}` (K-50 madde 7): dalga icinde kokun toplam gecisine gore azalan
    (esitlikte `root.id`), koksuzler sonda; kok icinde lemma gecisine gore azalan (esitlikte
    `lemma.id`); `sira` 1 tabanli ve dalga icindedir."""
    kok_gecis = {k.letters_bw: k.occurrences for k in kokler}

    def anahtar(lm: LemmaSatiri) -> tuple[bool, int, int, int, int]:
        kok = lm.root_letters_bw
        if kok is None:
            return (True, 0, 0, -lm.occurrences, lemma_id[lm.qac_ref])
        return (False, -kok_gecis[kok], kok_id[kok], -lm.occurrences, lemma_id[lm.qac_ref])

    sonuc: dict[str, tuple[int, int]] = {}
    for no in range(SON_DALGA + 1):
        grup = sorted((lm for lm in lemmalar if dalgalar[lm.qac_ref] == no), key=anahtar)
        for sira, lm in enumerate(grup, start=1):
            sonuc[lm.qac_ref] = (no, sira)
    return sonuc


# --- veritabani ------------------------------------------------------------------------------

KOK_STAGING: Final = (
    "CREATE TEMP TABLE staging_root (id integer, letters_bw text, letters text,"
    " occurrences integer, ayah_count integer, idf_q real, data_version text) ON COMMIT DROP"
)
KOK_COPY: Final = (
    "COPY pg_temp.staging_root (id, letters_bw, letters, occurrences, ayah_count, idf_q,"
    " data_version) FROM STDIN"
)
KOK_EKLE: Final = (
    "INSERT INTO icerik.root (id, letters, letters_bw, occurrences, ayah_count, idf_q, source_id,"
    " data_version) SELECT s.id, s.letters, s.letters_bw, s.occurrences, s.ayah_count, s.idf_q,"
    " %s, s.data_version FROM pg_temp.staging_root s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.root r WHERE r.letters_bw = s.letters_bw)"
    " ORDER BY s.id"
)
# Yalniz turetilmis sutunlar: letters, letters_bw, source_id, kok_anlami SET listesinde yok.
KOK_GUNCELLE: Final = (
    "UPDATE icerik.root r SET occurrences = s.occurrences, ayah_count = s.ayah_count,"
    " idf_q = s.idf_q, data_version = s.data_version FROM pg_temp.staging_root s"
    " WHERE r.letters_bw = s.letters_bw AND (r.occurrences, r.ayah_count, r.idf_q, r.data_version)"
    " IS DISTINCT FROM (s.occurrences, s.ayah_count, s.idf_q, s.data_version)"
)
LEMMA_STAGING: Final = (
    "CREATE TEMP TABLE staging_lemma (id integer, qac_ref text, text text, text_clean text,"
    " root_id integer, occurrences integer, data_version text) ON COMMIT DROP"
)
LEMMA_COPY: Final = (
    "COPY pg_temp.staging_lemma (id, qac_ref, text, text_clean, root_id, occurrences,"
    " data_version) FROM STDIN"
)
LEMMA_EKLE: Final = (
    "INSERT INTO icerik.lemma (id, lang, text, text_clean, root_id, occurrences, qac_ref,"
    " origin, status, source_id, data_version) SELECT s.id, 'ar', s.text, s.text_clean,"
    " s.root_id, s.occurrences, s.qac_ref, %s, %s::icerik.xref_status, %s, s.data_version"
    " FROM pg_temp.staging_lemma s WHERE NOT EXISTS (SELECT 1 FROM icerik.lemma l"
    " WHERE l.lang = 'ar' AND l.qac_ref = s.qac_ref) ORDER BY s.id"
)
# Yalniz occurrences ve data_version: text, text_clean, qac_ref, status, origin SET'te yok.
LEMMA_GUNCELLE: Final = (
    "UPDATE icerik.lemma l SET occurrences = s.occurrences, data_version = s.data_version"
    " FROM pg_temp.staging_lemma s WHERE l.lang = 'ar' AND l.qac_ref = s.qac_ref"
    " AND (l.occurrences, l.data_version) IS DISTINCT FROM (s.occurrences, s.data_version)"
)
DALGA_STAGING: Final = (
    "CREATE TEMP TABLE staging_dalga (lemma_id integer, dalga smallint, sira integer,"
    " data_version text) ON COMMIT DROP"
)
DALGA_COPY: Final = "COPY pg_temp.staging_dalga (lemma_id, dalga, sira, data_version) FROM STDIN"
DALGA_EKLE: Final = (
    "INSERT INTO icerik.lemma_dalga (lemma_id, dalga, sira, data_version)"
    " SELECT s.lemma_id, s.dalga, s.sira, s.data_version FROM pg_temp.staging_dalga s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.lemma_dalga d WHERE d.lemma_id = s.lemma_id)"
    " ORDER BY s.lemma_id"
)
DALGA_GUNCELLE: Final = (
    "UPDATE icerik.lemma_dalga d SET dalga = s.dalga, sira = s.sira, data_version = s.data_version"
    " FROM pg_temp.staging_dalga s WHERE d.lemma_id = s.lemma_id"
    " AND (d.dalga, d.sira, d.data_version) IS DISTINCT FROM (s.dalga, s.sira, s.data_version)"
)
KELIME_STAGING: Final = (
    'CREATE TEMP TABLE staging_qword (anchor text COLLATE "C", surah smallint, ayah smallint,'
    " word smallint, root_id integer, lemma_id integer, pos text, features jsonb,"
    " lemma_qac_ref text, root_letters_bw text) ON COMMIT DROP"
)
KELIME_COPY: Final = (
    "COPY pg_temp.staging_qword (anchor, surah, ayah, word, root_id, lemma_id, pos, features,"
    " lemma_qac_ref, root_letters_bw) FROM STDIN"
)
KELIME_EKSIK: Final = (
    "SELECT s.anchor FROM pg_temp.staging_qword s WHERE NOT EXISTS"
    " (SELECT 1 FROM icerik.quran_word w WHERE w.anchor = s.anchor) ORDER BY s.anchor"
)
KELIME_FAZLA: Final = (
    "SELECT w.anchor FROM icerik.quran_word w WHERE NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_qword s WHERE s.anchor = w.anchor) ORDER BY w.anchor"
)
KELIME_NUMARA_FARKI: Final = (
    "SELECT w.anchor FROM icerik.quran_word w JOIN pg_temp.staging_qword s ON s.anchor = w.anchor"
    " WHERE (w.surah, w.ayah, w.word) IS DISTINCT FROM (s.surah, s.ayah, s.word)"
    " ORDER BY w.anchor"
)
KELIME_BASKA_KAYNAK: Final = (
    "SELECT w.anchor FROM icerik.quran_word w JOIN pg_temp.staging_qword s ON s.anchor = w.anchor"
    " WHERE w.morph_source IS NOT NULL AND w.morph_source <> %s ORDER BY w.anchor"
)
# Yalniz QAC sutunlari: Tanzil sutunlari, source_id ve data_version SET listesinde yok.
KELIME_GUNCELLE: Final = (
    "UPDATE icerik.quran_word w SET root_id = s.root_id, lemma_id = s.lemma_id, pos = s.pos,"
    " features = s.features, morph_source = %s FROM pg_temp.staging_qword s"
    " WHERE w.anchor = s.anchor AND (w.root_id, w.lemma_id, w.pos, w.features, w.morph_source)"
    " IS DISTINCT FROM (s.root_id, s.lemma_id, s.pos, s.features, %s::text)"
)
# Yukleme sonrasi degismezler (ayni islemde): her kelimenin lemma ve koku staged govde LEM ve
# ROOT'una karsilik gelir; Fatiha ve 30. cuz lemmalari dalga 0 ya da 1'dedir.
LEMMA_TUTARSIZ: Final = (
    "SELECT s.anchor FROM pg_temp.staging_qword s JOIN icerik.quran_word w ON w.anchor = s.anchor"
    " LEFT JOIN icerik.lemma l ON l.id = w.lemma_id LEFT JOIN icerik.root r ON r.id = w.root_id"
    " WHERE l.qac_ref IS DISTINCT FROM s.lemma_qac_ref"
    " OR r.letters_bw IS DISTINCT FROM s.root_letters_bw"
    " OR w.morph_source IS DISTINCT FROM %s::text ORDER BY s.anchor"
)
# `%s, %s`: 30. cuzun baslangic ayeti (sure, ayet); Fatiha = sure 1.
FATIHA_CUZ30_DALGA_DISI: Final = (
    "SELECT DISTINCT l.qac_ref FROM icerik.quran_word w JOIN icerik.lemma l ON l.id = w.lemma_id"
    " JOIN icerik.lemma_dalga d ON d.lemma_id = l.id WHERE (w.surah = 1 OR (w.surah, w.ayah)"
    " >= (%s, %s)) AND d.dalga NOT IN (0, 1) ORDER BY l.qac_ref"
)


def _copy(conn: psycopg.Connection, sorgu: str, satirlar: Sequence[Sequence[object]]) -> None:
    with conn.cursor() as imlec, imlec.copy(sorgu) as kopya:
        for satir in satirlar:
            kopya.write_row(satir)


def _kok_kimlikleri(
    conn: psycopg.Connection, kokler: Sequence[KokSatiri]
) -> tuple[dict[str, int], list[str]]:
    """Kimlikler (`letters_bw` -> id) ve kimligi/yazisi degismis ya da eksik kok bulgulari."""
    mevcut: dict[str, int] = {}
    harf: dict[str, str] = {}
    kaynak: dict[str, str] = {}
    tum_harfler: dict[str, str] = {}
    for kimlik, harfler, bw, kaynak_id in conn.execute(
        "SELECT id, letters, letters_bw, source_id FROM icerik.root"
    ).fetchall():
        tum_harfler[str(harfler)] = str(bw)
        if bw is not None:
            mevcut[str(bw)] = int(kimlik)
            harf[str(bw)] = str(harfler)
            kaynak[str(bw)] = str(kaynak_id)
    satir = conn.execute("SELECT coalesce(max(id), 0) FROM icerik.root").fetchone()
    taban = int(satir[0]) if satir is not None else 0
    bulgu: list[str] = []
    staged = {k.letters_bw: k for k in kokler}
    for bw, k in staged.items():
        if bw in mevcut and (harf[bw] != k.letters or kaynak[bw] != KAYNAK):
            bulgu.append(bw)
        elif bw not in mevcut and k.letters in tum_harfler:
            bulgu.append(bw)  # ayni harfler baska letters_bw altinda (letters tekil)
    bulgu += [bw for bw, kaynak_id in kaynak.items() if kaynak_id == KAYNAK and bw not in staged]
    kimlikler = kimlik_ata(
        mevcut, [k.letters_bw for k in sorted(kokler, key=lambda k: k.ilk_gecis)], taban
    )
    return kimlikler, bulgu


def _lemma_kimlikleri(
    conn: psycopg.Connection, lemmalar: Sequence[LemmaSatiri], kok_id: Mapping[str, int]
) -> tuple[dict[str, int], list[str]]:
    """Kimlikler (`qac_ref` -> id) ve degismemesi gereken sutunu degismis ya da eksik lemmalar."""
    mevcut: dict[str, int] = {}
    ayrinti: dict[str, tuple[object, ...]] = {}
    for kimlik, ref, metin, temiz, kok, durum, koken, kaynak_id in conn.execute(
        "SELECT id, qac_ref, text, text_clean, root_id, status::text, origin, source_id"
        " FROM icerik.lemma WHERE lang = 'ar' AND qac_ref IS NOT NULL"
    ).fetchall():
        mevcut[str(ref)] = int(kimlik)
        ayrinti[str(ref)] = (metin, temiz, kok, durum, koken, kaynak_id)
    satir = conn.execute("SELECT coalesce(max(id), 0) FROM icerik.lemma").fetchone()
    taban = int(satir[0]) if satir is not None else 0
    bulgu: list[str] = []
    staged = {lm.qac_ref: lm for lm in lemmalar}
    for ref, lm in staged.items():
        if ref not in mevcut:
            continue
        beklenen = (
            lm.text,
            lm.text_clean,
            kok_id[lm.root_letters_bw] if lm.root_letters_bw is not None else None,
            LEMMA_STATUS,
            LEMMA_ORIGIN,
            KAYNAK,
        )
        if ayrinti[ref] != beklenen:
            bulgu.append(ref)
    bulgu += [ref for ref, d in ayrinti.items() if d[5] == KAYNAK and ref not in staged]
    kimlikler = kimlik_ata(
        mevcut, [lm.qac_ref for lm in sorted(lemmalar, key=lambda x: x.ilk_gecis)], taban
    )
    return kimlikler, bulgu


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """QAC satirlarini yukler (cagiran `conn.transaction()` icindedir); sayaclari dondurur."""
    if not isinstance(h, QacHazirlik):
        raise TypeError("QAC yuklemesi QacHazirlik ister")
    sayilar: dict[str, int] = {}

    # --- root ---
    kok_id, bulgu = _kok_kimlikleri(conn, h.kokler)
    if bulgu:
        raise QaKaldi(
            f"root: degismemesi gereken sutun degismis ya da QAC koku staged'de yok ({len(bulgu)}):"
            f" {_capalar(bulgu)}"
        )
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_root")
    conn.execute(KOK_STAGING)
    _copy(
        conn,
        KOK_COPY,
        [
            (
                kok_id[k.letters_bw],
                k.letters_bw,
                k.letters,
                k.occurrences,
                k.ayah_count,
                k.idf_q,
                k.data_version,
            )
            for k in h.kokler
        ],
    )
    eklenen = conn.execute(KOK_EKLE, (KAYNAK,)).rowcount
    guncellenen = conn.execute(KOK_GUNCELLE).rowcount
    sayilar.update(
        kok_staging=len(h.kokler),
        kok_eklenen=eklenen,
        kok_guncellenen=guncellenen,
        kok_degismeyen=len(h.kokler) - eklenen - guncellenen,
    )

    # --- lemma ---
    lemma_id, bulgu = _lemma_kimlikleri(conn, h.lemmalar, kok_id)
    if bulgu:
        raise QaKaldi(
            "lemma: degismemesi gereken sutun (text, text_clean, qac_ref, status, kok) degismis"
            " ya da"
            f" QAC lemmasi staged'de yok ({len(bulgu)}): {_capalar(bulgu)}"
        )
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_lemma")
    conn.execute(LEMMA_STAGING)
    _copy(
        conn,
        LEMMA_COPY,
        [
            (
                lemma_id[lm.qac_ref],
                lm.qac_ref,
                lm.text,
                lm.text_clean,
                kok_id[lm.root_letters_bw] if lm.root_letters_bw is not None else None,
                lm.occurrences,
                lm.data_version,
            )
            for lm in h.lemmalar
        ],
    )
    eklenen = conn.execute(LEMMA_EKLE, (LEMMA_ORIGIN, LEMMA_STATUS, KAYNAK)).rowcount
    guncellenen = conn.execute(LEMMA_GUNCELLE).rowcount
    sayilar.update(
        lemma_staging=len(h.lemmalar),
        lemma_eklenen=eklenen,
        lemma_guncellenen=guncellenen,
        lemma_degismeyen=len(h.lemmalar) - eklenen - guncellenen,
    )

    # --- lemma_dalga ---
    dalga_ham = {d.qac_ref: d.dalga for d in h.dalgalar}
    sira = dalga_sirasi(h.lemmalar, h.kokler, dalga_ham, lemma_id, kok_id)
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_dalga")
    conn.execute(DALGA_STAGING)
    _copy(
        conn,
        DALGA_COPY,
        [(lemma_id[ref], d, s, h.data_version) for ref, (d, s) in sira.items()],
    )
    eklenen = conn.execute(DALGA_EKLE).rowcount
    guncellenen = conn.execute(DALGA_GUNCELLE).rowcount
    sayilar.update(
        dalga_staging=len(sira),
        dalga_eklenen=eklenen,
        dalga_guncellenen=guncellenen,
        dalga_degismeyen=len(sira) - eklenen - guncellenen,
    )

    # --- quran_word QAC sutunlari ---
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_qword")
    conn.execute(KELIME_STAGING)
    _copy(
        conn,
        KELIME_COPY,
        [
            (
                k.anchor,
                k.surah,
                k.ayah,
                k.word,
                kok_id[k.root_letters_bw] if k.root_letters_bw is not None else None,
                lemma_id[k.lemma_qac_ref] if k.lemma_qac_ref is not None else None,
                k.pos,
                Jsonb(k.features),
                k.lemma_qac_ref,
                k.root_letters_bw,
            )
            for k in h.qac_kelimeler
        ],
    )
    for sorgu, parametre, ileti in (
        (KELIME_EKSIK, (), "staged kelimesi quran_word'de yok (satir eklenmez; once Tanzil)"),
        (KELIME_FAZLA, (), "quran_word kelimesi staged'de yok (satir silinmez)"),
        (KELIME_NUMARA_FARKI, (), "quran_word (surah, ayah, word) staged ile farkli"),
        (KELIME_BASKA_KAYNAK, (KAYNAK,), "quran_word morph_source baska bir kaynaga ait"),
    ):
        sorun = _capa_listesi(conn, sorgu, parametre)
        if sorun:
            raise QaKaldi(f"{ileti} ({len(sorun)}): {_capalar(sorun)}")
    guncellenen = conn.execute(KELIME_GUNCELLE, (KAYNAK, KAYNAK)).rowcount
    sayilar.update(
        kelime_staging=len(h.qac_kelimeler),
        kelime_guncellenen=guncellenen,
        kelime_degismeyen=len(h.qac_kelimeler) - guncellenen,
    )

    # --- degismezler (ayni islem; ihlalde geri alinir) ---
    tutarsiz = _capa_listesi(conn, LEMMA_TUTARSIZ, (KAYNAK,))
    if tutarsiz:
        raise QaKaldi(
            f"quran_word lemma/kok/morph_source govde LEM ve ROOT'una uymuyor ({len(tutarsiz)}):"
            f" {_capalar(tutarsiz)}"
        )
    dis = _capa_listesi(conn, FATIHA_CUZ30_DALGA_DISI, h.cuz30)
    if dis:
        raise QaKaldi(f"Fatiha ya da 30. cuz lemmasi dalga 0/1 disinda ({len(dis)})")
    sayilar["lemma_tutarsiz"] = 0
    sayilar["fatiha_cuz30_dalga_disi"] = 0
    return sayilar
