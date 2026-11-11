"""`export pg --source elmalili-meal|elmalili-sade-meal`: taslak meal ve inceleme kuyrugu (A16.4).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit);
sablonlar `pg_fikstur.py` (taslak `INSERT_UNIT`) ve `pg_sure_adlari.py` (`INSERT_REVIEW`)'dir. Dosya
tarafi: kaynak kaydi (G-KAY), son `anchor` calismasi (`units.jsonl`), zincir (anchor -> normalize
-> ingest; `elmalili-meal` icin tanigin ingest'i de), QA raporu (BES kapi: G-KAY, G-BUT, G-CAP,
G-NOR, G-HIZ; G-HIZ kalirsa yukleme yapilmaz) ve satirlarin kati okunmasi. Tanik kaynagi
(`elmalili-meal-epub`) YUKLENMEZ.

BIRIM KURALLARI (K-49 madde 10 ve 11; hat meal biriminin METNINE hic yazmaz):

* Capa yoksa `metin_durumu = 'taslak'` ile eklenir (`attrs`, `tr_*`, `ayah_range`, `provenance`
  dahil). `page_map` yazilmaz.
* Capa varsa ve `content_hash` ayniysa, yalniz `taslak` satirda TURETILMIS sutunlar (`ord`,
  `ayah_range`, `tr_*`, `ar_norm`, `data_version`, `provenance`, `run_id`) staged'den gelir;
  `incelemede` ve `onayli` satira dokunulmaz.
* Capa varsa ve `content_hash` farkliysa metne, `content_hash`'e, `rev`'e, `attrs`'a ve durumlara
  DOKUNULMAZ (editor duzeltmesi ya da yeni kaynak surumu): staged ozeti herhangi bir inceleme
  kaydinda varsa `korunan_duzeltilmis` sayilir; yoksa kaynak surumu degisimi sayilir ve asagidaki
  inceleme kurali yeni kayit acar.
* `tr_stem IS NULL` olan birimde (editor onayi `tr_stem`'i NULL birakir) `tr_stem` veritabanindaki
  GUNCEL metinden `normalize.tr_stem` ile hesaplanir; baska sutuna dokunulmaz.
* Veritabaninda olup staged'de olmayan bir meal capasi (capa durur kurali) ya da baska bir
  `source_id` altindaki capa islemi geri aldirir.

INCELEME KURALLARI (K-49 madde 9 ve 11): `hedef_tablo = 'unit'`, `hedef_anahtar = capa`, `alan =
'metin'`, `eylem = 'oner'`, `koken = 'hat'`, `oneren = 'hat'`. `onerilen = {metin, content_hash,
uyari?, tanik?}` (`uyari`: sinir durumu kodlari; `tanik`: capraz tanik skoru); birlesik IZLEYEN
birimde `onerilen` NULL'dur (yalniz durum onayi). `onceki` ilk yuklemede (ve veritabani metni
staged ile ayni iken) bostur; kaynak surumu degisiminde `{metin, content_hash}` veritabanindaki
guncel metindir. Anahtar `(unit, 'metin', onerilen.content_hash)`: bu anahtarla HERHANGI bir
durumda kayit varsa yenisi acilmaz; birimin acik bir metin incelemesi varsa yeni kayit beklenir
(`bekleyen_kaynak_farki`). Tek istisna: son kaydi `reddedildi` olan TASLAK birim yeniden kuyruga
girer. Kayitlar tek ifadede, tanik skoruna gore ARTAN sirada (skoru olmayan sona, sonra `ord`)
eklenir; kimlik sirasi bu yuzden dusuk uyumlu ayetleri one alir.

Iletiler yalniz sayi, capa ve alan adi tasir; metin yazilmaz. Sayaclar: `staging`, `eklenen`,
`guncellenen`, `degismeyen`, `korunan`, `korunan_duzeltilmis`, `review_eklenen`,
`review_yeniden_kuyruk`, `review_kaynak_farki`, `bekleyen_kaynak_farki`, `tr_stem_dolan`,
`attrs_farki`.
"""

from collections.abc import Sequence
from typing import Final

import psycopg
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.meal import ANCHOR_ALANLARI, KIND, METIN_DURUMU, ROL, meal_capasi
from mutalaa_pipeline.anchor import AnchorError, content_hash
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor import parse as anchor_parse
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    MealSatiri,
    _anchor_calismasi,
    _bildirim,
    _capa_listesi,
    _capalar,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.lineage import OZET_DESENI, UNITS_ADI
from mutalaa_pipeline.normalize import tr_stem
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku

# --- satirlari okuma -----------------------------------------------------------------------


def _tam_sayi(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def satirlari_oku_meal(veri: bytes, source_id: str) -> list[MealSatiri]:
    """`units.jsonl` baytlarini kati okur; hata iletisi yalniz satir numarasi ve alan adi tasir."""
    satirlar: list[MealSatiri] = []
    gorulen: set[str] = set()
    for satir in satirlari_oku(veri, UNITS_ADI):
        yer = f"{UNITS_ADI} satir {satir.no}"
        if set(satir.veri) != ANCHOR_ALANLARI:
            raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
        capa = satir.metin("anchor")
        try:
            kanonik = anchor_format(anchor_parse(capa)) == capa
        except AnchorError:
            raise GirdiHatasi(f"{yer}: anchor gecersiz") from None
        if not kanonik or meal_capasi(source_id, capa) is None:
            raise GirdiHatasi(f"{yer}: anchor bu mealin kanonik capasi degil")
        if capa in gorulen:
            raise GirdiHatasi(f"{yer}: yinelenen anchor")
        gorulen.add(capa)
        if satir.metin("source_id") != source_id:
            raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
        if satir.metin("kind") != KIND:
            raise GirdiHatasi(f"{yer}: kind {KIND} degil")
        if satir.metin("metin_durumu") != METIN_DURUMU:
            raise GirdiHatasi(f"{yer}: metin_durumu taslak degil")
        if satir.metin("role") != ROL:
            raise GirdiHatasi(f"{yer}: role govde degil")
        metin = satir.metin("text")
        attrs = dict(satir.nesne("attrs"))
        if "\x00" in metin or (metin == "" and "birlesik_ile" not in attrs):
            raise GirdiHatasi(f"{yer}: text bos (birlesik izleyen degil) ya da NUL iceriyor")
        if metin != "" and "birlesik_ile" in attrs:  # birlesik degismezi, ters yon
            raise GirdiHatasi(f"{yer}: birlesik_ile var ama text bos degil")
        try:
            metin.encode("utf-8")
        except UnicodeEncodeError:
            raise GirdiHatasi(f"{yer}: text UTF-8 olarak yazilamaz") from None
        ozet = satir.metin("content_hash")
        if OZET_DESENI.fullmatch(ozet) is None:
            raise GirdiHatasi(f"{yer}: content_hash 64 haneli kucuk harfli onaltilik degil")
        sira, lo, hi = (
            _tam_sayi(satir.veri["ord"]),
            _tam_sayi(satir.veri["ayah_lo"]),
            _tam_sayi(satir.veri["ayah_hi"]),
        )
        if sira is None or sira < 1 or lo is None or hi is None or lo >= hi:
            raise GirdiHatasi(f"{yer}: ord ya da ayah_lo/ayah_hi gecersiz")
        if satir.veri["ar_norm"] is not None:
            raise GirdiHatasi(f"{yer}: ar_norm mealde bos olmali")
        for alan in ("tr_narrow", "tr_wide", "tr_stem", "data_version"):
            deger = satir.metin(alan)
            if "\x00" in deger or (alan == "data_version" and deger == ""):
                raise GirdiHatasi(f"{yer}: {alan} gecersiz")
        tanik = satir.veri["tanik"]
        if tanik is not None and (
            not isinstance(tanik, dict) or type(tanik.get("skor")) is not int
        ):
            raise GirdiHatasi(f"{yer}: tanik nesne degil ya da skor tam sayi degil")
        provenance = dict(satir.nesne("provenance"))
        uyari = provenance.get("uyari", [])
        if not isinstance(uyari, list) or not all(isinstance(u, str) for u in uyari):
            raise GirdiHatasi(f"{yer}: provenance.uyari metin listesi degil")
        satirlar.append(
            MealSatiri(
                anchor=capa,
                kind=KIND,
                role=ROL,
                ord=sira,
                ayah_lo=lo,
                ayah_hi=hi,
                metin=metin,
                content_hash=ozet,
                metin_durumu=METIN_DURUMU,
                attrs=attrs,
                tr_narrow=satir.metin("tr_narrow"),
                tr_wide=satir.metin("tr_wide"),
                tr_stem=satir.metin("tr_stem"),
                data_version=satir.metin("data_version"),
                provenance=provenance,
                source_id=source_id,
                tanik=dict(tanik) if isinstance(tanik, dict) else None,
                uyari=tuple(uyari),
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{UNITS_ADI} bos")
    return satirlar


def onerilen_kur(s: MealSatiri) -> dict[str, object] | None:
    """`review.onerilen`: `{metin, content_hash, uyari?, tanik?}`; birlesik izleyende None."""
    if "birlesik_ile" in s.attrs:
        return None
    nesne: dict[str, object] = {"metin": s.metin, "content_hash": s.content_hash}
    if s.uyari:
        nesne["uyari"] = list(s.uyari)
    if s.tanik is not None:
        nesne["tanik"] = s.tanik
    return nesne


# --- hazirlik ------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (meal kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    bayt, sha = _dosya_oku(klasor, manifest, UNITS_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)  # bes kapi; G-HIZ sert
    satirlar = satirlari_oku_meal(bayt, source_id)
    bozuk = [s.anchor for s in satirlar if content_hash(s.metin) != s.content_hash]
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
        meal=True,
        meal_satirlari=satirlar,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_meal (anchor text COLLATE "C", ord bigint, ayah_range int4range,'
    " metin text, content_hash char(64), attrs jsonb, tr_narrow text, tr_wide text, tr_stem text,"
    " data_version text, provenance jsonb, source_id text, onerilen jsonb, skor integer)"
    " ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_meal (anchor, ord, ayah_range, metin, content_hash, attrs, tr_narrow,"
    " tr_wide, tr_stem, data_version, provenance, source_id, onerilen, skor) FROM STDIN"
)

# Her staged satirin birimi ve inceleme durumu TEK geciste (hash birlesimi) bir gecici tabloya
# yazilir; sayaclar ve inceleme eklemesi bu tabloyu okur (review'da hedef_anahtar dizini yoktur:
# satir basina iliskili alt sorgu O(n^2) olurdu). `anahtar_var` = staged ozetiyle (izleyende NULL
# onerilen) herhangi bir durumda inceleme kaydi; `acik_var` = acik metin incelemesi; `son_durum`
# = birimin son metin incelemesinin durumu.
DURUM: Final = (
    "CREATE TEMP TABLE meal_durum ON COMMIT DROP AS"
    " WITH rv AS (SELECT r.hedef_anahtar, bool_or(r.durum = 'acik') AS acik_var,"
    " bool_or(r.onerilen IS NULL) AS null_var,"
    " array_agg(DISTINCT r.onerilen ->> 'content_hash')"
    " FILTER (WHERE r.onerilen IS NOT NULL) AS hashler,"
    " (array_agg(r.durum::text ORDER BY r.id DESC))[1] AS son_durum"
    " FROM icerik.review r WHERE r.hedef_tablo = 'unit' AND r.alan = 'metin'"
    " AND r.hedef_anahtar IN (SELECT anchor FROM pg_temp.staging_meal)"
    " GROUP BY r.hedef_anahtar)"
    " SELECT s.anchor, s.ord, s.skor, s.onerilen, s.content_hash AS s_hash,"
    " u.anchor AS u_anchor, u.metin AS u_metin, u.content_hash AS u_hash,"
    " u.metin_durumu::text AS u_durum,"
    " CASE WHEN s.onerilen IS NULL THEN COALESCE(rv.null_var, false)"
    " ELSE s.content_hash::text = ANY (COALESCE(rv.hashler, ARRAY[]::text[])) END AS anahtar_var,"
    " COALESCE(rv.acik_var, false) AS acik_var, rv.son_durum"
    " FROM pg_temp.staging_meal s LEFT JOIN icerik.unit u ON u.anchor = s.anchor"
    " LEFT JOIN rv ON rv.hedef_anahtar = s.anchor"
)
# Yeni inceleme acilir: acik kayit yok VE (anahtar yok YA DA taslak birimin son kaydi reddedildi).
ACILACAK: Final = (
    "WHERE NOT o.acik_var AND (NOT o.anahtar_var"
    " OR (o.u_durum = 'taslak' AND o.son_durum = 'reddedildi'))"
)
INSERT_REVIEW: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen,"
    " koken, oneren) SELECT 'unit', o.anchor, 'metin', 'oner',"
    " CASE WHEN o.u_anchor IS NOT NULL AND o.u_hash <> o.s_hash"
    " THEN jsonb_build_object('metin', o.u_metin, 'content_hash', o.u_hash::text) END,"
    " o.onerilen, 'hat', 'hat' FROM pg_temp.meal_durum o " + ACILACAK + " ORDER BY o.skor"
    " NULLS LAST, o.ord"
)
SAY_YENIDEN: Final = "SELECT count(*) FROM pg_temp.meal_durum o " + ACILACAK + " AND o.anahtar_var"
SAY_KAYNAK_FARKI: Final = (
    "SELECT count(*) FROM pg_temp.meal_durum o " + ACILACAK + " AND NOT o.anahtar_var"
    " AND o.u_anchor IS NOT NULL AND o.u_hash <> o.s_hash"
)
SAY_BEKLEYEN: Final = (
    "SELECT count(*) FROM pg_temp.meal_durum o WHERE o.acik_var AND NOT o.anahtar_var"
    " AND o.u_anchor IS NOT NULL AND o.u_hash <> o.s_hash"
)
# Son kaydi reddedilen taslak birim yeniden kuyruga girer (SAY_YENIDEN); ayni birim ayrica
# "korunan duzeltilmis" sayilmaz: iki sayac ayrik kumelerdir.
SAY_KORUNAN_DUZELTILMIS: Final = (
    "SELECT count(*) FROM pg_temp.meal_durum o WHERE o.u_anchor IS NOT NULL"
    " AND o.u_hash <> o.s_hash AND o.anahtar_var AND NOT (NOT o.acik_var"
    " AND o.u_durum = 'taslak' AND o.son_durum = 'reddedildi')"
)
# Sunucunun duzeltme ucuyla ayni advisory kilit (UnitEndpoints.Corrections.cs:
# `pg_advisory_xact_lock(hashtextextended('unit-correction:' || capa, 0))`): hat ayni birim icin
# inceleme acarken editor es zamanli duzeltme onerisi acamasin (ve tersi).
ADAY_KILIT: Final = (
    "SELECT o.anchor FROM pg_temp.meal_durum o " + ACILACAK + " AND o.u_anchor IS NOT NULL"
    " ORDER BY o.anchor"
)
KILIT_AL: Final = "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))"
KILIT_ONEKI: Final = "unit-correction:"
INSERT_UNIT: Final = (
    "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, ayah_range, metin, attrs,"
    " content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, data_version, provenance, run_id)"
    " SELECT s.anchor, 'meal', 'govde', s.source_id, s.ord, s.ayah_range, s.metin, s.attrs,"
    " s.content_hash, 'taslak', s.tr_narrow, s.tr_wide, s.tr_stem, s.data_version,"
    " s.provenance, %s::uuid FROM pg_temp.staging_meal s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.anchor)"
    " ORDER BY s.ord"
)
# Yalniz turetilmis sutunlar ve yalniz `taslak` satirlar, ozeti staged ile ayni olanlar; metin,
# content_hash, attrs, rev, role, durumlar ve successors SET listesinde yok.
UPDATE_UNIT: Final = (
    "UPDATE icerik.unit u SET ord = s.ord, ayah_range = s.ayah_range, tr_narrow = s.tr_narrow,"
    " tr_wide = s.tr_wide, tr_stem = s.tr_stem, ar_norm = NULL, data_version = s.data_version,"
    " provenance = s.provenance, run_id = %s::uuid, updated_at = now()"
    " FROM pg_temp.staging_meal s"
    " WHERE u.anchor = s.anchor AND u.source_id = s.source_id AND u.content_hash = s.content_hash"
    " AND u.metin_durumu = 'taslak'"
    " AND (u.ord, u.ayah_range, u.tr_narrow, u.tr_wide, u.tr_stem, u.ar_norm, u.data_version,"
    " u.provenance) IS DISTINCT FROM (s.ord, s.ayah_range, s.tr_narrow, s.tr_wide, s.tr_stem,"
    " NULL::text, s.data_version, s.provenance)"
)
KORUNAN: Final = (
    "SELECT count(*) FROM icerik.unit u JOIN pg_temp.staging_meal s ON s.anchor = u.anchor"
    " WHERE u.metin_durumu <> 'taslak'"
)
ATTRS_FARKI: Final = (
    "SELECT count(*) FROM icerik.unit u JOIN pg_temp.staging_meal s ON s.anchor = u.anchor"
    " WHERE u.attrs IS DISTINCT FROM s.attrs"
)
TR_STEM_NULL: Final = (
    "SELECT anchor, metin FROM icerik.unit WHERE source_id = %s AND tr_stem IS NULL"
)
TR_STEM_YAZ: Final = (
    "UPDATE icerik.unit SET tr_stem = %s, updated_at = now() WHERE anchor = %s AND tr_stem IS NULL"
)


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[MealSatiri]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_meal")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for s in satirlar:
            onerilen = onerilen_kur(s)
            skor = s.tanik.get("skor") if s.tanik is not None else None
            kopya.write_row(
                (
                    s.anchor,
                    s.ord,
                    Range(s.ayah_lo, s.ayah_hi, "[)"),
                    s.metin,
                    s.content_hash,
                    Jsonb(s.attrs),
                    s.tr_narrow,
                    s.tr_wide,
                    s.tr_stem,
                    s.data_version,
                    Jsonb(s.provenance),
                    s.source_id,
                    Jsonb(onerilen) if onerilen is not None else None,
                    skor if isinstance(skor, int) else None,
                )
            )


def _say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()
    return int(satir[0]) if satir is not None else 0


def _denetimler(conn: psycopg.Connection, source_id: str) -> None:
    """Isleme ozgu denetimler; her biri ilk capalari iletiye yazar."""
    baska = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_meal s ON s.anchor = u.anchor"
        " WHERE u.source_id <> s.source_id ORDER BY u.anchor",
    )
    if baska:
        raise GirdiHatasi(f"capa baska bir source_id altinda ({len(baska)}): {_capalar(baska)}")
    eksik = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u WHERE u.source_id = %s AND NOT EXISTS"
        " (SELECT 1 FROM pg_temp.staging_meal s WHERE s.anchor = u.anchor) ORDER BY u.anchor",
        (source_id,),
    )
    if eksik:
        raise QaKaldi(
            f"onceki yuklemedeki capa staged icinde yok ({len(eksik)}): {_capalar(eksik)}"
        )
    bozuk = _capa_listesi(
        conn,
        "SELECT anchor FROM pg_temp.staging_meal"
        " WHERE content_hash::text <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')"
        " ORDER BY anchor",
    )
    if bozuk:
        raise QaKaldi(f"content_hash metnin SHA-256'si degil ({len(bozuk)}): {_capalar(bozuk)}")


def _tr_stem_doldur(conn: psycopg.Connection, source_id: str) -> int:
    """`tr_stem IS NULL` birimlerde `tr_stem`i veritabanindaki GUNCEL metinden hesaplar."""
    bos = conn.execute(TR_STEM_NULL, (source_id,)).fetchall()
    if not bos:
        return 0
    with conn.cursor() as imlec:
        imlec.executemany(TR_STEM_YAZ, [(tr_stem(str(metin)), str(capa)) for capa, metin in bos])
    return len(bos)


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Meal birimlerini ekler, inceleme kuyrugunu doldurur; cagiran `conn.transaction()` icindedir.

    Siralama onemlidir: sayaclar ve inceleme kayitlari birim eklenmeden ONCE hesaplanir (yeni
    birimler `u_anchor IS NULL` olarak ilk yukleme sayilir).
    """
    _staging_yukle(conn, h.meal_satirlari)
    _denetimler(conn, h.source_id)
    conn.execute("DROP TABLE IF EXISTS pg_temp.meal_durum")
    conn.execute(DURUM)
    # Var olan birimler icin inceleme acilacaksa once birim kilidi alinir (siralama: capa; kilit
    # ilk yuklemede gerekmez: birim henuz yoktur), sonra durum kilit altinda yeniden okunur.
    adaylar = [str(r[0]) for r in conn.execute(ADAY_KILIT).fetchall()]
    for capa in adaylar:
        conn.execute(KILIT_AL, (KILIT_ONEKI + capa,))
    if adaylar:
        conn.execute("DROP TABLE pg_temp.meal_durum")
        conn.execute(DURUM)
    korunan = _say(conn, KORUNAN)
    korunan_duzeltilmis = _say(conn, SAY_KORUNAN_DUZELTILMIS)
    bekleyen = _say(conn, SAY_BEKLEYEN)
    yeniden = _say(conn, SAY_YENIDEN)
    kaynak_farki = _say(conn, SAY_KAYNAK_FARKI)
    attrs_farki = _say(conn, ATTRS_FARKI)
    review = conn.execute(INSERT_REVIEW).rowcount
    eklenen = conn.execute(INSERT_UNIT, (ctx.run_id,)).rowcount
    guncellenen = conn.execute(UPDATE_UNIT, (ctx.run_id,)).rowcount
    tr_stem_dolan = _tr_stem_doldur(conn, h.source_id)
    if attrs_farki:
        ctx.uyar(f"{attrs_farki} birimde attrs staged ile farkli (hat attrs'a yazmaz)")
    if bekleyen:
        ctx.uyar(f"{bekleyen} birimde acik inceleme var: yeni kaynak surumu kaydi bekliyor")
    return {
        "staging": len(h.meal_satirlari),
        "eklenen": eklenen,
        "guncellenen": guncellenen,
        "degismeyen": len(h.meal_satirlari) - eklenen - guncellenen,
        "korunan": korunan,
        "korunan_duzeltilmis": korunan_duzeltilmis,
        "review_eklenen": review,
        "review_yeniden_kuyruk": yeniden,
        "review_kaynak_farki": kaynak_farki,
        "bekleyen_kaynak_farki": bekleyen,
        "tr_stem_dolan": tr_stem_dolan,
        "attrs_farki": attrs_farki,
    }
