# ruff: noqa: RUF001
"""Meal raporlari (A16.3): kapsam, kod noktasi envanteri, capraz tanik, sadelestirme taramasi.

`qa run --source <meal>` kapilarin yaninda `data/reports/{run_id}-meal-raporlari.json` dosyasini
yazar. Raporlar METIN ICERMEZ: yalniz capa, sure numarasi, sayi, kod noktasi (U+XXXX), kategori
ve ozet. Sozcuk listesi de yoktur (sozcuk meal metninin parcasidir); editor sorunlu ayetin
capasina gidip metne bakar.

* Kapsam: sure basina beklenen ve bulunan birim, birlesik bas/izleyen, bos metin, uyari kodu
  sayilari (`provenance.uyari`) ve ingest'in sayfa basi/sonu bolgeleri (sure, uzunluk, ozet).
* Kod noktasi envanteri: birim metinlerindeki kategori sayilari ve "ilgili" karakterler
  (Cc, Cf, Co, Cn, birlesen isaretler, bosluk disi bosluklar, kesme benzeri isaretler).
* Capraz tanik (yalniz `elmalili-meal`): tanik skoru dagilimi ve en dusuk skorlu ayetler. Baskin
  uyari: tanik de bir dijital derlemedir; baskisi belgesizdir ve ortak koken ihtimali vardir;
  skor ozgun baskiya sadakat degildir (K-49).
* Sadelestirme taramasi (yalniz `elmalili-meal`): veriye dayanir, yapay zeka KULLANILMAZ.
  Her ayet icin orijinal mealle guncel (sadelestirilmis) meal ortak olup tanikta bulunmayan
  sozcuk sayisi (`tr_narrow` sozcukleri), ayrica sapka ve kesme isareti sayisi farki hesaplanir;
  en yuksek ayetler capa ve sayi olarak listelenir. Sonuc bir TARAMA ipucudur, hukum degildir.
"""

import statistics
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Final

from mutalaa_pipeline.adimlar.meal import meal_capasi
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.normalize import search_keys
from mutalaa_pipeline.staged import Satir

EN_COK_LISTE: Final = 50
SAPKALI: Final = frozenset("âîûÂÎÛ")
KESME_BENZERI: Final = frozenset("'`´‘’ʻʼʾʿ")
ILGILI_KATEGORILER: Final = frozenset({"Cc", "Cf", "Co", "Cn", "Cs", "Mn", "Mc", "Me"})
TANIK_UYARISI: Final = (
    "Tanik de dijital bir derlemedir; baskisi belgesizdir ve Vikikaynak ile ortak koken ihtimali"
    " vardir. Skor iki metnin yakinligidir, ozgun baskiya sadakat degildir (K-49)."
)
TARAMA_UYARISI: Final = (
    "Veriye dayali tarama ipucu: yapay zeka kullanilmaz, hukum vermez. Sayilar, orijinal mealde"
    " guncel mealle ortak olup tanikta bulunmayan sozcuk sayisidir; metin ve sozcuk icermez."
)


def _kod(harf: str) -> str:
    return f"U+{ord(harf):04X}"


def kod_noktasi_envanteri(metinler: Sequence[str]) -> dict[str, object]:
    kategori: Counter[str] = Counter()
    ilgili: Counter[tuple[str, str]] = Counter()
    for metin in metinler:
        for harf in metin:
            k = unicodedata.category(harf)
            kategori[k] += 1
            ozel = (k == "Zs" and harf != " ") or harf in KESME_BENZERI or k in ILGILI_KATEGORILER
            if ozel and harf != "\n":
                ilgili[(k, _kod(harf))] += 1
    return {
        "unidata": unicodedata.unidata_version,
        "kategori_sayilari": dict(sorted(kategori.items())),
        "ilgili": [
            {"kategori": k, "kod": kod, "adet": n} for (k, kod), n in sorted(ilgili.items())
        ],
    }


def kapsam_raporu(
    slug: str, satirlar: Sequence[Satir], ingest_ayrintilari: Mapping[str, object]
) -> dict[str, object]:
    sure_birim: Counter[int] = Counter()
    sure_izleyen: Counter[int] = Counter()
    sure_bos: Counter[int] = Counter()
    sure_uyarili: Counter[int] = Counter()
    uyari_sayilari: Counter[str] = Counter()
    uzunluklar: list[int] = []
    bas = 0
    for satir in satirlar:
        cozulen = meal_capasi(slug, satir.metin("anchor"))
        if cozulen is None:
            continue
        sure = cozulen[0]
        sure_birim[sure] += 1
        attrs = satir.nesne("attrs")
        if "birlesik_ile" in attrs:
            sure_izleyen[sure] += 1
        if "kapsam" in attrs:
            bas += 1
        metin = satir.metin("text")
        if metin == "":
            sure_bos[sure] += 1
        else:
            uzunluklar.append(len(metin))
        uyari = satir.nesne("provenance").get("uyari")
        if isinstance(uyari, list) and uyari:
            sure_uyarili[sure] += 1
            for kod in uyari:
                uyari_sayilari[str(kod)] += 1
    return {
        "kaynak": slug,
        "sure": len(sure_birim),
        "birim": sum(sure_birim.values()),
        "beklenen": sum(AYET_SAYILARI),
        "birlesik_bas": bas,
        "birlesik_izleyen": sum(sure_izleyen.values()),
        "bos_metin": sum(sure_bos.values()),
        "uyari_sayilari": dict(sorted(uyari_sayilari.items())),
        "metin_uzunlugu": (
            {
                "min": min(uzunluklar),
                "max": max(uzunluklar),
                "ortalama": round(statistics.fmean(uzunluklar), 1),
                "toplam": sum(uzunluklar),
            }
            if uzunluklar
            else None
        ),
        "sure_basina": [
            {
                "sure": s,
                "beklenen": AYET_SAYILARI[s - 1],
                "birim": sure_birim.get(s, 0),
                "birlesik_izleyen": sure_izleyen.get(s, 0),
                "bos_metin": sure_bos.get(s, 0),
                "uyarili": sure_uyarili.get(s, 0),
            }
            for s in range(1, 115)
        ],
        "sayfa_bolgeleri": ingest_ayrintilari.get("bolgeler", []),
    }


def _dagilim(skorlar: Sequence[int]) -> dict[str, int]:
    kovalar = [(0, 9), (10, 29), (30, 49), (50, 69), (70, 89), (90, 99), (100, 100)]
    return {f"{a}-{b}": sum(1 for x in skorlar if a <= x <= b) for a, b in kovalar}


def capraz_tanik_raporu(slug: str, satirlar: Sequence[Satir]) -> dict[str, object] | None:
    """Tanik skoru dagilimi ve en dusuk skorlu ayetler; tanigi olmayan mealde None."""
    skorlu: list[tuple[int, int, str]] = []  # (skor, ord, capa)
    taniksiz = 0
    grup_birim = 0
    yontem: dict[str, object] = {}
    for satir in satirlar:
        tanik = satir.veri.get("tanik")
        if not isinstance(tanik, dict):
            taniksiz += 1
            continue
        skor = tanik.get("skor")
        if type(skor) is not int:
            continue
        yontem = {k: tanik.get(k) for k in ("yontem", "yontem_surumu", "kaynak")}
        if tanik.get("kapsam") is not None:
            grup_birim += 1
        skorlu.append((skor, satir.sayi("ord"), satir.metin("anchor")))
    if not skorlu:
        return None
    degerler = [s for s, _, _ in skorlu]
    sirali = sorted(skorlu)
    return {
        "uyari": TANIK_UYARISI,
        "yontem": yontem,
        "tanikli_birim": len(skorlu),
        "taniksiz_birim": taniksiz,
        "grup_kapsamli_birim": grup_birim,
        "skor": {
            "min": min(degerler),
            "p10": sorted(degerler)[len(degerler) // 10],
            "medyan": statistics.median(degerler),
            "ortalama": round(statistics.fmean(degerler), 2),
        },
        "dagilim": _dagilim(degerler),
        "en_dusuk": [{"capa": c, "skor": s} for s, _, c in sirali[:EN_COK_LISTE]],
    }


def _sozcuk_kumesi(tr_narrow: str) -> set[str]:
    return set(tr_narrow.split(" ")) - {""}


def _sapka(metin: str) -> int:
    return sum(1 for h in metin if h in SAPKALI)


def _kesme(metin: str) -> int:
    return sum(1 for h in metin if h in KESME_BENZERI)


def sadelestirme_taramasi(
    slug: str,
    satirlar: Sequence[Satir],
    sade_narrow: Mapping[tuple[int, int], str],
    tanik_satirlari: Sequence[Satir],
) -> dict[str, object]:
    """Orijinal mealde sadelestirme izi taramasi (veriye dayali; yapay zeka yok).

    `sade_narrow`: `(sure, ayet) -> tr_narrow` (guncel meal); `tanik_satirlari`: tanigin parcalari.
    """
    birim: dict[tuple[int, int], Satir] = {}
    for satir in satirlar:
        cozulen = meal_capasi(slug, satir.metin("anchor"))
        if cozulen is not None:
            birim[cozulen] = satir
    sonuclar: list[tuple[int, int, str, int, int]] = []  # (aday, ord, capa, sapka, kesme)
    taranan = 0
    for t in tanik_satirlari:
        sure = t.sayi("sure")
        kapsam = t.veri.get("kapsam")
        if not isinstance(kapsam, list) or len(kapsam) != 2:
            continue
        lo, hi = int(kapsam[0]), int(kapsam[1])
        v_sozcuk: set[str] = set()
        s_sozcuk: set[str] = set()
        v_metin = ""
        for a in range(lo, hi + 1):
            parca = birim.get((sure, a))
            if parca is None:
                continue
            v_sozcuk |= _sozcuk_kumesi(parca.metin("tr_narrow"))
            v_metin += " " + parca.metin("text")
            s_sozcuk |= _sozcuk_kumesi(sade_narrow.get((sure, a), ""))
        e_sozcuk = _sozcuk_kumesi(search_keys(t.metin("metin")).tr_narrow)
        aday = len((v_sozcuk & s_sozcuk) - e_sozcuk)
        sapka = abs(_sapka(v_metin) - _sapka(t.metin("metin")))
        kesme = abs(_kesme(v_metin) - _kesme(t.metin("metin")))
        taranan += 1
        # Her kapsanan ayete ayni grup degeri yazilir (capa listesi icin ilk ayet temsil eder).
        ilk = birim.get((sure, lo))
        if ilk is not None:
            sonuclar.append((aday, ilk.sayi("ord"), ilk.metin("anchor"), sapka, kesme))
    aday_dagilim = Counter(min(a, 10) for a, _, _, _, _ in sonuclar)
    en_yuksek = sorted(sonuclar, key=lambda x: (-x[0], x[1]))[:EN_COK_LISTE]
    return {
        "uyari": TARAMA_UYARISI,
        "taranan_parca": taranan,
        "aday_sozcuk_dagilimi": {
            ("10+" if k == 10 else str(k)): v for k, v in sorted(aday_dagilim.items())
        },
        "aday_olan_parca": sum(1 for a, _, _, _, _ in sonuclar if a > 0),
        "sapka_farki_olan_parca": sum(1 for _, _, _, s, _ in sonuclar if s > 0),
        "kesme_farki_olan_parca": sum(1 for _, _, _, _, k in sonuclar if k > 0),
        "en_yuksek": [
            {"capa": c, "aday_sozcuk": a, "sapka_farki": s, "kesme_farki": k}
            for a, _, c, s, k in en_yuksek
        ],
    }
