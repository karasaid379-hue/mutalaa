"""Lugat kaynagi (`lugat-rnk`, `lugat-sozluk-rganeyev`) testlerinin ortak yardimcilari.

Test degildir; YALNIZ SENTETIK veri: baslik sozler "denemea", "denemeb" ... gibi anlamsiz
dizgiler, tanimlar "TANIM-RNK-n" ve "TANIM-RG-n" imzalidir; ciktilarin hicbirinde (rapor, gunluk)
bu imzalarin sizmadigi sinanir. Gercek lugat metni, Risale metni ya da anlam YOKTUR. Kelime-Frekans
zinciri `lugat_yardimci` sentetik zipinden uretilir (eslesme icin gerekli).
"""

from dataclasses import dataclass
from pathlib import Path

import pytest
from lugat_yardimci import LugatKoku, lugat_hazirla
from test_sources import alanlar_kur, kayit_yaz

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import lugat_kaynak
from mutalaa_pipeline.ingest.lugat_kaynak import (
    BICIMLER,
    KAYNAK_RGANEYEV,
    KAYNAK_RNK,
    kilit_hazirla,
    kilit_metni,
)
from mutalaa_pipeline.qa import run_risale_lugat
from mutalaa_pipeline.staged import satirlari_oku

TARIH_LUGAT = "2026-11-15"
RNK_URL = "https://deneme.invalid/lugat.txt"
RG_URL = "https://deneme.invalid/rganeyev"
RNK_SURUM = "hash-deneme-1"
RG_SURUM = "b" * 40
TANIM_RNK = "TANIM-RNK"
TANIM_RG = "TANIM-RG"
NFD_TANIM = "TANIM-RNK-NFD e\N{COMBINING ACUTE ACCENT}"
NBSP = "\N{NO-BREAK SPACE}"

# RNK (sentetik): satir sirasi anlam sirasidir.
RNK_SATIRLARI = [
    f"denemea|{TANIM_RNK}-1",  # 1. anlam
    f"denemea|{TANIM_RNK}-2",  # 2. anlam (ayni ham baslik)
    f"Denemea|{TANIM_RNK}-3",  # ham baslik farkli (buyuk D): ayri baslik, anlam_no 1
    f"denemeb |{TANIM_RNK}-4",  # basliktaki son bosluk kirpilir
    f"denemec|  \t{TANIM_RNK}-5 | ic ayrac korunur \t ",  # bas/son bosluk ve sekme kirpilir
    f"yenia|{NFD_TANIM}",  # NFC uygulanmaz (e + U+0301 kalir)
    f"yenib|{NBSP}{TANIM_RNK}-7{NBSP}",  # U+00A0 kirpilmaz
    f"denemee deneme f|{TANIM_RNK}-8",  # cok sozcuklu baslik (terkip)
    "bozukayracsiz",  # bozuk: ayrac yok
    f"|{TANIM_RNK}-9",  # bozuk: bos baslik
    "bostanim|   ",  # bozuk: bos tanim
    "",  # bozuk: bos satir
    f"nul\x00|{TANIM_RNK}-10",  # bozuk: NUL
    f"((|{TANIM_RNK}-11",  # bozuk: harf ya da rakam yok
]
# rganeyev (sentetik): `baslik: tanim`; yalniz RNK'da olmayan anahtarlar alinir.
RG_SATIRLARI = [
    f"denemea: {TANIM_RG}-1",  # RNK'da var: alinmaz
    f"Denemea : {TANIM_RG}-2",  # RNK'da var (anahtar ayni): alinmaz
    f"denemed: {TANIM_RG}-3",  # alinir, 1. anlam
    f"denemed: {TANIM_RG}-4",  # alinir, 2. anlam
    f"rgyeni: {TANIM_RG}-5",  # alinir; Kelime-Frekans'ta yok
    f"\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}stekrg: {TANIM_RG}-6",  # i-sapkali sozcuk basi
    f"rgbitisik:{TANIM_RG}-7",  # ayractan sonra bosluk yok
    "rgayracsiz bir satir",  # bozuk
    f"denemee (deneme) f: {TANIM_RG}-8",  # parantez atilir: RNK'nin cok sozcuklu basligi
]


def dosya_metni(satirlar: list[str], *, son_lf: bool = False) -> bytes:
    """Satirlar LF ile birlesir; gercek dosyalar gibi son satirin LF'si yoktur."""
    return ("\n".join(satirlar) + ("\n" if son_lf else "")).encode("utf-8")


@dataclass
class KaynakKoku:
    """`LugatKoku` (Kelime-Frekans zinciri) ve iki lugat kaynaginin gelen dosyalari."""

    lk: LugatKoku
    rnk: bytes
    rg: bytes
    kilit_klasoru: Path

    @property
    def veri_kok(self) -> Path:
        return self.lk.veri_kok

    @property
    def kok(self) -> Path:
        return self.lk.kok

    def ingest(self, slug: str, **kw: object) -> int:
        return lugat_kaynak.komut_ingest_lugat_kaynak(
            source=slug,
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.kok,
        )

    def qa(self, slug: str, *, gate: list[str] | None = None) -> int:
        return run_risale_lugat.komut_qa_run_lugat(
            run=None, gate=gate, config=None, kok=self.kok, source=slug
        )

    def staged_klasorleri(self, slug: str) -> list[Path]:
        kok = self.veri_kok / "staged" / slug
        return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []

    def satirlar(self, slug: str) -> list[dict[str, object]]:
        veri = (self.staged_klasorleri(slug)[-1] / "lugat.jsonl").read_bytes()
        return [s.veri for s in satirlari_oku(veri, "lugat.jsonl")]

    def madde(self, slug: str, baslik: str, anlam_no: int = 1) -> dict[str, object]:
        (satir,) = [
            s for s in self.satirlar(slug) if s["basliksoz"] == baslik and s["anlam_no"] == anlam_no
        ]
        return satir

    def gelen(self, slug: str) -> Path:
        return self.veri_kok / "gelen" / slug / TARIH_LUGAT / BICIMLER[slug].dosya

    def tum_cikti_baytlari(self) -> dict[str, bytes]:
        return self.lk.tum_cikti_baytlari()


def kayitlari_yaz(kok: Path) -> None:
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK_RNK,
            tur="sozluk",
            baslik="Deneme RNK lugat",
            surum=RNK_SURUM,
            provider="deneme",
            kaynak_url=RNK_URL,
        ),
    )
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK_RGANEYEV,
            tur="sozluk",
            baslik="Deneme rganeyev lugat",
            surum=RG_SURUM,
            provider="github",
            kaynak_url=RG_URL,
        ),
    )


def kilitleri_yaz(
    monkeypatch: pytest.MonkeyPatch, klasor: Path, rnk: bytes, rg: bytes
) -> dict[str, Path]:
    """Gelen baytlardan kilitleri uretir, `KILIT_YOLLARI`na baglar."""
    rnk_kilit = kilit_hazirla(KAYNAK_RNK, rnk, None, TARIH_LUGAT, RNK_URL, RNK_SURUM)
    rg_kilit = kilit_hazirla(KAYNAK_RGANEYEV, rg, rnk, TARIH_LUGAT, RG_URL, RG_SURUM)
    yollar: dict[str, Path] = {}
    for slug, kilit in ((KAYNAK_RNK, rnk_kilit), (KAYNAK_RGANEYEV, rg_kilit)):
        yol = klasor / BICIMLER[slug].kilit_dosyasi
        yol.write_bytes(kilit_metni(kilit).encode("utf-8"))
        monkeypatch.setitem(lugat_kaynak.KILIT_YOLLARI, slug, yol)
        yollar[slug] = yol
    return yollar


def kaynak_hazirla(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    rnk: bytes | None = None,
    rg: bytes | None = None,
    kf_ingest: bool = True,
    **lugat_kw: object,
) -> KaynakKoku:
    """Kelime-Frekans zinciri (sentetik), iki lugat kaynaginin gelen dosyalari, kayitlar, kilitler.

    `kf_ingest=False`: Kelime-Frekans staged ciktisi uretilmez (eslesme verisi yok).
    """
    lk = lugat_hazirla(tmp_path, monkeypatch, **lugat_kw)  # type: ignore[arg-type]
    if kf_ingest:
        assert lk.ingest() == 0
    rnk = rnk if rnk is not None else dosya_metni(RNK_SATIRLARI)
    rg = rg if rg is not None else dosya_metni(RG_SATIRLARI)
    kayitlari_yaz(lk.kok)
    for slug, veri in ((KAYNAK_RNK, rnk), (KAYNAK_RGANEYEV, rg)):
        klasor = lk.veri_kok / "gelen" / slug / TARIH_LUGAT
        klasor.mkdir(parents=True)
        (klasor / BICIMLER[slug].dosya).write_bytes(veri)
    kilit_klasoru = lk.tmp / "kilitler"
    kilit_klasoru.mkdir()
    kilitleri_yaz(monkeypatch, kilit_klasoru, rnk, rg)
    return KaynakKoku(lk, rnk, rg, kilit_klasoru)


def tam_zincir(kok: KaynakKoku) -> None:
    """RNK ve rganeyev ingest + QA (hepsi 0 ile bitmeli)."""
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        assert kok.ingest(slug) == 0
        assert kok.qa(slug) == 0


__all__ = [
    "NBSP",
    "NFD_TANIM",
    "RG_SATIRLARI",
    "RNK_SATIRLARI",
    "TANIM_RG",
    "TANIM_RNK",
    "TARIH_LUGAT",
    "GirdiHatasi",
    "KaynakKoku",
    "dosya_metni",
    "kaynak_hazirla",
    "tam_zincir",
]
