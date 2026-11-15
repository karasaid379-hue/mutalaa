"""Sozluk OCR metinlerinde baslik soz arama (A20.6, K-52 madde 9): `{sozluk, bulundu, satir_no}`.

Uc sozluk (`lugat-redhouse-1890`, `lugat-kamus-i-turki`, `lugat-naci`) `_djvu.txt` OCR dosyasi
olarak gelir (guvenilmeyen veri; yalniz bayt olarak okunur). Arama SONUCU yalniz konumdur:
OCR metni, baslik soz ve satir icerigi hicbir cikti, rapor ya da gunluge yazilmaz.

Yontem `satir-basi-ilk-jeton-1` (olcumle secildi; 100 baslik soz, siklik tabakali ornek):
her satirin bastaki bosluk, nokta, tire, yildiz, tirnak, `[`, `(` ve rakamlar atildiktan sonraki ilk
harf jetonu madde basi adayidir; anahtar = kucuk harf (Turkce acik esleme), kesme ve tire
silinmis, genis katlama (sapka ve ust isaretler atilmis). Baslik soz ayni anahtarla aranir;
`satir_no` ilk eslesen satirin 1 tabanli numarasidir. Gercek veride olculen (13 Kasim 2026; ornek
yuzdesi, parantezde kontrol): Kamus-i Turki Latin kopya 45 (2), Redhouse 2 (1), Naci 0 (0); 21.486
maddenin tamaminda 9.002, 831 ve 144 isabet. Redhouse'ta Latin yazim aktarimi OCR'da bozuk, Naci'nin
OCR metni Arap harflidir (Latin baslik soz bulunamaz). Madde basi yerine "satirin herhangi bir
jetonu" ya da "ilk uc jeton" da olculdu: kontrol (karistirilmis harfli sozler) payi birlikte
yukseldigi icin secilmedi.

Guvenilirlik her kosuda yeniden olculur (`olcum`): ornek isabeti % 30'un altindaysa ya da kontrol
isabetinden en az % 20 puan yuksek degilse sozluk "guvenilmez" bayragini alir; sonuc yine yazilir.
Isabet, madde basi OLDUGUNU kanitlamaz (devam satiri da olabilir): editor basvurusudur.
"""

import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import lower_turkish
from mutalaa_pipeline.normalize.turkish import fold_wide

SOZLUKLER: Final = ("lugat-redhouse-1890", "lugat-kamus-i-turki", "lugat-naci")
OCR_SONEKI: Final = "_djvu.txt"
YONTEM: Final = "satir-basi-ilk-jeton-1"
EN_BUYUK_BAYT: Final = 32 << 20
ORNEK_SAYISI: Final = 100
TABAKA_SAYISI: Final = 10
TOHUM: Final = 20261113
GUVEN_ESIGI_YUZDE: Final = 30
KONTROL_FARKI_YUZDE: Final = 20

_BASTAKI_ISARETLER: Final = " \t.-*\"'[(0123456789"
_KESME2: Final = chr(0x2019)
_JETON: Final = re.compile(rf"[^\W0-9_]+(?:['{_KESME2}\-][^\W0-9_]+)*")
_SILINECEK: Final = str.maketrans("", "", f"'{_KESME2}-")


def anahtar(sozcuk: str) -> str:
    """Eslestirme anahtari: Turkce kucuk harf, kesme ve tire silinmis, genis katlama."""
    return fold_wide(lower_turkish(sozcuk).translate(_SILINECEK))


@dataclass(frozen=True)
class SozlukIndeksi:
    """Bir sozlugun madde basi indeksi: anahtar -> ilk satir (1 tabanli)."""

    sozluk: str
    satir_sayisi: int
    ilk_satir: Mapping[str, int]


def satir_sayisi(veri: bytes) -> int:
    """LF ile biten satirlarin sayisi (son satir LF'siz ise o da sayilir)."""
    if not veri:
        return 0
    return veri.count(b"\n") + (0 if veri.endswith(b"\n") else 1)


def indeks_kur(sozluk: str, veri: bytes) -> SozlukIndeksi:
    """OCR baytlarindan madde basi indeksi; UTF-8 olmayan ya da cok buyuk girdi `GirdiHatasi`."""
    if len(veri) > EN_BUYUK_BAYT:
        raise GirdiHatasi(f"{sozluk}: OCR dosyasi cok buyuk ({len(veri)} bayt)")
    try:
        metin = veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{sozluk}: OCR dosyasi UTF-8 degil") from None
    ilk: dict[str, int] = {}
    for no, satir in enumerate(metin.split("\n"), start=1):
        eslesme = _JETON.match(satir.rstrip("\r").lstrip(_BASTAKI_ISARETLER))
        if eslesme is not None:
            ilk.setdefault(anahtar(eslesme.group()), no)
    return SozlukIndeksi(sozluk, satir_sayisi(veri), ilk)


def ara(indeks: SozlukIndeksi, basliksoz: str) -> dict[str, object]:
    """`{sozluk, bulundu, satir_no}`; bulunamazsa `satir_no` null. Metin dondurmez."""
    anahtari = anahtar(basliksoz)
    satir = indeks.ilk_satir.get(anahtari) if anahtari else None
    return {"sozluk": indeks.sozluk, "bulundu": satir is not None, "satir_no": satir}


def _karistir(sozcuk: str, rnd: random.Random) -> str:
    harfler = list(sozcuk)
    rnd.shuffle(harfler)
    return "".join(harfler)


def ornek_sec(sirali: Sequence[str]) -> tuple[list[str], list[str]]:
    """Siklik sirali baslik soz listesinden tabakali ornek ve ayni sayida kontrol dizisi.

    Liste, siklik azalan (esitlikte alfabetik) sirada olmali; ona esit buyuklukte `TABAKA_SAYISI`
    rutbe dilimine bolunur, her dilimden sabit tohumla `ORNEK_SAYISI / TABAKA_SAYISI` soz secilir.
    Kontrol: secilen sozlerin harfleri karistirilmis hali (sans eslesmesi tabani).
    """
    rnd = random.Random(TOHUM)
    n = len(sirali)
    ornek: list[str] = []
    for t in range(TABAKA_SAYISI):
        dilim = list(sirali[t * n // TABAKA_SAYISI : (t + 1) * n // TABAKA_SAYISI])
        ornek += rnd.sample(dilim, min(ORNEK_SAYISI // TABAKA_SAYISI, len(dilim)))
    kontrol = [_karistir(s, rnd) for s in ornek]
    return ornek, kontrol


def olcum(indeksler: Sequence[SozlukIndeksi], sirali: Sequence[str]) -> dict[str, object]:
    """Ornek isabet olcumu (YALNIZ sayi): sozluk basina `ornek`, `bulundu`, `oran_yuzde`,
    `kontrol_bulundu`, `tabaka_bulundu` ve `guvenilmez` (+ `neden`)."""
    ornek, kontrol = ornek_sec(sirali)
    n = len(ornek)
    sozlukler: dict[str, object] = {}
    for indeks in indeksler:
        bulundu = [bool(ara(indeks, s)["bulundu"]) for s in ornek]
        kontrol_bulundu = sum(bool(ara(indeks, s)["bulundu"]) for s in kontrol)
        toplam = sum(bulundu)
        oran = toplam * 100 // n if n else 0
        kontrol_oran = kontrol_bulundu * 100 // n if n else 0
        neden = ""
        if oran < GUVEN_ESIGI_YUZDE:
            neden = "oran-dusuk"
        elif oran - kontrol_oran < KONTROL_FARKI_YUZDE:
            neden = "kontrolden-ayirt-edilemiyor"
        dilim = max(n // TABAKA_SAYISI, 1)
        sozlukler[indeks.sozluk] = {
            "ornek": n,
            "bulundu": toplam,
            "oran_yuzde": oran,
            "kontrol_bulundu": kontrol_bulundu,
            "tabaka_bulundu": [sum(bulundu[i : i + dilim]) for i in range(0, n, dilim)],
            "guvenilmez": neden != "",
            "neden": neden,
        }
    return {
        "tur": "lugat-sozluk-isabet",
        "yontem": YONTEM,
        "tohum": TOHUM,
        "tabaka": TABAKA_SAYISI,
        "guven_esigi_yuzde": GUVEN_ESIGI_YUZDE,
        "kontrol_farki_yuzde": KONTROL_FARKI_YUZDE,
        "sozlukler": sozlukler,
    }


def guvenilmezler(olcumu: Mapping[str, object]) -> list[str]:
    """Olcumde `guvenilmez` bayragi alan sozluklerin kimlikleri (SOZLUKLER sirasinda)."""
    tablo = olcumu["sozlukler"]
    if not isinstance(tablo, dict):
        raise GirdiHatasi("sozluk olcumu: sozlukler nesne degil")
    return [s for s in SOZLUKLER if isinstance(tablo.get(s), dict) and tablo[s]["guvenilmez"]]
