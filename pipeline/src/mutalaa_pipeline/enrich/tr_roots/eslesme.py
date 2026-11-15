# ruff: noqa: RUF001, RUF002
"""Yapisal kanitin QAC kok ve lemma envanterine KESIN eslesmesi (K-51 madde 9 (c)).

Iki yol vardir:

* kok harfleri: kanittaki harf dizisi ile `root.letters`, hemze ve elif biciminin katlanmasindan
  sonra BIREBIR esit olmali. Katlama: hemze bicimleri `ء`, `آ` ve `ٱ` `ا`, elif maksura `ي`,
  te marbuta `ه` (kaikki imlai yazar, QAC Uthmani'dir: `كتاب` / `كتب`);
* etimon-lemma: etimonun `normalize_ar` bicimi, uzun unlu elifi (`ا`) atilmis anahtar olarak QAC
  `lemma.text_clean` ile (o da elifi atilmis) esit olmali (QAC hancer elifi yazar, etimon imlai
  elif yazar).

Sonuc bir ADAY KUMESIDIR; adayin tekligi politikanin isidir (`politika.py`). Bu modul veritabani
ve dosya bilmez: envanteri `QacEnvanteri.kur` staged `roots.jsonl` ve `lemmas.jsonl` satirlarindan
kurar.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.enrich.tr_roots.etimoloji import TUR_ETIMON, TUR_KOK, Kanit
from mutalaa_pipeline.normalize.arabic import normalize_ar

YONTEM_KOK: Final = "kok_harfleri"
YONTEM_ETIMON: Final = "etimon_lemma"
_ARAPCA_HARFLER: Final = frozenset(chr(k) for k in range(0x0621, 0x064B)) | {"ٱ"}
_KATLAMA: Final = str.maketrans(
    {
        "أ": "ء",  # elif ustunde hemze
        "إ": "ء",  # elif altinda hemze
        "ئ": "ء",  # ye ustunde hemze
        "ؤ": "ء",  # vav ustunde hemze
        "آ": "ا",  # elif med
        "ٱ": "ا",  # elif vasla
        "ى": "ي",  # elif maksura
        "ة": "ه",  # te marbuta
    }
)


def kok_katla(harfler: str) -> str:
    """Kok harf dizisinin katlanmis anahtari: yalniz Arapca harfler, bosluklu, katlanmis."""
    return " ".join(h.translate(_KATLAMA) for h in harfler if h in _ARAPCA_HARFLER)


def etimon_anahtari(metin: str) -> str:
    """Etimon ya da QAC `text_clean` anahtari: `normalize_ar`, uzun unlu elifi atilmis."""
    return normalize_ar(metin).replace("ا", "")


@dataclass(frozen=True, order=True)
class QacKok:
    letters_bw: str
    letters: str


@dataclass(frozen=True, order=True)
class QacLemma:
    qac_ref: str
    root_letters_bw: str | None


@dataclass
class QacEnvanteri:
    """Katlanmis kok anahtari -> kokler; elifsiz lemma anahtari -> lemmalar."""

    kokler: dict[str, list[QacKok]] = field(default_factory=dict)
    lemmalar: dict[str, list[QacLemma]] = field(default_factory=dict)
    kok_bw: dict[str, QacKok] = field(default_factory=dict)

    @classmethod
    def kur(
        cls,
        kok_satirlari: Iterable[Mapping[str, object]],
        lemma_satirlari: Iterable[Mapping[str, object]],
    ) -> "QacEnvanteri":
        env = cls()
        for s in kok_satirlari:
            bw, harf = s.get("letters_bw"), s.get("letters")
            if isinstance(bw, str) and isinstance(harf, str):
                kok = QacKok(bw, harf)
                env.kok_bw[bw] = kok
                env.kokler.setdefault(kok_katla(harf), []).append(kok)
        for s in lemma_satirlari:
            ref, temiz, kok_bw = s.get("qac_ref"), s.get("text_clean"), s.get("root_letters_bw")
            if isinstance(ref, str) and isinstance(temiz, str):
                lemma = QacLemma(ref, kok_bw if isinstance(kok_bw, str) else None)
                env.lemmalar.setdefault(etimon_anahtari(temiz), []).append(lemma)
        return env


@dataclass(frozen=True)
class Eslesme:
    """Kanit kumesinin QAC adaylari: kok -> hangi yollar; lemma -> koku."""

    kokler: Mapping[QacKok, frozenset[str]]  # yontem kumesi
    lemmalar: Mapping[QacLemma, QacKok]

    @property
    def kok_kumesi(self) -> frozenset[QacKok]:
        return frozenset(self.kokler)


def eslestir(envanter: QacEnvanteri, kanitlar: Iterable[Kanit]) -> Eslesme:
    """Kanitlarin QAC adaylari (kok harfleri ve etimon-lemma yollari birlestirilir)."""
    kokler: dict[QacKok, set[str]] = {}
    lemmalar: dict[QacLemma, QacKok] = {}
    for k in kanitlar:
        if k.tur == TUR_KOK:
            for kok in envanter.kokler.get(kok_katla(k.deger), []):
                kokler.setdefault(kok, set()).add(YONTEM_KOK)
        elif k.tur == TUR_ETIMON:
            for lemma in envanter.lemmalar.get(etimon_anahtari(k.deger), []):
                lemma_koku = envanter.kok_bw.get(lemma.root_letters_bw or "")
                if lemma_koku is None:
                    continue  # koksuz lemma kok adayi degildir
                kokler.setdefault(lemma_koku, set()).add(YONTEM_ETIMON)
                lemmalar[lemma] = lemma_koku
    return Eslesme({k: frozenset(v) for k, v in kokler.items()}, lemmalar)
