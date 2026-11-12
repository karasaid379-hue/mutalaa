"""Hazir kaynaktan kelime anlami adaylari: saf islevler (A17.6, K-50 madde 5); dosya ve DB yok.

Girdi: QAC kelimeleri (`words.jsonl`: kelime capasi -> govde lemmasi `lemma_qac_ref`), QuranWBW
anlam girdileri (`meanings.jsonl`: kelime capasi -> kanonik anlam metni) ve QAC dalgalari
(`waves.jsonl`: lemma -> dalga, sira). Her QAC kelimesinin anlami AYNI konumdaki (`q:s:a:k`)
QuranWBW girdisidir; anlamlar govde lemmasina gore toplanir (kelime duzeyi sayim; lemmasiz kelime
atlanir).

GRUPLAMA (K-50 madde 5, K-43 madde 5 emsali): anlamlar `normalize_tr(anlam, "genis")` anahtariyla
kumelenir (Turkce noktali ve noktasiz i acik eslemeyle; buyuk-kucuk harf ve ayirici isaret
farki bir kumeyi bolmez). Anahtar YALNIZ gruplamada kullanilir, hicbir cikti alanina
YAZILMAZ. Kumenin gorunen yazimi o kumedeki en sik GERCEK kanonik yazimdir (esitlikte UTF-8
bayt sirasi); `anlam_kisa` baskin
kumenin gorunen yazimidir. `dagilim` kumelere BOLUNMEZ: her gercek yazim ayri `{anlam, sayi}`
girdisidir (sayiya gore azalan, esitlikte UTF-8 bayt sirasi); `baskin_sayi` ise baskin KUMENIN
toplamidir (ayni anahtara dusen yazimlar tek anahtar altinda sayilir). Baskin kume: en buyuk
toplam, esitlikte gorunen yazimin UTF-8 bayt sirasi.

`baskin_pay = baskin_sayi / toplam`; `tutarsiz_hazir_anlam` = baskin_pay < 0,8 (tam sayi
aritmetigi: `baskin_sayi * 10 < toplam * 8`). Esik aday kumesini degistirmez: her lemma aday olur.
`kuran_anlamlari`: en sik uc kumenin gorunen yazimi (en cok 3 madde).

DALGA SECIMI (`--wave N`): `N = 1` dalga 0 ve 1'i birlikte, `N >= 2` yalniz N'yi isler.

Anlam metinleri yalniz staged satirlarinda ve (export'ta) `review.onerilen` icinde bulunur;
hata iletileri, gunlukler ve raporlar anlam metni tasimaz (yalniz sayi ve `qac_ref`).
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.quranwbw import KAYNAK, veri_surumu
from mutalaa_pipeline.normalize import lower_turkish, normalize_tr

GLOSSES_ADI: Final = "glosses.jsonl"
ESIK_PAYDA: Final = 10  # baskin_pay >= 0,8  <=>  baskin_sayi * 10 >= toplam * 8
ESIK_PAY: Final = 8
KURAN_ANLAMI_SINIRI: Final = 3
SON_DALGA: Final = 4


def secilen_dalgalar(wave: int) -> frozenset[int]:
    """`--wave N` -> islenecek dalgalar: 1 -> {0, 1}; 2..4 -> {N}; baska deger `GirdiHatasi`."""
    if not 1 <= wave <= SON_DALGA:
        raise GirdiHatasi(f"--wave 1..{SON_DALGA} olmali (dalga 0, --wave 1 ile birlikte acilir)")
    return frozenset({0, 1}) if wave == 1 else frozenset({wave})


def grup_anahtari(anlam: str) -> tuple[bool, str]:
    """Gruplama anahtari: `normalize_tr` GENIS anahtari. Anahtar bos kalirsa (anlam yalniz
    Turkce olmayan harf ya da isaret iceriyorsa) kumeyi bozmamak icin Turkce acik eslemeyle kucuk
    harfe cevrilmis anlam kullanilir (`True` isareti ayri bir anahtar uzayi acar)."""
    anahtar = normalize_tr(anlam, "genis")
    if anahtar != "":
        return False, anahtar
    return True, lower_turkish(anlam)


def _bayt_sirasi(metin: str) -> bytes:
    return metin.encode("utf-8")


@dataclass(frozen=True)
class LemmaAdayi:
    qac_ref: str
    toplam: int
    baskin_sayi: int
    anlam_kisa: str
    dagilim: tuple[tuple[str, int], ...]  # (gercek yazim, sayi); sayiya gore azalan
    kuran_anlamlari: tuple[str, ...]

    @property
    def tutarli(self) -> bool:
        return self.baskin_sayi * ESIK_PAYDA >= self.toplam * ESIK_PAY


def lemma_adayi(qac_ref: str, anlamlar: Counter[str]) -> LemmaAdayi:
    """Bir lemmanin anlam sayaclarindan adayi uretir (bos sayac `ValueError`)."""
    if not anlamlar:
        raise ValueError("bos anlam sayaci")
    kumeler: dict[tuple[bool, str], Counter[str]] = {}
    for anlam, sayi in anlamlar.items():
        kumeler.setdefault(grup_anahtari(anlam), Counter())[anlam] += sayi
    gorunen: list[tuple[str, int]] = []  # (kumenin gorunen yazimi, kume toplami)
    for yazimlar in kumeler.values():
        yazim = min(yazimlar, key=lambda a: (-yazimlar[a], _bayt_sirasi(a)))
        gorunen.append((yazim, sum(yazimlar.values())))
    gorunen.sort(key=lambda oge: (-oge[1], _bayt_sirasi(oge[0])))
    dagilim = tuple(sorted(anlamlar.items(), key=lambda oge: (-oge[1], _bayt_sirasi(oge[0]))))
    return LemmaAdayi(
        qac_ref=qac_ref,
        toplam=sum(anlamlar.values()),
        baskin_sayi=gorunen[0][1],
        anlam_kisa=gorunen[0][0],
        dagilim=dagilim,
        kuran_anlamlari=tuple(yazim for yazim, _ in gorunen[:KURAN_ANLAMI_SINIRI]),
    )


def aday_satiri(aday: LemmaAdayi, dalga: int, sira: int, surum: str) -> dict[str, object]:
    """`glosses.jsonl` satiri (ondalik sayi yok: `baskin_pay` = `baskin_sayi` / `toplam`)."""
    return {
        "qac_ref": aday.qac_ref,
        "dalga": dalga,
        "sira": sira,
        "toplam": aday.toplam,
        "baskin_sayi": aday.baskin_sayi,
        "anlam_kisa": aday.anlam_kisa,
        "dagilim": [{"anlam": a, "sayi": n} for a, n in aday.dagilim],
        "kuran_anlamlari": list(aday.kuran_anlamlari),
        "tutarsiz_hazir_anlam": not aday.tutarli,
        "source_id": KAYNAK,
        "data_version": veri_surumu(surum),
    }


@dataclass(frozen=True)
class Uretim:
    """Bir `--wave` calismasinin sonucu (adim ve QA ayni islevi kullanir)."""

    satirlar: list[dict[str, object]]  # `qac_ref`e gore sirasiz; dosya yazicisi siralar
    adaylar: list[LemmaAdayi]
    dalgalar: dict[str, int]  # qac_ref -> dalga
    lemmasiz_kelime: int  # govdesinde lemma olmayan kelime (anlami toplanmaz)
    secilen_kelime: int  # secilen dalgalardaki lemmalarin anlami toplanan kelime sayisi


def uret(
    kelime_satirlari: Sequence[Mapping[str, object]],
    anlam_satirlari: Sequence[Mapping[str, object]],
    dalga_satirlari: Sequence[Mapping[str, object]],
    wave: int,
    surum: str,
) -> Uretim:
    """`--wave` icin aday satirlari. Eksik anlam girdisi ya da bilinmeyen lemma `GirdiHatasi`."""
    secilen = secilen_dalgalar(wave)
    anlam = {str(s["anchor"]): str(s["text"]) for s in anlam_satirlari}
    dalga: dict[str, int] = {}
    sira: dict[str, int] = {}
    for d in dalga_satirlari:
        ref = str(d["qac_ref"])
        no, s = d["dalga"], d["sira"]
        if not isinstance(no, int) or not isinstance(s, int):
            raise GirdiHatasi("waves.jsonl: dalga ya da sira tam sayi degil")
        dalga[ref], sira[ref] = no, s
    sayaclar: dict[str, Counter[str]] = {}
    lemmasiz = secilen_kelime = 0
    for k in kelime_satirlari:
        lemma = k["lemma_qac_ref"]
        if lemma is None:
            lemmasiz += 1
            continue
        ref = str(lemma)
        if ref not in dalga:
            raise GirdiHatasi("words.jsonl: waves.jsonl'da olmayan lemma basvurusu")
        if dalga[ref] not in secilen:
            continue
        capa = str(k["anchor"])
        if capa not in anlam:
            raise GirdiHatasi(f"quranwbw: {capa} icin anlam girdisi yok")
        sayaclar.setdefault(ref, Counter())[anlam[capa]] += 1
        secilen_kelime += 1
    adaylar = [lemma_adayi(ref, sayac) for ref, sayac in sorted(sayaclar.items())]
    eksik = [ref for ref, no in dalga.items() if no in secilen and ref not in sayaclar]
    if eksik:
        raise GirdiHatasi(f"secilen dalgada kelimesi olmayan {len(eksik)} lemma var")
    return Uretim(
        satirlar=[aday_satiri(a, dalga[a.qac_ref], sira[a.qac_ref], surum) for a in adaylar],
        adaylar=adaylar,
        dalgalar={a.qac_ref: dalga[a.qac_ref] for a in adaylar},
        lemmasiz_kelime=lemmasiz,
        secilen_kelime=secilen_kelime,
    )


# --- kapsama raporu (yalniz sayi) ---------------------------------------------------------


def kapsama_raporu(uretim: Uretim, wave: int, kelime_sayisi: int, surum: str) -> dict[str, object]:
    """Dalga basina lemma, tutarli/tutarsiz sayisi, kelime kapsami ve baskin pay dagilimi.

    YALNIZ sayi ve dalga numarasi: anlam metni, lemma metni ya da `qac_ref` yoktur.
    `baskin_pay_dagilimi`: baskin payin onda bir araliklari (`0.0-0.1` ... `0.9-1.0`; sag uc
    son aralikta dahil) basina lemma sayisi, tam sayi aritmetigiyle.
    """
    dalga_sayac: dict[int, dict[str, int]] = {}
    kovalar = Counter[int]()
    tek_anlam = 0
    for aday in uretim.adaylar:
        no = uretim.dalgalar[aday.qac_ref]
        satir = dalga_sayac.setdefault(no, {"lemma": 0, "tutarli": 0, "tutarsiz": 0, "kelime": 0})
        satir["lemma"] += 1
        satir["tutarli" if aday.tutarli else "tutarsiz"] += 1
        satir["kelime"] += aday.toplam
        kovalar[min(aday.baskin_sayi * 10 // aday.toplam, 9)] += 1
        tek_anlam += len(aday.dagilim) == 1
    tutarli = sum(1 for a in uretim.adaylar if a.tutarli)
    return {
        "tur": "anlam-kapsama",
        "kaynak": KAYNAK,
        "data_version": veri_surumu(surum),
        "wave": wave,
        "secilen_dalgalar": sorted(secilen_dalgalar(wave)),
        "lemma": len(uretim.adaylar),
        "tutarli": tutarli,
        "tutarsiz": len(uretim.adaylar) - tutarli,
        "tek_yazimli_lemma": tek_anlam,
        "anlami_toplanan_kelime": uretim.secilen_kelime,
        "toplam_kelime": kelime_sayisi,
        "lemmasiz_kelime": uretim.lemmasiz_kelime,
        "esik": "baskin_sayi * 10 >= toplam * 8",
        "dalga_basina": {str(no): dalga_sayac[no] for no in sorted(dalga_sayac)},
        "baskin_pay_dagilimi": {
            f"0.{i}-{'1.0' if i == 9 else f'0.{i + 1}'}": kovalar.get(i, 0) for i in range(10)
        },
    }
