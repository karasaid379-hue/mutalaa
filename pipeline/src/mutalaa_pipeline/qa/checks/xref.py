"""Kur'an ici baglanti QA kapilari (A18.3, K-51): G-KAY, G-BUT, G-CAP.

Kapi islevleri bellekteki `XrefGirdisi` uzerinde calisir (staged `xref_links.jsonl`); `qa/
run_xref.py` zinciri yukler. Veritabani tarafi iki katmandir:

* `db_staged_hatalari`: staged satirlarin veritabaniyla tutarliligi (yukleme ONCESI; `qa run
  --source xref-baglantilar --db`): capa ve ayet ozeti, paylasilan kok ya da lemmanin iki
  ayetin `quran_word.root_id` / `lemma_id` degerlerinde bulunmasi;
* `sql_hatalari`: `icerik.xref` icindeki satirlarin ayni tutarliligi (yukleme SONRASI; `export
  pg` ayni sorguyu islem sonunda calistirir, ihlal varsa geri alir). `lemma` ve `kok`
  tutarliligi %100 olmali (Test stratejisi §4): her ortak kimlik, hem kaynak hem hedef ayetin
  kelime satirlarinda ayni kimlikle bulunur.

* G-KAY: kaynak kayitlari gecerli (`atif_metni` dolu); her satirin `evidence.source_id` degeri
  kayitli bir kaynaktir ve turune uygundur (`kok`, `lemma`: `qac-morfoloji`; `benzer_ayet`:
  `tanzil-uthmani` ya da `qursim`).
* G-BUT: satir alan kumeleri, `score` = `confidence` (0..1), evidence anahtar kumeleri, skor
  formulu (`benzer_ayet` sozluksel; QurSim sabit 0,50 ve Label'a bagli puan yok), kok ve lemma
  icin birim basina en cok 5 satir, `idf_n >= 0,3`, manifest sayilariyla tutarlilik.
* G-CAP: capalar kanonik ayet capasi, src != dst, dogal anahtar tekil, `benzer_ayet` icin
  `src < dst` (kuresel ayet sirasi), paylasilan kelime capalari ilgili ayete ait.

Bulgular ASCII ve kisadir; yalniz sayi, capa ve alan adi tasir (metin yok).
"""

import math
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg

from mutalaa_pipeline.anchor import AnchorError, Q, parse
from mutalaa_pipeline.enrich.baglantilar.benzer import QURSIM_SKORU, skor_hesapla
from mutalaa_pipeline.enrich.baglantilar.kok_lemma import EN_COK_KOMSU, IDF_ESIGI, yuvarla
from mutalaa_pipeline.enrich.baglantilar.uret import (
    ALAN_ADI,
    BENZER,
    KOK,
    LEMMA,
    QAC_KAYNAGI,
    QURSIM_KAYNAGI,
    TURLER,
    UTHMANI_KAYNAGI,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

SATIR_ALANLARI: Final = frozenset(
    {
        "tur_no",
        "src_no",
        "dst_no",
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
KOK_KANIT_ALANLARI: Final = frozenset({"shared", "src_hash", "dst_hash", "source_id"})
SOZLUKSEL_KANIT_ALANLARI: Final = frozenset(
    {
        "subtype",
        "matched_words",
        "ayah_words",
        "coverage",
        "index",
        "kapsayan",
        "src_hash",
        "dst_hash",
        "source_id",
    }
)
IZINLI_KAYNAK: Final[Mapping[str, frozenset[str]]] = {
    KOK: frozenset({QAC_KAYNAGI}),
    LEMMA: frozenset({QAC_KAYNAGI}),
    BENZER: frozenset({UTHMANI_KAYNAGI, QURSIM_KAYNAGI}),
}
GEREKLI_KAYITLAR: Final = (QAC_KAYNAGI, UTHMANI_KAYNAGI, QURSIM_KAYNAGI)
OZET_DESENI: Final = re.compile(r"[0-9a-f]{16}")
KELIME_CAPASI: Final = re.compile(r"q:(?P<ayet>[0-9]{1,3}:[0-9]{1,3}):[0-9]{1,3}")


@dataclass
class XrefGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayitlar: Mapping[str, Kaynak]  # slug -> kaynak kaydi (GEREKLI_KAYITLAR)
    satirlar: list[Satir]
    turler: Sequence[str]  # manifest: uretilen turler
    manifest_sayilari: Mapping[str, int]  # tur -> manifestteki satir sayisi
    data_version: Mapping[str, str]  # tur -> manifestteki data_version
    en_cok: Mapping[str, int] = field(
        default_factory=lambda: {KOK: EN_COK_KOMSU, LEMMA: EN_COK_KOMSU}
    )


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


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: XrefGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    for slug in GEREKLI_KAYITLAR:
        kayit = g.kayitlar.get(slug)
        if kayit is None:
            bulgular.append(f"{slug}: kaynak kaydi yok")
        elif all(harf in " \t\n" for harf in kayit.atif_metni):
            bulgular.append(f"{slug}: atif_metni bos")
    kayitsiz: Counter[str] = Counter()
    uygunsuz: Counter[str] = Counter()
    for s in g.satirlar:
        kaynak = _kanit(s).get("source_id")
        tur = _tur(s)
        if not isinstance(kaynak, str) or kaynak not in g.kayitlar:
            kayitsiz[str(kaynak)[:40]] += 1
        elif kaynak not in IZINLI_KAYNAK.get(tur, frozenset()):
            uygunsuz[f"{tur}/{kaynak}"] += 1
    for kaynak, n in sorted(kayitsiz.items()):
        bulgular.append(f"evidence.source_id kayitsiz: {_g(kaynak)} ({n} satir)")
    for anahtar, n in sorted(uygunsuz.items()):
        bulgular.append(f"evidence.source_id tura uygun degil: {_g(anahtar)} ({n} satir)")
    return KapiSonucu(
        "G-KAY",
        tuple(bulgular),
        {"kaynak_kaydi": len(g.kayitlar), "kayitsiz_source_id": sum(kayitsiz.values())},
    )


# --- G-BUT -------------------------------------------------------------------------------


def _kok_lemma_kaniti(tur: str, kanit: Mapping[str, object]) -> list[str]:
    hatalar: list[str] = []
    ad = ALAN_ADI[tur]
    if set(kanit) != KOK_KANIT_ALANLARI:
        return ["evidence_alanlari"]
    ortaklar = kanit["shared"]
    if not isinstance(ortaklar, list) or not ortaklar:
        return ["shared_bos"]
    for o in ortaklar:
        if (
            not isinstance(o, dict)
            or set(o) != {ad, "idf", "src_word", "dst_word"}
            or not isinstance(o[ad], int)
            or isinstance(o[ad], bool)
            or not _sayi(o["idf"])
            or not isinstance(o["src_word"], str)
            or not isinstance(o["dst_word"], str)
        ):
            return ["shared_ogesi"]
        if o["idf"] < IDF_ESIGI - 1e-6 or o["idf"] > 1.0 + 1e-9:
            hatalar.append("idf_araligi")
    return hatalar


def _sozluksel_kaniti(s: Satir, kanit: Mapping[str, object]) -> list[str]:
    ek = {"qursim", "dongusel"}
    anahtarlar = set(kanit)
    if not (anahtarlar == SOZLUKSEL_KANIT_ALANLARI or anahtarlar == SOZLUKSEL_KANIT_ALANLARI | ek):
        return ["evidence_alanlari"]
    hatalar: list[str] = []
    ortak, uzunluk, kapsama = kanit["matched_words"], kanit["ayah_words"], kanit["coverage"]
    if (
        not isinstance(ortak, int)
        or not isinstance(uzunluk, int)
        or isinstance(ortak, bool)
        or isinstance(uzunluk, bool)
        or not _sayi(kapsama)
        or not 4 <= ortak <= uzunluk
    ):
        return ["matched_words"]
    if abs(float(s.veri["score"]) - yuvarla(skor_hesapla(ortak, uzunluk))) > 1e-9:  # type: ignore[arg-type]
        hatalar.append("skor_formulu")
    if abs(float(kapsama) - round(ortak / uzunluk, 6)) > 1e-9:  # type: ignore[arg-type]
        hatalar.append("kapsama")
    if kanit["index"] not in ("uthmani", "imlai") or kanit["kapsayan"] not in ("src", "dst"):
        hatalar.append("index_ya_da_kapsayan")
    if kanit["source_id"] != UTHMANI_KAYNAGI:
        hatalar.append("source_id")
    if "qursim" in kanit or "dongusel" in kanit:
        q = kanit.get("qursim")
        if (
            kanit.get("dongusel") is not True
            or not isinstance(q, dict)
            or set(q) != {"label"}
            or not isinstance(q["label"], int)
            or isinstance(q["label"], bool)
        ):
            hatalar.append("qursim_isareti")
    return hatalar


def _alim_kaniti(s: Satir, kanit: Mapping[str, object]) -> list[str]:
    if set(kanit) != {"subtype", "label", "src_hash", "dst_hash", "source_id"}:
        return ["evidence_alanlari"]
    hatalar: list[str] = []
    label = kanit["label"]
    if not isinstance(label, int) or isinstance(label, bool) or label < 0:
        hatalar.append("label")
    # Label'a bagli puan yok (K-51 madde 12): skor her zaman sabittir.
    if s.veri.get("score") != QURSIM_SKORU or s.veri.get("confidence") != QURSIM_SKORU:
        hatalar.append("qursim_skoru_sabit_degil")
    if kanit["source_id"] != QURSIM_KAYNAGI:
        hatalar.append("source_id")
    return hatalar


def satir_hatalari(s: Satir) -> list[str]:
    """Bir satirin G-BUT ihlalleri (bos: temiz)."""
    if set(s.veri) != SATIR_ALANLARI:
        return ["satir_alanlari"]
    tur = _tur(s)
    if tur not in TURLER:
        return ["tur"]
    skor, guven = s.veri["score"], s.veri["confidence"]
    if not _sayi(skor) or not _sayi(guven) or not 0 <= float(skor) <= 1:  # type: ignore[arg-type]
        return ["skor_araligi"]
    hatalar: list[str] = []
    if skor != guven:
        hatalar.append("skor_guven_ayni_degil")
    if s.veri["src_span"] is not None or s.veri["dst_span"] is not None:
        hatalar.append("aralik_dolu")
    kanit = _kanit(s)
    for alan in ("src_hash", "dst_hash"):
        ozet = kanit.get(alan)
        if not isinstance(ozet, str) or OZET_DESENI.fullmatch(ozet) is None:
            hatalar.append(alan)
    if tur in (KOK, LEMMA):
        hatalar += _kok_lemma_kaniti(tur, kanit)
    elif kanit.get("subtype") == "sozluksel":
        hatalar += _sozluksel_kaniti(s, kanit)
    elif kanit.get("subtype") == "alim":
        hatalar += _alim_kaniti(s, kanit)
    else:
        hatalar.append("subtype")
    return hatalar


def g_but(g: XrefGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    hatalar: Counter[str] = Counter()
    ornek: dict[str, int] = {}
    sayac: Counter[str] = Counter()
    kaynak_sayac: Counter[tuple[str, str]] = Counter()
    for s in g.satirlar:
        for h in satir_hatalari(s):
            hatalar[h] += 1
            ornek.setdefault(h, s.no)
        tur = _tur(s)
        sayac[tur] += 1
        kaynak_sayac[(tur, str(s.veri.get("src_anchor")))] += 1
    for h, n in sorted(hatalar.items()):
        bulgular.append(f"satir ihlali {h}: {n} satir (ilk: satir {ornek[h]})")
    for tur in g.turler:
        if sayac.get(tur, 0) != g.manifest_sayilari.get(tur):
            bulgular.append(f"{tur}: satir sayisi manifestle tutmuyor")
    for tur in sayac:
        if tur not in g.turler:
            bulgular.append(f"{tur}: manifestte listelenmeyen tur")
    for s in g.satirlar:
        tur = _tur(s)
        beklenen = g.data_version.get(tur)
        if beklenen is not None and s.veri.get("data_version") != beklenen:
            bulgular.append(f"{tur}: data_version manifestle tutmuyor (satir {s.no})")
            break
    for (tur, capa), n in sorted(kaynak_sayac.items()):
        sinir = g.en_cok.get(tur)
        if sinir is not None and n > sinir:
            bulgular.append(f"{tur}: {_g(capa)} icin {n} satir (en cok {sinir})")
    return KapiSonucu("G-BUT", tuple(bulgular), {"satir": len(g.satirlar), **dict(sayac)})


# --- G-CAP -------------------------------------------------------------------------------


def _ayet_capasi(deger: object) -> tuple[int, int] | None:
    if not isinstance(deger, str):
        return None
    try:
        ref = parse(deger)
    except AnchorError:
        return None
    birim = ref.anchor
    if not isinstance(birim, Q) or birim.ilk is not None or ref.span is not None:
        return None
    return birim.sure, birim.ayet


def g_cap(g: XrefGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    gorulen: set[tuple[str, str, str]] = set()
    sayac: Counter[str] = Counter()
    ornek: dict[str, int] = {}

    def isle(ad: str, s: Satir) -> None:
        sayac[ad] += 1
        ornek.setdefault(ad, s.no)

    onceki: tuple[int, int, int] | None = None
    for s in g.satirlar:
        src, dst = _ayet_capasi(s.veri.get("src_anchor")), _ayet_capasi(s.veri.get("dst_anchor"))
        if src is None or dst is None:
            isle("capa_gecersiz", s)
            continue
        tur = _tur(s)
        if src == dst:
            isle("src_dst_ayni", s)
        anahtar = (tur, str(s.veri["src_anchor"]), str(s.veri["dst_anchor"]))
        if anahtar in gorulen:
            isle("dogal_anahtar_yinelenen", s)
        gorulen.add(anahtar)
        if tur == BENZER and src >= dst:
            isle("benzer_ayet_src_kucuk_degil", s)
        t_no, s_no, d_no = (s.veri.get(a) for a in ("tur_no", "src_no", "dst_no"))
        if all(isinstance(x, int) and not isinstance(x, bool) for x in (t_no, s_no, d_no)):
            gecerli = (int(str(t_no)), int(str(s_no)), int(str(d_no)))
            if onceki is not None and gecerli <= onceki:
                isle("sira_bozuk", s)
            onceki = gecerli
        else:
            isle("sira_alani", s)
        if tur in (KOK, LEMMA):
            _kelime_capalari(s, str(s.veri["src_anchor"]), str(s.veri["dst_anchor"]), isle)
    for ad, n in sorted(sayac.items()):
        bulgular.append(f"capa ihlali {ad}: {n} satir (ilk: satir {ornek[ad]})")
    return KapiSonucu("G-CAP", tuple(bulgular), {"satir": len(g.satirlar), **dict(sayac)})


def _kelime_capalari(s: Satir, src: str, dst: str, isle: Callable[[str, Satir], None]) -> None:
    ortaklar = _kanit(s).get("shared")
    if not isinstance(ortaklar, list):
        return
    for o in ortaklar:
        if not isinstance(o, dict):
            continue
        for alan, ayet in (("src_word", src), ("dst_word", dst)):
            kelime = o.get(alan)
            e = KELIME_CAPASI.fullmatch(kelime) if isinstance(kelime, str) else None
            if e is None or f"q:{e.group('ayet')}" != ayet:
                isle("kelime_capasi_ayete_ait_degil", s)
                return


KAPI_ISLEVLERI: Final[Mapping[str, Callable[[XrefGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- veritabani: staged satirlar (yukleme oncesi) ------------------------------------------


def db_staged_hatalari(conn: psycopg.Connection, satirlar: Sequence[Satir]) -> dict[str, int]:
    """Staged satirlarin veritabaniyla tutarsizliklari (hepsi 0 olmali; salt okuma)."""
    ozet = {
        str(capa): str(h)[:16]
        for capa, h in conn.execute(
            "SELECT anchor, content_hash FROM icerik.unit WHERE kind = 'ayet' AND source_id = %s"
            " AND status = 'etkin'",
            (UTHMANI_KAYNAGI,),
        ).fetchall()
    }
    kelime = {
        str(capa): (None if k is None else int(k), None if lm is None else int(lm))
        for capa, k, lm in conn.execute(
            "SELECT anchor, root_id, lemma_id FROM icerik.quran_word"
        ).fetchall()
    }
    hata: Counter[str] = Counter()
    for s in satirlar:
        kanit = _kanit(s)
        for uc, ozet_alani in (("src_anchor", "src_hash"), ("dst_anchor", "dst_hash")):
            capa = str(s.veri.get(uc))
            if capa not in ozet:
                hata["birim_yok"] += 1
            elif ozet[capa] != kanit.get(ozet_alani):
                hata["ozet_eski"] += 1
        tur = _tur(s)
        if tur not in (KOK, LEMMA):
            continue
        ad, yer = ALAN_ADI[tur], 0 if tur == KOK else 1
        ortaklar = kanit.get("shared")
        for o in ortaklar if isinstance(ortaklar, list) else []:
            if not isinstance(o, dict):
                continue
            for alan in ("src_word", "dst_word"):
                kayit = kelime.get(str(o.get(alan)))
                if kayit is None or kayit[yer] != o.get(ad):
                    hata[f"{tur}_tutarsiz"] += 1
    return {
        ad: hata.get(ad, 0) for ad in ("birim_yok", "ozet_eski", "kok_tutarsiz", "lemma_tutarsiz")
    }


def db_bulgulari(hatalar: Mapping[str, int], onek: str) -> list[str]:
    return [f"{onek}: {ad} {n} (0 olmali)" for ad, n in hatalar.items() if n]


# --- veritabani: icerik.xref (yukleme sonrasi) ---------------------------------------------

KAPSAM: Final = "@@KAPSAM@@"  # sql_hatalari: " AND x.type::text = ANY(turler)" (ya da bos)
_ORTAK_ESLESME = (
    "SELECT count(*) FROM icerik.xref x CROSS JOIN LATERAL jsonb_array_elements("
    "CASE WHEN jsonb_typeof(x.evidence -> 'shared') = 'array' THEN x.evidence -> 'shared'"
    " ELSE '[]'::jsonb END) s WHERE x.type = '{tur}' AND x.origin = 'hat' AND x.status = 'aday'"
    " AND NOT (jsonb_typeof(s -> '{ad}') = 'number' AND"
    " starts_with(s ->> 'src_word', x.src_anchor || ':') AND"
    " starts_with(s ->> 'dst_word', x.dst_anchor || ':') AND"
    " EXISTS (SELECT 1 FROM icerik.quran_word w WHERE w.anchor = s ->> 'src_word'"
    " AND w.{sutun} = (s ->> '{ad}')::int) AND"
    " EXISTS (SELECT 1 FROM icerik.quran_word w WHERE w.anchor = s ->> 'dst_word'"
    " AND w.{sutun} = (s ->> '{ad}')::int))" + KAPSAM
)
SQL_SORGULARI: Final[Mapping[str, str]] = {
    "kok_tutarsiz": _ORTAK_ESLESME.format(tur="kok", ad="root", sutun="root_id"),
    "lemma_tutarsiz": _ORTAK_ESLESME.format(tur="lemma", ad="lemma", sutun="lemma_id"),
    "shared_bos": (
        "SELECT count(*) FROM icerik.xref x WHERE x.type IN ('kok', 'lemma') AND x.origin = 'hat'"
        " AND x.status = 'aday' AND (jsonb_typeof(x.evidence -> 'shared') IS DISTINCT FROM"
        " 'array' OR jsonb_array_length(x.evidence -> 'shared') = 0)" + KAPSAM
    ),
    "kayitsiz_source_id": (
        "SELECT count(*) FROM icerik.xref x WHERE x.origin = 'hat' AND NOT EXISTS"
        " (SELECT 1 FROM icerik.source s WHERE s.slug = x.evidence ->> 'source_id')" + KAPSAM
    ),
    "aday_ozet_eski": (
        "SELECT count(*) FROM icerik.xref x WHERE x.origin = 'hat' AND x.status = 'aday'"
        " AND x.type IN ('kok', 'lemma', 'benzer_ayet') AND ("
        "NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = x.src_anchor AND u.kind = 'ayet'"
        " AND u.source_id = 'tanzil-uthmani' AND left(u.content_hash, 16) ="
        " x.evidence ->> 'src_hash') OR NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE"
        " u.anchor = x.dst_anchor AND u.kind = 'ayet' AND u.source_id = 'tanzil-uthmani'"
        " AND left(u.content_hash, 16) = x.evidence ->> 'dst_hash'))" + KAPSAM
    ),
    "benzer_ayet_src_kucuk_degil": (
        "SELECT count(*) FROM icerik.xref x JOIN icerik.quran_word a ON a.anchor ="
        " x.src_anchor || ':1' JOIN icerik.quran_word b ON b.anchor = x.dst_anchor || ':1'"
        " WHERE x.type = 'benzer_ayet' AND x.origin = 'hat' AND a.ayah_index >= b.ayah_index"
        + KAPSAM
    ),
}


def sql_hatalari(conn: psycopg.Connection, turler: Sequence[str] | None = None) -> dict[str, int]:
    """`icerik.xref` icindeki hat satirlarinin ihlalleri (hepsi 0 olmali; salt okuma).

    `turler` verilirse yalniz o turlerin satirlari denetlenir (yukleme: kosunun kapsami).
    """
    kapsam = "" if turler is None else " AND x.type::text = ANY(%(turler)s)"
    sonuc: dict[str, int] = {}
    for ad, sorgu in SQL_SORGULARI.items():
        satir = conn.execute(
            sorgu.replace(KAPSAM, kapsam), {"turler": list(turler)} if turler is not None else None
        ).fetchone()
        sonuc[ad] = int(satir[0]) if satir is not None else 0
    return sonuc
