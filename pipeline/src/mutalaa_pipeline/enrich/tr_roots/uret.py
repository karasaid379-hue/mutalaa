"""Iki mealin birlesik sayimi, tur duzeyi karar tablosu ve staged satirlari (K-51 madde 7 ve 9).

Karar tablosu TUR DUZEYINDEDIR: yuzey bicim (`Parca.anahtar`, Turkce kucuk harf) -> lemma karari.
Ayni bicim iki mealde de gecerse sayilar toplanir ve karar tektir. Lemma karari, lemmanin butun
yuzey bicimlerinden toplanan zeyrek turleri uzerinden TEK KEZ verilir (bir lemmanin iki farkli
karari olmaz).

Cikti satirlari ASCII kacisli, siralidir ve zaman damgasi icermez (ayni girdi ayni bayt):

* `tr_lemmas.jsonl`: tek lemmaya inen yuzey bicimlerin BUTUN lemmalari (karar `onayli_otomatik`,
  `aday` ya da `kok_yok`; yukleme `kok_yok` icin satir acmaz ama otomatik onayin neden geri
  alindigini bu satirdan okur); anahtar `lemma`;
* `tr_forms.jsonl`: her yuzey bicim; anahtar `form`;
* istatistik: sinif sayilari, neden dagilimi, zeyrek kapsami (yan rapor ve manifest).

`review_onerilir`: lemma `aday`, bir kok onerisi tasiyor ve toplam sikligi `min_freq` ya da daha
fazla. Esigin altindakiler raporda sayilir; review acilmaz.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.enrich.tr_roots.bolme import parcalar
from mutalaa_pipeline.enrich.tr_roots.eslesme import QacEnvanteri
from mutalaa_pipeline.enrich.tr_roots.etimoloji import KaikkiIndeksi
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Lemmatizer
from mutalaa_pipeline.enrich.tr_roots.politika import (
    ADAY,
    KARARLAR,
    KOK_YOK,
    ONAYLI,
    POLITIKA_SURUMU,
    Karar,
    YuzeyKarari,
    yuzey_karari,
)
from mutalaa_pipeline.normalize.turkish import normalize_tr

LEMMALAR_ADI: Final = "tr_lemmas.jsonl"
FORMLAR_ADI: Final = "tr_forms.jsonl"
VARSAYILAN_MIN_SIKLIK: Final = 3


@dataclass(frozen=True)
class KaynakMetni:
    """Bir mealin birimleri: `(capa, metin)` ciftleri."""

    kaynak_id: str
    birimler: Sequence[tuple[str, str]]


@dataclass(frozen=True)
class Uretim:
    lemma_satirlari: list[dict[str, object]]
    form_satirlari: list[dict[str, object]]
    istatistik: dict[str, object]


def _yuzde(pay: int, payda: int) -> float:
    return round(100 * pay / payda, 2) if payda else 0.0


def sikliklari_say(kaynaklar: Sequence[KaynakMetni]) -> dict[str, Counter[str]]:
    """Yuzey bicim -> kaynak basina gecis sayisi (sozcuk parcasi basina)."""
    sayac: dict[str, Counter[str]] = {}
    for kaynak in kaynaklar:
        for _, metin in kaynak.birimler:
            for p in parcalar(metin):
                sayac.setdefault(p.anahtar, Counter())[kaynak.kaynak_id] += 1
    return sayac


def _lemma_satiri(
    lemma: str,
    karar: Karar,
    poslar: frozenset[str],
    freq: Counter[str],
    min_sik: int,
    data_version: str,
) -> dict[str, object]:
    toplam = sum(freq.values())
    return {
        "lemma": lemma,
        "text_clean": normalize_tr(lemma, "dar"),
        "karar": karar.karar,
        "neden": karar.neden,
        "kanit": karar.kanit(),
        "root_letters_bw": karar.kok.letters_bw if karar.kok else None,
        "root_letters": karar.kok.letters if karar.kok else None,
        "ar_lemma_qac_ref": karar.ar_lemma.qac_ref if karar.ar_lemma else None,
        "pos": sorted(poslar),
        "freq": toplam,
        "freq_kaynak": dict(sorted(freq.items())),
        "review_onerilir": karar.karar == ADAY and karar.kok is not None and toplam >= min_sik,
        "politika_surumu": POLITIKA_SURUMU,
        "source_id": "kaikki-tr",
        "data_version": data_version,
    }


def uret(
    kaynaklar: Sequence[KaynakMetni],
    lemmatizer: Lemmatizer,
    indeks: KaikkiIndeksi,
    env: QacEnvanteri,
    *,
    min_sik: int = VARSAYILAN_MIN_SIKLIK,
    data_version: str,
) -> Uretim:
    """Sayim, lemmatizasyon, karar tablosu, staged satirlari ve istatistik."""
    siklik = sikliklari_say(kaynaklar)
    analizler = {f: lemmatizer.analiz(f.replace("'", "")) for f in sorted(siklik)}

    # lemma -> butun yuzey bicimlerinden toplanan zeyrek turleri
    lemma_poslari: dict[str, set[str]] = {}
    for analiz in analizler.values():
        for c in analiz.cozumler:
            lemma_poslari.setdefault(c.lemma, set()).add(c.pos)
    poslar_sabit: Mapping[str, frozenset[str]] = {k: frozenset(v) for k, v in lemma_poslari.items()}

    onbellek: dict[tuple[str, frozenset[str]], Karar] = {}
    kararlar: dict[str, YuzeyKarari] = {
        f: yuzey_karari(a, indeks, env, onbellek, poslar_sabit) for f, a in analizler.items()
    }

    lemma_sikligi: dict[str, Counter[str]] = {}
    lemma_kararlari: dict[str, Karar] = {}
    form_satirlari: list[dict[str, object]] = []
    for f in sorted(siklik):
        k = kararlar[f]
        if k.lemma is not None and k.lemma_karari is not None:
            lemma_sikligi.setdefault(k.lemma, Counter()).update(siklik[f])
            lemma_kararlari[k.lemma] = k.lemma_karari
        form_satirlari.append(
            {
                "form": f,
                "lemma": k.lemma,
                "karar": k.karar,
                "neden": k.neden,
                "freq": sum(siklik[f].values()),
                "freq_kaynak": dict(sorted(siklik[f].items())),
                "bilinen": not analizler[f].bilinmiyor,
                "source_id": "kaikki-tr",
                "data_version": data_version,
            }
        )

    lemma_satirlari: list[dict[str, object]] = []
    for lemma in sorted(lemma_sikligi):
        karar = lemma_kararlari[lemma]
        anahtar = normalize_tr(lemma, "dar")
        if anahtar != lemma:
            continue  # dar anahtar lemmayla ayni degil: lemma satiri kurulamaz
        lemma_satirlari.append(
            _lemma_satiri(
                lemma, karar, poslar_sabit[lemma], lemma_sikligi[lemma], min_sik, data_version
            )
        )

    return Uretim(
        lemma_satirlari,
        form_satirlari,
        _istatistik(kaynaklar, siklik, kararlar, form_satirlari, lemma_satirlari),
    )


def _istatistik(
    kaynaklar: Sequence[KaynakMetni],
    siklik: Mapping[str, Counter[str]],
    kararlar: Mapping[str, YuzeyKarari],
    form_satirlari: Sequence[Mapping[str, object]],
    lemma_satirlari: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    tur_toplam = len(siklik)
    token_toplam = sum(sum(c.values()) for c in siklik.values())
    bilinen_tur = sum(1 for s in form_satirlari if s["bilinen"])
    bilinen_token = sum(int(str(s["freq"])) for s in form_satirlari if s["bilinen"])
    siniflar: dict[str, dict[str, int | float]] = {}
    for ad in KARARLAR:
        turler = [f for f, k in kararlar.items() if k.karar == ad]
        tokenlar = sum(sum(siklik[f].values()) for f in turler)
        siniflar[ad] = {
            "tur": len(turler),
            "token": tokenlar,
            "tur_yuzde": _yuzde(len(turler), tur_toplam),
            "token_yuzde": _yuzde(tokenlar, token_toplam),
        }
    nedenler: Counter[str] = Counter()
    neden_token: Counter[str] = Counter()
    for f, k in kararlar.items():
        nedenler[f"{k.karar}:{k.neden}"] += 1
        neden_token[f"{k.karar}:{k.neden}"] += sum(siklik[f].values())
    kaynak_ozeti: dict[str, dict[str, int]] = {}
    for kaynak in kaynaklar:
        kid = kaynak.kaynak_id
        sayilar: dict[str, int] = {"tur": 0, "token": 0}
        for ad in KARARLAR:
            sayilar[f"token_{ad}"] = 0
        for f, c in siklik.items():
            n = c.get(kid, 0)
            if n:
                sayilar["tur"] += 1
                sayilar["token"] += n
                sayilar[f"token_{kararlar[f].karar}"] += n
        kaynak_ozeti[kid] = sayilar
    lemma_sinif = Counter(str(s["karar"]) for s in lemma_satirlari)
    return {
        "tur": tur_toplam,
        "token": token_toplam,
        "zeyrek_bilinen": {
            "tur": bilinen_tur,
            "token": bilinen_token,
            "tur_yuzde": _yuzde(bilinen_tur, tur_toplam),
            "token_yuzde": _yuzde(bilinen_token, token_toplam),
        },
        "siniflar": siniflar,
        "nedenler": {k: {"tur": nedenler[k], "token": neden_token[k]} for k in sorted(nedenler)},
        "kaynaklar": kaynak_ozeti,
        "lemma": {
            ONAYLI: lemma_sinif[ONAYLI],
            ADAY: lemma_sinif[ADAY],
            KOK_YOK: lemma_sinif[KOK_YOK],
            "aday_oneri_var": sum(
                1 for s in lemma_satirlari if s["karar"] == ADAY and s["root_letters_bw"]
            ),
            "review_onerilir": sum(1 for s in lemma_satirlari if s["review_onerilir"]),
            "esik_alti_aday": sum(
                1
                for s in lemma_satirlari
                if s["karar"] == ADAY and s["root_letters_bw"] and not s["review_onerilir"]
            ),
        },
    }
