"""Ust veri testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

`sentetik_xml` gercek `quran-data.xml` bicimini taklit eden, ama SENTETIK konumlar tasiyan bir
dosya uretir: sure tablosu gercek ayet sayilaridir (`AYET_SAYILARI`, ayristirici bunu ister), cuz,
ceyrek, menzil, ruku, sayfa ve secde baslangiclari ise kuresel ayet sirasina esit aralikla
dagitilmistir; gercek bir sinir degildir ve hicbir deger hafizadan yazilmaz. Sure adlari
"Deneme ..." metnidir. Hizb ceyregi sayisi 4'un katidir.
"""

import hashlib
from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur
from test_sources import alanlar_kur, kayit_yaz
from zincir_yardimci import Zincir, ortam_kur, sablon_kopyala

from mutalaa_pipeline.adimlar.anchor_tanzil import BASLANGIC
from mutalaa_pipeline.adimlar.anchor_ust_veri import komut_anchor_ust_veri
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.export import ayet_sayilari
from mutalaa_pipeline.ingest import tanzil
from mutalaa_pipeline.ingest.tanzil import UstVeriKilidi
from mutalaa_pipeline.ingest.tanzil_ust_veri import (
    KAYNAK,
    komut_ingest_ust_veri,
)
from mutalaa_pipeline.qa.dogrulama import QPC1_KAYNAGI, QURAN_META_KAYNAGI
from mutalaa_pipeline.runctx import RunContext

TARIH = "2026-11-08"
URL = "https://tanzil.net/res/text/metadata/quran-data.xml"
GRUP_BOYUTLARI = {"juzs": 30, "hizbs": 240, "manzils": 7, "rukus": 556, "pages": 604}
SECDE_SAYISI = 15
KOK_URL = "https://deneme.invalid/"


def konum(sira: int) -> tuple[int, int]:
    """Kuresel ayet sirasi (1..6236) -> `(sure, ayet)` (gercek ayet sayilari tablosundan)."""
    sure = bisect_left(BASLANGIC, sira)
    return sure, sira - BASLANGIC[sure - 1]


def esit_araliklar(adet: int, ilk: int = 1, kapsam: int = 6236) -> list[int]:
    """`adet` kadar kesin artan kuresel sira; ilki `ilk`."""
    adim = (kapsam - ilk) // adet
    return [ilk + i * adim for i in range(adet)]


def _oge(ad: str, **oznitelikler: object) -> str:
    ozn = " ".join(f'{k}="{v}"' for k, v in oznitelikler.items())
    return f"\t\t<{ad} {ozn} />\n"


def sentetik_xml(
    *,
    surum: str = "1.0",
    degistir: Callable[[dict[str, list[dict[str, object]]]], None] | None = None,
    onek: str = "",
) -> bytes:
    """Sentetik `quran-data.xml`; `degistir` grup sozluklerini yerinde bozabilir."""
    gruplar: dict[str, list[dict[str, object]]] = {}
    gruplar["suras"] = [
        {
            "index": s,
            "ayas": adet,
            "start": BASLANGIC[s - 1],
            "name": f"Deneme {s}",
            "tname": f"Deneme-{s}",
            "ename": f"Deneme {s}",
            "type": "Meccan" if s % 2 else "Medinan",
            "order": s,
            "rukus": 1,
        }
        for s, adet in enumerate(AYET_SAYILARI, start=1)
    ]
    for grup, adet in GRUP_BOYUTLARI.items():
        gruplar[grup] = [
            {"index": i, "sura": konum(sira)[0], "aya": konum(sira)[1]}
            for i, sira in enumerate(esit_araliklar(adet), start=1)
        ]
    gruplar["sajdas"] = [
        {
            "index": i,
            "sura": konum(sira)[0],
            "aya": konum(sira)[1],
            "type": "recommended" if i % 4 else "obligatory",
        }
        for i, sira in enumerate(esit_araliklar(SECDE_SAYISI, ilk=50, kapsam=6000), start=1)
    ]
    if degistir is not None:
        degistir(gruplar)
    oge_adlari = {
        "suras": "sura",
        "juzs": "juz",
        "hizbs": "quarter",
        "manzils": "manzil",
        "rukus": "ruku",
        "pages": "page",
        "sajdas": "sajda",
    }
    govde = ""
    for grup in ("suras", "juzs", "hizbs", "manzils", "rukus", "pages", "sajdas"):
        satirlar = gruplar.get(grup)
        if satirlar is None:
            continue
        govde += f"\t<{grup}>\n" + "".join(_oge(oge_adlari[grup], **s) for s in satirlar)
        govde += f"\t</{grup}>\n"
    metin = (
        '<?xml version="1.0" encoding="utf-8" ?>\n'
        + onek
        + f'<quran type="metadata" version="{surum}" license="deneme">\n'
        + govde
        + "</quran>\n"
    )
    return metin.encode("utf-8")


def kilit_xml_icin(veri: bytes, tarih: str = TARIH, surum: str = "1.0") -> UstVeriKilidi:
    return UstVeriKilidi(
        url=URL,
        surum=surum,
        alinma_tarihi=tarih,
        boyut=len(veri),
        sha256=hashlib.sha256(veri).hexdigest(),
    )


@dataclass
class UstVeriZinciri:
    """Sahte depo kokunde: tam sentetik Uthmani zinciri + ust veri XML'i ve kilidi."""

    z: Zincir
    xml: bytes
    kilit: UstVeriKilidi

    def ctx(self, adim: str, kaynaklar: list[str], **kw: object) -> RunContext:
        return ctx_kur(self.z.tmp, self.z.kok, adim=adim, kaynaklar=kaynaklar, **kw)  # type: ignore[arg-type]

    def ingest(self, **kw: object) -> int:
        return komut_ingest_ust_veri(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def anchor(self, **kw: object) -> int:
        return komut_anchor_ust_veri(
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def qa(self) -> int:
        from mutalaa_pipeline.qa.run_ust_veri import komut_qa_run_ust_veri

        return komut_qa_run_ust_veri(run=None, gate=None, config=None, kok=self.z.kok)

    def hepsi(self) -> None:
        assert self.ingest() == 0
        assert self.anchor() == 0
        assert self.qa() == 0


def kayitlari_yaz(kok: Path) -> None:
    """Ust veri, QPC1 ve quran-meta kaynak kayitlari (sahte depo koku)."""
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK,
            tur="mushaf_duzeni",
            baslik="Deneme ust veri",
            surum="1.0",
            provider="tanzil",
            kaynak_url=URL,
        ),
    )
    for slug in (QPC1_KAYNAGI, QURAN_META_KAYNAGI):
        kayit_yaz(kok, alanlar_kur(slug, tur="mushaf_duzeni", baslik=f"Deneme {slug}", surum="1"))


def ust_veri_hazirla(
    sablon: Path,
    hedef: Path,
    monkeypatch: pytest.MonkeyPatch,
    xml: bytes | None = None,
) -> UstVeriZinciri:
    """Tam sentetik zincir sablonunun kopyasina ust veri girdilerini koyar (hicbir adim kosulmaz).

    Uthmani zincirinin QA'si bu noktada kosulabilir (`ayet-sayilari.json` henuz gercektir);
    sentetik XML'in ozeti tutarlilik icin `shared/data/ayet-sayilari.json` kopyasina ve uc
    kopyaya yazilir (yalniz bu sahte kokte).
    """
    z = sablon_kopyala(sablon, hedef)
    ortam_kur(z, monkeypatch)
    veri = xml if xml is not None else sentetik_xml()
    kayitlari_yaz(z.kok)
    gelen = z.veri_kok / "gelen" / "tanzil-ust-veri" / TARIH
    gelen.mkdir(parents=True)
    (gelen / "quran-data.xml").write_bytes(veri)
    kilit = kilit_xml_icin(veri)
    kilitler = tanzil.kilit_yukle(z.tmp / "kilit.json")
    (z.tmp / "kilit.json").write_bytes(tanzil.kilit_metni(kilitler, kilit).encode("utf-8"))
    return UstVeriZinciri(z, veri, kilit)


def json_kopyalarini_yaz(kok: Path, veri: bytes) -> None:
    """Sahte kokteki `ayet-sayilari.json` ve kopyalari XML'in ozetiyle yeniden yazilir."""
    belge = ayet_sayilari.belge_kur(veri, URL, TARIH)
    for yol, metin in ayet_sayilari.tum_metinler(belge).items():
        hedef = kok / yol
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(metin.encode("utf-8"))


def sentetik_kelimeler(
    kelime_sayisi: Callable[[int, int], int] = lambda sure, ayet: 2 + (sure + ayet) % 3,
) -> list[dict[str, object]]:
    """Her ayet icin `kelime_sayisi(sure, ayet)` sentetik kelime satiri (yalniz sayisal alanlar)."""
    return [
        {"surah": sure, "ayah": ayet, "word": k, "ayah_index": BASLANGIC[sure - 1] + ayet}
        for sure, adet in enumerate(AYET_SAYILARI, start=1)
        for ayet in range(1, adet + 1)
        for k in range(1, kelime_sayisi(sure, ayet) + 1)
    ]
