# ruff: noqa: RUF001, RUF003
"""Lugat (Kelime-Frekans) testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

Hicbir Risale metni, lugat OCR metni ya da gercek anlam yoktur: baslik sozler "denemea",
"denemeb" ... gibi anlamsiz dizgiler, `anlam` degerleri "ANLAM-SENTETIK-N", OCR satirlari
"OCR-SENTETIK-N" imzalidir; ciktilarda bu imzalarin sizmasi sinanir. Zip bellekte uretilir (diske
acilmaz); gercek `data/` kullanilmaz.
"""

import csv
import io
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline.ingest import kelime_frekans
from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK, kilit_metni, kilit_onerisi
from mutalaa_pipeline.ingest.sozluk_ocr import SOZLUKLER
from mutalaa_pipeline.qa import run_risale_lugat
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_oku

COMMIT = "0123456789abcdef0123456789abcdef01234567"
TARIH = "2026-11-12"
DEPO = "https://deneme.invalid/Risale-i-Nur-Kelime-Frekans"
URL = f"{DEPO}/archive/{COMMIT}.zip"
ZIP_ADI = f"Risale-i-Nur-Kelime-Frekans-{COMMIT}.zip"
KOK_ADI = f"Risale-i-Nur-Kelime-Frekans-{COMMIT}"
KITAP_A = "1-Deneme Kitap A"
KITAP_B = "2-Deneme Kitap B"
ALT_A = "1-Deneme Kitap A alt"
ANLAM_IMZASI = "ANLAM-SENTETIK"
OCR_IMZASI = "OCR-SENTETIK"
# Baslik sozler (anlamsiz): `denemeI` ve `denemeı` ayni `tr_narrow` anahtarini paylasir (I -> ı).
DENEMEI_BUYUK = "denemeI"
DENEMEI_NOKTASIZ = "deneme\N{LATIN SMALL LETTER DOTLESS I}"
NFD_SOZ = "denemee\N{COMBINING ACUTE ACCENT}"

FREKANS_A = {
    "denemea": 120,
    "Denemea": 1,
    "denemeb": 30,
    "denemec": 5,
    DENEMEI_BUYUK: 3,
    DENEMEI_NOKTASIZ: 2,
    NFD_SOZ: 4,
    "(": 4,  # noktalama: baslik soz degil, elenir
}
FREKANS_B = {"denemea": 20, "denemed": 7, "denemec": 2}
FREKANS_ALT = {"denemea": 10, "denemeb": 3}  # A'nin alt kumesi: cift sayilmaz
CSV_A = [
    ("denemea", f"{ANLAM_IMZASI}-1"),
    ("denemea", f"{ANLAM_IMZASI}-1"),
    ("denemea", f"{ANLAM_IMZASI}-2"),
    (DENEMEI_NOKTASIZ, f"{ANLAM_IMZASI}-3"),
    ("denemea denemeb", f"{ANLAM_IMZASI}-4"),  # iki sozlu kelime: tek baslik soza eslesmez
]
CSV_B = [("denemea", f"{ANLAM_IMZASI}-2"), ("denemed", f"{ANLAM_IMZASI}-5")]
CSV_ALT = [("denemea", f"{ANLAM_IMZASI}-1")]

OCR_KAMUS = (
    f"{OCR_IMZASI}-0\n1. denemeb. {OCR_IMZASI}-1\n\ndenemea, {OCR_IMZASI}-2\n"
    f"gecen {OCR_IMZASI}-3 denemec\n"
)
OCR_REDHOUSE = f"{OCR_IMZASI}-4 ilk\ndenemec ve {OCR_IMZASI}-5\n"
OCR_NACI = "ابت " + OCR_IMZASI + "-6\nابتث\n"


def frekans_metni(satirlar: Mapping[str, int]) -> str:
    return "kelime,frekans\n" + "".join(f"{k},{n}\n" for k, n in satirlar.items())


def csv_metni(satirlar: list[tuple[str, str]], ek: str = "") -> str:
    tampon = io.StringIO(newline="")
    yazici = csv.writer(tampon, quoting=csv.QUOTE_ALL, lineterminator="\n")
    yazici.writerow(["kelime", "anlam"])
    yazici.writerows(satirlar)
    return tampon.getvalue() + ek


def sentetik_zip(
    *,
    frekans: Mapping[str, Mapping[str, int]] | None = None,
    csvler: Mapping[str, list[tuple[str, str]]] | None = None,
    csv_ek: Mapping[str, str] | None = None,
    ekstra: Mapping[str, bytes] | None = None,
    commit: str = COMMIT,
) -> bytes:
    """Gercek zipin yapisini taklit eden sentetik zip (frekans, CSV, terkipli, betik, README)."""
    frekans = (
        frekans
        if frekans is not None
        else {KITAP_A: FREKANS_A, KITAP_B: FREKANS_B, ALT_A: FREKANS_ALT}
    )
    csvler = csvler if csvler is not None else {KITAP_A: CSV_A, KITAP_B: CSV_B, ALT_A: CSV_ALT}
    csv_ek = csv_ek or {}
    kok = f"Risale-i-Nur-Kelime-Frekans-{commit}"
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{kok}/README.md", "Deneme README")
        # Zip icindeki betik calistirilmaz: calisirsa `CALISTI.txt` olusur.
        z.writestr(
            f"{kok}/data/eRisale/analysis/terkipsiz/tablo_olustur.py",
            "open('CALISTI.txt', 'w').write('x')\n",
        )
        for ad, satirlar in frekans.items():
            z.writestr(
                f"{kok}/data/eRisale/analysis/terkipsiz/{ad}_frekans.txt", frekans_metni(satirlar)
            )
            z.writestr(f"{kok}/data/eRisale/analysis/terkipsiz/{ad}_analiz.txt", "Deneme analiz")
            # `terkipli/` ve `SorularlaRisale/` agaci okunmaz: bozuk icerik sorun cikarmamali.
            z.writestr(
                f"{kok}/data/eRisale/analysis/terkipli/{ad}_frekans.txt", "bozuk,bozuk,bozuk\n"
            )
            z.writestr(f"{kok}/data/SorularlaRisale/raw/{ad}.csv", "bozuk")
        for ad, satirlar in csvler.items():
            z.writestr(f"{kok}/data/eRisale/raw/{ad}.csv", csv_metni(satirlar, csv_ek.get(ad, "")))
        for ad, veri in (ekstra or {}).items():
            z.writestr(ad, veri)
    return tampon.getvalue()


def sentetik_ocr() -> dict[str, bytes]:
    return {
        "lugat-kamus-i-turki": OCR_KAMUS.encode("utf-8"),
        "lugat-redhouse-1890": OCR_REDHOUSE.encode("utf-8"),
        "lugat-naci": OCR_NACI.encode("utf-8"),
    }


@dataclass
class LugatKoku:
    """Sahte kok: gelen dosyalari, kaynak kayitlari ve kilit yolu."""

    tmp: Path
    kok: Path
    veri_kok: Path
    zip_verisi: bytes
    ocr: dict[str, bytes]
    kilit_yolu: Path

    def ctx(self, adim: str, kaynaklar: list[str], **kw: object) -> RunContext:
        return ctx_kur(self.tmp, self.kok, adim=adim, kaynaklar=kaynaklar, **kw)  # type: ignore[arg-type]

    def ingest(self, **kw: object) -> int:
        return kelime_frekans.komut_ingest_lugat(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.kok,
        )

    def qa(self, **kw: object) -> int:
        return run_risale_lugat.komut_qa_run_lugat(run=None, gate=None, config=None, kok=self.kok)

    def staged_klasorleri(self) -> list[Path]:
        kok = self.veri_kok / "staged" / KAYNAK
        return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []

    def satirlar(self) -> list[dict[str, object]]:
        veri = (self.staged_klasorleri()[-1] / "lugat.jsonl").read_bytes()
        return [s.veri for s in satirlari_oku(veri, "lugat.jsonl")]

    def tum_cikti_baytlari(self) -> dict[str, bytes]:
        """`data/staged`, `data/reports` ve `data/logs` altindaki butun dosyalar (raw haric)."""
        sonuc: dict[str, bytes] = {}
        for alt in ("staged", "reports", "logs"):
            kok = self.veri_kok / alt
            if kok.is_dir():
                for yol in sorted(kok.rglob("*")):
                    if yol.is_file():
                        sonuc[yol.relative_to(self.veri_kok).as_posix()] = yol.read_bytes()
        return sonuc


def kayitlari_yaz(kok: Path) -> None:
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK,
            tur="sozluk",
            baslik="Deneme Kelime-Frekans",
            surum=COMMIT,
            provider="github",
            kaynak_url=DEPO,
        ),
    )
    for sozluk in SOZLUKLER:
        kayit_yaz(
            kok,
            alanlar_kur(
                sozluk,
                tur="sozluk",
                baslik=f"Deneme {sozluk}",
                provider="archive.org",
                kaynak_url=f"https://deneme.invalid/{sozluk}",
            ),
        )


def lugat_hazirla(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    zip_verisi: bytes | None = None,
    ocr: dict[str, bytes] | None = None,
    gelen_zip: bytes | None = None,
) -> LugatKoku:
    """Sahte kok, gelen dosyalari, kayitlar ve kilit (`gelen_zip` kilitten farkli olabilir)."""
    tmp = tmp_path / "t"
    tmp.mkdir()
    kok = kok_kur(tmp)
    kayitlari_yaz(kok)
    veri_kok = tmp / "data"
    zip_verisi = zip_verisi if zip_verisi is not None else sentetik_zip()
    ocr = ocr if ocr is not None else sentetik_ocr()
    gelen = veri_kok / "gelen" / KAYNAK / TARIH
    gelen.mkdir(parents=True)
    (gelen / ZIP_ADI).write_bytes(gelen_zip if gelen_zip is not None else zip_verisi)
    for sozluk, veri in ocr.items():
        klasor = veri_kok / "gelen" / sozluk / TARIH
        klasor.mkdir(parents=True)
        (klasor / "Deneme Sozluk_djvu.txt").write_bytes(veri)
    kilit_yolu = tmp / "kelime_frekans.lock.json"
    kilit = kilit_onerisi(zip_verisi, ocr, TARIH, DEPO, URL, COMMIT)
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setattr(kelime_frekans, "KILIT_YOLU", kilit_yolu)
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri_kok))
    monkeypatch.chdir(tmp)  # betik calisirsa `CALISTI.txt` buraya duser
    return LugatKoku(tmp, kok, veri_kok, zip_verisi, ocr, kilit_yolu)
