"""Acik atif ve iktibas QA kapilari (A18.4, K-51): G-KAY, G-BUT, G-CAP.

Kapi islevleri bellekteki `AtifGirdisi` uzerinde calisir (staged `xref_citations.jsonl`); `qa/
run_xref_atif.py` zinciri yukler. Veritabani tarafi iki katmandir: `db_staged_hatalari` (yukleme
ONCESI, `--db`: birim, ozet ve aralik tutarliligi) ve `sql_hatalari` (yukleme SONRASI, `export pg`
islem sonunda calistirir, ihlal varsa geri alir; ayrica her aday satirin `review` kaydi vardir).

* G-KAY: kaynak kayitlari gecerli; her satirin `evidence.source_id` degeri kayitli bir kaynaktir
  ve ture uygundur (`atif`: `tanzil-uthmani`; `iktibas`: `index` ile uyumlu `tanzil-uthmani` ya da
  `tanzil-simple-clean`).
* G-BUT: satir alan kumeleri, `score` ve `confidence` [0, 1], evidence anahtar kumeleri,
  `coverage = n/N`, `identity = n/(n+e)`, skor formulu (`phrase_freq` ve `f = 1` arasinda),
  `consistent_quote` ile guven uyumu (false: 0,30; true: en az 0,95), manifest sayilari.
* G-CAP: `src_anchor` hedef meal capasi, `dst_anchor` ayet capasi, `src_span` gecerli ve
  `evidence.src_span` ile ayni, `dst_span` kelime konumu `[ilk, son + 1)` ayet kelime sayisi
  icinde, dogal anahtar tekil, siralama kesin artan.

Bulgular ASCII ve kisadir; yalniz sayi, capa ve alan adi tasir (metin yok).
"""

import math
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import psycopg

from mutalaa_pipeline.anchor import AnchorError, Meal, Q, parse
from mutalaa_pipeline.enrich.citations.kurallar import GUVEN_TUTARLI, GUVEN_TUTARSIZ, iktibas_puani
from mutalaa_pipeline.enrich.citations.uret import SIMPLE_KAYNAGI, TURLER, UTHMANI_KAYNAGI
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

SATIR_ALANLARI: Final = frozenset(
    {
        "tur_no",
        "src_no",
        "src_bas",
        "dst_no",
        "dst_bas",
        "type",
        "src_anchor",
        "dst_anchor",
        "src_span",
        "dst_span",
        "score",
        "confidence",
        "evidence",
        "data_version",
    }
)
ATIF_ZORUNLU: Final = frozenset(
    {"bicim", "position", "src_hash", "dst_hash", "source_id", "src_span"}
)
ATIF_ISTEGE_BAGLI: Final = frozenset({"group", "consistent_quote"})
IKTIBAS_ZORUNLU: Final = frozenset(
    {
        "matched_words",
        "ayah_words",
        "coverage",
        "identity",
        "edits",
        "index",
        "phrase_freq",
        "position",
        "phrase_key",
        "src_hash",
        "dst_hash",
        "source_id",
        "src_span",
    }
)
IKTIBAS_ISTEGE_BAGLI: Final = frozenset(
    {"context", "alternatives", "consistent_quote", "group", "konum_belirsiz"}
)
POZISYONLAR: Final = frozenset({"baslik", "dipnot", "metin"})
INDEKS_KAYNAK: Final = {"uthmani": UTHMANI_KAYNAGI, "imlai": SIMPLE_KAYNAGI}
ATIF_BICIMLERI: Final = frozenset({"sayisal", "ad", "ad_sira", "adlandirilmis"})
OZET_DESENI: Final = re.compile(r"[0-9a-f]{16}")
GEREKLI_KAYITLAR: Final = (UTHMANI_KAYNAGI, SIMPLE_KAYNAGI)
SINIR: Final = 1e-6


@dataclass
class AtifGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayitlar: Mapping[str, Kaynak]  # slug -> kaynak kaydi (uthmani, simple-clean, hedef mealler)
    satirlar: list[Satir]
    hedefler: Sequence[str]  # manifest: taranan mealler
    manifest_sayilari: Mapping[str, int]  # tur -> manifestteki satir sayisi
    data_version: str = ""


def _g(deger: object, en_uzun: int = 48) -> str:
    return ascii(deger)[:en_uzun]


def _tur(s: Satir) -> str:
    deger = s.veri.get("type")
    return deger if isinstance(deger, str) else ""


def _kanit(s: Satir) -> dict[str, object]:
    deger = s.veri.get("evidence")
    return deger if isinstance(deger, dict) else {}


def _sayi(deger: object) -> bool:
    return isinstance(deger, int | float) and not isinstance(deger, bool) and math.isfinite(deger)


def _tam(deger: object) -> bool:
    return isinstance(deger, int) and not isinstance(deger, bool)


def _aralik(deger: object) -> tuple[int, int] | None:
    if (
        isinstance(deger, list)
        and len(deger) == 2
        and _tam(deger[0])
        and _tam(deger[1])
        and 0 <= deger[0] < deger[1]
    ):
        return int(deger[0]), int(deger[1])
    return None


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: AtifGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    for slug in (*GEREKLI_KAYITLAR, *g.hedefler):
        kayit = g.kayitlar.get(slug)
        if kayit is None:
            bulgular.append(f"{slug}: kaynak kaydi yok")
        elif all(harf in " \t\n" for harf in kayit.atif_metni):
            bulgular.append(f"{slug}: atif_metni bos")
    kayitsiz: Counter[str] = Counter()
    uygunsuz: Counter[str] = Counter()
    for s in g.satirlar:
        kanit = _kanit(s)
        kaynak, tur = kanit.get("source_id"), _tur(s)
        if not isinstance(kaynak, str) or kaynak not in g.kayitlar:
            kayitsiz[str(kaynak)[:40]] += 1
        elif (tur == "atif" and kaynak != UTHMANI_KAYNAGI) or (
            tur == "iktibas" and INDEKS_KAYNAK.get(str(kanit.get("index"))) != kaynak
        ):
            uygunsuz[f"{tur}/{kaynak}"] += 1
    for kaynak, n in sorted(kayitsiz.items()):
        bulgular.append(f"evidence.source_id kayitsiz: {_g(kaynak)} ({n} satir)")
    for anahtar, n in sorted(uygunsuz.items()):
        bulgular.append(f"evidence.source_id ture uygun degil: {_g(anahtar)} ({n} satir)")
    return KapiSonucu(
        "G-KAY",
        tuple(bulgular),
        {"kaynak_kaydi": len(g.kayitlar), "kayitsiz_source_id": sum(kayitsiz.values())},
    )


# --- G-BUT -------------------------------------------------------------------------------


def _guven_uyumu(kanit: Mapping[str, object], guven: float) -> list[str]:
    tutarli = kanit.get("consistent_quote")
    if tutarli is False and abs(guven - GUVEN_TUTARSIZ) > SINIR:
        return ["tutarsiz_guven"]
    if tutarli is True and guven < GUVEN_TUTARLI - SINIR:
        return ["tutarli_guven"]
    if "consistent_quote" in kanit and not isinstance(tutarli, bool):
        return ["consistent_quote_tur"]
    return []


def _atif_hatalari(s: Satir, kanit: Mapping[str, object], skor: float, guven: float) -> list[str]:
    hatalar: list[str] = []
    anahtarlar = set(kanit)
    if not (ATIF_ZORUNLU <= anahtarlar <= ATIF_ZORUNLU | ATIF_ISTEGE_BAGLI):
        return ["evidence_alanlari"]
    if abs(skor - 1.0) > SINIR:
        hatalar.append("atif_skor_1_degil")
    if kanit["bicim"] not in ATIF_BICIMLERI:
        hatalar.append("bicim")
    if s.veri.get("dst_span") is not None:
        hatalar.append("atif_dst_span_dolu")
    return [*hatalar, *_guven_uyumu(kanit, guven)]


def _iktibas_hatalari(
    s: Satir, kanit: Mapping[str, object], skor: float, guven: float
) -> list[str]:
    anahtarlar = set(kanit)
    if not (IKTIBAS_ZORUNLU <= anahtarlar <= IKTIBAS_ZORUNLU | IKTIBAS_ISTEGE_BAGLI):
        return ["evidence_alanlari"]
    n, uzunluk, sik, duz = (
        kanit[a] for a in ("matched_words", "ayah_words", "phrase_freq", "edits")
    )
    if not all(_tam(x) for x in (n, uzunluk, sik, duz)):
        return ["tam_sayi_alanlari"]
    n, uzunluk, sik, duz = int(str(n)), int(str(uzunluk)), int(str(sik)), int(str(duz))
    if not (1 <= n <= uzunluk and sik >= 1 and duz >= 0):
        return ["matched_words"]
    hatalar: list[str] = []
    kapsama, kimlik = kanit["coverage"], kanit["identity"]
    if not _sayi(kapsama) or abs(float(str(kapsama)) - min(1.0, n / uzunluk)) > SINIR:
        hatalar.append("coverage")
    if not _sayi(kimlik) or abs(float(str(kimlik)) - n / (n + duz)) > SINIR:
        hatalar.append("identity")
    alt = iktibas_puani(n, uzunluk, duz, sik)
    ust = iktibas_puani(n, uzunluk, duz, 1)
    if not alt - SINIR <= skor <= ust + SINIR:
        hatalar.append("skor_formulu")
    if kanit["index"] not in INDEKS_KAYNAK:
        hatalar.append("index")
    if kanit["position"] not in POZISYONLAR:
        hatalar.append("position")
    if not isinstance(kanit["phrase_key"], str) or kanit["phrase_key"] == "":
        hatalar.append("phrase_key")
    ara = _aralik(s.veri.get("dst_span"))
    if ara is None or not (1 <= ara[0] < ara[1] <= uzunluk + 1):
        hatalar.append("dst_span")
    return [*hatalar, *_guven_uyumu(kanit, guven)]


def g_but(g: AtifGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    sayac: Counter[str] = Counter()
    ornek: dict[str, int] = {}
    tur_sayilari: Counter[str] = Counter()

    def isle(ad: str, s: Satir) -> None:
        sayac[ad] += 1
        ornek.setdefault(ad, s.no)

    for s in g.satirlar:
        if set(s.veri) != SATIR_ALANLARI:
            isle("satir_alanlari", s)
            continue
        tur = _tur(s)
        tur_sayilari[tur] += 1
        skor, guven = s.veri.get("score"), s.veri.get("confidence")
        if tur not in TURLER:
            isle("tur", s)
            continue
        if not (_sayi(skor) and _sayi(guven)) or not (
            0.0 <= float(str(skor)) <= 1.0 and 0.0 <= float(str(guven)) <= 1.0
        ):
            isle("skor_guven_araligi", s)
            continue
        kanit = _kanit(s)
        for alan in ("src_hash", "dst_hash"):
            if (
                not isinstance(kanit.get(alan), str)
                or OZET_DESENI.fullmatch(str(kanit[alan])) is None
            ):
                isle("ozet_bicimi", s)
        hatalar = (
            _atif_hatalari(s, kanit, float(str(skor)), float(str(guven)))
            if tur == "atif"
            else _iktibas_hatalari(s, kanit, float(str(skor)), float(str(guven)))
        )
        for h in hatalar:
            isle(h, s)
    for ad, n in sorted(sayac.items()):
        bulgular.append(f"butunluk ihlali {ad}: {n} satir (ilk: satir {ornek[ad]})")
    for tur in TURLER:
        beklenen = g.manifest_sayilari.get(tur)
        if beklenen is None or beklenen != tur_sayilari[tur]:
            bulgular.append(
                f"manifest satir sayisi tutmuyor: {tur} (dosya {tur_sayilari[tur]},"
                f" manifest {beklenen})"
            )
    return KapiSonucu(
        "G-BUT",
        tuple(bulgular),
        {
            "satir": len(g.satirlar),
            **dict(sayac),
            **{f"satir_{t}": tur_sayilari[t] for t in TURLER},
        },
    )


# --- G-CAP -------------------------------------------------------------------------------


def _capa_kontrol(src: str, dst: str, onekler: Sequence[str]) -> list[str]:
    hatalar: list[str] = []
    try:
        r = parse(src).anchor
        if not isinstance(r, Meal) or not any(src.startswith(o) for o in onekler):
            hatalar.append("src_hedef_meal_degil")
    except AnchorError:
        hatalar.append("src_capa_gecersiz")
    try:
        d = parse(dst).anchor
        if not isinstance(d, Q) or d.ilk is not None or f"q:{d.sure}:{d.ayet}" != dst:
            hatalar.append("dst_ayet_capasi_degil")
    except AnchorError:
        hatalar.append("dst_capa_gecersiz")
    return hatalar


def g_cap(g: AtifGirdisi) -> KapiSonucu:
    from mutalaa_pipeline.ingest.meal_kaynaklari import capa_onegi

    onekler = [capa_onegi(h) for h in g.hedefler]
    bulgular: list[str] = []
    sayac: Counter[str] = Counter()
    ornek: dict[str, int] = {}
    gorulen: set[tuple[object, ...]] = set()
    onceki: tuple[int, ...] | None = None

    def isle(ad: str, s: Satir) -> None:
        sayac[ad] += 1
        ornek.setdefault(ad, s.no)

    for s in g.satirlar:
        if set(s.veri) != SATIR_ALANLARI:
            continue
        src, dst = s.veri.get("src_anchor"), s.veri.get("dst_anchor")
        if not isinstance(src, str) or not isinstance(dst, str):
            isle("capa_metin_degil", s)
            continue
        for h in _capa_kontrol(src, dst, onekler):
            isle(h, s)
        aralik = _aralik(s.veri.get("src_span"))
        if aralik is None:
            isle("src_span", s)
        elif _kanit(s).get("src_span") != [aralik[0], aralik[1]]:
            isle("kanit_src_span_farkli", s)
        dst_span = s.veri.get("dst_span")
        anahtar = (_tur(s), src, str(s.veri.get("src_span")), dst, str(dst_span))
        if anahtar in gorulen:
            isle("dogal_anahtar_yinelenen", s)
        gorulen.add(anahtar)
        alanlar = tuple(s.veri.get(a) for a in ("tur_no", "src_no", "src_bas", "dst_no", "dst_bas"))
        if all(_tam(x) for x in alanlar):
            gecerli = tuple(int(str(x)) for x in alanlar)
            if onceki is not None and gecerli <= onceki:
                isle("sira_bozuk", s)
            onceki = gecerli
        else:
            isle("sira_alani", s)
    for ad, n in sorted(sayac.items()):
        bulgular.append(f"capa ihlali {ad}: {n} satir (ilk: satir {ornek[ad]})")
    return KapiSonucu("G-CAP", tuple(bulgular), {"satir": len(g.satirlar), **dict(sayac)})


KAPI_ISLEVLERI: Final[Mapping[str, Callable[[AtifGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- veritabani: staged satirlar (yukleme oncesi) ------------------------------------------


def db_staged_hatalari(conn: psycopg.Connection, satirlar: Sequence[Satir]) -> dict[str, int]:
    """Staged satirlarin veritabaniyla tutarsizliklari (hepsi 0 olmali; salt okuma)."""
    ayet_ozet = {
        str(c): str(h)[:16]
        for c, h in conn.execute(
            "SELECT anchor, content_hash FROM icerik.unit WHERE kind = 'ayet' AND source_id = %s"
            " AND status = 'etkin'",
            (UTHMANI_KAYNAGI,),
        ).fetchall()
    }
    meal = {
        str(c): (str(h)[:16], len(str(m)))
        for c, h, m in conn.execute(
            "SELECT anchor, content_hash, metin FROM icerik.unit WHERE kind = 'meal'"
            " AND status = 'etkin'"
        ).fetchall()
    }
    hata: Counter[str] = Counter()
    for s in satirlar:
        kanit = _kanit(s)
        src, dst = str(s.veri.get("src_anchor")), str(s.veri.get("dst_anchor"))
        if src not in meal:
            hata["meal_birimi_yok"] += 1
        else:
            if meal[src][0] != kanit.get("src_hash"):
                hata["src_ozet_eski"] += 1
            aralik = _aralik(s.veri.get("src_span"))
            if aralik is not None and aralik[1] > meal[src][1]:
                hata["src_span_metin_disi"] += 1
        if dst not in ayet_ozet:
            hata["ayet_birimi_yok"] += 1
        elif ayet_ozet[dst] != kanit.get("dst_hash"):
            hata["dst_ozet_eski"] += 1
    return {
        ad: hata.get(ad, 0)
        for ad in (
            "meal_birimi_yok",
            "src_ozet_eski",
            "src_span_metin_disi",
            "ayet_birimi_yok",
            "dst_ozet_eski",
        )
    }


def db_bulgulari(hatalar: Mapping[str, int], onek: str) -> list[str]:
    return [f"{onek}: {ad} {n} (0 olmali)" for ad, n in hatalar.items() if n]


# --- veritabani: icerik.xref (yukleme sonrasi) ---------------------------------------------

_KAPSAM: Final = (
    " AND x.type::text = ANY(%(turler)s) AND EXISTS (SELECT 1 FROM unnest(%(onekler)s::text[]) p"
    " WHERE starts_with(x.src_anchor, p))"
)
SQL_SORGULARI: Final[Mapping[str, str]] = {
    "kayitsiz_source_id": (
        "SELECT count(*) FROM icerik.xref x WHERE x.origin = 'hat' AND NOT EXISTS"
        " (SELECT 1 FROM icerik.source s WHERE s.slug = x.evidence ->> 'source_id')" + _KAPSAM
    ),
    "aday_ozet_eski": (
        "SELECT count(*) FROM icerik.xref x WHERE x.origin = 'hat' AND x.status = 'aday' AND ("
        "NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = x.src_anchor AND u.kind = 'meal'"
        " AND left(u.content_hash, 16) = x.evidence ->> 'src_hash') OR NOT EXISTS (SELECT 1 FROM"
        " icerik.unit u WHERE u.anchor = x.dst_anchor AND u.kind = 'ayet' AND u.source_id ="
        " 'tanzil-uthmani' AND left(u.content_hash, 16) = x.evidence ->> 'dst_hash'))" + _KAPSAM
    ),
    "src_span_gecersiz": (
        "SELECT count(*) FROM icerik.xref x JOIN icerik.unit u ON u.anchor = x.src_anchor AND"
        " u.kind = 'meal' WHERE x.origin = 'hat' AND x.status = 'aday' AND (x.src_span IS NULL OR"
        " isempty(x.src_span) OR lower(x.src_span) < 0 OR upper(x.src_span) > char_length(u.metin))"
        + _KAPSAM
    ),
    "aday_review_yok": (
        "SELECT count(*) FROM icerik.xref x WHERE x.origin = 'hat' AND x.status = 'aday' AND"
        " NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.xref_id = x.id)" + _KAPSAM
    ),
}


def sql_hatalari(
    conn: psycopg.Connection,
    turler: Sequence[str],
    onekler: Sequence[str],
    uretilen_kosulu: str = "",
) -> dict[str, int]:
    """`icerik.xref` icindeki atif ve iktibas hat satirlarinin ihlalleri (hepsi 0 olmali).

    `uretilen_kosulu`: ek SQL kosulu (yukleyici: bu kosuda uretilen satirlarla sinirlar; uretilmeyen
    ama `review` kaydi nedeniyle silinmeyen eski aday satirlar bu denetime girmez).
    """
    sonuc: dict[str, int] = {}
    for ad, sorgu in SQL_SORGULARI.items():
        ek = "" if ad == "aday_review_yok" else uretilen_kosulu
        sonuc[ad] = _say(conn, sorgu + ek, turler, onekler)
    return sonuc


def _say(
    conn: psycopg.Connection, sorgu: str, turler: Sequence[str], onekler: Sequence[str]
) -> int:
    satir = conn.execute(sorgu, {"turler": list(turler), "onekler": list(onekler)}).fetchone()
    return int(satir[0]) if satir is not None else 0
