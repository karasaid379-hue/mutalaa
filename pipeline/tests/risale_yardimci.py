# ruff: noqa: RUF001, RUF002
"""Risale (Diyanet) testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

Hicbir Risale metni yoktur: paragraflar "Deneme paragrafi N ..." metinleridir; Arapca isaretler
Arap alfabesinin harflerinden ("ا ب ت ث ...") olusur ve dosya ASCII kalsin diye ozel karakterler
kacis dizileriyle yazilir. Zip bellekte uretilir (diske acilmaz); gercek `data/` kullanilmaz.
"""

import io
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline.ingest import risale_diyanet
from mutalaa_pipeline.ingest.risale_diyanet import DEPO_ONEKI, KAYNAK, kilit_metni, kilit_onerisi
from mutalaa_pipeline.runctx import RunContext

COMMIT = "0123456789abcdef0123456789abcdef01234567"
KOK_ADI = f"Risale-i-Nur-Diyanet-{COMMIT}"
ZIP_ADI = f"{KOK_ADI}.zip"
TARIH = "2026-11-12"
ARAPCA_1 = "ا ب ت ث"
ARAPCA_2 = "ا ب ت ث ج"
ARAPCA_3 = "ح خ د ذ ر ز"
NFC_DEGIL = "بَّ"  # shadda + fatha: NFC bunu fatha + shadda yapar

TXT_1 = "\n".join(
    [
        "Deneme Başlığı",
        ARAPCA_1,
        "Deneme paragrafı 1 (Hâşiye[1]) devam.",
        f"Deneme paragrafı 2 {ARAPCA_2} içinde.",
        "Deneme\N{SOFT HYPHEN}paragrafı 3 ve\N{ZERO WIDTH NON-JOINER}bir\N{NO-BREAK SPACE}boşluk.",
        "***",
        "Deneme alt başlık",
        f"Deneme paragrafı 4 {NFC_DEGIL} NFC değil.",
        "***",
        "[1] Hâşiye: Deneme dipnotu 1.",
        "Deneme dipnotu devam satırı.",
        "[2] Hâşiye: Deneme dipnotu 2.",
        "",
    ]
)
MD_1 = "\n".join(
    [
        "---",
        "source_name: Deneme",
        "---",
        "",
        "# Deneme Başlığı",
        "",
        f'<p class="arabic" dir="rtl">{ARAPCA_1}</p>',
        "",
        "Deneme paragrafı 1 [^hâşiye1] devam.",
        "",
        f'Deneme paragrafı 2 <span class="arabic" dir="rtl">{ARAPCA_2}</span> içinde.',
        "",
        "Deneme\N{SOFT HYPHEN}paragrafı 3 ve\N{ZERO WIDTH NON-JOINER}bir\N{NO-BREAK SPACE}boşluk.",
        "",
        "***",
        "",
        "## Deneme alt başlık",
        "",
        f"**Deneme** paragrafı 4 {NFC_DEGIL} NFC değil.",
        "",
        "***",
        "",
        "[^hâşiye1]: Deneme dipnotu 1.",
        "",
        "Deneme dipnotu devam satırı.",
        "",
        "[^hâşiye2]: Deneme dipnotu 2.",
        "",
        "[^hâşiye3]: Yalnız markdown dipnotu.",
        "",
    ]
)
# `<br/>` ile bolunmus Arapca blok, txt'de TEK satir (kaynak tutarsizligi): ikinci gecis eslestirir.
TXT_2 = "\N{ZERO WIDTH NO-BREAK SPACE}" + "\r\n".join(
    ["Deneme Ikinci", f"{ARAPCA_2} {ARAPCA_3}", "Deneme paragrafı 5.", ""]
)
MD_2 = "\n".join(
    [
        "# Deneme Ikinci",
        "",
        f'<p class="arabic" dir="rtl">{ARAPCA_2}<br/>{ARAPCA_3}</p>',
        "",
        "Deneme paragrafı 5.",
        "",
    ]
)
TXT_3 = "Deneme Kucuk Kitap\nDeneme paragrafı 6.\n"
MD_3 = "# Deneme Kucuk Kitap\n\nDeneme paragrafı 6.\n"

KIMLIK: dict[str, object] = {
    "surum": 1,
    "kitaplar": [
        {
            "slug": "deneme",
            "txt_klasor": "01 Deneme",
            "md_klasor": "01 Deneme",
            "dosyalar": [
                {"txt": "Deneme-01-Birinci.txt", "md": "01 Birinci.md", "bolum": "soz-1"},
                {"txt": "Deneme-02-Ikinci.txt", "md": "02 Ikinci.md", "bolum": "soz-3"},
            ],
        },
        {
            "slug": "kucuk-deneme",
            "txt_klasor": "02 Kucuk",
            "md_klasor": "02 Kucuk",
            "dosyalar": [{"txt": "Kucuk.txt", "md": "00 Kucuk.md", "bolum": None}],
        },
    ],
    "md_yalniz": {},
}
UYELER_1: dict[str, bytes] = {
    "txt/01 Deneme/Deneme-01-Birinci.txt": TXT_1.encode("utf-8"),
    "obsidian-markdown/01 Deneme/01 Birinci.md": MD_1.encode("utf-8"),
    "txt/01 Deneme/Deneme-02-Ikinci.txt": TXT_2.encode("utf-8"),
    "obsidian-markdown/01 Deneme/02 Ikinci.md": MD_2.encode("utf-8"),
    "txt/02 Kucuk/Kucuk.txt": TXT_3.encode("utf-8"),
    "obsidian-markdown/02 Kucuk/00 Kucuk.md": MD_3.encode("utf-8"),
    "README.md": b"Deneme README\n",
}


def zip_yap(
    uyeler: Mapping[str, bytes], *, kok: str = KOK_ADI, sikistir: int = zipfile.ZIP_DEFLATED
) -> bytes:
    """Bellekte zip: her uye `kok/` altinda (GitHub zip'i gibi)."""
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", sikistir) as z:
        for ad, veri in uyeler.items():
            z.writestr(f"{kok}/{ad}", veri)
    return tampon.getvalue()


def kimlik_baytlari(kimlik: Mapping[str, object] | None = None) -> bytes:
    return (
        json.dumps(kimlik if kimlik is not None else KIMLIK, ensure_ascii=True, indent=1) + "\n"
    ).encode("utf-8")


@dataclass
class RisaleKoku:
    """Sahte depo kokunde sentetik zip, kimlik tablosu, kilit ve kaynak kaydi."""

    tmp: Path
    kok: Path
    veri_kok: Path
    zip_baytlari: bytes
    kilit_yolu: Path
    kimlik_yolu: Path

    @property
    def gelen_zip(self) -> Path:
        return self.veri_kok / "gelen" / KAYNAK / TARIH / ZIP_ADI

    def ctx(self, adim: str = "qa", **kw: object) -> RunContext:
        return ctx_kur(self.tmp, self.kok, adim=adim, kaynaklar=[KAYNAK], **kw)  # type: ignore[arg-type]

    def ingest(self, **kw: object) -> int:
        return risale_diyanet.komut_ingest_risale(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.kok,
        )

    def qa(self, gate: list[str] | None = None, run: str | None = None) -> int:
        from mutalaa_pipeline.qa import run_risale

        return run_risale.komut_qa_run_risale(run=run, gate=gate, config=None, kok=self.kok)

    def staged_klasorleri(self) -> list[Path]:
        kok = self.veri_kok / "staged" / KAYNAK
        return sorted(p for p in kok.iterdir() if p.is_dir()) if kok.is_dir() else []

    def units(self) -> list[dict[str, object]]:
        klasor = self.staged_klasorleri()[-1]
        satirlar = (klasor / "units.jsonl").read_bytes().decode("utf-8").splitlines()
        return [json.loads(s) for s in satirlar]


def risale_hazirla(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    uyeler: Mapping[str, bytes] | None = None,
    kilit_uyeleri: Mapping[str, bytes] | None = None,
    kimlik: Mapping[str, object] | None = None,
) -> RisaleKoku:
    """Sentetik zip `gelen` altina konur; kilit `kilit_uyeleri`nden (varsayilan `uyeler`) gelir.

    `kilit_uyeleri` ayriysa gelen zip kilitle TUTMAZ (kilit uyusmazligi senaryosu).
    """
    kok = kok_kur(tmp_path)
    veri_kok = tmp_path / "data"
    zip_baytlari = zip_yap(uyeler if uyeler is not None else UYELER_1)
    kilit_zip = zip_yap(kilit_uyeleri) if kilit_uyeleri is not None else zip_baytlari
    gelen = veri_kok / "gelen" / KAYNAK / TARIH
    gelen.mkdir(parents=True)
    (gelen / ZIP_ADI).write_bytes(zip_baytlari)
    kimlik_yolu = tmp_path / "risale_diyanet_kimlik.json"
    kimlik_yolu.write_bytes(kimlik_baytlari(kimlik))
    kilit = kilit_onerisi(
        kilit_zip,
        TARIH,
        DEPO_ONEKI,
        f"{DEPO_ONEKI}/archive/{COMMIT}.zip",
        COMMIT,
        risale_diyanet.kimlik_yukle(kimlik_yolu),
    )
    kilit_yolu = tmp_path / "risale.lock.json"
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri_kok))
    monkeypatch.setattr(risale_diyanet, "KILIT_YOLU", kilit_yolu)
    monkeypatch.setattr(risale_diyanet, "KIMLIK_YOLU", kimlik_yolu)
    kayit_yaz(
        kok,
        alanlar_kur(
            KAYNAK,
            tur="risale",
            baslik="Deneme Diyanet",
            surum=COMMIT,
            provider="github",
            kaynak_url=DEPO_ONEKI,
        ),
    )
    return RisaleKoku(tmp_path, kok, veri_kok, zip_baytlari, kilit_yolu, kimlik_yolu)
