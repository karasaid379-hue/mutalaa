"""`export pg --source risale-baski-rnk`: RNK baski sayfa esleme `page_map` yukleme (A20.3, K-52).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit,
`source` satiri `pg._source_satirlari` ile); sablon `pg_yapi.py`'dir. Dosya tarafi: kaynak kaydi
(G-KAY), son `anchor --source risale-baski-rnk` calismasi (`page_map.jsonl`), zincir (sayfa esleme
-> `risale-rnk-metin` anchor -> normalize -> ingest), QA raporu (DORT kapi: G-KAY, G-BUT, G-CAP,
G-NOR; kalan kapida yukleme yapilmaz) ve satirlarin kati okunmasi.

Yazma kurali (K-52 madde 6; Editoryal veritabani 9.1):

* `page_map` upsert'i: `INSERT ... ON CONFLICT (source_id, volume, page, line) DO UPDATE`; yalniz
  TURETILMIS sutunlar (`start_anchor`, `start_offset`, `end_anchor`, `end_offset`, `data_version`)
  guncellenir ve yalniz degeri farkliysa. `line`, `line_type`, `centered`, `glyphs` ve `id` hic
  yazilmaz. `page_map` durum sutunu tasimaz; `review` ACILMAZ.
* Satir SILINMEZ: veritabaninda `risale-baski-rnk` altinda olup staged'de olmayan satir islemi
  geri aldirir (cikis 1, `QaKaldi`).
* Onkosul: her baslangic ve bitis capasi `icerik.unit` tablosunda ve `risale-rnk-metin` altindadir,
  uc birimlerin veritabanindaki `content_hash` degeri staged'deki (`start_hash`, `end_hash`) ile
  ayni, ofsetler birimin veritabanindaki metnine sigar. `risale-rnk-metin` yuklenmemisse, metni
  staged'den farkliysa (editor duzeltmesi, eski yukleme) ya da ofset sigmiyorsa islem geri
  alinir (cikis 1) ve veritabaninda hicbir sey degismez. Ozetler `page_map` tablosuna YAZILMAZ;
  yalniz yukleme anindaki bu denetim icindir (xref'teki `src_hash` denetiminin karsiligi).
* `volume` RNK dosyasinin cilt numarasidir (`adimlar/risale_sayfa.py`).

Iletiler ve rapor yalniz sayi, sayfa ve capa tasir; metin yazilmaz. Sayaclar: `sayfa_staging`,
`sayfa_eklenen`, `sayfa_guncellenen`, `sayfa_degismeyen`, `sayfa_bolum_basi`, `sayfa_dosya`.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.risale import rn_yolu
from mutalaa_pipeline.adimlar.risale_sayfa import (
    BOLUM_BASI_EKI,
    SATIR_ALANLARI,
    SAYFA_ESLEME_ADI,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    RisaleSayfaSatiri,
    _anchor_calismasi,
    _capa_listesi,
    _capalar,
    _manifest_ozet,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_BASKI, KAYNAK_ORNEK, KAYNAK_RNK
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku

SMALLINT_USTU: Final = 32767
INT_USTU: Final = 2147483647
# `page_map` kaynagi -> sayfa capalarinin birim olarak yuklendigi kaynak. Gercek RNK'da sayfa
# eslemesi ayri kaynaktir (`risale-baski-rnk`) ve metin `risale-rnk-metin`dedir; fiksturde
# (A20.5a) ikisi ayni kaynaktir (`test-risale-ornek`) ve `pg_risale.hazirla` onu birimlerle ayni
# islemde yukler.
METIN_KAYNAGI: Final = {KAYNAK_BASKI: KAYNAK_RNK, KAYNAK_ORNEK: KAYNAK_ORNEK}


def kaynak_denetle(source_id: str) -> str:
    """`page_map` kaynagi (`risale-baski-rnk` ya da fikstur) kabul edilir; metin kaynagini verir."""
    metin = METIN_KAYNAGI.get(source_id)
    if metin is None:
        raise GirdiHatasi(f"{source_id}: bu yukleme yalniz {KAYNAK_BASKI} icindir")
    return metin


# --- satirlari okuma -----------------------------------------------------------------------


def _ofset(yer: str, deger: object, alan: str) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int) or not 0 <= deger <= INT_USTU:
        raise GirdiHatasi(f"{yer}: {alan} gecersiz")
    return deger


def satirlari_coz(veri: bytes, source_id: str) -> list[RisaleSayfaSatiri]:
    """`page_map.jsonl` baytlarini kati okur; hata iletisi yalniz satir numarasi/alan adi tasir."""
    satirlar: list[RisaleSayfaSatiri] = []
    gorulen: set[tuple[int, int]] = set()
    for satir in satirlari_oku(veri, SAYFA_ESLEME_ADI):
        yer = f"{SAYFA_ESLEME_ADI} satir {satir.no}"
        if set(satir.veri) != SATIR_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        if satir.metin("source_id") != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        volume, sayfa = satir.sayi("volume"), satir.sayi("page")
        if not 1 <= volume <= SMALLINT_USTU or not 1 <= sayfa <= INT_USTU:
            raise GirdiHatasi(f"{yer}: volume ya da page gecersiz")
        if (volume, sayfa) in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen (volume, page)")
        gorulen.add((volume, sayfa))
        capalar: list[str] = []
        for alan in ("start_anchor", "end_anchor"):
            capa = satir.metin(alan)
            rn_yolu(capa)  # gramer, kanonik bicim, birim duzeyi (GirdiHatasi)
            capalar.append(capa)
        surum = satir.metin("data_version")
        if surum == "" or "\x00" in surum:
            raise GirdiHatasi(f"{yer}: data_version gecersiz")
        ozetler: list[str] = []
        for alan in ("start_hash", "end_hash"):
            ozet = satir.metin(alan)
            if lineage.OZET_DESENI.fullmatch(ozet) is None:
                raise GirdiHatasi(f"{yer}: {alan} 64 haneli kucuk harfli onaltilik degil")
            ozetler.append(ozet)
        satirlar.append(
            RisaleSayfaSatiri(
                volume=volume,
                page=sayfa,
                start_anchor=capalar[0],
                start_offset=_ofset(yer, satir.veri["start_offset"], "start_offset"),
                end_anchor=capalar[1],
                end_offset=_ofset(yer, satir.veri["end_offset"], "end_offset"),
                source_id=source_id,
                data_version=surum,
                start_hash=ozetler[0],
                end_hash=ozetler[1],
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{SAYFA_ESLEME_ADI} bos")
    return satirlar


# --- hazirlik ------------------------------------------------------------------------------


def calismadan_baytlar(
    ctx: RunContext, klasor: Path, manifest: Mapping[str, object]
) -> tuple[str, str, bytes]:
    """Anchor calismasinin `page_map.jsonl` dosyasi: `(veri koku yolu, sha256, bayt)`.

    Dosya manifestteki ozetle dogrulanir; satirlar burada AYRISTIRILMAZ (`satirlari_coz`).
    """
    beklenen = _manifest_ozet(manifest, SAYFA_ESLEME_ADI)
    if beklenen is None:
        raise GirdiHatasi(f"manifestte {SAYFA_ESLEME_ADI} yok (once anchor --source)")
    dosya = klasor / SAYFA_ESLEME_ADI
    try:
        veri = dosya.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{SAYFA_ESLEME_ADI} okunamadi") from None
    sha = lineage.sha256_bayt(veri)
    if sha != beklenen:
        raise GirdiHatasi(f"{SAYFA_ESLEME_ADI} ozeti manifestle tutmuyor")
    return lineage.goreli_yol(ctx.veri_kok, dosya), sha, veri


def calismadan_oku(
    ctx: RunContext, klasor: Path, manifest: Mapping[str, object], source_id: str
) -> tuple[str, str, list[RisaleSayfaSatiri]]:
    """`calismadan_baytlar` ve kati okuma: `(veri koku yolu, sha256, satirlar)`."""
    yol, sha, veri = calismadan_baytlar(ctx, klasor, manifest)
    return yol, sha, satirlari_coz(veri, source_id)


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (RNK baski sayfa esleme).

    Yalniz `risale-baski-rnk` icin: fiksturun `page_map` satirlari `pg_risale.hazirla` icinde,
    birimlerle birlikte okunur (`calismadan_oku`).
    """
    if kaynak_denetle(source_id) != KAYNAK_RNK:
        raise GirdiHatasi(f"{source_id}: page_map birimlerle birlikte yuklenir (export pg)")
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("sayfa esleme calistirmasinin ciktilari saglam degil")
    yol, sha, veri = calismadan_baytlar(ctx, klasor, manifest)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, (KAYNAK_RNK,))
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)  # dort kapi; kalirsa yukleme yok
    satirlar = satirlari_coz(veri, source_id)
    # Ham dosyalar `risale-rnk-metin` ingest'inindir (ayni klasor iki kaydin kaynagidir).
    ham_dosyalar = {slug: ham[KAYNAK_RNK] for slug in kaynak_idleri}
    girdiler = [lineage.Girdi(yol, sha, anchor_run_id)]
    girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[KAYNAK_RNK]]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham=ham_dosyalar,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler={slug: kaynaklar[slug].notice_text for slug in kaynak_idleri},
        parmak=ctx.parmak_izi(girdiler),
        risale_sayfa=satirlar,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    "CREATE TEMP TABLE staging_risale_sayfa (volume smallint, page integer,"
    ' start_anchor text COLLATE "C", start_offset integer, end_anchor text COLLATE "C",'
    " end_offset integer, source_id text, data_version text, start_hash text, end_hash text)"
    " ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_risale_sayfa (volume, page, start_anchor, start_offset, end_anchor,"
    " end_offset, source_id, data_version, start_hash, end_hash) FROM STDIN"
)
# Capalar `risale-rnk-metin` biriminde olmali (yuklenmemis metin: islem geri alinir, cikis 1).
EKSIK_CAPA: Final = (
    "SELECT x.anchor FROM (SELECT start_anchor AS anchor FROM pg_temp.staging_risale_sayfa"
    " UNION SELECT end_anchor FROM pg_temp.staging_risale_sayfa) x WHERE NOT EXISTS"
    " (SELECT 1 FROM icerik.unit u WHERE u.anchor = x.anchor AND u.source_id = %s)"
    " ORDER BY x.anchor"
)
# Uc birimlerin veritabanindaki `content_hash` degeri staged'deki ile ayni olmali: farkliysa birim
# staged'den sonra degismis (ya da eski yukleme) ve ofsetler baska metne ait olurdu.
OZET_FARKI: Final = (
    "SELECT 'sayfa ' || s.volume || '/' || s.page FROM pg_temp.staging_risale_sayfa s"
    " JOIN icerik.unit b ON b.anchor = s.start_anchor JOIN icerik.unit e ON e.anchor = s.end_anchor"
    " WHERE b.content_hash IS DISTINCT FROM s.start_hash"
    " OR e.content_hash IS DISTINCT FROM s.end_hash ORDER BY s.volume, s.page"
)
# Ofsetler birimin veritabanindaki metnine sigmali (kod noktasi: char_length).
OFSET_TASAN: Final = (
    "SELECT 'sayfa ' || s.volume || '/' || s.page FROM pg_temp.staging_risale_sayfa s"
    " JOIN icerik.unit b ON b.anchor = s.start_anchor JOIN icerik.unit e ON e.anchor = s.end_anchor"
    " WHERE s.start_offset >= char_length(b.metin) OR s.end_offset > char_length(e.metin)"
    " ORDER BY s.volume, s.page"
)
# Satir silinmez: veritabaninda olup staged'de olmayan satir islemi geri aldirir.
EKSIK_SATIR: Final = (
    "SELECT 'sayfa ' || p.volume || '/' || p.page FROM icerik.page_map p WHERE p.source_id = %s"
    " AND NOT EXISTS (SELECT 1 FROM pg_temp.staging_risale_sayfa s WHERE s.source_id = p.source_id"
    " AND s.volume IS NOT DISTINCT FROM p.volume AND s.page = p.page AND p.line IS NULL)"
    " ORDER BY p.volume, p.page"
)
# Yazimdan ONCE: staged anahtarlarindan veritabaninda var olanlar ve degerleri farkli olanlar.
SAYAC: Final = (
    "SELECT count(*), count(*) FILTER (WHERE (p.start_anchor, p.start_offset, p.end_anchor,"
    " p.end_offset, p.data_version) IS DISTINCT FROM (s.start_anchor, s.start_offset,"
    " s.end_anchor, s.end_offset, s.data_version))"
    " FROM icerik.page_map p JOIN pg_temp.staging_risale_sayfa s"
    " ON s.source_id = p.source_id AND s.volume IS NOT DISTINCT FROM p.volume"
    " AND s.page = p.page AND p.line IS NULL"
)
# Yalniz turetilmis sutunlar ve yalniz degeri farkli satir; line, line_type, centered, glyphs ve
# id SET listesinde ve INSERT'te yok.
UPSERT: Final = (
    "INSERT INTO icerik.page_map (source_id, volume, page, start_anchor, start_offset,"
    " end_anchor, end_offset, data_version)"
    " SELECT s.source_id, s.volume, s.page, s.start_anchor, s.start_offset, s.end_anchor,"
    " s.end_offset, s.data_version FROM pg_temp.staging_risale_sayfa s"
    " ORDER BY s.volume, s.page"
    " ON CONFLICT (source_id, volume, page, line) DO UPDATE SET"
    " start_anchor = EXCLUDED.start_anchor, start_offset = EXCLUDED.start_offset,"
    " end_anchor = EXCLUDED.end_anchor, end_offset = EXCLUDED.end_offset,"
    " data_version = EXCLUDED.data_version"
    " WHERE (icerik.page_map.start_anchor, icerik.page_map.start_offset,"
    " icerik.page_map.end_anchor, icerik.page_map.end_offset, icerik.page_map.data_version)"
    " IS DISTINCT FROM (EXCLUDED.start_anchor, EXCLUDED.start_offset, EXCLUDED.end_anchor,"
    " EXCLUDED.end_offset, EXCLUDED.data_version)"
)


def yukle(conn: psycopg.Connection, h: Hazirlik) -> dict[str, int]:
    """`page_map` upsert'i; cagiran `conn.transaction()` icindedir (kilit `pg._yukle`de)."""
    satirlar = h.risale_sayfa
    if not satirlar:
        raise GirdiHatasi("RNK baski sayfa hazirligi yok")
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_risale_sayfa")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for s in satirlar:
            kopya.write_row(
                (
                    s.volume,
                    s.page,
                    s.start_anchor,
                    s.start_offset,
                    s.end_anchor,
                    s.end_offset,
                    s.source_id,
                    s.data_version,
                    s.start_hash,
                    s.end_hash,
                )
            )
    metin_kaynagi = kaynak_denetle(h.source_id)
    eksik_capa = _capa_listesi(conn, EKSIK_CAPA, (metin_kaynagi,))
    if eksik_capa:
        raise QaKaldi(
            f"page_map capasi {metin_kaynagi} biriminde yok ({len(eksik_capa)}):"
            f" {_capalar(eksik_capa)} (once export pg --source {metin_kaynagi})"
        )
    ozet_farki = _capa_listesi(conn, OZET_FARKI)
    if ozet_farki:
        raise QaKaldi(
            f"page_map uc birimi staged'den sonra degismis ({len(ozet_farki)}):"
            f" {_capalar(ozet_farki)} (once export pg --source {metin_kaynagi}"
            " ya da anchor yeniden calismali)"
        )
    tasan = _capa_listesi(conn, OFSET_TASAN)
    if tasan:
        raise QaKaldi(f"page_map ofseti birim metnine sigmiyor ({len(tasan)}): {_capalar(tasan)}")
    yok = _capa_listesi(conn, EKSIK_SATIR, (h.source_id,))
    if yok:
        raise QaKaldi(
            f"veritabanindaki page_map satiri staged icinde yok ({len(yok)}): {_capalar(yok)}"
        )
    sonuc = conn.execute(SAYAC).fetchone()
    var, degisen = (int(sonuc[0]), int(sonuc[1])) if sonuc is not None else (0, 0)
    eklenecek = len(satirlar) - var
    yazilan = conn.execute(UPSERT).rowcount
    if yazilan != eklenecek + degisen:
        raise QaKaldi(
            f"page_map yazimi beklenenden farkli ({yazilan} satir, beklenen {eklenecek + degisen})"
        )
    return {
        "sayfa_staging": len(satirlar),
        "sayfa_eklenen": eklenecek,
        "sayfa_guncellenen": degisen,
        "sayfa_degismeyen": var - degisen,
        "sayfa_bolum_basi": sum(1 for s in satirlar if s.data_version.endswith(BOLUM_BASI_EKI)),
        "sayfa_dosya": len({s.volume for s in satirlar}),
    }


__all__ = ["hazirla", "kaynak_denetle", "satirlari_coz", "yukle"]
