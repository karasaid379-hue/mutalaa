"""QuranWBW Turkce kelime anlami QA kapilari (A17.6, K-50): G-KAY, G-BUT, G-CAP ve olcumler.

Kapi islevleri bellekteki `QuranwbwGirdisi` uzerinde calisir; ham dosya, staged satirlari ve QAC
satirlari `qa/run_quranwbw.py` tarafindan yuklenir. Bulgu listesi bos ise kapi `gecti`. Bulgular
ASCII ve kisadir; yalniz capa, sayi ve kisaltilmis ozet tasir, ANLAM METNI asla.

G-NOR bu kaynakta YOKTUR (arama metni uretilmez; gerekli kapilar `qa/__init__.py`
`YAPI_KAPILARI`).

* G-KAY: kaynak kaydi gecerli ve `atif_metni` dolu; kayit adresi ve surumu kilitle ayni; ingest
  manifestindeki surum kayit surumuyle ayni; ham dosya kilitteki boyut ve SHA-256 ile tutuyor.
* G-BUT: staged `meanings.jsonl` ham dosyadan yeniden uretilenle ayni (metin ham dosyadan yeniden
  uretilebilir); bos girdi 0, kontrol karakteri 0, metin kanonik; 114 sure, 6.236 ayet ve sure
  basina ayet sayisi `AYET_SAYILARI` ile ayni; ayet basina kelime sayisi QAC `words.jsonl` ile
  ayni; staged `glosses.jsonl` anlam girdileri, QAC kelimeleri ve dalgalardan yeniden uretilenle
  ayni (secilen dalgalarin her lemmasi aday).
* G-CAP: anlam girdilerinin capasi kanonik, tekil, `q:s:a:k`, `surah/ayah/word` alanlariyla ayni
  ve okuma sirasinda; kume QAC kelime capalariyla ayni; `provenance` ham dosya ozetini ve cikarici
  surumunu tasir; aday satirlarinin `qac_ref` degeri tekil, QAC lemma kumesinde ve dalgasi QAC
  `waves.jsonl` ile ayni; sabit alanlar (`source_id`, `data_version`) dogru.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from mutalaa_pipeline.anchor import parse, sort_key
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.enrich.glosses import Uretim, secilen_dalgalar, uret
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.quranwbw import (
    CIKARICI_SURUMU,
    KAYNAK,
    QuranwbwKilidi,
    cikar,
    veri_surumu,
)
from mutalaa_pipeline.qa.checks.qac import (
    _ayet_kelime_sayilari,
    _g,
    _kelime_konumu,
    _satir_farki,
    ayet_capalari,
)
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

SABIT_ALANLAR: Final = ("source_id", "data_version")
SURE_SAYISI: Final = len(AYET_SAYILARI)


@dataclass
class QuranwbwGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    kilit: QuranwbwKilidi
    ham: bytes
    ham_sha256: str
    ingest_surum: str | None
    wave: int
    anlam_satirlari: Sequence[Satir]  # staged meanings.jsonl
    gloss_satirlari: Sequence[Satir]  # staged glosses.jsonl
    qac_kelime_satirlari: Sequence[Satir]  # QAC words.jsonl
    qac_lemma_satirlari: Sequence[Satir]  # QAC lemmas.jsonl
    qac_dalga_satirlari: Sequence[Satir]  # QAC waves.jsonl

    @cached_property
    def surum(self) -> str:
        return self.kayit.surum or ""

    @cached_property
    def yeniden_cikarilan(self) -> list[dict[str, object]] | None:
        """Ham dosyadan yeniden cikarilan satirlar; cikarilamiyorsa None (G-BUT bulgu yazar)."""
        try:
            return cikar(self.ham, self.ham_sha256, self.surum)
        except GirdiHatasi:
            return None

    @cached_property
    def yeniden_uretilen(self) -> Uretim | None:
        try:
            return uret(
                [s.veri for s in self.qac_kelime_satirlari],
                [s.veri for s in self.anlam_satirlari],
                [s.veri for s in self.qac_dalga_satirlari],
                self.wave,
                self.surum,
            )
        except GirdiHatasi:
            return None


def _kontrol_karakteri(metin: str) -> bool:
    return any(ord(h) < 0x20 or 0x7F <= ord(h) <= 0x9F for h in metin)


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: QuranwbwGirdisi) -> KapiSonucu:
    """Kaynak kaydi ve ham dosya/kilit tutarliligi."""
    bulgular: list[str] = []
    kayit, kilit = g.kayit, g.kilit
    if all(harf in " \t\n" for harf in kayit.atif_metni):
        bulgular.append(f"{KAYNAK}: atif_metni bos")
    if kayit.kaynak_url != kilit.url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    if kayit.surum != kilit.surum:
        bulgular.append(f"{KAYNAK}: kayit surumu kilit surumuyle ayni degil")
    if g.ingest_surum is not None and g.ingest_surum != kayit.surum:
        bulgular.append(f"{KAYNAK}: ingest manifestindeki surum kayit surumuyle ayni degil")
    if g.ham_sha256 != kilit.sha256 or len(g.ham) != kilit.boyut:
        bulgular.append(f"{KAYNAK}: ham dosya kilitteki sha256 ve boyutla tutmuyor")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kaynak_kaydi": 1, "ham_bayt": len(g.ham)})


# --- G-BUT -------------------------------------------------------------------------------


def _farklar(g: QuranwbwGirdisi) -> list[str]:
    bulgular: list[str] = []
    cikarilan = g.yeniden_cikarilan
    if cikarilan is None:
        return [f"{KAYNAK}: ham dosya yeniden cikarilamadi (bicim bozuk)"]
    bulgular += _satir_farki("meanings", g.anlam_satirlari, cikarilan, "anchor")
    uretim = g.yeniden_uretilen
    if uretim is None:
        bulgular.append("glosses: QAC kelimeleri ve anlamlardan yeniden uretilemedi")
    else:
        bulgular += _satir_farki("glosses", g.gloss_satirlari, uretim.satirlar, "qac_ref")
    return bulgular


def g_but(g: QuranwbwGirdisi) -> KapiSonucu:
    """Yeniden uretilebilirlik, bos girdi, sayilar, QAC kelime sayilari ve aday kapsami."""
    bulgular = _farklar(g)
    metinler = [str(s.veri.get("text")) for s in g.anlam_satirlari]
    bos = sum(1 for m in metinler if all(h in " \t\n" for h in m))
    if bos:
        bulgular.append(f"bos anlam girdisi: {bos} (0 olmali)")
    kontrol = sum(1 for m in metinler if _kontrol_karakteri(m))
    if kontrol:
        bulgular.append(f"kontrol karakteri iceren anlam girdisi: {kontrol}")
    kanonik_degil = sum(1 for m in metinler if kanonik_metin(m) != m)
    if kanonik_degil:
        bulgular.append(f"kanonik (NFC, kirpilmis) olmayan anlam girdisi: {kanonik_degil}")
    ayetler = _ayet_kelime_sayilari(g.anlam_satirlari)
    qac_ayetler = _ayet_kelime_sayilari(g.qac_kelime_satirlari)
    if len(ayetler) != sum(AYET_SAYILARI):
        bulgular.append(f"ayet sayisi {len(ayetler)}; AYET_SAYILARI toplami {sum(AYET_SAYILARI)}")
    sure_ayet = Counter(sure for sure, _ in ayetler)
    sure_farki = [
        sure for sure in range(1, SURE_SAYISI + 1) if sure_ayet.get(sure) != AYET_SAYILARI[sure - 1]
    ]
    if sure_farki or set(sure_ayet) - set(range(1, SURE_SAYISI + 1)):
        bulgular.append(f"sure basina ayet sayisi tablodan farkli: {len(sure_farki)} sure")
    kelime_farki = ayet_capalari(
        (s, a)
        for (s, a) in ayetler.keys() | qac_ayetler.keys()
        if ayetler.get((s, a)) != qac_ayetler.get((s, a))
    )
    if kelime_farki:
        bulgular.append(
            f"ayet basina kelime sayisi QAC ile farkli: {len(kelime_farki)} ayet:"
            f" {', '.join(kelime_farki[:5])}"
        )
    sayilar = {
        "girdi": len(g.anlam_satirlari),
        "qac_kelime": len(g.qac_kelime_satirlari),
        "ayet": len(ayetler),
        "ayet_kelime_farki": len(kelime_farki),
        "bos_girdi": bos,
        "aday": len(g.gloss_satirlari),
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def _provenance_tamam(satir: Satir, ham_sha256: str) -> bool:
    kaynak = satir.veri.get("provenance")
    return (
        isinstance(kaynak, dict)
        and kaynak.get("ham_sha256") == ham_sha256
        and kaynak.get("cikarici") == CIKARICI_SURUMU
        and isinstance(kaynak.get("yol"), str)
    )


def g_cap(g: QuranwbwGirdisi) -> KapiSonucu:
    """Anlam capalari kanonik ve tekil; provenance ve sabit alanlar dogru; aday anahtarlari."""
    bulgular: list[str] = []
    gecersiz: list[str] = []
    uyumsuz: list[str] = []
    sirasiz: list[str] = []
    capalar: list[str] = []
    onceki = None
    yanlis_kaynak = 0
    for s in g.anlam_satirlari:
        capa = s.veri.get("anchor")
        konum = _kelime_konumu(capa)
        etiket = _g(capa)
        if konum is None:
            gecersiz.append(etiket)
            continue
        capalar.append(str(capa))
        if (s.veri.get("surah"), s.veri.get("ayah"), s.veri.get("word")) != konum:
            uyumsuz.append(etiket)
        anahtar = sort_key(parse(str(capa)))
        if onceki is not None and anahtar <= onceki:
            sirasiz.append(etiket)
        onceki = anahtar
        if not _provenance_tamam(s, g.ham_sha256):
            yanlis_kaynak += 1
    for ad, liste, neden in (
        ("gecersiz capa", gecersiz, "kanonik q:s:a:k degil"),
        ("capa-alan uyumsuzlugu", uyumsuz, "surah/ayah/word capadan farkli"),
        ("capa sirasi", sirasiz, "okuma sirasinda artmiyor ya da yinelendi"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} satir: {neden}: {', '.join(liste[:5])}")
    if len(set(capalar)) != len(capalar):
        bulgular.append(f"yinelenen kelime capasi: {len(capalar) - len(set(capalar))}")
    if yanlis_kaynak:
        bulgular.append(
            f"provenance eksik ya da ham dosya ozetiyle tutmuyor: {yanlis_kaynak} satir"
        )
    qac_capalar = {str(s.veri.get("anchor")) for s in g.qac_kelime_satirlari}
    if set(capalar) != qac_capalar:
        bulgular.append(
            f"kelime capasi kumesi QAC ile ayni degil ({len(set(capalar))}/{len(qac_capalar)})"
        )
    beklenen = {"source_id": KAYNAK, "data_version": veri_surumu(g.surum)}
    for ad, satirlar in (("meanings", g.anlam_satirlari), ("glosses", g.gloss_satirlari)):
        yanlis = sum(
            1 for s in satirlar if any(s.veri.get(a) != beklenen[a] for a in SABIT_ALANLAR)
        )
        if yanlis:
            bulgular.append(f"{ad}: {yanlis} satirda source_id ya da data_version yanlis")
    referanslar = [str(s.veri.get("qac_ref")) for s in g.gloss_satirlari]
    if len(set(referanslar)) != len(referanslar):
        bulgular.append(f"glosses: {len(referanslar) - len(set(referanslar))} yinelenen qac_ref")
    lemma_kumesi = {str(s.veri.get("qac_ref")) for s in g.qac_lemma_satirlari}
    bilinmeyen = [r for r in set(referanslar) if r not in lemma_kumesi]
    if bilinmeyen:
        bulgular.append(f"glosses: QAC lemma kumesinde olmayan {len(bilinmeyen)} qac_ref")
    dalga = {str(s.veri.get("qac_ref")): s.veri.get("dalga") for s in g.qac_dalga_satirlari}
    secilen = secilen_dalgalar(g.wave)
    dalga_farki = [
        r
        for r, s in zip(referanslar, g.gloss_satirlari, strict=True)
        if dalga.get(r) != s.veri.get("dalga") or s.veri.get("dalga") not in secilen
    ]
    if dalga_farki:
        bulgular.append(
            f"glosses: dalga QAC waves.jsonl ya da --wave ile farkli: {len(dalga_farki)}"
        )
    sayilar = {
        "kelime_capasi": len(capalar),
        "gecersiz": len(gecersiz),
        "tekil": len(set(capalar)),
        "aday_qac_ref": len(set(referanslar)),
    }
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[Mapping[str, Callable[[QuranwbwGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- olcumler ----------------------------------------------------------------------------


def olcumler(g: QuranwbwGirdisi) -> dict[str, object]:
    """Rapora giren olcumler (yalniz sayi ve dalga numarasi; metin yok)."""
    tutarsiz = sum(1 for s in g.gloss_satirlari if s.veri.get("tutarsiz_hazir_anlam") is True)
    dalga = Counter(int(str(s.veri["dalga"])) for s in g.gloss_satirlari)
    return {
        "wave": g.wave,
        "girdi": len(g.anlam_satirlari),
        "farkli_anlam": len({str(s.veri.get("text")) for s in g.anlam_satirlari}),
        "aday": len(g.gloss_satirlari),
        "tutarli": len(g.gloss_satirlari) - tutarsiz,
        "tutarsiz": tutarsiz,
        "dalga": {str(no): dalga[no] for no in sorted(dalga)},
    }
