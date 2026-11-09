"""`export pg --source test-kucuk|test-tefsir-ornek|test-ses`: sentetik fiksturler (A13.6).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi); iki fark vardir.

Birim fiksturleri (`test-kucuk`, `test-tefsir-ornek`): birimler `metin_durumu = 'taslak'` girer
(sentetik veri kanonik basvuru degildir; K-38 madde 4) ve Tanzil'den farkli olarak `parent_path`,
`role`, `attrs` ile `tr_narrow`, `tr_wide`, `tr_stem` (A05 normallestirici; `normalize --source`)
yazilir; `ar_norm` bos kalir. Yazma kurali (K-39 ruhu, taslak satirlar icin):

* Capa yoksa eklenir.
* Capa varsa ve `content_hash` ayniysa, yalniz TURETILMIS sutunlar (`parent_path`, `ord`,
  `ayah_range`, `tr_*`, `ar_norm`, `data_version`, `provenance`, `run_id`) ve yalniz `metin_durumu =
  'taslak'` satirlarda guncellenir; `incelemede`/`onayli` satira hic dokunulmaz (`korunan`
  sayaci). `metin`, `content_hash`, `role`, `attrs`, `rev`, `status`, `marks` hic yazilmaz.
* Var olan capada metin ya da `content_hash` farkliysa, capa baska `source_id` altindaysa ya da
  veritabaninda olup staged'de olmayan bir `source_id` capasi varsa islem geri alinir (cikis 1
  ya da 2; Tanzil ile ayni). Hat insan duzenlemesinin (taslakta bile) ustune yazmaz.
* `review` satiri ACILMAZ: sentetik birimler icin editore anlamsiz is cikar; fiksturler yalniz
  `dev` ve `internal` derlemelerde (P-12) ve test amaclidir.

`test-ses` (`hazirla_yalniz_kaynak`): birim uretmez; yalniz kaynak kaydi gecerli olmali (G-KAY) ve
`source` satiri yuklenir (`pg._source_satirlari`). Zincir, anchor calistirmasi ve QA raporu aranmaz.

Iletiler yalniz sayi, capa ve alan adi tasir; metin yazilmaz.
"""

from collections.abc import Sequence
from typing import Final

import psycopg
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse as anchor_parse
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    FiksturSatiri,
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
from mutalaa_pipeline.ingest.fikstur import KIND
from mutalaa_pipeline.lineage import OZET_DESENI, UNITS_ADI
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku

METIN_DURUMU: Final = "taslak"
ROL: Final = "govde"
ALANLAR: Final = frozenset(
    {
        "anchor",
        "kind",
        "role",
        "parent_path",
        "ord",
        "ayah_lo",
        "ayah_hi",
        "text",
        "content_hash",
        "metin_durumu",
        "attrs",
        "tr_narrow",
        "tr_wide",
        "tr_stem",
        "ar_norm",
        "data_version",
        "provenance",
        "source_id",
    }
)


# --- satirlari okuma -----------------------------------------------------------------------


def _tam_sayi_ya_da_yok(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def satirlari_oku_fikstur(veri: bytes, source_id: str) -> list[FiksturSatiri]:
    """`units.jsonl` baytlarini kati okur; hata iletisi yalniz satir numarasi/alan adi tasir."""
    satirlar: list[FiksturSatiri] = []
    gorulen: set[str] = set()
    for satir in satirlari_oku(veri, UNITS_ADI):
        yer = f"{UNITS_ADI} satir {satir.no}"
        if set(satir.veri) != ALANLAR:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        capa = satir.metin("anchor")
        try:
            if anchor_format(anchor_parse(capa)) != capa:
                raise GirdiHatasi(f"{yer}: anchor kanonik degil")
        except AnchorError:
            raise GirdiHatasi(f"{yer}: anchor gecersiz") from None
        if capa in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen anchor")
        gorulen.add(capa)
        if satir.metin("source_id") != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        kind = satir.metin("kind")
        if kind != KIND[source_id]:
            raise GirdiHatasi(f"{yer}: kind {KIND[source_id]} degil")
        if satir.metin("metin_durumu") != METIN_DURUMU:
            raise GirdiHatasi(f"{yer}: metin_durumu taslak degil")
        if satir.metin("role") != ROL:
            raise GirdiHatasi(f"{yer}: role govde degil")
        metin = satir.metin("text")
        if metin == "" or "\x00" in metin:
            raise GirdiHatasi(f"{yer}: text bos ya da NUL iceriyor")
        try:
            metin.encode("utf-8")
        except UnicodeEncodeError:
            raise GirdiHatasi(f"{yer}: text UTF-8 olarak yazilamaz") from None
        ozet = satir.metin("content_hash")
        if OZET_DESENI.fullmatch(ozet) is None:
            raise GirdiHatasi(f"{yer}: content_hash 64 haneli kucuk harfli onaltilik degil")
        sira = _tam_sayi_ya_da_yok(satir.veri["ord"])
        lo, hi = (
            _tam_sayi_ya_da_yok(satir.veri["ayah_lo"]),
            _tam_sayi_ya_da_yok(satir.veri["ayah_hi"]),
        )
        if sira is None or sira < 1:
            raise GirdiHatasi(f"{yer}: ord gecersiz")
        if (lo is None) != (hi is None) or (lo is not None and hi is not None and lo >= hi):
            raise GirdiHatasi(f"{yer}: ayah_lo/ayah_hi gecersiz")
        if kind == "tefsir" and lo is None:
            raise GirdiHatasi(f"{yer}: tefsir biriminde ayah_lo/ayah_hi zorunlu")
        yol = satir.veri["parent_path"]
        if yol is not None and (not isinstance(yol, str) or yol == ""):
            raise GirdiHatasi(f"{yer}: parent_path gecersiz")
        if satir.veri["ar_norm"] is not None:
            raise GirdiHatasi(f"{yer}: ar_norm fiksturde bos olmali")
        for alan in ("tr_narrow", "tr_wide", "tr_stem", "data_version"):
            deger = satir.metin(alan)
            if "\x00" in deger or (alan == "data_version" and deger == ""):
                raise GirdiHatasi(f"{yer}: {alan} gecersiz")
        satirlar.append(
            FiksturSatiri(
                anchor=capa,
                kind=kind,
                role=ROL,
                parent_path=yol,
                ord=sira,
                ayah_lo=lo,
                ayah_hi=hi,
                metin=metin,
                content_hash=ozet,
                metin_durumu=METIN_DURUMU,
                attrs=dict(satir.nesne("attrs")),
                tr_narrow=satir.metin("tr_narrow"),
                tr_wide=satir.metin("tr_wide"),
                tr_stem=satir.metin("tr_stem"),
                ar_norm=None,
                data_version=satir.metin("data_version"),
                provenance=dict(satir.nesne("provenance")),
                source_id=source_id,
            )
        )
    return satirlar


# --- hazirlik ------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (birim fiksturu)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    bayt, sha = _dosya_oku(klasor, manifest, UNITS_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)
    satirlar = satirlari_oku_fikstur(bayt, source_id)
    bozuk = [
        s.anchor for s in satirlar if lineage.sha256_bayt(s.metin.encode("utf-8")) != s.content_hash
    ]
    if bozuk:
        raise QaKaldi(f"staged content_hash metinle tutmuyor ({len(bozuk)}): {_capalar(bozuk)}")
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / UNITS_ADI)
    girdiler = [lineage.Girdi(yol, sha, anchor_run_id)]
    for slug in kaynak_idleri:
        girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[slug]]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham=ham,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        fikstur=True,
        fikstur_satirlari=satirlar,
    )


def hazirla_yalniz_kaynak(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Birimsiz fikstur (`test-ses`): yalniz kaynak kaydi denetlenir; zincir ve QA aranmaz."""
    if run is not None:
        raise GirdiHatasi(f"--run {source_id} icin anlamsiz: zincir ve anchor calistirmasi yok")
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id="",
        units_yol="",
        units_sha256="",
        satirlar=[],
        zincir=[],
        ingest={},
        ham={slug: [] for slug in kaynak_idleri},
        qa_rapor_id="",
        kaynaklar=kaynaklar,
        bildirimler={slug: kaynaklar[slug].notice_text for slug in kaynak_idleri},
        parmak=ctx.parmak_izi([]),
        yalniz_kaynak=True,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_fikstur (anchor text COLLATE "C", kind icerik.unit_kind,'
    ' role text, parent_path text COLLATE "C", ord bigint, ayah_range int4range, metin text,'
    " content_hash char(64), metin_durumu icerik.metin_durumu, attrs jsonb, tr_narrow text,"
    " tr_wide text, tr_stem text, ar_norm text, data_version text, provenance jsonb,"
    " source_id text) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_fikstur (anchor, kind, role, parent_path, ord, ayah_range, metin,"
    " content_hash, metin_durumu, attrs, tr_narrow, tr_wide, tr_stem, ar_norm, data_version,"
    " provenance, source_id) FROM STDIN"
)
INSERT_UNIT: Final = (
    "INSERT INTO icerik.unit (anchor, kind, role, source_id, parent_path, ord, ayah_range, metin,"
    " attrs, content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, ar_norm, data_version,"
    " provenance, run_id)"
    " SELECT s.anchor, s.kind, s.role, s.source_id, s.parent_path, s.ord, s.ayah_range, s.metin,"
    " s.attrs, s.content_hash, s.metin_durumu, s.tr_narrow, s.tr_wide, s.tr_stem, s.ar_norm,"
    " s.data_version, s.provenance, %s::uuid"
    " FROM pg_temp.staging_fikstur s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.anchor)"
    " ORDER BY s.ord"
)
# Yalniz turetilmis sutunlar ve yalniz `taslak` satirlar; metin, content_hash, role, attrs, rev,
# status, marks, successors SET listesinde yok.
UPDATE_UNIT: Final = (
    "UPDATE icerik.unit u SET parent_path = s.parent_path, ord = s.ord,"
    " ayah_range = s.ayah_range, tr_narrow = s.tr_narrow, tr_wide = s.tr_wide,"
    " tr_stem = s.tr_stem, ar_norm = s.ar_norm, data_version = s.data_version,"
    " provenance = s.provenance, run_id = %s::uuid, updated_at = now()"
    " FROM pg_temp.staging_fikstur s"
    " WHERE u.anchor = s.anchor AND u.source_id = s.source_id AND u.content_hash = s.content_hash"
    " AND u.metin_durumu = 'taslak'"
    " AND (u.parent_path, u.ord, u.ayah_range, u.tr_narrow, u.tr_wide, u.tr_stem, u.ar_norm,"
    " u.data_version, u.provenance)"
    " IS DISTINCT FROM (s.parent_path, s.ord, s.ayah_range, s.tr_narrow, s.tr_wide, s.tr_stem,"
    " s.ar_norm, s.data_version, s.provenance)"
)
KORUNAN: Final = (
    "SELECT count(*) FROM icerik.unit u JOIN pg_temp.staging_fikstur s ON s.anchor = u.anchor"
    " WHERE u.metin_durumu <> 'taslak'"
)


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[FiksturSatiri]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_fikstur")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for s in satirlar:
            aralik = Range(s.ayah_lo, s.ayah_hi, "[)") if s.ayah_lo is not None else None
            kopya.write_row(
                (
                    s.anchor,
                    s.kind,
                    s.role,
                    s.parent_path,
                    s.ord,
                    aralik,
                    s.metin,
                    s.content_hash,
                    s.metin_durumu,
                    Jsonb(s.attrs),
                    s.tr_narrow,
                    s.tr_wide,
                    s.tr_stem,
                    s.ar_norm,
                    s.data_version,
                    Jsonb(s.provenance),
                    s.source_id,
                )
            )


def _denetimler(conn: psycopg.Connection, source_id: str) -> None:
    """Isleme ozgu denetimler; her biri ilk capalari iletiye yazar."""
    baska = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_fikstur s ON s.anchor = u.anchor"
        " WHERE u.source_id <> s.source_id ORDER BY u.anchor",
    )
    if baska:
        raise GirdiHatasi(f"capa baska bir source_id altinda ({len(baska)}): {_capalar(baska)}")
    fark = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_fikstur s ON s.anchor = u.anchor"
        " WHERE u.content_hash <> s.content_hash OR u.metin IS DISTINCT FROM s.metin"
        " ORDER BY u.anchor",
    )
    if fark:
        raise QaKaldi(f"var olan capada content_hash/metin farki ({len(fark)}): {_capalar(fark)}")
    eksik = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u WHERE u.source_id = %s AND NOT EXISTS"
        " (SELECT 1 FROM pg_temp.staging_fikstur s WHERE s.anchor = u.anchor) ORDER BY u.anchor",
        (source_id,),
    )
    if eksik:
        raise QaKaldi(
            f"onceki yuklemedeki capa staged icinde yok ({len(eksik)}): {_capalar(eksik)}"
        )
    bozuk = _capa_listesi(
        conn,
        "SELECT anchor FROM pg_temp.staging_fikstur"
        " WHERE content_hash::text <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')"
        " ORDER BY anchor",
    )
    if bozuk:
        raise QaKaldi(f"content_hash metnin SHA-256'si degil ({len(bozuk)}): {_capalar(bozuk)}")


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Fikstur birimlerini ekler/gunceller; cagiran `conn.transaction()` icindedir.

    Sayaclar: `staging`, `eklenen`, `guncellenen`, `degismeyen`, `korunan` (taslak olmayan var
    olan satirlar; dokunulmadi).
    """
    _staging_yukle(conn, h.fikstur_satirlari)
    _denetimler(conn, h.source_id)
    korunan = conn.execute(KORUNAN).fetchone()
    eklenen = conn.execute(INSERT_UNIT, (ctx.run_id,)).rowcount
    guncellenen = conn.execute(UPDATE_UNIT, (ctx.run_id,)).rowcount
    return {
        "staging": len(h.fikstur_satirlari),
        "eklenen": eklenen,
        "guncellenen": guncellenen,
        "degismeyen": len(h.fikstur_satirlari) - eklenen - guncellenen,
        "korunan": int(korunan[0]) if korunan is not None else 0,
    }
