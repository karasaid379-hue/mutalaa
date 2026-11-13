"""`lemma` seti ve olcumu: QAC tutarliligi (A18.5; K-51 madde 12; sinif `altin`, deterministik).

Set: QAC morfolojisinin (`qac-morfoloji` surum 0.4, `enrich morphology` staged `words.jsonl`)
ayet basina lemma (`lemma_qac_ref`) ve kok (`root_letters_bw`) kumeleri; 6.236 ornek, her ornek bir
ayet. Deterministik tutarlilik testidir (A17 `quran_word.lemma_id` QAC govde LEM'inden turer):

1. AYET: veritabanindaki ayet basina lemma kumesi (`quran_word.lemma_id` -> `lemma.qac_ref`) ve kok
   kumesi (`quran_word.root_id` -> `root.letters_bw`) QAC kumeleriyle ayni mi.
2. XREF: her `lemma` xref satirinda paylasilan lemma, kaynak ve hedef ayetin QAC lemma
   kumelerinin KESISIMINDE mi (Test stratejisi §4: "`xref` satiri icin %100 tutarli").

`tutarlilik` = (tutarli ayet + tutarli xref satiri) / (ayet + xref satiri); esik 1,0. Olcum
dogruluk degil TUTARLILIK testidir: uretim de QAC'den turedigi icin dongusellik denetimi bu turde
uygulanmaz (manifest `olcum_turu = tutarlilik`; K-51 madde 12). Deterministik oldugu icin bolme
uygulanmaz, bütün orneklerde olculur.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

import psycopg

from mutalaa_pipeline.qa.checks.xref import sql_hatalari
from mutalaa_pipeline.qa.gold import setler
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import ESIKLER, esik_degerlendir, kapi_karari

KAYNAK_QAC: Final = "qac-morfoloji"
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type lemma --build"
DOGRULAMA_YONTEMI: Final = (
    "QAC morfolojisi (staged words.jsonl) ayet basina lemma ve kok kumeleri; veritabani"
    " quran_word lemma/kok kumeleriyle ve lemma xref satirlarinin paylasilan lemmasiyla"
    " karsilastirilir (deterministik tutarlilik testi)."
)


def ayet_capasi(sure: object, ayet: object) -> str:
    return f"q:{int(str(sure))}:{int(str(ayet))}"


def qac_ayet_kumeleri(
    kelimeler: Iterable[Mapping[str, object]],
) -> dict[str, tuple[list[str], list[str]]]:
    """QAC kelime satirlarindan ayet -> (sirali lemma refleri, sirali kok harfleri)."""
    lemma: dict[str, set[str]] = defaultdict(set)
    kok: dict[str, set[str]] = defaultdict(set)
    for k in kelimeler:
        capa = ayet_capasi(k["surah"], k["ayah"])
        lemma[capa]
        kok[capa]
        if k.get("lemma_qac_ref"):
            lemma[capa].add(str(k["lemma_qac_ref"]))
        if k.get("root_letters_bw"):
            kok[capa].add(str(k["root_letters_bw"]))
    return {c: (sorted(lemma[c]), sorted(kok[c])) for c in sorted(lemma)}


def ornekleri_kur(
    kumeler: Mapping[str, tuple[list[str], list[str]]], qac_surum: str
) -> list[dict[str, object]]:
    return [
        {
            "id": capa,
            "sinif": "altin",
            "kaynak": {
                "source_id": KAYNAK_QAC,
                "surum": qac_surum,
                "madde": f"words.jsonl {capa}",
            },
            "dogrulama_yontemi": DOGRULAMA_YONTEMI,
            "uretim_komutu": URETIM_KOMUTU,
            "lemma_qac_refler": lemmalar,
            "kok_harfleri_bw": kokler,
        }
        for capa, (lemmalar, kokler) in kumeler.items()
    ]


def taslak(qac_surum: str, tohum: int = setler.VARSAYILAN_TOHUM) -> dict[str, object]:
    return {
        "sinif": "altin",
        "olcum_turu": "tutarlilik",
        "kaynak": [
            {
                "source_id": KAYNAK_QAC,
                "surum": qac_surum,
                "madde": "staged words.jsonl: lemma_qac_ref ve root_letters_bw (ayet basina)",
                "rol": "kanit",
            }
        ],
        "dogrulama_yontemi": DOGRULAMA_YONTEMI,
        "uretim_komutu": URETIM_KOMUTU,
        "tohum": tohum,
        "dongusellik_notu": (
            "Tutarlilik testi: uretim de QAC'den turedigi icin dongusellik denetimi uygulanmaz"
            " (K-51 madde 12); bolme uygulanmaz."
        ),
    }


SORGU_AYET: Final = (
    "SELECT w.surah, w.ayah, array_remove(array_agg(DISTINCT l.qac_ref), NULL),"
    " array_remove(array_agg(DISTINCT r.letters_bw), NULL)"
    " FROM icerik.quran_word w"
    " LEFT JOIN icerik.lemma l ON l.id = w.lemma_id"
    " LEFT JOIN icerik.root r ON r.id = w.root_id"
    " GROUP BY w.surah, w.ayah"
)
SORGU_XREF: Final = (
    "SELECT x.src_anchor, x.dst_anchor, x.evidence -> 'shared' FROM icerik.xref x"
    " WHERE x.type = 'lemma' AND x.origin = 'hat'"
    " ORDER BY x.src_anchor, x.dst_anchor"
)


def db_ayet_kumeleri(conn: psycopg.Connection) -> dict[str, tuple[list[str], list[str]]]:
    return {
        ayet_capasi(s, a): (sorted(str(x) for x in lm), sorted(str(x) for x in kk))
        for s, a, lm, kk in conn.execute(SORGU_AYET).fetchall()
    }


def lemma_xref_satirlari(
    conn: psycopg.Connection,
) -> list[tuple[str, str, list[int]]]:
    """`(src, dst, paylasilan lemma kimlikleri)`; kimlik evidence.shared[].lemma."""
    sonuc: list[tuple[str, str, list[int]]] = []
    for src, dst, shared in conn.execute(SORGU_XREF).fetchall():
        ids = [int(s["lemma"]) for s in (shared or []) if isinstance(s, dict) and "lemma" in s]
        sonuc.append((str(src), str(dst), ids))
    return sonuc


def lemma_refleri(conn: psycopg.Connection) -> dict[int, str]:
    return {
        int(i): str(r)
        for i, r in conn.execute(
            "SELECT id, qac_ref FROM icerik.lemma WHERE qac_ref IS NOT NULL"
        ).fetchall()
    }


def lemma_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    db_ayet: Mapping[str, tuple[list[str], list[str]]],
    xref: Sequence[tuple[str, str, Sequence[int]]],
    refler: Mapping[int, str],
    sql_ihlalleri: Mapping[str, int] | None = None,
) -> TurSonucu:
    qac = {
        str(o["id"]): (list(o["lemma_qac_refler"]), list(o["kok_harfleri_bw"]))  # type: ignore[call-overload]
        for o in ornekler
    }
    lemma_farki: list[str] = []
    kok_farki: list[str] = []
    eksik_ayet = 0
    for capa, (lemmalar, kokler) in qac.items():
        db = db_ayet.get(capa)
        if db is None:
            eksik_ayet += 1
            lemma_farki.append(capa)
            continue
        if db[0] != lemmalar:
            lemma_farki.append(capa)
        if db[1] != kokler:
            kok_farki.append(capa)
    tutarli_ayet = len(qac) - len(set(lemma_farki))
    xref_hatali: list[str] = []
    for src, dst, ids in xref:
        s, d = qac.get(src), qac.get(dst)
        if s is None or d is None or not ids:
            xref_hatali.append(f"{src}|{dst}")
            continue
        ortak = set(s[0]) & set(d[0])
        if any(refler.get(i) not in ortak for i in ids):
            xref_hatali.append(f"{src}|{dst}")
    tutarli_xref = len(xref) - len(xref_hatali)
    toplam = len(qac) + len(xref)
    tutarlilik = (tutarli_ayet + tutarli_xref) / toplam if toplam else 0.0
    olculer = {
        "tutarlilik": tutarlilik,
        "tutarlilik_ayet": tutarli_ayet / len(qac) if qac else 0.0,
        "tutarlilik_xref": tutarli_xref / len(xref) if xref else 1.0,
    }
    esikler = dict(ESIKLER["lemma"])
    sonuc = kapi_karari(esikler, olculer)
    sorgu = dict(sql_ihlalleri or {})
    return TurSonucu(
        cli_tur="lemma",
        manifest=manifest,
        sonuc=sonuc,
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=tahmin_ozeti(
            [
                *(f"{c}|{'/'.join(v[0])}|{'/'.join(v[1])}" for c, v in sorted(db_ayet.items())),
                *(f"{s}|{d}|{','.join(map(str, i))}" for s, d, i in xref),
            ]
        ),
        olculen_ornek=len(qac),
        ayrintilar={
            "ayet": {
                "ornek": len(qac),
                "tutarli": tutarli_ayet,
                "lemma_kumesi_farkli": len(set(lemma_farki)),
                "kok_kumesi_farkli_bilgi": len(set(kok_farki)),
                "veritabaninda_olmayan_ayet": eksik_ayet,
                "farkli_ayet_ornekleri": sorted(set(lemma_farki))[:20],
            },
            "xref": {
                "satir": len(xref),
                "tutarli": tutarli_xref,
                "tutarsiz_ornekleri": xref_hatali[:20],
            },
            "xref_sql_ihlalleri_a18_3": dict(sorted(sorgu.items())),
            "bolme": "uygulanmaz (deterministik tutarlilik testi)",
        },
        notlar=[
            (
                "Dogruluk degil tutarlilik testidir; uretim de QAC'den turedigi icin dongusellik "
                "denetimi uygulanmaz (K-51 madde 12)."
            ),
            "Kok kumesi farki bilgi amaclidir; kapi yalniz lemma tutarliligina bakar.",
        ],
        referans_kapsami={"kapsam": "Kur'an'in 6.236 ayeti ve lemma xref satirlarinin tamami"},
        uretim_kaynaklari=[KAYNAK_QAC],
    )


def sql_ihlalleri_al(conn: psycopg.Connection) -> dict[str, int]:
    return sql_hatalari(conn, ["lemma"])
