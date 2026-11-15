"""Atif ve iktibas satirlarinin uretimi (staged biçimi) ve istatistik (A18.4).

Cikti, `xref` dogal anahtarli satirlardir: `type` (`atif` | `iktibas`), `src_anchor` (meal birim
capasi), `src_span` (kod noktasi `[bas, son)`), `dst_anchor` (`q:s:a`), `dst_span` (iktibasta
kelime konumu `[ilk, son + 1)`, atifta NULL), `score`, `confidence`, `evidence`, `data_version`.
Sira alanlari (`tur_no`, `src_no`, `src_bas`, `dst_no`, `dst_bas`) staged siralamasini belirler;
yukleyici bunlari yazmaz. Staged dosya ondalik JSON sayisi tasimaz: ondalik degerler 6 haneli
dizgedir (`ondalik`); `sayisal` yukleme ve QA icin sayiya cevirir.
"""

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.enrich.baglantilar.uret import ondalik
from mutalaa_pipeline.enrich.citations.iktibas import (
    ATIF,
    IKTIBAS,
    AdayHat,
    Birim,
    MotorGirdisi,
    birim_isle,
)
from mutalaa_pipeline.enrich.citations.kurallar import sinif_ipucu

TURLER: Final = (ATIF, IKTIBAS)  # staged sirasi (tur_no)
CITATIONS_SURUMU: Final = "1"
ONDALIK: Final = re.compile(r"[0-9]\.[0-9]{6}")
UTHMANI_KAYNAGI: Final = "tanzil-uthmani"
SIMPLE_KAYNAGI: Final = "tanzil-simple-clean"


@dataclass
class Uretim:
    satirlar: list[dict[str, object]] = field(default_factory=list)
    istatistik: dict[str, object] = field(default_factory=dict)


def _kanit_dizgeye(kanit: Mapping[str, object]) -> dict[str, object]:
    yeni = dict(kanit)
    for alan in ("coverage", "identity"):
        deger = yeni.get(alan)
        if isinstance(deger, float):
            yeni[alan] = ondalik(deger)
    baglam = yeni.get("context")
    if isinstance(baglam, dict) and isinstance(baglam.get("meal_benzerligi"), float):
        yeni["context"] = {**baglam, "meal_benzerligi": ondalik(baglam["meal_benzerligi"])}
    return yeni


def _sayi_cevir(deger: object) -> float:
    if not isinstance(deger, str) or ONDALIK.fullmatch(deger) is None:
        raise ValueError("ondalik dizge degil")
    return float(deger)


def sayisal(veri: Mapping[str, object]) -> dict[str, object]:
    """Staged satirin ondalik dizgelerini sayiya cevirir; hatali biçimde `ValueError`."""
    sonuc = dict(veri)
    for alan in ("score", "confidence"):
        sonuc[alan] = _sayi_cevir(veri.get(alan))
    kanit = veri.get("evidence")
    if not isinstance(kanit, dict):
        raise ValueError("evidence nesne degil")
    yeni = dict(kanit)
    for alan in ("coverage", "identity"):
        if alan in yeni:
            yeni[alan] = _sayi_cevir(yeni[alan])
    baglam = yeni.get("context")
    if isinstance(baglam, dict) and "meal_benzerligi" in baglam:
        yeni["context"] = {**baglam, "meal_benzerligi": _sayi_cevir(baglam["meal_benzerligi"])}
    sonuc["evidence"] = yeni
    return sonuc


def satir_kur(h: AdayHat, birim_no: int, dst_capa: str, data_version: str) -> dict[str, object]:
    kanit = _kanit_dizgeye(h.evidence)
    kanit.setdefault("src_span", list(h.src_span))
    return {
        "tur_no": TURLER.index(h.tur),
        "src_no": birim_no,
        "src_bas": h.src_span[0],
        "dst_no": h.dst_sira,
        "dst_bas": h.dst_span[0] if h.dst_span else 0,
        "type": h.tur,
        "src_anchor": h.src_anchor,
        "dst_anchor": dst_capa,
        "src_span": list(h.src_span),
        "dst_span": list(h.dst_span) if h.dst_span else None,
        "score": ondalik(h.score),
        "confidence": ondalik(h.confidence),
        "evidence": kanit,
        "data_version": data_version,
    }


def _sinif(h: AdayHat) -> str:
    kanit = h.evidence
    mw = kanit.get("matched_words")
    cov = kanit.get("coverage")
    pf = kanit.get("phrase_freq")
    cq = kanit.get("consistent_quote")
    return sinif_ipucu(
        h.tur,
        h.confidence,
        matched_words=mw if isinstance(mw, int) else None,
        coverage=cov if isinstance(cov, float) else None,
        phrase_freq=pf if isinstance(pf, int) else None,
        consistent_quote=cq if isinstance(cq, bool) else None,
    )


def uret(
    g: MotorGirdisi,
    birimler: Sequence[Birim],
    data_version: str,
) -> Uretim:
    """Birimlerin (anchor baytlarina gore sirali) atif ve iktibas satirlari ve istatistigi."""
    sayac: Counter[str] = Counter()
    sonuc = Uretim()
    guven_kovalari: Counter[str] = Counter()
    siniflar: dict[str, Counter[str]] = {t: Counter() for t in TURLER}
    kaynak_tur: dict[str, Counter[str]] = {}
    for no, b in enumerate(birimler):
        satirlar = birim_isle(g, b, sayac)
        kaynak = b.anchor.split(":")[1]
        for h in satirlar:
            sonuc.satirlar.append(satir_kur(h, no, g.ayet_capalari[h.dst_sira], data_version))
            siniflar[h.tur][_sinif(h)] += 1
            kaynak_tur.setdefault(kaynak, Counter())[h.tur] += 1
            kova = min(9, int(h.confidence * 10))
            guven_kovalari[f"{kova / 10:.1f}-{(kova + 1) / 10:.1f}"] += 1
    sonuc.satirlar.sort(
        key=lambda s: (s["tur_no"], s["src_no"], s["src_bas"], s["dst_no"], s["dst_bas"])
    )
    tur_sayilari = Counter(str(s["type"]) for s in sonuc.satirlar)
    ist: dict[str, object] = {
        "satir_toplam": len(sonuc.satirlar),
        "tur": {t: tur_sayilari[t] for t in TURLER},
        "sinif": {t: dict(sorted(siniflar[t].items())) for t in TURLER},
        "guven_dagilimi": dict(sorted(guven_kovalari.items())),
        "kaynak_tur": {k: dict(sorted(v.items())) for k, v in sorted(kaynak_tur.items())},
        "sayaclar": dict(sorted(sayac.items())),
        "ad_tabanli_etkin": bool(g.sozluk is not None and not g.sozluk.bos),
        "kalip_listesi_girdi": len(g.kalip),
        "adlandirilmis_ayet": len(g.adlandirilmis),
        "indeksler": [i.ad for i in g.indeksler],
    }
    sonuc.istatistik = ist
    return sonuc
