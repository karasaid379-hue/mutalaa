"""Turkce kelime -> Arapca kok QA kapilari (A18.2, K-51 madde 9): G-KAY, G-BUT, G-CAP.

Kapi islevleri bellekteki `TrRootsGirdisi` uzerinde calisir (dosya tarafi); `qa/run_tr_roots.py`
zinciri yukler. G-CAP uzantisi veritabani tarafidir (`span_hatalari`): `tr_root_index` icindeki
her aralik yari acik ve birim metni uzunlugu icinde, `unit_hash` birimin GUNCEL `content_hash`
degerinin ilk 16 hanesi olmali. `export pg` ayni sorguyu yukleme isleminin sonunda calistirir
(hata varsa islem geri alinir); `qa run --source kaikki-tr --db` ayni sorguyu ayri kosturur.

Bulgular ASCII ve kisadir; yalniz sayi, capa ve lemma sirasi tasir, SOZLUK METNI asla.

* G-KAY: kaynak kaydi gecerli, `tur = sozluk`, `atif_metni` dolu; manifestteki surum kayit
  surumuyle ayni; iki kaikki dokumunun SHA-256 degeri `SHA256SUMS` ile tutuyor.
* G-BUT: satir alan kumeleri, bos ve kontrol karakterli lemma/form yok, lemma NFC; sayilar
  tutarli (form sikliklarinin toplami = manifest token sayisi; lemma sikligi = bicimlerinin
  toplami); karar degerleri gecerli; `onayli_otomatik` her lemma satirinda GECERLI kanit
  (K-51 madde 9 biçimi).
* G-CAP: lemma ve form anahtarlari tekil; kok ve Arapca lemma QAC kumesinde, Arapca lemmanin koku
  lemma kokuyle ayni; her bicimin lemmasi lemma tablosunda (kok_yok disinda) ve karari ayni.
"""

import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg

from mutalaa_pipeline.enrich.tr_roots.eslesme import YONTEM_ETIMON, YONTEM_KOK
from mutalaa_pipeline.enrich.tr_roots.politika import (
    KARARLAR,
    KAYNAK_ID,
    KOK_YOK,
    ONAYLI,
    POLITIKA_ADI,
    POLITIKA_SURUMU,
    YONTEM_ADI,
    YONTEM_SURUMU,
)
from mutalaa_pipeline.normalize.turkish import normalize_tr
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

KAYNAK: Final = KAYNAK_ID
LEMMA_ALANLARI: Final = frozenset(
    {
        "lemma",
        "text_clean",
        "karar",
        "neden",
        "kanit",
        "root_letters_bw",
        "root_letters",
        "ar_lemma_qac_ref",
        "pos",
        "freq",
        "freq_kaynak",
        "review_onerilir",
        "politika_surumu",
        "source_id",
        "data_version",
    }
)
FORM_ALANLARI: Final = frozenset(
    {
        "form",
        "lemma",
        "karar",
        "neden",
        "freq",
        "freq_kaynak",
        "bilinen",
        "source_id",
        "data_version",
    }
)
KANIT_ALANLARI: Final = frozenset(
    {"politika", "politika_surumu", "yontem", "yontem_surumu", "kaynaklar", "qac", "karar", "neden"}
)
KAYNAK_KAYDI_ALANLARI: Final = frozenset({"source_id", "surum", "madde", "alan", "deger"})
ESLESME_DEGERLERI: Final = frozenset({YONTEM_KOK, YONTEM_ETIMON, "ikisi"})
ORNEK_SAYISI: Final = 5


def _g(deger: object, en_uzun: int = 60) -> str:
    return ascii(str(deger))[1:-1][:en_uzun]


def kanit_hatalari(kanit: object, karar: str, neden: str) -> list[str]:
    """`lemma.kanit` K-51 madde 9 biçimine uyuyor mu; hata kodlari (bos: gecerli).

    `onayli_otomatik` icin ek koşullar: kaynak listesi bos degil, `qac.letters_bw` dolu ve
    `qac.eslesme` bilinen bir yontem, `politika_surumu` guncel.
    """
    if not isinstance(kanit, dict):
        return ["kanit_nesne_degil"]
    hatalar: list[str] = []
    if set(kanit) != KANIT_ALANLARI:
        hatalar.append("kanit_alan_kumesi")
        return hatalar
    if kanit["politika"] != POLITIKA_ADI or kanit["yontem"] != YONTEM_ADI:
        hatalar.append("kanit_politika_adi")
    if kanit["yontem_surumu"] != YONTEM_SURUMU:
        hatalar.append("kanit_yontem_surumu")
    if kanit["karar"] != karar or kanit["neden"] != neden:
        hatalar.append("kanit_karar_tutmuyor")
    kaynaklar = kanit["kaynaklar"]
    if not isinstance(kaynaklar, list) or not all(
        isinstance(k, dict)
        and set(k) == KAYNAK_KAYDI_ALANLARI
        and all(isinstance(v, str) and v for v in k.values())
        and k["source_id"] == KAYNAK
        for k in kaynaklar
    ):
        hatalar.append("kanit_kaynak_kaydi")
        kaynaklar = []
    qac = kanit["qac"]
    if not isinstance(qac, dict) or not {"letters_bw", "letters", "eslesme"} <= set(qac):
        hatalar.append("kanit_qac")
        qac = {}
    if karar == ONAYLI:
        if kanit["politika_surumu"] != POLITIKA_SURUMU:
            hatalar.append("kanit_politika_surumu")
        if not kaynaklar:
            hatalar.append("kanit_kaynak_yok")
        if not isinstance(qac.get("letters_bw"), str) or not qac.get("letters_bw"):
            hatalar.append("kanit_qac_kok_yok")
        if qac.get("eslesme") not in ESLESME_DEGERLERI:
            hatalar.append("kanit_eslesme")
    return hatalar


@dataclass
class TrRootsGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    manifest_surum: str | None
    manifest_token: int | None
    dokum_ozetleri: Mapping[str, str]  # dosya adi -> manifestteki SHA-256
    kayitli_ozetler: Mapping[str, str]  # dosya adi -> SHA256SUMS'taki SHA-256
    lemma_satirlari: list[Satir]
    form_satirlari: list[Satir]
    qac_kok_satirlari: list[Satir]
    qac_lemma_satirlari: list[Satir]
    veri_surumleri: set[str] = field(default_factory=set)


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: TrRootsGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    if all(harf in " \t\n" for harf in g.kayit.atif_metni):
        bulgular.append(f"{KAYNAK}: atif_metni bos")
    if g.kayit.tur.value != "sozluk":
        bulgular.append(f"{KAYNAK}: tur sozluk degil")
    if g.manifest_surum != g.kayit.surum:
        bulgular.append(f"{KAYNAK}: manifest surumu kayit surumuyle ayni degil")
    for ad in sorted(g.kayitli_ozetler):
        if g.dokum_ozetleri.get(ad) != g.kayitli_ozetler[ad]:
            bulgular.append(f"{KAYNAK}: dokum ozeti SHA256SUMS ile tutmuyor ({_g(ad)})")
    if not g.kayitli_ozetler:
        bulgular.append(f"{KAYNAK}: SHA256SUMS dosyasinda dokum ozeti yok")
    return KapiSonucu(
        "G-KAY", tuple(bulgular), {"kaynak_kaydi": 1, "dokum": len(g.kayitli_ozetler)}
    )


# --- G-BUT -------------------------------------------------------------------------------


def _temiz_mi(metin: str) -> bool:
    return (
        metin != ""
        and unicodedata.is_normalized("NFC", metin)
        and not any(unicodedata.category(k) in ("Cc", "Cf", "Cs") for k in metin)
    )


def _alan_kumesi(satirlar: Sequence[Satir], beklenen: frozenset[str], ad: str) -> list[str]:
    return [
        f"{ad} satir {s.no}: alan kumesi beklenen degil"
        for s in satirlar
        if set(s.veri) != beklenen
    ][:ORNEK_SAYISI]


def g_but(g: TrRootsGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    bulgular += _alan_kumesi(g.lemma_satirlari, LEMMA_ALANLARI, "tr_lemmas")
    bulgular += _alan_kumesi(g.form_satirlari, FORM_ALANLARI, "tr_forms")
    if bulgular:
        return KapiSonucu("G-BUT", tuple(bulgular), {})
    lemma_sikligi: Counter[str] = Counter()
    toplam = 0
    for s in g.form_satirlari:
        form, freq = s.metin("form"), s.sayi("freq")
        if not _temiz_mi(form):
            bulgular.append(
                f"tr_forms satir {s.no}: form bos, NFC degil ya da kontrol karakteri var"
            )
        if s.metin("karar") not in KARARLAR:
            bulgular.append(f"tr_forms satir {s.no}: karar gecersiz")
        kaynak_sayilari = s.nesne("freq_kaynak")
        if freq < 1 or sum(int(str(v)) for v in kaynak_sayilari.values()) != freq:
            bulgular.append(
                f"tr_forms satir {s.no}: freq kaynak sikliklarinin toplamiyla ayni degil"
            )
        toplam += freq
        lemma = s.veri.get("lemma")
        if isinstance(lemma, str):
            lemma_sikligi[lemma] += freq
    if g.manifest_token is not None and toplam != g.manifest_token:
        bulgular.append(f"tr_forms: freq toplami ({toplam}) manifest token sayisiyla ayni degil")
    onayli = 0
    for s in g.lemma_satirlari:
        lemma, karar, neden = s.metin("lemma"), s.metin("karar"), s.metin("neden")
        if not _temiz_mi(lemma):
            bulgular.append(f"tr_lemmas satir {s.no}: lemma bos, NFC degil ya da kontrol karakteri")
        if karar not in KARARLAR:
            bulgular.append(f"tr_lemmas satir {s.no}: karar gecersiz")
        if s.sayi("freq") != lemma_sikligi.get(lemma, -1):
            bulgular.append(f"tr_lemmas satir {s.no}: freq bicimlerinin toplamiyla ayni degil")
        if s.metin("source_id") != KAYNAK or s.metin("politika_surumu") != POLITIKA_SURUMU:
            bulgular.append(f"tr_lemmas satir {s.no}: sabit alanlar (source_id, politika_surumu)")
        for hata in kanit_hatalari(s.veri.get("kanit"), karar, neden):
            bulgular.append(f"tr_lemmas satir {s.no}: {hata}")
        if karar == ONAYLI:
            onayli += 1
            if s.veri.get("root_letters_bw") is None:
                bulgular.append(f"tr_lemmas satir {s.no}: onayli lemmada kok yok")
    return KapiSonucu(
        "G-BUT",
        tuple(bulgular[:50]),
        {"form": len(g.form_satirlari), "lemma": len(g.lemma_satirlari), "onayli": onayli},
    )


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: TrRootsGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    kokler = {
        str(s.veri.get("letters_bw")): str(s.veri.get("letters")) for s in g.qac_kok_satirlari
    }
    lemma_kokleri = {
        str(s.veri.get("qac_ref")): s.veri.get("root_letters_bw") for s in g.qac_lemma_satirlari
    }
    gorulen: set[str] = set()
    lemma_kararlari: dict[str, str] = {}
    for s in g.lemma_satirlari:
        lemma, anahtar = s.metin("lemma"), s.metin("text_clean")
        if anahtar != normalize_tr(lemma, "dar"):
            bulgular.append(f"tr_lemmas satir {s.no}: text_clean dar anahtarla ayni degil")
        if anahtar in gorulen:
            bulgular.append(f"tr_lemmas satir {s.no}: yinelenen text_clean")
        gorulen.add(anahtar)
        lemma_kararlari[lemma] = s.metin("karar")
        bw = s.veri.get("root_letters_bw")
        if bw is not None and (bw not in kokler or kokler[str(bw)] != s.veri.get("root_letters")):
            bulgular.append(f"tr_lemmas satir {s.no}: kok QAC kok kumesinde degil")
        ref = s.veri.get("ar_lemma_qac_ref")
        if ref is not None:
            if str(ref) not in lemma_kokleri:
                bulgular.append(f"tr_lemmas satir {s.no}: Arapca lemma QAC lemma kumesinde degil")
            elif lemma_kokleri[str(ref)] != bw:
                bulgular.append(
                    f"tr_lemmas satir {s.no}: Arapca lemmanin koku lemma kokunden farkli"
                )
    onceki = ""
    for s in g.form_satirlari:
        form = s.metin("form")
        if form <= onceki and onceki:
            bulgular.append(f"tr_forms satir {s.no}: form tekil ve sirali degil")
        onceki = form
        form_lemma = s.veri.get("lemma")
        if isinstance(form_lemma, str):
            beklenen = lemma_kararlari.get(form_lemma)
            if beklenen is None and s.metin("karar") != KOK_YOK:
                bulgular.append(f"tr_forms satir {s.no}: lemma tabloda yok")
            elif beklenen is not None and beklenen != s.metin("karar"):
                bulgular.append(f"tr_forms satir {s.no}: karar lemma kararindan farkli")
        elif s.metin("karar") == ONAYLI:
            bulgular.append(f"tr_forms satir {s.no}: lemmasiz bicim onayli olamaz")
    for s in g.lemma_satirlari + g.form_satirlari:
        g.veri_surumleri.add(s.metin("data_version"))
    if len(g.veri_surumleri) > 1:
        bulgular.append("data_version tek degil")
    return KapiSonucu(
        "G-CAP",
        tuple(bulgular[:50]),
        {"lemma": len(g.lemma_satirlari), "form": len(g.form_satirlari)},
    )


KAPI_ISLEVLERI: Final[Mapping[str, Callable[[TrRootsGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- G-CAP uzantisi: veritabani (tr_root_index) --------------------------------------------

SPAN_SORGULARI: Final[Mapping[str, str]] = {
    "aralik_gecersiz": (
        "SELECT count(*) FROM icerik.tr_root_index t WHERE t.span_start < 0"
        " OR t.span_start >= t.span_end"
    ),
    "birim_yok": (
        "SELECT count(*) FROM icerik.tr_root_index t"
        " WHERE NOT EXISTS (SELECT 1 FROM icerik.unit u WHERE u.anchor = t.anchor)"
    ),
    "metin_disi": (
        "SELECT count(*) FROM icerik.tr_root_index t JOIN icerik.unit u ON u.anchor = t.anchor"
        " WHERE t.span_end > char_length(u.metin)"
    ),
    "ozet_eski": (
        "SELECT count(*) FROM icerik.tr_root_index t JOIN icerik.unit u ON u.anchor = t.anchor"
        " WHERE t.unit_hash <> left(u.content_hash, 16)"
    ),
    "onaysiz_lemma": (
        "SELECT count(*) FROM icerik.tr_root_index t JOIN icerik.lemma l ON l.id = t.tr_lemma_id"
        " WHERE l.status <> 'onayli' OR l.lang <> 'tr'"
    ),
}


def span_hatalari(conn: psycopg.Connection) -> dict[str, int]:
    """`tr_root_index` ihlalleri (hepsi 0 olmali); sorgular salt okunurdur."""
    sonuc: dict[str, int] = {}
    for ad, sorgu in SPAN_SORGULARI.items():
        satir = conn.execute(sorgu).fetchone()
        sonuc[ad] = int(satir[0]) if satir is not None else 0
    return sonuc


def span_bulgulari(hatalar: Mapping[str, int]) -> list[str]:
    return [f"tr_root_index: {ad} {n} (0 olmali)" for ad, n in hatalar.items() if n]


def db_g_cap(conn: psycopg.Connection) -> KapiSonucu:
    """G-CAP uzantisi: veritabanindaki tr_root_index (yari acik aralik, metin uzunlugu, ozet)."""
    hatalar = span_hatalari(conn)
    satir = conn.execute("SELECT count(*) FROM icerik.tr_root_index").fetchone()
    sayi = int(satir[0]) if satir is not None else 0
    return KapiSonucu("G-CAP", tuple(span_bulgulari(hatalar)), {"tr_root_index": sayi, **hatalar})
