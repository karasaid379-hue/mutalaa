"""`export pg --source sure-adlari-vikipedi`: `surah_alias` adaylari ve `review` satirlari (A11.3).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi). Dosya tarafi: kaynak
kaydi (G-KAY), son `anchor` calismasi (`aliases.jsonl`), zincir (anchor -> ingest sure-adlari ve
ingest tanzil-ust-veri), QA raporu (G-KAY, G-BUT; G-CAP ve G-NOR bu kaynakta yoktur) ve satirlarin
kati okunmasi.

Yazma kurali (K-43 madde 4-5, Editoryal veritabani §8): YALNIZ EKLER.

* `(surah_no, alias)` anahtari `surah_alias` icinde yoksa satir `status = 'aday'` ile eklenir ve
  ayni aday icin bir `review` satiri acilir: `hedef_tablo = 'surah_alias'`, `hedef_anahtar =
  '{surah_no}:{alias}'`, `alan = 'status'`, `eylem = 'oner'`, `koken = 'hat'`, `oneren = 'hat'`,
  `onceki` NULL, `onerilen` = `aliases.jsonl` satirinin `onerilen` nesnesi.
* Var olan satira (aday, onayli ya da red) hic dokunulmaz: editorun degistirdigi deger uzerine
  yazilmaz. Staged'deki `alias_key`, `kind` ya da `risky` veritabanindakinden farkliysa satir
  degistirilmez, `mevcut_farkli` sayacina girer ve rapora uyari olarak yazilir; yeni onerinin
  gecerli olmasi icin editor onceki adayi reddeder ya da siler. Boylece `review.onerilen` ile
  `surah_alias` satiri ayrismaz (hat var olan `review` satirlarina da dokunmaz).
* Ayni hedef icin herhangi bir durumda `review` satiri zaten varsa yenisi acilmaz.
* Hicbir satir silinmez; staged'de olmayan `aday` satirlar `db_disi_aday` olarak sayilir.

`surah_alias` tablosunda kaynak ya da anlam sutunu yoktur; bunlar `review.onerilen` icindedir.
Iletiler yalniz sayi tasir (sure/alias metni yazilmaz).
"""

from collections.abc import Sequence
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    AdaySatiri,
    Hazirlik,
    _anchor_calismasi,
    _bildirim,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.lineage import ALIASLAR_ADI
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_oku

KINDLER: Final = frozenset({"kanonik", "yazim", "arapca", "diger_ad"})
SURE_SAYISI: Final = 114
ALANLAR: Final = frozenset(
    {"surah_no", "alias", "alias_key", "kind", "risky", "status", "onerilen"}
)
ONERILEN_ZORUNLU: Final = ("kind", "alias", "risky", "kaynaklar", "yazimlar")


def _adaylari_oku(veri: bytes) -> list[AdaySatiri]:
    satirlar: list[AdaySatiri] = []
    gorulen: set[tuple[int, str]] = set()
    for satir in satirlari_oku(veri, ALIASLAR_ADI):
        yer = f"{ALIASLAR_ADI} satir {satir.no}"
        if set(satir.veri) != ALANLAR:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        no, alias, anahtar = satir.sayi("surah_no"), satir.metin("alias"), satir.metin("alias_key")
        kind = satir.metin("kind")
        risky = satir.veri["risky"]
        if not 1 <= no <= SURE_SAYISI or kind not in KINDLER or not isinstance(risky, bool):
            raise GirdiHatasi(f"{yer}: surah_no, kind ya da risky gecersiz")
        if satir.metin("status") != "aday":
            raise GirdiHatasi(f"{yer}: status aday degil")
        for alan, deger in (("alias", alias), ("alias_key", anahtar)):
            if deger.strip(" ") == "" or "\x00" in deger:
                raise GirdiHatasi(f"{yer}: {alan} bos ya da NUL iceriyor")
        if (no, alias) in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen (surah_no, alias)")
        gorulen.add((no, alias))
        onerilen = satir.nesne("onerilen")
        if any(a not in onerilen for a in ONERILEN_ZORUNLU) or (
            onerilen["kind"] != kind or onerilen["alias"] != alias or onerilen["risky"] != risky
        ):
            raise GirdiHatasi(f"{yer}: onerilen alanlari satirla tutarsiz")
        if ("anlam" in onerilen) != (kind == "kanonik"):
            raise GirdiHatasi(f"{yer}: anlam yalniz kanonik satirda olmali")
        satirlar.append(AdaySatiri(no, alias, anahtar, kind, risky, dict(onerilen)))
    if not satirlar:
        raise GirdiHatasi(f"{ALIASLAR_ADI} bos")
    return satirlar


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (sure adi kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    bayt, sha = _dosya_oku(klasor, manifest, ALIASLAR_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)
    adaylar = _adaylari_oku(bayt)
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / ALIASLAR_ADI)
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
        sure_adi=True,
        adaylar=adaylar,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    "CREATE TEMP TABLE staging_alias (surah_no smallint, alias text, alias_key text,"
    " kind text, risky boolean, onerilen jsonb) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_alias (surah_no, alias, alias_key, kind, risky, onerilen) FROM STDIN"
)
YENI: Final = (
    "NOT EXISTS (SELECT 1 FROM icerik.surah_alias a WHERE a.surah_no = s.surah_no"
    " AND a.alias = s.alias)"
)
# Hedef icin herhangi bir durumda review varsa yenisi acilmaz (var olan review'a dokunulmaz).
INSERT_REVIEW: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen,"
    " koken, oneren) SELECT 'surah_alias', s.surah_no::text || ':' || s.alias, 'status', 'oner',"
    " NULL, s.onerilen, 'hat', 'hat' FROM pg_temp.staging_alias s WHERE "
    + YENI
    + " AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.hedef_tablo = 'surah_alias'"
    " AND r.hedef_anahtar = s.surah_no::text || ':' || s.alias)"
    " ORDER BY s.surah_no, s.alias"
)
# status yazilmaz: sutun varsayilani 'aday'dir.
INSERT_ALIAS: Final = (
    "INSERT INTO icerik.surah_alias (surah_no, alias, alias_key, kind, risky)"
    " SELECT s.surah_no, s.alias, s.alias_key, s.kind, s.risky FROM pg_temp.staging_alias s"
    " WHERE " + YENI + " ORDER BY s.surah_no, s.alias"
)
MEVCUT_FARKLI: Final = (
    "SELECT count(*) FROM icerik.surah_alias a JOIN pg_temp.staging_alias s"
    " ON s.surah_no = a.surah_no AND s.alias = a.alias"
    " WHERE (a.alias_key, a.kind, a.risky) IS DISTINCT FROM (s.alias_key, s.kind, s.risky)"
)
MEVCUT_ADAY_DISI: Final = (
    "SELECT count(*) FROM icerik.surah_alias a JOIN pg_temp.staging_alias s"
    " ON s.surah_no = a.surah_no AND s.alias = a.alias WHERE a.status <> 'aday'"
)
DB_DISI_ADAY: Final = (
    "SELECT count(*) FROM icerik.surah_alias a WHERE a.status = 'aday' AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_alias s WHERE s.surah_no = a.surah_no AND s.alias = a.alias)"
)


def _say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()
    return int(satir[0]) if satir is not None else 0


def yukle(conn: psycopg.Connection, h: Hazirlik) -> dict[str, int]:
    """Yeni adaylari `surah_alias` + `review` olarak ekler; var olan satira dokunmaz.

    Cagiran `conn.transaction()` icindedir. Sayaclar: `aday_staging`, `aday_eklenen`,
    `review_eklenen`, `aday_degismeyen`, `mevcut_farkli`, `mevcut_aday_disi`, `db_disi_aday`.
    """
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_alias")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for a in h.adaylar:
            kopya.write_row((a.surah_no, a.alias, a.alias_key, a.kind, a.risky, Jsonb(a.onerilen)))
    mevcut_farkli = _say(conn, MEVCUT_FARKLI)
    mevcut_aday_disi = _say(conn, MEVCUT_ADAY_DISI)
    db_disi = _say(conn, DB_DISI_ADAY)
    review = conn.execute(INSERT_REVIEW).rowcount  # alias eklenmeden ONCE (YENI kosulu)
    eklenen = conn.execute(INSERT_ALIAS).rowcount
    return {
        "aday_staging": len(h.adaylar),
        "aday_eklenen": eklenen,
        "review_eklenen": review,
        "aday_degismeyen": len(h.adaylar) - eklenen,
        "mevcut_farkli": mevcut_farkli,
        "mevcut_aday_disi": mevcut_aday_disi,
        "db_disi_aday": db_disi,
    }
