"""Atif araclari icin `DiziTespitcisi` sarmalayicilari (A20.7a olcumu; QDetect elendi).

Uc aday arac ayni Tanzil metniyle beslenir (`data/gelen/tanzil-uthmani` ve `tanzil-simple-clean`):
araclarin kendi paketlerindeki Kur'an verisi kullanilmaz. Araclar `importlib` ile yuklenir; proje
bagimliligi degillerdir (`uv run --with <paket>==<surum>`); kazanan secilince `uv add` ile eklenir
(K-51 guncellemesi) ve yalniz onun sarmalayicisi kalir.

Her sarmalayici bir diziyi (Arapca metin) alir ve `DiziEslesmesi` listesi dondurur; ofsetler dizi
metninde kod noktasi, `[bas, son)`. Araclar bosluklari tek bosluga indirip kendi ofsetlerini
bildirdigi icin ofsetler bosluk disi karakter sirasi uzerinden asil metne geri esitlenir.

Metin hicbir yerde saklanmaz ya da yazilmaz.
"""

import importlib
import importlib.metadata
import re
from collections.abc import Callable, Sequence
from itertools import accumulate
from pathlib import Path
from typing import Any, Final

from mutalaa_pipeline.enrich.citations import DiziEslesmesi

ARAC_PAKETLERI: Final = {
    "ijaza": ("ijaza", "ijaza", "2.0.0"),
    "quran-detector": ("quran_detector", "quran-detector", "0.0.2"),
    "quran-toolkit": ("quran_toolkit", "quran-toolkit", "0.1.0"),
}

type AyetMetni = tuple[int, int, str, str]  # (sure, ayet, uthmani, simple_clean)

_BOSLUK_DISI: Final = re.compile(r"\S")
_SOZCUK: Final = re.compile(r"\S+")


def paket_surumu(paket: str) -> str:
    """Yuklu paketin dagitim surumu."""
    return importlib.metadata.version(paket)


def bosluk_disi_konumlar(metin: str) -> list[int]:
    """Bosluk olmayan her karakterin `metin` icindeki konumu (k. karakter -> konum)."""
    return [m.start() for m in _BOSLUK_DISI.finditer(metin)]


def _kompaktan_asila(konumlar: Sequence[int], k_bas: int, k_son: int) -> tuple[int, int] | None:
    """Bosluk disi karakter dizisi `[k_bas, k_son)` -> asil metin `[bas, son)`."""
    if not 0 <= k_bas < k_son <= len(konumlar):
        return None
    return konumlar[k_bas], konumlar[k_son - 1] + 1


class IjazaSarmalayici:
    """ijaza 2.0.0: `QuranValidator.scan_for_verses` (kademeli eslesme, tek en iyi ayet/pencere)."""

    ad: str = "ijaza"
    surum: str = "2.0.0"

    def __init__(
        self,
        ayetler: Sequence[AyetMetni],
        *,
        min_words: int = 3,
        max_words: int = 50,
        esik: float = 0.85,
    ) -> None:
        self._ayar = {"min_words": min_words, "max_words": max_words, "confidence_threshold": esik}
        modul: Any = importlib.import_module("ijaza.validator")
        asil_yukle: Callable[[str], list[Any]] = modul._load_json_data
        veri = [
            {"id": i, "surah": s, "ayah": a, "text": uthmani, "textSimple": basit}
            for i, (s, a, uthmani, basit) in enumerate(ayetler, start=1)
        ]

        def yukle(dosya: str) -> list[Any]:
            return veri if dosya == "quran-verses.json" else asil_yukle(dosya)

        modul._load_json_data = yukle
        try:
            self._dogrulayici: Any = importlib.import_module("ijaza").create_validator()
        finally:
            modul._load_json_data = asil_yukle

    def tespit_et(self, dizi_metni: str) -> list[DiziEslesmesi]:
        birlesik = " ".join(dizi_metni.split())
        konumlar = bosluk_disi_konumlar(dizi_metni)
        onek = [0, *accumulate(0 if k.isspace() else 1 for k in birlesik)]
        sonuc: list[DiziEslesmesi] = []
        for e in self._dogrulayici.scan_for_verses(birlesik, **self._ayar):
            aralik = _kompaktan_asila(konumlar, onek[e["start_pos"]], onek[e["end_pos"]])
            if aralik is None:
                continue
            ayetler = tuple((v.surah, v.ayah) for v in e["verses"])
            kelime = len(birlesik[e["start_pos"] : e["end_pos"]].split())
            sonuc.append(
                DiziEslesmesi(aralik[0], aralik[1], ayetler, float(e["confidence"]), kelime)
            )
        return sonuc


class DetectorSarmalayici:
    """quran-detector 0.0.2: `Engine.detect` (trie + Levenshtein; Tanzil Simple Clean ile)."""

    ad: str = "quran-detector"
    surum: str = "0.0.2"

    def __init__(self, ayetler: Sequence[AyetMetni], calisma: Path) -> None:
        engine_modulu: Any = importlib.import_module("quran_detector.engine")
        config_modulu: Any = importlib.import_module("quran_detector.config")
        metin_modulu: Any = importlib.import_module("quran_detector.text")
        kaynaklar: Any = importlib.import_module("importlib.resources")
        veri_klasoru = kaynaklar.files("quran_detector") / "data"
        calisma.mkdir(parents=True, exist_ok=True)
        basit = calisma / "quran-simple.txt"
        # Tanzil Simple Clean satirlari ("sure|ayet|metin"); araclarin kendi dosya bicimi.
        with basit.open("w", encoding="utf-8", newline="\n") as dosya:
            for sure, ayet, _uthmani, metin in ayetler:
                dosya.write(f"{sure}|{ayet}|{metin}\n")
        self._engine: Any = engine_modulu.Engine.from_paths(
            str(basit),
            str(veri_klasoru / "quran-index.xml"),
            str(veri_klasoru / "non-terminals.txt"),
        )
        self._ayarlar: Any = config_modulu.Settings()
        self._pad: Callable[[str], str] = metin_modulu.pad_symbols

    def tespit_et(self, dizi_metni: str) -> list[DiziEslesmesi]:
        konumlar = bosluk_disi_konumlar(dizi_metni)
        sozcukler = [len(m.group()) for m in _SOZCUK.finditer(self._pad(dizi_metni))]
        toplam = [0, *accumulate(sozcukler)]
        sonuc: list[DiziEslesmesi] = []
        for kayit in self._engine.detect(self._pad(dizi_metni), settings=self._ayarlar):
            bas, son = kayit["start_in_text"], kayit["end_in_text"]
            if not 0 <= bas < son <= len(sozcukler):
                continue
            aralik = _kompaktan_asila(konumlar, toplam[bas], toplam[son])
            if aralik is None:
                continue
            sure = self._engine.surah_rank[kayit["surah_name"]]
            ayetler = tuple((sure, a) for a in range(kayit["aya_start"], kayit["aya_end"] + 1))
            # Arac skor vermez (`skor = None`); uzunluk kelime sayisidir.
            sonuc.append(DiziEslesmesi(aralik[0], aralik[1], ayetler, None, son - bas))
        return sonuc


class ToolkitSarmalayici:
    """quran-toolkit 0.1.0: `AyahDetector.find` (kelime dizisi eslesmesi; Tanzil Simple Clean)."""

    ad: str = "quran-toolkit"
    surum: str = "0.1.0"

    def __init__(self, ayetler: Sequence[AyetMetni], calisma: Path, *, min_words: int = 4) -> None:
        paket: Any = importlib.import_module("quran_toolkit")
        calisma.mkdir(parents=True, exist_ok=True)
        csv_yolu = calisma / "quran.csv"
        uthmani_yolu = calisma / "quran-uthmani.txt"
        with csv_yolu.open("w", encoding="utf-8", newline="\n") as dosya:
            for sure, ayet, _uthmani, metin in ayetler:
                for sira, sozcuk in enumerate(metin.split(), start=1):
                    dosya.write(f"{sure},{ayet},{sira},{sozcuk}\n")
        with uthmani_yolu.open("w", encoding="utf-8", newline="\n") as dosya:
            for sure, ayet, uthmani, _metin in ayetler:
                dosya.write(f"{sure}|{ayet}|{uthmani}\n")
        self._dedektor: Any = paket.AyahDetector(
            quran_csv_path=str(csv_yolu),
            quran_uthmani_path=str(uthmani_yolu),
            min_words=min_words,
        )

    def tespit_et(self, dizi_metni: str) -> list[DiziEslesmesi]:
        sonuc: list[DiziEslesmesi] = []
        for e in self._dedektor.find(dizi_metni):
            ayetler = tuple((e.surah, a) for a in range(e.ayah_start, e.ayah_end + 1))
            sonuc.append(
                DiziEslesmesi(
                    e.char_start, e.char_end, ayetler, None, e.word_end - e.word_start + 1
                )
            )
        return sonuc
