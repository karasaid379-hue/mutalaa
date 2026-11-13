"""`export pg --source risale-rnk-metin`: RNK Risale birimleri (A20.2b, K-51).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit,
`source` satiri `pg._source_satirlari` ile); sablonlar `pg_fikstur.py` ve `pg_meal.py`'dir. Dosya
tarafi: kaynak kaydi (G-KAY), son `anchor` calismasi (`units.jsonl`), zincir (anchor -> normalize
-> ingest), QA raporu (DORT kapi: G-KAY, G-BUT, G-CAP, G-NOR; kalan kapida yukleme yapilmaz) ve
satirlarin kati okunmasi. Diyanet (`risale-asil-nusha`) karsilastirma verisidir: `export pg` onu
REDDEDER (cikis 2; K-51 madde 2).

BOYUT: `units.jsonl` yuzlerce MB, ~139 bin satirdir. Dosya hicbir yerde bellege toptan alinmaz:
`hazirla` satir satir akitip dogrular (bellekte yalniz capa kumesi), `yukle` ayni dosyayi yeniden
akitir ve `staging_risale` gecici tablosuna `COPY` ile PARTI PARTI (`PARTI`) yazar; butun partiler
ve sonraki ifadeler TEK islem icindedir, hata hepsini geri alir. Yuklemeden once dosya ozeti
yeniden hesaplanir (hazirlik ile yukleme arasinda dosya degismemeli).

BIRIM KURALLARI (K-51 madde 8 ve 11, K-26; hat Risale metnini DUZELTMEZ):

* Capa yoksa `metin_durumu = 'taslak'` ve `status = 'etkin'` ile eklenir (`role`, `parent_path`,
  `ord`, `marks`, `sentences`, `attrs`, `tr_*`, `ar_norm`, `provenance` dahil).
  `ayah_range` NULL'dur. `unit` tablosunda `origin` sutunu yoktur.
* Capa varsa, `metin_durumu = 'taslak'` ve `content_hash` ile metin staged ile AYNIYSA yalniz
  TURETILMIS sutunlar (`parent_path`, `ord`, `marks`, `sentences`, `ar_norm`, `tr_narrow`,
  `tr_wide`, `tr_stem`, `provenance`, `data_version`, `run_id`) staged'den gelir. `metin`,
  `content_hash`, `role`, `attrs`, `rev`, `status`, `successors` ve durum SET listesinde yoktur.
* Capa varsa ve `metin_durumu <> 'taslak'` (incelemede, onayli, red) satira HIC yazilmaz
  (`atlanan_onayli`; ozeti ya da metni staged'den farkli olani ayrica `atlanan_metin_degisti`).
* Capa varsa, TASLAK ve metin ya da `content_hash` farkliysa bu yukleme hatasi DEGIL,
  `metin_degisti` sayilir ve uyari yazilir: satir DEGISTIRILMEZ (Risale metni duzeltilmez;
  kaynak guncellenirse yeniden capalama kurali Capa semasi §9'dadir, burada uygulanmaz).
* Baska bir `source_id` altindaki capa islemi geri aldirir (cikis 2); veritabaninda olup staged'de
  olmayan capa (capa durur kurali) islemi geri aldirir (cikis 1).
* Turkce (`attrs.dil = 'tr'`) taslak birimde `tr_stem IS NULL` ise `tr_stem` veritabanindaki
  metinden hesaplanir (`pg_meal._tr_stem_doldur` kalibi; yalniz bu sutun). Osmanlica ve Arapca
  kitapta `tr_*` hep NULL'dur; yalniz `ar_norm` dolar (K-51 madde 4).

Iletiler ve rapor yalniz sayi, capa ve alan adi tasir; metin yazilmaz. Sayaclar: `staging`,
`kitap`, `eklenen`, `ayni_kalan`, `guncellenen`, `metin_degisti`, `atlanan_onayli`,
`atlanan_metin_degisti`, `tr_stem_dolan`.
"""

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import psycopg
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.risale import (
    ANCHOR_ALANLARI,
    DILLER,
    KIND,
    METIN_DURUMU,
    ROL_BASLIK,
    ROL_DIPNOT,
    ROL_GOVDE,
    parent_yolu,
    rn_yolu,
)
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    _anchor_calismasi,
    _bildirim,
    _capa_listesi,
    _capalar,
    _manifest_ozet,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_RNK, KAYNAKLAR
from mutalaa_pipeline.lineage import OZET_DESENI, UNITS_ADI
from mutalaa_pipeline.normalize import tr_stem
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_akit

PARTI: Final = 5000  # `COPY` parti buyuklugu (satir); parti sinirlari islem sinirlari degildir
ROLLER: Final = frozenset({ROL_GOVDE, ROL_BASLIK, ROL_DIPNOT})
ISARET_TURLERI: Final = frozenset({"ar", "hasiye", "rnk"})  # birlestirme isareti `satir` yuklenmez
ETIKET: Final = f"anchor {KAYNAK_RNK} {UNITS_ADI}"


@dataclass(frozen=True, slots=True)
class RisaleSatiri:
    """Dogrulanmis `units.jsonl` satiri; `metin` yalniz veritabanina gider, iletilere girmez."""

    anchor: str
    role: str
    parent_path: str
    ord: int
    metin: str
    marks: list[dict[str, object]]
    sentences: list[tuple[int, int]]
    attrs: dict[str, object]
    content_hash: str
    tr_narrow: str | None
    tr_wide: str | None
    tr_stem: str | None
    ar_norm: str | None
    data_version: str
    provenance: dict[str, object]
    source_id: str


@dataclass(frozen=True)
class RisaleGirdisi:
    """Hazirlik ozeti: dosya bellekte tutulmaz, `yukle` ayni yolu yeniden akitir."""

    yol: Path
    sha256: str
    satir_sayisi: int
    kitap_sayisi: int


# --- kaynak denetimi -----------------------------------------------------------------------


def kaynak_denetle(source_id: str) -> None:
    """Yalniz yuklenebilir Risale kaynagi kabul edilir; Diyanet reddedilir (cikis 2)."""
    kayit = KAYNAKLAR.get(source_id)
    if kayit is None or not kayit.yukleme:
        raise GirdiHatasi(
            f"{source_id}: karsilastirma verisi, export pg birim yuklemez"
            f" (K-51 madde 2: birincil metin {KAYNAK_RNK})"
        )


# --- satirlari okuma -----------------------------------------------------------------------


def _tam_sayi(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def _nul_var(nesne: object) -> bool:
    """JSON degerinde NUL (jsonb'ye yazilamaz) var mi."""
    return "\\u0000" in json.dumps(nesne, ensure_ascii=True)


def _isaretler(yer: str, deger: object, uzunluk: int) -> list[dict[str, object]]:
    if not isinstance(deger, list):
        raise GirdiHatasi(f"{yer}: marks liste degil")
    sonuc: list[dict[str, object]] = []
    for isaret in deger:
        if not isinstance(isaret, dict) or isaret.get("t") not in ISARET_TURLERI:
            raise GirdiHatasi(f"{yer}: marks bilinmeyen isaret turu")
        bas = _tam_sayi(isaret.get("s"))
        son = _tam_sayi(isaret.get("e", bas))
        if bas is None or son is None or not 0 <= bas <= son <= uzunluk:
            raise GirdiHatasi(f"{yer}: marks araligi gecersiz")
        sonuc.append(isaret)
    return sonuc


def _cumleler(yer: str, deger: object, uzunluk: int) -> list[tuple[int, int]]:
    if not isinstance(deger, list):
        raise GirdiHatasi(f"{yer}: sentences liste degil")
    sonuc: list[tuple[int, int]] = []
    onceki = 0
    for aralik in deger:
        if not isinstance(aralik, list) or len(aralik) != 2:
            raise GirdiHatasi(f"{yer}: sentences araligi gecersiz")
        bas, son = _tam_sayi(aralik[0]), _tam_sayi(aralik[1])
        if bas is None or son is None or not onceki <= bas < son <= uzunluk:
            raise GirdiHatasi(f"{yer}: sentences araligi gecersiz ya da sirasiz")
        sonuc.append((bas, son))
        onceki = son
    return sonuc


def _anahtar(yer: str, satir: Satir, alan: str, dil: str) -> str | None:
    """`tr_*` yalniz Turkce kitapta dolu; Osmanlica ve Arapca kitapta NULL olmali."""
    deger = satir.veri[alan]
    if dil != "tr":
        if deger is not None:
            raise GirdiHatasi(f"{yer}: {alan} Turkce olmayan kitapta bos olmali")
        return None
    if not isinstance(deger, str) or "\x00" in deger:
        raise GirdiHatasi(f"{yer}: {alan} gecersiz")
    return deger


def satir_coz(satir: Satir, source_id: str) -> RisaleSatiri:
    """Tek `units.jsonl` satirini kati dogrular; iletiler yalniz satir no ve alan adi tasir."""
    yer = f"{satir.etiket}: satir {satir.no}"
    if set(satir.veri) != ANCHOR_ALANLARI:
        raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
    capa = satir.metin("anchor")
    yol = rn_yolu(capa)  # gramer, kanonik bicim ve kitap/bolum adlari (GirdiHatasi)
    if satir.metin("source_id") != source_id:
        raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
    if satir.metin("kind") != KIND:
        raise GirdiHatasi(f"{yer}: kind {KIND} degil")
    if satir.metin("metin_durumu") != METIN_DURUMU:
        raise GirdiHatasi(f"{yer}: metin_durumu taslak degil")
    rol = satir.metin("role")
    if rol not in ROLLER:
        raise GirdiHatasi(f"{yer}: role gecersiz")
    ust = satir.metin("parent_path")
    if ust != parent_yolu(yol):
        raise GirdiHatasi(f"{yer}: parent_path capayla tutmuyor")
    metin = satir.metin("text")
    if metin == "" or "\x00" in metin:
        raise GirdiHatasi(f"{yer}: text bos ya da NUL iceriyor")
    try:
        ozet_ = content_hash(metin)
    except UnicodeEncodeError:
        raise GirdiHatasi(f"{yer}: text UTF-8 olarak yazilamaz") from None
    ozet = satir.metin("content_hash")
    if OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi(f"{yer}: content_hash 64 haneli kucuk harfli onaltilik degil")
    if ozet_ != ozet:  # hat hatasi: cikis 1 (cagiran yakalar)
        raise QaKaldi(f"staged content_hash metinle tutmuyor: {_capalar([capa])}")
    sira = _tam_sayi(satir.veri["ord"])
    if sira is None or sira < 1:
        raise GirdiHatasi(f"{yer}: ord gecersiz")
    if satir.veri["ayah_lo"] is not None or satir.veri["ayah_hi"] is not None:
        raise GirdiHatasi(f"{yer}: ayah_lo/ayah_hi Risale biriminde bos olmali")
    attrs = dict(satir.nesne("attrs"))
    provenance = dict(satir.nesne("provenance"))
    if _nul_var(attrs) or _nul_var(provenance):
        raise GirdiHatasi(f"{yer}: attrs ya da provenance NUL iceriyor")
    dil = attrs.get("dil")
    if not isinstance(dil, str) or dil not in DILLER:
        raise GirdiHatasi(f"{yer}: attrs.dil tr, ota ya da ar degil")
    ar_norm = satir.veri["ar_norm"]
    if ar_norm is not None and (not isinstance(ar_norm, str) or "\x00" in ar_norm):
        raise GirdiHatasi(f"{yer}: ar_norm gecersiz")
    surum = satir.metin("data_version")
    if surum == "":
        raise GirdiHatasi(f"{yer}: data_version gecersiz")
    uzunluk = len(metin)
    isaretler = _isaretler(yer, satir.veri["marks"], uzunluk)
    cumleler = _cumleler(yer, satir.veri["sentences"], uzunluk)
    if _nul_var(isaretler):
        raise GirdiHatasi(f"{yer}: marks NUL iceriyor")
    return RisaleSatiri(
        anchor=capa,
        role=rol,
        parent_path=ust,
        ord=sira,
        metin=metin,
        marks=isaretler,
        sentences=cumleler,
        attrs=attrs,
        content_hash=ozet,
        tr_narrow=_anahtar(yer, satir, "tr_narrow", dil),
        tr_wide=_anahtar(yer, satir, "tr_wide", dil),
        tr_stem=_anahtar(yer, satir, "tr_stem", dil),
        ar_norm=ar_norm,
        data_version=surum,
        provenance=provenance,
        source_id=source_id,
    )


def satirlari_akit_risale(yol: Path, source_id: str) -> Iterator[RisaleSatiri]:
    """`units.jsonl` satirlarini akitip dogrular (bellekte tek satir)."""
    for satir in satirlari_akit(yol, ETIKET):
        yield satir_coz(satir, source_id)


def dosyayi_dogrula(yol: Path, source_id: str, sha256: str) -> RisaleGirdisi:
    """Tum dosyayi akitip dogrular: yinelenen capa, bicim ve ozet uyumu. Metin saklanmaz."""
    gorulen: set[str] = set()
    kitaplar: set[str] = set()
    sayi = 0
    for satir in satirlari_akit_risale(yol, source_id):
        if satir.anchor in gorulen:
            raise GirdiHatasi(f"{ETIKET}: yinelenen anchor: {_capalar([satir.anchor])}")
        gorulen.add(satir.anchor)
        kitaplar.add(satir.anchor.split(":")[1])
        sayi += 1
    return RisaleGirdisi(yol=yol, sha256=sha256, satir_sayisi=sayi, kitap_sayisi=len(kitaplar))


# --- hazirlik ------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (RNK Risale metni)."""
    kaynak_denetle(source_id)
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    beklenen = _manifest_ozet(manifest, UNITS_ADI)
    if beklenen is None:
        raise GirdiHatasi(f"anchor manifestinde {UNITS_ADI} yok (once anchor --source)")
    units_dosya = klasor / UNITS_ADI
    try:
        sha = lineage.sha256_dosya(units_dosya)
    except OSError:
        raise GirdiHatasi(f"{UNITS_ADI} okunamadi") from None
    if sha != beklenen:
        raise GirdiHatasi(f"{UNITS_ADI} ozeti manifestle tutmuyor")
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)  # dort kapi; kalirsa yukleme yok
    risale = dosyayi_dogrula(units_dosya, source_id, sha)
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    yol = lineage.goreli_yol(ctx.veri_kok, units_dosya)
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
        risale=risale,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_risale (sira bigint, anchor text COLLATE "C", role text,'
    ' parent_path text COLLATE "C", ord bigint, metin text, marks jsonb, sentences int4range[],'
    " attrs jsonb, content_hash char(64), tr_narrow text, tr_wide text, tr_stem text,"
    " ar_norm text, data_version text, provenance jsonb, source_id text) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_risale (sira, anchor, role, parent_path, ord, metin, marks, sentences,"
    " attrs, content_hash, tr_narrow, tr_wide, tr_stem, ar_norm, data_version, provenance,"
    " source_id) FROM STDIN"
)
STAGING_ANALIZ: Final = "ANALYZE pg_temp.staging_risale"
INSERT_UNIT: Final = (
    "INSERT INTO icerik.unit (anchor, kind, role, source_id, parent_path, ord, metin, marks,"
    " sentences, attrs, content_hash, metin_durumu, tr_narrow, tr_wide, tr_stem, ar_norm,"
    " data_version, provenance, run_id)"
    " SELECT s.anchor, 'risale', s.role, s.source_id, s.parent_path, s.ord, s.metin, s.marks,"
    " s.sentences, s.attrs, s.content_hash, 'taslak', s.tr_narrow, s.tr_wide, s.tr_stem,"
    " s.ar_norm, s.data_version, s.provenance, %s::uuid"
    " FROM pg_temp.staging_risale s"
    " WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.anchor)"
    " ORDER BY s.sira"
)
# Yalniz turetilmis sutunlar, yalniz `taslak` satirlar ve metni ile ozeti staged ile ayni olanlar;
# metin, content_hash, role, attrs, rev, status, successors ve metin_durumu SET listesinde yok.
UPDATE_UNIT: Final = (
    "UPDATE icerik.unit u SET parent_path = s.parent_path, ord = s.ord, marks = s.marks,"
    " sentences = s.sentences, ar_norm = s.ar_norm, tr_narrow = s.tr_narrow,"
    " tr_wide = s.tr_wide, tr_stem = s.tr_stem, provenance = s.provenance,"
    " data_version = s.data_version, run_id = %s::uuid, updated_at = now()"
    " FROM pg_temp.staging_risale s"
    " WHERE u.anchor = s.anchor AND u.source_id = s.source_id AND u.metin_durumu = 'taslak'"
    " AND u.content_hash = s.content_hash AND u.metin = s.metin"
    " AND (u.parent_path, u.ord, u.marks, u.sentences, u.ar_norm, u.tr_narrow, u.tr_wide,"
    " u.tr_stem, u.provenance, u.data_version)"
    " IS DISTINCT FROM (s.parent_path, s.ord, s.marks, s.sentences, s.ar_norm, s.tr_narrow,"
    " s.tr_wide, s.tr_stem, s.provenance, s.data_version)"
)
# Var olan satirlarin durumu (INSERT'ten ONCE): taslak + metin farki, taslak olmayan, taslak
# olmayan + metin farki. Ucu de ayri kumelerdir (ilk ikisi kesisimsiz); `metin` karsilastirmasi
# yalniz capasi var olan satirlara uygulanir.
SAYAC: Final = (
    "SELECT count(*) FILTER (WHERE u.metin_durumu = 'taslak' AND (u.content_hash <> s.content_hash"
    " OR u.metin IS DISTINCT FROM s.metin)),"
    " count(*) FILTER (WHERE u.metin_durumu <> 'taslak'),"
    " count(*) FILTER (WHERE u.metin_durumu <> 'taslak' AND (u.content_hash <> s.content_hash"
    " OR u.metin IS DISTINCT FROM s.metin))"
    " FROM icerik.unit u JOIN pg_temp.staging_risale s ON s.anchor = u.anchor"
)
METIN_DEGISTI_CAPALAR: Final = (
    "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_risale s ON s.anchor = u.anchor"
    " WHERE u.metin_durumu = 'taslak' AND (u.content_hash <> s.content_hash"
    " OR u.metin IS DISTINCT FROM s.metin) ORDER BY u.anchor"
)
TR_STEM_NULL: Final = (
    "SELECT anchor, metin FROM icerik.unit WHERE source_id = %s AND metin_durumu = 'taslak'"
    " AND tr_stem IS NULL AND attrs ->> 'dil' = 'tr'"
)
TR_STEM_YAZ: Final = (
    "UPDATE icerik.unit SET tr_stem = %s, updated_at = now()"
    " WHERE anchor = %s AND tr_stem IS NULL AND metin_durumu = 'taslak'"
)


def _kopya_satiri(sira: int, s: RisaleSatiri) -> tuple[object, ...]:
    return (
        sira,
        s.anchor,
        s.role,
        s.parent_path,
        s.ord,
        s.metin,
        Jsonb(s.marks),
        [Range(bas, son, "[)") for bas, son in s.sentences],
        Jsonb(s.attrs),
        s.content_hash,
        s.tr_narrow,
        s.tr_wide,
        s.tr_stem,
        s.ar_norm,
        s.data_version,
        Jsonb(s.provenance),
        s.source_id,
    )


def _staging_yukle(conn: psycopg.Connection, girdi: RisaleGirdisi, source_id: str) -> int:
    """Dosyayi akitip `PARTI` satirlik `COPY`lerle gecici tabloya yazar; yazilan satir sayisi."""
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_risale")
    conn.execute(STAGING)
    sira = 0
    satirlar = satirlari_akit_risale(girdi.yol, source_id)
    bitti = False
    while not bitti:
        parti: list[tuple[object, ...]] = []
        for satir in satirlar:
            sira += 1
            parti.append(_kopya_satiri(sira, satir))
            if len(parti) >= PARTI:
                break
        else:
            bitti = True
        if parti:
            with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
                for kayit in parti:
                    kopya.write_row(kayit)
    conn.execute(STAGING_ANALIZ)
    return sira


def _denetimler(conn: psycopg.Connection, source_id: str) -> None:
    """Isleme ozgu denetimler; her biri ilk capalari iletiye yazar."""
    baska = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u JOIN pg_temp.staging_risale s ON s.anchor = u.anchor"
        " WHERE u.source_id <> s.source_id ORDER BY u.anchor",
    )
    if baska:
        raise GirdiHatasi(f"capa baska bir source_id altinda ({len(baska)}): {_capalar(baska)}")
    eksik = _capa_listesi(
        conn,
        "SELECT u.anchor FROM icerik.unit u WHERE u.source_id = %s AND NOT EXISTS"
        " (SELECT 1 FROM pg_temp.staging_risale s WHERE s.anchor = u.anchor) ORDER BY u.anchor",
        (source_id,),
    )
    if eksik:
        raise QaKaldi(
            f"onceki yuklemedeki capa staged icinde yok ({len(eksik)}): {_capalar(eksik)}"
        )
    bozuk = _capa_listesi(
        conn,
        "SELECT anchor FROM pg_temp.staging_risale"
        " WHERE content_hash::text <> encode(sha256(convert_to(metin, 'UTF8')), 'hex')"
        " ORDER BY anchor",
    )
    if bozuk:
        raise QaKaldi(f"content_hash metnin SHA-256'si degil ({len(bozuk)}): {_capalar(bozuk)}")


def _tr_stem_doldur(conn: psycopg.Connection, source_id: str) -> int:
    """`tr_stem IS NULL` Turkce taslak birimde `tr_stem`i veritabanindaki metinden hesaplar."""
    bos = conn.execute(TR_STEM_NULL, (source_id,)).fetchall()
    if not bos:
        return 0
    with conn.cursor() as imlec:
        imlec.executemany(TR_STEM_YAZ, [(tr_stem(str(metin)), str(capa)) for capa, metin in bos])
    return len(bos)


def _say3(conn: psycopg.Connection, sorgu: str) -> tuple[int, int, int]:
    satir = conn.execute(sorgu).fetchone()
    if satir is None:
        return 0, 0, 0
    return int(satir[0]), int(satir[1]), int(satir[2])


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Risale birimlerini ekler/gunceller; cagiran `conn.transaction()` icindedir.

    Siralama onemlidir: sayaclar INSERT'ten once hesaplanir (yeni birimler `var olan` degildir).
    """
    girdi = h.risale
    if girdi is None:
        raise GirdiHatasi("Risale hazirligi yok")
    try:
        ozet = lineage.sha256_dosya(girdi.yol)
    except OSError:
        raise GirdiHatasi(f"{UNITS_ADI} okunamadi") from None
    if ozet != girdi.sha256:
        raise GirdiHatasi(f"{UNITS_ADI} hazirliktan sonra degisti")
    yazilan = _staging_yukle(conn, girdi, h.source_id)
    if yazilan != girdi.satir_sayisi:
        raise GirdiHatasi(f"{UNITS_ADI} satir sayisi hazirliktan farkli")
    _denetimler(conn, h.source_id)
    metin_degisti, atlanan, atlanan_degisti = _say3(conn, SAYAC)
    degisen = _capa_listesi(conn, METIN_DEGISTI_CAPALAR) if metin_degisti else []
    eklenen = conn.execute(INSERT_UNIT, (ctx.run_id,)).rowcount
    guncellenen = conn.execute(UPDATE_UNIT, (ctx.run_id,)).rowcount
    tr_stem_dolan = _tr_stem_doldur(conn, h.source_id)
    if metin_degisti:
        ctx.uyar(
            f"{metin_degisti} taslak birimde metin ya da content_hash staged'den farkli:"
            f" degistirilmedi (Risale metni duzeltilmez): {_capalar(degisen)}"
        )
    if atlanan_degisti:
        ctx.uyar(f"{atlanan_degisti} taslak olmayan birimde metin staged'den farkli: dokunulmadi")
    return {
        "staging": yazilan,
        "kitap": girdi.kitap_sayisi,
        "eklenen": eklenen,
        "ayni_kalan": yazilan - eklenen - guncellenen - metin_degisti - atlanan,
        "guncellenen": guncellenen,
        "metin_degisti": metin_degisti,
        "atlanan_onayli": atlanan,
        "atlanan_metin_degisti": atlanan_degisti,
        "tr_stem_dolan": tr_stem_dolan,
    }


__all__ = ["RisaleGirdisi", "RisaleSatiri", "hazirla", "kaynak_denetle", "satir_coz", "yukle"]
