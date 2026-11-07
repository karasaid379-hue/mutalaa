"""Tanzil testlerinin ortak yardimcilari (test degildir).

Fiksturler `tests/fixtures/tanzil/` altindaki parcalardir: gercek Tanzil dosyalarindan betikle
kesilmis bayt dilimleridir (KAYNAK.txt). Tam dosya gereken yerde SENTETIK "Deneme" metni kullanilir;
gercek metin hafizadan yazilmaz.
"""

import hashlib
from pathlib import Path

from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.ingest import tanzil, tanzil_bicim

FIKSTUR = Path(__file__).parent / "fixtures" / "tanzil"
VARYANTLAR = ("uthmani", "simple-clean")
BASLIK_TURU = {"uthmani": "Uthmani", "simple-clean": "Simple Clean"}
PARCA_AYET = 40  # parca: 1|1 ... 2|33
PARCA_BILDIRIM_SATIR = 30  # 2 bos satir + 28 '#' satiri
PARCA_CAPALAR = [f"q:1:{a}" for a in range(1, 8)] + [f"q:2:{a}" for a in range(1, 34)]
TARIH = "2026-11-02"


def parca_oku(varyant: str) -> bytes:
    """Gercek dosyadan kesilmis parca (ilk 40 ayet satiri + tam bildirim blogu)."""
    return (FIKSTUR / f"{varyant}-parca.txt").read_bytes()


def sentetik_bildirim(varyant: str, yil: str = "2026") -> bytes:
    """Sentetik bildirim blogu: 2 bos satir ve '#' satirlari (baslik satiri dahil)."""
    tur = BASLIK_TURU[varyant]
    return (
        b"\n\n# Deneme bildirim blogu\n"
        + f"#  Tanzil Quran Text ({tur}, Version 1.1)\n".encode("ascii")
        + f"#  Deneme (C) 2007-{yil}\n".encode("ascii")
    )


def sentetik_tam(varyant: str, bildirim: bytes | None = None) -> bytes:
    """6.236 sentetik ayet satiri (`Deneme <sure> <ayet>`) + bildirim; gercek metin yok."""
    satirlar = [
        f"{sure}|{ayet}|Deneme {sure} {ayet}\n"
        for sure, adet in enumerate(AYET_SAYILARI, start=1)
        for ayet in range(1, adet + 1)
    ]
    govde = "".join(satirlar).encode("utf-8")
    return govde + (bildirim if bildirim is not None else sentetik_bildirim(varyant))


def ayet_bitisi(veri: bytes) -> int:
    """Ayet bolgesinin bitisi (bayt): son ayet satirinin LF'si dahil, ardindan 2 bos satir."""
    return veri.index(b"\n\n\n# ") + 1


def kilit_kur(
    varyant: str, veri: bytes, *, tam: bool = False, tarih: str = TARIH
) -> tanzil.KilitGirdisi:
    """`veri` icin kilit girdisi: dosya ve parca ozetleri `veri`nin kendisinden hesaplanir."""
    ayrisma = tanzil_bicim.ayristir(veri, tam=tam)
    return tanzil.KilitGirdisi(
        varyant=varyant,
        url=tanzil.FORM_ADRESI,
        secenekler=dict(tanzil.SECENEKLER),
        surum="1.1",
        alinma_tarihi=tarih,
        boyut=len(veri),
        sha256=hashlib.sha256(veri).hexdigest(),
        metin_sha256=ayrisma.metin_sha256,
        bildirim_sha256=ayrisma.bildirim_sha256,
    )


def gelen_yaz(veri_kok: Path, varyant: str, veri: bytes, tarih: str = TARIH) -> Path:
    """`<veri_kok>/gelen/tanzil/<tarih>/quran-<varyant>.txt` dosyasini yazar."""
    yol = veri_kok / "gelen" / "tanzil" / tarih / tanzil.dosya_adi(varyant)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_bytes(veri)
    return yol
