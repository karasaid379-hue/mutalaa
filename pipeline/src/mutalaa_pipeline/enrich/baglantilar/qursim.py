"""QurSim CSV okuyucusu (K-51 madde 12): yalniz `SS`, `SV`, `TS`, `TV` ve `Label`.

Dosya `data/gelen/qursim/<tarih>/QurSim_filtered.csv` (sutunlar: dizin, `ID`, `SS`, `SV`,
`Verse1`, `TS`, `TV`, `Verse2`, `Label`). `Verse1` ve `Verse2` Arapca metin sutunlaridir:
bu modul onlari OKUMAZ, SAKLAMAZ ve LOGLAMAZ; satirdan yalniz bes sutun sirasiyla alinir,
satir hemen birakilir. Girdi guvenilmeyen veridir: `csv` modulu, `encoding="utf-8"`, capalar
6.236 ayetlik kumeyle dogrulanir, gecersiz satir sayaca yazilir ve atlanir.

`Label` anlami dogrulanamadi: deger yalniz ham olarak saklanir (`evidence.label`); esik ya da
puan Label'a baglanmaz. Cift, kuresel ayet sirasiyla `(lo, hi)` biciminde normallestirilir
(`SS:SV` ile `TS:TV` sirasi onemsizdir); yinelenen ciftte ilk satir (dosya sirasi) tutulur.
"""

import csv
import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi

SUTUNLAR: Final = ("SS", "SV", "TS", "TV", "Label")
SAYI: Final = re.compile(r"[1-9][0-9]{0,2}")
LABEL: Final = re.compile(r"[0-9]{1,3}")
YINELENEN: Final = "yinelenen_cift"
HATA_NEDENLERI: Final = (
    "sutun_sayisi",
    "sayi_gecersiz",
    "capa_gecersiz",
    "kendi_ayeti",
    "label_gecersiz",
)


@dataclass
class QursimSonucu:
    ciftler: dict[tuple[int, int], int] = field(default_factory=dict)  # (lo, hi) -> ham Label
    satir: int = 0
    gecerli: int = 0  # gecerli ve tekil cift sayisi (len(ciftler))
    gecersiz: Counter[str] = field(default_factory=Counter)  # neden -> sayi (yinelenen dahil degil)
    yinelenen: int = 0
    label_dagilimi: Counter[int] = field(default_factory=Counter)

    @property
    def gecersiz_toplam(self) -> int:
        return sum(self.gecersiz.values())


def qursim_oku(yol: Path, ayet_sirasi: Mapping[str, int]) -> QursimSonucu:
    """CSV'yi okur; `ayet_sirasi`: `q:s:a` capasi -> kuresel ayet sirasi (gecerli ayet kumesi)."""
    sonuc = QursimSonucu()
    try:
        with yol.open("r", encoding="utf-8", newline="") as dosya:
            okuyucu = csv.reader(dosya)
            baslik = next(okuyucu, None)
            if baslik is None or any(ad not in baslik for ad in SUTUNLAR):
                raise GirdiHatasi("QurSim baslik satirinda SS, SV, TS, TV ya da Label yok")
            if len(set(baslik)) != len(baslik):
                raise GirdiHatasi("QurSim baslik satirinda yinelenen sutun adi var")
            sira = [baslik.index(ad) for ad in SUTUNLAR]
            en_az = max(sira) + 1
            for satir in okuyucu:
                sonuc.satir += 1
                if len(satir) != len(baslik) or len(satir) < en_az:
                    sonuc.gecersiz["sutun_sayisi"] += 1
                    continue
                ss, sv, ts, tv, etiket = (satir[i] for i in sira)
                del satir  # Verse1 ve Verse2 hicbir yerde tutulmaz
                _isle(sonuc, ayet_sirasi, ss, sv, ts, tv, etiket)
    except UnicodeDecodeError:
        raise GirdiHatasi("QurSim dosyasi UTF-8 degil") from None
    except (OSError, csv.Error):
        raise GirdiHatasi("QurSim dosyasi okunamadi ya da CSV gecersiz") from None
    sonuc.gecerli = len(sonuc.ciftler)
    return sonuc


def _isle(
    sonuc: QursimSonucu,
    ayet_sirasi: Mapping[str, int],
    ss: str,
    sv: str,
    ts: str,
    tv: str,
    etiket: str,
) -> None:
    if not all(SAYI.fullmatch(d) for d in (ss, sv, ts, tv)):
        sonuc.gecersiz["sayi_gecersiz"] += 1
        return
    a = ayet_sirasi.get(f"q:{ss}:{sv}")
    b = ayet_sirasi.get(f"q:{ts}:{tv}")
    if a is None or b is None:
        sonuc.gecersiz["capa_gecersiz"] += 1
        return
    if a == b:
        sonuc.gecersiz["kendi_ayeti"] += 1
        return
    if LABEL.fullmatch(etiket) is None:
        sonuc.gecersiz["label_gecersiz"] += 1
        return
    cift = (a, b) if a < b else (b, a)
    if cift in sonuc.ciftler:
        sonuc.yinelenen += 1
        return
    sonuc.ciftler[cift] = int(etiket)
    sonuc.label_dagilimi[int(etiket)] += 1
