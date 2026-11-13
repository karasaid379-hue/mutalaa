"""`kok`, `lemma` ve `benzer_ayet` satirlarinin uretimi (A18.3).

Girdi bellektedir (`DbGirdisi`, Simple Clean ayet kelimeleri, QurSim sonucu); cikti, `xref`
dogal anahtarli satirlardir (`satir_kur`): `type`, `src_anchor`, `dst_anchor` (birim: ayet),
`src_span` ve `dst_span` NULL (birimin tamami), `score` = `confidence` (Baglanti modeli §6'da
ayri bir guven tanimi yoktur; K-51 madde 12 gibi), `evidence`, `data_version`. Sira alanlari
(`tur_no`, `src_no`, `dst_no`) staged dosyasinin capa sirasini belirler; yukleyici bunlari
yazmaz.

Satir bicimleri (`evidence`):

* `kok` / `lemma`: `shared` [{`root` | `lemma` (veritabani kimligi), `idf`, `src_word`,
  `dst_word`}], `src_hash`, `dst_hash` (birim `content_hash` ilk 16 hane), `source_id` =
  `qac-morfoloji`.
* `benzer_ayet` sozluksel: `subtype` = `sozluksel`, `matched_words`, `ayah_words`, `coverage`,
  `index` (`uthmani` | `imlai`), `kapsayan` (`src` | `dst`: sayimin yapildigi ayet), `src_hash`,
  `dst_hash`, `source_id` = `tanzil-uthmani`. QurSim da ayni cifti verdiyse ek olarak
  `qursim` = {`label`} ve `dongusel` = true (K-51 madde 10: QurSim ile olculemez).
* `benzer_ayet` QurSim: `subtype` = `alim`, `label` (ham), `src_hash`, `dst_hash`, `source_id` =
  `qursim`; `score` = `confidence` = 0,50 (sabit).
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.enrich.baglantilar.benzer import (
    EN_COK_BENZER,
    BenzerSatir,
    adaylari_bul,
    birlestir,
    sinirla,
)
from mutalaa_pipeline.enrich.baglantilar.girdi import Ayet, DbGirdisi, ayet_kelimeleri
from mutalaa_pipeline.enrich.baglantilar.kok_lemma import (
    EN_COK_KOMSU,
    IDF_ESIGI,
    Alan,
    Komsu,
    df_uyumsuzluklari,
    komsular,
    kumeleri_kur,
)
from mutalaa_pipeline.enrich.baglantilar.qursim import QursimSonucu
from mutalaa_pipeline.enrich.quran_index import KuranIndeksi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize.arabic import normalize_ar

KOK: Final = "kok"
LEMMA: Final = "lemma"
BENZER: Final = "benzer_ayet"
TURLER: Final = (KOK, LEMMA, BENZER)  # staged sirasi (tur_no)
QAC_KAYNAGI: Final = "qac-morfoloji"
UTHMANI_KAYNAGI: Final = "tanzil-uthmani"
QURSIM_KAYNAGI: Final = "qursim"
BESMELE_AYETI: Final = "q:1:1"
# Staged dosyasi ondalik JSON sayisi tasimaz (kati okuyucu, `export/ortak.kati_json`): ondalik
# degerler 6 haneli dizgedir (`ondalik`); `sayisal` yukleme ve QA icin sayiya cevirir.
ONDALIK: Final = re.compile(r"[0-9]\.[0-9]{6}")
LINKS_SURUMU: Final = "1"
ALAN_ADI: Final = {KOK: "root", LEMMA: "lemma"}
ALAN_SUTUNU: Final[Mapping[str, Alan]] = {KOK: "root_id", LEMMA: "lemma_id"}


@dataclass(frozen=True)
class SimpleKelimeleri:
    kelimeler: list[list[str]]
    besmele_kirpilan: int  # basmala onekinden arindirilan ilk ayet sayisi
    besmele_bulunmayan: int  # sure basi ayeti basmala ile baslamayan (9. sure vb.) ayet sayisi


@dataclass(frozen=True)
class Girdi:
    db: DbGirdisi
    simple: SimpleKelimeleri | None = None  # Simple Clean ayet kelimeleri (imlai indeks)
    qursim: QursimSonucu | None = None
    toplam: int | None = None  # IDF paydasi; None: ayet sayisi (gercek veride 6.236)


@dataclass
class Uretim:
    satirlar: list[dict[str, object]] = field(default_factory=list)
    istatistik: dict[str, object] = field(default_factory=dict)


def simple_kelimeleri(metinler: Mapping[str, str], ayetler: Sequence[Ayet]) -> SimpleKelimeleri:
    """Simple Clean ayet metinlerinden (`q:s:a` -> metin) normalize kelime listeleri.

    Ayet kumesi veritabanindakiyle birebir ayni olmali; aksi halde `GirdiHatasi`.

    Tanzil metin dosyalari basmalayi 1. ve 9. sure disindaki her surenin ILK ayetinin onune
    koyar (Simple Clean `q:2:1` basmala + ayet metnidir; QAC kelime dizisinde basmala yalniz
    `q:1:1`dedir). Basmala onekini hafizadan yazmayiz: `q:1:1` kelimeleri basmalanin kendisidir;
    1'den farkli bir surenin 1. ayeti bu kelimelerle basliyorsa ve geriye kelime kaliyorsa
    onek atilir (yalniz bellekteki eslestirme kopyasinda; kaynak metne dokunulmaz).
    """
    if set(metinler) != {a.capa for a in ayetler}:
        raise GirdiHatasi("Simple Clean ayet kumesi veritabanindaki ayet kumesiyle ayni degil")
    kelimeler = [normalize_ar(metinler[a.capa]).split() for a in ayetler]
    besmele: list[str] = []
    for a, k in zip(ayetler, kelimeler, strict=True):
        if a.capa == BESMELE_AYETI:
            besmele = k
    kirpilan = bulunmayan = 0
    if besmele:
        n = len(besmele)
        for a, k in zip(ayetler, kelimeler, strict=True):
            _, sure, ayet = a.capa.split(":")
            if ayet != "1" or sure == "1":
                continue
            if len(k) > n and k[:n] == besmele:
                del k[:n]
                kirpilan += 1
            else:
                bulunmayan += 1
    return SimpleKelimeleri(kelimeler, kirpilan, bulunmayan)


def ondalik(deger: float) -> str:
    """Staged ondalik dizgesi: 6 haneli, `0.500000` biciminde."""
    return f"{deger:.6f}"


def _sayi_cevir(deger: object) -> float:
    if not isinstance(deger, str) or ONDALIK.fullmatch(deger) is None:
        raise ValueError("ondalik dizge degil")
    return float(deger)


def sayisal(veri: Mapping[str, object]) -> dict[str, object]:
    """Staged satirin ondalik dizgelerini (`score`, `confidence`, `idf`, `coverage`) sayiya cevirir.

    Biciminde ya da yerinde olmayan deger `ValueError` verir; kopya doner, girdi degismez.
    """
    sonuc = dict(veri)
    for alan in ("score", "confidence"):
        sonuc[alan] = _sayi_cevir(veri.get(alan))
    kanit = veri.get("evidence")
    if not isinstance(kanit, dict):
        raise ValueError("evidence nesne degil")
    yeni = dict(kanit)
    if "coverage" in yeni:
        yeni["coverage"] = _sayi_cevir(yeni["coverage"])
    ortaklar = yeni.get("shared")
    if isinstance(ortaklar, list):
        yeni["shared"] = [
            {**o, "idf": _sayi_cevir(o.get("idf"))} if isinstance(o, dict) else o for o in ortaklar
        ]
    sonuc["evidence"] = yeni
    return sonuc


def satir_kur(
    tur: str,
    src: Ayet,
    dst: Ayet,
    skor: float,
    evidence: dict[str, object],
    data_version: str,
) -> dict[str, object]:
    return {
        "tur_no": TURLER.index(tur),
        "src_no": src.sira,
        "dst_no": dst.sira,
        "type": tur,
        "src_anchor": src.capa,
        "dst_anchor": dst.capa,
        "src_span": None,
        "dst_span": None,
        "score": ondalik(skor),
        "confidence": ondalik(skor),
        "evidence": evidence,
        "data_version": data_version,
    }


def _kok_lemma_satiri(tur: str, k: Komsu, ayetler: Sequence[Ayet], surum: str) -> dict[str, object]:
    src, dst = ayetler[k.src], ayetler[k.dst]
    ad = ALAN_ADI[tur]
    evidence: dict[str, object] = {
        "shared": [
            {
                ad: o.kimlik,
                "idf": ondalik(o.idf),
                "src_word": o.src_kelime,
                "dst_word": o.dst_kelime,
            }
            for o in k.ortaklar
        ],
        "src_hash": src.ozet,
        "dst_hash": dst.ozet,
        "source_id": QAC_KAYNAGI,
    }
    return satir_kur(tur, src, dst, k.skor, evidence, surum)


def kok_lemma_uret(
    girdi: Girdi, tur: str, surum: str, en_cok: int = EN_COK_KOMSU
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Bir turun (`kok` ya da `lemma`) satirlari ve istatistigi."""
    db = girdi.db
    kumeler = kumeleri_kur(db.kelimeler, ALAN_SUTUNU[tur], len(db.ayetler), toplam=girdi.toplam)
    if tur == KOK:
        uyumsuz = df_uyumsuzluklari(kumeler.df, db.kok_ayah_count)
        if uyumsuz:
            raise GirdiHatasi(
                f"root.ayah_count hesaplanan ayet sayisiyla tutmuyor ({len(uyumsuz)} kok)"
            )
    satirlar = [
        _kok_lemma_satiri(tur, k, db.ayetler, surum) for k in komsular(kumeler, en_cok=en_cok)
    ]
    ist: dict[str, object] = {
        "satir": len(satirlar),
        "kaynak_ayet": len({s["src_no"] for s in satirlar}),
        "kumesi_bos_ayet": sum(1 for kume in kumeler.ilk_kelime if not kume),
        "kimlik_toplam": len(kumeler.df),
        "idf_esigi_alti_cikarilan": kumeler.cikarilan,
        "kumede_kalan": len(kumeler.idf),
        "idf_esigi": IDF_ESIGI,
        "en_cok_komsu": en_cok,
    }
    return satirlar, ist


def _benzer_satiri(b: BenzerSatir, ayetler: Sequence[Ayet], surum: str) -> dict[str, object]:
    lo, hi = ayetler[b.lo], ayetler[b.hi]
    kanit: dict[str, object] = {"src_hash": lo.ozet, "dst_hash": hi.ozet}
    s = b.sozluksel
    if s is not None:
        kanit.update(
            subtype="sozluksel",
            matched_words=s.ortak,
            ayah_words=s.ayet_kelime,
            coverage=ondalik(s.kapsama),
            index=s.indeks,
            kapsayan=s.kapsayan,
            source_id=UTHMANI_KAYNAGI,
        )
        if b.qursim_label is not None:
            kanit.update(qursim={"label": b.qursim_label}, dongusel=True)
    else:
        kanit.update(subtype="alim", label=b.qursim_label, source_id=QURSIM_KAYNAGI)
    return satir_kur(BENZER, lo, hi, b.skor, kanit, surum)


def benzer_uret(
    girdi: Girdi, surum: str, en_cok: int = EN_COK_BENZER
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """`benzer_ayet`: sozluksel (Uthmani ve imlai) ve QurSim ciftleri, tek satir/cift."""
    db = girdi.db
    indeksler = {"uthmani": KuranIndeksi(ayet_kelimeleri(db.kelimeler, len(db.ayetler)))}
    if girdi.simple is not None:
        indeksler["imlai"] = KuranIndeksi(girdi.simple.kelimeler)
    adaylar = adaylari_bul(indeksler)
    secilen = sinirla(adaylar, en_cok)
    qs = girdi.qursim
    qursim = qs.ciftler if qs is not None else {}
    biriken = birlestir(adaylar, secilen, qursim)
    satirlar = [_benzer_satiri(b, db.ayetler, surum) for b in biriken]
    kesisim = {c for c in qursim if c in adaylar}
    farkli = (
        sum(
            1
            for sira, imlai in enumerate(girdi.simple.kelimeler)
            if len(imlai) != indeksler["uthmani"].ayet_uzunlugu(sira)
        )
        if girdi.simple is not None
        else 0
    )
    ist: dict[str, object] = {
        "satir": len(satirlar),
        "sozluksel_aday_cift": len(adaylar),
        "sozluksel_secilen_cift": len(secilen),
        "en_cok_benzer": en_cok,
        "indeksler": sorted(indeksler),
        "simple_besmele_kirpilan": girdi.simple.besmele_kirpilan if girdi.simple else 0,
        "simple_besmele_bulunmayan": girdi.simple.besmele_bulunmayan if girdi.simple else 0,
        "imlai_uthmani_kelime_sayisi_farkli_ayet": farkli,
        "uthmani_kazanan": sum(1 for a in adaylar.values() if a.indeks == "uthmani"),
        "imlai_kazanan": sum(1 for a in adaylar.values() if a.indeks == "imlai"),
        "satir_sozluksel": sum(1 for b in biriken if b.sozluksel is not None),
        "satir_saf_qursim": sum(1 for b in biriken if b.sozluksel is None),
        "satir_dongusel": sum(
            1 for b in biriken if b.sozluksel is not None and b.qursim_label is not None
        ),
        "qursim_gecerli_cift": len(qursim),
        "qursim_kendi_indeksimizde": len(kesisim),
        "qursim_kendi_indeksimizde_secilen": sum(1 for c in kesisim if c in secilen),
        "qursim_satir": qs.satir if qs is not None else 0,
        "qursim_gecersiz": qs.gecersiz_toplam if qs is not None else 0,
        "qursim_gecersiz_nedenler": dict(sorted(qs.gecersiz.items())) if qs is not None else {},
        "qursim_yinelenen": qs.yinelenen if qs is not None else 0,
        "qursim_label_dagilimi": (
            {str(k): v for k, v in sorted(qs.label_dagilimi.items())} if qs is not None else {}
        ),
    }
    return satirlar, ist


def uret(girdi: Girdi, turler: Sequence[str], surumler: Mapping[str, str]) -> Uretim:
    """`turler` icin satirlar (staged sirasinda) ve istatistik; `surumler`: tur -> data_version."""
    sonuc = Uretim()
    for tur in TURLER:
        if tur not in turler:
            continue
        if tur == BENZER:
            satirlar, ist = benzer_uret(girdi, surumler[tur])
        else:
            satirlar, ist = kok_lemma_uret(girdi, tur, surumler[tur])
        sonuc.satirlar.extend(satirlar)
        sonuc.istatistik[tur] = ist
    sonuc.istatistik["satir_toplam"] = len(sonuc.satirlar)
    return sonuc
