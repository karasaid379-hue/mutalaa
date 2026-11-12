"""QAC morfoloji QA kapilari (A17.3, K-50): G-KAY, G-BUT, G-CAP ve olcumler.

Kapi islevleri bellekteki `QacGirdisi` uzerinde calisir; ham dosya, staged satirlari ve capraz
sayim kopyasi `qa/run_qac.py` tarafindan yuklenir. Bulgu listesi bos ise kapi `gecti`. Bulgular
ASCII ve kisadir; yalniz capa, sayi ve kisaltilmis ozet tasir, metin asla.

G-NOR bu kaynakta YOKTUR (arama metni uretilmez; gerekli kapilar `qa/__init__.py`
`YAPI_KAPILARI`).

* G-KAY: kaynak kaydi gecerli ve `atif_metni` dolu; `notice_text` dosyanin bildirim blogunun
  (CRLF -> LF, sondaki satir sonlari atilmis) baytlariyla, staged `notice.txt` ve kilitteki
  `bildirim_sha256` ile ayni; kayit surumu, kilit surumu ve bildirim basligindaki surum ayni;
  kayit adresi kilit adresiyle ayni; ham dosya kilitteki boyut ve SHA-256 ile tutuyor.
* G-BUT: staged `words`, `lemmas`, `roots`, `waves` satirlari ham dosyadan yeniden uretilenle
  ayni; ayet sayisi `AYET_SAYILARI` ile ve sure basina ayet sayisi tabloyla ayni; ayet basina
  kelime sayisi Tanzil `words.jsonl` kelime bolmesiyle ayni (fark = ayet sayisi); kelime
  numaralari her ayette 1'den bosluksuz; her kelime satirinin lemma ve koku lemma/kok
  envanteriyle tutarli (%100); lemma gecisleri kelime sayisiyla kapanir; Fatiha ve 30. cuz
  lemmalari dalga 0 ya da 1'de. Capraz sayim (`mustafa0x`) kapi degil olcumdur.
* G-CAP: her kelime capasi kanonik, tekil, `q:s:a:k` ve satirin `surah/ayah/word` alanlariyla ayni;
  capalar okuma sirasinda; `qac_ref`, `letters_bw` ve dalga anahtarlari tekil; dalga kumesi lemma
  kumesiyle ayni; sabit alanlar (`source_id`, `data_version`) dogru.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Q, parse, sort_key
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.enrich.morphology import (
    SAYFA_ETIKETLERI,
    Kelime,
    Uretim,
    kelimelere_topla,
    uret,
    veri_surumu,
)
from mutalaa_pipeline.ingest.qac import (
    KAYNAK,
    QacDosyasi,
    QacKilidi,
    bildirim_surumu,
)
from mutalaa_pipeline.lineage import kisa_ozet
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.qa.qac_capraz import Capraz, Karsilastirma, karsilastir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ORNEK_CAPA: Final = 5
SABIT_ALANLAR: Final = ("source_id", "data_version")


@dataclass
class QacGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    kilit: QacKilidi
    ham: bytes
    ham_sha256: str
    dosya: QacDosyasi  # ham dosyadan ayristirilmis
    bildirim_dosyasi: bytes | None  # staged ingest klasorundeki notice.txt
    ingest_surum: str | None
    cuz_basi: tuple[int, int]
    kelime_satirlari: Sequence[Satir]  # staged words.jsonl
    lemma_satirlari: Sequence[Satir]
    kok_satirlari: Sequence[Satir]
    dalga_satirlari: Sequence[Satir]
    tanzil_kelime_satirlari: Sequence[Satir]  # tanzil-uthmani words.jsonl
    depo_kok: Path
    capraz: Capraz | None = None

    @cached_property
    def surum(self) -> str:
        return self.kayit.surum or ""

    @cached_property
    def kelimeler(self) -> list[Kelime]:
        return kelimelere_topla(self.dosya.segmentler)

    @cached_property
    def uretim(self) -> Uretim:
        return uret(self.dosya.segmentler, self.cuz_basi, self.surum)

    @cached_property
    def lemma_metinleri(self) -> dict[str, str]:
        return {str(s["qac_ref"]): str(s["text"]) for s in self.uretim.lemma_satirlari}

    @cached_property
    def kok_metinleri(self) -> dict[str, str]:
        return {str(s["letters_bw"]): str(s["letters"]) for s in self.uretim.kok_satirlari}

    @cached_property
    def karsilastirma(self) -> Karsilastirma | None:
        if self.capraz is None:
            return None
        return karsilastir(self.kelimeler, self.lemma_metinleri, self.kok_metinleri, self.capraz)


# --- yardimcilar -------------------------------------------------------------------------


def _g(deger: object, en_uzun: int = 60) -> str:
    return ascii(str(deger))[1:-1][:en_uzun]


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(_g(c) for c in capalar[:ORNEK_CAPA])
    fazla = len(capalar) - ORNEK_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def ayet_capalari(ciftler: Iterable[tuple[int, int]]) -> list[str]:
    """`(sure, ayet)` ciftlerinin okuma sirasinda (sayisal: `q:10:1`, `q:2:1`den sonra).

    Bicimleme yalniz `mutalaa_pipeline.anchor` ile; gecersiz cift (aralik disi sure/ayet) capa
    uretemez ve `gecersiz:{sure}:{ayet}` etiketiyle sona yazilir.
    """
    gecerli: list[str] = []
    gecersiz: list[str] = []
    for sure, ayet in sorted(set(ciftler)):
        try:
            capa = anchor_format(AnchorRef(Q(sure, ayet)))
            parse(capa)  # aralik denetimi (bicimleyici sure/ayet araligini sinamaz)
            gecerli.append(capa)
        except (AnchorError, ValueError):
            gecersiz.append(f"gecersiz:{sure}:{ayet}")
    return gecerli + gecersiz


def _bos(metin: str) -> bool:
    return all(harf in " \t\n" for harf in metin)


def _kelime_konumu(capa: object) -> tuple[int, int, int] | None:
    """Kanonik `q:s:a:k` capasinin `(s, a, k)` degeri; degilse None."""
    if not isinstance(capa, str):
        return None
    try:
        ref = parse(capa)
        kanonik = anchor_format(ref) == capa
    except (AnchorError, ValueError):
        return None
    kok = ref.anchor
    if not kanonik or ref.span is not None or not isinstance(kok, Q):
        return None
    if kok.ilk is None or kok.son is not None:
        return None
    return kok.sure, kok.ayet, kok.ilk


def _satir_farki(
    ad: str, staged: Sequence[Satir], uretilen: Sequence[Mapping[str, object]], anahtar: str
) -> list[str]:
    """Staged satirlar ham dosyadan yeniden uretilenle ayni mi (sayi olarak)."""
    bulgular: list[str] = []
    beklenen = {str(r[anahtar]): r for r in uretilen}
    gorulen = {str(s.veri.get(anahtar)): s.veri for s in staged}
    if len(gorulen) != len(staged):
        bulgular.append(f"{ad}: {len(staged) - len(gorulen)} yinelenen anahtar")
    eksik = [k for k in beklenen if k not in gorulen]
    fazla = [k for k in gorulen if k not in beklenen]
    farkli = [k for k, v in gorulen.items() if k in beklenen and v != beklenen[k]]
    for neden, liste in (("eksik", eksik), ("fazla", fazla), ("farkli", farkli)):
        if liste:
            bulgular.append(
                f"{ad}: ham dosyadan yeniden uretilenle {neden}: {len(liste)} satir:"
                f" {_capalar(liste)}"
            )
    return bulgular


def _ayet_kelime_sayilari(satirlar: Sequence[Satir]) -> Counter[tuple[int, int]]:
    sayac: Counter[tuple[int, int]] = Counter()
    for s in satirlar:
        sure, ayet = s.veri.get("surah"), s.veri.get("ayah")
        if isinstance(sure, int) and isinstance(ayet, int):
            sayac[(sure, ayet)] += 1
    return sayac


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: QacGirdisi) -> KapiSonucu:
    """Kaynak kaydi, bildirim ve ham dosya/kilit tutarliligi."""
    bulgular: list[str] = []
    kayit, kilit = g.kayit, g.kilit
    sayilar = {"kaynak_kaydi": 1, "bildirim_bayt": len(g.dosya.bildirim_baytlari())}
    if _bos(kayit.atif_metni):
        bulgular.append(f"{KAYNAK}: atif_metni bos")
    beklenen = g.dosya.bildirim_baytlari()
    if kayit.notice_text is None:
        bulgular.append(f"{KAYNAK}: kayitta notice_text yok (dosyada bildirim blogu var)")
    else:
        yazilan = kayit.notice_text.encode("utf-8")
        if yazilan != beklenen:
            bulgular.append(
                f"{KAYNAK}: notice_text dosyadaki bildirim blogundan farkli"
                f" (bayt {len(yazilan)}/{len(beklenen)})"
            )
        ozet = lineage.sha256_bayt(yazilan)
        if ozet != kilit.bildirim_sha256:
            bulgular.append(
                f"{KAYNAK}: sha256(notice_text) {kisa_ozet(ozet)} kilitteki bildirim_sha256"
                f" {kisa_ozet(kilit.bildirim_sha256)} degil"
            )
    if g.bildirim_dosyasi is None:
        bulgular.append(f"{KAYNAK}: staged notice.txt yok")
    elif g.bildirim_dosyasi != beklenen:
        bulgular.append(f"{KAYNAK}: staged notice.txt dosyadaki bildirim blogundan farkli")
    baslik_surumu = bildirim_surumu(g.dosya.bildirim)
    if baslik_surumu is None:
        bulgular.append(f"{KAYNAK}: bildirim basligi (surum) cozulemedi")
    else:
        if kayit.surum != baslik_surumu:
            bulgular.append(
                f"{KAYNAK}: kayit surumu {_g(kayit.surum)} dosya basligindaki"
                f" {_g(baslik_surumu)} ile ayni degil"
            )
        if kilit.surum != baslik_surumu:
            bulgular.append(f"{KAYNAK}: kilit surumu dosya basligindaki surumle ayni degil")
    if g.ingest_surum is not None and g.ingest_surum != kayit.surum:
        bulgular.append(f"{KAYNAK}: ingest manifestindeki surum kayit surumuyle ayni degil")
    if kayit.kaynak_url != kilit.url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    if g.ham_sha256 != kilit.sha256 or len(g.ham) != kilit.boyut:
        bulgular.append(f"{KAYNAK}: ham dosya kilitteki sha256 ve boyutla tutmuyor")
    ozet_dosya = g.dosya.bildirim_ozeti()
    if (ozet_dosya.sha256, ozet_dosya.bayt, ozet_dosya.satir) != (
        kilit.bildirim_sha256,
        kilit.bildirim_bayt,
        kilit.bildirim_satir,
    ):
        bulgular.append(f"{KAYNAK}: bildirim blogu kilitteki ozetle tutmuyor")
    return KapiSonucu("G-KAY", tuple(bulgular), sayilar)


# --- G-BUT -------------------------------------------------------------------------------


def _sure_ayet_sayilari(sayac: Counter[tuple[int, int]]) -> dict[int, int]:
    sure_basina: Counter[int] = Counter(sure for sure, _ in sayac)
    return dict(sure_basina)


def _lemma_tutarsizligi(g: QacGirdisi) -> tuple[int, int]:
    """(tutarsiz kelime, lemma ya da kok envanterinde olmayan kelime): kelime satirlari ile
    envanter satirlarinin lemma/kok eslesmesi."""
    lemma_kok = {str(s.veri["qac_ref"]): s.veri.get("root_letters_bw") for s in g.lemma_satirlari}
    kokler = {str(s.veri["letters_bw"]) for s in g.kok_satirlari}
    tutarsiz = yok = 0
    for s in g.kelime_satirlari:
        lemma, kok = s.veri.get("lemma_qac_ref"), s.veri.get("root_letters_bw")
        if kok is not None and kok not in kokler:
            yok += 1
        if lemma is None:
            continue
        if lemma not in lemma_kok:
            yok += 1
        elif lemma_kok[str(lemma)] != kok:
            tutarsiz += 1
    return tutarsiz, yok


def g_but(g: QacGirdisi) -> KapiSonucu:
    """Yeniden uretilebilirlik, sayilar, Tanzil bolmesi, lemma tutarliligi ve dalgalar."""
    bulgular: list[str] = []
    uretim = g.uretim
    bulgular += _satir_farki("words", g.kelime_satirlari, uretim.kelime_satirlari, "anchor")
    bulgular += _satir_farki("lemmas", g.lemma_satirlari, uretim.lemma_satirlari, "qac_ref")
    bulgular += _satir_farki("roots", g.kok_satirlari, uretim.kok_satirlari, "letters_bw")
    bulgular += _satir_farki("waves", g.dalga_satirlari, uretim.dalga_satirlari, "qac_ref")

    qac_ayetler = _ayet_kelime_sayilari(g.kelime_satirlari)
    tanzil_ayetler = _ayet_kelime_sayilari(g.tanzil_kelime_satirlari)
    sure_sayisi = len(AYET_SAYILARI)
    if len(qac_ayetler) != sum(AYET_SAYILARI):
        bulgular.append(
            f"ayet sayisi {len(qac_ayetler)}; AYET_SAYILARI toplami {sum(AYET_SAYILARI)}"
        )
    sure_ayet = _sure_ayet_sayilari(qac_ayetler)
    sure_farki = [
        sure for sure in range(1, sure_sayisi + 1) if sure_ayet.get(sure) != AYET_SAYILARI[sure - 1]
    ]
    if sure_farki or set(sure_ayet) - set(range(1, sure_sayisi + 1)):
        bulgular.append(f"sure basina ayet sayisi tablodan farkli: {len(sure_farki)} sure")
    kelime_farki = ayet_capalari(
        (s, a)
        for (s, a) in qac_ayetler.keys() | tanzil_ayetler.keys()
        if qac_ayetler.get((s, a)) != tanzil_ayetler.get((s, a))
    )
    if kelime_farki:
        bulgular.append(
            f"ayet basina kelime sayisi Tanzil bolmesinden farkli: {len(kelime_farki)} ayet:"
            f" {_capalar(kelime_farki)}"
        )
    bosluk = _bosluklu_ayetler(g)
    if bosluk:
        bulgular.append(
            f"kelime numarasi 1'den bosluksuz degil: {len(bosluk)} ayet: {_capalar(bosluk)}"
        )

    tutarsiz, yok = _lemma_tutarsizligi(g)
    if tutarsiz or yok:
        bulgular.append(
            f"lemma/kok tutarsiz: {tutarsiz} kelime lemma-kok eslesmesi farkli,"
            f" {yok} kelime envanterde yok (LEM tutarliligi %100 olmali)"
        )
    lemmali = sum(1 for s in g.kelime_satirlari if s.veri.get("lemma_qac_ref") is not None)
    toplam_gecis = sum(int(str(s.veri["occurrences"])) for s in g.lemma_satirlari)
    if lemmali != toplam_gecis:
        bulgular.append(
            f"lemma gecisleri toplami {toplam_gecis} lemmali kelime sayisi {lemmali} degil"
        )
    bulgular += _dalga_denetimi(g)
    sayilar = {
        "kelime": len(g.kelime_satirlari),
        "ayet": len(qac_ayetler),
        "tanzil_kelime": len(g.tanzil_kelime_satirlari),
        "ayet_kelime_farki": len(kelime_farki),
        "lemma": len(g.lemma_satirlari),
        "kok": len(g.kok_satirlari),
        "lemma_tutarsiz": tutarsiz + yok,
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


def _bosluklu_ayetler(g: QacGirdisi) -> list[str]:
    numaralar: dict[tuple[int, int], list[int]] = {}
    for s in g.kelime_satirlari:
        sure, ayet, kelime = s.veri.get("surah"), s.veri.get("ayah"), s.veri.get("word")
        if isinstance(sure, int) and isinstance(ayet, int) and isinstance(kelime, int):
            numaralar.setdefault((sure, ayet), []).append(kelime)
    return ayet_capalari(
        (s, a) for (s, a), n in numaralar.items() if sorted(n) != list(range(1, len(n) + 1))
    )


def _dalga_denetimi(g: QacGirdisi) -> list[str]:
    """Fatiha ve 30. cuz lemmalari dalga 0 ya da 1'de; sira her dalgada 1'den kesintisiz."""
    bulgular: list[str] = []
    dalga = {str(s.veri["qac_ref"]): s.veri.get("dalga") for s in g.dalga_satirlari}
    ozel: set[str] = set()
    for s in g.kelime_satirlari:
        lemma, sure, ayet = s.veri.get("lemma_qac_ref"), s.veri.get("surah"), s.veri.get("ayah")
        if not isinstance(lemma, str) or not isinstance(sure, int) or not isinstance(ayet, int):
            continue
        if sure == 1 or (sure, ayet) >= g.cuz_basi:
            ozel.add(lemma)
    yuksek = sorted(k for k in ozel if not isinstance(dalga.get(k), int) or int(str(dalga[k])) > 1)
    if yuksek:
        bulgular.append(f"Fatiha/30. cuz lemmasi dalga 1'den buyuk: {len(yuksek)} lemma")
    sira_grup: dict[object, list[int]] = {}
    for s in g.dalga_satirlari:
        sira = s.veri.get("sira")
        if isinstance(sira, int):
            sira_grup.setdefault(s.veri.get("dalga"), []).append(sira)
    bozuk = [d for d, n in sira_grup.items() if sorted(n) != list(range(1, len(n) + 1))]
    if bozuk:
        bulgular.append(f"dalga sirasi 1'den kesintisiz degil: {len(bozuk)} dalga")
    return bulgular


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: QacGirdisi) -> KapiSonucu:
    """Kelime capalari kanonik ve tekil; anahtarlar tekil; sabit alanlar dogru."""
    bulgular: list[str] = []
    gecersiz: list[str] = []
    uyumsuz: list[str] = []
    sirasiz: list[str] = []
    capalar: list[str] = []
    onceki = None
    for s in g.kelime_satirlari:
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
    for ad, liste, neden in (
        ("gecersiz capa", gecersiz, "kanonik q:s:a:k degil"),
        ("capa-alan uyumsuzlugu", uyumsuz, "surah/ayah/word capadan farkli"),
        ("capa sirasi", sirasiz, "okuma sirasinda artmiyor ya da yinelendi"),
    ):
        if liste:
            bulgular.append(f"{ad}: {len(liste)} satir: {neden}: {_capalar(liste)}")
    if len(set(capalar)) != len(capalar):
        bulgular.append(f"yinelenen kelime capasi: {len(capalar) - len(set(capalar))}")
    for ad, satirlar, alan in (
        ("lemmas", g.lemma_satirlari, "qac_ref"),
        ("roots", g.kok_satirlari, "letters_bw"),
        ("waves", g.dalga_satirlari, "qac_ref"),
    ):
        anahtarlar = [str(s.veri.get(alan)) for s in satirlar]
        if len(set(anahtarlar)) != len(anahtarlar):
            bulgular.append(f"{ad}: {len(anahtarlar) - len(set(anahtarlar))} yinelenen {alan}")
    lemma_kumesi = {str(s.veri.get("qac_ref")) for s in g.lemma_satirlari}
    dalga_kumesi = {str(s.veri.get("qac_ref")) for s in g.dalga_satirlari}
    if lemma_kumesi != dalga_kumesi:
        bulgular.append(
            f"dalga kumesi lemma kumesiyle ayni degil ({len(dalga_kumesi)}/{len(lemma_kumesi)})"
        )
    beklenen = {"source_id": KAYNAK, "data_version": veri_surumu(g.surum)}
    for ad, satirlar in (
        ("words", g.kelime_satirlari),
        ("lemmas", g.lemma_satirlari),
        ("roots", g.kok_satirlari),
        ("waves", g.dalga_satirlari),
    ):
        yanlis = sum(
            1 for s in satirlar if any(s.veri.get(a) != beklenen[a] for a in SABIT_ALANLAR)
        )
        if yanlis:
            bulgular.append(f"{ad}: {yanlis} satirda source_id ya da data_version yanlis")
    sayilar = {"kelime_capasi": len(capalar), "gecersiz": len(gecersiz), "tekil": len(set(capalar))}
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


KAPI_ISLEVLERI: Final[Mapping[str, Callable[[QacGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
}


# --- olcumler ----------------------------------------------------------------------------


def olcumler(g: QacGirdisi) -> dict[str, object]:
    """Rapora giren olcumler (yalniz sayi, etiket adi ve kimlik; metin yok)."""
    segmentler = g.dosya.segmentler
    dosya_etiketleri = {s.tag for s in segmentler}
    dalga_sayac = Counter(int(str(s.veri["dalga"])) for s in g.dalga_satirlari)
    envanter = g.uretim.envanter
    sonuc: dict[str, object] = {
        "segment": len(segmentler),
        "kelime": envanter.kelime_sayisi,
        "ayet": envanter.toplam_ayet,
        "lemma": len(envanter.lemmalar),
        "kok": len(envanter.kokler),
        "etiket_dosyada": len(dosya_etiketleri),
        "etiket_sayfada": len(SAYFA_ETIKETLERI),
        "etiket_sayfada_olmayan": sorted(dosya_etiketleri - SAYFA_ETIKETLERI),
        "etiket_dosyada_olmayan": sorted(SAYFA_ETIKETLERI - dosya_etiketleri),
        "lemmasiz_kelime": envanter.lemmasiz_kelime,
        "koksuz_kelime": envanter.koksuz_kelime,
        "iki_govdeli_kelime": envanter.iki_govdeli_kelime,
        "ayirt_rakamli_lemma": sum(1 for lm in envanter.lemmalar if lm.qac_ref[-1:].isdigit()),
        "dalga": {str(no): dalga_sayac.get(no, 0) for no in range(5)},
    }
    capraz = g.capraz
    if capraz is None:
        sonuc["capraz"] = {"durum": "atlandi"}
    else:
        kars = g.karsilastirma
        assert kars is not None
        sonuc["capraz"] = {
            "durum": "yapildi",
            "kopya_satir": capraz.satir_sayisi,
            "kopya_lem": capraz.lem_sayisi,
            "kopya_root": capraz.root_sayisi,
            "qac_lem": len({s.lem for s in segmentler if s.lem is not None}),
            "qac_root": len({s.kok for s in segmentler if s.kok is not None}),
            **kars.sayilar(),
            "ornek_capalar": list(kars.ornek_capalar),
        }
    return sonuc
