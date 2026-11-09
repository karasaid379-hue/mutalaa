"""`export pg --source tanzil-ust-veri`: `quran_marker` ve `page_map` yukleme (A11.4-A11.6, K-43).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi); fark: birim degil yapi
satiri yuklenir. Dosya tarafi: kaynak kaydi (G-KAY), son `anchor` calismasi (`markers.jsonl`,
`pages.jsonl`), zincir (anchor -> ust veri ingest ve tanzil-uthmani anchor -> ...), QA raporu
(G-KAY, G-BUT, G-CAP; G-NOR bu kaynakta yoktur) ve satirlarin kati okunmasi.

Yazma kurali (K-43 madde 3, K-39'un yapi verisine uzantisi): yukleme upsert'tir ve satir silmez;
`review` ACILMAZ. Var olan satirin degeri degismisse ya da veritabaninda `source_id` altinda olup
staged'de olmayan bir satir varsa islem geri alinir (cikis 1, `QaKaldi`). `page_map` satirlari
sayfa basina tektir (`volume`, `line`, `line_type`, `start_offset`, `end_offset`, `glyphs` NULL,
`centered` false); bu sutunlarin da degismis olmasi degisiklik sayilir. Yalnizca `source` satiri
`tanzil-ust-veri` icindir: `medine-604-duzen` ve `quran-meta` dogrulayicidir, yuklenmez.

Iletiler yalniz sayi, tur/numara ve capa tasir.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, Q
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse as anchor_parse
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    IsaretSatiri,
    SayfaSatiri,
    _anchor_calismasi,
    _bildirim,
    _capa_listesi,
    _capalar,
    _manifest_ozet,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.lineage import ISARETLER_ADI, SAYFALAR_ADI
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku

ISARET_TURLERI: Final = frozenset({"cuz", "hizb", "rub", "secde"})
SECDE_TURLERI: Final = frozenset({"recommended", "obligatory"})
ISARET_ALANLARI: Final = frozenset(
    {"kind", "no", "anchor", "secde_turu", "source_id", "data_version"}
)
SAYFA_ALANLARI: Final = frozenset(
    {"page", "start_anchor", "end_anchor", "source_id", "data_version"}
)


# --- satirlari okuma -----------------------------------------------------------------------


def _capa_turu(capa: str, yer: str) -> Q:
    try:
        ref = anchor_parse(capa)
        kanonik = anchor_format(ref) == capa
    except AnchorError:
        raise GirdiHatasi(f"{yer}: anchor gecersiz") from None
    kok = ref.anchor
    if not kanonik or ref.span is not None or not isinstance(kok, Q) or kok.son is not None:
        raise GirdiHatasi(f"{yer}: anchor kanonik bir q: capasi degil")
    return kok


def _isaretleri_oku(veri: bytes, source_id: str) -> list[IsaretSatiri]:
    satirlar: list[IsaretSatiri] = []
    gorulen: set[tuple[str, int]] = set()
    for satir in satirlari_oku(veri, ISARETLER_ADI):
        yer = f"{ISARETLER_ADI} satir {satir.no}"
        if set(satir.veri) != ISARET_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        kind, no = satir.metin("kind"), satir.sayi("no")
        if kind not in ISARET_TURLERI:
            raise GirdiHatasi(f"{yer}: kind gecersiz")
        if no < 1 or (kind, no) in gorulen:
            raise GirdiHatasi(f"{yer}: no gecersiz ya da yinelenen")
        gorulen.add((kind, no))
        kok = _capa_turu(satir.metin("anchor"), yer)
        if kok.ilk is not None:
            raise GirdiHatasi(f"{yer}: anchor ayet capasi degil")
        etiket = satir.veri["secde_turu"]
        if (kind == "secde") != (etiket is not None):
            raise GirdiHatasi(f"{yer}: secde_turu yalniz secde satirinda dolu olmali")
        if etiket is not None and (not isinstance(etiket, str) or etiket not in SECDE_TURLERI):
            raise GirdiHatasi(f"{yer}: secde_turu recommended ya da obligatory degil")
        if satir.metin("source_id") != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        surum = satir.metin("data_version")
        if surum == "" or "\x00" in surum:
            raise GirdiHatasi(f"{yer}: data_version gecersiz")
        satirlar.append(
            IsaretSatiri(
                kind=kind,
                no=no,
                anchor=satir.metin("anchor"),
                secde_turu=etiket if isinstance(etiket, str) else None,
                source_id=source_id,
                data_version=surum,
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{ISARETLER_ADI} bos")
    return satirlar


def _sayfalari_oku(veri: bytes, source_id: str) -> list[SayfaSatiri]:
    satirlar: list[SayfaSatiri] = []
    gorulen: set[int] = set()
    for satir in satirlari_oku(veri, SAYFALAR_ADI):
        yer = f"{SAYFALAR_ADI} satir {satir.no}"
        if set(satir.veri) != SAYFA_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        sayfa = satir.sayi("page")
        if sayfa < 1 or sayfa in gorulen:
            raise GirdiHatasi(f"{yer}: page gecersiz ya da yinelenen")
        gorulen.add(sayfa)
        for alan in ("start_anchor", "end_anchor"):
            kok = _capa_turu(satir.metin(alan), f"{yer} {alan}")
            if kok.ilk is None:
                raise GirdiHatasi(f"{yer}: {alan} kelime capasi degil")
        if satir.metin("source_id") != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        surum = satir.metin("data_version")
        if surum == "" or "\x00" in surum:
            raise GirdiHatasi(f"{yer}: data_version gecersiz")
        satirlar.append(
            SayfaSatiri(
                page=sayfa,
                start_anchor=satir.metin("start_anchor"),
                end_anchor=satir.metin("end_anchor"),
                source_id=source_id,
                data_version=surum,
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{SAYFALAR_ADI} bos")
    return satirlar


def _dosya_oku(klasor: Path, manifest: dict[str, object], ad: str) -> tuple[bytes, str]:
    beklenen = _manifest_ozet(manifest, ad)
    if beklenen is None:
        raise GirdiHatasi(f"anchor manifestinde {ad} yok (once anchor --source)")
    try:
        veri = (klasor / ad).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{ad} okunamadi") from None
    ozet = lineage.sha256_bayt(veri)
    if ozet != beklenen:
        raise GirdiHatasi(f"{ad} ozeti manifestle tutmuyor")
    return veri, ozet


# --- hazirlik ------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (yapi kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    isaret_bayt, isaret_sha = _dosya_oku(klasor, manifest, ISARETLER_ADI)
    sayfa_bayt, sayfa_sha = _dosya_oku(klasor, manifest, SAYFALAR_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(
        ctx, source_id, anchor_run_id, isaret_sha, {"sayfalar_sha256": sayfa_sha}
    )
    isaretler = _isaretleri_oku(isaret_bayt, source_id)
    sayfalar = _sayfalari_oku(sayfa_bayt, source_id)
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    isaret_yol = lineage.goreli_yol(ctx.veri_kok, klasor / ISARETLER_ADI)
    sayfa_yol = lineage.goreli_yol(ctx.veri_kok, klasor / SAYFALAR_ADI)
    girdiler = [
        lineage.Girdi(isaret_yol, isaret_sha, anchor_run_id),
        lineage.Girdi(sayfa_yol, sayfa_sha, anchor_run_id),
    ]
    for slug in kaynak_idleri:
        girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[slug]]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=isaret_yol,
        units_sha256=isaret_sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham=ham,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        yapi=True,
        isaretler=isaretler,
        sayfalar=sayfalar,
    )


# --- veritabani ----------------------------------------------------------------------------

ISARET_STAGING: Final = (
    'CREATE TEMP TABLE staging_marker (kind text, no smallint, anchor text COLLATE "C",'
    " secde_turu text, source_id text, data_version text) ON COMMIT DROP"
)
ISARET_COPY: Final = (
    "COPY pg_temp.staging_marker (kind, no, anchor, secde_turu, source_id, data_version) FROM STDIN"
)
SAYFA_STAGING: Final = (
    'CREATE TEMP TABLE staging_page (page integer, start_anchor text COLLATE "C",'
    ' end_anchor text COLLATE "C", source_id text, data_version text) ON COMMIT DROP'
)
SAYFA_COPY: Final = (
    "COPY pg_temp.staging_page (page, start_anchor, end_anchor, source_id, data_version) FROM STDIN"
)
FARKLI_ISARET: Final = (
    "SELECT m.kind || '/' || m.no FROM icerik.quran_marker m JOIN pg_temp.staging_marker s"
    " ON s.kind = m.kind AND s.no = m.no WHERE (m.anchor, m.secde_turu, m.source_id,"
    " m.data_version) IS DISTINCT FROM (s.anchor, s.secde_turu, s.source_id, s.data_version)"
    " ORDER BY m.kind, m.no"
)
EKSIK_ISARET: Final = (
    "SELECT m.kind || '/' || m.no FROM icerik.quran_marker m WHERE m.source_id = %s AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_marker s WHERE s.kind = m.kind AND s.no = m.no)"
    " ORDER BY m.kind, m.no"
)
# Yalniz Tanzil sutunlari; secde_turu NULL olabilir.
INSERT_ISARET: Final = (
    "INSERT INTO icerik.quran_marker (kind, no, anchor, secde_turu, source_id, data_version)"
    " SELECT s.kind, s.no, s.anchor, s.secde_turu, s.source_id, s.data_version"
    " FROM pg_temp.staging_marker s WHERE NOT EXISTS (SELECT 1 FROM icerik.quran_marker m"
    " WHERE m.kind = s.kind AND m.no = s.no) ORDER BY s.kind, s.no"
)
# Sayfa satiri: (source_id, volume NULL, page, line NULL); bu anahtar disindaki her sutun degeri
# de karsilastirilir (centered false, line_type/start_offset/end_offset/glyphs NULL).
FARKLI_SAYFA: Final = (
    "SELECT 'sayfa ' || p.page FROM icerik.page_map p JOIN pg_temp.staging_page s"
    " ON s.source_id = p.source_id AND s.page = p.page AND p.volume IS NULL AND p.line IS NULL"
    " WHERE (p.start_anchor, p.end_anchor, p.data_version, p.centered, p.line_type,"
    " p.start_offset, p.end_offset, p.glyphs::text) IS DISTINCT FROM"
    " (s.start_anchor, s.end_anchor, s.data_version, false, NULL, NULL, NULL, NULL)"
    " ORDER BY p.page"
)
EKSIK_SAYFA: Final = (
    "SELECT 'sayfa ' || p.page FROM icerik.page_map p WHERE p.source_id = %s AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_page s WHERE s.source_id = p.source_id AND s.page = p.page"
    " AND p.volume IS NULL AND p.line IS NULL) ORDER BY p.page"
)
INSERT_SAYFA: Final = (
    "INSERT INTO icerik.page_map (source_id, page, start_anchor, end_anchor, data_version)"
    " SELECT s.source_id, s.page, s.start_anchor, s.end_anchor, s.data_version"
    " FROM pg_temp.staging_page s WHERE NOT EXISTS (SELECT 1 FROM icerik.page_map p"
    " WHERE p.source_id = s.source_id AND p.page = s.page AND p.volume IS NULL"
    " AND p.line IS NULL) ORDER BY s.page"
)


def _denetle(conn: psycopg.Connection, farkli: str, eksik: str, source_id: str, ad: str) -> None:
    degisen = _capa_listesi(conn, farkli)
    if degisen:
        raise QaKaldi(
            f"var olan {ad} satirinin degeri degismis ({len(degisen)}): {_capalar(degisen)}"
        )
    yok = _capa_listesi(conn, eksik, (source_id,))
    if yok:
        raise QaKaldi(
            f"veritabanindaki {ad} satiri staged icinde yok ({len(yok)}): {_capalar(yok)}"
        )


def yukle(conn: psycopg.Connection, h: Hazirlik) -> dict[str, int]:
    """`quran_marker` ve `page_map` upsert'i (K-43 madde 3): ekler; degisen/eksik satirda `QaKaldi`.

    Cagiran `conn.transaction()` icindedir. Satir silinmez, `review` acilmaz.
    """
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_marker")
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_page")
    conn.execute(ISARET_STAGING)
    conn.execute(SAYFA_STAGING)
    with conn.cursor() as imlec:
        with imlec.copy(ISARET_COPY) as kopya:
            for m in h.isaretler:
                kopya.write_row((m.kind, m.no, m.anchor, m.secde_turu, m.source_id, m.data_version))
        with imlec.copy(SAYFA_COPY) as kopya:
            for p in h.sayfalar:
                kopya.write_row((p.page, p.start_anchor, p.end_anchor, p.source_id, p.data_version))
    _denetle(conn, FARKLI_ISARET, EKSIK_ISARET, h.source_id, "quran_marker")
    _denetle(conn, FARKLI_SAYFA, EKSIK_SAYFA, h.source_id, "page_map")
    isaret_eklenen = conn.execute(INSERT_ISARET).rowcount
    sayfa_eklenen = conn.execute(INSERT_SAYFA).rowcount
    return {
        "isaret_staging": len(h.isaretler),
        "isaret_eklenen": isaret_eklenen,
        "isaret_degismeyen": len(h.isaretler) - isaret_eklenen,
        "sayfa_staging": len(h.sayfalar),
        "sayfa_eklenen": sayfa_eklenen,
        "sayfa_degismeyen": len(h.sayfalar) - sayfa_eklenen,
    }
