"""QuranWBW ve QAC yukleme testlerinin ortak yardimcilari (test degildir; SENTETIK veri).

`sentetik_6_json` gercek `6.json` BICIMINI taklit eder (sure -> ayet -> `[[kelime anlamlari]]`)
ama icerigi uydurmadir: anlamlar "Deneme anlam N" metinleridir (Kur'an kelimesi ya da gercek bir
kelime anlami degil); kelime sayilari sentetik QAC kelimelerinden gelir (G-BUT ayet basina esitlik
sinar). Turkce i/I gruplamasi icin yalniz "Deneme" + I, i, noktasiz i ve noktali I harflerinden
olusan anlamsiz dizgiler kullanilir; dosya ASCII kalsin diye karakter adlari (N{...}) kullanilir.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur, ctx_kur
from qac_yardimci import TARIH, QacZinciri
from test_sources import alanlar_kur, kayit_yaz
from zincir_yardimci import Zincir

from mutalaa_pipeline.adimlar.enrich_glosses import komut_enrich_glosses
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.ingest import quranwbw
from mutalaa_pipeline.ingest.quranwbw import DOSYA_ADI, kilit_metni, kilit_onerisi
from mutalaa_pipeline.qa import run_quranwbw
from mutalaa_pipeline.qa.run import komut_qa_run
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import satirlari_oku

KAYNAK = "quranwbw-tr"
QAC = "qac-morfoloji"
URL = "https://deneme.invalid/quranwbw/6.json?version=1"
SURUM = "v4-version-1"
# Yalniz I, i, dotless i ve dotted I harflerinden olusan ANLAMSIZ dizgiler: ayni genis anahtar.
I_VARYANTLARI = (
    "Deneme I\N{LATIN SMALL LETTER DOTLESS I}\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}i",
    "Deneme \N{LATIN SMALL LETTER DOTLESS I}i\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}I",
    "Deneme \N{LATIN CAPITAL LETTER I WITH DOT ABOVE}\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}ii",
    "DENEME I\N{LATIN SMALL LETTER DOTLESS I}\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}i",
)
GENIS_I_ANAHTARI = "deneme iiii"


def sentetik_anlam(lemma: str | None, sira: int) -> str:
    """Lemmanin `sira`. gecisi icin anlam (deterministik; 'Deneme anlam N')."""
    if lemma is None:
        return "Deneme lemmasiz 1"
    no = sum(map(ord, lemma)) % 31
    if no % 7 == 0:  # I/i/dotless gruplamasi: dort yazim tek kume
        return I_VARYANTLARI[sira % len(I_VARYANTLARI)]
    if sira % 11 == 5:  # baska bir anlam (kume farki)
        return f"Deneme baska {no}"
    if sira % 9 == 4:  # buyuk-kucuk harf farki: ayni genis anahtar
        return f"DENEME ANLAM {no}"
    return f"Deneme anlam {no}"


def sentetik_6_json(kelimeler: Sequence[Mapping[str, object]]) -> bytes:
    """QAC kelime satirlarindan (`surah`, `ayah`, `word`, `lemma_qac_ref`) sentetik `6.json`."""
    sayac: Counter[str] = Counter()
    ayetler: dict[int, dict[int, list[str]]] = {}
    for k in sorted(
        kelimeler, key=lambda r: (int(str(r["surah"])), int(str(r["ayah"])), int(str(r["word"])))
    ):
        lemma = k["lemma_qac_ref"]
        ref = None if lemma is None else str(lemma)
        sira = sayac[ref or ""]
        sayac[ref or ""] += 1
        sure = ayetler.setdefault(int(str(k["surah"])), {})
        sure.setdefault(int(str(k["ayah"])), []).append(sentetik_anlam(ref, sira))
    govde = {
        str(sure): {str(ayet): [anlamlar] for ayet, anlamlar in sorted(ayet_tablosu.items())}
        for sure, ayet_tablosu in sorted(ayetler.items())
    }
    return json.dumps(govde, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@dataclass
class QuranwbwZinciri:
    """Sahte kokte: QAC zinciri (kosulmus) + sentetik `6.json`, kilit ve kayit."""

    qz: QacZinciri
    ham: bytes
    kilit_yolu: Path

    @property
    def z(self) -> Zincir:
        return self.qz.z

    def ctx(self, adim: str, kaynaklar: list[str], **kw: object) -> RunContext:
        return ctx_kur(self.z.tmp, self.z.kok, adim=adim, kaynaklar=kaynaklar, **kw)  # type: ignore[arg-type]

    def ingest(self, **kw: object) -> int:
        return quranwbw.komut_ingest_quranwbw(
            gelen_tarih=None,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def enrich(self, wave: int = 1, **kw: object) -> int:
        return komut_enrich_glosses(
            wave=wave,
            dry_run=bool(kw.get("dry_run", False)),
            force=bool(kw.get("force", False)),
            config=None,
            kok=self.z.kok,
        )

    def qa(self, **kw: object) -> int:
        return run_quranwbw.komut_qa_run_quranwbw(run=None, gate=None, config=None, kok=self.z.kok)

    def hepsi(self, wave: int = 1) -> None:
        assert self.ingest() == 0
        assert self.enrich(wave) == 0
        assert self.qa() == 0

    def staged(self, kaynak: str, ad: str) -> list[dict[str, object]]:
        klasorler = sorted((self.z.veri_kok / "staged" / kaynak).iterdir(), key=lambda p: p.name)
        for klasor in reversed(klasorler):
            if (klasor / ad).is_file():
                return [s.veri for s in satirlari_oku((klasor / ad).read_bytes(), ad)]
        raise AssertionError(f"{kaynak}/{ad} yok")


def quranwbw_hazirla(
    qz: QacZinciri, monkeypatch: pytest.MonkeyPatch, *, ham: bytes | None = None
) -> QuranwbwZinciri:
    """QAC zincirinin (qa dahil KOSULMUS) ustune sentetik `6.json`, kilit ve kayit koyar."""
    kelimeler = qz.staged(QAC, "words.jsonl")
    veri = ham if ham is not None else sentetik_6_json(kelimeler)
    gelen = qz.z.veri_kok / "gelen" / KAYNAK / TARIH
    gelen.mkdir(parents=True)
    (gelen / DOSYA_ADI).write_bytes(veri)
    (gelen / "SHA256SUMS").write_bytes(
        f"{hashlib.sha256(veri).hexdigest()} *{DOSYA_ADI}\n".encode()
    )
    kilit = kilit_onerisi(veri, TARIH, URL, SURUM)
    kilit_yolu = qz.z.tmp / "quranwbw.lock.json"
    kilit_yolu.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setattr(quranwbw, "KILIT_YOLU", kilit_yolu)
    kayit_yaz(
        qz.z.kok,
        alanlar_kur(
            KAYNAK,
            tur="kelime_anlami",
            baslik="Deneme QuranWBW",
            surum=SURUM,
            provider="quranwbw",
            kaynak_url=URL,
        ),
    )
    return QuranwbwZinciri(qz, veri, kilit_yolu)


# --- veritabani yardimcilari ---------------------------------------------------------------


def ihracat(z: Zincir, conn: psycopg.Connection, source: str, **kw: object) -> int:
    """`export pg --source <source>` (baglanti disaridan; kapatilmaz)."""
    return pg.komut_export_pg(
        ayarlar_kur(z.tmp),
        depo_kok=z.kok,
        source=source,
        baglanti=lambda: conn,
        **kw,  # type: ignore[arg-type]
    )


def tanzil_qa(z: Zincir) -> None:
    """`tanzil-uthmani` QA raporu (Tanzil yuklemesi icin)."""
    assert komut_qa_run(source="tanzil-uthmani", run=None, gate=None, config=None, kok=z.kok) == 0
