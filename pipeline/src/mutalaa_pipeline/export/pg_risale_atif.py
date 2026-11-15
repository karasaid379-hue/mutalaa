"""`export pg --source risale-atif-dizini`: Risale ayet atif adaylari, `xref` (A20.7b; K-52).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit,
`source` satiri `pg._source_satirlari` ile); sablon `pg_risale_sayfa.py`'dir. Dosya tarafi: kaynak
kaydi (G-KAY), son `enrich risale-citations` calismasi (`xrefs.jsonl`; `anchor` adimi), zincir
(atif -> `risale-rnk-metin` anchor -> normalize -> ingest), QA raporu (DORT kapi; kalan kapida
yukleme yapilmaz) ve satirlarin kati okunmasi. Veritabanina dokunmadan yapilir.

Sentetik fikstur (`test-risale-ornek`): iki sentetik `xref` satiri `xref.jsonl` dosyasindadir
(anchor calismasi); `pg_risale.hazirla` onu `fikstur_oku` ile okur, `pg._yukle` birimlerden
sonra AYNI islemde `yukle` ile yazar. Fiksturun hedefi gercek ayet capasidir (`q:1:1`, `q:1:2`);
hedef ayet `unit`te yoksa (Tanzil yuklenmemis) xref YAZILMAZ, uyari ve `xref_hedefi_yok`
sayaci yazilir, birimler yine yuklenir (fikstur Tanzil'siz de yuklenebilmeli).

YAZMA KURALI (Baglanti modeli §4 madde 3; K-27; K-47; Icerik hatti kurallari):

* Upsert `ON CONFLICT ON CONSTRAINT xref_natural_key` (`type, src_anchor, src_span, dst_anchor,
  dst_span`; NULLS NOT DISTINCT). Yeni satir `origin = 'hat'`, `status = 'aday'` girer.
* Var olan satirda YALNIZ `origin = 'hat' AND status = 'aday'` ise YALNIZ turetilmis sutunlar
  (`score`, `confidence`, `evidence`, `data_version`) guncellenir ve yalniz degeri farkliysa.
  `onayli`, `red` ve `origin <> 'hat'` satira HIC yazilmaz. Reddedilen baglanti ayni dogal
  anahtarla durdugu icin yeniden eklenmez ve guncellenmez.
* Onkosul (K-47): `src_anchor` ve `dst_anchor` birimleri `icerik.unit`te olmali, `src_span` kaynak
  birim metnine sigmali, `evidence.src_hash` birimin `content_hash` degerinin ilk 16 hanesi
  olmali. Biri tutmazsa islem geri alinir (cikis 1) ve veritabaninda hicbir sey degismez.
* Silme YOK: staged'de artik bulunmayan `hat` + `aday` satir yalniz sayilir
  (`onceki_aday_artik`). Kapsamli silme `--prune` bayragiyla (VARSAYILAN KAPALI) ve
  `--yedek-alindi` onayiyla acilir; yalniz `origin = 'hat' AND status = 'aday' AND
  evidence->>'source_id' = '<kaynak>'` ve `review` kaydi OLMAYAN satiri siler. UYARI: bu bir veri
  silme islemidir; calistirmadan once kullanici onayi ve `scripts/backup-db.ps1` yedegi gerekir.
* `--dry-run` baglanir, her seyi yapar ve geri alir (Rollback); hicbir sey yazilmaz.

`score` ve `confidence` staged'de binde tam sayidir (`score_binde`, `confidence_binde`; 0..1000):
veritabaninda `binde / 1000` olur (`xref.score`, `xref.confidence` `real`, 0..1). Fiksturun
`score` ve `confidence` alanlari 0 ya da 1 tam sayisidir ve `* 1000` binde olur.

Iletiler ve rapor yalniz sayi ve capa tasir; metin yazilmaz. Sayaclar: `xref_staging`,
`xref_eklenen`, `xref_guncellenen`, `xref_ayni_kalan`, `xref_korunan_onayli`, `xref_korunan_red`,
`xref_korunan_editor`, `onceki_aday_artik`, `xref_silinen`, `xref_prune_review_nedeniyle_atlanan`,
`xref_hedefi_yok`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import psycopg
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, Q, Rn, format, parse
from mutalaa_pipeline.enrich import risale_atif
from mutalaa_pipeline.enrich.risale_atif import KAYNAK_ID
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    _anchor_calismasi,
    _capa_listesi,
    _capalar,
    _manifest_ozet,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_ORNEK, KAYNAK_RNK
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_oku

KAYNAKLAR: Final = frozenset({KAYNAK_ID, KAYNAK_ORNEK})
FIKSTUR_XREF_ADI: Final = "xref.jsonl"
BINDE: Final = 1000
CONSTRAINT: Final = "xref_natural_key"
SRC_HASH_UZUNLUGU: Final = 16
HAT_SATIRLARI: Final = risale_atif.XREF_ALANLARI
FIKSTUR_SATIRLARI: Final = frozenset(
    {
        "confidence",
        "data_version",
        "dst_anchor",
        "dst_span",
        "evidence",
        "origin",
        "score",
        "src_anchor",
        "src_span",
        "status",
        "type",
    }
)
PRUNE_UYARISI: Final = (
    "--prune VERI SILER: kullanici onayi ve scripts/backup-db.ps1 yedegi olmadan calistirilmaz;"
    " --yedek-alindi ile yedegin alindigi onaylanmalidir"
)


@dataclass(frozen=True)
class XrefYuk:
    """Dogrulanmis `xref` aday satiri (binde puanlarla); metin tasimaz."""

    tur: str
    src_anchor: str
    src_span: tuple[int, int]
    dst_anchor: str
    dst_span: tuple[int, int] | None
    score_binde: int
    confidence_binde: int
    evidence: dict[str, object]
    data_version: str


def kaynak_denetle(source_id: str) -> None:
    if source_id not in KAYNAKLAR:
        raise GirdiHatasi(f"{source_id}: xref yuklemesi yalniz {KAYNAK_ID} ve fiksturu icindir")


def prune_denetle(source_id: str, prune: bool, yedek_alindi: bool, run: str | None = None) -> None:
    """`--prune` yalniz atif dizininde, varsayilan (en yeni) calismayla ve `--yedek-alindi` ile.

    `--run` ile eski bir zincir secilmisse `--prune` reddedilir (cikis 2): eski calismada
    olmayan guncel adaylar silinir, turetilmis sutunlar eski degere doner.
    """
    if yedek_alindi and not prune:
        raise GirdiHatasi("--yedek-alindi yalniz --prune ile birlikte verilir")
    if not prune:
        return
    if source_id != KAYNAK_ID:
        raise GirdiHatasi(f"--prune yalniz {KAYNAK_ID} icindir")
    if run is not None:
        raise GirdiHatasi(
            "--prune --run ile birlikte verilmez: silme yalniz en yeni calismayla yapilir"
        )
    if not yedek_alindi:
        raise GirdiHatasi(PRUNE_UYARISI)


# --- satirlari okuma -----------------------------------------------------------------------


def _aralik(yer: str, deger: object, bos_olabilir: bool) -> tuple[int, int] | None:
    if deger is None and bos_olabilir:
        return None
    if (
        isinstance(deger, list)
        and len(deger) == 2
        and all(isinstance(x, int) and not isinstance(x, bool) for x in deger)
        and 0 <= deger[0] < deger[1] <= 2147483647
    ):
        return int(deger[0]), int(deger[1])
    raise GirdiHatasi(f"{yer}: aralik [bas, son) gecersiz")


def _capa(yer: str, deger: object, tur: type) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi(f"{yer}: capa metin degil")
    try:
        ref = parse(deger)
    except AnchorError:
        raise GirdiHatasi(f"{yer}: capa gramere uymuyor") from None
    if format(ref) != deger or ref.span is not None or not isinstance(ref.anchor, tur):
        raise GirdiHatasi(f"{yer}: capa kanonik birim capasi degil")
    if isinstance(ref.anchor, Rn) and ref.anchor.s is not None:
        raise GirdiHatasi(f"{yer}: capa cumle capasi")
    if isinstance(ref.anchor, Q) and ref.anchor.ilk is not None:
        raise GirdiHatasi(f"{yer}: capa kelime capasi (birim duzeyi bekleniyor)")
    return deger


def _binde(yer: str, deger: object, olcek: int) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi(f"{yer}: tam sayi degil")
    sonuc = deger * olcek
    if not 0 <= sonuc <= BINDE:
        raise GirdiHatasi(f"{yer}: 0..1 (binde 0..1000) disinda")
    return sonuc


def _satir_coz(satir: Satir, source_id: str, fikstur: bool) -> XrefYuk:
    yer = f"{satir.etiket} satir {satir.no}"
    beklenen = FIKSTUR_SATIRLARI if fikstur else HAT_SATIRLARI
    if set(satir.veri) != beklenen:
        raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
    v = satir.veri
    tur = v["type"]
    if tur not in risale_atif.TURLER:
        raise GirdiHatasi(f"{yer}: type atif ya da iktibas degil")
    if v["origin"] != risale_atif.ORIGIN or v["status"] != risale_atif.STATUS:
        raise GirdiHatasi(f"{yer}: origin hat ve status aday olmali")
    evidence = v["evidence"]
    if not isinstance(evidence, dict):
        raise GirdiHatasi(f"{yer}: evidence nesne degil")
    risale_atif.evidence_denetle(evidence)
    if evidence.get("source_id") != source_id:
        raise GirdiHatasi(f"{yer}: evidence.source_id --source ile ayni degil")
    surum = satir.metin("data_version")
    if surum == "" or "\x00" in surum:
        raise GirdiHatasi(f"{yer}: data_version gecersiz")
    olcek = BINDE if fikstur else 1
    skor_alani, guven_alani = (
        ("score", "confidence") if fikstur else ("score_binde", "confidence_binde")
    )
    return XrefYuk(
        tur=str(tur),
        src_anchor=_capa(f"{yer}: src_anchor", v["src_anchor"], Rn),
        src_span=_aralik(f"{yer}: src_span", v["src_span"], False) or (0, 0),
        dst_anchor=_capa(f"{yer}: dst_anchor", v["dst_anchor"], Q),
        dst_span=_aralik(f"{yer}: dst_span", v["dst_span"], True),
        score_binde=_binde(f"{yer}: {skor_alani}", v[skor_alani], olcek),
        confidence_binde=_binde(f"{yer}: {guven_alani}", v[guven_alani], olcek),
        evidence=dict(evidence),
        data_version=surum,
    )


def satirlari_coz(veri: bytes, source_id: str, ad: str) -> list[XrefYuk]:
    """`xrefs.jsonl` / `xref.jsonl` baytlarini kati okur; iletiler yalniz satir/alan adi tasir."""
    fikstur = source_id == KAYNAK_ORNEK
    sonuc: list[XrefYuk] = []
    gorulen: set[tuple[object, ...]] = set()
    for satir in satirlari_oku(veri, ad):
        x = _satir_coz(satir, source_id, fikstur)
        anahtar = (x.tur, x.src_anchor, x.src_span, x.dst_anchor, x.dst_span)
        if anahtar in gorulen:
            raise GirdiHatasi(f"{ad} satir {satir.no}: yinelenen xref dogal anahtari")
        gorulen.add(anahtar)
        sonuc.append(x)
    if not sonuc:
        raise GirdiHatasi(f"{ad} bos")
    return sonuc


# --- hazirlik ------------------------------------------------------------------------------


def dosya_baytlari(
    ctx: RunContext, klasor: Path, manifest: Mapping[str, object], ad: str
) -> tuple[str, str, bytes]:
    """Anchor calismasinin `ad` dosyasi: `(veri koku yolu, sha256, bayt)`; ozet tutmali."""
    beklenen = _manifest_ozet(manifest, ad)
    if beklenen is None:
        raise GirdiHatasi(f"manifestte {ad} yok")
    dosya = klasor / ad
    try:
        veri = dosya.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{ad} okunamadi") from None
    sha = lineage.sha256_bayt(veri)
    if sha != beklenen:
        raise GirdiHatasi(f"{ad} ozeti manifestle tutmuyor")
    return lineage.goreli_yol(ctx.veri_kok, dosya), sha, veri


def fikstur_oku(
    ctx: RunContext, klasor: Path, manifest: Mapping[str, object], source_id: str
) -> tuple[str, str, list[XrefYuk]]:
    """Fiksturun `xref.jsonl` dosyasi: `(veri koku yolu, sha256, satirlar)`."""
    yol, sha, veri = dosya_baytlari(ctx, klasor, manifest, FIKSTUR_XREF_ADI)
    return yol, sha, satirlari_coz(veri, source_id, FIKSTUR_XREF_ADI)


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (atif dizini)."""
    if source_id != KAYNAK_ID:
        raise GirdiHatasi(f"{source_id}: xref satirlari birimlerle birlikte yuklenir (export pg)")
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("atif calistirmasinin ciktilari saglam degil")
    yol, sha, veri = dosya_baytlari(ctx, klasor, manifest, risale_atif.XREFS_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, _ham = _zincir_denetle(ctx, zincir, (KAYNAK_RNK,))
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)  # dort kapi; kalirsa yukleme yok
    satirlar = satirlari_coz(veri, source_id, risale_atif.XREFS_ADI)
    girdiler = [lineage.Girdi(yol, sha, anchor_run_id)]
    girdiler += [lineage.Girdi(g, o) for g, o in _gelen_girdileri(manifest) if o is not None]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham={slug: [] for slug in kaynak_idleri},  # ham dosyasi yok: alinma tarihi/ozet NULL
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler={slug: kaynaklar[slug].notice_text for slug in kaynak_idleri},
        parmak=ctx.parmak_izi(girdiler),
        xref=satirlar,
    )


def _gelen_girdileri(manifest: Mapping[str, object]) -> list[tuple[str, str | None]]:
    """Atif calismasinin Tanzil (`gelen/...`) girdileri: parmak izine girer."""
    sonuc: list[tuple[str, str | None]] = []
    girdiler = manifest.get("girdiler")
    if isinstance(girdiler, list):
        for k in girdiler:
            if (
                isinstance(k, dict)
                and isinstance(k.get("yol"), str)
                and k["yol"].startswith("gelen/")
            ):
                ozet = k.get("sha256")
                sonuc.append((str(k["yol"]), ozet if isinstance(ozet, str) else None))
    return sonuc


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    "CREATE TEMP TABLE staging_xref (sira integer, type icerik.xref_type,"
    ' src_anchor text COLLATE "C", src_span int4range, dst_anchor text COLLATE "C",'
    " dst_span int4range, score real,"
    " confidence real, evidence jsonb, data_version text) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_xref (sira, type, src_anchor, src_span, dst_anchor, dst_span, score,"
    " confidence, evidence, data_version) FROM STDIN"
)
STAGING_ANALIZ: Final = "ANALYZE pg_temp.staging_xref"
# Dogal anahtar eslesmesi (NULL'lar eslesir: xref_natural_key NULLS NOT DISTINCT).
ESLES: Final = (
    "x.type = s.type AND x.src_anchor = s.src_anchor AND x.src_span IS NOT DISTINCT FROM s.src_span"
    " AND x.dst_anchor = s.dst_anchor AND x.dst_span IS NOT DISTINCT FROM s.dst_span"
)
TUREV: Final = "(x.score, x.confidence, x.evidence, x.data_version)"
TUREV_S: Final = "(s.score, s.confidence, s.evidence, s.data_version)"
# K-47: iki ucta da birim olmali (src: Risale metni, dst: ayet).
EKSIK_DST: Final = (
    "SELECT DISTINCT s.dst_anchor FROM pg_temp.staging_xref s WHERE NOT EXISTS"
    " (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.dst_anchor) ORDER BY s.dst_anchor"
)
EKSIK_SRC: Final = (
    "SELECT DISTINCT s.src_anchor FROM pg_temp.staging_xref s WHERE NOT EXISTS"
    " (SELECT 1 FROM icerik.unit u WHERE u.anchor = s.src_anchor) ORDER BY s.src_anchor"
)
# src_span kaynak birim metnine sigmali (kod noktasi: char_length); ozet degismemis olmali.
SPAN_TASAN: Final = (
    "SELECT s.src_anchor FROM pg_temp.staging_xref s JOIN icerik.unit u ON u.anchor = s.src_anchor"
    " WHERE upper(s.src_span) > char_length(u.metin) ORDER BY s.sira"
)
OZET_FARKI: Final = (
    "SELECT s.src_anchor FROM pg_temp.staging_xref s JOIN icerik.unit u ON u.anchor = s.src_anchor"
    " WHERE s.evidence ? 'src_hash' AND s.evidence->>'src_hash' <> left(u.content_hash, 16)"
    " ORDER BY s.sira"
)
# Yazimdan ONCE sayaclar: yeni, guncellenecek, ayni, korunan onayli, red, editor aday.
SAYAC: Final = (
    "SELECT count(*) FILTER (WHERE x.id IS NULL),"
    " count(*) FILTER (WHERE x.origin = 'hat' AND x.status = 'aday'"
    f" AND {TUREV} IS DISTINCT FROM {TUREV_S}),"
    " count(*) FILTER (WHERE x.origin = 'hat' AND x.status = 'aday'"
    f" AND {TUREV} IS NOT DISTINCT FROM {TUREV_S}),"
    " count(*) FILTER (WHERE x.status = 'onayli'),"
    " count(*) FILTER (WHERE x.status = 'red'),"
    " count(*) FILTER (WHERE x.status = 'aday' AND x.origin <> 'hat')"
    f" FROM pg_temp.staging_xref s LEFT JOIN icerik.xref x ON {ESLES}"
)
# Staged'de artik bulunmayan onceki `hat` + `aday` satirlar (kaynak kapsami).
ARTIK_KOSUL: Final = (
    "x.origin = 'hat' AND x.status = 'aday' AND x.evidence->>'source_id' = %s"
    " AND NOT EXISTS (SELECT 1 FROM pg_temp.staging_xref s WHERE " + ESLES + ")"
)
ARTIK: Final = "SELECT count(*) FROM icerik.xref x WHERE " + ARTIK_KOSUL
# Yalniz yeni satir ekler; var olan satirda yalniz `hat` + `aday` ve yalniz turetilmis sutunlar.
UPSERT: Final = (
    "INSERT INTO icerik.xref AS x (src_anchor, src_span, dst_anchor, dst_span, type, score,"
    " confidence, evidence, origin, status, data_version)"
    " SELECT s.src_anchor, s.src_span, s.dst_anchor, s.dst_span, s.type, s.score, s.confidence,"
    " s.evidence, 'hat', 'aday', s.data_version FROM pg_temp.staging_xref s ORDER BY s.sira"
    f" ON CONFLICT ON CONSTRAINT {CONSTRAINT} DO UPDATE SET score = EXCLUDED.score,"
    " confidence = EXCLUDED.confidence, evidence = EXCLUDED.evidence,"
    " data_version = EXCLUDED.data_version"
    " WHERE x.origin = 'hat' AND x.status = 'aday'"
    " AND (x.score, x.confidence, x.evidence, x.data_version) IS DISTINCT FROM"
    " (EXCLUDED.score, EXCLUDED.confidence, EXCLUDED.evidence, EXCLUDED.data_version)"
)
# `--prune`: kapsami `origin = 'hat' AND status = 'aday' AND evidence->>'source_id'` ve review yok.
PRUNE_REVIEW: Final = (
    "SELECT count(*) FROM icerik.xref x WHERE "
    + ARTIK_KOSUL
    + " AND EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)"
)
PRUNE: Final = (
    "DELETE FROM icerik.xref x WHERE "
    + ARTIK_KOSUL
    + " AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)"
)


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[XrefYuk]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_xref")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for sira, s in enumerate(satirlar, start=1):
            kopya.write_row(
                (
                    sira,
                    s.tur,
                    s.src_anchor,
                    Range(s.src_span[0], s.src_span[1], "[)"),
                    s.dst_anchor,
                    None if s.dst_span is None else Range(s.dst_span[0], s.dst_span[1], "[)"),
                    s.score_binde / BINDE,
                    s.confidence_binde / BINDE,
                    Jsonb(s.evidence),
                    s.data_version,
                )
            )
    conn.execute(STAGING_ANALIZ)


def _say(conn: psycopg.Connection, sorgu: str, parametre: Sequence[object] = ()) -> int:
    satir = conn.execute(sorgu, parametre).fetchone()
    return int(satir[0]) if satir is not None else 0


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """`xref` adaylarini ekler/gunceller; cagiran `conn.transaction()` icindedir.

    Onkosul eksiginde `QaKaldi` (cikis 1, islem geri alinir). Sayaclar modul belgesindedir.
    """
    satirlar = h.xref
    if not satirlar:
        raise GirdiHatasi("xref hazirligi yok")
    kaynak = h.source_id
    kaynak_denetle(kaynak)
    fikstur = kaynak == KAYNAK_ORNEK
    _staging_yukle(conn, satirlar)
    eksik_src = _capa_listesi(conn, EKSIK_SRC)
    if eksik_src:
        raise QaKaldi(
            f"xref kaynak ucu unit'te yok ({len(eksik_src)}): {_capalar(eksik_src)}"
            f" (once export pg --source {KAYNAK_RNK if not fikstur else kaynak})"
        )
    eksik_dst = _capa_listesi(conn, EKSIK_DST)
    if eksik_dst:
        if not fikstur:
            raise QaKaldi(
                f"xref hedef ayeti unit'te yok ({len(eksik_dst)}): {_capalar(eksik_dst)}"
                " (once export pg --source tanzil-uthmani)"
            )
        ctx.uyar(
            f"fikstur xref hedef ayeti unit'te yok ({len(eksik_dst)}): xref yazilmadi"
            " (once export pg --source tanzil-uthmani)"
        )
        return {"xref_staging": len(satirlar), "xref_hedefi_yok": len(eksik_dst)}
    tasan = _capa_listesi(conn, SPAN_TASAN)
    if tasan:
        raise QaKaldi(f"xref src_span birim metnine sigmiyor ({len(tasan)}): {_capalar(tasan)}")
    ozet = _capa_listesi(conn, OZET_FARKI)
    if ozet:
        raise QaKaldi(
            f"xref kaynak birimi staged'den sonra degismis ({len(ozet)}): {_capalar(ozet)}"
            " (enrich risale-citations yeniden calismali)"
        )
    sonuc = conn.execute(SAYAC).fetchone()  # toplama sorgusu her zaman bir satir doner
    eklenecek, guncellenecek, ayni, onayli, red, editor = (
        [int(x) for x in sonuc] if sonuc is not None else [0] * 6
    )
    artik = _say(conn, ARTIK, (kaynak,))
    yazilan = conn.execute(UPSERT).rowcount
    if yazilan != eklenecek + guncellenecek:
        raise QaKaldi(
            f"xref yazimi beklenenden farkli ({yazilan} satir, beklenen"
            f" {eklenecek + guncellenecek})"
        )
    silinen = review_atlanan = 0
    if h.xref_prune:
        ctx.uyar(PRUNE_UYARISI)
        review_atlanan = _say(conn, PRUNE_REVIEW, (kaynak,))
        silinen = conn.execute(PRUNE, (kaynak,)).rowcount
    elif artik:
        ctx.uyar(f"{artik} onceki aday staged'de yok: silinmedi (--prune ile ve onayla silinir)")
    if onayli or red or editor:
        ctx.uyar(f"{onayli + red + editor} xref onayli/red/editor kararli: dokunulmadi")
    return {
        "xref_staging": len(satirlar),
        "xref_eklenen": eklenecek,
        "xref_guncellenen": guncellenecek,
        "xref_ayni_kalan": ayni,
        "xref_korunan_onayli": onayli,
        "xref_korunan_red": red,
        "xref_korunan_editor": editor,
        "onceki_aday_artik": artik,
        "xref_silinen": silinen,
        "xref_prune_review_nedeniyle_atlanan": review_atlanan,
    }


__all__ = [
    "KAYNAKLAR",
    "XrefYuk",
    "fikstur_oku",
    "hazirla",
    "kaynak_denetle",
    "prune_denetle",
    "satirlari_coz",
    "yukle",
]
