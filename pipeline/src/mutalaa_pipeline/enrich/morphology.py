"""QAC morfolojisi: saf islevler (A17.3, A17.5, K-50); dosya, veritabani ve zincir yok.

Girdi `ingest/qac.py` segmentleridir. Burada:

* segmentler kelimeye toplanir. Kelimenin GOVDESI `STEM` bayrakli segmenttir; birden cok `STEM`
  varsa (kaynakta 486 kelime: kaynasik edat/olumsuzluk/ilgi bilesikleri) ILK govde kelimenin
  govdesidir (kok her zaman ilk govdededir). Kok, lemma ve sozcuk turu govdeden gelir.
* kelime capalari (`q:{sure}:{ayet}:{kelime}`) YALNIZ `mutalaa_pipeline.anchor` ile bicimlenir ve
  dogrulanir; gecersiz konum `GirdiHatasi` (cikis 2).
* lemma ve kok envanteri: `occurrences` govde lemmasinin (kokun) kelime sayisi, `ayah_count`
  gectigi farkli ayet sayisi, `idf_q = ln(toplam_ayet / ayah_count)` (toplam ayet veriden).
* dalgalar (K-50 madde 7), `sira` ve DB'siz `kimlik_ata`.

Yazi: lemma ve kok metni extended Buckwalter'dan `enrich.buckwalter` ile Arapca yapilir; sonuc
kendi urettigimiz metindir ve `anchor.metin.kanonik_metin` ile BIR KEZ kanonik hale getirilir
(NFC yalniz burada); `text_clean` `normalize_ar` ile uretilir; `qac_ref` ozgun QAC dizgisini korur.
QAC LEM dizgisinin sonundaki ondalik rakam (homograf ayirt eden sira numarasi; ornegin ayni yazimli
iki lemmadan ikincisi) Buckwalter tablosunda YOKTUR ve cevrilmez: metin rakamsiz govdeden
uretilir, rakam `ayirt_no` alaninda tutulur, kimlik `qac_ref`'in tamamina baglidir.

Hata iletileri yalniz sira numarasi ve sayi tasir; icerik metni asla.
"""

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.anchor import AnchorError, AnchorRef, Q, parse
from mutalaa_pipeline.anchor import format as anchor_format
from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.enrich.buckwalter import BuckwalterHatasi, bw_arapca
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.qac import KAYNAK, Segment
from mutalaa_pipeline.normalize import normalize_ar

# Dalga 0 etiketleri: QAC etiket kumesi sayfasinin (`qac-belge/.../tagset.html`) gruplamasi.
# Zamirler: "Pronouns" grubu (Fig 1). Harf/edat sinifi: sayfanin ucuncu temel sozcuk turu
# "particle" (Fig 3: Prepositions, lam Prefixes, Conjunctions, Particles). Isimler (N, PN, ADJ,
# IMPN), zarflar (T, LOC), fiil (V) ve "Disconnected Letters" (INL; govdesinde LEM yoktur) bu
# kumeye girmez. DET sayfada yoktur (yalniz onek segmentinde gecer; govde etiketi olmaz).
ZAMIR_ETIKETLERI: Final = frozenset({"PRON", "DEM", "REL"})
HARF_ETIKETLERI: Final = frozenset(
    {
        # Prepositions, lam Prefixes, Conjunctions
        "P",
        "EMPH",
        "IMPV",
        "PRP",
        "CONJ",
        "SUB",
        # Particles
        "ACC",
        "AMD",
        "ANS",
        "AVR",
        "CAUS",
        "CERT",
        "CIRC",
        "COM",
        "COND",
        "EQ",
        "EXH",
        "EXL",
        "EXP",
        "FUT",
        "INC",
        "INT",
        "INTG",
        "NEG",
        "PREV",
        "PRO",
        "REM",
        "RES",
        "RET",
        "RSLT",
        "SUP",
        "SUR",
        "VOC",
    }
)
DALGA0_ETIKETLERI: Final = ZAMIR_ETIKETLERI | HARF_ETIKETLERI
# Sayfadaki oteki etiketler (dalga 0 disi): Nouns (N, PN), Derived nominals (ADJ, IMPN), Adverbs
# (T, LOC), Verbs (V), Disconnected Letters (INL). Sayfa toplam 44 etiket listeler.
DIGER_SAYFA_ETIKETLERI: Final = frozenset({"N", "PN", "ADJ", "IMPN", "T", "LOC", "V", "INL"})
SAYFA_ETIKETLERI: Final = DALGA0_ETIKETLERI | DIGER_SAYFA_ETIKETLERI

FATIHA_SURESI: Final = 1
CUZ_ISARETI: Final = "cuz"
SON_CUZ: Final = 30
DALGA_ESIKLERI: Final = ((1, 50), (2, 80), (3, 95))  # (dalga, kumulatif yuzde); kalan dalga 4
SON_DALGA: Final = 4
GOVDE_DISI_ONEKLER: Final = ("POS:", "LEM:", "ROOT:")
AYIRT_DESENI: Final = re.compile(r"(?P<govde>.+?)(?P<no>[0-9]+)")


# --- kelimeler ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Kelime:
    """Bir kelimenin segmentleri (dosya sirasinda) ve govdesi."""

    sure: int
    ayet: int
    kelime: int
    segmentler: tuple[Segment, ...]
    govde_indeksi: int  # `segmentler` icinde ilk `STEM` segmentinin indeksi

    @property
    def govde(self) -> Segment:
        return self.segmentler[self.govde_indeksi]

    @property
    def govde_sayisi(self) -> int:
        return sum(1 for s in self.segmentler if s.govde)


def kelimelere_topla(segmentler: Sequence[Segment]) -> list[Kelime]:
    """Ardisik ayni `(sure, ayet, kelime)` segmentlerini kelimeye toplar.

    Her kelime ayni konum anahtariyla tek bir ardisik blok olmali, segment numaralari 1'den
    kesintisiz artmali ve en az bir `STEM` segmenti bulunmali; aksi halde `GirdiHatasi`.
    """
    kelimeler: list[Kelime] = []
    gorulen: set[tuple[int, int, int]] = set()
    blok: list[Segment] = []

    def kapat() -> None:
        if not blok:
            return
        ilk = blok[0]
        anahtar = (ilk.sure, ilk.ayet, ilk.kelime)
        if anahtar in gorulen:
            raise GirdiHatasi(f"qac: kelime {len(gorulen) + 1}: segmentler ardisik degil")
        gorulen.add(anahtar)
        if [s.segment for s in blok] != list(range(1, len(blok) + 1)):
            raise GirdiHatasi(f"qac: kelime {len(gorulen)}: segment numaralari kesintisiz degil")
        indeksler = [i for i, s in enumerate(blok) if s.govde]
        if not indeksler:
            raise GirdiHatasi(f"qac: kelime {len(gorulen)}: govde (STEM) segmenti yok")
        kelimeler.append(Kelime(ilk.sure, ilk.ayet, ilk.kelime, tuple(blok), indeksler[0]))
        blok.clear()

    for segment in segmentler:
        if blok and (blok[0].sure, blok[0].ayet, blok[0].kelime) != (
            segment.sure,
            segment.ayet,
            segment.kelime,
        ):
            kapat()
        blok.append(segment)
    kapat()
    return kelimeler


def kelime_capasi(sure: int, ayet: int, kelime: int) -> str:
    """`q:{sure}:{ayet}:{kelime}`; bicimleme ve dogrulama yalniz `mutalaa_pipeline.anchor` ile.

    Gecersiz konum (sure/ayet araligi, uc haneyi asan numara) `GirdiHatasi`.
    """
    try:
        dizge = anchor_format(AnchorRef(Q(sure, ayet, kelime)))
        parse(dizge)
    except (AnchorError, ValueError):
        raise GirdiHatasi(f"qac: gecersiz kelime konumu (sure {sure}, ayet {ayet})") from None
    return dizge


def govde_ozellikleri(kelime: Kelime) -> list[str]:
    """Govdenin `STEM`, `POS:`, `LEM:` ve `ROOT:` disindaki ozellikleri (dosya sirasinda)."""
    return [
        o for o in kelime.govde.ozellikler if o != "STEM" and not o.startswith(GOVDE_DISI_ONEKLER)
    ]


def _segment_ozeti(segment: Segment) -> dict[str, object]:
    return {"tag": segment.tag, "ozellik": list(segment.ozellikler)}


def kelime_ozellikleri(kelime: Kelime) -> dict[str, object]:
    """`quran_word.features` icin sade nesne.

    `govde`: govdenin LEM, ROOT, POS ve STEM disindaki ozellikleri; `onek` ve `sonek`: govdeden
    once ve sonra gelen segmentler (etiket ve ozellikleri; ikinci govde `sonek`te yer alir).
    Bos listeler yazilmaz.
    """
    sonuc: dict[str, object] = {"govde": govde_ozellikleri(kelime)}
    onek = [_segment_ozeti(s) for s in kelime.segmentler[: kelime.govde_indeksi]]
    sonek = [_segment_ozeti(s) for s in kelime.segmentler[kelime.govde_indeksi + 1 :]]
    if onek:
        sonuc["onek"] = onek
    if sonek:
        sonuc["sonek"] = sonek
    return sonuc


def veri_surumu(surum: str) -> str:
    return f"{KAYNAK}@{surum}"


def kelime_satiri(kelime: Kelime, surum: str) -> dict[str, object]:
    """`words.jsonl` satiri (QAC kelimesi): kelime capasi, govde etiketi, lemma ve kok referansi."""
    govde = kelime.govde
    return {
        "anchor": kelime_capasi(kelime.sure, kelime.ayet, kelime.kelime),
        "surah": kelime.sure,
        "ayah": kelime.ayet,
        "word": kelime.kelime,
        "pos": govde.tag,
        "lemma_qac_ref": govde.lem,
        "root_letters_bw": govde.kok,
        "features": kelime_ozellikleri(kelime),
        "segment_sayisi": len(kelime.segmentler),
        "govde_sayisi": kelime.govde_sayisi,
        "source_id": KAYNAK,
        "data_version": veri_surumu(surum),
    }


# --- yazi --------------------------------------------------------------------------------


def lemma_ayir(qac_ref: str) -> tuple[str, int | None]:
    """LEM dizgisini `(govde, ayirt_no)` yapar: sondaki ondalik rakam dizisi ayirt eden sira
    numarasidir (Buckwalter tablosunda yoktur, cevrilmez); yoksa `ayirt_no` None."""
    eslesme = AYIRT_DESENI.fullmatch(qac_ref)
    if eslesme is None:
        return qac_ref, None
    return eslesme.group("govde"), int(eslesme.group("no"))


def lemma_metni(qac_ref: str, sira: int) -> tuple[str, str, int | None]:
    """`(text, text_clean, ayirt_no)`: lemma Arapca ve arama metni.

    `text` Buckwalter'dan cevrilir ve `kanonik_metin` bir kez uygulanir; `text_clean`
    `normalize_ar(text)`'tir. Tabloda olmayan karakter `GirdiHatasi` (iletide yalniz sira).
    """
    govde, ayirt = lemma_ayir(qac_ref)
    try:
        text = kanonik_metin(bw_arapca(govde))
    except BuckwalterHatasi:
        raise GirdiHatasi(f"lemma {sira}: Buckwalter tablosunda olmayan karakter") from None
    return text, normalize_ar(text), ayirt


def kok_harfleri(letters_bw: str, sira: int) -> str:
    """Kok harfleri: her Buckwalter harfi Arapcaya cevrilir, aralarina U+0020 konur (ornek girdi
    "bkt": uc harf, aralarinda iki bosluk); `kanonik_metin` bir kez uygulanir."""
    try:
        return kanonik_metin(" ".join(bw_arapca(h) for h in letters_bw))
    except BuckwalterHatasi:
        raise GirdiHatasi(f"kok {sira}: Buckwalter tablosunda olmayan karakter") from None


# --- envanter ----------------------------------------------------------------------------


@dataclass
class KokKaydi:
    letters_bw: str
    ilk_gecis: int
    occurrences: int = 0
    ayetler: set[tuple[int, int]] = field(default_factory=set)

    @property
    def ayah_count(self) -> int:
        return len(self.ayetler)


@dataclass
class LemmaKaydi:
    qac_ref: str
    ilk_gecis: int
    kok_bw: str | None
    occurrences: int = 0
    ayetler: set[tuple[int, int]] = field(default_factory=set)
    etiketler: Counter[str] = field(default_factory=Counter)
    fatiha: bool = False
    cuz30: bool = False

    @property
    def ayah_count(self) -> int:
        return len(self.ayetler)

    @property
    def baskin_etiket(self) -> str:
        """En sik govde etiketi; esitlikte etiket adi sirasi."""
        return min(self.etiketler.items(), key=lambda oge: (-oge[1], oge[0]))[0]


@dataclass
class Envanter:
    lemmalar: list[LemmaKaydi]  # ilk gecis sirasinda
    kokler: list[KokKaydi]  # ilk gecis sirasinda
    toplam_ayet: int
    kelime_sayisi: int
    lemmasiz_kelime: int  # govdesinde LEM olmayan kelime
    koksuz_kelime: int
    iki_govdeli_kelime: int


def envanter_hesapla(kelimeler: Sequence[Kelime], cuz_basi: tuple[int, int]) -> Envanter:
    """Kelimelerden lemma ve kok envanteri (govde lemmasi; kelime duzeyi sayim).

    `cuz_basi`: 30. cuzun baslangic ayeti `(sure, ayet)`; ondan sonraki her ayet 30. cuzdedir
    (30. cuz son cuzdur). Bir LEM dizgisi birden cok kokle gecerse `GirdiHatasi` (kimlik
    kurali lemma anahtarinin tek kokle gectigini varsayar).
    """
    lemmalar: dict[str, LemmaKaydi] = {}
    kokler: dict[str, KokKaydi] = {}
    ayetler: set[tuple[int, int]] = set()
    lemmasiz = koksuz = iki_govde = 0
    for k in kelimeler:
        ayet = (k.sure, k.ayet)
        ayetler.add(ayet)
        govde = k.govde
        if k.govde_sayisi > 1:
            iki_govde += 1
        kok = None
        if govde.kok is None:
            koksuz += 1
        else:
            kok = kokler.get(govde.kok)
            if kok is None:
                kok = kokler[govde.kok] = KokKaydi(govde.kok, len(kokler) + 1)
            kok.occurrences += 1
            kok.ayetler.add(ayet)
        if govde.lem is None:
            lemmasiz += 1
            continue
        lemma = lemmalar.get(govde.lem)
        if lemma is None:
            lemma = lemmalar[govde.lem] = LemmaKaydi(govde.lem, len(lemmalar) + 1, govde.kok)
        elif lemma.kok_bw != govde.kok:
            raise GirdiHatasi(f"lemma {lemma.ilk_gecis}: birden cok kokle geciyor")
        lemma.occurrences += 1
        lemma.ayetler.add(ayet)
        lemma.etiketler[govde.tag] += 1
        lemma.fatiha = lemma.fatiha or k.sure == FATIHA_SURESI
        lemma.cuz30 = lemma.cuz30 or ayet >= cuz_basi
    return Envanter(
        lemmalar=list(lemmalar.values()),
        kokler=list(kokler.values()),
        toplam_ayet=len(ayetler),
        kelime_sayisi=len(kelimeler),
        lemmasiz_kelime=lemmasiz,
        koksuz_kelime=koksuz,
        iki_govdeli_kelime=iki_govde,
    )


def idf_q(ayah_count: int, toplam_ayet: int) -> str:
    """`ln(toplam_ayet / ayah_count)` dokuz ondalikla (staged JSON ondalik sayi tasimaz)."""
    if ayah_count < 1 or toplam_ayet < ayah_count:
        raise GirdiHatasi("idf_q: ayah_count 1 ile toplam ayet arasinda olmali")
    return format(math.log(toplam_ayet / ayah_count), ".9f")


def lemma_satiri(lemma: LemmaKaydi, toplam_ayet: int, surum: str) -> dict[str, object]:
    text, text_clean, ayirt = lemma_metni(lemma.qac_ref, lemma.ilk_gecis)
    return {
        "qac_ref": lemma.qac_ref,
        "ilk_gecis": lemma.ilk_gecis,
        "text": text,
        "text_clean": text_clean,
        "ayirt_no": ayirt,
        "root_letters_bw": lemma.kok_bw,
        "occurrences": lemma.occurrences,
        "ayah_count": lemma.ayah_count,
        "idf_q": idf_q(lemma.ayah_count, toplam_ayet),
        "source_id": KAYNAK,
        "data_version": veri_surumu(surum),
    }


def kok_satiri(kok: KokKaydi, toplam_ayet: int, surum: str) -> dict[str, object]:
    return {
        "letters_bw": kok.letters_bw,
        "ilk_gecis": kok.ilk_gecis,
        "letters": kok_harfleri(kok.letters_bw, kok.ilk_gecis),
        "occurrences": kok.occurrences,
        "ayah_count": kok.ayah_count,
        "idf_q": idf_q(kok.ayah_count, toplam_ayet),
        "source_id": KAYNAK,
        "data_version": veri_surumu(surum),
    }


# --- cuz sinirlari ve dalgalar -----------------------------------------------------------


def cuz_baslangici(isaretler: Sequence[Mapping[str, object]], no: int = SON_CUZ) -> tuple[int, int]:
    """`markers.jsonl` satirlarindan `no`. cuzun baslangic ayeti `(sure, ayet)` (yoksa hata)."""
    for satir in isaretler:
        if satir.get("kind") == CUZ_ISARETI and satir.get("no") == no:
            capa = satir.get("anchor")
            if not isinstance(capa, str):
                break
            try:
                anchor = parse(capa).anchor
            except AnchorError:
                break
            if isinstance(anchor, Q) and anchor.ilk is None:
                return anchor.sure, anchor.ayet
            break
    raise GirdiHatasi(f"isaretlerde {no}. cuzun baslangic ayeti yok ya da gecersiz")


@dataclass(frozen=True)
class DalgaKaydi:
    qac_ref: str
    dalga: int
    sira: int
    etiket: str  # en sik govde etiketi
    fatiha: bool
    cuz30: bool
    zorla: bool  # siklik dalgasi 1'den buyuktu; Fatiha/30. cuz nedeniyle dalga 1'e alindi


def dalgalari_hesapla(
    lemmalar: Sequence[LemmaKaydi], kokler: Sequence[KokKaydi]
) -> list[DalgaKaydi]:
    """Dalga ve sira (K-50 madde 7); sonuc `(dalga, sira)` sirasindadir.

    Dalga 0: en sik govde etiketi `DALGA0_ETIKETLERI`'nde. Kalanlar sikliga gore (azalan, esitlikte
    ilk gecis) dizilir; yuzdeler dalga 0 disarida birikimlidir ve tam sayiyla hesaplanir: bir lemma,
    kendisinden ONCEKI birikim esigin altindaysa o dalgadadir (esige ulasmak icin gereken en az
    lemma sayisi). Dalga 1 = ilk %50; dalga 2 = %80'e, dalga 3 = %95'e kadar, dalga 4 = kalan.
    Fatiha (sure 1) ve 30. cuz lemmalari dalga 1'e alinir (dalga 0'dakiler 0'da kalir).
    `sira`: dalga icinde kokun toplam gecisine gore azalan (esitlikte kok ilk gecisi), koksuzler
    sonda; kok icinde lemma gecisine gore azalan (esitlikte lemma ilk gecisi); 1 tabanli. Kimlik
    sirasi yerine `ilk_gecis` kullanilir: bos veritabaninda `lemma.id` ve `root.id` ilk gecis
    sirasiyla verilir (`kimlik_ata`).
    """
    kok_tablosu = {k.letters_bw: k for k in kokler}
    dalga: dict[str, int] = {}
    zorla: set[str] = set()
    kalan = sorted(
        (lm for lm in lemmalar if lm.baskin_etiket not in DALGA0_ETIKETLERI),
        key=lambda lm: (-lm.occurrences, lm.ilk_gecis),
    )
    for lm in lemmalar:
        if lm.baskin_etiket in DALGA0_ETIKETLERI:
            dalga[lm.qac_ref] = 0
    toplam = sum(lm.occurrences for lm in kalan)
    birikim = 0
    for lm in kalan:
        no = SON_DALGA
        for aday, yuzde in DALGA_ESIKLERI:
            if birikim * 100 < yuzde * toplam:
                no = aday
                break
        if no > 1 and (lm.fatiha or lm.cuz30):
            no = 1
            zorla.add(lm.qac_ref)
        dalga[lm.qac_ref] = no
        birikim += lm.occurrences

    def sira_anahtari(lm: LemmaKaydi) -> tuple[bool, int, int, int, int]:
        kok = kok_tablosu.get(lm.kok_bw) if lm.kok_bw is not None else None
        if kok is None:
            return (True, 0, 0, -lm.occurrences, lm.ilk_gecis)
        return (False, -kok.occurrences, kok.ilk_gecis, -lm.occurrences, lm.ilk_gecis)

    sonuc: list[DalgaKaydi] = []
    for no in range(SON_DALGA + 1):
        grup = sorted((lm for lm in lemmalar if dalga[lm.qac_ref] == no), key=sira_anahtari)
        sonuc.extend(
            DalgaKaydi(
                qac_ref=lm.qac_ref,
                dalga=no,
                sira=sira,
                etiket=lm.baskin_etiket,
                fatiha=lm.fatiha,
                cuz30=lm.cuz30,
                zorla=lm.qac_ref in zorla,
            )
            for sira, lm in enumerate(grup, start=1)
        )
    return sonuc


def dalga_satiri(d: DalgaKaydi, surum: str) -> dict[str, object]:
    return {
        "qac_ref": d.qac_ref,
        "dalga": d.dalga,
        "sira": d.sira,
        "etiket": d.etiket,
        "fatiha": d.fatiha,
        "cuz30": d.cuz30,
        "zorla": d.zorla,
        "source_id": KAYNAK,
        "data_version": veri_surumu(surum),
    }


# --- tum satirlar ------------------------------------------------------------------------


@dataclass(frozen=True)
class Uretim:
    """Bir QAC dosyasindan uretilen butun staged satirlari (adim ve QA ayni islevi kullanir)."""

    envanter: Envanter
    dalgalar: list[DalgaKaydi]
    kelime_satirlari: list[dict[str, object]]
    lemma_satirlari: list[dict[str, object]]
    kok_satirlari: list[dict[str, object]]
    dalga_satirlari: list[dict[str, object]]


def uret(segmentler: Sequence[Segment], cuz_basi: tuple[int, int], surum: str) -> Uretim:
    """Segmentlerden `words`, `lemmas`, `roots` ve `waves` satirlari (saf islev)."""
    kelimeler = kelimelere_topla(segmentler)
    envanter = envanter_hesapla(kelimeler, cuz_basi)
    dalgalar = dalgalari_hesapla(envanter.lemmalar, envanter.kokler)
    if len(dalgalar) != len(envanter.lemmalar):
        raise GirdiHatasi("dalga satiri sayisi lemma sayisiyla ayni degil")
    return Uretim(
        envanter=envanter,
        dalgalar=dalgalar,
        kelime_satirlari=[kelime_satiri(k, surum) for k in kelimeler],
        lemma_satirlari=[lemma_satiri(lm, envanter.toplam_ayet, surum) for lm in envanter.lemmalar],
        kok_satirlari=[kok_satiri(k, envanter.toplam_ayet, surum) for k in envanter.kokler],
        dalga_satirlari=[dalga_satiri(d, surum) for d in dalgalar],
    )


# --- kimlik ------------------------------------------------------------------------------


def kimlik_ata(
    mevcut: Mapping[str, int], siralanmis_anahtarlar: Sequence[str], taban: int = 0
) -> dict[str, int]:
    """Kalici kimlik atamasi (DB'siz): var olan anahtarin kimligi korunur; yeni anahtara
    `max(id) + 1`'den baslayarak, verilen (ilk gecis) sirasiyla ardisik kimlik verilir.
    `taban`: tablodaki oteki satirlarin (ornegin Turkce lemmalar) en buyuk kimligi; yeni kimlik
    onu da asar.

    Ayni girdi ayni sonucu verir: bos mevcutta kimlikler 1'den ilk gecis sirasiyla, ikinci
    calistirmada (mevcut = onceki sonuc) hicbir kimlik degismez. Yinelenen anahtar `ValueError`.
    """
    if len(set(siralanmis_anahtarlar)) != len(siralanmis_anahtarlar):
        raise ValueError("yinelenen anahtar")
    siradaki = max(max(mevcut.values(), default=0), taban) + 1
    sonuc: dict[str, int] = {}
    for anahtar in siralanmis_anahtarlar:
        if anahtar in mevcut:
            sonuc[anahtar] = mevcut[anahtar]
        else:
            sonuc[anahtar] = siradaki
            siradaki += 1
    return sonuc
