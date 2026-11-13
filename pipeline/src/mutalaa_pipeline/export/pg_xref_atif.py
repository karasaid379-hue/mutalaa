"""`export pg --source xref-atif-iktibas`: acik atif ve iktibas baglantilari (A18.4).

`--source` adi `xref-atif-iktibas`tir: staged klasoru (`staged/xref-atif-iktibas/{run_id}/`, adim
`enrich`) ve advisory kilit adidir; icerik kaynagi degildir (A18.3 `xref-baglantilar` deseni).
`evidence.source_id` degerleri (`tanzil-uthmani`, `tanzil-simple-clean`) onceden bulunan kayitli
kaynaklardir; bu yukleme `source` satiri yazmaz. Akis (`export/pg_xref.py` deseni): dosya
onkosullari (kaynak kayitlari, son `enrich` calismasi ve ciktilari, QA raporu: G-KAY, G-BUT,
G-CAP) -> tek veritabani islemi (advisory kilit, staging + COPY).

YAZMA KURALLARI (Baglanti modeli §4 madde 3; K-51 madde 8)

* Dogal anahtar `UNIQUE NULLS NOT DISTINCT (type, src_anchor, src_span, dst_anchor, dst_span)`;
  hat yalniz `origin = 'hat'` ve `status = 'aday'` satiri gunceller (`score`, `confidence`,
  `evidence`, `data_version`; `id` ve `status` korunur; yalniz FARKLIYSA yazilir: ikinci kosu 0
  degisiklik). `onayli`, `red` ve editor satirlarina dokunulmaz (sayilir).
* Bu kosuda uretilmeyen `origin = 'hat'` ve `status = 'aday'` satir SILINIR; kapsam yalniz
  staged'in turleri ve taranan meallerin birimleridir (`src_anchor` onekli). Insan onayi isteyen
  turde her aday satirin `review` kaydi vardir (yeni aday icin asagida); silinecek satirin hat
  tarafindan acilmis, hic dokunulmamis (`inceleyen` ve `duzenlenen` bos) ACIK `review` kaydi once
  silinir. Baska bir kayda (kapali, editor duzenlemeli) bagli aday satir silinmez (sayilir).
* Uretilmeyen `onayli` hat satiri SILINMEZ: yeniden dogrulama `review` kaydi acilir (`alan =
  'status'`, `eylem = 'oner'`, `onerilen = {"yeniden_dogrula": true, "neden": "uretilmedi"}`);
  uc birim metni degismisse (`evidence.src_hash` ya da `dst_hash` birimin guncel `content_hash`
  ilk 16 haneyle uyusmuyor) `neden = "uc_metni_degisti"` (oncelikli). Ayni `xref_id` icin ACIK
  kayit varsa yenisi acilmaz.
* Her YENI (ya da henuz hic `review` kaydi olmayan) aday satir icin `review` acilir (`atif` ve
  `iktibas` insan onayi ister): `hedef_tablo = 'xref'`, `hedef_anahtar` = xref kimligi, `xref_id`,
  `alan = 'status'`, `eylem = 'oner'`, `koken = oneren = 'hat'`, `guven = confidence`,
  `onerilen = {score, confidence, sinif_ipucu}`. Ayni `xref_id` icin HERHANGI durumda kayit
  varsa yenisi acilmaz (kapali karar yeniden acilmaz).
* Staged birim ozetleri veritabanindaki guncel `content_hash` ile tutmuyorsa yukleme `GirdiHatasi`
  (cikis 2) ile durur: `enrich citations` yeniden kosulmalidir.

Yukleme sonunda `qa/checks/xref_atif.sql_hatalari` calisir; ihlal varsa islem geri alinir.
Iletiler yalniz sayi, kimlik ve capa tasir. Sayaclar: `xref_*`, `review_*`.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg
from psycopg.types.json import Jsonb
from psycopg.types.range import Range

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_citations import (
    CITATIONS_ADIMI,
    CITATIONS_DOSYASI,
)
from mutalaa_pipeline.enrich.citations.kurallar import sinif_ipucu
from mutalaa_pipeline.enrich.citations.uret import TURLER, UTHMANI_KAYNAGI, sayisal
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import Hazirlik, _qa_denetle
from mutalaa_pipeline.export.pg_xref import (
    DOKUNULMAYAN,
    EKLE,
    ESLESME,
    GUNCELLE,
    NEDEN_UC_METNI,
    NEDEN_URETILMEDI,
    ORIGIN,
)
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.ingest.meal_kaynaklari import MEAL_KAYNAKLARI, capa_onegi
from mutalaa_pipeline.qa.checks.xref_atif import GEREKLI_KAYITLAR, sql_hatalari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import satirlari_oku


@dataclass(frozen=True)
class AtifSatiri:
    tur: str
    src_anchor: str
    src_span: tuple[int, int]
    dst_anchor: str
    dst_span: tuple[int, int] | None
    score: float
    confidence: float
    evidence: dict[str, object]
    data_version: str
    sinif: str


@dataclass
class AtifHazirlik(Hazirlik):
    """`Hazirlik` + staged atif/iktibas satirlari, taranan mealler ve turler."""

    xref_satirlari: list[AtifSatiri] = field(default_factory=list)
    hedefler: tuple[str, ...] = ()
    turler: tuple[str, ...] = TURLER


# --- satirlari okuma ---------------------------------------------------------------------


def _aralik(deger: object, ad: str, no: int, *, bos_olabilir: bool) -> tuple[int, int] | None:
    if deger is None and bos_olabilir:
        return None
    if (
        isinstance(deger, list)
        and len(deger) == 2
        and all(isinstance(x, int) and not isinstance(x, bool) for x in deger)
        and 0 <= deger[0] < deger[1]
    ):
        return int(deger[0]), int(deger[1])
    raise GirdiHatasi(f"{CITATIONS_DOSYASI} satir {no}: {ad} gecersiz")


def xref_satirlari_oku(veri: bytes) -> list[AtifSatiri]:
    """Staged dosya -> `AtifSatiri` (ondalik dizgeler sayiya cevrilir; kati)."""
    sonuc: list[AtifSatiri] = []
    for s in satirlari_oku(veri, CITATIONS_DOSYASI, bos_olabilir=True):
        try:
            v = sayisal(s.veri)
        except ValueError:
            raise GirdiHatasi(f"{CITATIONS_DOSYASI} satir {s.no}: ondalik alan gecersiz") from None
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
            raise GirdiHatasi(
                f"{CITATIONS_DOSYASI} satir {s.no}: tur, capa ya da evidence gecersiz"
            )
        src_span = _aralik(v.get("src_span"), "src_span", s.no, bos_olabilir=False)
        dst_span = _aralik(v.get("dst_span"), "dst_span", s.no, bos_olabilir=True)
        assert src_span is not None
        skor, guven = v["score"], v["confidence"]
        assert isinstance(skor, float) and isinstance(guven, float)
        mw, cov, pf, cq = (
            kanit.get(a) for a in ("matched_words", "coverage", "phrase_freq", "consistent_quote")
        )
        sinif = sinif_ipucu(
            str(tur),
            guven,
            matched_words=mw if isinstance(mw, int) and not isinstance(mw, bool) else None,
            coverage=cov if isinstance(cov, float) else None,
            phrase_freq=pf if isinstance(pf, int) and not isinstance(pf, bool) else None,
            consistent_quote=cq if isinstance(cq, bool) else None,
        )
        sonuc.append(
            AtifSatiri(str(tur), src, src_span, dst, dst_span, skor, guven, kanit, surum, sinif)
        )
    return sonuc


# --- hazirlik ----------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (xref-atif-iktibas kaynagi)."""
    kaynaklar = ctx.require_sources((*GEREKLI_KAYITLAR, *MEAL_KAYNAKLARI, *ek_kaynaklar))
    klasor_ust = ctx.staged_kaynak_dizini(source_id)
    if run is not None:
        if lineage.RUN_ID_DESENI.fullmatch(run) is None:
            raise GirdiHatasi("--run bir UUID degil")
        secilen = next((k for k in lineage.calismalar(klasor_ust) if k[0] == run), None)
        if secilen is None or secilen[2].get("adim") != CITATIONS_ADIMI:
            raise GirdiHatasi("--run icin manifestli enrich calistirmasi yok")
    else:
        secilen = lineage.son_basarili(klasor_ust, CITATIONS_ADIMI)
        if secilen is None:
            raise GirdiHatasi("manifestli enrich calistirmasi yok (once enrich citations)")
    enrich_run_id, klasor, manifest = secilen
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("enrich calistirmasinin ciktilari saglam degil")
    veri, sha = _dosya_oku(klasor, manifest, CITATIONS_DOSYASI)
    qa_rapor_id = _qa_denetle(ctx, source_id, enrich_run_id, sha)
    ayrintilar = manifest.get("ayrintilar")
    hedefler = ayrintilar.get("hedefler") if isinstance(ayrintilar, dict) else None
    if (
        not isinstance(hedefler, list)
        or not hedefler
        or not all(isinstance(h, str) and h in MEAL_KAYNAKLARI for h in hedefler)
    ):
        raise GirdiHatasi("enrich manifestinde hedefler yok ya da gecersiz")
    satirlar = xref_satirlari_oku(veri)
    onekler = [capa_onegi(str(h)) for h in hedefler]
    if any(not any(s.src_anchor.startswith(o) for o in onekler) for s in satirlar):
        raise GirdiHatasi("staged dosyasinda taranmayan meal capasi var")
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / CITATIONS_DOSYASI)
    return AtifHazirlik(
        source_id=source_id,
        kaynak_idleri=(),
        anchor_run_id=enrich_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=[],
        ingest={},
        ham={},
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler={},
        parmak=ctx.parmak_izi([lineage.Girdi(yol, sha, enrich_run_id)]),
        xref_satirlari=satirlar,
        hedefler=tuple(str(h) for h in hedefler),
    )


# --- veritabani --------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_xref (tur text, src_anchor text COLLATE "C",'
    ' src_span int4range, dst_anchor text COLLATE "C", dst_span int4range, score real,'
    " confidence real, evidence jsonb, data_version text, sinif text) ON COMMIT DROP"
)
COPY: Final = (
    "COPY pg_temp.staging_xref (tur, src_anchor, src_span, dst_anchor, dst_span, score,"
    " confidence, evidence, data_version, sinif) FROM STDIN"
)
# Staged ozetler, birimlerin GUNCEL content_hash ilk 16 haneyle tutmali (yoksa enrich eski).
ESKI_OZET: Final = (
    "SELECT count(*) FROM pg_temp.staging_xref s WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u"
    " WHERE u.kind = 'meal' AND u.anchor = s.src_anchor AND left(u.content_hash, 16) ="
    " s.evidence ->> 'src_hash') OR NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.kind = 'ayet'"
    " AND u.source_id = %(kaynak)s AND u.anchor = s.dst_anchor AND left(u.content_hash, 16) ="
    " s.evidence ->> 'dst_hash')"
)
# Kapsam: staged'in turleri ve taranan meallerin birimleri.
KAPSAM: Final = (
    "x.type::text = ANY(%(turler)s) AND x.origin = 'hat' AND EXISTS (SELECT 1 FROM"
    " unnest(%(onekler)s::text[]) p WHERE starts_with(x.src_anchor, p))"
)
URETILMEYEN_ADAY: Final = (
    "SELECT x.id FROM icerik.xref x WHERE "
    + KAPSAM
    + " AND x.status = 'aday' AND NOT EXISTS (SELECT 1 FROM pg_temp.staging_xref s WHERE "
    + ESLESME
    + ")"
)
# Silinebilir: yalniz hat tarafindan acilmis, dokunulmamis, ACIK review kayitlari var.
SILINEBILIR: Final = (
    "SELECT a.id FROM (" + URETILMEYEN_ADAY + ") a WHERE NOT EXISTS (SELECT 1 FROM icerik.review r"
    " WHERE r.xref_id = a.id AND NOT (r.durum = 'acik' AND r.koken = 'hat' AND r.inceleyen IS NULL"
    " AND r.duzenlenen IS NULL))"
)
REVIEW_SIL: Final = "DELETE FROM icerik.review r WHERE r.xref_id IN (" + SILINEBILIR + ")"
SIL: Final = "DELETE FROM icerik.xref x WHERE x.id IN (" + SILINEBILIR + ")"
SIL_ENGELLENEN: Final = (
    "SELECT count(*) FROM (" + URETILMEYEN_ADAY + ") a WHERE a.id NOT IN (" + SILINEBILIR + ")"
)
# Her aday satir icin (herhangi durumda review yoksa) onay review'u.
REVIEW_ACIK_YENI: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, xref_id, alan, eylem, onerilen, guven,"
    " koken, oneren) SELECT 'xref', x.id::text, x.id, 'status', 'oner', jsonb_build_object('score',"
    " s.score, 'confidence', s.confidence, 'sinif_ipucu', s.sinif), s.confidence, 'hat', 'hat'"
    " FROM icerik.xref x JOIN pg_temp.staging_xref s ON " + ESLESME + " WHERE x.origin = 'hat'"
    " AND x.status = 'aday' AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)"
    " ORDER BY s.confidence DESC, x.src_anchor, x.dst_anchor"
)
_ESKI_UC: Final = (
    "(NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.kind = 'meal' AND u.anchor = x.src_anchor"
    " AND left(u.content_hash, 16) = x.evidence ->> 'src_hash') OR NOT EXISTS (SELECT 1 FROM"
    " icerik.unit u WHERE u.kind = 'ayet' AND u.source_id = %(kaynak)s AND u.anchor ="
    " x.dst_anchor AND left(u.content_hash, 16) = x.evidence ->> 'dst_hash'))"
)
YENIDEN_DOGRULA_ADAYLARI: Final = (
    "WITH aday AS (SELECT x.id, x.type, x.src_anchor, x.dst_anchor, CASE WHEN " + _ESKI_UC + " THEN"
    " 'uc_metni_degisti' WHEN NOT EXISTS (SELECT 1 FROM pg_temp.staging_xref s WHERE "
    + ESLESME
    + ") THEN 'uretilmedi' END AS neden FROM icerik.xref x WHERE "
    + KAPSAM
    + " AND x.status = 'onayli')"
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


def _aralik_degeri(aralik: tuple[int, int] | None) -> Range[int] | None:
    return None if aralik is None else Range(aralik[0], aralik[1], "[)")


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[AtifSatiri]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_xref")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(COPY) as kopya:
        for s in satirlar:
            kopya.write_row(
                (
                    s.tur,
                    s.src_anchor,
                    _aralik_degeri(s.src_span),
                    s.dst_anchor,
                    _aralik_degeri(s.dst_span),
                    s.score,
                    s.confidence,
                    Jsonb(s.evidence),
                    s.data_version,
                    s.sinif,
                )
            )


def _say(
    conn: psycopg.Connection, sorgu: str, parametre: Mapping[str, object] | None = None
) -> int:
    satir = conn.execute(sorgu, parametre).fetchone()
    return int(satir[0]) if satir is not None else 0


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Atif ve iktibas baglantilarini yazar (cagiran `conn.transaction()` icindedir)."""
    if not isinstance(h, AtifHazirlik):
        raise TypeError("xref-atif-iktibas yuklemesi AtifHazirlik ister")
    onekler = [capa_onegi(m) for m in h.hedefler]
    _staging_yukle(conn, h.xref_satirlari)
    parametre = {"kaynak": UTHMANI_KAYNAGI, "turler": list(h.turler), "onekler": onekler}
    eski = _say(conn, ESKI_OZET, parametre)
    if eski:
        raise GirdiHatasi(
            f"{eski} staged satirin birim ozeti veritabaniyla tutmuyor (once enrich citations)"
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
    review_silinen = conn.execute(REVIEW_SIL, parametre).rowcount
    silinen = conn.execute(SIL, parametre).rowcount
    review_aday = conn.execute(REVIEW_ACIK_YENI).rowcount

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
        "review_aday_acilan": review_aday,
        "review_aday_silinen": review_silinen,
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
    tur_sayilari = Counter(s.tur for s in h.xref_satirlari)
    for tur in h.turler:
        sayilar[f"xref_staging_{tur}"] = tur_sayilari[tur]
    uretilen = " AND EXISTS (SELECT 1 FROM pg_temp.staging_xref s WHERE " + ESLESME + ")"
    hatalar = sql_hatalari(conn, h.turler, onekler, uretilen)
    ihlal = [f"{ad} {n}" for ad, n in hatalar.items() if n]
    if ihlal:
        raise QaKaldi("xref SQL denetimi (0 olmali): " + "; ".join(ihlal))
    ctx.gunluk.bilgi("export_pg_xref_atif", **{k: v for k, v in sayilar.items() if v})
    return sayilar
