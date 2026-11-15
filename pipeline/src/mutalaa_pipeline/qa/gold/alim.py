"""`benzer-ayet-alim` seti ve olcumu: alim kaynakli satirlarin KAYNAK BUTUNLUGU (A18.5).

KAPI: `xref_gate (benzer_ayet, 'alim', altin)`; `olcum_turu = kaynak` (K-51 madde 12).

Olculen satirlar: `evidence.source_id = 'qursim'` YA DA `evidence.qursim` nesnesi olan HER
`benzer_ayet` satiri (QurSim'in kendi cifti ya da sozluksel satirin QurSim ile ortak isaretli
hali). Set: `QurSim_filtered.csv` ciftleri (yalniz `SS`, `SV`, `TS`, `TV`, `Label` okunur; metin
sutunlarina dokunulmaz), `lo < hi` kuresel ayet sirasiyla normallestirilmis.

Her satir icin iki sey denetlenir: (1) cift (yon normalize) QurSim cift kumesinde; (2) satirin
`evidence.source_id` degeri ve (varsa) `evidence.qursim` isaretinin kaynagi (`qursim`) kayitli
kaynaklar arasinda. `kaynak_butunlugu` = ikisi de tutan satir / olculen satir; esik 1,0. Olculen
satir yoksa 0,0'dir (bos kume gecmez).

BU BIR DOGRULUK OLCUMU DEGILDIR: set, olculen uretimin kaynagidir (donguselligi belgeli ve
bilincli: manifest `olcum_turu = kaynak`; dongusellik denetimi bu turde muaftir). Olculen sey
"uretim, kaynagin cift listesini ve kaynak kimligini bozmadan tasidi mi"dir. Sozluksel satirlarin
dogrulugu ayri kapida (`benzer_ayet`/`sozluksel`) olculur.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

import psycopg

from mutalaa_pipeline.qa.gold import setler
from mutalaa_pipeline.qa.gold.benzer import CiftAnahtari, cift
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import ESIKLER, esik_degerlendir, kapi_karari

KAYNAK_QURSIM: Final = "qursim"
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type benzer-ayet-alim --build"
DOGRULAMA_YONTEMI: Final = (
    "QurSim_filtered.csv cift kumesi (SS, SV, TS, TV; yon normalize lo < hi): alim kaynakli her"
    " benzer_ayet satirinin cifti kumede ve source_id kayitli olmali (kaynak butunlugu; dogruluk"
    " olcumu degil)."
)
SORGU_SATIRLAR: Final = (
    "SELECT src_anchor, dst_anchor, evidence FROM icerik.xref"
    " WHERE type = 'benzer_ayet' AND origin = 'hat' ORDER BY src_anchor, dst_anchor"
)
SORGU_KAYITLI: Final = "SELECT slug FROM icerik.source"
AlimSatiri = tuple[str, str, Mapping[str, object]]  # (src, dst, evidence)


def alim_mi(kanit: object) -> bool:
    """`evidence.source_id = 'qursim'` ya da `evidence.qursim` nesnesi."""
    return isinstance(kanit, dict) and (
        kanit.get("source_id") == KAYNAK_QURSIM or isinstance(kanit.get("qursim"), dict)
    )


def ornekleri_kur(
    qursim: Mapping[CiftAnahtari, int], ayet_capasi: Mapping[int, str], qursim_surum: str
) -> list[dict[str, object]]:
    return [
        {
            "id": f"{ayet_capasi[c[0]]}|{ayet_capasi[c[1]]}",
            "sinif": "altin",
            "kaynak": {
                "source_id": KAYNAK_QURSIM,
                "surum": qursim_surum,
                "madde": "QurSim_filtered.csv cift",
            },
            "dogrulama_yontemi": DOGRULAMA_YONTEMI,
            "uretim_komutu": URETIM_KOMUTU,
            "qursim_label": qursim[c],
        }
        for c in sorted(qursim)
    ]


def taslak(qursim_surum: str, sayilar: Mapping[str, object]) -> dict[str, object]:
    return {
        "sinif": "altin",
        "olcum_turu": "kaynak",
        "kaynak": [
            {
                "source_id": KAYNAK_QURSIM,
                "surum": qursim_surum,
                "madde": "QurSim_filtered.csv (SS, SV, TS, TV, Label)",
                "rol": "kanit",
            }
        ],
        "dogrulama_yontemi": DOGRULAMA_YONTEMI,
        "uretim_komutu": URETIM_KOMUTU,
        "tohum": setler.VARSAYILAN_TOHUM,
        "dongusellik_notu": (
            "Kaynak butunlugu olcumu: set uretim kaynaginin kendisidir (QurSim); dongusellik"
            " denetimi bu tur icin muaftir (olcum_turu = kaynak). Dogruluk degil, kaynagin cift"
            " listesinin ve kaynak kimliginin bozulmadan tasindigi denetlenir."
        ),
        "ozet_sayilar": dict(sayilar),
    }


def alim_satirlari(conn: psycopg.Connection) -> tuple[list[AlimSatiri], int]:
    """Alim kaynakli satirlar `(src, dst, evidence)` ve alim OLMAYAN benzer_ayet satiri sayisi."""
    secilen: list[AlimSatiri] = []
    diger = 0
    for src, dst, kanit in conn.execute(SORGU_SATIRLAR).fetchall():
        if alim_mi(kanit):
            secilen.append((str(src), str(dst), kanit))
        else:
            diger += 1
    return secilen, diger


def kayitli_kaynaklar(conn: psycopg.Connection) -> frozenset[str]:
    return frozenset(str(s) for (s,) in conn.execute(SORGU_KAYITLI).fetchall())


def _kullanilan_kaynaklar(kanit: Mapping[str, object]) -> frozenset[str]:
    kaynaklar = {str(kanit.get("source_id"))}
    if isinstance(kanit.get("qursim"), dict):
        kaynaklar.add(KAYNAK_QURSIM)
    return frozenset(kaynaklar)


def alim_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    satirlar: Iterable[AlimSatiri],
    sira: Mapping[str, int],
    kayitli: frozenset[str],
    *,
    alim_olmayan_satir: int = 0,
) -> TurSonucu:
    kume: set[CiftAnahtari] = set()
    for o in ornekler:
        capa_a, capa_b = str(o["id"]).split("|")
        kume.add(cift(sira[capa_a], sira[capa_b]))
    olculen = list(satirlar)
    sayac: Counter[str] = Counter()
    gorulen: set[CiftAnahtari] = set()
    kusurlu: list[str] = []
    for src, dst, kanit in olculen:
        a, b = sira.get(src), sira.get(dst)
        cift_tuttu = a is not None and b is not None and cift(a, b) in kume
        kayit_tuttu = _kullanilan_kaynaklar(kanit) <= kayitli
        if a is not None and b is not None:
            gorulen.add(cift(a, b))
        if not cift_tuttu:
            sayac["cift_qursim_de_yok"] += 1
        if not kayit_tuttu:
            sayac["source_id_kayitli_degil"] += 1
        if not (cift_tuttu and kayit_tuttu):
            kusurlu.append(f"{src}|{dst}")
    n = len(olculen)
    tutan = n - len(kusurlu)
    olculer = {"kaynak_butunlugu": tutan / n if n else 0.0}
    esikler = dict(ESIKLER["benzer_ayet_alim"])
    kaynak_dagilimi = Counter(",".join(sorted(_kullanilan_kaynaklar(k))) for _, _, k in olculen)
    return TurSonucu(
        cli_tur="benzer-ayet-alim",
        manifest=manifest,
        sonuc=kapi_karari(esikler, olculer),
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=tahmin_ozeti(sorted(f"{s}|{d}" for s, d, _ in olculen)),
        olculen_ornek=n,
        ayrintilar={
            "olculen_satir": n,
            "tutan_satir": tutan,
            "kusurlu_satir": len(kusurlu),
            "kusur_nedenleri": dict(sorted(sayac.items())),
            "kusurlu_ornekleri": kusurlu[:20],
            "qursim_cift_sayisi": len(kume),
            "qursim_cifti_veritabaninda_olmayan": len(kume - gorulen),
            "kaynak_dagilimi": dict(sorted(kaynak_dagilimi.items())),
            "alim_olmayan_benzer_ayet_satiri_bilgi": alim_olmayan_satir,
            "kayitli_kaynak_sayisi": len(kayitli),
            "bolme": "uygulanmaz (kaynak butunlugu: butun alim satirlari olculur)",
        },
        notlar=[
            (
                "KAYNAK BUTUNLUGU olcumudur, dogruluk degil: set uretimin kaynagidir; dongusellik "
                "denetimi bu tur icin muaftir (olcum_turu = kaynak)."
            ),
            (
                "Olculen satirlar: evidence.source_id = qursim ya da evidence.qursim nesnesi olan "
                "tum benzer_ayet satirlari."
            ),
        ],
        referans_kapsami={
            "kapsam": "alim kaynakli (QurSim) tum satirlar",
            "qursim_cifti_veritabaninda_olmayan": len(kume - gorulen),
        },
        uretim_kaynaklari=sorted({k for _, _, e in olculen for k in _kullanilan_kaynaklar(e)}),
    )
