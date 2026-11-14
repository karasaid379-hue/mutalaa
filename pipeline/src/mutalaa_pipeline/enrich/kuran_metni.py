"""Atif araci icin Kur'an metni: Tanzil'in iki dosyasi, bellekte (A20.7b).

Kur'an metni yalniz Tanzil kaynak dosyalarindan gelir (`data/gelen/tanzil-uthmani/<tarih>/` ve
`data/gelen/tanzil-simple-clean/<tarih>/`); her dosya `tanzil.lock.json` kilidiyle (SHA-256 ve
bicim) dogrulanir ve `ingest/tanzil_bicim.ayristir` ile ayristirilir. Dosyaya hicbir donusum
uygulanmaz (K-26); metin buradan yalniz arac sarmalayicisina ve kelime sayimina gider, hicbir
yere yazilmaz ya da gunluge girmez.

Kelime numarasi QAC konumudur (K-43): `anchor.quran.kelimelere_bol` Uthmani metnine uygulanir.
Simple Clean metni ayni kuralla (besmele onegi ve durak isaretleri kelime degildir) bolunur ve
kelime sayisi QAC sayisiyla ayniysa ayet "hizali"dir: simple-clean konumu QAC konumudur. Hizasiz
ayetlerde (Simple Clean'de bir kelime fazla) kelime konumu verilmez; hedef ayet duzeyinde kalir.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor.quran import besmele_onekli_mi, durak_belirteci_mi, kelimelere_bol
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import tanzil

GELEN_KLASORU: Final = "gelen"
UTHMANI: Final = "uthmani"
SIMPLE: Final = "simple-clean"
VARYANTLAR: Final = (UTHMANI, SIMPLE)
AYET_SAYISI: Final = 6236


@dataclass(frozen=True, slots=True)
class Ayet:
    """Bir ayet: iki yazimi, QAC kelime sayisi ve (hizaliysa) Simple Clean kelimeleri."""

    sure: int
    ayet: int
    uthmani: str
    basit: str
    kelime: int  # QAC kelime sayisi (besmele onegi ve durak isaretleri haric)
    basit_kelimeler: tuple[str, ...] | None  # hizaliysa QAC sirasinda; degilse None

    @property
    def hizali(self) -> bool:
        return self.basit_kelimeler is not None


class KuranMetni:
    """Tanzil'den okunan 6.236 ayet ve kullanilan dosyalarin veri soyu kaydi."""

    def __init__(
        self,
        ayetler: tuple[Ayet, ...],
        girdiler: tuple[lineage.Girdi, ...],
        tarihler: Mapping[str, str],
    ) -> None:
        self.ayetler = ayetler
        self.girdiler = girdiler
        self.tarihler = dict(tarihler)
        self._indeks = {(a.sure, a.ayet): a for a in ayetler}

    def kelime_sayisi(self, sure: int, ayet: int) -> int:
        return self._indeks[(sure, ayet)].kelime

    def ayet(self, sure: int, ayet: int) -> Ayet | None:
        return self._indeks.get((sure, ayet))

    @property
    def hizasiz(self) -> int:
        return sum(1 for a in self.ayetler if not a.hizali)


def kaynak_kimligi(varyant: str) -> str:
    return tanzil.kaynak_kimligi(varyant)


def basit_kelimeler(sure: int, ayet: int, basit: str) -> tuple[str, ...]:
    """Simple Clean ayetinin kelimeleri: besmele onegi ve durak isaretleri atilir (K-43 kurali)."""
    belirtecler = basit.split(" ")
    belirtecler = [b for b in belirtecler if b != ""]
    if besmele_onekli_mi(sure, ayet):
        belirtecler = belirtecler[4:]
    return tuple(b for b in belirtecler if not durak_belirteci_mi(b))


def ayetleri_kur(
    uthmani: list[tuple[int, int, str]], basit: list[tuple[int, int, str]]
) -> tuple[Ayet, ...]:
    """Iki ayrismis dosyadan `Ayet` listesi; iki dosyanin ayet sirasi ayni olmali."""
    if len(uthmani) != len(basit):
        raise GirdiHatasi("Tanzil dosyalarinin ayet sayisi ayni degil")
    sonuc: list[Ayet] = []
    for (s1, a1, uth), (s2, a2, bas) in zip(uthmani, basit, strict=True):
        if (s1, a1) != (s2, a2):
            raise GirdiHatasi("Tanzil dosyalarinin ayet sirasi ayni degil")
        qac = len(kelimelere_bol(uth, s1, a1))
        kelimeler = basit_kelimeler(s1, a1, bas)
        sonuc.append(Ayet(s1, a1, uth, bas, qac, kelimeler if len(kelimeler) == qac else None))
    return tuple(sonuc)


def _tarih_klasoru(veri_kok: Path, varyant: str, istenen: str | None) -> tuple[Path, str]:
    gelen = veri_kok / GELEN_KLASORU / kaynak_kimligi(varyant)
    tarih = tanzil.gelen_tarihi_coz(gelen, istenen)
    return gelen / tarih, tarih


def _oku(klasor: Path, varyant: str) -> bytes:
    yol = klasor / tanzil.dosya_adi(varyant)
    try:
        if not yol.is_file():
            raise GirdiHatasi(f"{kaynak_kimligi(varyant)}: gelen dosyasi yok")
        if yol.stat().st_size > tanzil.EN_BUYUK_GELEN_BAYT:
            raise GirdiHatasi(f"{kaynak_kimligi(varyant)}: gelen dosyasi cok buyuk")
        return yol.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{kaynak_kimligi(varyant)}: gelen dosyasi okunamadi") from None


def yukle(veri_kok: Path, gelen_tarih: str | Mapping[str, str] | None = None) -> KuranMetni:
    """Iki Tanzil dosyasini `data/gelen` altindan okur, kilitle dogrular ve ayristirir.

    Tarih verilmezse her varyantin en yeni tarih klasoru kullanilir (`{varyant: tarih}` de olur).
    Kilitle tutmayan dosya `GirdiHatasi` (cikis 2). Yalniz bellekte tutulur.
    """
    kilitler = tanzil.kilit_yukle()
    ham: dict[str, list[tuple[int, int, str]]] = {}
    girdiler: list[lineage.Girdi] = []
    tarihler: dict[str, str] = {}
    for varyant in VARYANTLAR:
        istenen = gelen_tarih.get(varyant) if isinstance(gelen_tarih, Mapping) else gelen_tarih
        klasor, tarih = _tarih_klasoru(veri_kok, varyant, istenen)
        veri = _oku(klasor, varyant)
        if varyant not in kilitler:
            raise GirdiHatasi(f"{kaynak_kimligi(varyant)}: kilitte kayit yok")
        ayrisma = tanzil.kilit_denetle(kilitler[varyant], veri)
        ham[varyant] = [(a.sure, a.ayet, a.metin) for a in ayrisma.ayetler]
        yol = f"{GELEN_KLASORU}/{kaynak_kimligi(varyant)}/{tarih}/{tanzil.dosya_adi(varyant)}"
        girdiler.append(lineage.Girdi(yol=yol, sha256=lineage.sha256_bayt(veri)))
        tarihler[varyant] = tarih
    ayetler = ayetleri_kur(ham[UTHMANI], ham[SIMPLE])
    if len(ayetler) != AYET_SAYISI:
        raise GirdiHatasi(f"Tanzil ayet sayisi {AYET_SAYISI} degil")
    return KuranMetni(ayetler, tuple(girdiler), tarihler)
