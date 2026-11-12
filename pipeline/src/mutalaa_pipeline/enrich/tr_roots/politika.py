# ruff: noqa: RUF001
"""Otomatik onay politikasi (K-51 madde 9 (a)-(e); Kok ve lemma §5 adim 7): SURUMLU.

`POLITIKA_SURUMU` kosullarin anlami degisince artar; kanit nesnesi onu tasir ve her yukleme eski
surumle uretilmis otomatik onayi yeniden degerlendirebilir.

Karar uc siniftan biridir:

* `onayli_otomatik`: (a) lemmatizasyon tek lemmaya iner ve soz kapali siniftan (zamir, baglac,
  edat, yardimci fiil) degildir; (b) yapisal sozluk kaniti vardir (kaikki `root` sablonu, kaynak
  dili `ar` olan `bor`/`der`/`inh` sablonu, `ety`/`etymon` agacinda `ar:` etimonu; Turkce ->
  Osmanlica -> Arapca zinciri dahil; serbest metindeki "Arabic" kanit degildir); (c) QAC eslesmesi
  kesin ve TEKTIR (tek kok adayi); (d) kaynaklar celismez: zeyrek turu kaikki maddesinin turuyle
  eslesir ve ayni lemma ve turdeki BUTUN kaikki maddeleri (Turkce ve Osmanlica) ayni koke gider;
  (e) dil modeli yoktur;
* `aday`: kanit var ama bir koruma tutmadi (cok adayli QAC, Turkce ile Osmanlicanin farkli koku,
  tur uyusmazligi, homograf maddelerin celismesi, belirsiz lemma) ya da kanit yalniz serbest
  metindir. Tek QAC kok adayi varsa `kok` onerisi olarak tasinir (editor kuyrugu icin);
* `kok_yok`: guvenilir kanit yok (bilinmeyen sozcuk, kapali sinif, madde ya da kanit yok, kanit var
  ama QAC kokune eslesmiyor). Bu sozcuge kok atanmaz ve lemma satiri acilmaz.

Otomatik eslemede `etymological_only` her zaman false'tur (anlam kaymasi otomatik taninmaz).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.enrich.tr_roots.eslesme import (
    YONTEM_ETIMON,
    YONTEM_KOK,
    Eslesme,
    QacEnvanteri,
    QacKok,
    QacLemma,
    eslestir,
)
from mutalaa_pipeline.enrich.tr_roots.etimoloji import KaikkiIndeksi, Madde
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Analiz

POLITIKA_ADI: Final = "tr-kok-otomatik-onay"
POLITIKA_SURUMU: Final = "1"
YONTEM_ADI: Final = "kaikki-yapisal-etimoloji+qac-eslesme"
YONTEM_SURUMU: Final = "1"
KAYNAK_ID: Final = "kaikki-tr"

ONAYLI: Final = "onayli_otomatik"
ADAY: Final = "aday"
KOK_YOK: Final = "kok_yok"
KARARLAR: Final = (ONAYLI, ADAY, KOK_YOK)

# nedenler
KOSULLAR_SAGLANDI: Final = "kosullar_saglandi"
BILINMEYEN_SOZCUK: Final = "bilinmeyen_sozcuk"
KAPALI_SINIF: Final = "kapali_sinif"
BELIRSIZ_LEMMA: Final = "belirsiz_lemma"
MADDE_YOK: Final = "madde_yok"
KANIT_YOK: Final = "kanit_yok"
YALNIZ_SERBEST_METIN: Final = "yalniz_serbest_metin"
QAC_ESLESMEDI: Final = "qac_eslesmedi"
COK_ADAYLI_QAC: Final = "cok_adayli_qac"
TR_OTA_KOK_CAKISMASI: Final = "tr_ota_kok_cakismasi"
KOK_CAKISMASI: Final = "kok_cakismasi"
POS_UYUSMAZLIGI: Final = "pos_uyusmazligi"
HOMOGRAF_CELISKISI: Final = "homograf_madde_celisiyor"

# zeyrek (Zemberek) lemma turu -> kaikki `pos` kumesi
POS_ESLEME: Final[Mapping[str, frozenset[str]]] = {
    "Noun": frozenset({"noun", "name"}),
    "Adj": frozenset({"adj"}),
    "Verb": frozenset({"verb"}),
    "Adv": frozenset({"adv"}),
    "Interj": frozenset({"intj"}),
    "Num": frozenset({"num"}),
}
KAPALI_POS: Final = frozenset({"Pron", "Conj", "Postp", "Det", "Ques", "Dup", "Punc", "Abbrv"})
# Kisa kapali liste: yardimci fiiller ve ek-fiil/edat benzeri islevsel sozcukler (lower_turkish).
KAPALI_LEMMALAR: Final = frozenset(
    {
        "olmak",
        "etmek",
        "edilmek",
        "eylemek",
        "kılmak",
        "bulunmak",
        "imek",
        "değil",
        "var",
        "yok",
        "ile",
        "ki",
        "de",
        "da",
        "mi",
        "mı",
        "mu",
        "mü",
    }
)
EN_COK_KAYNAK: Final = 16


@dataclass(frozen=True)
class Karar:
    """Bir lemmanin kok eslemesi karari ve denetlenebilir kaniti."""

    karar: str
    neden: str
    kok: QacKok | None = None  # tek kok adayi (onay ya da aday onerisi)
    ar_lemma: QacLemma | None = None  # etimonla tek QAC lemmasi eslesiyorsa
    yontem: str = "yok"  # kok_harfleri | etimon_lemma | ikisi | yok
    adaylar: tuple[QacKok, ...] = ()
    kaynaklar: tuple[Mapping[str, str], ...] = ()
    kaikki_surum: str = ""

    def kanit(self) -> dict[str, object]:
        """K-51 madde 9 kanit nesnesi (`root_id` ve `ar_lemma_id` yuklemede eklenir)."""
        qac: dict[str, object] = {
            "letters_bw": self.kok.letters_bw if self.kok else None,
            "letters": self.kok.letters if self.kok else None,
            "eslesme": self.yontem,
            "ar_lemma_qac_ref": self.ar_lemma.qac_ref if self.ar_lemma else None,
        }
        if len(self.adaylar) > 1:
            qac["adaylar"] = [
                {"letters_bw": k.letters_bw, "letters": k.letters} for k in self.adaylar
            ]
        return {
            "politika": POLITIKA_ADI,
            "politika_surumu": POLITIKA_SURUMU,
            "yontem": YONTEM_ADI,
            "yontem_surumu": YONTEM_SURUMU,
            "kaynaklar": [dict(k) for k in self.kaynaklar],
            "qac": qac,
            "karar": self.karar,
            "neden": self.neden,
        }


@dataclass(frozen=True)
class YuzeyKarari:
    """Bir yuzey bicimin karari: tek lemmaya iniyorsa `lemma` ve lemma karari dolu."""

    karar: str
    neden: str
    lemma: str | None = None
    lemma_karari: Karar | None = None


def kapali_mi(lemma: str, poslar: frozenset[str]) -> bool:
    """Kapali sinif: zamir, baglac, edat, belirtec ve soru ekleri ile kisa kapali liste."""
    return lemma in KAPALI_LEMMALAR or bool(poslar & KAPALI_POS)


@dataclass(frozen=True)
class _MaddeSonucu:
    madde: Madde
    osmanlica: tuple[Madde, ...]
    kendi: Eslesme
    ota: Eslesme

    @property
    def kokler(self) -> frozenset[QacKok]:
        return self.kendi.kok_kumesi | self.ota.kok_kumesi

    @property
    def yapisal(self) -> bool:
        return self.madde.yapisal or any(o.yapisal for o in self.osmanlica)

    @property
    def zayif(self) -> bool:
        return self.madde.zayif or any(o.zayif for o in self.osmanlica)


def _madde_sonucu(madde: Madde, indeks: KaikkiIndeksi, env: QacEnvanteri) -> _MaddeSonucu:
    ota: dict[Madde, None] = {}
    for bicim in madde.osmanlica:
        for o in indeks.osmanlica_maddeleri(bicim, madde.pos):
            ota[o] = None
    return _MaddeSonucu(
        madde,
        tuple(ota),
        eslestir(env, madde.kanitlar),
        eslestir(env, [k for o in ota for k in o.kanitlar]),
    )


def _kaynaklar(sonuclar: Sequence[_MaddeSonucu], surum: str) -> tuple[Mapping[str, str], ...]:
    kayitlar: dict[tuple[str, str, str], Mapping[str, str]] = {}
    for s in sonuclar:
        for m in (s.madde, *s.osmanlica):
            for k in m.kanitlar:
                alan = f"{m.dil}:{m.pos}:{k.alan}"
                kayitlar[(m.sozcuk, alan, k.deger)] = {
                    "source_id": KAYNAK_ID,
                    "surum": surum,
                    "madde": m.sozcuk,
                    "alan": alan,
                    "deger": k.deger,
                }
    return tuple(kayitlar[a] for a in sorted(kayitlar))[:EN_COK_KAYNAK]


def _yontem(kok: QacKok, sonuclar: Sequence[_MaddeSonucu]) -> str:
    yollar: set[str] = set()
    for s in sonuclar:
        yollar |= s.kendi.kokler.get(kok, frozenset()) | s.ota.kokler.get(kok, frozenset())
    if {YONTEM_KOK, YONTEM_ETIMON} <= yollar:
        return "ikisi"
    return next(iter(yollar), "yok")


def _ar_lemma(kok: QacKok, sonuclar: Sequence[_MaddeSonucu]) -> QacLemma | None:
    lemmalar: set[QacLemma] = set()
    for s in sonuclar:
        for esl in (s.kendi, s.ota):
            lemmalar |= {lm for lm, k in esl.lemmalar.items() if k == kok}
    return next(iter(lemmalar)) if len(lemmalar) == 1 else None


def lemma_karari(
    lemma: str,
    poslar: frozenset[str],
    indeks: KaikkiIndeksi,
    env: QacEnvanteri,
) -> Karar:
    """Bir lemmanin (ve zeyrek lemma turlerinin) kok eslemesi karari.

    Kapali sinif ve `lemmatizasyon tek lemmaya iner` kosullari yuzey duzeyinde (`yuzey_karari`)
    denetlenir; burada kaikki kaniti, QAC eslesmesi ve kaynaklarin celismemesi degerlendirilir.
    """
    surum = indeks.surum

    def sonuc(
        karar: str,
        neden: str,
        *,
        kok: QacKok | None = None,
        ar_lemma: QacLemma | None = None,
        yontem: str = "yok",
        adaylar: tuple[QacKok, ...] = (),
        kaynaklar: tuple[Mapping[str, str], ...] = (),
    ) -> Karar:
        return Karar(karar, neden, kok, ar_lemma, yontem, adaylar, kaynaklar, surum)

    maddeler = indeks.tr_maddeleri(lemma)
    if not maddeler:
        return sonuc(KOK_YOK, MADDE_YOK)
    kaikki_poslar: frozenset[str] = frozenset().union(
        *(POS_ESLEME.get(p, frozenset()) for p in poslar)
    )
    eslesen = [m for m in maddeler if m.pos in kaikki_poslar]
    tur_uyusmuyor = not eslesen or any(
        not (POS_ESLEME.get(p, frozenset()) & {m.pos for m in maddeler}) for p in poslar
    )
    secilen = eslesen or maddeler
    sonuclar = [_madde_sonucu(m, indeks, env) for m in secilen]
    kaynaklar = _kaynaklar(sonuclar, surum)

    if not any(s.yapisal for s in sonuclar):
        if any(s.zayif for s in sonuclar):
            return sonuc(ADAY, YALNIZ_SERBEST_METIN)
        return sonuc(KOK_YOK, KANIT_YOK)

    birlesik = frozenset().union(*(s.kokler for s in sonuclar))
    if not birlesik:
        return sonuc(KOK_YOK, QAC_ESLESMEDI, kaynaklar=kaynaklar)
    if len(birlesik) > 1:
        adaylar = tuple(sorted(birlesik))
        cakisma = any(
            s.kendi.kok_kumesi and s.ota.kok_kumesi and not (s.kendi.kok_kumesi & s.ota.kok_kumesi)
            for s in sonuclar
        )
        tek_madde_cok = any(len(s.kokler) > 1 for s in sonuclar)
        if cakisma:
            neden = TR_OTA_KOK_CAKISMASI
        elif tek_madde_cok:
            neden = COK_ADAYLI_QAC
        else:
            neden = KOK_CAKISMASI
        return sonuc(ADAY, neden, adaylar=adaylar, kaynaklar=kaynaklar)

    (kok,) = birlesik
    neden = KOSULLAR_SAGLANDI
    karar = ONAYLI
    if any(s.kokler != birlesik for s in sonuclar):
        karar, neden = ADAY, HOMOGRAF_CELISKISI
    elif tur_uyusmuyor:
        karar, neden = ADAY, POS_UYUSMAZLIGI
    return sonuc(
        karar,
        neden,
        kok=kok,
        ar_lemma=_ar_lemma(kok, sonuclar),
        yontem=_yontem(kok, sonuclar),
        adaylar=(kok,),
        kaynaklar=kaynaklar,
    )


def yuzey_karari(
    analiz: Analiz,
    indeks: KaikkiIndeksi,
    env: QacEnvanteri,
    onbellek: dict[tuple[str, frozenset[str]], Karar] | None = None,
    lemma_poslari: Mapping[str, frozenset[str]] | None = None,
) -> YuzeyKarari:
    """Bir yuzey bicimin karari (tur duzeyi karar tablosunun satiri).

    Sira: bilinmeyen -> kapali sinif -> belirsiz lemma (birden cok lemma) -> lemma karari.
    `lemma_poslari` (lemma -> butun yuzey bicimlerinden toplanan zeyrek turleri) verilirse lemma
    karari onunla verilir; verilmezse bu bicimin cozumlerindeki turler kullanilir.
    """
    if analiz.bilinmiyor:
        return YuzeyKarari(KOK_YOK, BILINMEYEN_SOZCUK)
    lemmalar = sorted(analiz.lemmalar)

    def poslar_al(lm: str) -> frozenset[str]:
        return (lemma_poslari or {}).get(lm) or analiz.poslar(lm)

    if any(kapali_mi(lm, poslar_al(lm)) for lm in lemmalar):
        return YuzeyKarari(KOK_YOK, KAPALI_SINIF)
    onbellek = onbellek if onbellek is not None else {}

    def karar_al(lm: str) -> Karar:
        anahtar = (lm, poslar_al(lm))
        if anahtar not in onbellek:
            onbellek[anahtar] = lemma_karari(lm, anahtar[1], indeks, env)
        return onbellek[anahtar]

    if len(lemmalar) > 1:
        if all(karar_al(lm).karar == KOK_YOK for lm in lemmalar):
            return YuzeyKarari(KOK_YOK, KANIT_YOK)
        return YuzeyKarari(ADAY, BELIRSIZ_LEMMA)
    lm = lemmalar[0]
    k = karar_al(lm)
    return YuzeyKarari(k.karar, k.neden, lm, k)
