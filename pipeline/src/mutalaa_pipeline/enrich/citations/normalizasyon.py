"""Iktibas esleme normalizasyonu (Iktibas tespiti §4): saf islevler.

A05 `normalize_ar` kurallari (hareke, ustte kucuk elif, Kur'an isaretleri ve tatvil silinir;
elif bicimleri tek elif, ya -> ye, te marbuta -> he, vav ve ye uzerindeki hemze duz vav ve ye) +
iki esleme adimi: yalin hemze (U+0621) silinir; noktalama ve rakam bosluga doner. Sonuc yalniz
bellekteki esleme anahtaridir; kanonik metin degismez (K-26).

`belirtecler` kaynak metnin kod noktasi ofsetlerini korur: ham sozcuk (bosluklarla ayrilan dizi)
ayri ayri normalize edilir ve her anahtar, geldigi ham sozcugun `[bas, son)` araligini tasir.
"""

import re
import unicodedata
from dataclasses import dataclass
from typing import Final

from mutalaa_pipeline.normalize import normalize_ar

HEMZE: Final = "\N{ARABIC LETTER HAMZA}"
_HAM_SOZCUK: Final = re.compile(r"[^\s]+")


@dataclass(frozen=True)
class Belirtec:
    anahtar: str
    bas: int  # ham sozcugun kod noktasi baslangici (kaynak metinde)
    son: int  # yari acik bitis


def _rakam_bosluk(metin: str) -> str:
    return "".join(" " if unicodedata.category(k) == "Nd" else k for k in metin)


def anahtarlar(sozcuk: str) -> list[str]:
    """Tek ham sozcuk (ya da bir QAC `norm` degeri) -> esleme anahtarlari (genelde bir tane)."""
    duz = _rakam_bosluk(normalize_ar(sozcuk).replace(HEMZE, ""))
    return duz.split()


def belirtecler(metin: str) -> list[Belirtec]:
    """Metnin esleme belirtecleri (kaynak ofsetli); anahtari bos kalan sozcuk atlanir."""
    sonuc: list[Belirtec] = []
    for m in _HAM_SOZCUK.finditer(metin):
        sonuc.extend(Belirtec(a, m.start(), m.end()) for a in anahtarlar(m.group()))
    return sonuc


def anahtar_dizisi(metin: str) -> list[str]:
    return [b.anahtar for b in belirtecler(metin)]
