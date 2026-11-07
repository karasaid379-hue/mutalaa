"""`qa run` raporlarini okuma ve kabul karari (`export pg` ve G-CAP tabani ortak kullanir).

Rapor `data/reports/{run_id}.json` dosyasidir (qa/run.py). Dosya adi UUIDv7 oldugundan ad sirasi
zaman sirasidir. Bir anchor calismasinin (`anchor_run_id`, `units_sha256`) kabulu, o calismaya
ait raporlarin EN YENISINDEN okunur:

* dort kapiyi da iceren ve hepsi `gecti` olan tam rapor kabul eder;
* kapisi kalan ya da tamamlanamayan (cikis kodu 0 degil) bir kosu, daha eski bir tam raporu
  gecersiz kilar: son degerlendirme gecmediyse ya da yapilamadiysa yukleme yapilmaz;
* basarili bir kismi (`--gate`) kosu karari degistirmez: bir sonraki daha eski rapora bakilir.

Rapor ve iletiler icerik tasimaz (capa, sayi, kapi adi).
"""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from mutalaa_pipeline.qa import GECTI, KALDI, KAPILAR, QA_KOMUTU
from mutalaa_pipeline.runctx import RAPOR_KLASORU, QaKaldi


@dataclass(frozen=True)
class QaRaporu:
    """Tek bir `qa run` raporu (dosya adi + ayristirilmis JSON nesnesi)."""

    rapor_id: str
    veri: Mapping[str, object]

    @property
    def kapilar(self) -> Mapping[str, object] | None:
        """Raporun degerlendirdigi kapilar; zincir hatasiyla biten kosuda yoktur."""
        deger = self.veri.get("kapilar")
        return deger if isinstance(deger, dict) else None

    @property
    def tam(self) -> bool:
        """Dort kapiyi da degerlendirmis mi (`--gate` ile kosulan kismi rapor degil)."""
        kapilar = self.kapilar
        return kapilar is not None and all(kapi in kapilar for kapi in KAPILAR)

    @property
    def cikis_kodu(self) -> int | None:
        deger = self.veri.get("cikis_kodu")
        return deger if isinstance(deger, int) and not isinstance(deger, bool) else None

    @property
    def tamamlandi(self) -> bool:
        """Kosu 0 ile bitti.

        Alan hic yoksa (ornegin elle yazilmis rapor) sorun sayilmaz; alan varsa int 0 olmali:
        metin, ondalik, bool ve null tamamlandi sayilmaz.
        """
        if "cikis_kodu" not in self.veri:
            return True
        return self.cikis_kodu == 0

    def kalan_kapilar(self, hepsi: bool) -> list[str]:
        """`gecti` olmayan kapilar. `hepsi=False` iken yalniz acikca `kaldi` diyenler."""
        kapilar = self.kapilar or {}
        if hepsi:
            return [kapi for kapi in KAPILAR if kapilar.get(kapi) != GECTI]
        return [kapi for kapi in KAPILAR if kapilar.get(kapi) == KALDI]


def _oku(veri_kok: Path) -> list[QaRaporu]:
    klasor = veri_kok / RAPOR_KLASORU
    if not klasor.is_dir():
        return []
    raporlar: list[QaRaporu] = []
    for yol in sorted(klasor.glob("*.json"), key=lambda p: p.name):
        try:
            veri = json.loads(yol.read_bytes().decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(veri, dict) and veri.get("komut") == QA_KOMUTU:
            raporlar.append(QaRaporu(yol.name.removesuffix(".json"), veri))
    return raporlar


class QaRaporlari:
    """Veri kokundeki `qa run` raporlari (kurulurken bir kez okunur, zaman sirasinda)."""

    def __init__(self, veri_kok: Path) -> None:
        self._raporlar = _oku(veri_kok)

    def eslesenler(self, source_id: str, anchor_run_id: str, units_sha: str) -> list[QaRaporu]:
        """Ayni kaynak, anchor calismasi ve `units_sha256` icin raporlar (eskiden yeniye)."""
        return [
            rapor
            for rapor in self._raporlar
            if rapor.veri.get("kaynak") == source_id
            and rapor.veri.get("anchor_run_id") == anchor_run_id
            and rapor.veri.get("units_sha256") == units_sha
        ]

    def onayla(self, source_id: str, anchor_run_id: str, units_sha: str) -> str:
        """Kabul eden raporun kimligi; kabul yoksa `QaKaldi` (cikis 1) ve nedeni."""
        adaylar = self.eslesenler(source_id, anchor_run_id, units_sha)
        if not adaylar:
            raise QaKaldi("bu anchor calistirmasi ve ozeti icin QA raporu yok (once qa run)")
        for rapor in reversed(adaylar):  # en yeni rapor once
            kalanlar = rapor.kalan_kapilar(hepsi=rapor.tam)
            if kalanlar:
                raise QaKaldi("QA kapisi gecmedi: " + ", ".join(kalanlar))
            if not rapor.tamamlandi:
                raise QaKaldi(f"son QA kosusu tamamlanmadi (cikis {rapor.cikis_kodu}); once qa run")
            if rapor.tam:
                return rapor.rapor_id
            # basarili kismi (--gate) kosu ya da kapi iddia etmeyen rapor: daha eski rapora bakilir
        raise QaKaldi(f"QA raporu dort kapiyi da icermiyor ({', '.join(KAPILAR)})")

    def onayli_mi(self, source_id: str, anchor_run_id: str, units_sha: str) -> bool:
        try:
            self.onayla(source_id, anchor_run_id, units_sha)
        except QaKaldi:
            return False
        return True
