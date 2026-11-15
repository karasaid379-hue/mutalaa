"""Hazir arac karsilastirmasi: `ijaza` ve `quran-search-in-text` (A18.5; Iktibas tespiti §11).

Her iki arac ETIKETLI TEST VERISI TASIMAZ: yalniz karsilastirma aracidir, degerlendirme seti
degildir (K-51 madde 12). Sentetik paragraflardaki Arapca diziler BIZIM `arapca_diziler`
cikariciyla ayrilir (§11 karar kurali: "bizim cikardigimiz dizilerle"); araca her dizi ayri
verilir, donen aciklik dizi ofsetiyle paragrafa tasinir.

* `ijaza` 2.0.0: `QuranValidator().scan_for_verses(dizi_metni)` (varsayilan `min_words=3`,
  `confidence_threshold=0.85`); sonuc `verses`, `start_pos`, `end_pos` (kod noktasi, dizi icinde).
* `quran-search-in-text` 0.1.3: `AyehYab().ayeh_find(dizi_metni)` (varsayilan `min_word=3`,
  `min_len_pure_text=10`); sonuc `ayehid` (kuresel ayet no, virgullu liste = ardisik ayetler),
  `index_start_end`.

Olcum bizim motorla ayni olcutle yapilir (dizi duzeyi IoU >= 0,5 ve ayet duzeyi; uzun/kisa tahmin
kelime sayisi aciklik metninden sayilir). Bir arac hata verirse hata turu raporlanir ve atlanir.
"""

import re
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.enrich.citations.diziler import arapca_diziler
from mutalaa_pipeline.qa.gold.olcum import (
    ESIKLER,
    AciklikSonucu,
    ReferansAciklik,
    TahminAciklik,
    aciklik_esle,
)

KISA_N: Final = 4
ARALIK: Final = re.compile(r"[0-9]{1,3}:[0-9]{1,3}")


@dataclass(frozen=True)
class AracTahmini:
    hedef: str
    bas: int
    son: int
    kelime: int


Arac = Callable[[str], list[tuple[list[str], int, int]]]  # dizi metni -> (hedefler, bas, son)


def ijaza_araci() -> Arac:
    """`ijaza` ile dizi tarayici: her bulgu `(hedef capalar, bas, son)`."""
    from ijaza import QuranValidator

    dogrulayici = QuranValidator()

    def tara(metin: str) -> list[tuple[list[str], int, int]]:
        sonuc: list[tuple[list[str], int, int]] = []
        for b in dogrulayici.scan_for_verses(metin):
            ayetler = [f"q:{v.surah}:{v.ayah}" for v in b["verses"]]
            if not ayetler and ARALIK.fullmatch(str(b.get("reference", ""))):
                ayetler = [f"q:{b['reference']}"]
            sonuc.append((ayetler, int(b["start_pos"]), int(b["end_pos"])))
        return sonuc

    return tara


def search_in_text_araci(ayet_capalari: Sequence[str]) -> Arac:
    """`quran-search-in-text` ile dizi tarayici (kuresel ayet no -> capa)."""
    from quran_search_in_text.ayeh_yab import AyehYab  # type: ignore[import-untyped]

    bulucu = AyehYab()

    def tara(metin: str) -> list[tuple[list[str], int, int]]:
        cikti = bulucu.ayeh_find(metin)
        sonuc: list[tuple[list[str], int, int]] = []
        for grup in cikti["list_output"]:
            for b in grup:
                kimlikler = [int(x) for x in str(b.get("ayehid", "")).split(",") if x]
                if not kimlikler:
                    continue
                bas, son = b["index_start_end"]
                sonuc.append(([ayet_capalari[k - 1] for k in kimlikler], int(bas), int(son)))
        return sonuc

    return tara


def arac_calistir(
    arac: Arac, ornekler: Sequence[Mapping[str, object]]
) -> tuple[dict[str, list[AracTahmini]], dict[str, float | int]]:
    """Her paragrafin Arapca dizilerini araca verir; `(ornek -> tahminler, sure/hata sayaclari)`."""
    sonuc: dict[str, list[AracTahmini]] = {}
    hata = 0
    baslangic = time.monotonic()
    for o in ornekler:
        metin = str(o["paragraf"])
        liste: list[AracTahmini] = []
        for dizi in arapca_diziler(metin):
            try:
                bulgular = arac(dizi.metin)
            except Exception:  # arac hatasi olcumu durdurmaz; yalniz sayilir
                hata += 1
                continue
            for hedefler, bas, son in bulgular:
                if not 0 <= bas < son <= len(dizi.metin):
                    continue
                kelime = len(dizi.metin[bas:son].split())
                for h in hedefler:
                    liste.append(AracTahmini(h, dizi.bas + bas, dizi.bas + son, kelime))
        sonuc[str(o["id"])] = liste
    return sonuc, {"hata": hata, "sure_sn": round(time.monotonic() - baslangic, 2)}


def genel_olc(
    ornekler: Sequence[Mapping[str, object]], tahminler: Mapping[str, Sequence[AracTahmini]]
) -> dict[str, object]:
    """Dizi ve ayet duzeyinde PRF (tum, uzun, kisa); bizim motorla ayni olcut."""

    def topla(ayet_duzeyi: bool) -> tuple[AciklikSonucu, list[int], list[int]]:
        t_ok: list[bool] = []
        r_ok: list[bool] = []
        t_n: list[int] = []
        r_n: list[int] = []
        for o in ornekler:
            golds = o["iktibas"]
            assert isinstance(golds, list)
            tah = list(tahminler.get(str(o["id"]), ()))
            if ayet_duzeyi:
                en: dict[str, int] = {}
                for t in tah:
                    en[t.hedef] = max(en.get(t.hedef, 0), t.kelime)
                t_list = [TahminAciklik(c, 0, 1) for c in sorted(en)]
                t_n.extend(en[c] for c in sorted(en))
                r_list = [ReferansAciklik(frozenset(g["hedefler"]), 0, 1) for g in golds]
            else:
                t_list = [TahminAciklik(t.hedef, t.bas, t.son) for t in tah]
                t_n.extend(t.kelime for t in tah)
                r_list = [
                    ReferansAciklik(frozenset(g["hedefler"]), g["bas"], g["son"]) for g in golds
                ]
            s = aciklik_esle(t_list, r_list)
            t_ok.extend(s.tahmin_eslesen)
            r_ok.extend(s.referans_eslesen)
            r_n.extend(int(g["kelime"]) for g in golds)
        return AciklikSonucu(len(t_ok), len(r_ok), tuple(t_ok), tuple(r_ok)), t_n, r_n

    sonuc: dict[str, object] = {}
    for ad, ayet in (("dizi", False), ("ayet", True)):
        toplu, t_n, r_n = topla(ayet)
        sonuc[ad] = {
            "tum": toplu.prf().sozluk(),
            "uzun": toplu.prf([n >= KISA_N for n in t_n], [n >= KISA_N for n in r_n]).sozluk(),
            "kisa": toplu.prf([n < KISA_N for n in t_n], [n < KISA_N for n in r_n]).sozluk(),
        }
    return sonuc


def hedefleri_tuttu_mu(olcum: Mapping[str, object]) -> dict[str, object]:
    """§11 olcutu: uzun kesinlik >= 0,95 ve duyarlilik >= 0,85; kisa kesinlik >= 0,85 (dizi)."""
    dizi = olcum["dizi"]
    assert isinstance(dizi, dict)
    uzun, kisa = dizi["uzun"], dizi["kisa"]
    e_uzun, e_kisa = ESIKLER["iktibas_uzun"], ESIKLER["iktibas_kisa"]
    kontrol = {
        "uzun_kesinlik": float(uzun["kesinlik"]) >= e_uzun["kesinlik"],
        "uzun_duyarlilik": float(uzun["duyarlilik"]) >= e_uzun["duyarlilik"],
        "kisa_kesinlik": float(kisa["kesinlik"]) >= e_kisa["kesinlik"],
    }
    return {"kontrol": kontrol, "hedefler_tuttu": all(kontrol.values())}
