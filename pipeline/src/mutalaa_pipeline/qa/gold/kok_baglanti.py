"""`kok-baglanti` seti ve olcumu: Kur'an ici `kok` xref satirlarinin QAC tutarliligi (A18.5).

KAPI: `xref_gate (kok, 'xref', altin)`; `olcum_turu = tutarlilik` (K-51 madde 12; `lemma` kalibi).

Set (`altin`, deterministik): QAC morfolojisinin (`qac-morfoloji`, `enrich morphology` staged
`words.jsonl`) ayet basina kok kumesi (`root_letters_bw`); 6.236 ornek, her ornek bir ayet.

Olcum: her `kok` xref satirinda (`origin = 'hat'`) `evidence.shared[].root` kok kimliklerinin
HEPSI, kaynak ve hedef ayetin (1) veritabanindaki `quran_word.root_id` kumesinde VE (2) QAC set
kumelerinin KESISIMINDE bulunmali. Satir tutarli ise sayilir; `tutarlilik` = tutarli satir /
satir, esik 1,0. Bos `shared` listesi tutarsizdir. Satir yoksa olcum 0,0'dir (bos kume sessizce
gecmez).

Dogruluk degil TUTARLILIK testidir: uretim de QAC'den turedigi icin dongusellik denetimi uygulanmaz
(manifest `olcum_turu = tutarlilik`; K-51 madde 12). Deterministik oldugu icin bolme uygulanmaz.
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Final

import psycopg

from mutalaa_pipeline.qa.gold import lemma, setler
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import ESIKLER, esik_degerlendir, kapi_karari

KAYNAK_QAC: Final = "qac-morfoloji"
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type kok-baglanti --build"
DOGRULAMA_YONTEMI: Final = (
    "QAC morfolojisi (staged words.jsonl) ayet basina kok kumeleri; her kok xref satirinda"
    " paylasilan kok kimlikleri kaynak ve hedef ayetin hem veritabani quran_word.root_id"
    " kumesinde hem QAC kumelerinin kesisiminde bulunur (deterministik tutarlilik testi)."
)

SORGU_AYET_KOKLERI: Final = (
    "SELECT w.surah, w.ayah, array_remove(array_agg(DISTINCT w.root_id), NULL)"
    " FROM icerik.quran_word w GROUP BY w.surah, w.ayah"
)
SORGU_XREF: Final = (
    "SELECT x.src_anchor, x.dst_anchor, x.evidence -> 'shared' FROM icerik.xref x"
    " WHERE x.type = 'kok' AND x.origin = 'hat' ORDER BY x.src_anchor, x.dst_anchor"
)

KokSatiri = tuple[str, str, list[int]]  # (src, dst, paylasilan kok kimlikleri)


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
            "kok_harfleri_bw": kokler,
        }
        for capa, (_, kokler) in kumeler.items()
    ]


def taslak(qac_surum: str, tohum: int = setler.VARSAYILAN_TOHUM) -> dict[str, object]:
    return {
        "sinif": "altin",
        "olcum_turu": "tutarlilik",
        "kaynak": [
            {
                "source_id": KAYNAK_QAC,
                "surum": qac_surum,
                "madde": "staged words.jsonl: root_letters_bw (ayet basina)",
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


def db_ayet_kok_kimlikleri(conn: psycopg.Connection) -> dict[str, frozenset[int]]:
    return {
        lemma.ayet_capasi(s, a): frozenset(int(k) for k in kokler)
        for s, a, kokler in conn.execute(SORGU_AYET_KOKLERI).fetchall()
    }


def kok_xref_satirlari(conn: psycopg.Connection) -> list[KokSatiri]:
    """`(src, dst, paylasilan kok kimlikleri)`; kimlik evidence.shared[].root."""
    sonuc: list[KokSatiri] = []
    for src, dst, shared in conn.execute(SORGU_XREF).fetchall():
        ids = [int(s["root"]) for s in (shared or []) if isinstance(s, dict) and "root" in s]
        sonuc.append((str(src), str(dst), ids))
    return sonuc


def kok_harfleri(conn: psycopg.Connection) -> dict[int, str]:
    return {
        int(i): str(h) for i, h in conn.execute("SELECT id, letters_bw FROM icerik.root").fetchall()
    }


def kok_baglanti_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    db_kokler: Mapping[str, frozenset[int]],
    xref: Iterable[KokSatiri],
    harfler: Mapping[int, str],
) -> TurSonucu:
    qac = {str(o["id"]): set(o["kok_harfleri_bw"]) for o in ornekler}  # type: ignore[call-overload]
    satirlar = list(xref)
    tutarsiz: list[str] = []
    db_tutmadi = qac_tutmadi = bos_shared = 0
    for src, dst, ids in satirlar:
        if not ids:
            bos_shared += 1
            tutarsiz.append(f"{src}|{dst}")
            continue
        db_s, db_d = db_kokler.get(src, frozenset()), db_kokler.get(dst, frozenset())
        q_s, q_d = qac.get(src, set()), qac.get(dst, set())
        db_ok = all(i in db_s and i in db_d for i in ids)
        qac_ok = all(harfler.get(i, "") in q_s and harfler.get(i, "") in q_d for i in ids)
        db_tutmadi += not db_ok
        qac_tutmadi += not qac_ok
        if not (db_ok and qac_ok):
            tutarsiz.append(f"{src}|{dst}")
    toplam = len(satirlar)
    tutarli = toplam - len(tutarsiz)
    olculer = {"tutarlilik": tutarli / toplam if toplam else 0.0}
    esikler = dict(ESIKLER["kok_baglanti"])
    return TurSonucu(
        cli_tur="kok-baglanti",
        manifest=manifest,
        sonuc=kapi_karari(esikler, olculer),
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=tahmin_ozeti(
            [f"{s}|{d}|{','.join(map(str, i))}" for s, d, i in sorted(satirlar)]
        ),
        olculen_ornek=toplam,
        ayrintilar={
            "xref": {
                "satir": toplam,
                "tutarli": tutarli,
                "tutarsiz": len(tutarsiz),
                "bos_shared": bos_shared,
                "db_root_id_kumesinde_degil": db_tutmadi,
                "qac_kesisiminde_degil": qac_tutmadi,
                "tutarsiz_ornekleri": tutarsiz[:20],
            },
            "set_ornek_ayet": len(qac),
            "bolme": "uygulanmaz (deterministik tutarlilik testi)",
        },
        notlar=[
            (
                "Dogruluk degil tutarlilik testidir; uretim de QAC'den turedigi icin dongusellik "
                "denetimi uygulanmaz (K-51 madde 12)."
            ),
            "Olculen: Kur'an ici kok xref satirlarinin tamami (ornekleme yok).",
        ],
        referans_kapsami={"kapsam": "veritabanindaki tum `kok` xref satirlari (origin = hat)"},
        uretim_kaynaklari=[KAYNAK_QAC],
    )
