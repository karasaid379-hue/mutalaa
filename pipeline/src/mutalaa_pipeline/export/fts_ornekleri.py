"""Arama bolum 3 sorgu tablosunun Arapca sorgulari ile `fts-query/query.jsonl` satirlari (A12.4).

`mutalaa export test-vectors --fts-ornekleri`: `docs/03-veri/05-arama-fts5.md` bolum 3
sorgu tablosunun (`| Sorgu | MATCH ifadesi |`) iki Arapca sorgusunu BAYT BAYT alir ve
`shared/test-vectors/fts-query/query.jsonl` dosyasina iki satir yazar:

    fq-ar-0001  Arapca terim: sorgu = tablodaki Arapca terim (kod bicimi temizlenmis hucre)
                match `ar_norm : "<normalize_ar>"`, tri `"<normalize_ar>"`
    fq-ar-0002  kok suzgeci (KOK_ONEKI) + Arapca kok: kok `normalize_ar(kok)`, baska alan bos

Beklenen deger `normalize_ar` ile (Python referansi) hesaplanir ve belgedeki MATCH hucresiyle
capraz denetlenir: ilk satirin hucresi bir kod parcasi olarak `ar_norm : "<normalize_ar>"`
tasimali. Uyusmazlikta `GirdiHatasi` (cikis 2) verilir ve durulur; beklenen deger
uydurulmaz, belge duzeltilmez.

Dosyanin `fq-0NNN` satirlari bayt bayt korunur; `fq-ar-` satirlari her calistirmada atilip
yeniden kurulur ve sona eklenir (kimlik sirasi: `fq-0` < `fq-ar-`). Yazim UTF-8, LF, BOM yok,
ham UTF-8 (`\\u` kacisi yok; `fts-query/query.jsonl` icin kural kapali). Bu modul
`test_vectors.py`in disindadir: oradaki "normallestiriciyi ice aktarmaz" ilkesi korunur.
"""

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi, ayni_mi, kati_json, utf8_oku, yaz
from mutalaa_pipeline.normalize import normalize_ar

BELGE_YOLU: Final = "docs/03-veri/05-arama-fts5.md"
VEKTOR_YOLU: Final = "shared/test-vectors/fts-query/query.jsonl"
ARAPCA_ONEKI: Final = "fq-ar-"
KOK_ONEKI: Final = "k\u00f6k:"  # belgedeki yazim (NFC)
NOT_METNI: Final = "Arama 3 tablosu, belgeden programla al\u0131nd\u0131 (A12.4)"

_TABLO_BASI: Final = re.compile(r"^\| Sorgu \| MATCH ifadesi \|$")
_TABLO_AYIRICISI: Final = re.compile(r"^\|(?: ?-+ ?\|)+$")
_TABLO_SATIRI: Final = re.compile(r"^\| `(?P<sorgu>[^`]+)` \| (?P<ifade>.+) \|$")


@dataclass(frozen=True)
class BelgeSatiri:
    """Belgedeki sorgu tablosunun bir satiri (`sorgu` kod bicimi temizlenmis hucre)."""

    sorgu: str
    ifade: str  # MATCH ifadesi hucresi, aynen
    belge_satiri: int  # 1 tabanli


def _arapca(metin: str) -> bool:
    """Bos olmayan ve yalniz Arapca harf/isaretlerden olusan metin."""
    if metin == "":
        return False
    for harf in metin:
        try:
            if not unicodedata.name(harf).startswith("ARABIC"):
                return False
        except ValueError:
            return False
    return True


def tablo_oku(kok: Path) -> list[BelgeSatiri]:
    """Arama sorgu tablosu (bolum 3) sorgu tablosunu okur; bicim bozuksa `GirdiHatasi`."""
    yol = kok / BELGE_YOLU
    if not yol.is_file():
        raise GirdiHatasi(f"{BELGE_YOLU} yok (Arapca sorgular belgeden okunur)")
    satirlar = [s.removesuffix("\r") for s in utf8_oku(yol, BELGE_YOLU).split("\n")]
    basliklar = [i for i, s in enumerate(satirlar) if _TABLO_BASI.match(s)]
    if len(basliklar) != 1:
        raise GirdiHatasi(
            f"{BELGE_YOLU}: sorgu tablosu basligi (Sorgu, MATCH ifadesi) tam bir kez bulunmali"
            f" (bulunan {len(basliklar)})"
        )
    bas = basliklar[0]
    if bas + 1 >= len(satirlar) or _TABLO_AYIRICISI.match(satirlar[bas + 1]) is None:
        raise GirdiHatasi(f"{BELGE_YOLU}: satir {bas + 2}: tablo ayirici satiri bekleniyordu")
    tablo: list[BelgeSatiri] = []
    for i in range(bas + 2, len(satirlar)):
        satir = satirlar[i]
        if not satir.startswith("|"):
            break
        eslesme = _TABLO_SATIRI.match(satir)
        if eslesme is None:
            raise GirdiHatasi(f"{BELGE_YOLU}: satir {i + 1}: tablo satiri bicimi gecersiz")
        tablo.append(BelgeSatiri(eslesme.group("sorgu"), eslesme.group("ifade"), i + 1))
    if not tablo:
        raise GirdiHatasi(f"{BELGE_YOLU}: sorgu tablosunda satir yok")
    return tablo


def _tek(adaylar: list[BelgeSatiri], ad: str) -> BelgeSatiri:
    if len(adaylar) != 1:
        raise GirdiHatasi(
            f"{BELGE_YOLU}: sorgu tablosunda {ad} satiri tam bir kez bulunmali"
            f" (bulunan {len(adaylar)})"
        )
    return adaylar[0]


def satirlari_kur(tablo: list[BelgeSatiri]) -> list[dict[str, object]]:
    """Tablodan `fq-ar-0001` ve `fq-ar-0002` vektor nesnelerini kurar (anahtar sirasi sabit)."""
    terim = _tek([t for t in tablo if _arapca(t.sorgu)], "Arapca terim")
    kok = _tek(
        [
            t
            for t in tablo
            if t.sorgu.startswith(KOK_ONEKI) and _arapca(t.sorgu.removeprefix(KOK_ONEKI))
        ],
        f"{KOK_ONEKI} Arapca kok",
    )

    terim_norm = normalize_ar(terim.sorgu)
    beklenen_match = f'ar_norm : "{terim_norm}"'
    if beklenen_match not in re.findall(r"`([^`]+)`", terim.ifade):
        raise GirdiHatasi(
            f"{BELGE_YOLU}: satir {terim.belge_satiri}: MATCH hucresi normalize_ar ciktisini"
            " kod parcasi olarak tasimiyor; beklenen deger uydurulmaz, belge duzeltilmez"
            " (/belge-esitle ya da /karar)"
        )
    kok_norm = normalize_ar(kok.sorgu.removeprefix(KOK_ONEKI))
    if kok_norm == "":
        raise GirdiHatasi(f"{BELGE_YOLU}: satir {kok.belge_satiri}: kok normalize sonrasi bos")

    def beklenen(**alanlar: object) -> dict[str, object]:
        varsayilan: dict[str, object] = {
            "address": None,
            "match": None,
            "tri": None,
            "narrow": [],
            "kok": None,
            "kaynak": None,
            "ignored": [],
            "tooLong": False,
        }
        return {**varsayilan, **alanlar}

    return [
        {
            "id": f"{ARAPCA_ONEKI}0001",
            "input": {"query": terim.sorgu},
            "expected": beklenen(match=beklenen_match, tri=f'"{terim_norm}"'),
            "note": NOT_METNI,
        },
        {
            "id": f"{ARAPCA_ONEKI}0002",
            "input": {"query": kok.sorgu},
            "expected": beklenen(kok=kok_norm),
            "note": NOT_METNI,
        },
    ]


def _satir_yaz(nesne: dict[str, object]) -> str:
    return json.dumps(nesne, ensure_ascii=False, separators=(",", ":"))


def dosya_metni(kok: Path) -> str:
    """Mevcut `fq-0NNN` satirlari aynen + yeniden kurulan `fq-ar-` satirlari."""
    metin = utf8_oku(kok / VEKTOR_YOLU, VEKTOR_YOLU) if (kok / VEKTOR_YOLU).is_file() else None
    if metin is None:
        raise GirdiHatasi(f"{VEKTOR_YOLU} yok (fq-ar- satirlari mevcut dosyaya eklenir)")
    if metin.startswith(chr(0xFEFF)) or "\r" in metin:
        raise GirdiHatasi(f"{VEKTOR_YOLU}: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    satirlar = metin.split("\n")
    if satirlar[-1] != "":
        raise GirdiHatasi(f"{VEKTOR_YOLU}: dosya sonunda satir sonu yok")
    satirlar.pop()
    kalan: list[str] = []
    for no, satir in enumerate(satirlar, start=1):
        try:
            veri = kati_json(satir)
        except GirdiHatasi as hata:
            raise GirdiHatasi(f"{VEKTOR_YOLU}:{no}: {hata}") from hata
        kimlik = veri.get("id") if isinstance(veri, dict) else None
        if not isinstance(kimlik, str):
            raise GirdiHatasi(f"{VEKTOR_YOLU}:{no}: id (metin) zorunlu")
        if kimlik.startswith(ARAPCA_ONEKI):
            continue
        if kimlik >= ARAPCA_ONEKI:
            raise GirdiHatasi(
                f"{VEKTOR_YOLU}:{no}: id '{ARAPCA_ONEKI}' oneginden once siralanmali"
                " (fq-ar- satirlari sona eklenir)"
            )
        kalan.append(satir)
    yeni = [_satir_yaz(n) for n in satirlari_kur(tablo_oku(kok))]
    return "".join(s + "\n" for s in (*kalan, *yeni))


def uret(kok: Path) -> bool:
    """`fq-ar-` satirlarini yazar; dosya degistiyse True."""
    return yaz(kok, VEKTOR_YOLU, dosya_metni(kok))


def denetle(kok: Path) -> list[str]:
    """Yazmadan uretir ve diskle bayt bayt karsilastirir; farkliysa tek iletilik liste."""
    if ayni_mi(kok, VEKTOR_YOLU, dosya_metni(kok)):
        return []
    return [f"{VEKTOR_YOLU} (fq-ar- satirlari belgeyle uyusmuyor)"]
