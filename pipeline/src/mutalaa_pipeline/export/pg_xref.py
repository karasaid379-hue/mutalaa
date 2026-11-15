"""`export pg --source xref-baglantilar`: `kok`, `lemma` ve `benzer_ayet` baglantilari (A18.3).

`--source` adi `xref-baglantilar`dir: staged klasoru (`staged/xref-baglantilar/{run_id}/`, adim
`enrich`) ve advisory kilit adidir; icerik kaynagi degildir. `evidence.source_id` degerleri
(`qac-morfoloji`, `tanzil-uthmani`, `qursim`) kayitli kaynaklardir. `qursim` kaynak satiri bu
yuklemede eklenir (alinma tarihi ve dosya ozeti `data/gelen` girdisinden); `qac-morfoloji` ve
`tanzil-uthmani` satirlari onceden bulunmalidir. Akis (`export/pg_tr_roots.py` deseni): dosya
onkosullari (kaynak kayitlari, son `enrich` calismasi ve ciktilari, QA raporu: G-KAY, G-BUT,
G-CAP) -> tek veritabani islemi (advisory kilit, `source` satiri `export/pg.py` ortak kodunda,
staging + COPY).

YAZMA KURALLARI (Baglanti modeli §4 madde 3; K-51 madde 8)

* Dogal anahtar `UNIQUE NULLS NOT DISTINCT (type, src_anchor, src_span, dst_anchor, dst_span)`;
  hat yalniz `origin = 'hat'` ve `status = 'aday'` satiri gunceller (`score`, `confidence`,
  `evidence`, `data_version`; `id` ve `status` korunur; yalniz FARKLIYSA yazilir: ikinci kosu 0
  degisiklik). `onayli`, `red` ve editor satirlarina dokunulmaz (sayilir).
* Bu kosuda uretilmeyen `origin = 'hat'` ve `status = 'aday'` satir SILINIR; kapsam yalniz
  staged'in turleridir (`kok` kosusu `lemma` satirina dokunmaz). Bir `review` kaydina bagli aday
  satir silinmez (sayilir).
* Uretilmeyen `onayli` hat satiri SILINMEZ: yeniden dogrulama `review` kaydi acilir (`hedef_tablo
  = 'xref'`, `hedef_anahtar` = xref kimligi, `xref_id`, `alan = 'status'`, `eylem = 'oner'`,
  `koken = oneren = 'hat'`, `onerilen = {"yeniden_dogrula": true, "neden": "uretilmedi"}`). Uc
  birim metni degismisse (`evidence.src_hash` ya da `dst_hash` birimin guncel `content_hash` ilk 16
  hanesiyle uyusmuyor) ayni kayit `neden = "uc_metni_degisti"` ile acilir (uretilse de uretilmese
  de; bu neden onceliklidir). Ayni `xref_id` icin ACIK kayit varsa yenisi acilmaz. Otomatik
  turler icin baska `review` ACILMAZ (K-51 madde 8).
* Staged ayet ozetleri veritabanindaki guncel `content_hash` ile tutmuyorsa yukleme `GirdiHatasi`
  (cikis 2) ile durur: `enrich links` yeniden kosulmalidir.

Yukleme sonunda `qa/checks/xref.sql_hatalari` calisir; ihlal varsa islem geri alinir
(kok ve lemma tutarliligi %100, kayitsiz `source_id` 0, aday ozeti guncel). Iletiler yalniz sayi,
kimlik ve capa tasir. Sayaclar: `xref_*`, `review_*`.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_links import LINKS_ADIMI, LINKS_DOSYASI
from mutalaa_pipeline.enrich.baglantilar.uret import (
    QAC_KAYNAGI,
    QURSIM_KAYNAGI,
    TURLER,
    UTHMANI_KAYNAGI,
    sayisal,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import Hazirlik, _qa_denetle
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.qa.checks.xref import GEREKLI_KAYITLAR, sql_hatalari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku

ORIGIN: Final = "hat"
YUKLENEN_KAYNAK: Final = QURSIM_KAYNAGI  # `source` satiri bu yuklemede eklenen kaynak
ONCEDEN_VAR: Final = (QAC_KAYNAGI, UTHMANI_KAYNAGI)
NEDEN_URETILMEDI: Final = "uretilmedi"
NEDEN_UC_METNI: Final = "uc_metni_degisti"


@dataclass(frozen=True)
class XrefSatiri:
    tur: str
    src_anchor: str
    dst_anchor: str
    score: float
    confidence: float
    evidence: dict[str, object]
    data_version: str


@dataclass
class XrefHazirlik(Hazirlik):
    """`Hazirlik` + staged baglanti satirlari ve uretilen turler."""

    xref_satirlari: list[XrefSatiri] = field(default_factory=list)
    turler: tuple[str, ...] = ()


# --- satirlari okuma ---------------------------------------------------------------------


def xref_satirlari_oku(veri: bytes) -> list[XrefSatiri]:
    """Staged baglanti dosyasi -> `XrefSatiri` (ondalik dizgeler sayiya cevrilir; kati)."""
    sonuc: list[XrefSatiri] = []
    for s in satirlari_oku(veri, LINKS_DOSYASI):
        try:
            v = sayisal(s.veri)
        except ValueError:
            raise GirdiHatasi(f"{LINKS_DOSYASI} satir {s.no}: ondalik alan gecersiz") from None
        tur, src, dst, kanit, surum = (
            v.get("type"),
            v.get("src_anchor"),
            v.get("dst_anchor"),
            v.get("evidence"),
            v.get("data_version"),
        )
        if (
            tur not in TURLER
            or not isinstance(src, str)
            or not isinstance(dst, str)
            or not isinstance(kanit, dict)
            or not isinstance(surum, str)
        ):
            raise GirdiHatasi(f"{LINKS_DOSYASI} satir {s.no}: tur, capa ya da evidence gecersiz")
        skor, guven = v["score"], v["confidence"]
        assert isinstance(skor, float) and isinstance(guven, float)
        sonuc.append(XrefSatiri(str(tur), src, dst, skor, guven, kanit, surum))
    return sonuc


def _ham_girdiler(ctx: RunContext, manifest: Mapping[str, object]) -> list[dict[str, str]]:
    """`qursim` ham dosyasi (`gelen/qursim/<tarih>/...`): `source.alinma_tarihi` ve ozet icin."""
    sonuc: list[dict[str, str]] = []
    for yol, ozet in lineage_girdileri(manifest):
        parcalar = yol.split("/")
        if len(parcalar) == 4 and parcalar[0] == "gelen" and parcalar[1] == QURSIM_KAYNAGI:
            if ozet is None or lineage.OZET_DESENI.fullmatch(ozet) is None:
                raise GirdiHatasi("enrich manifestinde QurSim girdi ozeti gecersiz")
            dosya = ctx.veri_kok / yol
            if not dosya.is_file() or lineage.sha256_dosya(dosya) != ozet:
                raise GirdiHatasi("QurSim dosyasi yok ya da ozeti manifestle tutmuyor")
            sonuc.append({"yol": yol, "sha256": ozet})
    return sonuc


def lineage_girdileri(manifest: Mapping[str, object]) -> list[tuple[str, str | None]]:
    kayitlar = manifest.get("girdiler")
    sonuc: list[tuple[str, str | None]] = []
    for k in kayitlar if isinstance(kayitlar, list) else []:
        if isinstance(k, dict) and isinstance(k.get("yol"), str):
            ozet = k.get("sha256")
            sonuc.append((str(k["yol"]), ozet if isinstance(ozet, str) else None))
    return sonuc


# --- hazirlik ----------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (xref-baglantilar kaynagi)."""
    kaynaklar = ctx.require_sources((*GEREKLI_KAYITLAR, *ek_kaynaklar))  # G-KAY: kayit gecerli
    klasor_ust = ctx.staged_kaynak_dizini(source_id)
    if run is not None:
        if lineage.RUN_ID_DESENI.fullmatch(run) is None:
            raise GirdiHatasi("--run bir UUID degil")
        secilen = next((k for k in lineage.calismalar(klasor_ust) if k[0] == run), None)
        if secilen is None or secilen[2].get("adim") != LINKS_ADIMI:
            raise GirdiHatasi("--run icin manifestli enrich calistirmasi yok")
    else:
        secilen = lineage.son_basarili(klasor_ust, LINKS_ADIMI)
        if secilen is None:
            raise GirdiHatasi("manifestli enrich calistirmasi yok (once enrich links)")
    enrich_run_id, klasor, manifest = secilen
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("enrich calistirmasinin ciktilari saglam degil")
    veri, sha = _dosya_oku(klasor, manifest, LINKS_DOSYASI)
    qa_rapor_id = _qa_denetle(ctx, source_id, enrich_run_id, sha)
    ayrintilar = manifest.get("ayrintilar")
    turler = ayrintilar.get("turler") if isinstance(ayrintilar, dict) else None
    if (
        not isinstance(turler, list)
        or not turler
        or not all(isinstance(t, str) and t in TURLER for t in turler)
    ):
        raise GirdiHatasi("enrich manifestinde turler yok ya da gecersiz")
    satirlar = xref_satirlari_oku(veri)
    if any(s.tur not in turler for s in satirlar):
        raise GirdiHatasi("staged dosyasinda manifestte listelenmeyen tur var")
    ham = _ham_girdiler(ctx, manifest)
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / LINKS_DOSYASI)
    kaynak_idleri = (YUKLENEN_KAYNAK,)
    return XrefHazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=enrich_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=[],
        ingest={},
        ham={slug: ham if slug == QURSIM_KAYNAGI else [] for slug in kaynak_idleri},
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=dict.fromkeys(kaynak_idleri),
        parmak=ctx.parmak_izi([lineage.Girdi(yol, sha, enrich_run_id)]),
        xref_satirlari=satirlar,
        turler=tuple(str(t) for t in turler),
    )


# --- veritabani --------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_xref (tur text, src_anchor text COLLATE "C",'
    ' src_span int4range, dst_anchor text COLLATE "C", dst_span int4range, score real,'
    " confidence real, evidence jsonb, data_version text) ON COMMIT DROP"
)
COPY: Final = (
    "COPY pg_temp.staging_xref (tur, src_anchor, src_span, dst_anchor, dst_span, score,"
    " confidence, evidence, data_version) FROM STDIN"
)
# Staged satirin dogal anahtarla eslestigi var olan xref satiri (NULL span'lar esit sayilir).
ESLESME: Final = (
    "x.type = s.tur::icerik.xref_type AND x.src_anchor = s.src_anchor AND x.dst_anchor ="
    " s.dst_anchor AND x.src_span IS NOT DISTINCT FROM s.src_span AND x.dst_span IS NOT DISTINCT"
    " FROM s.dst_span"
)
# Staged ozeti, birimin GUNCEL content_hash ilk 16 hanesiyle tutmali (yoksa enrich eski).
ESKI_OZET: Final = (
    "SELECT count(*) FROM pg_temp.staging_xref s WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u"
    " WHERE u.kind = 'ayet' AND u.source_id = %(kaynak)s AND u.anchor = s.src_anchor AND"
    " left(u.content_hash, 16) = s.evidence ->> 'src_hash') OR NOT EXISTS (SELECT 1 FROM"
    " icerik.unit u WHERE u.kind = 'ayet' AND u.source_id = %(kaynak)s AND u.anchor ="
    " s.dst_anchor AND left(u.content_hash, 16) = s.evidence ->> 'dst_hash')"
)
DOKUNULMAYAN: Final = (
    "SELECT x.status::text, x.origin::text, count(*) FROM pg_temp.staging_xref s JOIN"
    " icerik.xref x ON " + ESLESME + " WHERE NOT (x.origin = 'hat' AND x.status = 'aday')"
    " GROUP BY 1, 2"
)
GUNCELLE: Final = (
    "UPDATE icerik.xref x SET score = s.score, confidence = s.confidence, evidence = s.evidence,"
    " data_version = s.data_version FROM pg_temp.staging_xref s WHERE " + ESLESME + " AND"
    " x.origin = 'hat' AND x.status = 'aday' AND (x.score, x.confidence, x.evidence,"
    " x.data_version) IS DISTINCT FROM (s.score, s.confidence, s.evidence, s.data_version)"
)
EKLE: Final = (
    "INSERT INTO icerik.xref (src_anchor, src_span, dst_anchor, dst_span, type, score,"
    " confidence, evidence, origin, status, data_version) SELECT s.src_anchor, s.src_span,"
    " s.dst_anchor, s.dst_span, s.tur::icerik.xref_type, s.score, s.confidence, s.evidence,"
    " 'hat', 'aday', s.data_version FROM pg_temp.staging_xref s WHERE NOT EXISTS (SELECT 1 FROM"
    " icerik.xref x WHERE " + ESLESME + ") ORDER BY s.tur, s.src_anchor, s.dst_anchor"
    " ON CONFLICT ON CONSTRAINT xref_natural_key DO NOTHING"
)
# Kapsam: staged'in turleri. Bir review kaydina bagli aday satir silinmez (FK).
SIL_KAPSAM: Final = (
    "x.type::text = ANY(%(turler)s) AND x.origin = 'hat' AND x.status = 'aday' AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_xref s WHERE " + ESLESME + ")"
)
SIL: Final = (
    "DELETE FROM icerik.xref x WHERE "
    + SIL_KAPSAM
    + " AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)"
)
SIL_ENGELLENEN: Final = (
    "SELECT count(*) FROM icerik.xref x WHERE "
    + SIL_KAPSAM
    + " AND EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)"
)
_ESKI_UC: Final = (
    "(NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.kind = 'ayet' AND u.source_id = %(kaynak)s"
    " AND u.anchor = x.src_anchor AND left(u.content_hash, 16) = x.evidence ->> 'src_hash')"
    " OR NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.kind = 'ayet' AND u.source_id ="
    " %(kaynak)s AND u.anchor = x.dst_anchor AND left(u.content_hash, 16) ="
    " x.evidence ->> 'dst_hash'))"
)
YENIDEN_DOGRULA_ADAYLARI: Final = (
    "WITH aday AS (SELECT x.id, x.type, x.src_anchor, x.dst_anchor, CASE WHEN " + _ESKI_UC + " THEN"
    " 'uc_metni_degisti' WHEN NOT EXISTS (SELECT 1 FROM pg_temp.staging_xref s WHERE "
    + ESLESME
    + ") THEN 'uretilmedi' END AS neden FROM icerik.xref x WHERE x.type::text = ANY(%(turler)s)"
    " AND x.origin = 'hat' AND x.status = 'onayli')"
)
YENIDEN_DOGRULA_ACIK: Final = (
    " SELECT a.neden, EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = a.id AND r.durum ="
    " 'acik') FROM aday a WHERE a.neden IS NOT NULL"
)
YENIDEN_DOGRULA_EKLE: Final = (
    " INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, xref_id, alan, eylem, onerilen,"
    " koken, oneren) SELECT 'xref', a.id::text, a.id, 'status', 'oner',"
    " jsonb_build_object('yeniden_dogrula', true, 'neden', a.neden), 'hat', 'hat' FROM aday a"
    " WHERE a.neden IS NOT NULL AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id ="
    " a.id AND r.durum = 'acik') ORDER BY a.type, a.src_anchor, a.dst_anchor RETURNING"
    " onerilen ->> 'neden'"
)


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[XrefSatiri]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_xref")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(COPY) as kopya:
        for s in satirlar:
            kopya.write_row(
                (
                    s.tur,
                    s.src_anchor,
                    None,
                    s.dst_anchor,
                    None,
                    s.score,
                    s.confidence,
                    Jsonb(s.evidence),
                    s.data_version,
                )
            )


def _say(
    conn: psycopg.Connection, sorgu: str, parametre: Mapping[str, object] | None = None
) -> int:
    satir = conn.execute(sorgu, parametre).fetchone()
    return int(satir[0]) if satir is not None else 0


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Baglantilari yazar (cagiran `conn.transaction()` icindedir)."""
    if not isinstance(h, XrefHazirlik):
        raise TypeError("xref-baglantilar yuklemesi XrefHazirlik ister")
    eksik = [
        slug
        for slug in ONCEDEN_VAR
        if conn.execute("SELECT 1 FROM icerik.source WHERE slug = %s", (slug,)).fetchone() is None
    ]
    if eksik:
        raise GirdiHatasi(
            f"kaynak satiri veritabaninda yok: {', '.join(eksik)} (once export pg --source ...)"
        )
    _staging_yukle(conn, h.xref_satirlari)
    parametre = {"kaynak": UTHMANI_KAYNAGI, "turler": list(h.turler)}
    eski = _say(conn, ESKI_OZET, parametre)
    if eski:
        raise GirdiHatasi(
            f"{eski} staged satirin ayet ozeti veritabaniyla tutmuyor (once enrich links)"
        )
    dokunulmayan: dict[str, int] = {"onayli": 0, "red": 0, "editor_ve_diger": 0}
    for durum, origin, n in conn.execute(DOKUNULMAYAN).fetchall():
        if origin == ORIGIN and durum == "onayli":
            dokunulmayan["onayli"] += int(n)
        elif origin == ORIGIN and durum == "red":
            dokunulmayan["red"] += int(n)
        else:
            dokunulmayan["editor_ve_diger"] += int(n)
    guncellenen = conn.execute(GUNCELLE).rowcount
    eklenen = conn.execute(EKLE).rowcount
    sil_engellenen = _say(conn, SIL_ENGELLENEN, parametre)
    silinen = conn.execute(SIL, parametre).rowcount

    adaylar = conn.execute(YENIDEN_DOGRULA_ADAYLARI + YENIDEN_DOGRULA_ACIK, parametre).fetchall()
    zaten_acik = sum(1 for _, acik in adaylar if acik)
    acilan = [
        str(n)
        for (n,) in conn.execute(
            YENIDEN_DOGRULA_ADAYLARI + YENIDEN_DOGRULA_EKLE, parametre
        ).fetchall()
    ]
    sayilar: dict[str, int] = {
        "xref_staging": len(h.xref_satirlari),
        "xref_eklenen": eklenen,
        "xref_guncellenen": guncellenen,
        "xref_silinen": silinen,
        "xref_silinmeyen_review_bagli": sil_engellenen,
        "xref_korunan_onayli": dokunulmayan["onayli"],
        "xref_korunan_red": dokunulmayan["red"],
        "xref_korunan_editor_ve_diger": dokunulmayan["editor_ve_diger"],
        "review_uretilmedi_acilan": sum(1 for n in acilan if n == NEDEN_URETILMEDI),
        "review_uc_metni_degisti_acilan": sum(1 for n in acilan if n == NEDEN_UC_METNI),
        "review_zaten_acik": zaten_acik,
    }
    sayilar["xref_degismeyen"] = (
        len(h.xref_satirlari)
        - eklenen
        - guncellenen
        - dokunulmayan["onayli"]
        - dokunulmayan["red"]
        - dokunulmayan["editor_ve_diger"]
    )
    for tur in h.turler:
        sayilar[f"xref_staging_{tur}"] = sum(1 for s in h.xref_satirlari if s.tur == tur)
    hatalar = sql_hatalari(conn, h.turler)
    ihlal = [f"{ad} {n}" for ad, n in hatalar.items() if n]
    if ihlal:
        raise QaKaldi("xref SQL denetimi (0 olmali): " + "; ".join(ihlal))
    ctx.gunluk.bilgi("export_pg_xref", **{k: v for k, v in sayilar.items() if v})
    return sayilar
