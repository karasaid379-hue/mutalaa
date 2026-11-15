"""A20.7a atif araci olcum duzenegi: orneklem, kosu ve rapor (hat tarafi; veritabani yok).

Uc aday arac (`ijaza` 2.0.0, `quran-detector` 0.0.2, `quran-toolkit` 0.1.0; QDetect elendi) ayni
girdi ve ayni Tanzil metni uzerinde, her biri ayri bir surecte olculdu (13 Kasim 2026; K-52 madde
13). Kazanan `quran-toolkit` 0.1.0'dir ve proje bagimliligidir; `ijaza` ve `quran-detector`
sarmalayicilari silindi: bu duzenek bugun yalniz `quran-toolkit` kosar, rapor birlestirme kodu
olcum kaydini okumak icin kalir:

    uv run --directory pipeline python -I -X utf8 -m mutalaa_pipeline.enrich.arac_olcumu ornek ...
    uv run --directory pipeline python -I -X utf8 \\
        -m mutalaa_pipeline.enrich.arac_olcumu kos --arac quran-toolkit ...
    uv run --directory pipeline python -I -X utf8 -m mutalaa_pipeline.enrich.arac_olcumu rapor ...

Etiket yoktur (Iktibas tespiti §10, Risale altin seti: etiketleme insan adimi İ-13): sonuc
kesinlik ve duyarlilik DEGILDIR; raporda "etiketlenmemis" diye yazilir. Olculenler: araclar arasi
uyum, hiz, bellek, hata, aday sayisi ve skor dagilimi, `ar` isaretleriyle hizalanma, `alinti`
(`﹛…|﹜`) ve `blok` (`~…|@`) araliklarinda bulunma orani ve Tanzil metninden uretilen
POZITIF/NEGATIF KONTROLLER (araclarin kendi ayet metnini ve rastgele kelime dizilerini ele
alisi). Kontroller etiket yerine gecmez; yalnizca baglayici sarmalayici hatalarini ve
duyarliligin ust sinirini gosterir.

Bu modul metin yazmaz: orneklem dosyasi (`data/gold/risale-atif/ornek.jsonl`), ham kosu ciktilari
ve rapor yalniz capa, tabaka, sayi, ofset ve sure:ayet numarasi tasir. Girdi dosyalari guvenilmeyen
veri sayilir; her calistirma `python -I` ile yapilir.
"""

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from mutalaa_pipeline.anchor import Rn, parse, sort_key
from mutalaa_pipeline.enrich import arapca_dizi, atif_gramer
from mutalaa_pipeline.enrich.risale_atif import DiziEslesmesi, DiziTespitcisi
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.tanzil_bicim import ayristir
from mutalaa_pipeline.normalize.arabic import normalize_ar
from mutalaa_pipeline.staged import satir_baytlari, satirlari_akit

TOHUM: Final = 20261113
ORNEKLEM_BOYUTU: Final = 420
KONTROL_ADEDI: Final = 120
ARACLAR: Final = ("ijaza", "quran-detector", "quran-toolkit")
RAPOR_ADI: Final = "a20-atif-araclari.json"
ORNEK_YOLU: Final = "gold/risale-atif/ornek.jsonl"
HAM_KLASORU: Final = "staged/a20-atif-olcum"
RAPOR_SURUMU: Final = 1
KISA_KELIME_ESIGI: Final = 4  # Iktibas tespiti §7/§10: 4 kelimeden kisa = kisa
SAYI_RAKAMLARI: Final = frozenset("0123456789") | frozenset(map(chr, range(0x0660, 0x066A)))


# --- orneklem -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Aday:
    """Orneklem adayi paragraf: metin yok, yalniz capa, sayim ve ozet."""

    anchor: str
    kitap: str
    dil: str
    role: str
    ar_isaret: int
    ar_kelime: int
    sayi: int
    uzunluk: int
    content_hash: str

    @property
    def tabaka_ar(self) -> str:
        if self.ar_isaret == 0:
            return "yok"
        return "kisa" if self.ar_kelime < KISA_KELIME_ESIGI else "uzun"

    @property
    def tabaka_sayi(self) -> str:
        if self.sayi == 0:
            return "yok"
        return "az" if self.sayi <= 2 else "cok"

    @property
    def tabaka(self) -> str:
        return f"{self.dil}|{self.tabaka_ar}|{self.tabaka_sayi}"


def sayi_say(metin: str) -> int:
    """Metindeki rakam dizilerinin sayisi (ASCII ve Arapca-Hint)."""
    sayi, icinde = 0, False
    for karakter in metin:
        if karakter in SAYI_RAKAMLARI:
            if not icinde:
                sayi += 1
            icinde = True
        else:
            icinde = False
    return sayi


def _kitap(capa: str) -> str:
    ref = parse(capa)
    if not isinstance(ref.anchor, Rn):
        raise GirdiHatasi("birim capasi Risale capasi degil")
    return ref.anchor.yol[0]


def aday_olustur(veri: Mapping[str, object]) -> Aday | None:
    """`units.jsonl` satirindan aday; metinsiz ya da Risale olmayan satir `None`."""
    metin, capa = veri.get("text"), veri.get("anchor")
    attrs, marks = veri.get("attrs"), veri.get("marks")
    if not isinstance(metin, str) or not isinstance(capa, str) or not metin:
        return None
    if not isinstance(attrs, dict) or not isinstance(marks, list):
        raise GirdiHatasi("birim satiri: attrs ya da marks yok")
    dil, rol, ozet = attrs.get("dil"), veri.get("role"), veri.get("content_hash")
    if not isinstance(dil, str) or not isinstance(rol, str) or not isinstance(ozet, str):
        raise GirdiHatasi("birim satiri: dil, role ya da content_hash yok")
    diziler = arapca_dizi.isaretlerden(metin, marks)
    return Aday(
        anchor=capa,
        kitap=_kitap(capa),
        dil=dil,
        role=rol,
        ar_isaret=len(diziler),
        ar_kelime=sum(len(d.metin.split()) for d in diziler),
        sayi=sayi_say(metin),
        uzunluk=len(metin),
        content_hash=ozet,
    )


def dagit(boyutlar: Mapping[str, int], n: int) -> dict[str, int]:
    """`n` ornegi tabakalara esit paylasir; dolan tabakanin payi digerlerine gecer."""
    kota = dict.fromkeys(sorted(boyutlar), 0)
    kalan = min(n, sum(boyutlar.values()))
    acik = [k for k in kota if boyutlar[k] > 0]
    while kalan > 0 and acik:
        pay = max(1, kalan // len(acik))
        yeni: list[str] = []
        for anahtar in acik:
            al = min(pay, boyutlar[anahtar] - kota[anahtar], kalan)
            kota[anahtar] += al
            kalan -= al
            if boyutlar[anahtar] > kota[anahtar]:
                yeni.append(anahtar)
        acik = yeni
    return kota


def _tabakadan_sec(adaylar: Sequence[Aday], k: int, tohum: int, tabaka: str) -> list[Aday]:
    """Tabakadan `k` aday; kitaplara turlu dagitilir (kitap sirasi ve icindeki sira tohumlu)."""
    rng = random.Random(f"{tohum}:{tabaka}")
    kitaplar: dict[str, list[Aday]] = {}
    for aday in sorted(adaylar, key=lambda a: sort_key(parse(a.anchor))):
        kitaplar.setdefault(aday.kitap, []).append(aday)
    sirali_kitaplar = sorted(kitaplar)
    rng.shuffle(sirali_kitaplar)
    for kitap in sirali_kitaplar:
        rng.shuffle(kitaplar[kitap])
    secilen: list[Aday] = []
    sira = 0
    while len(secilen) < k:
        for kitap in sirali_kitaplar:
            if sira < len(kitaplar[kitap]) and len(secilen) < k:
                secilen.append(kitaplar[kitap][sira])
        sira += 1
    return secilen


def orneklem_sec(
    adaylar: Iterable[Aday], n: int = ORNEKLEM_BOYUTU, tohum: int = TOHUM
) -> list[Aday]:
    """Tabakali (dil, Arapca ve sayi yogunlugu), sabit tohumlu orneklem; capaya gore sirali."""
    tabakalar: dict[str, list[Aday]] = {}
    for aday in adaylar:
        tabakalar.setdefault(aday.tabaka, []).append(aday)
    kotalar = dagit({t: len(v) for t, v in tabakalar.items()}, n)
    secilen: list[Aday] = []
    for tabaka in sorted(tabakalar):
        if kotalar[tabaka] > 0:
            secilen.extend(_tabakadan_sec(tabakalar[tabaka], kotalar[tabaka], tohum, tabaka))
    secilen.sort(key=lambda a: sort_key(parse(a.anchor)))
    return secilen


def ornek_satiri(aday: Aday) -> dict[str, object]:
    """`ornek.jsonl` satiri: capa, tabaka ve sayimlar (metin yok)."""
    return {
        "anchor": aday.anchor,
        "ar_isaret": aday.ar_isaret,
        "ar_kelime": aday.ar_kelime,
        "content_hash": aday.content_hash,
        "dil": aday.dil,
        "kitap": aday.kitap,
        "role": aday.role,
        "sayi": aday.sayi,
        "tabaka": aday.tabaka,
        "uzunluk": aday.uzunluk,
    }


def ornek_baytlari(secilen: Iterable[Aday]) -> bytes:
    return b"".join(satir_baytlari(ornek_satiri(a)) for a in secilen)


def birimleri_oku(units: Path) -> Iterator[dict[str, object]]:
    for satir in satirlari_akit(units, "units"):
        yield satir.veri


def ornek_uret(units: Path, cikti: Path, n: int = ORNEKLEM_BOYUTU, tohum: int = TOHUM) -> int:
    """Staged `units.jsonl`'den orneklemi uretir ve `cikti`ya yazar; secilen sayisini dondurur."""
    adaylar = [a for v in birimleri_oku(units) if (a := aday_olustur(v)) is not None]
    secilen = orneklem_sec(adaylar, n, tohum)
    baytlar = ornek_baytlari(secilen)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    if not (cikti.is_file() and cikti.read_bytes() == baytlar):
        cikti.write_bytes(baytlar)
    return len(secilen)


def ornegi_oku(yol: Path) -> list[dict[str, Any]]:
    return [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s]


# --- Kur'an metni ve kontroller -----------------------------------------------------------


def tanzil_oku(uthmani_yolu: Path, basit_yolu: Path) -> list[tuple[int, int, str, str]]:
    """Iki Tanzil dosyasini kati bicimde okur: `(sure, ayet, uthmani, simple_clean)` x 6.236."""
    uthmani = ayristir(uthmani_yolu.read_bytes())
    basit = ayristir(basit_yolu.read_bytes())
    sonuc: list[tuple[int, int, str, str]] = []
    for u, b in zip(uthmani.ayetler, basit.ayetler, strict=True):
        if (u.sure, u.ayet) != (b.sure, b.ayet):
            raise GirdiHatasi("Tanzil dosyalarinin ayet sirasi ayni degil")
        sonuc.append((u.sure, u.ayet, u.metin, b.metin))
    return sonuc


def kontrol_uret(
    ayetler: Sequence[tuple[int, int, str, str]], tohum: int = TOHUM, adet: int = KONTROL_ADEDI
) -> list[dict[str, Any]]:
    """Tanzil metninden pozitif/negatif kontrol dizileri (bellekte; kaydedilmez).

    `uthmani_tam`, `basit_tam`, `yalin_tam` (harekesiz anahtar), `yalin_kismi` (ortadan 5 kelime) ve
    `negatif` (8 kelime, her biri baska bir ayetten rastgele). Hedef `(sure, ayet)` ya da `None`.
    """
    rng = random.Random(f"{tohum}:kontrol")
    uygun = [a for a in ayetler if len(a[3].split()) >= 8]
    secilen = rng.sample(uygun, adet)
    kontroller: list[dict[str, Any]] = []
    for sure, ayet, uthmani, basit in secilen:
        yalin = normalize_ar(basit).split()
        orta = max(0, (len(yalin) - 5) // 2)
        hedef = (sure, ayet)
        kontroller += [
            {"tur": "uthmani_tam", "hedef": hedef, "metin": uthmani},
            {"tur": "basit_tam", "hedef": hedef, "metin": basit},
            {"tur": "yalin_tam", "hedef": hedef, "metin": " ".join(yalin)},
            {"tur": "yalin_kismi", "hedef": hedef, "metin": " ".join(yalin[orta : orta + 5])},
        ]
    havuz = [normalize_ar(a[3]).split() for a in ayetler]
    for _ in range(adet):
        kelimeler = [rng.choice(rng.choice(havuz)) for _ in range(8)]
        kontroller.append({"tur": "negatif", "hedef": None, "metin": " ".join(kelimeler)})
    return kontroller


# --- bellek ve sayac yardimcilari ---------------------------------------------------------


def bellek_mb() -> tuple[float, float]:
    """`(simdiki, tepe)` calisma kumesi MB; Windows'ta psapi, digerlerinde `resource`."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Sayaclar(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        sayac = Sayaclar()
        sayac.cb = ctypes.sizeof(Sayaclar)
        kernel = ctypes.WinDLL("kernel32")
        kernel.GetCurrentProcess.restype = ctypes.c_void_p
        psapi = ctypes.WinDLL("psapi")
        psapi.GetProcessMemoryInfo.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(Sayaclar),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(sayac), sayac.cb)
        return sayac.WorkingSetSize / 1048576, sayac.PeakWorkingSetSize / 1048576
    import resource

    tepe = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return tepe, tepe


def _nicel(deger: float | None, basamak: int = 4) -> float | None:
    return None if deger is None else round(deger, basamak)


def yuzdelik(sirali: Sequence[float], oran: float) -> float | None:
    """En yakin sira yuzdeligi (sirali dizi); bos dizide `None`."""
    if not sirali:
        return None
    return sirali[min(len(sirali) - 1, max(0, round(oran * (len(sirali) - 1))))]


def dagilim(degerler: Iterable[float]) -> dict[str, Any]:
    """`n`, `min`, `p10`, `p25`, `p50`, `p75`, `p90`, `maks`, `ort` (bos girdide yalniz `n`)."""
    sirali = sorted(degerler)
    if not sirali:
        return {"n": 0}
    return {
        "n": len(sirali),
        "min": _nicel(sirali[0]),
        "p10": _nicel(yuzdelik(sirali, 0.10)),
        "p25": _nicel(yuzdelik(sirali, 0.25)),
        "p50": _nicel(yuzdelik(sirali, 0.50)),
        "p75": _nicel(yuzdelik(sirali, 0.75)),
        "p90": _nicel(yuzdelik(sirali, 0.90)),
        "maks": _nicel(sirali[-1]),
        "ort": _nicel(sum(sirali) / len(sirali)),
    }


# --- kosu ---------------------------------------------------------------------------------


def _eslesme_listesi(eslesmeler: Sequence[DiziEslesmesi]) -> list[list[Any]]:
    return [
        [e.bas, e.son, [list(a) for a in e.ayetler], _nicel(e.skor), e.kelime_sayisi]
        for e in eslesmeler
    ]


def _sarmalayici(
    arac: str, ayetler: Sequence[tuple[int, int, str, str]], calisma: Path
) -> DiziTespitcisi:
    from mutalaa_pipeline.enrich import arac_sarmalayicilari as s
    from mutalaa_pipeline.enrich.kuran_metni import ayetleri_kur

    del calisma  # arac dosya yazmaz (kuran_metni: bellekte jeton listesi)
    if arac != s.ARAC_ADI:
        raise GirdiHatasi("bu arac sarmalayicisi kaldirildi (K-52 madde 13: kazanan quran-toolkit)")
    kuran = ayetleri_kur(
        [(sure, ayet, uthmani) for sure, ayet, uthmani, _ in ayetler],
        [(sure, ayet, basit) for sure, ayet, _, basit in ayetler],
    )
    return s.ToolkitSarmalayici(kuran)


def _cagir(tespitci: DiziTespitcisi, metin: str) -> tuple[list[DiziEslesmesi], float, str | None]:
    """`(eslesmeler, saniye, hata_turu)`; istisnalar yakalanir (yalniz tur adi saklanir)."""
    t0 = time.perf_counter()
    try:
        sonuc = list(tespitci.tespit_et(metin))
        hata = None
    except Exception as e:
        sonuc, hata = [], type(e).__name__
    return sonuc, time.perf_counter() - t0, hata


def kos(
    arac: str,
    units: Path,
    ornek: Path,
    uthmani: Path,
    basit: Path,
    calisma: Path,
    cikti: Path,
) -> dict[str, Any]:
    """Tek araci orneklem ve kontroller uzerinde kosar; ham sonucu `cikti` JSON'una yazar."""
    from mutalaa_pipeline.enrich.arac_sarmalayicilari import (
        ARAC_ADI,
        ARAC_MODULU,
        ARAC_SURUMU,
        paket_surumu,
    )

    modul, dagitim, beklenen = ARAC_MODULU, ARAC_ADI, ARAC_SURUMU
    ham: dict[str, Any] = {"rapor_surumu": RAPOR_SURUMU, "arac": arac, "beklenen_surum": beklenen}
    ham["python"] = sys.version.split()[0]
    bellek_once = bellek_mb()
    try:
        ham["surum"] = paket_surumu(dagitim)
        ayetler = tanzil_oku(uthmani, basit)
        t0 = time.perf_counter()
        tespitci = _sarmalayici(arac, ayetler, calisma)
        ham["kurulum_sn"] = round(time.perf_counter() - t0, 3)
    except Exception as e:
        ham["kurulum_hatasi"] = type(e).__name__
        _yaz(cikti, ham)
        return ham
    del modul
    bellek_kurulum = bellek_mb()

    ornek_satirlari = ornegi_oku(ornek)
    secili = {s["anchor"] for s in ornek_satirlari}
    birimler: dict[str, dict[str, object]] = {
        str(v["anchor"]): v for v in birimleri_oku(units) if v.get("anchor") in secili
    }
    ham["dizi_modu"], ham["tam_modu"] = [], []
    for satir in ornek_satirlari:
        birim = birimler[satir["anchor"]]
        metin = str(birim["text"])
        marks = birim["marks"]
        if not isinstance(marks, list):
            raise GirdiHatasi("marks liste degil")
        for sira, dizi in enumerate(arapca_dizi.isaretlerden(metin, marks)):
            es, sn, hata = _cagir(tespitci, dizi.metin)
            ham["dizi_modu"].append(
                {
                    "a": satir["anchor"],
                    "i": sira,
                    "dil": satir["dil"],
                    "tur": dizi.tur,
                    "b": dizi.bas,
                    "cp": dizi.uzunluk,
                    "kelime": len(dizi.metin.split()),
                    "sn": round(sn, 5),
                    "es": _eslesme_listesi(es),
                    "hata": hata,
                }
            )
        es, sn, hata = _cagir(tespitci, metin)
        ham["tam_modu"].append(
            {
                "a": satir["anchor"],
                "dil": satir["dil"],
                "cp": len(metin),
                "sn": round(sn, 5),
                "isaretler": [
                    [d.bas, d.son, d.tur] for d in arapca_dizi.isaretlerden(metin, marks)
                ],
                "es": _eslesme_listesi(es),
                "hata": hata,
            }
        )
    ham["kontrol"] = []
    for kontrol in kontrol_uret(ayetler):
        es, sn, hata = _cagir(tespitci, kontrol["metin"])
        adaylar = sorted({tuple(a) for e in es for a in e.ayetler})
        ham["kontrol"].append(
            {
                "tur": kontrol["tur"],
                "hedef": list(kontrol["hedef"]) if kontrol["hedef"] is not None else None,
                "adaylar": [list(a) for a in adaylar],
                "es": len(es),
                "sn": round(sn, 5),
                "hata": hata,
            }
        )
    bellek_son = bellek_mb()
    ham["bellek_mb"] = {
        "baslangic_simdiki": round(bellek_once[0], 1),
        "kurulum_sonrasi_simdiki": round(bellek_kurulum[0], 1),
        "tepe": round(bellek_son[1], 1),
    }
    _yaz(cikti, ham)
    return ham


def _yaz(yol: Path, govde: Mapping[str, object]) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    metin = json.dumps(govde, ensure_ascii=True, sort_keys=True, indent=1) + "\n"
    yol.write_bytes(metin.encode("utf-8"))


# --- rapor --------------------------------------------------------------------------------

_SKOR_KOVALARI: Final = ((0.0, 0.5), (0.5, 0.7), (0.7, 0.85), (0.85, 0.95), (0.95, 1.0001))
_ADAY_KOVALARI: Final = (("0", 0, 0), ("1", 1, 1), ("2", 2, 2), ("3-5", 3, 5), ("6+", 6, 10**9))


def _ayet_kumesi(kayit: Mapping[str, Any]) -> frozenset[tuple[int, int]]:
    return frozenset((a[0], a[1]) for e in kayit["es"] for a in e[2])


def _oran(pay: int, payda: int) -> float | None:
    return None if payda == 0 else round(pay / payda, 4)


def _dizi_ozeti(kayitlar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    bulan = [k for k in kayitlar if _ayet_kumesi(k)]
    ozet: dict[str, Any] = {
        "dizi": len(kayitlar),
        "bulunan_dizi": len(bulan),
        "bulma_orani": _oran(len(bulan), len(kayitlar)),
        "hata": dict(Counter(k["hata"] for k in kayitlar if k["hata"])),
    }
    ozet["eslesme_sayisi"] = sum(len(k["es"]) for k in kayitlar)
    ozet["aday_ayet_dagilimi"] = {
        ad: sum(1 for k in kayitlar if alt <= len(_ayet_kumesi(k)) <= ust)
        for ad, alt, ust in _ADAY_KOVALARI
    }
    skorlar = [e[3] for k in kayitlar for e in k["es"] if e[3] is not None]
    ozet["skor"] = dagilim(skorlar)
    ozet["skor_yok_eslesme"] = sum(1 for k in kayitlar for e in k["es"] if e[3] is None)
    ozet["skor_kovalari"] = {
        f"[{alt},{min(ust, 1.0)}]": sum(1 for s in skorlar if alt <= s < ust)
        for alt, ust in _SKOR_KOVALARI
    }
    ozet["eslesen_kelime"] = dagilim(e[4] for k in kayitlar for e in k["es"] if e[4] is not None)
    ozet["kapsama"] = dagilim(
        min(1.0, (e[1] - e[0]) / k["cp"]) for k in kayitlar for e in k["es"] if k["cp"] > 0
    )
    return ozet


def _hiz(kayitlar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    saniyeler = sorted(k["sn"] for k in kayitlar)
    toplam_cp = sum(k["cp"] for k in kayitlar)
    return {
        "toplam_sn": round(sum(saniyeler), 3),
        "ms_p50": _nicel(1000 * (yuzdelik(saniyeler, 0.5) or 0.0), 3),
        "ms_p95": _nicel(1000 * (yuzdelik(saniyeler, 0.95) or 0.0), 3),
        "ms_maks": _nicel(1000 * (saniyeler[-1] if saniyeler else 0.0), 3),
        "sn_1000_kod_noktasi": _nicel(sum(saniyeler) / toplam_cp * 1000, 4) if toplam_cp else None,
    }


def _hizalanma(kayitlar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Tam paragraf kosusunda eslesmelerin `ar` isaretleriyle iliskisi."""
    sayac: Counter[str] = Counter()
    for k in kayitlar:
        for bas, son, *_ in k["es"]:
            kesisen = [i for i in k["isaretler"] if bas < i[1] and i[0] < son]
            if not kesisen:
                sayac["isaret_disi"] += 1
            elif any(i[0] <= bas and son <= i[1] for i in kesisen):
                sayac["isaret_icinde"] += 1
            else:
                sayac["kismen"] += 1
    toplam = sum(sayac.values())
    return {
        "eslesme": toplam,
        "isaret_icinde": sayac["isaret_icinde"],
        "kismen": sayac["kismen"],
        "isaret_disi": sayac["isaret_disi"],
        "isaret_disi_orani": _oran(sayac["isaret_disi"], toplam),
    }


def _kontrol_ozeti(kayitlar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    sonuc: dict[str, Any] = {}
    for tur in sorted({k["tur"] for k in kayitlar}):
        alt = [k for k in kayitlar if k["tur"] == tur]
        if tur == "negatif":
            sonuc[tur] = {
                "n": len(alt),
                "yanlis_bulma_orani": _oran(sum(1 for k in alt if k["adaylar"]), len(alt)),
                "hata": sum(1 for k in alt if k["hata"]),
            }
            continue
        hedefli = [tuple(k["hedef"]) in {tuple(a) for a in k["adaylar"]} for k in alt]
        yalniz = [{tuple(a) for a in k["adaylar"]} == {tuple(k["hedef"])} for k in alt]
        sonuc[tur] = {
            "n": len(alt),
            "hedefi_bulma_orani": _oran(sum(hedefli), len(alt)),
            "yalniz_hedef_orani": _oran(sum(yalniz), len(alt)),
            "ortalama_aday": _nicel(sum(len(k["adaylar"]) for k in alt) / len(alt), 3),
            "hata": sum(1 for k in alt if k["hata"]),
        }
    return sonuc


def _cagri_hizi(kayitlar: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    saniyeler = sorted(k["sn"] for k in kayitlar)
    return {
        "cagri": len(saniyeler),
        "toplam_sn": round(sum(saniyeler), 3),
        "ms_p50": _nicel(1000 * (yuzdelik(saniyeler, 0.5) or 0.0), 3),
        "ms_p95": _nicel(1000 * (yuzdelik(saniyeler, 0.95) or 0.0), 3),
    }


def dizi_yapisi(hamlar: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """`ar` araliklarinin dil ve tur bazinda kelime uzunlugu (araclarin en az kelime siniri)."""
    kaynak: list[Mapping[str, Any]] = next(
        (h["dizi_modu"] for h in hamlar.values() if "dizi_modu" in h), []
    )
    gruplar: dict[str, list[int]] = {}
    for k in kaynak:
        gruplar.setdefault(f"{k['dil']}|{k['tur']}", []).append(k["kelime"])
    return {
        grup: {
            "dizi": len(v),
            "kelime": dagilim(v),
            "kelime_3_altinda": sum(1 for x in v if x < 3),
            "kelime_4_altinda": sum(1 for x in v if x < 4),
        }
        for grup, v in sorted(gruplar.items())
    }


def arac_ozeti(ham: Mapping[str, Any]) -> dict[str, Any]:
    """Bir aracin ham kosu ciktisindan ozet bolumu."""
    if "kurulum_hatasi" in ham:
        return {"surum": ham.get("surum"), "kosulamadi": ham["kurulum_hatasi"]}
    dizi = ham["dizi_modu"]
    ozet: dict[str, Any] = {
        "surum": ham["surum"],
        "python": ham["python"],
        "kurulum_sn": ham["kurulum_sn"],
        "bellek_mb": ham["bellek_mb"],
        "dizi_modu": {**_dizi_ozeti(dizi), "hiz": _hiz(dizi)},
        "tam_modu": {
            "paragraf": len(ham["tam_modu"]),
            "hata": dict(Counter(k["hata"] for k in ham["tam_modu"] if k["hata"])),
            "eslesme_sayisi": sum(len(k["es"]) for k in ham["tam_modu"]),
            "bulunan_paragraf": sum(1 for k in ham["tam_modu"] if k["es"]),
            "hiz": _hiz(ham["tam_modu"]),
            "hizalanma": _hizalanma(ham["tam_modu"]),
        },
        "kontrol": _kontrol_ozeti(ham["kontrol"]),
        "kontrol_hiz": _cagri_hizi(ham["kontrol"]),
    }
    for ad, filtre in (
        ("dil", lambda k: k["dil"]),
        ("tur", lambda k: k["tur"]),
        ("dil_tur", lambda k: f"{k['dil']}|{k['tur']}"),
    ):
        gruplar: dict[str, list[Mapping[str, Any]]] = {}
        for k in dizi:
            gruplar.setdefault(filtre(k), []).append(k)
        ozet["dizi_modu"]["bulma_" + ad] = {
            g: {"dizi": len(v), "bulma_orani": _oran(sum(1 for k in v if _ayet_kumesi(k)), len(v))}
            for g, v in sorted(gruplar.items())
        }
    return ozet


def uyum_ozeti(hamlar: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Araclar arasi uyum: dizi modunda ayet kumeleri, tam modunda (paragraf, ayet) ciftleri."""
    calisan = {a: h for a, h in hamlar.items() if "dizi_modu" in h}
    if len(calisan) < 2:
        return {"yetersiz_arac": True}
    dizi_kumeleri: dict[str, dict[tuple[str, int], frozenset[tuple[int, int]]]] = {
        a: {(k["a"], k["i"]): _ayet_kumesi(k) for k in h["dizi_modu"]} for a, h in calisan.items()
    }
    anahtarlar = sorted(set.intersection(*(set(d) for d in dizi_kumeleri.values())))
    sonuc: dict[str, Any] = {"ortak_dizi": len(anahtarlar)}
    ciftler: dict[str, Any] = {}
    adlar = sorted(calisan)
    for i, a in enumerate(adlar):
        for b in adlar[i + 1 :]:
            ikisi, jaccard, kesisen, tam = 0, [], 0, 0
            for anahtar in anahtarlar:
                sa, sb = dizi_kumeleri[a][anahtar], dizi_kumeleri[b][anahtar]
                if sa or sb:
                    jaccard.append(len(sa & sb) / len(sa | sb))
                if sa and sb:
                    ikisi += 1
                    kesisen += bool(sa & sb)
                    tam += sa == sb
            ciftler[f"{a}+{b}"] = {
                "ikisi_de_buldu": ikisi,
                "kesisim_orani": _oran(kesisen, ikisi),
                "tam_ayni_kume_orani": _oran(tam, ikisi),
                "jaccard_ortalama": _nicel(sum(jaccard) / len(jaccard)) if jaccard else None,
                "en_az_biri_buldu": len(jaccard),
            }
    sonuc["dizi_modu_ciftler"] = ciftler
    kume_sayaci: Counter[str] = Counter()
    uzlasma: Counter[str] = Counter()
    for anahtar in anahtarlar:
        bulanlar = [a for a in adlar if dizi_kumeleri[a][anahtar]]
        kume_sayaci["+".join(bulanlar) if bulanlar else "hicbiri"] += 1
        if len(bulanlar) >= 2:
            kumeler = [dizi_kumeleri[a][anahtar] for a in bulanlar]
            if all(k == kumeler[0] for k in kumeler):
                uzlasma["tam"] += 1
            elif frozenset.intersection(*kumeler):
                uzlasma["ortak_ayet_var"] += 1
            else:
                uzlasma["celisen"] += 1
    sonuc["bulan_arac_kumeleri"] = dict(sorted(kume_sayaci.items()))
    sonuc["birden_cok_aracin_buldugu_diziler"] = dict(sorted(uzlasma.items()))
    tam_cift: dict[str, Any] = {}
    paragraf: dict[str, dict[str, frozenset[tuple[str, int, int]]]] = {}
    for a, h in calisan.items():
        paragraf[a] = {
            k["a"]: frozenset((k["a"], s, ay) for s, ay in _ayet_kumesi(k)) for k in h["tam_modu"]
        }
    for i, a in enumerate(adlar):
        for b in adlar[i + 1 :]:
            birlesim = kesisim = 0
            for capa in sorted(set(paragraf[a]) & set(paragraf[b])):
                birlesim += len(paragraf[a][capa] | paragraf[b][capa])
                kesisim += len(paragraf[a][capa] & paragraf[b][capa])
            tam_cift[f"{a}+{b}"] = {
                "birlesim_cift": birlesim,
                "kesisim_cift": kesisim,
                "jaccard": _oran(kesisim, birlesim),
            }
    sonuc["tam_modu_paragraf_ayet_ciftleri"] = tam_cift
    return sonuc


def _yoklama(
    calisan: Mapping[str, Mapping[str, Any]], tur: str, en_az_kelime: int
) -> dict[str, Any]:
    satir: dict[str, Any] = {}
    ortak: set[tuple[str, int]] | None = None
    diziler: set[tuple[str, int]] = set()
    en_az_biri: set[tuple[str, int]] = set()
    for arac, h in sorted(calisan.items()):
        alt = {
            (k["a"], k["i"]): k
            for k in h["dizi_modu"]
            if k["tur"] == tur and k["kelime"] >= en_az_kelime
        }
        bulan = {a for a, k in alt.items() if _ayet_kumesi(k)}
        satir[arac] = {"dizi": len(alt), "bulan": len(bulan), "oran": _oran(len(bulan), len(alt))}
        ortak = bulan if ortak is None else ortak & bulan
        diziler |= set(alt)
        en_az_biri |= bulan
    satir["en_az_bir_arac"] = {
        "bulan": len(en_az_biri),
        "oran": _oran(len(en_az_biri), len(diziler)),
    }
    satir["butun_araclar"] = {
        "bulan": len(ortak or ()),
        "oran": _oran(len(ortak or ()), len(diziler)),
    }
    return satir


def alinti_yoklama(hamlar: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """`alinti` (`﹛…|﹜`) ve `blok` (`~…|@`) araliklarinda araclarin bulma orani (BÇ-68 yoklamasi).

    Her tur icin `tumu` ve araclarin en az kelime sinirini karsilayan `kelime_4_ve_ustu` alt kumesi.
    """
    calisan = {a: h for a, h in hamlar.items() if "dizi_modu" in h}
    return {
        tur: {"tumu": _yoklama(calisan, tur, 0), "kelime_4_ve_ustu": _yoklama(calisan, tur, 4)}
        for tur in ("alinti", "blok")
    }


def gramer_olcumu(birimler: Iterable[Mapping[str, object]]) -> dict[str, Any]:
    """Arac bagimsiz acik atif gramerinin orneklemdeki sayimlari ve `ar` isaret kapsami."""
    sinyal: Counter[str] = Counter()
    atilan: Counter[str] = Counter()
    paragraf_atifli = paragraf = 0
    isaret_disi = tr_paragraf = bos_isaret = 0
    for v in birimler:
        metin = str(v["text"])
        marks = v["marks"]
        if not isinstance(marks, list):
            raise GirdiHatasi("marks liste degil")
        paragraf += 1
        bos_isaret += sum(1 for m in marks if m.get("t") == "ar" and m.get("s") == m.get("e"))
        sonuc = atif_gramer.ayristir(metin, None)
        paragraf_atifli += bool(sonuc.atiflar)
        sinyal.update(a.sinyal for a in sonuc.atiflar)
        atilan.update(sonuc.atilan)
        attrs = v["attrs"]
        if isinstance(attrs, dict) and attrs.get("dil") == "tr":
            tr_paragraf += 1
            isaret_disi += bool(arapca_dizi.isaret_disi_diziler(metin, marks))
    return {
        "sure_adi_tablosu": "yok; yalniz adsiz parantezli sayisal bicimler",
        "paragraf": paragraf,
        "bos_ar_isareti_atlandi": bos_isaret,
        "atifli_paragraf": paragraf_atifli,
        "atif_sinyalleri": dict(sorted(sinyal.items())),
        "atilan": dict(sorted(atilan.items())),
        "tr_paragraf": tr_paragraf,
        "tr_paragrafta_isaret_disi_arap_harfli_dizi": isaret_disi,
    }


def _tabaka_sayimi(ornek: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "n": len(ornek),
        "tohum": TOHUM,
        "tabaka": dict(sorted(Counter(s["tabaka"] for s in ornek).items())),
        "dil": dict(sorted(Counter(s["dil"] for s in ornek).items())),
        "rol": dict(sorted(Counter(s["role"] for s in ornek).items())),
        "kitap_sayisi": len({s["kitap"] for s in ornek}),
        "ar_isaret_toplam": sum(s["ar_isaret"] for s in ornek),
        "ar_isaretli_paragraf": sum(1 for s in ornek if s["ar_isaret"] > 0),
        "ornek_sha256": None,
    }


def rapor_uret(ham_klasoru: Path, ornek: Path, units: Path, cikti: Path) -> dict[str, Any]:
    """Ham kosu ciktilarini birlestirir ve `a20-atif-araclari.json` raporunu yazar."""
    hamlar: dict[str, dict[str, Any]] = {}
    for arac in ARACLAR:
        yol = ham_klasoru / f"{arac}.json"
        if yol.is_file():
            hamlar[arac] = json.loads(yol.read_text(encoding="utf-8"))
    ornek_satirlari = ornegi_oku(ornek)
    secili = {s["anchor"] for s in ornek_satirlari}
    birimler = [v for v in birimleri_oku(units) if v.get("anchor") in secili]
    sayim = _tabaka_sayimi(ornek_satirlari)
    sayim["ornek_sha256"] = hashlib.sha256(ornek.read_bytes()).hexdigest()
    rapor: dict[str, Any] = {
        "rapor_surumu": RAPOR_SURUMU,
        "asama": "A20.7a",
        "etiket_durumu": "etiketlenmemis",
        "etiket_notu": (
            "Risale altin seti etiketi (I-13) gelmedi: kesinlik, duyarlilik ve F1 HESAPLANMADI. "
            "Asagidaki sayilar araclar arasi uyum, hiz, bellek, hata, aday ve skor dagilimi, "
            "ar isaretleriyle hizalanma ve Tanzil metninden uretilen kontrollerdir."
        ),
        "orneklem": sayim,
        "kaynaklar": {
            "kuran_metni": "Tanzil Uthmani ve Simple Clean 1.1 (data/gelen/tanzil-*/2026-11-13)",
            "birimler": "staged risale-rnk-metin anchor ciktisi",
        },
        "araclar": {a: arac_ozeti(h) for a, h in sorted(hamlar.items())},
        "uyum": uyum_ozeti(hamlar),
        "alinti_ve_blok_yoklamasi": alinti_yoklama(hamlar),
        "dizi_yapisi": dizi_yapisi(hamlar),
        "acik_atif_gramer": gramer_olcumu(birimler),
        "kosulmayan_araclar": [a for a in ARACLAR if a not in hamlar],
    }
    _yaz(cikti, rapor)
    return rapor


# --- komut satiri -------------------------------------------------------------------------


def _argumanlar(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="arac_olcumu", description=__doc__.split("\n")[0])
    alt = p.add_subparsers(dest="komut", required=True)
    o = alt.add_parser("ornek", help="420 paragraflik tabakali orneklemi uretir")
    o.add_argument("--units", type=Path, required=True)
    o.add_argument("--cikti", type=Path, required=True)
    o.add_argument("--n", type=int, default=ORNEKLEM_BOYUTU)
    o.add_argument("--tohum", type=int, default=TOHUM)
    k = alt.add_parser("kos", help="tek araci kosar (uv run --with <paket>==<surum> ile)")
    k.add_argument("--arac", choices=ARACLAR, required=True)
    k.add_argument("--units", type=Path, required=True)
    k.add_argument("--ornek", type=Path, required=True)
    k.add_argument("--tanzil-uthmani", type=Path, required=True)
    k.add_argument("--tanzil-simple", type=Path, required=True)
    k.add_argument("--calisma", type=Path, required=True)
    k.add_argument("--cikti", type=Path, required=True)
    r = alt.add_parser("rapor", help="ham kosulari birlestirip raporu yazar")
    r.add_argument("--ham", type=Path, required=True)
    r.add_argument("--ornek", type=Path, required=True)
    r.add_argument("--units", type=Path, required=True)
    r.add_argument("--cikti", type=Path, required=True)
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Cikis kodlari: `0` basarili, `2` girdi hatasi (Icerik hatti §4)."""
    a = _argumanlar(argv)
    try:
        if a.komut == "ornek":
            sayi = ornek_uret(a.units, a.cikti, a.n, a.tohum)
            print(f"ornek: {sayi} paragraf -> {a.cikti.name}")
        elif a.komut == "kos":
            ham = kos(
                a.arac, a.units, a.ornek, a.tanzil_uthmani, a.tanzil_simple, a.calisma, a.cikti
            )
            durum = ham.get("kurulum_hatasi", "tamam")
            print(f"kos: {a.arac} {ham.get('surum')} durum={durum}")
        else:
            rapor = rapor_uret(a.ham, a.ornek, a.units, a.cikti)
            print(f"rapor: {len(rapor['araclar'])} arac -> {a.cikti.name}")
    except GirdiHatasi as hata:
        print(f"hata: {hata}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
